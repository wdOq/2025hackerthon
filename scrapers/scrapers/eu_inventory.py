#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EU ECHA EC Inventory scraper using Selenium for regwatch system
Falls back to local files when Azure WAF blocks access
"""
import hashlib, os, time, tempfile
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from pathlib import Path
import pandas as pd

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import NoSuchElementException
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

LIST_URL = "https://echa.europa.eu/information-on-chemicals/ec-inventory"

@dataclass
class ECInventoryRecord:
    cas_rn: str
    ec_no: str
    name_canonical: str
    formula: str
    description: str

class EUEchaSelenium:
    """EU ECHA EC Inventory scraper using Selenium with local file fallback"""
    
    def __init__(self, name: str, jurisdiction: str = "EU", slug: str = "eu_echa_selenium", 
                 max_records: int = None):
        self.name = name
        self.jurisdiction = jurisdiction
        self.slug = slug
        self.url = LIST_URL
        self.max_records = max_records
        # Local fallback directory
        self.local_dir = Path("outputs/echa_selenium")
        
    def _get_local_csv_files(self) -> List[Path]:
        """Get available local CSV files, prioritizing standard format files"""
        if not self.local_dir.exists():
            return []
        
        csv_files = []
        # Prioritize files that are likely to be in standard CSV format
        priority_files = ["graphrag_substances.csv", "graphrag_listings.csv", "graphrag_list.csv"]
        
        # Add priority files first
        for filename in priority_files:
            file_path = self.local_dir / filename
            if file_path.exists():
                csv_files.append(file_path)
        
        # Add other CSV files
        for file in self.local_dir.glob("*.csv"):
            if file.name not in priority_files:
                csv_files.append(file)
                
        return csv_files
        
    def _download_csv_selenium(self) -> Optional[str]:
        """Use Selenium to download CSV from ECHA"""
        if not SELENIUM_AVAILABLE:
            return None
            
        temp_dir = tempfile.mkdtemp()
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        prefs = {
            "download.default_directory": temp_dir,
            "download.prompt_for_download": False,
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        driver = None
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Hide automation indicators
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            driver.get(LIST_URL)
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Check if we hit Azure WAF or other blocking
            page_title = driver.title.lower()
            if "azure waf" in page_title or "access denied" in page_title or "blocked" in page_title:
                print(f"[!] Access blocked by WAF: {driver.title}")
                print("[!] Will try local files as fallback")
                return None
            
            # Close overlays
            try:
                overlay = driver.find_element(By.CSS_SELECTOR, "#legal_notice_overlay")
                if overlay.is_displayed():
                    driver.execute_script("arguments[0].style.display = 'none';", overlay)
            except NoSuchElementException:
                pass
            
            time.sleep(3)
            
            # Find and click CSV button (強制顯示/啟用，模擬人為操作，強制隱藏覆蓋層)
            import random
            try:
                # 強制隱藏所有 modal/overlay/header
                hide_js = '''
                var selectors = ['.modal', '.overlay', '.modal-header', '.yui3-widget-hd', '#legal_notice_overlay'];
                selectors.forEach(function(sel){
                  var nodes = document.querySelectorAll(sel);
                  nodes.forEach(function(n){ n.style.display='none'; n.style.visibility='hidden'; });
                });
                '''
                driver.execute_script(hide_js)
                time.sleep(random.uniform(1, 2))
                csv_button = driver.find_element(By.CSS_SELECTOR, "#_disslists_WAR_disslistsportlet_exportButtonCSV")
                # 強制顯示/啟用按鈕
                driver.execute_script("arguments[0].style.display = 'block'; arguments[0].disabled = false;", csv_button)
                time.sleep(random.uniform(1, 2))
                # 滾動到按鈕
                driver.execute_script("arguments[0].scrollIntoView();", csv_button)
                time.sleep(random.uniform(0.5, 1.5))
                # 模擬滑鼠移動
                from selenium.webdriver import ActionChains
                actions = ActionChains(driver)
                actions.move_to_element(csv_button).perform()
                time.sleep(random.uniform(0.5, 1.5))
                # 再次檢查是否可點擊
                if not csv_button.is_displayed():
                    print("[!] CSV button found but not displayed - 強制顯示後仍不可見，可能被 WAF 隱藏")
                    print("[!] Will try local files as fallback")
                    return None
                if csv_button.get_attribute('disabled'):
                    print("[!] CSV button disabled - 強制啟用後仍不可點擊，可能被 WAF 隱藏")
                    print("[!] Will try local files as fallback")
                    return None
                try:
                    csv_button.click()
                except Exception as clickerr:
                    print(f"[!] CSV button click intercepted: {clickerr}")
                    print("[!] 嘗試用 JS 直接觸發 click")
                    driver.execute_script("arguments[0].click();", csv_button)
            except NoSuchElementException:
                print("[!] CSV button not found")
                print("[!] Will try local files as fallback")
                return None
            
            # Wait for download
            for i in range(60):
                time.sleep(1)
                for file in os.listdir(temp_dir):
                    if file.endswith('.csv'):
                        return os.path.join(temp_dir, file)
            return None
                
        except Exception as e:
            print(f"[!] Selenium error: {e}")
            # Check if it's a WAF issue
            if "Azure WAF" in str(e) or "access denied" in str(e).lower():
                print("[!] ECHA website is protected by Azure WAF - blocking automated access")
            print("[!] Will try local files as fallback")
            return None
        finally:
            if driver:
                driver.quit()
    
    def _parse_csv_file(self, csv_file: str) -> List[ECInventoryRecord]:
        """Parse the downloaded CSV file"""
        try:
            # Find header row
            with open(csv_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            header_row = None
            for i, line in enumerate(lines):
                if 'CAS no.' in line and 'EC no.' in line and 'Name' in line:
                    header_row = i
                    break
            
            if header_row is None:
                df = pd.read_csv(csv_file)
            else:
                df = pd.read_csv(csv_file, skiprows=header_row, sep='\t', encoding='utf-8')
            
            df.columns = df.columns.str.strip().str.replace('"', '')
            
            # Map columns
            colmap = {}
            for c in df.columns:
                lc = c.strip().lower()
                if "name" in lc: colmap["name"] = c
                elif "ec" in lc and "no" in lc: colmap["ec_no"] = c
                elif "cas" in lc and "no" in lc: colmap["cas_no"] = c
                elif "descr" in lc: colmap["description"] = c
                elif "formula" in lc: colmap["formula"] = c
            
            records = []
            for _, row in df.iterrows():
                if pd.isna(row.get(colmap.get("name"), "")) and pd.isna(row.get(colmap.get("cas_no"), "")):
                    continue
                
                if self.max_records and len(records) >= self.max_records:
                    break
                    
                records.append(ECInventoryRecord(
                    cas_rn=str(row.get(colmap.get("cas_no", ""), "")) if not pd.isna(row.get(colmap.get("cas_no", ""))) else "",
                    ec_no=str(row.get(colmap.get("ec_no", ""), "")) if not pd.isna(row.get(colmap.get("ec_no", ""))) else "",
                    name_canonical=str(row.get(colmap.get("name", ""), "")) if not pd.isna(row.get(colmap.get("name", ""))) else "",
                    description=str(row.get(colmap.get("description", ""), "")) if not pd.isna(row.get(colmap.get("description", ""))) else "",
                    formula=str(row.get(colmap.get("formula", ""), "")) if not pd.isna(row.get(colmap.get("formula", ""))) else "",
                ))
            
            return records
            
        except Exception as e:
            print(f"[!] Error parsing CSV: {e}")
            return []
    
    def fetch(self) -> Dict:
        """Main fetch method for regwatch integration"""
        try:
            csv_file = self._download_csv_selenium()
            records = []
            source_info = ""
            
            if csv_file:
                # Successfully downloaded from website
                records = self._parse_csv_file(csv_file)
                source_info = "Downloaded from ECHA website"
                # Cleanup
                try:
                    os.remove(csv_file)
                    os.rmdir(os.path.dirname(csv_file))
                except:
                    pass
            else:
                # Fallback to local files
                print("[!] Trying local files as fallback...")
                local_files = self._get_local_csv_files()
                
                if local_files:
                    for local_file in local_files:
                        print(f"[*] Trying local file: {local_file.name}")
                        try:
                            records = self._parse_csv_file(str(local_file))
                            if records:
                                source_info = f"Local file: {local_file.name} (modified: {datetime.fromtimestamp(local_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M')})"
                                break
                        except Exception as e:
                            print(f"[!] Error reading {local_file.name}: {e}")
                            continue
                else:
                    print("[!] No local files found in outputs/echa_selenium/")
            
            if not records:
                return self._create_empty_result("No data retrieved from website or local files")
            
            per_section_records = [asdict(record) for record in records]
            full_content = "\n".join([f"{r.cas_rn}|{r.ec_no}|{r.name_canonical}" for r in records])
            sha256 = hashlib.sha256(full_content.encode("utf-8")).hexdigest()
            
            return {
                "title": self.name,
                "version_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "regulation_number": "EC Inventory",
                "category": "chemical_inventory", 
                "notes": f"ECHA EC Inventory - {len(records)} substances ({source_info})",
                "sha256": sha256,
                "content_length": len(full_content),
                "excerpt": full_content[:1000],
                "structured_sections": [{"section": "EC Inventory", "count": len(records)}],
                "per_section_records": per_section_records,
                "full_content": full_content
            }
            
        except Exception as e:
            return self._create_empty_result(f"Error: {e}")
    
    def _create_empty_result(self, reason: str) -> Dict:
        """Create empty result for error cases"""
        return {
            "title": self.name,
            "version_date": None,
            "regulation_number": "EC Inventory",
            "notes": f"ECHA EC Inventory - 無法獲取：{reason}",
            "sha256": hashlib.sha256("".encode()).hexdigest(),
            "content_length": 0,
            "excerpt": "",
            "structured_sections": {},
            "per_section_records": [],
            "full_content": ""
        }