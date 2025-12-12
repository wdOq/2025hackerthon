import os
import json

# 1. 設定你的 txt 檔案資料夾路徑
txt_folder = r"D:\User\Adison\desktop\result_of_agent\1,2-二氯乙烷(Ethylene Dichloride)"
output_json = r"D:\User\Adison\desktop\result_of_agent\1,2-二氯乙烷(Ethylene Dichloride)\combined11.json"

# 2. 取得所有 txt 檔案
txt_files = [f for f in os.listdir(txt_folder) if f.endswith(".txt")]

all_data = []

# 3. 逐個讀取 txt 檔並加入 list
for file_name in txt_files:
    file_path = os.path.join(txt_folder, file_name)
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read().strip()  # 去掉首尾空白
        all_data.append({"text": content})

# 4. 將結果寫入 JSON 檔
with open(output_json, "w", encoding="utf-8") as f:
    json.dump(all_data, f, ensure_ascii=False, indent=2)

print(f"合併完成，共 {len(all_data)} 個檔案，輸出到 {output_json}")
