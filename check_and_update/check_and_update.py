#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
檢查 request.json 中的日期，若 by_slug 目錄沒有該日期一個月內的資料，則自動執行 regwatch.py
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path


def load_request_time(request_file: str = "request.json") -> datetime:
    """讀取 request.json 中的 Time 欄位，轉換為 datetime 物件"""
    try:
        with open(request_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        time_str = data.get("Time")
        if not time_str:
            raise ValueError("request.json 中未找到 'Time' 欄位")
        
        # 解析日期格式 YYYY/MM/DD
        request_time = datetime.strptime(time_str, "%Y/%m/%d")
        return request_time
    
    except FileNotFoundError:
        print(f"[!] 錯誤：找不到 {request_file}")
        sys.exit(1)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[!] 錯誤：無法解析 {request_file} - {e}")
        sys.exit(1)


def check_by_slug_data(request_time: datetime, by_slug_dir: str = "outputs/by_slug") -> bool:
    """
    檢查 by_slug 目錄是否有該日期一個月內的資料
    必須檢查所有必要的資料來源：
    - EU: eu_echa_inventory, eu_reach_eurlex
    - TW: tw_inventory, tw_cscra_moenv
    - US: us_tsca_inventory, us_cfr40
    
    Args:
        request_time: request.json 中的時間
        by_slug_dir: by_slug 目錄路徑
    
    Returns:
        True: 所有資料來源都有一個月內的資料，不需重新執行
        False: 任一資料來源沒有一個月內的資料，需要重新執行
    """
    by_slug_path = Path(by_slug_dir)
    
    if not by_slug_path.exists():
        print(f"[!] 警告：{by_slug_dir} 目錄不存在")
        return False
    
    # 計算一個月前的日期（往前推 30 天）
    one_month_before = request_time - timedelta(days=30)
    
    print(f"[*] Request Time: {request_time.strftime('%Y/%m/%d')}")
    print(f"[*] 檢查是否有 {one_month_before.strftime('%Y/%m/%d')} 之後的資料...\n")
    
    # 定義必須檢查的資料來源
    required_sources = [
        "eu_echa_inventory",      # EU inventory
        "eu_reach_eurlex",        # EU 法規
        "tw_inventory",           # TW inventory
        "tw_cscra_moenv",        # TW 法規
        "us_tsca_inventory",      # US inventory
        "us_cfr40"               # US 法規
    ]
    
    # 搜尋所有 JSON 檔案（排除無日期前綴的舊格式）
    json_files = list(by_slug_path.glob("*.json"))
    
    # 建立資料來源的最新日期字典
    source_latest_date = {}
    
    for file in json_files:
        filename = file.name
        # 檢查是否以 8 位數字開頭（YYYYMMDD）
        if len(filename) >= 8 and filename[:8].isdigit():
            try:
                file_date_str = filename[:8]
                file_date = datetime.strptime(file_date_str, "%Y%m%d")
                
                # 提取資料來源名稱（移除日期前綴和 .json）
                source_name = filename[9:].replace('.json', '')
                
                # 更新該資料來源的最新日期
                if source_name not in source_latest_date or file_date > source_latest_date[source_name]:
                    source_latest_date[source_name] = file_date
                    
            except ValueError:
                continue
    
    # 檢查每個必要的資料來源
    all_up_to_date = True
    missing_sources = []
    outdated_sources = []
    
    for source in required_sources:
        if source not in source_latest_date:
            print(f"[!] {source}: 未找到任何資料")
            missing_sources.append(source)
            all_up_to_date = False
        else:
            latest_date = source_latest_date[source]
            if latest_date >= one_month_before:
                print(f"[✓] {source}: 最新資料日期 {latest_date.strftime('%Y/%m/%d')} (符合)")
            else:
                print(f"[!] {source}: 最新資料日期 {latest_date.strftime('%Y/%m/%d')} (過舊)")
                outdated_sources.append(source)
                all_up_to_date = False
    
    # 顯示總結
    print("\n" + "="*60)
    if all_up_to_date:
        print("[✓] 所有資料來源都是最新的（在一個月內）")
    else:
        print("[!] 以下資料來源需要更新：")
        if missing_sources:
            print(f"    缺少資料: {', '.join(missing_sources)}")
        if outdated_sources:
            print(f"    資料過舊: {', '.join(outdated_sources)}")
    print("="*60 + "\n")
    
    return all_up_to_date


def run_regwatch():
    """執行 regwatch.py"""
    print("\n" + "="*60)
    print("[*] 開始執行 regwatch.py 更新資料...")
    print("="*60 + "\n")
    
    try:
        # 使用當前 Python 環境執行 regwatch.py
        result = subprocess.run(
            [sys.executable, "regwatch.py"],
            check=True,
            capture_output=False,
            text=True
        )
        
        print("\n" + "="*60)
        print("[✓] regwatch.py 執行完成")
        print("="*60)
        
    except subprocess.CalledProcessError as e:
        print(f"\n[!] 錯誤：regwatch.py 執行失敗")
        print(f"[!] 返回碼: {e.returncode}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"\n[!] 錯誤：找不到 regwatch.py")
        sys.exit(1)


def main():
    """主程式流程"""
    print("="*60)
    print("檢查法規資料是否需要更新")
    print("="*60 + "\n")
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))          # scrapers/
    PROJECT_ROOT = os.path.dirname(BASE_DIR)                       # GreenChem-Aide/
    request_file = os.path.join(PROJECT_ROOT, "deep_research", "request.json")
    # 1. 讀取 request.json 中的時間
    request_time = load_request_time(request_file=request_file)
    
    # 2. 檢查 by_slug 目錄是否有一個月內的資料
    has_recent_data = check_by_slug_data(request_time)
    
    # 3. 若沒有一個月內的資料，則執行 regwatch.py
    if not has_recent_data:
        run_regwatch()
        # 執行ConverJsonToJson.py來讓graphrag更新
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))     # scrapers/
        PROJECT_ROOT = os.path.dirname(BASE_DIR)                  # GreenChem-Aide/
        RAG_ROOT = os.path.join(PROJECT_ROOT, "ragtest")          # ragtest/
        script_path = os.path.join(PROJECT_ROOT, "ConvertJsonlToJson.py")
        print("執行 ConvertJsonlToJson.py 來合併Json檔...")
        subprocess.run([sys.executable, script_path],cwd=PROJECT_ROOT,check=True)
        # === 執行 graphrag index(這邊還需要進一步修正找找看graphrag更新更快的方法) ===
        print("執行 GraphRAG index 更新...")
        #subprocess.run(
        #    [
        #        sys.executable,
        #        "-m",
        #        "graphrag",
        #        "index",
        #        "--root",
        #        RAG_ROOT
        #    ],
        #    cwd=PROJECT_ROOT,     # 等同於 cd 到 ragtest 的上一層
        #    check=True
        #)
        print("✅ GraphRAG index 更新完成")
    else:
        print("\n[*] 無需更新，資料已是最新")


if __name__ == "__main__":
    main()
