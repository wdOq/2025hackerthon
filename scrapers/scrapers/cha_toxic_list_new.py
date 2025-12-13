#!/usr/bin/env python3
"""
環境部化學物質管理署毒性及關注化學物質清單爬蟲
移除URL並解析詳細化學物質資訊
"""

import os
import sys
import json
import time
import re
from datetime import datetime, timezone, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class CHAToxicListScraper:
    def __init__(self):
        self.base_url = "https://www.cha.gov.tw/sp-toch-list-1.html"
        self.driver = None
        
    def taipei_now(self):
        """取得台北時間"""
        return datetime.now(timezone(timedelta(hours=8)))

    def scrape(self):
        """主要爬取函數"""
        try:
            print("開始爬取環境部化學物質管理署毒性及關注化學物質清單...")
            
            # 設定Chrome選項
            chrome_options = self._get_chrome_options()
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # 載入主頁面
            print("載入主頁面...")
            self.driver.get(self.base_url)
            time.sleep(3)
            
            # 抓取化學物質記錄
            print("開始抓取化學物質記錄...")
            records = self._extract_chemical_records()
            
            # 生成結果
            result = self._generate_result(records)
            
            # 保存結果
            self._save_result(result)
            
            print(f"成功抓取 {len(records)} 筆化學物質資料")
            return result
            
        except Exception as e:
            print(f"抓取過程發生錯誤: {e}")
            raise e
        finally:
            if self.driver:
                self.driver.quit()

    def _get_chrome_options(self):
        """Chrome 瀏覽器選項設定"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-images')
        return chrome_options

    def _extract_chemical_records(self):
        """抓取化學物質記錄"""
        records = []
        
        try:
            # 尋找所有化學物質連結
            chemical_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='sp-toch-form']")
            
            print(f"找到 {len(chemical_links)} 個化學物質連結")
            
            # 取得所有連結的URL，避免DOM變化問題
            link_data = []
            for link in chemical_links:
                try:
                    link_text = link.text.strip()
                    link_url = link.get_attribute('href')
                    if link_text and link_url:
                        link_data.append((link_text, link_url))
                except Exception as e:
                    print(f"取得連結資料時發生錯誤: {e}")
                    continue
            
            print(f"準備抓取 {len(link_data)} 筆詳細資料")
            
            # 只處理第一個化學物質進行測試
            for i, (link_text, link_url) in enumerate(link_data):
                if i >= 1:  # 只處理第一個
                    break
                try:
                    # 解析基本資訊並獲取詳細資訊
                    record = self._parse_and_extract_chemical_info(link_text, link_url)
                    
                    if record:
                        records.append(record)
                        
                    print(f"已處理 {i + 1} 筆資料")
                        
                except Exception as e:
                    print(f"處理第 {i} 筆資料時發生錯誤: {e}")
                    continue
                    
        except Exception as e:
            print(f"抓取化學物質記錄時發生錯誤: {e}")
            
        return records

    def _parse_and_extract_chemical_info(self, link_text, link_url):
        """解析並提取化學物質完整資訊"""
        try:
            # 解析基本文字資訊
            parsed_info = self._parse_text_content(link_text)
            
            # 抓取詳細頁面資訊
            detailed_info = self._extract_chemical_details(link_url)
            
            # 建立完整記錄（只保留指定欄位）
            record = {
                "toxicity_level": parsed_info.get('toxicity_level', ''),
                "cas_number": parsed_info.get('cas_number', ''),
                "chinese_name": parsed_info.get('chinese_name', ''),
                "english_name": parsed_info.get('english_name', ''),
                "control_measures": detailed_info.get('control_measures', ''),
                "usage_description": detailed_info.get('usage_description', ''),
            }
            
            return record
            
        except Exception as e:
            print(f"解析化學物質資訊時發生錯誤: {e}")
            return None

    def _parse_text_content(self, text):
        """解析text欄位內容，提取毒物層級、CAS號、中文名稱、英文名稱"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        parsed = {
            'toxicity_level': '',
            'cas_number': '',
            'chinese_name': '',
            'english_name': ''
        }
        
        if len(lines) >= 6:
            # 基於已知的格式進行解析
            # 第0行：列管編號001-01
            # 第1行：1 (毒物層級第一部分)
            # 第2行：2 (毒物層級第二部分，但這裡是分類)
            # 第3行：1336-36-3等 (CAS號)
            # 第4行：多氯聯苯 (中文名稱)
            # 第5行：Polychlorinated biphenyls (英文名稱)
            
            # 根據您的要求，毒物層級應該是 "1、2" 
            if len(lines) >= 3 and lines[1].isdigit() and lines[2].isdigit():
                parsed['toxicity_level'] = f"{lines[1]}、{lines[2]}"
            elif len(lines) >= 2 and lines[1].isdigit():
                parsed['toxicity_level'] = lines[1]
            
            # CAS號 (第3行)
            if len(lines) >= 4:
                parsed['cas_number'] = lines[3]
            
            # 中文名稱 (第4行)
            if len(lines) >= 5:
                parsed['chinese_name'] = lines[4]
            
            # 英文名稱 (第5行)
            if len(lines) >= 6:
                parsed['english_name'] = lines[5]
        
        return parsed

    def _extract_chemical_details(self, link_url):
        """抓取化學物質詳細資訊"""
        try:
            self.driver.get(link_url)
            time.sleep(2)
            
            details = {
                "control_measures": "",
                "usage_description": "",
            }
            
            # 抓取表格資料
            try:
                tables = self.driver.find_elements(By.TAG_NAME, "table")
                for table in tables:
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    for row in rows:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 2:
                            key = cells[0].text.strip()
                            value = cells[1].text.strip()
                            
                            if "公告日期" in key:
                                details["announcement_date"] = value
            except Exception as e:
                print(f"抓取表格資料時發生錯誤: {e}")
            
            # 抓取管制事項和用途說明
            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                
                # 管制事項
                lines = page_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if any(keyword in line for keyword in ["禁止", "允許", "准繼續使用", "不在此限"]) and len(line) > 20:
                        details["control_measures"] = line
                        break
                
                # 用途說明
                if "用途：" in page_text:
                    usage_start = page_text.find("用途：")
                    # 找到下一個段落或適當的結束點
                    usage_text = page_text[usage_start:usage_start + 300]
                    lines = usage_text.split('\n')
                    usage_lines = []
                    for line in lines:
                        line = line.strip()
                        if line.startswith("用途：") or (line and not line.startswith("用途：")):
                            usage_lines.append(line)
                            if len(usage_lines) >= 3:  # 限制長度
                                break
                    details["usage_description"] = " ".join(usage_lines)
                    
            except Exception as e:
                print(f"抓取文字內容時發生錯誤: {e}")
            
            return details
            
        except Exception as e:
            print(f"抓取詳細資訊時發生錯誤: {e}")
            return {}

    def _generate_result(self, records):
        """生成最終結果"""
        taipei_time = self.taipei_now()
        
        # 生成內容摘要
        content_summary = f"# 環境部化學物質管理署毒性及關注化學物質清單\n"
        content_summary += f"總計: {len(records)} 筆化學物質資料\n\n"
        
        for record in records:
            content_summary += f"## {record.get('chinese_name', '化學物質')}\n"
            if record.get('toxicity_level'):
                content_summary += f"毒物層級: {record['toxicity_level']}\n"
            if record.get('cas_number'):
                content_summary += f"CAS號: {record['cas_number']}\n"
            if record.get('english_name'):
                content_summary += f"英文名稱: {record['english_name']}\n"
            if record.get('control_measures'):
                content_summary += f"管制事項: {record['control_measures'][:100]}...\n"
            content_summary += "\n"
        
        result = {
            "title": "環境部化學物質管理署毒性及關注化學物質清單",
            "content": content_summary,
            "full_content": content_summary,
            "per_section_records": records,
            "fetched_time": taipei_time.isoformat(),
            "source": "cha.gov.tw"
        }
        
        return result

    def _save_result(self, result):
        """保存結果到檔案"""
        # 確保輸出目錄存在
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存JSON檔案
        output_file = os.path.join(output_dir, "cha_toxic_list.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"結果已保存到: {output_file}")

if __name__ == "__main__":
    scraper = CHAToxicListScraper()
    result = scraper.scrape()
    print("抓取完成！")