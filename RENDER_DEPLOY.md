# Hướng dẫn Deploy lên Render

## Bước 1: Chuẩn bị Repository

1. **Khởi tạo Git (nếu chưa có):**
   ```bash
   git init
   git add .
   git commit -m "Initial commit - ExpenseBot Enterprise Edition"
   ```

2. **Tạo repository trên GitHub:**
   - Tạo repo mới trên GitHub
   - Push code lên:
     ```bash
     git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
     git branch -M main
     git push -u origin main
     ```

## Bước 2: Tạo Service trên Render

1. **Đăng nhập Render:**
   - Truy cập: https://render.com
   - Đăng nhập bằng GitHub

2. **Tạo Web Service:**
   - Click "New +" → "Web Service"
   - Connect GitHub repository của bạn
   - Chọn repository

3. **Cấu hình Service:**
   - **Name:** `expensebot` (hoặc tên bạn muốn)
   - **Region:** Singapore (gần Việt Nam nhất)
   - **Branch:** `main`
   - **Root Directory:** (để trống)
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot.py`

## Bước 3: Cấu hình Environment Variables

Thêm các biến môi trường sau trong Render Dashboard:

### Bắt buộc:
```
BOT_TOKEN=your_telegram_bot_token
GOOGLE_SHEET_ID=your_google_sheet_id
GSPREAD_CREDENTIALS_JSON={"type":"service_account",...} (toàn bộ nội dung credentials.json)
GROQ_API_KEY=your_groq_api_key
```

### Tùy chọn (nếu có):
```
API_KEY=your_api_key_for_keep_alive_api
GOOGLE_SEARCH_API_KEY=your_google_search_api_key
GOOGLE_CSE_ID=your_google_cse_id
```

### Cách lấy GSPREAD_CREDENTIALS_JSON:
1. Mở file `credentials.json` trên máy local
2. Copy TOÀN BỘ nội dung (bao gồm cả `{` và `}`)
3. Paste vào biến môi trường `GSPREAD_CREDENTIALS_JSON` trên Render
4. **Lưu ý:** Phải là JSON hợp lệ, không có xuống dòng thừa

## Bước 4: Deploy

1. Click "Create Web Service"
2. Render sẽ tự động:
   - Clone code từ GitHub
   - Cài đặt dependencies từ `requirements.txt`
   - Chạy `python bot.py`
3. Đợi build và deploy hoàn tất (khoảng 2-5 phút)

## Bước 5: Kiểm tra

1. **Kiểm tra Logs:**
   - Vào tab "Logs" trên Render Dashboard
   - Xem log để đảm bảo bot đã khởi động thành công
   - Tìm dòng: `✅ BOT ĐÃ SẴN SÀNG!`

2. **Test Bot:**
   - Mở Telegram
   - Gửi `/start` cho bot
   - Kiểm tra xem bot có phản hồi không

## Troubleshooting

### Bot không chạy:
- Kiểm tra logs trên Render
- Đảm bảo tất cả environment variables đã được set
- Kiểm tra `GSPREAD_CREDENTIALS_JSON` có đúng format JSON không

### Lỗi "Module not found":
- Kiểm tra `requirements.txt` có đầy đủ dependencies
- Xem logs build để biết package nào bị lỗi

### Bot không phản hồi:
- Kiểm tra `BOT_TOKEN` có đúng không
- Xem logs để tìm lỗi kết nối Telegram API

### Keep Alive không hoạt động:
- Render sẽ tự động ping endpoint `/` của Flask
- Kiểm tra logs xem Flask server có chạy không

## Lưu ý quan trọng:

1. **Free Tier:**
   - Render free tier sẽ "ngủ" sau 15 phút không có traffic
   - Bot sẽ tự động "thức dậy" khi có request
   - Keep Alive server giúp bot không bị ngủ

2. **Auto Deploy:**
   - Render tự động deploy khi bạn push code lên GitHub
   - Có thể tắt auto-deploy trong Settings

3. **Environment Variables:**
   - KHÔNG commit file `.env` lên GitHub
   - File `.env` đã có trong `.gitignore`
   - Chỉ set environment variables trên Render Dashboard

4. **Credentials:**
   - File `credentials.json` cũng đã có trong `.gitignore`
   - Sử dụng `GSPREAD_CREDENTIALS_JSON` environment variable thay thế

## Chi phí:

- **Free Tier:** Miễn phí (có giới hạn)
- **Starter Plan:** $7/tháng (không bị ngủ, tốc độ nhanh hơn)

---

**Chúc bạn deploy thành công! 🚀**

