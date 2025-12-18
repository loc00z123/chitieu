"""
Script để dừng tất cả các instance bot đang chạy
"""

import sys
import subprocess

if sys.platform == 'win32':
    # Windows
    try:
        # Tìm và dừng các process python đang chạy bot.py
        result = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
            capture_output=True,
            text=True
        )
        
        if 'python.exe' in result.stdout:
            print("Tim thay cac process Python dang chay...")
            print("Hay dong cac cua so terminal dang chay bot.py")
            print("Hoac nhan Ctrl+C trong cac terminal do")
        else:
            print("Khong tim thay process Python nao dang chay")
            
    except Exception as e:
        print(f"Loi: {e}")
        print("\nHay thu cong:")
        print("1. Dong tat ca cac cua so terminal")
        print("2. Hoac nhan Ctrl+C trong cac terminal dang chay bot")
else:
    # Linux/Mac
    try:
        subprocess.run(['pkill', '-f', 'bot.py'])
        print("Da dung cac process bot.py")
    except:
        print("Khong the dung process. Hay thu cong:")
        print("1. Tim process: ps aux | grep bot.py")
        print("2. Dung process: kill <PID>")

