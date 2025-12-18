# ExpenseBot - Telegram Bot Quản Lý Chi Tiêu Enterprise Edition

Bot Telegram chuyên nghiệp để quản lý chi tiêu, sử dụng Smart Pattern Matching + Groq AI + Google Search.

**Copyright (c) 2025 Lộc - All rights reserved.**

## Tính năng mới: Google Search Integration 🔍

Bot giờ đây có thể trả lời các câu hỏi về dữ liệu thực tế:
- Giá vàng, giá xăng hôm nay
- Thời tiết các thành phố
- Tin tức mới nhất
- Thông tin tổng quát (ai là tổng thống, tỷ giá USD...)

Xem hướng dẫn cấu hình: [GOOGLE_SEARCH_SETUP.md](GOOGLE_SEARCH_SETUP.md)

## Tính năng

- ✅ Kết nối với Telegram Bot API
- ✅ Smart Pattern Matching - Nhận diện số tiền và phân loại tự động
- ✅ Multi-Line Parsing - Xử lý nhiều món trong 1 tin nhắn
- ✅ Tự động phân loại (Ăn uống, Di chuyển, Học tập, Khác)
- ✅ Lưu trữ vào Google Sheets tự động (7 cột)
- ✅ Quản lý ngân sách tuần (700k/tuần)
- ✅ Báo cáo chi tiêu (`/report`)
- ✅ Biểu đồ tròn trực quan (`/chart`)
- ✅ Xuất báo cáo Excel (`/export`)
- ✅ Hoàn tác giao dịch (`/undo`)
- ✅ Cảnh sát chi tiêu - Cảnh báo lãng phí
- ✅ Hướng dẫn đầy đủ (`/help`)

## Cài đặt

### 1. Cài đặt Python

Đảm bảo bạn đã cài đặt Python 3.8 trở lên.

### 2. Cài đặt thư viện

```bash
python -m pip install -r requirements.txt
```

### 3. Cấu hình Telegram Bot Token

**Cách lấy Token:**

1. Mở ứng dụng Telegram và tìm **@BotFather**
2. Gửi lệnh `/newbot` cho BotFather
3. Làm theo hướng dẫn để tạo bot
4. BotFather sẽ trả về một **Token** dạng: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

### 4. Cấu hình Google Sheets

**Bước 1: Tạo Service Account**

1. Truy cập: https://console.cloud.google.com/
2. Tạo project mới hoặc chọn project hiện có
3. Vào **APIs & Services** > **Credentials**
4. Click **Create Credentials** > **Service Account**
5. Đặt tên và tạo service account
6. Vào **Keys** tab > **Add Key** > **Create new key** > Chọn **JSON**
7. Download file JSON và đổi tên thành `credentials.json`
8. Đặt file `credentials.json` vào thư mục dự án

**Bước 2: Tạo Google Sheet và chia sẻ**

1. Tạo Google Sheet mới với tên: **"QuanLyChiTieu"** (hoặc tên bạn muốn)
2. Lấy email của Service Account từ file `credentials.json` (trường `client_email`)
3. Chia sẻ Google Sheet cho email Service Account với quyền **Editor**

**Bước 3: Lấy Sheet ID (Tùy chọn)**

1. Mở Google Sheet
2. Copy Sheet ID từ URL: `https://docs.google.com/spreadsheets/d/[SHEET_ID]/edit`
3. Thêm vào file `.env`: `GOOGLE_SHEET_ID=your_sheet_id_here`

### 5. Cấu hình file `.env`

Tạo hoặc cập nhật file `.env` trong thư mục dự án:

```env
# Telegram Bot Token
BOT_TOKEN=your_telegram_bot_token_here

# Google Sheet Configuration (tùy chọn)
GOOGLE_SHEET_NAME=QuanLyChiTieu
GOOGLE_SHEET_ID=your_sheet_id_here
```

**Lưu ý:** Thay các giá trị `your_*_here` bằng giá trị thật của bạn.

## Chạy Bot

Sau khi đã cấu hình đầy đủ, chạy bot bằng lệnh:

```bash
python bot.py
```

Nếu thấy log: `Bot đang khởi động...` và `Đã kết nối với Google Sheet`, nghĩa là bot đã chạy thành công!

## Sử dụng

### Lệnh cơ bản

- `/start` - Lời chào và hướng dẫn nhanh
- `/help` hoặc `/huongdan` - Xem hướng dẫn đầy đủ
- `/report` hoặc `/thongke` - Xem báo cáo chi tiêu
- `/chart` - Xem biểu đồ tròn chi tiêu tháng này
- `/export` - Xuất báo cáo Excel tháng này
- `/undo` - Hoàn tác giao dịch cuối cùng

### Thêm chi tiêu

Gửi tin nhắn mô tả chi tiêu, ví dụ:
- `phở 50k` - Một món
- `cơm 35k, trà đá 5k, xăng 50k` - Nhiều món (phân cách bằng dấu phẩy)
- Hoặc xuống dòng:
  ```
  phở 50k
  cơm 35k
  ```

### Định dạng số tiền hỗ trợ

- `35k`, `50ng`, `30 nghìn` → 35,000đ
- `1.5tr`, `2 triệu` → 1,500,000đ
- `50000`, `50000đ`, `50000d` → 50,000đ

## Cấu trúc dữ liệu trong Google Sheet

Sheet sẽ có 7 cột:
- **Full Time**: Thời gian đầy đủ (2024-12-18 10:30:00)
- **Ngày**: 18
- **Tháng**: 12
- **Năm**: 2024
- **Tên món**: Tên của khoản chi tiêu
- **Phân loại**: Loại chi tiêu (Ăn uống/Di chuyển/Học tập/Khác)
- **Số tiền**: Số tiền đã chi

## Tính năng nâng cao

### Quản lý Ngân sách Tuần

- Hạn mức: **700,000đ/tuần**
- Bot tự động theo dõi và cảnh báo:
  - Hiển thị số dư còn lại sau mỗi giao dịch
  - Cảnh báo nếu tiêu quá 80% và mới đầu tuần
  - Báo động nếu vượt quá hạn mức

### Cảnh Sát Chi Tiêu

Bot tự động phát hiện và cảnh báo các khoản chi lãng phí:
- Game: nạp, skin, gacha, top up...
- Đồ uống: trà sữa, toco, mixue...
- Giải trí: phim, netflix...
- Khác: đồ chơi, mô hình, nhậu...

### Phân loại Tự động

Bot tự động phân loại dựa trên từ khóa:
- **Ăn uống**: phở, cơm, bún, cafe, trà...
- **Di chuyển**: xăng, xe, grab, taxi...
- **Học tập**: sách, vở, bút, học phí...
- **Khác**: Nếu không khớp từ khóa nào

## Lưu ý

- ⚠️ **KHÔNG** chia sẻ file `credentials.json` và `.env` với ai
- ⚠️ **KHÔNG** commit các file này lên Git (đã có trong `.gitignore`)
- File `credentials.json` phải được đặt trong thư mục dự án
- Đảm bảo Service Account có quyền Editor trên Google Sheet
- Bot hoạt động **hoàn toàn offline**, không cần AI, không tốn chi phí

## Troubleshooting

**Lỗi: "BOT_TOKEN không được tìm thấy"**
- Kiểm tra file `.env` có đúng định dạng không
- Đảm bảo không có dấu ngoặc kép thừa

**Lỗi: "Không tìm thấy file credentials.json"**
- Đảm bảo file `credentials.json` nằm trong thư mục dự án
- Kiểm tra tên file chính xác (không có khoảng trắng)

**Lỗi: "Permission denied" khi ghi vào Sheet**
- Kiểm tra đã chia sẻ Google Sheet cho Service Account chưa
- Đảm bảo Service Account có quyền Editor

**Lỗi: "Conflict: terminated by other getUpdates request"**
- Có nhiều instance bot đang chạy cùng lúc
- Dừng tất cả instance bot cũ (Ctrl+C)
- Chạy lại bot: `python bot.py`

**Bot không phản hồi**
- Kiểm tra bot đang chạy (không tắt terminal)
- Kiểm tra kết nối internet
- Xem log trong terminal để biết lỗi cụ thể

## Phiên bản

**Enterprise Edition** - Phiên bản chuyên nghiệp với đầy đủ tính năng:
- Smart Pattern Matching (không cần AI)
- Multi-Line Parsing
- Quản lý ngân sách tuần
- Biểu đồ trực quan
- Xuất Excel chuyên nghiệp
- Cảnh sát chi tiêu

## Bản quyền

Copyright (c) 2025 Lộc

Tất cả các quyền được bảo lưu. Phần mềm này là tài sản riêng và bảo mật. 
Việc sao chép, sửa đổi, phân phối hoặc sử dụng trái phép phần mềm này, 
qua bất kỳ phương tiện nào, đều bị nghiêm cấm.

Xem file [LICENSE](LICENSE) để biết thêm chi tiết về giấy phép.

---

**Tác giả:** Lộc  
**Năm phát triển:** 2025
