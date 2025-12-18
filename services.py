"""
Services Module - Business Logic cho ExpenseBot
Chứa các hàm xử lý logic chung: Google Sheets, tính toán, báo cáo
Có thể được import bởi bot.py và keep_alive.py

Copyright (c) 2025 Lộc
All rights reserved.
"""

import os
import logging
from datetime import datetime, timedelta
from collections import defaultdict
import gspread
from oauth2client.service_account import ServiceAccountCredentials

logger = logging.getLogger(__name__)

# Import Google Search API
try:
    from googleapiclient.discovery import build
    GOOGLE_SEARCH_AVAILABLE = True
except ImportError:
    GOOGLE_SEARCH_AVAILABLE = False
    logger.warning("⚠️ google-api-python-client not installed. Google Search features will be disabled.")

# ==================== CẤU HÌNH ====================
CREDENTIALS_FILE = 'credentials.json'
SHEET_NAME = 'QuanLyChiTieu'
SHEET_ID = os.getenv('GOOGLE_SHEET_ID', '')
WEEKLY_LIMIT = 700000  # 700 nghìn đồng/tuần

# Google Search API Configuration
GOOGLE_SEARCH_API_KEY = os.getenv('GOOGLE_SEARCH_API_KEY', '')
GOOGLE_CSE_ID = os.getenv('GOOGLE_CSE_ID', '')

# VietQR Configuration
MY_BANK_ID = "VPB"
MY_ACCOUNT_NO = "0375646013"
MY_ACCOUNT_NAME = "LE PHUOC LOC"
MY_TEMPLATE = "compact"

# Global worksheet instance
worksheet = None


def init_google_sheets():
    """
    Khởi tạo kết nối với Google Sheets
    Trả về worksheet object
    """
    global worksheet
    
    logger.info("=" * 60)
    logger.info("BƯỚC 1: KHỞI TẠO GOOGLE SHEETS")
    logger.info("=" * 60)
    
    # Kiểm tra file credentials
    if not os.path.exists(CREDENTIALS_FILE):
        logger.info(f"⚠️ Không tìm thấy file {CREDENTIALS_FILE}, đang kiểm tra biến môi trường...")
        credentials_json = os.getenv('GSPREAD_CREDENTIALS_JSON')
        
        if credentials_json:
            logger.info("✅ Tìm thấy GSPREAD_CREDENTIALS_JSON, đang tạo file credentials.json...")
            with open(CREDENTIALS_FILE, 'w', encoding='utf-8') as f:
                f.write(credentials_json)
            logger.info(f"✅ Đã tạo file {CREDENTIALS_FILE} từ biến môi trường")
        else:
            logger.critical(f"❌ CRITICAL ERROR: Không tìm thấy file {CREDENTIALS_FILE} và không có biến môi trường GSPREAD_CREDENTIALS_JSON!")
            raise FileNotFoundError(f"Không tìm thấy file {CREDENTIALS_FILE} và không có biến môi trường GSPREAD_CREDENTIALS_JSON")
    
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    service_email = creds.service_account_email
    logger.info(f"✅ Service Account: {service_email}")
    
    client = gspread.authorize(creds)
    logger.info("✅ Đã kết nối với Google Sheets API")
    
    # Mở Sheet
    if SHEET_ID:
        sheet = client.open_by_key(SHEET_ID)
    else:
        sheet = client.open(SHEET_NAME)
    
    logger.info(f"✅ Đã mở Sheet: {sheet.title}")
    
    ws = sheet.sheet1
    logger.info(f"✅ Đã chọn worksheet: {ws.title}")
    
    # Cập nhật global worksheet TRƯỚC khi sử dụng
    worksheet = ws
    
    # Kiểm tra và tạo header nếu cần
    existing_data = worksheet.get_all_values()
    if not existing_data:
        logger.info("📝 Sheet trống, đang tạo header mới (7 cột)...")
        header = ['Full Time', 'Ngày', 'Tháng', 'Năm', 'Tên món', 'Phân loại', 'Số tiền']
        worksheet.append_row(header)
        logger.info("✅ Đã tạo header")
    else:
        logger.info(f"✅ Sheet đã có {len(existing_data)} dòng dữ liệu")
    
    logger.info("=" * 60)
    logger.info("✅ KHỞI TẠO GOOGLE SHEETS THÀNH CÔNG!")
    logger.info("=" * 60)
    
    return worksheet


def get_worksheet():
    """Lấy worksheet instance, khởi tạo nếu chưa có"""
    global worksheet
    if worksheet is None:
        worksheet = init_google_sheets()
    return worksheet


def save_expenses_to_sheet(expenses: list) -> list:
    """
    Lưu nhiều chi tiêu vào Google Sheet
    Format: [Full Time, Ngày, Tháng, Năm, Tên món, Phân loại, Số tiền]
    Hỗ trợ backdated entry: Nếu expense có field 'date' (format DD/MM/YYYY), dùng ngày đó
    """
    logger.info("=" * 60)
    logger.info("BƯỚC 3: GHI VÀO GOOGLE SHEET")
    logger.info("=" * 60)
    
    ws = get_worksheet()
    if ws is None:
        raise ValueError("Google Sheets chưa được khởi tạo")
    
    now = datetime.now()
    default_full_time = now.strftime('%Y-%m-%d %H:%M:%S')
    default_day = now.day
    default_month = now.month
    default_year = now.year
    
    logger.info(f"⏰ Thời gian mặc định: {default_full_time} ({default_day}/{default_month}/{default_year})")
    
    saved_items = []
    
    try:
        for i, expense in enumerate(expenses, 1):
            item_name = expense.get('item', 'Không xác định')
            amount = expense.get('amount', 0)
            category = expense.get('category', 'Khác')
            
            # Xử lý backdated entry: Kiểm tra field 'date'
            expense_date = expense.get('date')
            if expense_date:
                # Parse date từ format DD/MM/YYYY
                try:
                    date_parts = expense_date.split('/')
                    if len(date_parts) == 3:
                        day = int(date_parts[0])
                        month = int(date_parts[1])
                        year = int(date_parts[2])
                        
                        # Validate date
                        try:
                            expense_datetime = datetime(year, month, day, 12, 0, 0)  # Set 12:00 mặc định
                            full_time = expense_datetime.strftime('%Y-%m-%d %H:%M:%S')
                            logger.info(f"📅 Sử dụng ngày từ expense: {expense_date} -> {day}/{month}/{year}")
                        except ValueError:
                            # Date không hợp lệ, dùng ngày hiện tại
                            logger.warning(f"⚠️ Date không hợp lệ: {expense_date}, dùng ngày hiện tại")
                            day = default_day
                            month = default_month
                            year = default_year
                            full_time = default_full_time
                    else:
                        # Format sai, dùng ngày hiện tại
                        logger.warning(f"⚠️ Format date sai: {expense_date}, dùng ngày hiện tại")
                        day = default_day
                        month = default_month
                        year = default_year
                        full_time = default_full_time
                except (ValueError, AttributeError) as e:
                    # Lỗi parse, dùng ngày hiện tại
                    logger.warning(f"⚠️ Lỗi parse date '{expense_date}': {e}, dùng ngày hiện tại")
                    day = default_day
                    month = default_month
                    year = default_year
                    full_time = default_full_time
            else:
                # Không có date, dùng ngày hiện tại
                day = default_day
                month = default_month
                year = default_year
                full_time = default_full_time
            
            row = [full_time, day, month, year, item_name, category, amount]
            logger.info(f"💾 Đang ghi món {i}: {item_name} - {amount:,}đ (Ngày: {day}/{month}/{year})")
            ws.append_row(row)
            saved_items.append(expense)
        
        logger.info("=" * 60)
        logger.info(f"✅ Đã ghi thành công {len(saved_items)} món vào Sheet!")
        logger.info("=" * 60)
        
        return saved_items
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi lưu vào Google Sheet: {e}")
        raise


def calculate_weekly_spend() -> dict:
    """
    Tính toán chi tiêu tuần hiện tại (Thứ 2 - Chủ Nhật)
    Trả về: {'total': tổng tiền, 'remaining': số dư còn lại, 'percentage': phần trăm đã dùng}
    """
    logger.info("=" * 60)
    logger.info("BƯỚC: TÍNH TOÁN CHI TIÊU TUẦN")
    logger.info("=" * 60)
    
    ws = get_worksheet()
    if ws is None:
        raise ValueError("Google Sheets chưa được khởi tạo")
    
    try:
        # Xác định tuần hiện tại (Thứ 2 - Chủ Nhật)
        now = datetime.now()
        # Tìm Thứ 2 của tuần này (weekday() trả về 0=Monday, 6=Sunday)
        days_since_monday = now.weekday()  # 0 = Monday, 6 = Sunday
        monday = now - timedelta(days=days_since_monday)
        monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        sunday = monday + timedelta(days=6)
        sunday = sunday.replace(hour=23, minute=59, second=59)
        
        logger.info(f"📅 Tuần hiện tại: {monday.strftime('%d/%m/%Y')} - {sunday.strftime('%d/%m/%Y')}")
        
        # Đọc dữ liệu từ Sheet
        all_data = ws.get_all_values()
        if len(all_data) <= 1:  # Chỉ có header
            return {
                'total': 0,
                'remaining': WEEKLY_LIMIT,
                'percentage': 0.0,
                'monday': monday,
                'sunday': sunday
            }
        
        data_rows = all_data[1:]
        week_total = 0
        
        for row in data_rows:
            if len(row) < 7:
                continue
            
            try:
                # Đọc từ Sheet (cột 2,3,4 là Ngày, Tháng, Năm; cột 7 là Số tiền)
                row_day = int(row[1]) if row[1] else 0
                row_month = int(row[2]) if row[2] else 0
                row_year = int(row[3]) if row[3] else 0
                amount = int(row[6]) if row[6] else 0
                
                # Tạo datetime từ dữ liệu
                try:
                    row_date = datetime(row_year, row_month, row_day)
                    # Kiểm tra xem có nằm trong tuần này không
                    if monday <= row_date <= sunday:
                        week_total += amount
                except ValueError:
                    continue
                    
            except (ValueError, IndexError) as e:
                logger.warning(f"⚠️ Lỗi đọc dòng: {e}")
                continue
        
        remaining = WEEKLY_LIMIT - week_total
        percentage = (week_total / WEEKLY_LIMIT * 100) if WEEKLY_LIMIT > 0 else 0
        
        logger.info(f"✅ Tuần này đã tiêu: {week_total:,}đ / {WEEKLY_LIMIT:,}đ ({percentage:.1f}%)")
        logger.info(f"💰 Còn dư: {remaining:,}đ")
        
        return {
            'total': week_total,
            'remaining': remaining,
            'percentage': percentage,
            'monday': monday,
            'sunday': sunday
        }
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi tính toán chi tiêu tuần: {e}")
        raise


def get_financial_context() -> str:
    """
    Đọc dữ liệu từ Google Sheet và tạo context cho AI
    Tính toán trực tiếp tại chỗ (Real-time calculation)
    Trả về: Đoạn văn bản tóm tắt tình hình tài chính với số liệu cụ thể
    """
    logger.info("=" * 60)
    logger.info("📊 TẠO FINANCIAL CONTEXT CHO AI (Real-time Calculation)")
    logger.info("=" * 60)
    
    ws = get_worksheet()
    if ws is None:
        logger.warning("⚠️ Worksheet chưa được khởi tạo")
        now = datetime.now()
        return (
            f"DỮ LIỆU TÀI CHÍNH THỰC TẾ (Cập nhật lúc {now.strftime('%H:%M:%S')}):\n"
            f"- Hôm nay ({now.strftime('%d/%m/%Y')}): Đã tiêu 0đ.\n"
            f"- Tháng này: 0đ.\n"
            f"- Ngân sách tuần: Còn dư {WEEKLY_LIMIT:,}đ.\n"
            f"- 5 giao dịch gần nhất: Không có dữ liệu."
        )
    
    try:
        # Đọc toàn bộ dữ liệu từ Sheet
        all_data = ws.get_all_values()
        
        # Lấy thời gian hiện tại
        now = datetime.now()
        today = now.day
        current_month = now.month
        current_year = now.year
        
        # Tính tuần hiện tại (Thứ 2 - Chủ Nhật)
        days_since_monday = now.weekday()  # 0 = Monday, 6 = Sunday
        monday = now - timedelta(days=days_since_monday)
        monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        sunday = monday + timedelta(days=6)
        sunday = sunday.replace(hour=23, minute=59, second=59)
        
        # Khởi tạo biến tính toán
        today_spend = 0
        month_spend = 0
        week_spend = 0
        last_5_transactions = []
        
        # Xử lý dữ liệu
        if len(all_data) > 1:  # Có dữ liệu (không chỉ header)
            data_rows = all_data[1:]  # Bỏ qua header
            
            # Lấy 5 giao dịch cuối cùng (từ dưới lên)
            valid_rows = []
            for row in data_rows:
                if len(row) >= 7:
                    try:
                        row_day = int(row[1]) if row[1] else 0
                        row_month = int(row[2]) if row[2] else 0
                        row_year = int(row[3]) if row[3] else 0
                        amount = int(row[6]) if row[6] else 0
                        item_name = row[4] if len(row) > 4 else 'Không xác định'
                        category = row[5] if len(row) > 5 else 'Khác'
                        
                        if amount > 0:
                            valid_rows.append({
                                'day': row_day,
                                'month': row_month,
                                'year': row_year,
                                'amount': amount,
                                'item': item_name,
                                'category': category
                            })
                    except (ValueError, IndexError):
                        continue
            
            # Tính toán các chỉ số
            for row_data in valid_rows:
                amount = row_data['amount']
                row_day = row_data['day']
                row_month = row_data['month']
                row_year = row_data['year']
                
                # Tính hôm nay
                if row_day == today and row_month == current_month and row_year == current_year:
                    today_spend += amount
                
                # Tính tháng này
                if row_month == current_month and row_year == current_year:
                    month_spend += amount
                
                # Tính tuần này
                try:
                    row_date = datetime(row_year, row_month, row_day)
                    if monday <= row_date <= sunday:
                        week_spend += amount
                except ValueError:
                    continue
            
            # Lấy 5 giao dịch cuối cùng (từ dưới lên)
            last_5_transactions = valid_rows[-5:] if len(valid_rows) > 0 else []
        
        # Tính số dư tuần
        weekly_remain = WEEKLY_LIMIT - week_spend
        
        # Tạo danh sách giao dịch gần nhất
        transactions_list = []
        if last_5_transactions:
            for i, trans in enumerate(reversed(last_5_transactions), 1):  # Đảo ngược để mới nhất ở trên
                transactions_list.append(
                    f"  {i}. {trans['item']}: {trans['amount']:,}đ ({trans['category']}) - "
                    f"{trans['day']}/{trans['month']}/{trans['year']}"
                )
        else:
            transactions_list.append("  Không có giao dịch nào.")
        
        # Tạo context string
        context_text = (
            f"DỮ LIỆU TÀI CHÍNH THỰC TẾ (Cập nhật lúc {now.strftime('%H:%M:%S')}):\n"
            f"- Hôm nay ({now.strftime('%d/%m/%Y')}): Đã tiêu {today_spend:,}đ.\n"
            f"- Tháng này: {month_spend:,}đ.\n"
            f"- Ngân sách tuần: Còn dư {weekly_remain:,}đ.\n"
            f"- 5 giao dịch gần nhất:\n"
            f"{chr(10).join(transactions_list)}"
        )
        
        logger.info("✅ Đã tạo financial context (Real-time)")
        logger.info(f"📊 Hôm nay: {today_spend:,}đ | Tháng: {month_spend:,}đ | Tuần còn: {weekly_remain:,}đ")
        logger.info(f"📝 Context length: {len(context_text)} ký tự")
        
        return context_text
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi tạo financial context: {e}", exc_info=True)
        now = datetime.now()
        # Trả về context mặc định dù có lỗi
        return (
            f"DỮ LIỆU TÀI CHÍNH THỰC TẾ (Cập nhật lúc {now.strftime('%H:%M:%S')}):\n"
            f"- Hôm nay ({now.strftime('%d/%m/%Y')}): Đã tiêu 0đ.\n"
            f"- Tháng này: 0đ.\n"
            f"- Ngân sách tuần: Còn dư {WEEKLY_LIMIT:,}đ.\n"
            f"- 5 giao dịch gần nhất: Không có dữ liệu."
        )


def get_expense_report() -> dict:
    """Đọc dữ liệu từ Sheet và tính toán báo cáo"""
    logger.info("=" * 60)
    logger.info("BƯỚC: ĐỌC DỮ LIỆU TỪ SHEET")
    logger.info("=" * 60)
    
    ws = get_worksheet()
    if ws is None:
        raise ValueError("Google Sheets chưa được khởi tạo")
    
    try:
        all_data = ws.get_all_values()
        if len(all_data) <= 1:  # Chỉ có header
            return {
                'today_total': 0,
                'month_total': 0,
                'top_expenses': []
            }
        
        # Bỏ qua header
        data_rows = all_data[1:]
        
        now = datetime.now()
        today = now.day
        current_month = now.month
        current_year = now.year
        
        today_total = 0
        month_total = 0
        category_totals = defaultdict(int)
        
        for row in data_rows:
            if len(row) < 7:
                continue
            
            try:
                # Đọc từ Sheet (cột 2,3,4 là Ngày, Tháng, Năm; cột 7 là Số tiền)
                row_day = int(row[1]) if row[1] else 0
                row_month = int(row[2]) if row[2] else 0
                row_year = int(row[3]) if row[3] else 0
                amount = int(row[6]) if row[6] else 0
                category = row[5] if len(row) > 5 else 'Khác'
                item_name = row[4] if len(row) > 4 else 'Không xác định'
                
                # Tính tổng hôm nay
                if row_day == today and row_month == current_month and row_year == current_year:
                    today_total += amount
                
                # Tính tổng tháng này
                if row_month == current_month and row_year == current_year:
                    month_total += amount
                    category_totals[category] += amount
                    
            except (ValueError, IndexError) as e:
                logger.warning(f"⚠️ Lỗi đọc dòng: {e}")
                continue
        
        # Sắp xếp top chi tiêu theo category
        top_expenses = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:5]
        
        logger.info(f"✅ Đã tính toán: Hôm nay {today_total:,}đ, Tháng này {month_total:,}đ")
        
        return {
            'today_total': today_total,
            'month_total': month_total,
            'top_expenses': top_expenses
        }
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi đọc Sheet: {e}")
        raise


def get_expenses_data() -> dict:
    """
    Lấy dữ liệu chi tiêu hôm nay và tháng này
    Trả về dict với format phù hợp cho API
    """
    try:
        report = get_expense_report()
        weekly_data = calculate_weekly_spend()
        
        return {
            'success': True,
            'data': {
                'today': {
                    'total': report['today_total'],
                    'formatted': f"{report['today_total']:,}đ"
                },
                'month': {
                    'total': report['month_total'],
                    'formatted': f"{report['month_total']:,}đ"
                },
                'week': {
                    'total': weekly_data['total'],
                    'remaining': weekly_data['remaining'],
                    'percentage': round(weekly_data['percentage'], 2),
                    'limit': WEEKLY_LIMIT,
                    'formatted': f"{weekly_data['total']:,}đ / {WEEKLY_LIMIT:,}đ"
                },
                'top_expenses': [
                    {'category': cat, 'amount': amt, 'formatted': f"{amt:,}đ"}
                    for cat, amt in report['top_expenses']
                ]
            },
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Lỗi khi lấy dữ liệu expenses: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


def get_report_data() -> dict:
    """
    Lấy báo cáo tổng quan (giống get_financial_context nhưng format JSON)
    Trả về dict với format phù hợp cho API
    """
    try:
        context_text = get_financial_context()
        report = get_expense_report()
        weekly_data = calculate_weekly_spend()
        
        return {
            'success': True,
            'data': {
                'summary': context_text,
                'today_total': report['today_total'],
                'month_total': report['month_total'],
                'week_total': weekly_data['total'],
                'week_remaining': weekly_data['remaining'],
                'week_percentage': round(weekly_data['percentage'], 2),
                'week_limit': WEEKLY_LIMIT,
                'top_expenses': [
                    {'category': cat, 'amount': amt}
                    for cat, amt in report['top_expenses']
                ]
            },
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Lỗi khi lấy báo cáo: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


# ==================== GOOGLE SEARCH ====================
def google_search(query: str, num_results: int = 5) -> str:
    """
    Tìm kiếm trên Google và trả về kết quả tóm tắt
    - query: Từ khóa tìm kiếm
    - num_results: Số lượng kết quả (mặc định 5)
    Trả về: Chuỗi text chứa kết quả tìm kiếm (Title + Snippet)
    """
    if not GOOGLE_SEARCH_AVAILABLE:
        logger.warning("⚠️ Google Search API không khả dụng (chưa cài đặt thư viện)")
        return ""
    
    if not GOOGLE_SEARCH_API_KEY or not GOOGLE_CSE_ID:
        logger.warning("⚠️ Google Search API Key hoặc CSE ID chưa được cấu hình")
        return ""
    
    try:
        logger.info("=" * 60)
        logger.info(f"🔍 ĐANG TÌM KIẾM GOOGLE: '{query}'")
        logger.info("=" * 60)
        
        # Khởi tạo Google Custom Search API
        service = build("customsearch", "v1", developerKey=GOOGLE_SEARCH_API_KEY)
        
        # Thực hiện tìm kiếm
        result = service.cse().list(
            q=query,
            cx=GOOGLE_CSE_ID,
            num=min(num_results, 10)  # Google API chỉ cho phép tối đa 10 kết quả
        ).execute()
        
        # Xử lý kết quả
        items = result.get('items', [])
        
        if not items:
            logger.warning("⚠️ Không tìm thấy kết quả nào")
            return "Không tìm thấy kết quả nào cho từ khóa này."
        
        # Tạo chuỗi kết quả
        search_results = []
        for i, item in enumerate(items[:num_results], 1):
            title = item.get('title', 'Không có tiêu đề')
            snippet = item.get('snippet', 'Không có mô tả')
            link = item.get('link', '')
            
            search_results.append(
                f"{i}. **{title}**\n"
                f"   {snippet}\n"
                f"   🔗 {link}"
            )
        
        result_text = "\n\n".join(search_results)
        
        logger.info(f"✅ Đã tìm thấy {len(items)} kết quả")
        logger.info(f"📝 Kết quả tóm tắt: {len(result_text)} ký tự")
        
        return result_text
        
    except Exception as e:
        error_str = str(e).lower()
        if 'quota' in error_str or '429' in error_str:
            logger.warning("⚠️ Google Search API quota đã hết")
            return "⚠️ Google Search API quota đã hết. Vui lòng thử lại sau."
        elif 'invalid' in error_str or '403' in error_str:
            logger.warning(f"⚠️ Google Search API key không hợp lệ: {e}")
            return "⚠️ Google Search API key không hợp lệ hoặc chưa được cấu hình."
        else:
            logger.error(f"❌ Lỗi Google Search API: {e}", exc_info=True)
            return f"⚠️ Không thể tìm kiếm: {str(e)}"


# ==================== IMAGE GENERATION ====================
def generate_image(prompt: str) -> bytes:
    """
    Tạo ảnh từ prompt sử dụng Pollinations.ai (miễn phí, không cần key)
    - prompt: Mô tả ảnh bằng tiếng Anh
    Trả về: Bytes của ảnh đã tạo (hoặc None nếu lỗi)
    """
    import urllib.parse
    import requests
    
    try:
        # Encode prompt để đưa vào URL
        encoded_prompt = urllib.parse.quote(prompt)
        
        # URL của Pollinations.ai với các tham số tối ưu
        image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=512&height=512&model=flux&nologo=true"
        
        logger.info("=" * 60)
        logger.info(f"🎨 ĐANG TẠO ẢNH: '{prompt}'")
        logger.info(f"🔗 URL: {image_url}")
        logger.info("=" * 60)
        
        # Tải ảnh từ URL
        response = requests.get(image_url, timeout=30, stream=True)
        
        if response.status_code == 200:
            # Đọc toàn bộ ảnh vào memory
            image_bytes = response.content
            logger.info(f"✅ Đã tải ảnh thành công: {len(image_bytes)} bytes")
            return image_bytes
        else:
            logger.error(f"❌ Lỗi tải ảnh: HTTP {response.status_code}")
            return None
        
    except requests.exceptions.Timeout:
        logger.error("❌ Timeout khi tải ảnh từ Pollinations.ai")
        return None
    except Exception as e:
        logger.error(f"❌ Lỗi tạo ảnh: {e}", exc_info=True)
        return None


# ==================== VIETQR GENERATION ====================
def generate_vietqr_url(amount: int, content: str = "") -> str:
    """
    Tạo URL mã QR chuyển khoản nhanh VietQR
    - amount: Số tiền (int)
    - content: Nội dung chuyển khoản (string)
    Trả về: URL của ảnh QR code
    """
    import urllib.parse
    
    try:
        # URL encode nội dung để xử lý khoảng trắng/tiếng Việt
        encoded_content = urllib.parse.quote(content) if content else ""
        encoded_account_name = urllib.parse.quote(MY_ACCOUNT_NAME)
        
        # Tạo URL chuẩn VietQR
        qr_url = (
            f"https://img.vietqr.io/image/{MY_BANK_ID}-{MY_ACCOUNT_NO}-{MY_TEMPLATE}.png"
            f"?amount={amount}"
            f"&addInfo={encoded_content}"
            f"&accountName={encoded_account_name}"
        )
        
        logger.info("=" * 60)
        logger.info(f"💳 ĐANG TẠO MÃ QR VIETQR")
        logger.info(f"💰 Số tiền: {amount:,}đ")
        logger.info(f"📝 Nội dung: '{content}'")
        logger.info(f"🔗 URL: {qr_url}")
        logger.info("=" * 60)
        
        return qr_url
        
    except Exception as e:
        logger.error(f"❌ Lỗi tạo VietQR URL: {e}", exc_info=True)
        return ""

