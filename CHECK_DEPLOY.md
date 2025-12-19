# Kiểm tra và Fix Deploy trên Render

## Bước 1: Kiểm tra Logs trên Render

1. Vào Render Dashboard: https://dashboard.render.com
2. Chọn service của bạn
3. Click tab **"Logs"**
4. Kiểm tra:
   - Có dòng `✅ BOT ĐÃ SẴN SÀNG!` không?
   - Có lỗi nào không? (màu đỏ)
   - Commit mới nhất có được deploy không?

## Bước 2: Manual Deploy (Nếu cần)

Nếu Render chưa tự động deploy:

1. Vào tab **"Events"** hoặc **"Manual Deploy"**
2. Click **"Manual Deploy"** → **"Deploy latest commit"**
3. Đợi build (2-5 phút)

## Bước 3: Restart Service

Nếu code đã deploy nhưng bot vẫn chạy code cũ:

1. Vào tab **"Settings"**
2. Scroll xuống phần **"Manual Deploy"**
3. Click **"Restart"** hoặc **"Clear build cache & deploy"**

## Bước 4: Kiểm tra Code đã được Deploy

Trong Logs, tìm các dòng này để xác nhận code mới:

- `💳 Tạo mã QR:` (tính năng QR mới)
- `🔄 Phát hiện yêu cầu tạo QR (Regex Fallback)...` (fallback QR)
- `✅ Groq AI yêu cầu tạo QR:` (AI QR)

## Bước 5: Test Tính Năng Mới

Sau khi deploy xong, test:

1. **Test QR tự nhiên:**
   - Gửi: "tạo mã qr 20k tra no"
   - Bot phải tạo QR code

2. **Test QR command:**
   - Gửi: `/pay 50k test`
   - Bot phải tạo QR code

## Lỗi Thường Gặp

### Lỗi "Module not found":
- Kiểm tra `requirements.txt` có đầy đủ không
- Xem logs build để biết package nào thiếu

### Lỗi "Import Error":
- Kiểm tra `services.py` có được commit không
- Kiểm tra imports trong `bot.py`

### Bot không phản hồi:
- Kiểm tra `BOT_TOKEN` có đúng không
- Kiểm tra logs có lỗi kết nối Telegram không

### QR không hoạt động:
- Kiểm tra logs có dòng `💳 Tạo mã QR:` không
- Kiểm tra `generate_vietqr_url` có được import không






