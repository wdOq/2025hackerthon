#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
統一的錯誤處理工具
為所有 scrapers 提供一致的錯誤輸出格式
"""
import hashlib


def create_error_result(name, reason, **kwargs):
    """
    創建統一格式的錯誤結果
    
    Args:
        name: Scraper 名稱
        reason: 錯誤原因描述
        **kwargs: 額外欄位（如 regulation_number, category 等）
    
    Returns:
        統一格式的錯誤結果字典
    """
    # 空字串的 SHA256 hash（統一使用）
    EMPTY_HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    
    result = {
        "title": name,
        "version_date": None,
        "notes": f"資料抓取失敗：{reason}",
        "sha256": EMPTY_HASH,
        "content_sha256": EMPTY_HASH,  # 雙重確保
        "content_length": 0,
        "excerpt": "",
        "full_content": "",
        "structured_sections": {},
        "per_section_records": [],
    }
    
    # 添加額外欄位
    result.update(kwargs)
    
    return result


def is_fetch_failed(entry):
    """
    判斷抓取是否失敗
    
    Args:
        entry: 抓取結果字典
    
    Returns:
        True: 抓取失敗
        False: 抓取成功
    """
    EMPTY_HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    
    # 檢查 sha256 (可能是 sha256 或 content_sha256)
    sha = entry.get("sha256") or entry.get("content_sha256")
    if sha == EMPTY_HASH:
        return True
    
    # 檢查 content_length
    if entry.get("content_length", -1) == 0:
        return True
    
    # 檢查 error 欄位
    if "error" in entry:
        return True
    
    return False
