import hashlib, re, sys, os
import requests
from bs4 import BeautifulSoup

# Add parent directory to path to import utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.content_optimizer import optimize_content
from utils import get_session
from utils.error_handler import create_error_result

HDR = {
    "User-Agent": "regwatch/1.0 (+compliance crawler; contact: example@example.com)",
    "Accept-Language": "zh-TW,zh;q=0.9"
}

class TaiwanCSCRA:
    """台灣化學物質註冊及評估法爬蟲 """
    def __init__(self, name, url, jurisdiction, slug):
        self.name, self.url, self.jurisdiction, self.slug = name, url, jurisdiction, slug

    def fetch(self):
        try:
            session = get_session()
            r = session.get(self.url, headers=HDR, timeout=30)
            r.raise_for_status()
            html = r.text
            soup = BeautifulSoup(html, "html.parser")
        except Exception as e:
            return create_error_result(self.name, f"無法連線或抓取網頁：{e}")

        # 更精確的標題提取
        title_element = soup.select_one("h1, h2, .LawName, .law-title") or soup.find("title")
        title_text = title_element.get_text(strip=True) if title_element else self.name
        
        # 提取法規基本資訊
        law_info = self._extract_law_info(soup)
        
        # 提取完整法條內容
        full_content = self._extract_full_content(soup)
        
        # 提取結構化章節
        structured_sections = self._extract_structured_sections(soup)
        
        # 優化內容長度
        content_data = optimize_content(full_content, structured_sections)
        
        # 計算完整內容的雜湊值（使用原始內容）
        content_for_hash = full_content if full_content else soup.get_text(" ", strip=True)
        sha256 = hashlib.sha256(content_for_hash.encode("utf-8")).hexdigest()

        # Build per-section records (one JSON line per 條)
        per_section_records = []
        try:
            plain = soup.get_text("\n", strip=True)
            # Normalize full-width spaces and digits
            plain = plain.replace("\u3000", " ")
            _fw = "\uff10\uff11\uff12\uff13\uff14\uff15\uff16\uff17\uff18\uff19"  # ０１２３４５６７８９
            _hw = "0123456789"
            trans = {ord(_fw[i]): _hw[i] for i in range(10)}
            plain = plain.translate(trans)
            
            # Support Chinese numerals and '之N'
            article_pattern = r"\u7b2c\s*([\u4e00-\u9fa5\u96f6\u30070-9]+(?:\u4e4b[0-9]+)?)\s*\u689d\s*(.*?)(?=\u7b2c\s*[\u4e00-\u9fa5\u96f6\u30070-9]+(?:\u4e4b[0-9]+)?\s*\u689d|$)"
            
            def _cn_to_int(s: str) -> int:
                # Simple Chinese numerals to int (supports up to thousands)
                units = {'十':10,'百':100,'千':1000}
                digits = {'零':0,'〇':0,'一':1,'二':2,'兩':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9}
                if not s:
                    return 0
                # if contains Arabic digits, return int directly
                if any(ch.isdigit() for ch in s):
                    try:
                        return int(''.join(ch for ch in s if ch.isdigit()))
                    except Exception:
                        pass
                total = 0
                num = 0
                last_unit = 1
                for ch in s:
                    if ch in digits:
                        num = digits[ch]
                    elif ch in units:
                        unit = units[ch]
                        if num == 0:
                            num = 1
                        total += num * unit
                        num = 0
                        last_unit = unit
                    else:
                        continue
                total += num
                return total if total else num

            # Collect candidate sections first with numeric index
            candidates = []
            for m in re.finditer(article_pattern, plain, re.DOTALL):
                art_no = m.group(1)
                body = (m.group(2) or "").strip()
                first_line = body.splitlines()[0] if body else ""
                heading = first_line[:60]
                mnum = re.match(r"([\u4e00-\u9fa5\u96f6\u30070-9]+)(?:\u4e4b([0-9]+))?", art_no)
                if mnum:
                    main = mnum.group(1)
                    sub = mnum.group(2)
                    main_n = _cn_to_int(main)
                    citation = f"{main_n}-{sub}" if sub else str(main_n)
                else:
                    citation = ''.join(ch for ch in art_no if ch.isdigit()) or art_no
                # Extract primary integer for order checks (ignore subparts like -1)
                try:
                    primary_int = int(citation.split('-')[0])
                except Exception:
                    primary_int = 0
                candidates.append((primary_int, citation, heading, body))

            # Enforce sequential order: if a detected number is not strictly next (prev+1),
            # merge its content into the previous section instead of starting a new one.
            merged = []
            for idx, (pnum, cite, head, text_block) in enumerate(candidates):
                if not merged:
                    merged.append([pnum, cite, head, text_block])
                    continue
                prev_pnum, prev_cite, prev_head, prev_text = merged[-1]
                if pnum == prev_pnum + 1:
                    merged.append([pnum, cite, head, text_block])
                else:
                    # Not in sequence; append text to previous
                    sep = "\n\n" if prev_text and text_block else ""
                    merged[-1][3] = f"{prev_text}{sep}{text_block}"

            # Emit per_section_records from merged list
            for pnum, cite, head, text_block in merged:
                per_section_records.append({
                    "part": "",
                    "section_citation": cite,
                    "section_heading": "",
                    "text": text_block,
                    "length": len(text_block)
                })
        except Exception:
            per_section_records = []

        result = {
            "title": title_text,
            "version_date": law_info.get("version_date"),
            "law_code": law_info.get("law_code"),
            "category": law_info.get("category"),
            "structured_sections": structured_sections,
            "per_section_records": per_section_records,
            "excerpt": (full_content or content_for_hash)[:1000],
            "sha256": sha256,
            "notes": "Enhanced Taiwan CSCRA parser with optimized content extraction."
        }
        
        # 加入優化後的內容資料
        result.update(content_data)
        return result

    def _extract_law_info(self, soup):
        """擷取法規基本資訊"""
        info = {}
        text = soup.get_text(" ", strip=True)
        
        date_patterns = [
            r"(發布日期|修正日期|制定日期|公告日期|實施日)\D*?(\d{4}\.\d{2}\.\d{2}|\d{4}-\d{2}-\d{2}|民國\d{2,3}年\d{1,2}月\d{1,2}日)",
            r"(\d{4}\.\d{2}\.\d{2}|\d{4}-\d{2}-\d{2}|民國\d{2,3}年\d{1,2}月\d{1,2}日).{0,20}(發布|修正|制定|公告)",
        ]
        for pattern in date_patterns:
            m = re.search(pattern, text)
            if m:
                info["version_date"] = m.group(2) if len(m.groups()) >= 2 else m.group(1)
                break
        code_match = re.search(r"(法規沿革|法規類別).*?([A-Z]\d{7})", text)
        if code_match:
            info["law_code"] = code_match.group(2)
        category_match = re.search(r"法規類別\D*?(.*?)(?=所屬單位|現行法規|$)", text)
        if category_match:
            info["category"] = category_match.group(1).strip()
        return info

    def _extract_full_content(self, soup):
        """擷取條文全文"""
        content_parts = []
        
        # Find article containers
        article_containers = soup.select(".law-article, .LawArticle, .article-content")
        if article_containers:
            for container in article_containers:
                content_parts.append(container.get_text(strip=True))
        else:
            # Fallback: find main content area
            main_content = soup.select_one("#mainContent, .main-content, .law-content, .content-area")
            if main_content:
                for element in main_content.select("nav, .navigation, .breadcrumb, .menu, script, style"):
                    element.decompose()
                content_parts.append(main_content.get_text(" ", strip=True))
        
        return "\n\n".join(content_parts) if content_parts else None

    def _extract_structured_sections(self, soup):
        """擷取章節與條文（結構化）"""
        sections = {}
        text = soup.get_text(" ", strip=True)
        
        # Extract chapters
        chapter_pattern = r"第\s*([一二三四五六七八九十百千IVX]+)\s*章\s*([^\n]*)"
        chapters = re.findall(chapter_pattern, text)
        for chapter_num, chapter_title in chapters:
            sections[f"第{chapter_num}章"] = {"title": chapter_title.strip(), "articles": []}
        
        # Extract articles  
        article_pattern = r"第\s*(\d+)\s*條\s*([^條]*?)(?=第\s*\d+\s*條|$)"
        articles = re.findall(article_pattern, text, re.DOTALL)
        
        current_section = next(iter(sections)) if sections else "條文"
        if current_section == "條文":
            sections[current_section] = {"title": "法規條文", "articles": []}
            
        for num, content in articles:
            data = {"number": num, "content": content.strip()[:500]}
            sections[current_section]["articles"].append(data)
        
        return sections
