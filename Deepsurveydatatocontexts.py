import json
import pprint # 僅為了讓輸出更美觀

def convert_json_to_list(file_name):
    """
    讀取 JSON 檔案並將其轉換為指定的列表格式。
    
    格式為： [['title1'], ['reasoning1_sent1', 'reasoning1_sent2'], ['title2'], ...]
    """
    
    output_list = []
    
    try:
        # 讀取 JSON 檔案
        with open(file_name, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 遍歷 JSON 中的每一個物件
        for item in data:
            # 1. 將 "title" 作為一個單獨的列表項添加
            if 'title' in item:
                output_list.append([item['title']])
            
            # 2. 將 "reasoning" 按句子拆分，並作為一個列表添加
            if 'reasoning' in item:
                # 使用句號 '.' 作為分隔符
                # 過濾掉拆分後可能產生的空字串
                # .strip() 用於去除每句話前後的空白
                sentences = [s.strip() for s in item['reasoning'].split('.') if s.strip()]
                
                # 將句號加回去，使句子看起來更完整
                sentences_with_period = [s + '.' for s in sentences]
                
                # 只有當 reasoning 欄位有內容時才添加
                if sentences_with_period:
                    output_list.append(sentences_with_period)
                    
    except FileNotFoundError:
        print(f"錯誤：找不到檔案 '{file_name}'")
        return None
    except json.JSONDecodeError:
        print(f"錯誤：檔案 '{file_name}' 不是有效的 JSON 格式。")
        return None
    except Exception as e:
        print(f"發生預期外的錯誤：{e}")
        return None

    return output_list

# --- 執行範例 ---

# 假設您的 JSON 檔案名稱為 '20251110_11.json'
# 請確保這個 .json 檔案與 .py 程式在同一個資料夾中
# 否則請提供完整路徑
file_name = r"D:\User\Adison\desktop\GreenChem-Aide\37chemicals\20251110_11.json" 
result = convert_json_to_list(file_name)

if result:
    print("轉換結果：")
    # 使用 pprint 讓長列表的輸出更容易閱讀
    pprint.pprint(result)
    