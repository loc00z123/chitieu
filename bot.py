"""
Telegram Bot Quản Lý Chi Tiêu - ExpenseBot Enterprise Edition
Sử dụng Smart Pattern Matching - Không cần AI
Phiên bản Enterprise với Multi-Line Parsing, Báo Cáo, Biểu Đồ và Xuất Excel
"""

import os
import re
import json
import logging
import io
from datetime import datetime, timedelta, time as dt_time
from collections import defaultdict
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, JobQueue
from telegram.constants import ParseMode
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Thread-safe backend
import matplotlib.pyplot as plt
import seaborn as sns
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter
from keep_alive import keep_alive

# Load biến môi trường từ file .env
load_dotenv()

# ==================== CẤU HÌNH LOGGING ====================
logging.basicConfig(
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ==================== CẤU HÌNH ====================
TELEGRAM_TOKEN = os.getenv('BOT_TOKEN', '')
CREDENTIALS_FILE = 'credentials.json'
SHEET_NAME = 'QuanLyChiTieu'
SHEET_ID = os.getenv('GOOGLE_SHEET_ID', '')

# ==================== CẤU HÌNH NGÂN SÁCH TUẦN ====================
WEEKLY_LIMIT = 700000  # 700 nghìn đồng/tuần

# ==================== LƯU TRỮ REMINDER ====================
REMINDER_FILE = 'reminders.json'
user_reminders = {}  # {user_id: {'hour': int, 'minute': int}}

# Load reminders từ file nếu có
def load_reminders():
    """Load reminders từ file JSON"""
    global user_reminders
    try:
        if os.path.exists(REMINDER_FILE):
            with open(REMINDER_FILE, 'r', encoding='utf-8') as f:
                user_reminders = json.load(f)
                logger.info(f"✅ Đã load {len(user_reminders)} reminders từ file")
    except Exception as e:
        logger.warning(f"⚠️ Không thể load reminders: {e}")
        user_reminders = {}

def save_reminders():
    """Lưu reminders vào file JSON"""
    try:
        with open(REMINDER_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_reminders, f, ensure_ascii=False, indent=2)
        logger.info("✅ Đã lưu reminders vào file")
    except Exception as e:
        logger.error(f"❌ Không thể lưu reminders: {e}")

# Load reminders khi khởi động
load_reminders()

logger.info("=" * 60)
logger.info("KHỞI ĐỘNG BOT QUẢN LÝ CHI TIÊU (Enterprise Edition)")
logger.info("=" * 60)
logger.info(f"💰 Hạn mức tuần: {WEEKLY_LIMIT:,}đ")
logger.info("📊 Tính năng Enterprise: Biểu đồ, Xuất Excel, Reminder, Bill Splitter")

if not TELEGRAM_TOKEN:
    logger.critical("❌ CRITICAL ERROR: TELEGRAM_TOKEN không được tìm thấy!")
    raise ValueError("TELEGRAM_TOKEN không được tìm thấy!")
else:
    logger.info("✅ TELEGRAM_TOKEN: Đã tìm thấy")

# ==================== TỪ KHÓA LÃNG PHÍ (Cảnh Sát Chi Tiêu) ====================
WASTEFUL_KEYWORDS = [
    'game', 'nạp', 'nap', 'skin', 'gacha', 'trà sữa', 'tra sua', 'toco', 'mixue', 
    'phim', 'netflix', 'đồ chơi', 'do choi', 'mô hình', 'mo hinh', 'nhậu', 'nhau',
    'pubg', 'lol', 'liên quân', 'lien quan', 'mobile legend', 'genshin', 'top up',
    'thẻ game', 'the game', 'card', 'gift code', 'code', 'vip', 'premium'
]

WASTEFUL_WARNINGS = [
    "Tiền không phải lá mít đâu nhé! 💸",
    "Lại tốn tiền vào cái này rồi, chán thanh niên! 😒",
    "Bớt bớt lại đi, cuối tháng ăn mì gói bây giờ! 🍜",
    "Tiêu tiền như nước, rồi lại than nghèo! 💧",
    "Cẩn thận kẻo hết tiền trước khi hết tháng! ⚠️",
    "Nhớ tiết kiệm một chút, đừng phung phí quá! 💰",
    "Lại chi tiêu không cần thiết rồi, cẩn thận nhé! 🚨",
    "Tiền kiếm được khó lắm, đừng vứt đi như vậy! 😤",
    "Có tiền thì tiêu, không có tiền thì... than! 😅",
    "Nhớ mục tiêu tiết kiệm của mình nhé! 🎯"
]

logger.info("✅ Đã tải từ khóa lãng phí và cảnh báo")

# ==================== TỪ ĐIỂN PHÂN LOẠI TỰ ĐỘNG ====================
CATEGORY_KEYWORDS = {
    'Ăn uống': [
        'phở', 'pho', 'cơm', 'com', 'bún', 'bun', 'nước', 'nuoc', 'cf', 'cafe', 'cà phê', 'ca phe',
        'trà', 'tra', 'chè', 'che', 'bánh', 'banh', 'mì', 'mi', 'bánh mì', 'banh mi', 'xôi', 'xoi',
        'cháo', 'chao', 'súp', 'sup', 'lẩu', 'lau', 'nướng', 'nuong', 'gà', 'ga', 'thịt', 'thit',
        'cá', 'ca', 'tôm', 'tom', 'rau', 'đồ ăn', 'do an', 'ăn', 'an', 'uống', 'uong', 'nước uống',
        'nuoc uong', 'sữa', 'sua', 'kem', 'bánh kẹo', 'banh keo', 'snack', 'kẹo', 'keo'
    ],
    'Di chuyển': [
        'xăng', 'xang', 'xe', 'grab', 'be', 'uber', 'taxi', 'gửi xe', 'gui xe', 'đỗ xe', 'do xe',
        'bãi xe', 'bai xe', 'vé', 've', 'ticket', 'máy bay', 'may bay', 'tàu', 'tau', 'xe bus',
        'xe buýt', 'xe buyt', 'đi lại', 'di lai', 'vận chuyển', 'van chuyen', 'ship', 'giao hàng',
        'giao hang', 'đi', 'di', 'về', 've', 'đi về', 'di ve'
    ],
    'Học tập': [
        'vở', 'vo', 'sách', 'sach', 'bút', 'but', 'học', 'hoc', 'sách giáo khoa', 'sach giao khoa',
        'tài liệu', 'tai lieu', 'photocopy', 'photo', 'in', 'mực', 'muc', 'bút chì', 'but chi',
        'thước', 'thuoc', 'compa', 'máy tính', 'may tinh', 'calculator', 'học phí', 'hoc phi',
        'phí học', 'phi hoc', 'đăng ký', 'dang ky', 'đăng kí', 'dang ki', 'khóa học', 'khoa hoc'
    ]
}

logger.info("✅ Đã tải từ điển phân loại tự động")

# ==================== HÀM XỬ LÝ THÔNG MINH ====================
def parse_amount(text: str) -> tuple:
    """Tìm và chuyển đổi số tiền từ text. Trả về: (amount, positions)"""
    text_lower = text.lower()
    patterns = [
        (r'(\d+(?:\.\d+)?)\s*tr(?:iệu)?', 1000000),
        (r'(\d+(?:\.\d+)?)\s*k(?:ilo)?', 1000),
        (r'(\d+(?:\.\d+)?)\s*ng(?:àn)?', 1000),
        (r'(\d+(?:\.\d+)?)\s*nghìn', 1000),
        (r'(\d+(?:\.\d+)?)\s*000', 1),
        (r'(\d+(?:\.\d+)?)\s*d(?:ồng)?', 1),
        (r'(\d+(?:\.\d+)?)\s*đ', 1),
        (r'(\d{4,})', 1),
    ]
    
    amounts_found = []
    for pattern, multiplier in patterns:
        matches = re.finditer(pattern, text_lower)
        for match in matches:
            try:
                number = float(match.group(1))
                amount = int(number * multiplier)
                amounts_found.append((amount, match.start(), match.end()))
            except:
                continue
    
    if amounts_found:
        amounts_found.sort(key=lambda x: x[0], reverse=True)
        amount = amounts_found[0][0]
        logger.info(f"💰 Tìm thấy số tiền: {amount:,}đ")
        return amount, amounts_found
    
    return 0, []


def extract_item_name(text: str, amount_positions: list) -> str:
    """Trích xuất tên món từ text, loại bỏ phần số tiền"""
    text_cleaned = text
    for amount, start, end in sorted(amount_positions, key=lambda x: x[1], reverse=True):
        text_cleaned = text_cleaned[:start] + text_cleaned[end:]
    
    text_cleaned = text_cleaned.strip()
    remove_words = ['nay', 'hôm nay', 'hom nay', 'vừa', 'vua', 'mới', 'moi', 'làm', 'lam', 
                    'ăn', 'an', 'uống', 'uong', 'mua', 'chi', 'tiêu', 'tieu', 'ngon', 'quá', 'qua']
    
    words = text_cleaned.split()
    words_cleaned = [w for w in words if w.lower() not in remove_words]
    item_name = ' '.join(words_cleaned).strip()
    item_name = re.sub(r'\d+', '', item_name).strip()
    
    if len(item_name) < 2:
        if amount_positions:
            first_amount_start = min(pos[1] for pos in amount_positions)
            item_name = text[:first_amount_start].strip()
        else:
            item_name = text.strip()
    
    item_name = re.sub(r'[^\w\s]', ' ', item_name)
    item_name = ' '.join(item_name.split())
    
    if not item_name:
        item_name = "Không xác định"
    
    logger.info(f"📝 Tên món trích xuất: {item_name}")
    return item_name


def auto_categorize(item_name: str) -> str:
    """Tự động phân loại dựa trên từ khóa trong tên món"""
    item_lower = item_name.lower()
    item_normalized = item_lower
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in item_normalized:
                logger.info(f"🏷️ Phân loại: {category} (từ khóa: {keyword})")
                return category
    
    logger.info(f"🏷️ Phân loại: Khác")
    return "Khác"


def parse_single_item(text: str) -> dict:
    """Parse một món đơn lẻ"""
    amount, amount_positions = parse_amount(text)
    if amount == 0:
        raise ValueError("Không tìm thấy số tiền")
    
    item_name = extract_item_name(text, amount_positions)
    category = auto_categorize(item_name)
    
    return {
        'item': item_name,
        'amount': amount,
        'category': category
    }


def parse_multiple_items(text: str) -> list:
    """
    Parse nhiều món từ một tin nhắn
    Hỗ trợ phân cách bởi dấu phẩy hoặc xuống dòng
    """
    logger.info("=" * 60)
    logger.info("BƯỚC 1: PHÂN TÍCH NHIỀU MÓN (Multi-Line Parsing)")
    logger.info("=" * 60)
    logger.info(f"📝 Text nhận được: '{text}'")
    
    # Tách text thành các phần (dấu phẩy hoặc xuống dòng)
    # Loại bỏ khoảng trắng thừa
    text = text.strip()
    
    # Tách theo dấu phẩy hoặc xuống dòng
    items_text = re.split(r'[,，\n\r]+', text)
    items_text = [item.strip() for item in items_text if item.strip()]
    
    logger.info(f"🔍 Đã tách thành {len(items_text)} phần")
    
    results = []
    for i, item_text in enumerate(items_text, 1):
        logger.info(f"🔍 Đang xử lý món {i}/{len(items_text)}: '{item_text}'")
        try:
            parsed_item = parse_single_item(item_text)
            results.append(parsed_item)
            logger.info(f"✅ Món {i}: {parsed_item['item']} - {parsed_item['amount']:,}đ - {parsed_item['category']}")
        except ValueError as e:
            logger.warning(f"⚠️ Món {i} không hợp lệ: {e}")
            continue
    
    if not results:
        raise ValueError("Không tìm thấy món hợp lệ nào trong tin nhắn")
    
    logger.info("=" * 60)
    logger.info(f"✅ Đã phân tích thành công {len(results)} món")
    logger.info("=" * 60)
    
    return results


# ==================== KẾT NỐI GOOGLE SHEETS ====================
def init_google_sheets():
    """Khởi tạo kết nối với Google Sheets"""
    logger.info("=" * 60)
    logger.info("BƯỚC 2: KIỂM TRA KẾT NỐI GOOGLE SHEETS")
    logger.info("=" * 60)
    
    try:
        # Xử lý credentials: Nếu không có file, tạo từ biến môi trường (cho Cloud deployment)
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
        
        if SHEET_ID:
            sheet = client.open_by_key(SHEET_ID)
        else:
            sheet = client.open(SHEET_NAME)
        
        logger.info(f"✅ Đã mở Sheet: {sheet.title}")
        
        worksheet = sheet.sheet1
        logger.info(f"✅ Đã chọn worksheet: {worksheet.title}")
        
        existing_data = worksheet.get_all_values()
        if not existing_data:
            logger.info("📝 Sheet trống, đang tạo header mới (7 cột)...")
            worksheet.append_row(['Full Time', 'Ngày', 'Tháng', 'Năm', 'Tên món', 'Phân loại', 'Số tiền'])
            logger.info("✅ Đã tạo header cho Sheet")
        else:
            logger.info(f"✅ Sheet đã có {len(existing_data)} dòng dữ liệu")
            # Kiểm tra header cũ, nếu cần thì cập nhật
            if len(existing_data[0]) < 7:
                logger.warning("⚠️ Header cũ có ít hơn 7 cột, nhưng sẽ tiếp tục ghi dữ liệu mới")
        
        logger.info("=" * 60)
        logger.info("✅ KẾT NỐI GOOGLE SHEETS THÀNH CÔNG!")
        logger.info("=" * 60)
        return worksheet
        
    except Exception as e:
        logger.critical(f"❌ CRITICAL ERROR: {e}")
        raise

worksheet = None
try:
    worksheet = init_google_sheets()
except Exception as e:
    logger.critical("❌ KHÔNG THỂ KHỞI ĐỘNG BOT!")
    raise

# ==================== LƯU VÀO GOOGLE SHEET ====================
def save_expenses_to_sheet(expenses: list) -> list:
    """
    Lưu nhiều chi tiêu vào Google Sheet
    Format: [Full Time, Ngày, Tháng, Năm, Tên món, Phân loại, Số tiền]
    """
    logger.info("=" * 60)
    logger.info("BƯỚC 3: GHI VÀO GOOGLE SHEET")
    logger.info("=" * 60)
    
    if worksheet is None:
        raise ValueError("Google Sheets chưa được khởi tạo")
    
    now = datetime.now()
    full_time = now.strftime('%Y-%m-%d %H:%M:%S')
    day = now.day
    month = now.month
    year = now.year
    
    logger.info(f"⏰ Thời gian: {full_time} ({day}/{month}/{year})")
    
    saved_items = []
    
    try:
        for i, expense in enumerate(expenses, 1):
            item_name = expense.get('item', 'Không xác định')
            amount = expense.get('amount', 0)
            category = expense.get('category', 'Khác')
            
            row = [full_time, day, month, year, item_name, category, amount]
            logger.info(f"💾 Đang ghi món {i}: {item_name} - {amount:,}đ")
            worksheet.append_row(row)
            saved_items.append(expense)
        
        logger.info("=" * 60)
        logger.info(f"✅ Đã ghi thành công {len(saved_items)} món vào Sheet!")
        logger.info("=" * 60)
        
        return saved_items
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi lưu vào Google Sheet: {e}")
        raise


# ==================== TÍNH TOÁN CHI TIÊU TUẦN ====================
def calculate_weekly_spend() -> dict:
    """
    Tính toán chi tiêu tuần hiện tại (Thứ 2 - Chủ Nhật)
    Trả về: {'total': tổng tiền, 'remaining': số dư còn lại, 'percentage': phần trăm đã dùng}
    """
    logger.info("=" * 60)
    logger.info("BƯỚC: TÍNH TOÁN CHI TIÊU TUẦN")
    logger.info("=" * 60)
    
    if worksheet is None:
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
        all_data = worksheet.get_all_values()
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


# ==================== BÁO CÁO CHI TIÊU ====================
def get_expense_report() -> dict:
    """Đọc dữ liệu từ Sheet và tính toán báo cáo"""
    logger.info("=" * 60)
    logger.info("BƯỚC: ĐỌC DỮ LIỆU TỪ SHEET")
    logger.info("=" * 60)
    
    if worksheet is None:
        raise ValueError("Google Sheets chưa được khởi tạo")
    
    try:
        all_data = worksheet.get_all_values()
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


# ==================== HOÀN TÁC (UNDO) ====================
def undo_last_expense() -> dict:
    """
    Xóa dòng cuối cùng có dữ liệu trong Google Sheet
    Trả về thông tin dòng đã xóa hoặc None nếu không có gì để xóa
    """
    logger.info("=" * 60)
    logger.info("BƯỚC: HOÀN TÁC GIAO DỊCH CUỐI")
    logger.info("=" * 60)
    
    if worksheet is None:
        raise ValueError("Google Sheets chưa được khởi tạo")
    
    try:
        all_data = worksheet.get_all_values()
        
        # Kiểm tra nếu Sheet trống hoặc chỉ có header
        if len(all_data) <= 1:
            logger.warning("⚠️ Sheet trống, không có gì để xóa")
            return None
        
        # Lấy dòng cuối cùng (bỏ qua header)
        last_row_index = len(all_data)
        last_row = all_data[-1]
        
        # Kiểm tra xem dòng có dữ liệu không
        if len(last_row) < 7 or not last_row[4]:  # Cột 5 (index 4) là Tên món
            logger.warning("⚠️ Dòng cuối không có dữ liệu hợp lệ")
            return None
        
        # Lấy thông tin dòng sẽ xóa
        deleted_info = {
            'item': last_row[4] if len(last_row) > 4 else 'Không xác định',
            'amount': int(last_row[6]) if len(last_row) > 6 and last_row[6] else 0,
            'category': last_row[5] if len(last_row) > 5 else 'Khác',
            'date': f"{last_row[1]}/{last_row[2]}/{last_row[3]}" if len(last_row) > 3 else 'N/A'
        }
        
        # Xóa dòng cuối cùng
        logger.info(f"🗑️ Đang xóa dòng {last_row_index}: {deleted_info['item']} - {deleted_info['amount']:,}đ")
        worksheet.delete_rows(last_row_index)
        
        logger.info("=" * 60)
        logger.info("✅ Đã xóa giao dịch cuối cùng thành công!")
        logger.info("=" * 60)
        
        return deleted_info
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi xóa giao dịch: {e}")
        raise


def get_wasteful_warning(item_name: str) -> str:
    """
    Kiểm tra xem tên món có chứa từ khóa lãng phí không
    Nếu có, trả về một câu cảnh báo ngẫu nhiên
    """
    item_lower = item_name.lower()
    
    for keyword in WASTEFUL_KEYWORDS:
        if keyword in item_lower:
            import random
            warning = random.choice(WASTEFUL_WARNINGS)
            logger.info(f"⚠️ Phát hiện từ khóa lãng phí: '{keyword}' trong '{item_name}'")
            return warning
    
    return None


# ==================== TELEGRAM HANDLERS ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh /start"""
    logger.info(f"📨 Nhận lệnh /start từ user: {update.effective_user.id}")
    welcome_message = (
        "Chào bạn! 👋\n\n"
        "🤖 **Bot Quản Lý Chi Tiêu Enterprise Edition**\n\n"
        "📝 **Cách sử dụng:**\n"
        "• Gửi một món: `phở 50k`\n"
        "• Gửi nhiều món: `cơm 35k, trà đá 5k, xăng 50k`\n"
        "• Hoặc xuống dòng:\n"
        "  `phở 50k`\n"
        "  `cơm 35k`\n\n"
        "💡 Gõ `/help` để xem hướng dẫn đầy đủ!\n\n"
        "Hỗ trợ: k, ng, nghìn, tr, triệu, d, đ"
    )
    await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN)
    logger.info("✅ Đã gửi welcome message")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh /help - Hiển thị hướng dẫn đầy đủ"""
    logger.info(f"📨 Nhận lệnh /help từ user: {update.effective_user.id}")
    
    help_message = (
        "📚 **HƯỚNG DẪN SỬ DỤNG BOT**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        "📝 **1. THÊM CHI TIÊU**\n"
        "Gửi tin nhắn mô tả chi tiêu:\n"
        "• `phở 50k` - Một món\n"
        "• `cơm 35k, trà đá 5k, xăng 50k` - Nhiều món (phân cách bằng dấu phẩy)\n"
        "• Hoặc xuống dòng:\n"
        "  `phở 50k`\n"
        "  `cơm 35k`\n\n"
        
        "💡 **Định dạng số tiền hỗ trợ:**\n"
        "• `35k`, `50ng`, `30 nghìn` → 35,000đ\n"
        "• `1.5tr`, `2 triệu` → 1,500,000đ\n"
        "• `50000`, `50000đ`, `50000d` → 50,000đ\n\n"
        
        "📊 **2. BÁO CÁO & THỐNG KÊ**\n"
        "• `/report` hoặc `/thongke`\n"
        "  → Xem báo cáo chi tiêu hôm nay, tháng này, top chi tiêu\n\n"
        
        "• `/chart`\n"
        "  → Xem biểu đồ tròn (Donut Chart) chi tiêu tháng này\n"
        "  → Hiển thị tỷ lệ % theo từng phân loại\n\n"
        
        "• `/export`\n"
        "  → Xuất báo cáo Excel tháng này\n"
        "  → File Excel chuyên nghiệp, có format đẹp\n\n"
        
        "🔧 **3. QUẢN LÝ**\n"
        "• `/undo`\n"
        "  → Hoàn tác giao dịch cuối cùng\n"
        "  → Xóa dòng cuối cùng trong Sheet\n\n"
        
        "🔔 **4. BÁO THỨC NHẬP LIỆU**\n"
        "• `/remind 21:30`\n"
        "  → Đặt báo thức nhắc nhở hàng ngày lúc 21:30\n"
        "  → Bot sẽ tự động nhắc bạn tổng kết chi tiêu\n\n"
        
        "• `/stopremind`\n"
        "  → Tắt báo thức nhắc nhở\n\n"
        
        "🧾 **5. MÁY TÍNH CHIA TIỀN**\n"
        "• `/chia 500k 4`\n"
        "  → Chia 500.000đ cho 4 người\n"
        "  → Kết quả: Mỗi người 125.000đ\n\n"
        
        "• `/chia 300k Nam, Hùng, Lộc`\n"
        "  → Chia 300.000đ cho 3 người\n"
        "  → Hiển thị chi tiết từng người\n\n"
        
        "💰 **6. QUẢN LÝ NGÂN SÁCH TUẦN**\n"
        "• Hạn mức: **700,000đ/tuần**\n"
        "• Bot tự động theo dõi và cảnh báo:\n"
        "  → Hiển thị số dư còn lại sau mỗi giao dịch\n"
        "  → Cảnh báo nếu tiêu quá 80% và mới đầu tuần\n"
        "  → Báo động nếu vượt quá hạn mức\n\n"
        
        "🚨 **7. CẢNH SÁT CHI TIÊU**\n"
        "Bot tự động phát hiện và cảnh báo các khoản chi lãng phí:\n"
        "• Game: nạp, skin, gacha, top up...\n"
        "• Đồ uống: trà sữa, toco, mixue...\n"
        "• Giải trí: phim, netflix...\n"
        "• Khác: đồ chơi, mô hình, nhậu...\n\n"
        
        "🏷️ **8. PHÂN LOẠI TỰ ĐỘNG**\n"
        "Bot tự động phân loại dựa trên từ khóa:\n"
        "• **Ăn uống:** phở, cơm, bún, cafe, trà...\n"
        "• **Di chuyển:** xăng, xe, grab, taxi...\n"
        "• **Học tập:** sách, vở, bút, học phí...\n"
        "• **Khác:** Nếu không khớp từ khóa nào\n\n"
        
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 **Mẹo sử dụng:**\n"
        "• Gõ `/help` để xem lại hướng dẫn này\n"
        "• Gõ `/start` để xem lời chào\n"
        "• Bot hoạt động offline, không cần AI\n"
        "• Tất cả dữ liệu được lưu vào Google Sheet\n\n"
        
        "🎯 **Phiên bản: Enterprise Edition**"
    )
    
    await update.message.reply_text(help_message, parse_mode=ParseMode.MARKDOWN)
    logger.info("✅ Đã gửi hướng dẫn cho user")


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh /report hoặc /thongke"""
    logger.info(f"📨 Nhận lệnh /report từ user: {update.effective_user.id}")
    
    try:
        report_data = get_expense_report()
        
        today_total = report_data['today_total']
        month_total = report_data['month_total']
        top_expenses = report_data['top_expenses']
        
        now = datetime.now()
        month_name = now.strftime('%B')
        
        # Tạo message báo cáo
        report_message = f"📊 **BÁO CÁO CHI TIÊU**\n"
        report_message += "━━━━━━━━━━━━━━━━━━\n"
        report_message += f"📅 Hôm nay: **{today_total:,}đ**\n"
        report_message += f"🗓️ Tháng {now.month}: **{month_total:,}đ**\n"
        report_message += "━━━━━━━━━━━━━━━━━━\n"
        
        if top_expenses:
            report_message += "🔥 **Top chi tiêu tháng:**\n"
            for i, (category, amount) in enumerate(top_expenses, 1):
                report_message += f"{i}. {category}: {amount:,}đ\n"
        else:
            report_message += "📝 Chưa có dữ liệu chi tiêu trong tháng này.\n"
        
        await update.message.reply_text(report_message, parse_mode=ParseMode.MARKDOWN)
        logger.info("✅ Đã gửi báo cáo cho user")
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi tạo báo cáo: {e}")
        error_msg = "❌ Đã xảy ra lỗi khi tạo báo cáo. Vui lòng thử lại sau."
        await update.message.reply_text(error_msg)


async def undo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh /undo - Xóa giao dịch cuối cùng"""
    logger.info(f"📨 Nhận lệnh /undo từ user: {update.effective_user.id}")
    
    try:
        deleted_info = undo_last_expense()
        
        if deleted_info is None:
            response = "❌ Không có gì để xóa.\n\nSheet trống hoặc không có giao dịch nào."
        else:
            response = f"✅ **Đã xóa giao dịch cuối cùng thành công!**\n\n"
            response += f"📝 Giao dịch đã xóa:\n"
            response += f"• {deleted_info['item']}: {deleted_info['amount']:,}đ\n"
            response += f"• Phân loại: {deleted_info['category']}\n"
            response += f"• Ngày: {deleted_info['date']}"
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
        logger.info("✅ Đã gửi phản hồi undo cho user")
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi xóa giao dịch: {e}")
        error_msg = "❌ Đã xảy ra lỗi khi xóa giao dịch. Vui lòng thử lại sau."
        await update.message.reply_text(error_msg)


# ==================== BÁO THỨC NHẬP LIỆU ====================
async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh /remind - Đặt báo thức nhắc nhở hàng ngày"""
    logger.info(f"📨 Nhận lệnh /remind từ user: {update.effective_user.id}")
    user_id = str(update.effective_user.id)
    
    try:
        if not context.args or len(context.args) == 0:
            response = (
                "❌ **Sai cú pháp!**\n\n"
                "💡 Cách sử dụng:\n"
                "• `/remind 21:30` - Đặt báo thức lúc 21:30 hàng ngày\n"
                "• `/remind 09:00` - Đặt báo thức lúc 9:00 sáng\n\n"
                "Ví dụ: `/remind 21:30`"
            )
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            return
        
        time_str = context.args[0]
        
        # Parse thời gian (HH:MM)
        try:
            time_parts = time_str.split(':')
            if len(time_parts) != 2:
                raise ValueError("Sai định dạng")
            
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            
            if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                raise ValueError("Giờ không hợp lệ")
            
            # Lưu reminder
            user_reminders[user_id] = {'hour': hour, 'minute': minute}
            save_reminders()
            
            # Lên lịch job
            job_queue = context.application.job_queue
            if job_queue:
                # Xóa job cũ nếu có
                current_jobs = job_queue.get_jobs_by_name(f"reminder_{user_id}")
                for job in current_jobs:
                    job.schedule_removal()
                
                # Tạo job mới - chạy hàng ngày vào giờ đã đặt
                reminder_time = dt_time(hour, minute)
                job_queue.run_daily(
                    send_daily_reminder,
                    time=reminder_time,
                    name=f"reminder_{user_id}",
                    chat_id=update.effective_chat.id
                )
                
                # Lưu chat_id vào reminder data để khôi phục sau khi restart
                user_reminders[user_id]['chat_id'] = update.effective_chat.id
                save_reminders()
            
            response = (
                f"✅ **Đã đặt báo thức thành công!**\n\n"
                f"🔔 Bot sẽ nhắc bạn hàng ngày lúc **{hour:02d}:{minute:02d}**\n\n"
                f"💡 Gõ `/stopremind` để tắt báo thức"
            )
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            logger.info(f"✅ Đã đặt reminder cho user {user_id} lúc {hour:02d}:{minute:02d}")
            
        except (ValueError, IndexError) as e:
            response = (
                "❌ **Sai định dạng giờ!**\n\n"
                "💡 Định dạng đúng: `HH:MM`\n"
                "• Ví dụ: `21:30`, `09:00`, `18:45`\n"
                "• Giờ: 00-23, Phút: 00-59"
            )
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            
    except Exception as e:
        logger.error(f"❌ Lỗi khi đặt reminder: {e}")
        error_msg = "❌ Đã xảy ra lỗi. Vui lòng thử lại sau."
        await update.message.reply_text(error_msg)


async def stopremind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh /stopremind - Tắt báo thức"""
    logger.info(f"📨 Nhận lệnh /stopremind từ user: {update.effective_user.id}")
    user_id = str(update.effective_user.id)
    
    try:
        if user_id in user_reminders:
            # Xóa reminder
            del user_reminders[user_id]
            save_reminders()
            
            # Xóa job
            job_queue = context.application.job_queue
            if job_queue:
                current_jobs = job_queue.get_jobs_by_name(f"reminder_{user_id}")
                for job in current_jobs:
                    job.schedule_removal()
            
            response = "✅ **Đã tắt báo thức nhắc nhở!**\n\n💡 Gõ `/remind [giờ]` để đặt lại"
            logger.info(f"✅ Đã tắt reminder cho user {user_id}")
        else:
            response = "ℹ️ Bạn chưa đặt báo thức nào.\n\n💡 Gõ `/remind [giờ]` để đặt báo thức"
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi tắt reminder: {e}")
        error_msg = "❌ Đã xảy ra lỗi. Vui lòng thử lại sau."
        await update.message.reply_text(error_msg)


async def send_daily_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Gửi tin nhắn nhắc nhở hàng ngày"""
    chat_id = context.job.chat_id
    reminder_message = (
        "🔔 **Nhắc nhở:**\n\n"
        "Đừng quên tổng kết chi tiêu hôm nay nhé! 💸\n\n"
        "💡 Gõ `/report` để xem báo cáo chi tiêu"
    )
    
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=reminder_message,
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"✅ Đã gửi reminder cho chat {chat_id}")
    except Exception as e:
        logger.error(f"❌ Lỗi khi gửi reminder: {e}")


# ==================== MÁY TÍNH CHIA TIỀN ====================
def parse_amount_for_split(text: str) -> int:
    """Parse số tiền từ text (dùng cho bill splitter)"""
    text_lower = text.lower().strip()
    
    patterns = [
        (r'(\d+(?:\.\d+)?)\s*tr(?:iệu)?', 1000000),
        (r'(\d+(?:\.\d+)?)\s*k(?:ilo)?', 1000),
        (r'(\d+(?:\.\d+)?)\s*ng(?:àn)?', 1000),
        (r'(\d+(?:\.\d+)?)\s*nghìn', 1000),
        (r'(\d+(?:\.\d+)?)\s*000', 1),
        (r'(\d+(?:\.\d+)?)\s*d(?:ồng)?', 1),
        (r'(\d+(?:\.\d+)?)\s*đ', 1),
        (r'(\d{4,})', 1),
    ]
    
    for pattern, multiplier in patterns:
        match = re.search(pattern, text_lower)
        if match:
            try:
                number = float(match.group(1))
                return int(number * multiplier)
            except:
                continue
    
    return 0


async def chia_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh /chia - Chia tiền giữa nhiều người"""
    logger.info(f"📨 Nhận lệnh /chia từ user: {update.effective_user.id}")
    
    try:
        if not context.args or len(context.args) < 2:
            response = (
                "❌ **Sai cú pháp!**\n\n"
                "💡 **Cách sử dụng:**\n"
                "• `/chia 500k 4` - Chia 500k cho 4 người\n"
                "• `/chia 300k Nam, Hùng, Lộc` - Chia 300k cho 3 người\n\n"
                "**Ví dụ:**\n"
                "• `/chia 500k 4`\n"
                "• `/chia 1tr Nam, Hùng, Lộc, Mai`"
            )
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            return
        
        # Parse số tiền
        amount_text = context.args[0]
        total_amount = parse_amount_for_split(amount_text)
        
        if total_amount == 0:
            response = (
                "❌ **Không tìm thấy số tiền hợp lệ!**\n\n"
                "💡 Định dạng số tiền:\n"
                "• `500k`, `1tr`, `500000`, `500000đ`"
            )
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            return
        
        # Parse số người hoặc danh sách tên
        remaining_args = ' '.join(context.args[1:])
        
        # Kiểm tra xem có phải là số không
        try:
            num_people = int(remaining_args)
            # Trường hợp 1: Chia cho số người
            if num_people <= 0:
                raise ValueError("Số người phải > 0")
            
            per_person = total_amount // num_people
            remainder = total_amount % num_people
            
            response = f"🧾 **HÓA ĐƠN CHIA TIỀN**\n"
            response += f"💰 Tổng: {total_amount:,}đ\n"
            response += f"👥 Số người: {num_people}\n"
            response += "━━━━━━━━━━━━━━━━━━\n"
            response += f"💵 **Mỗi người: {per_person:,}đ**\n"
            
            if remainder > 0:
                response += f"⚠️ Dư: {remainder:,}đ (có thể để tiền lẻ hoặc ai đó chịu thêm)\n"
            
            response += "━━━━━━━━━━━━━━━━━━\n"
            response += "👉 *Copy đoạn này gửi đòi nợ nhé!*"
            
        except ValueError:
            # Trường hợp 2: Chia theo danh sách tên
            # Tách tên bằng dấu phẩy
            names = [name.strip() for name in remaining_args.split(',')]
            names = [name for name in names if name]  # Loại bỏ tên rỗng
            
            if len(names) == 0:
                response = (
                    "❌ **Không tìm thấy tên người!**\n\n"
                    "💡 Ví dụ:\n"
                    "• `/chia 300k Nam, Hùng, Lộc`\n"
                    "• `/chia 500k An, Bình, Chi, Dung`"
                )
                await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
                return
            
            num_people = len(names)
            per_person = total_amount // num_people
            remainder = total_amount % num_people
            
            response = f"🧾 **HÓA ĐƠN CHIA TIỀN**\n"
            response += f"💰 Tổng: {total_amount:,}đ\n"
            response += f"👥 Số người: {num_people}\n"
            response += "━━━━━━━━━━━━━━━━━━\n"
            
            # Hiển thị từng người
            for i, name in enumerate(names):
                amount_for_person = per_person
                # Người cuối cùng nhận phần dư (nếu có)
                if i == len(names) - 1 and remainder > 0:
                    amount_for_person += remainder
                    response += f"👤 **{name}**: {amount_for_person:,}đ (gồm {remainder:,}đ dư)\n"
                else:
                    response += f"👤 **{name}**: {amount_for_person:,}đ\n"
            
            response += "━━━━━━━━━━━━━━━━━━\n"
            response += "👉 *Copy đoạn này gửi đòi nợ nhé!*"
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
        logger.info(f"✅ Đã tính chia tiền: {total_amount:,}đ cho {num_people} người")
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi chia tiền: {e}", exc_info=True)
        error_msg = "❌ Đã xảy ra lỗi. Vui lòng thử lại sau."
        await update.message.reply_text(error_msg)


# ==================== BIỂU ĐỒ TRỰC QUAN ====================
def get_monthly_data() -> pd.DataFrame:
    """Đọc dữ liệu tháng hiện tại từ Sheet và trả về DataFrame"""
    logger.info("=" * 60)
    logger.info("BƯỚC: ĐỌC DỮ LIỆU THÁNG HIỆN TẠI")
    logger.info("=" * 60)
    
    if worksheet is None:
        raise ValueError("Google Sheets chưa được khởi tạo")
    
    try:
        all_data = worksheet.get_all_values()
        if len(all_data) <= 1:  # Chỉ có header
            return pd.DataFrame()
        
        data_rows = all_data[1:]
        now = datetime.now()
        current_month = now.month
        current_year = now.year
        
        # Lọc dữ liệu tháng này
        monthly_data = []
        for row in data_rows:
            if len(row) < 7:
                continue
            
            try:
                row_day = int(row[1]) if row[1] else 0
                row_month = int(row[2]) if row[2] else 0
                row_year = int(row[3]) if row[3] else 0
                
                if row_month == current_month and row_year == current_year:
                    monthly_data.append({
                        'Full Time': row[0] if len(row) > 0 else '',
                        'Ngày': row_day,
                        'Tháng': row_month,
                        'Năm': row_year,
                        'Tên món': row[4] if len(row) > 4 else 'Không xác định',
                        'Phân loại': row[5] if len(row) > 5 else 'Khác',
                        'Số tiền': int(row[6]) if row[6] else 0
                    })
            except (ValueError, IndexError):
                continue
        
        df = pd.DataFrame(monthly_data)
        logger.info(f"✅ Đã đọc {len(df)} dòng dữ liệu tháng {current_month}/{current_year}")
        return df
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi đọc dữ liệu: {e}")
        raise


async def chart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh /chart - Vẽ biểu đồ tròn chi tiêu"""
    logger.info(f"📨 Nhận lệnh /chart từ user: {update.effective_user.id}")
    
    try:
        # Đọc dữ liệu tháng này
        df = get_monthly_data()
        
        if df.empty:
            response = "❌ Tháng này chưa có dữ liệu chi tiêu.\n\nHãy thêm một vài giao dịch trước nhé!"
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            return
        
        # Tính tổng theo phân loại
        category_totals = df.groupby('Phân loại')['Số tiền'].sum().sort_values(ascending=False)
        
        if category_totals.empty:
            response = "❌ Không có dữ liệu để vẽ biểu đồ."
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            return
        
        # Vẽ biểu đồ tròn (Donut Chart)
        logger.info("🎨 Đang vẽ biểu đồ...")
        
        # Cấu hình style
        plt.style.use('default')
        sns.set_palette("pastel")
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Màu pastel đẹp mắt
        colors = ['#FFB6C1', '#87CEEB', '#98FB98', '#F0E68C', '#DDA0DD', '#FFA07A', '#20B2AA']
        
        # Vẽ donut chart
        wedges, texts, autotexts = ax.pie(
            category_totals.values,
            labels=category_totals.index,
            autopct='%1.1f%%',
            startangle=90,
            colors=colors[:len(category_totals)],
            pctdistance=0.85,
            textprops={'fontsize': 12, 'weight': 'bold'}
        )
        
        # Tạo hiệu ứng donut (khoảng trống ở giữa)
        centre_circle = plt.Circle((0, 0), 0.70, fc='white')
        ax.add_artist(centre_circle)
        
        # Thêm thông tin tổng ở giữa
        total_amount = category_totals.sum()
        ax.text(0, 0, f'Tổng:\n{total_amount:,}đ', 
                ha='center', va='center', 
                fontsize=16, weight='bold', color='#333333')
        
        # Tiêu đề
        now = datetime.now()
        ax.set_title(f'Chi Tiêu Tháng {now.month}/{now.year}', 
                    fontsize=18, weight='bold', pad=20)
        
        # Điều chỉnh layout
        plt.tight_layout()
        
        # Lưu vào BytesIO
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        plt.close()  # Đóng figure để giải phóng bộ nhớ
        
        logger.info("✅ Đã tạo biểu đồ thành công")
        
        # Gửi ảnh qua Telegram
        await update.message.reply_photo(
            photo=img_buffer,
            caption=f"📊 **Biểu đồ chi tiêu tháng {now.month}/{now.year}**\n\n"
                   f"💰 Tổng: **{total_amount:,}đ**",
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info("✅ Đã gửi biểu đồ cho user")
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi tạo biểu đồ: {e}", exc_info=True)
        error_msg = "❌ Đã xảy ra lỗi khi tạo biểu đồ. Vui lòng thử lại sau."
        await update.message.reply_text(error_msg)


# ==================== XUẤT BÁO CÁO EXCEL ====================
async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh /export - Xuất báo cáo Excel"""
    logger.info(f"📨 Nhận lệnh /export từ user: {update.effective_user.id}")
    
    try:
        # Đọc dữ liệu tháng này
        df = get_monthly_data()
        
        if df.empty:
            response = "❌ Tháng này chưa có dữ liệu chi tiêu.\n\nHãy thêm một vài giao dịch trước nhé!"
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            return
        
        logger.info("📊 Đang tạo file Excel...")
        
        # Tạo Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = f"Chi Tieu Thang {datetime.now().month}"
        
        # Header style
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=12)
        header_alignment = Alignment(horizontal="center", vertical="center")
        
        # Header
        headers = ['Full Time', 'Ngày', 'Tháng', 'Năm', 'Tên món', 'Phân loại', 'Số tiền']
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num, value=header)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = header_alignment
        
        # Dữ liệu
        for row_num, row_data in enumerate(df.values, 2):
            for col_num, value in enumerate(row_data, 1):
                cell = ws.cell(row=row_num, column=col_num, value=value)
                if col_num == 7:  # Cột Số tiền
                    cell.number_format = '#,##0'
                    cell.alignment = Alignment(horizontal="right")
                else:
                    cell.alignment = Alignment(horizontal="left")
        
        # Điều chỉnh độ rộng cột
        column_widths = [20, 8, 8, 8, 25, 15, 15]
        for col_num, width in enumerate(column_widths, 1):
            ws.column_dimensions[get_column_letter(col_num)].width = width
        
        # Thêm dòng tổng
        total_row = len(df) + 3
        ws.cell(row=total_row, column=5, value="TỔNG CỘNG:").font = Font(bold=True)
        ws.cell(row=total_row, column=7, value=df['Số tiền'].sum())
        ws.cell(row=total_row, column=7).number_format = '#,##0'
        ws.cell(row=total_row, column=7).font = Font(bold=True)
        ws.cell(row=total_row, column=7).alignment = Alignment(horizontal="right")
        
        # Lưu vào BytesIO
        excel_buffer = io.BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        
        logger.info("✅ Đã tạo file Excel thành công")
        
        # Tên file
        now = datetime.now()
        filename = f"BaoCaoChiTieu_{now.month}_{now.year}.xlsx"
        
        # Gửi file qua Telegram
        await update.message.reply_document(
            document=excel_buffer,
            filename=filename,
            caption=f"📊 **Báo cáo chi tiêu tháng {now.month}/{now.year}**\n\n"
                   f"📝 Tổng số giao dịch: {len(df)}\n"
                   f"💰 Tổng tiền: **{df['Số tiền'].sum():,}đ**",
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info("✅ Đã gửi file Excel cho user")
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi xuất Excel: {e}", exc_info=True)
        error_msg = "❌ Đã xảy ra lỗi khi xuất báo cáo. Vui lòng thử lại sau."
        await update.message.reply_text(error_msg)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý tin nhắn từ user - Multi-Line Parsing"""
    user_text = update.message.text
    user_id = update.effective_user.id
    
    logger.info("=" * 60)
    logger.info("📨 NHẬN TIN NHẮN MỚI")
    logger.info("=" * 60)
    logger.info(f"👤 User ID: {user_id}")
    logger.info(f"💬 Tin nhắn: '{user_text}'")
    logger.info("-" * 60)
    
    try:
        # Parse nhiều món
        expenses = parse_multiple_items(user_text)
        
        # Lưu vào Sheet
        saved_expenses = save_expenses_to_sheet(expenses)
        
        # Tính toán chi tiêu tuần
        weekly_data = calculate_weekly_spend()
        week_total = weekly_data['total']
        remaining = weekly_data['remaining']
        percentage = weekly_data['percentage']
        current_weekday = datetime.now().weekday()  # 0=Monday, 6=Sunday
        
        # Tạo phản hồi đẹp
        if len(saved_expenses) == 1:
            expense = saved_expenses[0]
            response = f"✅ **Đã lưu:**\n"
            response += f"• {expense['item']}: {expense['amount']:,}đ ({expense['category']})"
        else:
            response = f"✅ **Đã lưu {len(saved_expenses)} khoản chi:**\n"
            total = 0
            for expense in saved_expenses:
                response += f"• {expense['item']}: {expense['amount']:,}đ ({expense['category']})\n"
                total += expense['amount']
            response += f"\n💰 **Tổng cộng: {total:,}đ**"
        
        # Thêm thông tin ngân sách tuần
        response += f"\n\n📊 **Tuần này:** {week_total:,}đ / {WEEKLY_LIMIT:,}đ"
        
        if remaining < 0:
            # Đã lố ngân sách
            over_budget = abs(remaining)
            response += f"\n⚠️ **BÁO ĐỘNG:** Bạn đã tiêu lố {over_budget:,}đ so với định mức tuần!"
        else:
            response += f" (Còn dư: {remaining:,}đ)"
        
        # Cảnh báo thông minh: Nếu tiêu quá 80% và mới Thứ 3 hoặc Thứ 4
        if percentage >= 80 and current_weekday <= 3:  # Monday=0, Tuesday=1, Wednesday=2, Thursday=3
            day_names = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ Nhật']
            current_day_name = day_names[current_weekday]
            response += f"\n\n⚠️ **Cảnh báo:** Tiêu chậm thôi, mới {current_day_name} đấy! ({percentage:.1f}% đã dùng)"
        
        # Kiểm tra từ khóa lãng phí và thêm cảnh báo
        for expense in saved_expenses:
            wasteful_warning = get_wasteful_warning(expense['item'])
            if wasteful_warning:
                response += f"\n\n🚨 {wasteful_warning}"
                break  # Chỉ thêm 1 cảnh báo cho mỗi lần lưu
        
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
        logger.info("✅ Đã gửi phản hồi thành công")
        logger.info("=" * 60)
        logger.info("✅ XỬ LÝ TIN NHẮN THÀNH CÔNG!")
        logger.info("=" * 60)
        
    except ValueError as e:
        error_str = str(e)
        logger.warning("=" * 60)
        logger.warning("⚠️ XỬ LÝ TIN NHẮN THẤT BẠI")
        logger.warning(f"📝 Lỗi: {error_str}")
        
        error_msg = (
            "❌ Em không hiểu, vui lòng nhập kiểu:\n"
            "• `Món ăn + số tiền`\n"
            "• `cơm 35k, trà 5k`\n\n"
            "Ví dụ:\n"
            "• `phở 50k`\n"
            "• `xăng 200k`\n"
            "• `cơm 35k, trà đá 5k`"
        )
        await update.message.reply_text(error_msg, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error("❌ XỬ LÝ TIN NHẮN THẤT BẠI (Exception)")
        logger.error(f"📝 Lỗi: {e}")
        logger.error(f"💡 Chi tiết:", exc_info=True)
        
        error_msg = "❌ Đã xảy ra lỗi. Vui lòng thử lại sau."
        await update.message.reply_text(error_msg)


# ==================== HÀM CHÍNH ====================
def main():
    """Hàm chính để khởi chạy bot"""
    # Khởi động Keep Alive server cho Render.com
    keep_alive()
    logger.info("✅ Đã khởi động Keep Alive server (Flask)")
    
    logger.info("=" * 60)
    logger.info("🚀 KHỞI ĐỘNG BOT")
    logger.info("=" * 60)
    
    if worksheet is None:
        logger.critical("❌ CRITICAL ERROR: Không thể khởi động bot!")
        return
    
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    logger.info("✅ Đã tạo Telegram Application")
    
    # Đăng ký handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("huongdan", help_command))  # Alias tiếng Việt
    application.add_handler(CommandHandler("report", report_command))
    application.add_handler(CommandHandler("thongke", report_command))
    application.add_handler(CommandHandler("chart", chart_command))
    application.add_handler(CommandHandler("export", export_command))
    application.add_handler(CommandHandler("undo", undo_command))
    application.add_handler(CommandHandler("remind", remind_command))
    application.add_handler(CommandHandler("stopremind", stopremind_command))
    application.add_handler(CommandHandler("chia", chia_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Khôi phục reminders và lên lịch jobs
    job_queue = application.job_queue
    if job_queue:
        logger.info("🔔 Đang khôi phục reminders...")
        restored_count = 0
        for user_id, reminder_data in user_reminders.items():
            try:
                hour = reminder_data['hour']
                minute = reminder_data['minute']
                chat_id = reminder_data.get('chat_id')
                
                if chat_id:
                    reminder_time = dt_time(hour, minute)
                    job_queue.run_daily(
                        send_daily_reminder,
                        time=reminder_time,
                        name=f"reminder_{user_id}",
                        chat_id=chat_id
                    )
                    restored_count += 1
                    logger.info(f"  ✅ Đã khôi phục reminder cho user {user_id} lúc {hour:02d}:{minute:02d}")
                else:
                    logger.warning(f"  ⚠️ Reminder cho user {user_id} thiếu chat_id - cần đặt lại")
            except Exception as e:
                logger.warning(f"  ⚠️ Không thể khôi phục reminder cho user {user_id}: {e}")
        
        if restored_count > 0:
            logger.info(f"✅ Đã khôi phục {restored_count} reminders")
    logger.info("✅ Đã đăng ký handlers")
    
    logger.info("=" * 60)
    logger.info("✅ BOT ĐÃ SẴN SÀNG!")
    logger.info("=" * 60)
    logger.info(f"📊 Đã kết nối với Google Sheet")
    logger.info("🤖 Bot đang chạy và sẵn sàng nhận tin nhắn...")
    logger.info("💡 Enterprise Edition - Multi-Line, Charts, Excel Export Enabled")
    logger.info("=" * 60)
    
    try:
        application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    except Exception as e:
        error_str = str(e)
        if "Conflict" in error_str or "getUpdates" in error_str:
            logger.critical("=" * 60)
            logger.critical("❌ CRITICAL ERROR: CONFLICT - NHIỀU INSTANCE BOT ĐANG CHẠY!")
            logger.critical("=" * 60)
            logger.critical("💡 GIẢI PHÁP:")
            logger.critical("   1. Dừng TẤT CẢ các terminal đang chạy bot (Ctrl+C)")
            logger.critical("   2. Chạy lại bot: python bot.py")
            logger.critical("=" * 60)
        else:
            logger.critical(f"❌ Lỗi: {e}")
        raise


if __name__ == '__main__':
    main()
