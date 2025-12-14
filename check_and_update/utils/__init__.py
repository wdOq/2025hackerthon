#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility functions for regwatch system
"""
import requests


def get_session():
    """
    Create and return a requests session with default headers
    
    Returns:
        requests.Session: Configured session object
    """
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    return session
