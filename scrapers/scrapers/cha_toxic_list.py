from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import re
import hashlib

class CHAToxicListScraper:
    def __init__(self, name="環境部化學物質管理署毒性及關注化學物質清單", 
                 url="https://www.cha.gov.tw/sp-toch-list-1.html", 
                 jurisdiction="TW", slug="tw_cha_toxic_list"):
        self.name = name
        self.url = url
        self.jurisdiction = jurisdiction
        self.slug = slug
        
        # Selenium 設定
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        self.driver = None

    def fetch(self):
        """主要抓取方法"""
        try:
            self.driver = webdriver.Chrome(options=self._get_chrome_options())
            
            # 載入網頁
            print(f"正在載入網頁: {self.url}")
            self.driver.get(self.url)
            
            # 等待網頁載入
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(3)
            
            # 抓取所有化學物質條目
            records = self._extract_chemical_records()
            
            # 產生內容摘要
            full_content = self._generate_full_content(records)
            sha256 = hashlib.sha256(full_content.encode("utf-8")).hexdigest()
            
            return {
                "title": self.name,
                "content": full_content,
                "full_content": full_content,
                "per_section_records": records,
                "content_length": len(full_content),
                "excerpt": full_content[:1000],
                "sha256": sha256,
                "total_chemicals": len(records),
                "notes": f"抓取了 {len(records)} 筆毒性及關注化學物質資料"
            }
            
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
            
            # 處理所有化學物質
            for i, (link_text, link_url) in enumerate(link_data):
                try:
                    # 先解析基本資訊
                    basic_record = self._parse_chemical_info(link_text, link_url)
                    
                    if basic_record:
                        # 抓取詳細資訊
                        detailed_info = self._extract_chemical_details(link_url)
                        
                        if detailed_info:
                            # 合併基本資訊和詳細資訊
                            basic_record.update(detailed_info)
                        
                        records.append(basic_record)
                        
                    # 每處理50筆顯示進度
                    if (i + 1) % 50 == 0:
                        print(f"已處理 {i + 1}/{len(link_data)} 筆資料")
                        
                except Exception as e:
                    print(f"處理第 {i + 1} 筆資料時發生錯誤: {e}")
                    continue
                    
        except Exception as e:
            print(f"抓取化學物質記錄時發生錯誤: {e}")
            
        return records

    def _extract_chemical_details(self, link_url):
        """抓取化學物質詳細資訊"""
        try:
            print(f"抓取詳細資訊: {link_url}")
            self.driver.get(link_url)
            time.sleep(3)  # 等待頁面載入
            
            # 初始化詳細資料
            details = {
                "control_measures": "",
                "usage_description": "",
                "announcement_date": ""
            }
            
            # 抓取表格資料
            try:
                pass
            except Exception as e:
                print(f"抓取表格資料時發生錯誤: {e}")
            
            # 抓取管制事項和用途說明
            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                
                # 抓取管制事項（尋找較長的包含「禁止」等關鍵字的句子）
                lines = page_text.split('\n')
                for line in lines:
                    line = line.strip()
                    if any(keyword in line for keyword in ["禁止", "允許", "准繼續使用", "不在此限"]) and len(line) > 30:
                        details["control_measures"] = line
                        break
                
                # 抓取用途說明
                if "用途：" in page_text:
                    usage_start = page_text.find("用途：")
                    usage_end = page_text.find('\n', usage_start)
                    if usage_end == -1:
                        usage_end = usage_start + 200
                    details["usage_description"] = page_text[usage_start:usage_end].strip()
                
                # 抓取公告日期
                date_match = re.search(r'公告日期：(\d{2}-\d{2}-\d{2})', page_text)
                if date_match:
                    details["announcement_date"] = date_match.group(1)
                    
            except Exception as e:
                print(f"抓取文字內容時發生錯誤: {e}")
            
            return details
            
        except Exception as e:
            print(f"抓取詳細資訊時發生錯誤: {e}")
            return {}

    def _parse_chemical_info(self, link_text, url):
        """解析化學物質資訊"""
        try:
            # 按行分割文字
            lines = [line.strip() for line in link_text.split('\n') if line.strip()]
            
            # 初始化欄位
            toxicity_level = ""
            cas_number = ""
            chinese_name = ""
            english_name = ""
            
            if len(lines) >= 2:
                # 第0行：列管編號001-01
                # 第1行：可能是毒物層級第一部分、"關注"或其他
                # 第2行：可能是毒物層級第二部分或CAS號
                
                # 處理毒物層級
                if len(lines) >= 3:
                    # 檢查第1、2行是否都是數字（如"1", "2"）
                    if lines[1].isdigit() and lines[2].isdigit():
                        toxicity_level = f"{lines[1]}、{lines[2]}"
                        # CAS號從第3行開始
                        cas_start_index = 3
                    elif lines[1].isdigit():
                        # 只有第1行是數字
                        toxicity_level = lines[1]
                        cas_start_index = 2
                    elif "關注" in lines[1]:
                        # 關注化學物質
                        toxicity_level = "關注"
                        cas_start_index = 2
                    else:
                        # 其他情況，可能第1行就是CAS號
                        cas_start_index = 1
                elif len(lines) >= 2:
                    # 只有2行的情況
                    if lines[1].isdigit():
                        toxicity_level = lines[1]
                        cas_start_index = 2
                    elif "關注" in lines[1]:
                        toxicity_level = "關注"
                        cas_start_index = 2
                    else:
                        cas_start_index = 1
                
                # 解析剩餘欄位
                remaining_lines = lines[cas_start_index:] if cas_start_index < len(lines) else []
                
                if len(remaining_lines) >= 1:
                    cas_number = remaining_lines[0]
                if len(remaining_lines) >= 2:
                    chinese_name = remaining_lines[1]
                if len(remaining_lines) >= 3:
                    english_name = remaining_lines[2]
            
            # 如果所有欄位都是空的，返回None跳過這個記錄
            if not any([toxicity_level, cas_number, chinese_name, english_name]):
                return None
            
            return {
                "toxicity_level": toxicity_level,
                "cas_number": cas_number,
                "chinese_name": chinese_name,
                "english_name": english_name
            }
                
        except Exception as e:
            print(f"解析化學物質資訊時發生錯誤: {e}")
            print(f"原始文字: {link_text}")
            return None

    def _generate_full_content(self, records):
        """產生完整內容摘要"""
        content_parts = []
        content_parts.append(f"# {self.name}")
        content_parts.append(f"資料來源: {self.url}")
        content_parts.append(f"總計: {len(records)} 筆化學物質資料")
        content_parts.append("")
        
        for record in records:
            content_parts.append(f"## {record.get('section_heading', 'N/A')}")
            content_parts.append(f"列管編號: {record.get('control_number', 'N/A')}")
            content_parts.append(f"分類: {record.get('category', 'N/A')}")
            if record.get('cas_number'):
                content_parts.append(f"CAS號: {record.get('cas_number')}")
            content_parts.append("")
        
        return "\n".join(content_parts)


if __name__ == "__main__":
    scraper = CHAToxicListScraper()
    try:
        result = scraper.fetch()
        
        # 儲存結果
        import os
        os.makedirs("outputs", exist_ok=True)
        
        with open("outputs/cha_toxic_list.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f" 成功抓取 {result['total_chemicals']} 筆毒性化學物質資料")
        print(f" 已儲存至 outputs/cha_toxic_list.json")
        
    except Exception as e:
        print(f" 執行失敗: {e}")
