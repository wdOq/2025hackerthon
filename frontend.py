import requests
import json

# 目標 URL (如果是在本機跑，通常是 localhost:5000)
url = "https://jerlene-transmeridional-unrecognisably.ngrok-free.dev"

# 模擬您原本 input_data.json 裡的內容
payload = {
 "request_type": "search chemical",
 "query": "what are some chemically similar substitutes for butyl acrylate along with detailed legal regulations for every country?",
 "target": "butyl acrylate",
 "substitution": "",
 "market": "US EPA (TSCA)",
 "industry": "",
}

print(f"正在傳送資料到 {url} ...")

print(f"正在傳送資料到 {url} ...")

try:
    # 發送 POST 請求
    response = requests.post(url, json=payload)

    # 檢查 HTTP 狀態碼
    if response.status_code == 200:
        print("\n=== 伺服器回應成功 ===")
        
        # 取得原始 JSON 資料
        result = response.json()
        
        # 使用 json.dumps 將資料排版漂亮印出 (indent=4)
        # ensure_ascii=False 確保中文能正常顯示，不會變成亂碼
        print(json.dumps(result, indent=4, ensure_ascii=False))
        
    else:
        print(f"\n=== 伺服器錯誤 (狀態碼: {response.status_code}) ===")
        print(response.text)

except Exception as e:
    print(f"連線發生錯誤: {e}")