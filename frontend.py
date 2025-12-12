import requests
import json

# 目標 URL (如果是在本機跑，通常是 localhost:5000)
url = "https://jerlene-transmeridional-unrecognisably.ngrok-free.dev"

# 模擬您原本 input_data.json 裡的內容
payload = {
 "query": "what are some chemically similar substitutes for Butyl D-glucoside along with detailed legal regulations for every country?",
 "target": "Butyl D-glucoside",
 "substitution": "",
 "market": "global",
 "industry": "manufacturing",
}

print(f"正在傳送資料到 {url} ...")

try:
 # 發送 POST 請求
 response = requests.post(url, json=payload)
 # 檢查結果
 if response.status_code == 200:
  result = response.json()
  print("\n=== 伺服器回應成功 ===")
  print("AI 回覆內容:", result.get("response"))
 else:
  print(f"\n=== 伺服器錯誤 {response.status_code} ===")
  print(response.text)
except Exception as e:
 print(f"連線失敗: {e}")