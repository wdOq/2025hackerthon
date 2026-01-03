import getpass
import os
import requests
from langchain_tavily import TavilySearch
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
import json
import sys
import csv
import subprocess
from flask import Flask
from flask import request, jsonify
from openai import OpenAI
#-----------------------------------------------APIKEY------------------------------------------------#
if not os.environ.get("TAVILY_API_KEY"):
    os.environ["TAVILY_API_KEY"] = getpass.getpass("Enter TAVILY API key: ")

if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter OpenAI API key: ")

#-----------------------------------------------Tools------------------------------------------#
@tool
def SASdatabase(query: str) -> dict:
    """
    This tool can be use to find chemical substance information from SAS database.
    
    Args:
        CID: 化學物質的化學識別碼 (Chemical ID)。
    """
    resp = requests.get(f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{query}/xrefs/RN/JSON")
    cas_numbers = []
    resp.raise_for_status()
    data = resp.json()
    cas_numbers = data.get("InformationList", {}).get("Information", [])[0].get("RN", [])
    for cas_no in cas_numbers:
        # 確保 cas_no 是字串且不含空
        if not cas_no or not isinstance(cas_no, str):
            continue
            
        sas_url = f"https://sas.cmdm.tw/api/casnos/{cas_no.strip()}"
        print(f"[Tool Log] 正在嘗試查詢 sas.cmdm.tw: {sas_url}")
        try:
            response_sas = requests.get(sas_url, timeout=10)
            
            # 根據您的要求："直到回傳結果"
            # 我們假設 200 OK 是唯一 "成功" 的狀態
            if response_sas.status_code == 200:
                # 找到了！驗證它是否為有效的 JSON
                try:
                    data_sas = response_sas.json()
                    print(f"[Tool Log] 成功！使用 CAS 號 {cas_no} 在 sas.cmdm.tw 找到資料。")
                    return {
                        "source": "SAS",
                        "CID": query,           # 回傳 CID
                        "result": data_sas #f"{search.invoke(f"CID: {CID}")}" 
                    }
                except requests.JSONDecodeError:
                    # API 回傳 200 但內容不是 JSON，這可能是一個錯誤
                    print(f"[Tool Warn] SAS API (CAS: {cas_no}) 回傳 200，但內容不是有效的 JSON。繼續嘗試下一個...")
                    continue # 繼續嘗試下一個 CAS 號
            
            # 如果是 404 (Not Found)，這是預期中的 "失敗"，我們就安靜地繼續嘗試下一個
            elif response_sas.status_code == 404:
                print(f"[Tool Log] CAS 號 {cas_no} 在 sas.cmdm.tw 查無資料 (404)。")
                continue
            
            # 其他錯誤 (500, 403, 400 等)
            else:
                print(f"[Tool Warn] SAS API (CAS: {cas_no}) 查詢失敗: 狀態 {response_sas.status_code}")
                # 即使出錯，我們也繼續嘗試下一個 CAS 號
                continue

        except requests.RequestException as e:
            print(f"[Tool Error] SAS API (CAS: {cas_no}) 請求失敗: {e}")
            # 網路錯誤，繼續嘗試下一個
            continue
@tool
def Convert_to_CID(query: str) -> dict:
    """This tool can be use to convert chemical substance name to CID."""
    resp = requests.get(f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{query}/cids/JSON")
    try:
        resp.raise_for_status()
        data = resp.json()
        cids = data.get("IdentifierList", {}).get("CID", [])
    except Exception:
        # On error, return the raw status and text for debugging
        return {
            "source": "ConverttoCID",
            "query": query,
            "result": {"error": resp.text if resp is not None else "request failed"}
        }
    resp = requests.get(f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cids}/property/CAS/JSON")#這行應該可以刪掉
    return {
        "source": "ConverttoCID",
        "query": query,
        "result": cids
    }
@tool
def Deepsurvey(query: str, CID: str) -> dict:
    """This tool can be use to find chemical substance information from Deepsurvey database."""
    """當你需要從 Deepsurvey 資料庫中查詢化學物質資訊時，請使用此工具。
    你需要提供化學物質的 CID (Chemical ID) 及化學物名稱作為輸入。"""
    # 取得 agent.py 所在的資料夾 (GreenChem-Aide)
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # 設定 deep_research 資料夾路徑
    DEEP_RESEARCH_DIR = os.path.join(BASE_DIR, "deep_research")
    
    # 設定相關檔案路徑
    REQUEST_JSON_PATH = os.path.join(DEEP_RESEARCH_DIR, "request.json")
    OUTPUT_DIR = os.path.join(BASE_DIR, "final_output")
    print(f"[Deepsurvey] 收到查詢: {query}, CID: {CID}")
    #--- 2. 寫入 request.json ---
    try:
        current_time = datetime.now().strftime("%Y/%m/%d")
        
        payload = {
            "CID": CID,
            "Time": current_time
        }
        
        # 確保資料夾存在
        os.makedirs(DEEP_RESEARCH_DIR, exist_ok=True)
        
        with open(REQUEST_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=4)
            
        print(f"[Deepsurvey] 已寫入請求至: {REQUEST_JSON_PATH}")
        
    except Exception as e:
        return {"error": f"寫入 request.json 失敗: {str(e)}", "query": CID}

    # --- 3. 執行 run_request.py ---
    try:
        print(f"[Deepsurvey] 正在執行 run_request.py ...")
        
        # cwd=DEEP_RESEARCH_DIR 確保腳本是在 deep_research 目錄下執行
        subprocess.run(
            ["python", "run_request.py"], 
            check=True, 
            cwd=DEEP_RESEARCH_DIR
        )
        print("[Deepsurvey] 外部腳本執行完畢。")
        
    except subprocess.CalledProcessError as e:
        return {"error": f"執行 run_request.py 失敗: {str(e)}", "query": CID}
    except Exception as e:
        return {"error": f"執行過程發生未知錯誤: {str(e)}", "query": CID}

    # --- 4. 從 final_output 提取結果 ---
    result_data = None
    target_file_path = None
    
    if os.path.exists(OUTPUT_DIR):
        # 搜尋策略：優先找檔名包含 CID 的 json，若無則找最新產生的 json
        json_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.json')]
        
        if json_files:
            # 嘗試尋找檔名包含 CID 的檔案 (例如 7858.json 或 result_7858.json)
            for file in json_files:
                if CID in file:
                    target_file_path = os.path.join(OUTPUT_DIR, file)
                    break
            
            # 如果沒找到特定 CID 的檔案，就抓列表中的第一個 (假設 pipeline 只產出一個結果)
            if not target_file_path and len(json_files) > 0:
                print(f"在跑完run_request.py後[Deepsurvey] 未找到特定 CID 的結果。")
    
    # 讀取檔案內容
    if target_file_path and os.path.exists(target_file_path):
        try:
            with open(target_file_path, 'r', encoding='utf-8') as f:
                result_data = json.load(f)
            print(f"[Deepsurvey] 成功讀取結果: {target_file_path}")
            return {
            "source": "Deepsurvey", 
            "query": CID, 
            "result": result_data
        }
        except Exception as e:
            return {"error": f"讀取結果 JSON 失敗: {str(e)}", "query": CID}
    else:
        return {
            "error": "Pipeline 執行完成，但在 final_output 資料夾中找不到對應的 JSON 結果。",
            "query": CID,
            "checked_path": OUTPUT_DIR
        }
                
@tool
def GraphRAG(query: str) -> str:
    """
    當你需要使用 GraphRAG 系統來回答特定法律規範知識時，
    請使用此工具。它會對設定在 './ragtest' 路徑下的資料庫執行本地查詢。
    請傳入你的自然語言查詢問題。
    """
    
    print(f"[GraphRAG Tool] 收到查詢: {query}")

    # 1. 構建命令
    # 我們將命令作為一個 list 傳遞給 subprocess.run
    # 這是最安全的方式，可以避免 shell 注入 (shell injection) 風險
    # 
    # 您的命令: python -m graphrag query --root ./ragtest --method local --query "..."
    # 注意: 我們使用 sys.executable 來確保我們用的是當前
    # 執行此 Python 腳本的同一個 Python 直譯器
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    command = [
        sys.executable,  # 使用當前的 Python 路徑 (等同於 'python')
        "-m",            # 模組標記
        "graphrag",      # 模組名稱
        "query",         # 指令
        "--root",        # 參數
        "./ragtest",     # 參數值
        "--method",      # 參數
        "local",         # 參數值
        "--query",       # 參數 (查詢內容)
        query            # Agent 傳入的查詢字串
    ]

    print(f"[GraphRAG Tool] 準備執行命令: {' '.join(command)}")

    # 2. 執行命令並捕獲輸出
    try:
        # subprocess.run() 是現代 Python 中執行外部命令的推薦方法
        result = subprocess.run(
            command,
            capture_output=True, # 捕獲 stdout 和 stderr
            text=True,           # 以文字模式 (str) 回傳，而不是 bytes
            check=True,          # 如果命令執行失敗 (回傳非 0 狀態碼)，則引發例外
            encoding='utf-8',    # 確保使用 UTF-8 編碼
            errors='replace', # 增加一點容錯
            env=env
        )
        
        # 3. 回傳成功的輸出
        # result.stdout 包含了命令執行後印在終端機上的所有內容
        print(f"[GraphRAG Tool] 執行成功。回傳 stdout 內容。")
        return result.stdout

    except subprocess.CalledProcessError as e:
        # 4. 處理命令執行失敗
        # 如果 'check=True' 捕捉到錯誤 (例如 graphrag 崩潰)
        print(f"[GraphRAG Tool] 錯誤: 命令執行失敗，回傳碼 {e.returncode}")
        print(f"[GraphRAG Tool] Stderr: {e.stderr}")
        # 將錯誤訊息回傳給 Agent
        return f"GraphRAG 執行錯誤:\nReturn Code: {e.returncode}\nError: {e.stderr}"
        
    except FileNotFoundError:
        # 5. 處理找不到命令 (例如 'python' 或 'graphrag' 模組未安裝)
        print(f"[GraphRAG Tool] 錯誤: 找不到命令。")
        return f"工具執行錯誤: 找不到 '{sys.executable}' 或 'graphrag' 模組。請檢查 Python 環境。"
        
    except Exception as e:
        # 6. 處理其他未知錯誤
        print(f"[GraphRAG Tool] 發生未知錯誤: {e}")
        return f"工具發生未知錯誤: {str(e)}"
#-----------------------------------------------初始化------------------------------------------#
search = TavilySearch(max_results=2)
tools = [search, SASdatabase, Deepsurvey, Convert_to_CID, GraphRAG]
model = init_chat_model("gpt-4o-mini", model_provider="openai")
agent_executor = create_react_agent(model, tools)
#-----------------------------------------------AGENT------------------------------------------#
few_shot_examples = ["""
    您是一個專業的化學資料分析師，您的任務是處理最新的使用者輸入，您唯一需要關注的化學物質關鍵字，是最新的 role: user 訊息中出現的那個。若使用者輸入的內容與化學物無關，請禮貌地告知使用者您只能處理化學物相關的查詢。
    首先找出使用者輸入中的化學物關鍵字，GraphRAG及SASdatabase皆可直接輸入化學物關鍵字名稱，GraphRAG負責尋找化合物的相關法律規範，SASdatabase負責查詢風險資料，deepsurvey負責查詢該物質的替代物、應用。若使用者輸入CID則可以直接將號碼傳入deepsurvey，若不是則須先使用Convert_to_CID將化學物關鍵字轉成CID號碼，再傳入deepsurvey搜尋相關資料。
    一定要使用到所有的工具。根據我給的範例請用以下方式呈現我要的資料1.我需要你將思考的邏輯呈現出來2.利用SAS、Deepsurvey、Convert_to_CID和GraphRAG工具去尋找使用者想要的資料，以下是幾個例子:
example1.
使用者問:1,2-二氯乙烷有哪些替代物?
AGENT要回答:
- 以下是我的思考邏輯:
提取使用者關鍵字->將使用者輸入的化學物名稱利用Convert_to_CID轉成CID號碼->呼叫工具SAS傳入化學物名稱獲得該物質替代物、應用與風險資料->呼叫工具Deepsurvey將CID號碼傳入搜尋替代物、應用與風險資料->呼叫GraphRAG獲取法律規範資料->獲取資料來源->產生替代物研究報告
- 報表如下:
1,2-二氯乙烷（1,2-dichloroethane，簡稱1,2-DCE）是一種常用的有機溶劑，但由於其具備毒性、可燃性，並被視為可能的致癌物，許多實驗室已尋求更安全的替代品。以下是幾種常見的替代溶劑及其說明：1.二氯甲烷（DCM）：常用溶劑，揮發性高，適用於多種應用，但仍具毒性和致癌風險。資料來源：南加州大學環境健康與安全2022。2.2-甲基四氫呋喃（2-MeTHF）：生物可降解，低毒性，可作為有機反應的溶劑。資料來源：麻省理工學院綠色化學中心2021。3.叔丁基甲基醚（t-BuOMe）：穩定性高，低毒性，可替代傳統溶劑。資料來源：賓大環境健康與輻射安全辦公室2019。4.乙酸乙酯（EtOAc）：廣泛應用，低毒性，適用於多種溶解需求。資料來源：美國化學會出版物2020。5.環己烷（Cyclohexane）：低毒性，適用於非極性物質的溶解。資料來源：加州州立大學斯坦尼斯勞斯分校2018。替代溶劑選擇建議如下：若需高環境友好性，可選擇2-甲基四氫呋喃（2-MeTHF）與叔丁基甲基醚（t-BuOMe），因其毒性低且具良好生物可降解性。若考慮成本，乙酸乙酯（EtOAc）是較低成本且適用性廣的替代品。若重視溶解非極性物質的能力，環己烷（Cyclohexane）是有效選項。
注意事項

在選擇替代溶劑時，應考慮以下因素：

1.毒性與安全性：確保所選溶劑的毒性低，並遵循相關安全操作規範。

2.溶解能力：選擇能夠有效溶解目標物質的溶劑。

3.成本與可獲得性：考慮溶劑的成本和在當地市場的可獲得性。

建議在實際應用前，進行小規模測試，以確保所選溶劑的適用性和安全性。
example2.
使用者問:幫我搜尋丙烯酸丁酯的替代物
AGENT要回答:
分析邏輯

提取關鍵字：「丙烯酸丁酯」「法規」「法律規範」

呼叫工具：使用Convert_to_CID將「丙烯酸丁酯」轉換為CID號碼，然後使用SAS和Deepsurvey進行搜尋，查找相關的替代物資料。                
呼叫工具：使用SAS和Deepsurvey進行搜尋，查找相關的替代物資料。
呼叫工具：使用GraphRAG查詢「丙烯酸丁酯」的法律規範資料。

資料整理與分析：

從搜尋結果中提取替代物的名稱、類型、特性與優點。

整理成表格形式，便於比較。

風險等級評估：根據資料來源，評估替代物的安全性與環境影響。

工業用途分類：了解每種替代物的主要應用領域。

結構相似性分類：比較替代物與丙烯酸丁酯的結構相似性，評估其作為替代品的可行性。

資料來源：標註每項資料的來源，確保資訊的可靠性。

報告生成：根據上述分析，撰寫替代物研究報告。

丙烯酸丁酯替代物報告:
1.丙烯酸正丁酯	與丙烯酸丁酯結構相似，具有良好的聚合性能，適用於製造塗料與黏合劑。	PubChem2018

2.丙烯酸異丁酯	揮發性較低，適用於低氣味產品，對環境友好。	PubChem2010

3.丙烯酸乙酯	成本較低，適用於大規模生產，具有良好的溶解性能。	PubChem2013

4.丙烯酸苯乙烯	提供優異的機械性能與耐候性，適用於高性能塗料與塑料。	PubChem2015

5.丙烯酸甲基丙烯酯	具有高反應性，適用於快速固化系統，常用於UV固化塗料。	PubChem2021
替代溶劑選擇建議

1.對環境友好性要求高：丙烯酸異丁酯具有較低的揮發性和氣味，對環境影響較小。

2.成本考量：丙烯酸乙酯成本較低，適用於大規模生產。

3.性能需求：丙烯酸苯乙烯提供優異的機械性能與耐候性，適用於高性能應用。

注意事項

1.毒性與安全性：在選擇替代溶劑時，應考慮其毒性與安全性，並遵循相關安全操作規範。

2.溶解能力：選擇能夠有效溶解目標物質的溶劑。

3.成本與可獲得性：考慮溶劑的成本和在當地市場的可獲得性。

如果您有特定的應用需求或進一步的問題，請提供更多詳細信息，我將竭誠為您提供更精確的建議。"""
]

# === Chatbot 主程式 ===
app = Flask(__name__)
MAX_HISTORY_TURNS = 1
initial_history_len = len(few_shot_examples)
@app.route('/', methods=['POST', 'GET'])
def chat():
    try:
        print("正在檢查法規更新...")
        
        # cwd=確保腳本是在 Greenchem-aide 目錄下執行
        subprocess.run(
            [sys.executable, "check_and_update.py"], 
            check=True, 
            cwd=os.path.dirname(os.path.abspath(__file__))+"/check_and_update"
        )
        print("scrapers 法規更新執行完畢。")    
    except subprocess.CalledProcessError as e:
        return {"error": f"執行 check_and_update/check_and_update.py 失敗: {str(e)}"}
    except Exception as e:
        return {"error": f"check_and_update執行過程發生未知錯誤: {str(e)}"}
    cache_path=r"D:\User\Adison\desktop\GreenChem-Aide\cache_for_quick_search"
    cache_filelist=os.listdir(cache_path)
    print("\nChatbot with Few-Shot Learning is ready! Type 'exit' to quit.\n")
    print(f"initial_history_len : {initial_history_len}")
    chat_history = few_shot_examples.copy()  # 初始化對話上下文
    data_from_client = request.get_json(force=True)
    if not data_from_client:
        return jsonify({"error": "未收到 JSON 資料"}), 400
    if isinstance(data_from_client, list):
        # 確保 List 不為空，否則給空字典
        payload = data_from_client[0] if data_from_client else {}
    else:
        # 如果原本就是 Dict (物件)，直接使用
        payload = data_from_client if data_from_client else {}
    request_type = payload.get("request_type", "chatbot")#預設為 chatbot避免舊 client 沒送這個欄位直接炸掉
    if request_type == "chatbot":
        print(f"\n[Server] 收到客戶端資料: {data_from_client}")
        user_input = json.dumps(data_from_client, ensure_ascii=False)
        input_message = {"role": "user", "content": user_input}
        cache_message = data_from_client['target']
        resp = requests.get(f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{cache_message}/cids/JSON")
        try:
            resp.raise_for_status()
            data = resp.json()
            cids = data.get("IdentifierList", {}).get("CID", [])
        except Exception:
            print("Error occurred during cache CID conversion.")
        cid = cids[0]
        for filename in cache_filelist:
            if filename.endswith(f'{cid}.json'):
                file_path = os.path.join(cache_path, filename)
                if os.path.getsize(file_path) == 0: 
                    print(f"[Cache Miss] 快取檔案為空: {filename}")
                    break # 檔案為空，繼續找下一個
                #=== 避免空的內容 ===
                else:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        cached_response = json.load(f)
                    print(f"[Cache Hit] 找到快取資料: {filename}")
                    return jsonify({
                        "status": "success",
                        "response": cached_response,
                    })
            else:
                print(f"[Cache Miss] 未找到快取資料 {cache_message}。")
        chat_history.append(input_message)
        history_for_agent = chat_history.copy()
        current_history_len = len(chat_history)
        print(f"current_history_len : {current_history_len}")
            # 如果總長度超過了「few-shot 範例數」+「最大歷史輪數」
        if current_history_len > initial_history_len + MAX_HISTORY_TURNS: 
            start_index = current_history_len - MAX_HISTORY_TURNS
            # 重新構建 history_for_agent： few_shot_examples + 最新的對話輪
            history_for_agent = few_shot_examples.copy() + chat_history[start_index:]
            print(f"重新構建對話歷史以符合最大輪數限制 : {history_for_agent}")
        print("AI: ", end="", flush=True)
        final_ai_message = None
        try:
            # 使用流式處理來逐步檢查輸出
            for step in agent_executor.stream({"messages": history_for_agent}, stream_mode="values"):
                msg = step["messages"][-1]
                final_ai_message = msg  # 保存最後的 AI 訊息
                    
                # 檢查是否有 tool_calls 屬性，這表示 Agent 決定呼叫工具
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    # 輸出 Agent 決策的 JSON
                    print("\n\n--- AGENT 呼叫工具 JSON ---")
                    # 使用簡單的輸出方式來顯示工具呼叫的結構
                    for call in msg.tool_calls:
                        tool_name = call.get('name') if isinstance(call, dict) else getattr(call, 'name', 'N/A')
                        tool_args = call.get('args') if isinstance(call, dict) else getattr(call, 'args', 'N/A')
                        print(f"Tool Name: {tool_name}")
                        print(f"Tool Args: {tool_args}")
                    print("---------------------------\n")
                    
                # 正常輸出 AI 的文字內容 (包含思考邏輯或最終答案)
                if hasattr(msg, "content"):
                    content = msg.content
                    print(content, end="", flush=True)
                    ai_response_content = content
            print("\n")
            return jsonify({
                "status": "success",
                "response": ai_response_content,
                # 如果需要回傳工具呼叫細節也可以放在這
            })
        except Exception as e:
            print(f"\n[Error] {e}\n")
        chat_history.pop()  
    elif request_type == "search chemical":
        try:
            cache_message = data_from_client['target']
            resp = requests.get(f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{cache_message}/cids/JSON")
            try:
                resp.raise_for_status()
                data = resp.json()
                cids = data.get("IdentifierList", {}).get("CID", [])
            except Exception:
                print("Error occurred during cache CID conversion.")
            cid = cids[0]
            print(f"cids:{cid}")
            for filename in cache_filelist:
                print(f"現在檔案:{filename}")
                if filename.endswith(f"{cid}.json"):
                    file_path = os.path.join(cache_path, filename)
                    if os.path.getsize(file_path) == 0: 
                        print(f"[Cache Miss] 快取檔案為空: {filename}")
                        break # 檔案為空，繼續找下一個
                    #=== 避免空的內容 ===
                    else:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            cached_response = json.load(f)
                        print(f"[Cache Hit] 找到快取資料: {filename}")
                        raw_text = cached_response
                else:
                    print(f"[Cache Miss] 未找到快取資料 {cache_message}。")
                    #這邊還要新增若沒有快取資訊要回到chatbot模式
            client = OpenAI() # Automatically reads OPENAI_API_KEY
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[  # 修正 2: 必須使用 messages 格式
                    {"role": "system", "content":f"""
                        請分析以下的文本，並提取出所有提到的「化學替代品」。
        
                            請嚴格遵守以下規則：
                            1. 只回傳純 JSON 字串 (Array of Objects)。
                            2. 不要使用 Markdown 格式 (不要寫 ```json)。
                            3. JSON 格式必須包含以下欄位：
                            - "introduction": 介紹有害物質本身 (字串)(這單獨一個欄位)(在所有回傳json中最前面)
                            - "data": 替代物列表 (Array of Objects)，每個物件包含以下：
                            - "name": 化學品名稱 (字串)
                            - "info": 替代理由的簡短摘要 (字串)
                            - "doi": 資料來源或doi (字串，若兩者皆無則填 "N/A")
                            4. 回傳內容必須能被 Python 的 json.loads() 直接解析。
                            5. 所有 key 與 value 必須使用雙引號
                            6. 禁止使用單引號
                            7.若有相同替代物的資訊請合併在同一個物件中，用逗號分隔
                            範例格式如下:
                            {{
                                "introduction": "...",
                                "data": [
                                    {{
                                    "name": "1,4-二氧六烷（1,4-Dioxane）",
                                    "info": "被分析為在毒性擔憂下更安全的溶劑，適合於臨床生產的翻譯。",
                                    "doi": "DOI:10.1021/acsptsci.0c00184"
                                    }},
                                    {{
                                    "name": "乙二醇（Ethylene Glycol）",
                                    "info": "提出作為安全的替代品，用於乙二胺的合成，經濟且環境友好。",
                                    "doi": "DOI:10.1021/acsomega.4c00709"
                                    }},
                                    {{
                                    "name": "1-丁基-3-甲基咪唑碘化物（1-Butyl-3-methylimidazolium iodide）",
                                    "info": "用於丙烯酸的去污效果，解決了Dichloroethane的環境及致癌問題。",
                                    "doi": "DOI:10.1007/s44211-022-00139-x"
                                    }},
                                    {{
                                    "name": "丙烯碳酸酯、丁酸丁酯及乙基醇",
                                    "info": "替代傳統氯化溶劑，這些溶劑被建議作為更安全的可再生溶劑。",
                                    "doi": "DOI:10.15255/CABEQ.2018.1471"
                                    }}
                                ]
                            }}
                        """},{"role": "user","content": f"原始文本如下，請進行分析：\n{raw_text}"}], response_format={"type": "json_object"}
            )
            content = completion.choices[0].message.content
            parsed_json = json.loads(content)
            #=== [關鍵修正] ===
            # 不要用 {parsed_json}，直接傳入字典
            return jsonify(parsed_json) 
        except Exception as e:
            return []
    else:
        return jsonify({"error": "請回傳正確的request_type"}), 400
    
if __name__ == "__main__":
    # 啟動伺服器
    app.run(host="0.0.0.0", port=5000, debug=True) 