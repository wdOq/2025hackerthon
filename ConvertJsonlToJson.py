import os
import json
import re
from datetime import datetime


INVALID_MARKER = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def file_contains_invalid_data(file_path):
    """檢查 json / jsonl 是否包含無效標記"""
    with open(file_path, "r", encoding="utf-8") as f:
        if file_path.endswith(".jsonl"):
            for line in f:
                if INVALID_MARKER in line:
                    return True
        else:
            content = json.load(f)
            return INVALID_MARKER in json.dumps(content, ensure_ascii=False)
    return False


def merge_latest_json_files(input_dir):
    """
    對每個 slug：
    - 若最新日期檔案無效
    - 則回退到前一個日期（檔名相同）
    """

    date_pattern = re.compile(r"^(\d{8})_(.+)$")
    slug_map = {}

    # === 1️⃣ 建立 slug -> [(date, filename)] ===
    for filename in os.listdir(input_dir):
        if not filename.endswith((".json", ".jsonl")):
            continue

        match = date_pattern.match(filename)
        if not match:
            continue

        date_str, slug = match.groups()

        try:
            file_date = datetime.strptime(date_str, "%Y%m%d")
        except ValueError:
            continue

        slug_map.setdefault(slug, []).append((file_date, filename))

    if not slug_map:
        raise RuntimeError("找不到符合 YYYYMMDD_slug.json 的檔案")

    merged_data = []
    files_used = []

    # === 2️⃣ 每個 slug 單獨回退 ===
    for slug, entries in slug_map.items():
        # 日期由新到舊
        entries.sort(reverse=True)

        selected_file = None

        for file_date, filename in entries:
            file_path = os.path.join(input_dir, filename)

            if file_contains_invalid_data(file_path):
                print(f"{filename} 無有效資料，回退上一日期")
                continue

            selected_file = filename
            break

        if not selected_file:
            print(f"slug {slug} 找不到任何有效資料，略過")
            continue

        files_used.append(selected_file)
        file_path = os.path.join(input_dir, selected_file)

        with open(file_path, "r", encoding="utf-8") as f:
            if selected_file.endswith(".jsonl"):
                for line in f:
                    line = line.strip()
                    if line:
                        merged_data.append(json.loads(line))
            else:
                content = json.load(f)
                if isinstance(content, list):
                    merged_data.extend(content)
                else:
                    merged_data.append(content)

    if not merged_data:
        raise RuntimeError("沒有任何可用資料")

    return merged_data, files_used

if __name__ == "__main__":
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    INPUT_DIR = os.path.join(BASE_DIR, "check_and_update", "outputs", "by_slug")
    OUTPUT_DIR = os.path.join(BASE_DIR, "ragtest", "input")
    merged_data, files_used = merge_latest_json_files(INPUT_DIR)
    print("來源檔案：")
    for f in files_used:
        print("  -", f)
    OUTPUT_FILE = os.path.join(OUTPUT_DIR,"converted.json")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=2)

    print(f"合併完成，輸出至：{OUTPUT_FILE}")

