#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Content optimizer for legal documents
Handles content length management and summarization
"""


def optimize_content(full_content, structured_sections=None):
    """
    Optimize content for storage and display
    
    Args:
        full_content: Full text content
        structured_sections: Structured sections dictionary
    
    Returns:
        Dictionary with optimized content info
    """
    if not full_content:
        return {
            "full_content": "",
            "content_length": 0,
            "content_summary": "",
            "is_truncated": False
        }
    
    content_length = len(full_content)
    
    # Generate summary (first 1000 characters)
    content_summary = full_content[:1000] if content_length > 1000 else full_content
    
    # Check if content needs truncation (optional, currently not truncating)
    is_truncated = False
    
    return {
        "full_content": full_content,
        "content_length": content_length,
        "content_summary": content_summary,
        "is_truncated": is_truncated
    }
