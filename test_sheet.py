"""
Script test kết nối Google Sheets
Chạy script này để kiểm tra xem có kết nối được với Sheet không
"""

import os
import sys
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

# Fix encoding cho Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()

SHEET_ID = os.getenv('GOOGLE_SHEET_ID', '1V0f_ZRfvX0qZF19E_VsR5f7OyNsYbhoj41D-c0K6sY4')
CREDENTIALS_FILE = 'credentials.json'

print("Dang kiem tra ket noi Google Sheets...\n")

try:
    # Đọc credentials
    print(f"1. Đang đọc file {CREDENTIALS_FILE}...")
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    
    # Lấy email Service Account
    service_email = creds.service_account_email
    print(f"   [OK] Email Service Account: {service_email}")
    print(f"   [WARNING] Hay dam bao email nay da duoc share quyen Editor tren Sheet!\n")
    
    # Kết nối
    print("2. Đang kết nối với Google Sheets API...")
    client = gspread.authorize(creds)
    print("   [OK] Da ket noi thanh cong\n")
    
    # Mở Sheet
    print(f"3. Đang mở Sheet với ID: {SHEET_ID}...")
    sheet = client.open_by_key(SHEET_ID)
    print(f"   [OK] Da mo Sheet: {sheet.title}\n")
    
    # Kiểm tra worksheet
    print("4. Đang kiểm tra worksheet...")
    worksheet = sheet.sheet1
    print(f"   [OK] Worksheet: {worksheet.title}\n")
    
    # Kiểm tra dữ liệu hiện có
    print("5. Đang kiểm tra dữ liệu...")
    data = worksheet.get_all_values()
    print(f"   [OK] Sheet co {len(data)} dong du lieu")
    if data:
        print(f"   📊 Dòng đầu tiên (header): {data[0]}")
        if len(data) > 1:
            print(f"   📊 Dòng cuối cùng: {data[-1]}")
    print()
    
    # Test ghi dữ liệu
    print("6. Đang test ghi dữ liệu...")
    from datetime import datetime
    test_row = [datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'Test Item', 'Khác', 999]
    worksheet.append_row(test_row)
    print(f"   [OK] Da ghi test row: {test_row}")
    print("   [OK] Ket noi va ghi du lieu thanh cong!\n")
    
    print("=" * 50)
    print("[OK] TAT CA DEU HOAT DONG TOT!")
    print("=" * 50)
    print(f"\n💡 Nếu bot vẫn không hoạt động, hãy:")
    print(f"   1. Kiểm tra email Service Account: {service_email}")
    print(f"   2. Đảm bảo email này đã được share quyền Editor trên Sheet")
    print(f"   3. Kiểm tra log khi chạy bot.py để xem lỗi cụ thể")
    
except FileNotFoundError:
    print(f"[ERROR] Khong tim thay file {CREDENTIALS_FILE}")
    print("[TIP] Hay dam bao file credentials.json nam trong thu muc du an")
except gspread.exceptions.SpreadsheetNotFound:
    print(f"[ERROR] Khong tim thay Sheet voi ID: {SHEET_ID}")
    print("[TIP] Hay kiem tra:")
    print("   1. Sheet ID co dung khong?")
    if 'service_email' in locals():
        print(f"   2. Service Account ({service_email}) da duoc share quyen Editor chua?")
except gspread.exceptions.APIError as e:
    print(f"[ERROR] Loi API: {e}")
    print("[TIP] Co the do Service Account khong co quyen truy cap Sheet")
except Exception as e:
    print(f"[ERROR] Loi: {e}")
    print(f"[TIP] Loai loi: {type(e).__name__}")

