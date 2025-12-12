import json

input_file = r"D:\User\Adison\download\by_slug\by_slug\regulation.json"    # 原始 JSONL
output_file = r"D:\User\Adison\download"    # 轉換後的 JSON

data = []
with open(input_file, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            data.append(json.loads(line))  # 將每行 JSON 解析成 dict

# 將 list 寫入 JSON
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"✅ 已成功轉換 {input_file} → {output_file}")
