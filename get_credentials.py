"""
Script để lấy nội dung credentials.json để paste vào Render
"""

import json
import os

CREDENTIALS_FILE = 'credentials.json'

if os.path.exists(CREDENTIALS_FILE):
    print("=" * 60)
    print("NOI DUNG CREDENTIALS.JSON")
    print("=" * 60)
    print("\nCopy toan bo doan duoi day va paste vao bien moi truong GSPREAD_CREDENTIALS_JSON tren Render:\n")
    print("-" * 60)
    
    with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
        print(content)
    
    print("-" * 60)
    print("\nDa copy xong! Paste vao Render Dashboard.")
else:
    print(f"Khong tim thay file {CREDENTIALS_FILE}")
    print("Hay dam bao file credentials.json co trong thu muc nay.")

