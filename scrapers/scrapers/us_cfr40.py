import hashlib
import json
import re
import time
import requests
from pathlib import Path
from bs4 import BeautifulSoup
from utils.content_optimizer import optimize_content

# 嘗試導入 Selenium 依賴
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import NoSuchElementException, TimeoutException
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

class USCFRTitle40:
    def __init__(self, name, url, jurisdiction, slug):
        self.name = name
        self.url = url
        self.jurisdiction = jurisdiction
        self.slug = slug
        self.base_url = "https://www.govinfo.gov/app/collection/cfr/2024/title40"
        self.govinfo_base_url = "https://www.govinfo.gov/content/pkg"
        
    def fetch(self):
        """
        從 GovInfo.gov 下載 CFR Title 40 的 Volume 1-37 XML 資料
        """
        if SELENIUM_AVAILABLE:
            try:
                result = self._fetch_from_govinfo()
                if result:
                    return result
                else:
                    print(" 抓取失敗")
            except Exception as e:
                print(f" 抓取錯誤: {e}")
        else:
            print(" Selenium 未安裝")
        
        return self._create_error_result("無法抓取 CFR Title 40 法規")
    
    def _fetch_from_govinfo(self):
        """用最新年份組合 XML 下載連結，失敗再往前一年遞減直到成功"""
        from datetime import datetime
        print(" 開始從 GovInfo.gov 下載 CFR Title 40...")
        all_volumes_data = []
        successful_downloads = 0
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        current_year = datetime.now().year
        min_year = 2010
        found_year = None
        for try_year in range(current_year, min_year - 1, -1):
            print(f"嘗試年份: {try_year}")
            # 先測試第一卷是否存在且為 XML
            test_url = f"{self.govinfo_base_url}/CFR-{try_year}-title40-vol1/xml/CFR-{try_year}-title40-vol1.xml"
            try:
                resp = requests.get(test_url, headers=headers, timeout=15)
                if resp.status_code == 200 and resp.content.strip().startswith(b'<?xml'):
                    found_year = try_year
                    print(f"找到可用年份: {found_year}")
                    break
                else:
                    print(f"  {try_year} 年卷1不存在或不是 XML (HTTP {resp.status_code})")
            except Exception as e:
                print(f"  {try_year} 年測試錯誤: {e}")
        if not found_year:
            print("找不到任何可用年份！")
            return None
        # 下載 Volume 1-37
        for vol_num in range(1, 38):
            try:
                print(f" 下載 Volume {vol_num}...")
                xml_url = f"{self.govinfo_base_url}/CFR-{found_year}-title40-vol{vol_num}/xml/CFR-{found_year}-title40-vol{vol_num}.xml"
                response = requests.get(xml_url, headers=headers, timeout=30)
                if response.status_code == 200 and response.content.strip().startswith(b'<?xml'):
                    volume_data = self._parse_xml_volume(response.content, vol_num)
                    if volume_data:
                        all_volumes_data.extend(volume_data)
                        successful_downloads += 1
                        print(f"   Volume {vol_num} 下載成功")
                    else:
                        print(f"   Volume {vol_num} 解析失敗")
                elif response.status_code == 404:
                    print(f"   Volume {vol_num} 不存在 (404)")
                else:
                    print(f"   Volume {vol_num} 下載失敗: HTTP {response.status_code}")
            except Exception as e:
                print(f"   Volume {vol_num} 錯誤: {e}")
                continue
        if successful_downloads > 0:
            print(f" 成功下載 {successful_downloads} 個 Volume（年份: {found_year}）")
            return self._process_volumes_data(all_volumes_data, successful_downloads)
        else:
            print(" 沒有成功下載任何 Volume")
            return None
    def _parse_xml_volume(self, xml_content, vol_num):
        """解析單個 Volume 的 XML 內容，失敗時印出部分原始內容方便 debug"""
        try:
            from xml.etree import ElementTree as ET
            # 解析 XML
            root = ET.fromstring(xml_content)
            volume_data = []
            # 優先查找 SECTION 元素 
            for section in root.iter('SECTION'):
                section_data = self._extract_cfr_section(section, vol_num)
                if section_data:
                    volume_data.append(section_data)
            # 如果沒有找到 SECTION，查找 PART 元素
            if not volume_data:
                for part in root.iter('PART'):
                    part_data = self._extract_cfr_part(part, vol_num)
                    if part_data:
                        volume_data.append(part_data)
            # 如果還是沒有，查找 SUBPART 元素
            if not volume_data:
                for subpart in root.iter('SUBPART'):
                    subpart_data = self._extract_cfr_subpart(subpart, vol_num)
                    if subpart_data:
                        volume_data.append(subpart_data)
            # 最後回退到通用元素查找
            if not volume_data:
                for elem in root.iter():
                    if elem.text and len(elem.text.strip()) > 50:
                        volume_data.append({
                            'volume': vol_num,
                            'tag': elem.tag,
                            'text': elem.text.strip(),
                            'attrib': dict(elem.attrib)
                        })
            if not volume_data:
                print(f" Volume {vol_num} 解析失敗，原始 XML 前 500 字：\n{xml_content[:500]!r}")
                try:
                    from xml.etree import ElementTree as ET
                    root = ET.fromstring(xml_content)
                    print(f" Volume {vol_num} 根標籤: {root.tag}, 子元素數量: {len(list(root))}")
                except Exception:
                    pass
            return volume_data
        except Exception as e:
            print(f" XML 解析錯誤 (Volume {vol_num}): {e}\n原始 XML 前 500 字：\n{xml_content[:500]!r}")
            return None
    
    def _extract_cfr_section(self, section_elem, vol_num):
        """提取 CFR SECTION 元素"""
        try:
            # 獲取章節編號
            sectno_elem = section_elem.find('SECTNO')
            section_number = sectno_elem.text.strip() if sectno_elem is not None and sectno_elem.text else ""
            
            # 獲取主題
            subject_elem = section_elem.find('SUBJECT')
            subject = subject_elem.text.strip() if subject_elem is not None and subject_elem.text else ""
            
            # 獲取所有段落內容
            content_parts = []
            
            # 收集所有 P (段落) 元素
            for p_elem in section_elem.findall('P'):
                if p_elem.text:
                    content_parts.append(p_elem.text.strip())
                
                # 也收集 P 元素內的子元素文字
                for child in p_elem:
                    if child.text:
                        content_parts.append(child.text.strip())
                    if child.tail:
                        content_parts.append(child.tail.strip())
            
            # 組合完整內容
            full_text = f"{subject}\n\n" + "\n\n".join(content_parts)
            full_text = full_text.strip()
            
            if len(full_text) < 10:
                return None
            
            return {
                'volume': vol_num,
                'section_id': section_number,
                'element_type': 'SECTION',
                'tag': 'SECTION',
                'heading': f"{section_number} {subject}" if section_number and subject else (subject or section_number),
                'subject': subject,
                'full_text': full_text,
                'text': full_text,
                'length': len(full_text),
                'attrib': dict(section_elem.attrib)
            }
            
        except Exception as e:
            print(f" SECTION 提取錯誤: {e}")
            return None
    
    def _extract_cfr_part(self, part_elem, vol_num):
        """提取 CFR PART 元素"""
        try:
            # 獲取 PART 標題
            hd_elem = part_elem.find('HD')
            part_title = hd_elem.text.strip() if hd_elem is not None and hd_elem.text else "PART"
            
            # 獲取 EAR (Part number)
            ear_elem = part_elem.find('EAR')
            part_number = ear_elem.text.strip() if ear_elem is not None and ear_elem.text else ""
            
            # 收集 PART 內的文字內容
            content_parts = []
            
            # 跳過結構性元素，只收集實際內容
            for elem in part_elem.iter():
                if elem.tag in ['P', 'SUBJECT', 'NOTE'] and elem.text:
                    content_parts.append(elem.text.strip())
            
            full_text = "\n\n".join(content_parts)
            
            if len(full_text) < 10:
                return None
            
            return {
                'volume': vol_num,
                'section_id': part_number,
                'element_type': 'PART',
                'tag': 'PART',
                'heading': part_title,
                'full_text': full_text,
                'text': full_text,
                'length': len(full_text),
                'attrib': dict(part_elem.attrib)
            }
            
        except Exception as e:
            print(f" PART 提取錯誤: {e}")
            return None
    
    def _extract_cfr_subpart(self, subpart_elem, vol_num):
        """提取 CFR SUBPART 元素"""
        try:
            # 獲取 SUBPART 標題
            hd_elem = subpart_elem.find('HD')
            subpart_title = hd_elem.text.strip() if hd_elem is not None and hd_elem.text else "SUBPART"
            
            # 收集 SUBPART 內的文字內容
            content_parts = []
            
            for elem in subpart_elem.iter():
                if elem.tag in ['P', 'SUBJECT', 'NOTE', 'RESERVED'] and elem.text:
                    content_parts.append(elem.text.strip())
            
            full_text = "\n\n".join(content_parts)
            
            if len(full_text) < 10:
                return None
            
            return {
                'volume': vol_num,
                'section_id': "",
                'element_type': 'SUBPART',
                'tag': 'SUBPART',
                'heading': subpart_title,
                'full_text': full_text,
                'text': full_text,
                'length': len(full_text),
                'attrib': dict(subpart_elem.attrib)
            }
            
        except Exception as e:
            print(f" SUBPART 提取錯誤: {e}")
            return None
    
    def _extract_section_data(self, section_elem, vol_num):
        """從 section 元素中提取資料"""
        try:
            section_data = {
                'volume': vol_num,
                'section_id': section_elem.get('id', ''),
                'tag': section_elem.tag,
                'text': '',
                'children': []
            }
            
            # 提取文本內容
            if section_elem.text:
                section_data['text'] = section_elem.text.strip()
            
            # 提取子元素
            for child in section_elem:
                if child.text and len(child.text.strip()) > 10:
                    section_data['children'].append({
                        'tag': child.tag,
                        'text': child.text.strip(),
                        'attrib': dict(child.attrib)
                    })
            
            # 組合完整文本
            all_text = section_data['text']
            for child in section_data['children']:
                all_text += f"\n{child['text']}"
            
            section_data['full_text'] = all_text.strip()
            
            return section_data if all_text.strip() else None
            
        except Exception as e:
            print(f" Section 資料提取錯誤: {e}")
            return None
    
    def _process_volumes_data(self, all_volumes_data, successful_downloads):
        """處理所有 Volume 的資料"""
        try:
            # 組合所有內容
            full_content_parts = []
            per_section_records = []
            
            for vol_data in all_volumes_data:
                vol_num = vol_data.get('volume', 'Unknown')
                
                if 'full_text' in vol_data:
                    # 這是解析的 CFR 元素資料
                    section_text = vol_data['full_text']
                    section_id = vol_data.get('section_id', '')
                    heading = vol_data.get('heading', f"Volume {vol_num}")
                    element_type = vol_data.get('element_type', 'Section')
                    
                    # 格式化標題和內容
                    if section_id:
                        title = f"Volume {vol_num} - {heading} ({section_id})"
                    else:
                        title = f"Volume {vol_num} - {heading}"
                    
                    full_content_parts.append(f"{title}:\n{section_text}")
                    
                    per_section_records.append({
                        'part': f"Volume {vol_num}",
                        'section_citation': section_id,
                        'section_heading': title,
                        'element_type': element_type,
                        'text': section_text,
                        'length': len(section_text)
                    })
                elif 'text' in vol_data:
                    # 這是一般資料
                    text = vol_data.get('text', '')
                    tag = vol_data.get('tag', '')
                    
                    if text and len(text) > 20:  # 只保留有意義的內容
                        title = f"Volume {vol_num} - {tag}"
                        full_content_parts.append(f"{title}:\n{text}")
                        
                        per_section_records.append({
                            'part': f"Volume {vol_num}",
                            'section_citation': tag,
                            'section_heading': title,
                            'element_type': tag,
                            'text': text,
                            'length': len(text)
                        })
            
            # 組合完整內容
            full_content = "\n\n".join(full_content_parts)
            
            # 計算雜湊值
            sha256 = hashlib.sha256(full_content.encode("utf-8")).hexdigest()
            
            title = f"CFR Title 40 - Protection of Environment (Volumes 1-37 from GovInfo.gov)"
            
            return {
                "title": title,
                "content": full_content,
                "full_content": full_content,
                "per_section_records": per_section_records,
                "content_length": len(full_content),
                "excerpt": full_content[:1000],
                "sha256": sha256,
                "volumes_downloaded": successful_downloads,
                "total_sections": len(per_section_records),
                "notes": f"Downloaded {successful_downloads} volumes from GovInfo.gov; CFR XML format processed with enhanced structure recognition."
            }
            
        except Exception as e:
            print(f" 資料處理錯誤: {e}")
            return None
    
    def _create_error_result(self, error_message):
        """創建錯誤結果"""
        return {
            "error": error_message,
            "title": self.name,
            "content": "",
            "full_content": "",
            "sections": [],
            "structured_sections": [],
            "content_length": 0,
            "excerpt": "",
            "sha256": hashlib.sha256(error_message.encode("utf-8")).hexdigest(),
            "notes": f"Error: {error_message}"
        }