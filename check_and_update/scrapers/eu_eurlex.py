import hashlib, re, time, sys, os
from bs4 import BeautifulSoup

# Add parent directory to path to import utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.content_optimizer import optimize_content
from utils.error_handler import create_error_result
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False


class EUEurLex:
    def _process_content(self, soup, source_type):
        
        try:
            # 標題提取
            title_element = (soup.find("h1") or 
                            soup.select_one(".document-title, .title") or 
                            soup.find("title"))
            title_text = title_element.get_text(strip=True) if title_element else self.name

            # 法規基本資訊
            law_info = self._extract_law_info(soup)
            # 完整法規內容
            full_content = self._extract_full_content(soup)
            # 結構化章節
            structured_sections, per_section_records = self._extract_structured_sections(soup)
            # 優化內容
            optimized_result = optimize_content(full_content, structured_sections)
            # 雜湊值
            content_for_hash = full_content if full_content else soup.get_text(" ", strip=True)
            sha256 = hashlib.sha256(content_for_hash.encode("utf-8")).hexdigest()

            return {
                "title": title_text,
                "version_date": law_info.get("version_date"),
                "regulation_number": law_info.get("regulation_number"),
                "document_type": law_info.get("document_type"),
                "content": optimized_result["full_content"],
                "full_content": optimized_result["full_content"],
                "sections": structured_sections,
                "structured_sections": structured_sections,
                "per_section_records": per_section_records,
                "content_length": optimized_result["content_length"],
                "excerpt": optimized_result.get("content_summary", "")[:1000] or (optimized_result["full_content"] or content_for_hash)[:1000],
                "sha256": sha256,
                "notes": f"{'Selenium website extraction' if source_type == 'Selenium網站抓取' else 'Local HTML file parser'} with full content extraction; {'content truncated' if optimized_result.get('is_truncated') else 'full content'}."
            }
        except Exception as e:
            
            return {}

    def _extract_law_info(self, soup):
        info = {}
        text = soup.get_text(" ", strip=True)
        date_patterns = [
            r"(Date of document|Data del documento|Dokumentdatum|Date|Datum)\D{0,20}(\d{1,2}\s\w+\s\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}[\/\.\-]\d{1,2}[\/\.\-]\d{4})",
            r"(\d{1,2}\s\w+\s\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}[\/\.\-]\d{1,2}[\/\.\-]\d{4}).{0,30}(document|published)",
        ]
        for pattern in date_patterns:
            date_match = re.search(pattern, text, flags=re.I)
            if date_match:
                info["version_date"] = date_match.group(2) if len(date_match.groups()) >= 2 else date_match.group(1)
                break
        regulation_patterns = [
            r"Regulation\s*\(EC\)\s*No\s*(\d+/\d+)",
            r"Directive\s*(\d+/\d+/EC)",
            r"Decision\s*(\d+/\d+/EU)",
        ]
        for pattern in regulation_patterns:
            reg_match = re.search(pattern, text, flags=re.I)
            if reg_match:
                info["regulation_number"] = reg_match.group(1)
                info["document_type"] = reg_match.group(0).split()[0]
                break
        return info

    def _extract_full_content(self, soup):
        content_parts = []
        content_selectors = [
            ".eli-main-content",
            "#document-content",
            ".legal-content",
            ".document-content",
            "#MainContent",
            ".content-wrapper",
            "main",
            ".text-content",
            "#content"
        ]
        main_content = None
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        if not main_content:
            reach_titles = soup.find_all(text=re.compile(r"REACH|1907/2006", re.I))
            if reach_titles:
                for title in reach_titles:
                    parent = title.parent
                    if parent:
                        while parent.parent and parent.parent.name not in ['html', 'body']:
                            parent = parent.parent
                        main_content = parent
                        break
        if main_content:
            for unwanted in main_content.select("script, style, .menu, .navigation, .breadcrumb, footer"):
                unwanted.decompose()
            annexes = main_content.select("[class*='annex'], [id*='annex']")
            if annexes:
                for annex in annexes:
                    content_parts.append(annex.get_text(" ", strip=True))
            articles = main_content.select("div[class*='article'], div[class*='Article'], .article")
            if articles:
                for article in articles:
                    content_parts.append(article.get_text(" ", strip=True))
            if not content_parts:
                content_parts.append(main_content.get_text(" ", strip=True))
        if not content_parts:
            body = soup.find("body")
            if body:
                for element in body.select("header, footer, nav, .menu, .navigation, script, style, .sidebar"):
                    element.decompose()
                content_text = body.get_text(" ", strip=True)
                if content_text:
                    content_parts.append(content_text)
        full_content = "\n\n".join(content_parts) if content_parts else ""
        return full_content

    def _extract_structured_sections(self, soup):
        import datetime
        sections = {}
        per_section_records = []
        annex_title_elements = soup.find_all('p', class_='title-annex-1')
        def roman_to_int(roman):
            values = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
            if not roman or not isinstance(roman, str):
                return 0
            roman = roman.upper()
            result = 0
            prev_value = 0
            for char in reversed(roman):
                value = values.get(char, 0)
                if value < prev_value:
                    result -= value
                else:
                    result += value
                prev_value = value
            return result
        annexes = []
        for title_elem in annex_title_elements:
            title_text = title_elem.get_text(strip=True)
            annex_match = re.match(r'ANNEX\s+([IVX]+)', title_text, re.IGNORECASE)
            if not annex_match:
                continue
            annex_num = annex_match.group(1)
            annex_key = f"ANNEX {annex_num}"
            full_title = title_text
            next_elem = title_elem.next_sibling
            while next_elem:
                if hasattr(next_elem, 'get_text'):
                    next_text = next_elem.get_text(strip=True)
                    if next_text and not next_text.startswith('ANNEX'):
                        if len(next_text) < 200 and not next_text.endswith('.'):
                            full_title += " " + next_text
                        break
                elif isinstance(next_elem, str) and next_elem.strip():
                    break
                next_elem = next_elem.next_sibling
            annexes.append({
                'annex_num': annex_num,
                'annex_key': annex_key,
                'title': full_title,
                'title_element': title_elem,
                'sort_order': roman_to_int(annex_num)
            })
        annexes.sort(key=lambda x: x['sort_order'])
        for i, annex_info in enumerate(annexes):
            annex_num = annex_info['annex_num']
            annex_key = annex_info['annex_key']
            full_title = annex_info['title']
            title_elem = annex_info['title_element']
            content_parts = []
            current_elem = title_elem
            while current_elem:
                current_elem = current_elem.next_sibling
                if not current_elem:
                    break
                if (hasattr(current_elem, 'get') and 
                    current_elem.get('class') == ['title-annex-1']):
                    break
                if hasattr(current_elem, 'get_text'):
                    elem_text = current_elem.get_text(strip=True)
                    if (elem_text.startswith('TITLE ') or 
                        elem_text.startswith('CHAPTER ') or
                        elem_text.startswith('Part ')):
                        break
                if hasattr(current_elem, 'get_text'):
                    elem_text = current_elem.get_text(" ", strip=True).replace('\n', ' ').replace('\r', ' ')
                    elem_text = ' '.join(elem_text.split())
                    if elem_text:
                        content_parts.append(elem_text)
                elif isinstance(current_elem, str) and current_elem.strip():
                    clean_text = current_elem.strip().replace('\n', ' ').replace('\r', ' ')
                    clean_text = ' '.join(clean_text.split())
                    content_parts.append(clean_text)
            annex_content = " ".join(content_parts)
            if len(annex_content) < 50:
                continue
            full_annex_text = f"{full_title} {annex_content}"
            per_section_records.append({
                "part": annex_key,
                "section_citation": annex_key,
                "section_heading": full_title,
                "text": full_annex_text,
                "length": len(full_annex_text),
                "fetched_at_taipei": datetime.datetime.now().isoformat()
            })
            sections[annex_key] = {
                "title": full_title,
                "sections": [{
                    "heading": full_title,
                    "content": full_annex_text
                }]
            }
        return sections, per_section_records

    def __init__(self, name, url, jurisdiction, slug):
        self.name, self.url, self.jurisdiction, self.slug = name, url, jurisdiction, slug
        self.backup_url = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32006R1907"

    def fetch(self):
        """Selenium 抓取 EUR-Lex 最新 EN HTML 連結與內容，並自動解析結構化結果"""
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium 未安裝，請安裝 selenium, webdriver_manager")
        
        html, download_url, latest_date = self._fetch_with_selenium()
        
        if not html or len(html) < 10000:
            print("[Selenium] 抓取內容太短或失敗")
            result = create_error_result(
                self.name,
                "Selenium 抓取失敗或內容不足"
            )
            result["download_url"] = download_url
            result["latest_date"] = latest_date
            return result
        # 用 BeautifulSoup 解析 html 並結構化
        soup = BeautifulSoup(html, "html.parser")
        
        result = self._process_content(soup, "Selenium網站抓取")
        import json
        
        # 補充 download_url, latest_date
        result["download_url"] = download_url
        result["latest_date"] = latest_date
        return result

    def _fetch_with_selenium(self):
        """Selenium 自動抓取 EUR-Lex 主頁最新日期，取得 EN HTML 下載連結"""
        driver = None
        try:
            driver = self._setup_driver()
            url = self.backup_url
            print(f"[Selenium] 開啟主頁: {url}")
            driver.get(url)
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(5)



            # 直接取得最新日期的 <a> 元素

            try:
                latest_date_a = driver.find_element(By.CSS_SELECTOR, "nav.consLegNav ul li a")
                latest_date = latest_date_a.text.strip()
                latest_href = latest_date_a.get_attribute("href")
                print(f"[Selenium] 偵測到最新日期: {latest_date}, 連結: {latest_href}")

                # 直接跳轉到最新日期的法規頁面
                driver.get(latest_href)
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(3)

                # 找到 EN HTML 下載連結
                en_html_link = driver.find_element(By.XPATH, "//a[contains(@title, 'HTML') and contains(@href, 'EN')]")
                download_url = en_html_link.get_attribute("href")
                print(f"[Selenium] 最新 EN HTML 下載連結: {download_url}")
            except Exception as e:
                print(f"[Selenium] 取得 EN HTML 連結失敗: {e}")
                latest_date = None
                download_url = None

            html = driver.page_source
            print(f"[Selenium] 成功獲取頁面內容，大小: {len(html)} 字符")
            return html, download_url, latest_date
        finally:
            if driver:
                driver.quit()

    def _setup_driver(self):
        """Configure and start Chrome browser for Selenium"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
