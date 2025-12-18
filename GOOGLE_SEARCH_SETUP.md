# Hướng dẫn cấu hình Google Search API

## Bước 1: Tạo Google Custom Search Engine (CSE)

1. Truy cập: https://programmablesearchengine.google.com/controlpanel/create
2. Điền thông tin:
   - **Tên:** ExpenseBot Search (hoặc tên bạn muốn)
   - **Mô tả:** Search engine cho ExpenseBot
   - **Sites to search:** Để trống hoặc nhập `*` để tìm kiếm toàn bộ web
3. Click **Create**

## Bước 2: Lấy CSE ID

1. Sau khi tạo xong, vào trang quản lý: https://programmablesearchengine.google.com/controlpanel/all
2. Click vào Search Engine vừa tạo
3. Trong phần **Setup**, bạn sẽ thấy **Search engine ID** (CSE ID)
4. Copy CSE ID này (dạng: `012345678901234567890:abcdefghijk`)

## Bước 3: Tạo Google Cloud API Key

1. Truy cập: https://console.cloud.google.com/
2. Tạo project mới hoặc chọn project hiện có
3. Vào **APIs & Services** > **Library**
4. Tìm và bật **Custom Search API**
5. Vào **APIs & Services** > **Credentials**
6. Click **Create Credentials** > **API Key**
7. Copy API Key này

## Bước 4: Cấu hình trong file `.env`

Thêm 2 dòng sau vào file `.env`:

```env
GOOGLE_SEARCH_API_KEY=your_api_key_here
GOOGLE_CSE_ID=your_cse_id_here
```

**Lưu ý:**
- Thay `your_api_key_here` bằng API Key bạn vừa lấy
- Thay `your_cse_id_here` bằng CSE ID bạn vừa lấy
- Không có dấu ngoặc kép, không có khoảng trắng thừa

## Bước 5: Cài đặt thư viện

Chạy lệnh:

```bash
python -m pip install google-api-python-client>=2.100.0
```

Hoặc cài đặt tất cả dependencies:

```bash
python -m pip install -r requirements.txt
```

## Kiểm tra

Sau khi cấu hình xong, khởi động lại bot và thử hỏi:
- "Giá vàng hôm nay"
- "Thời tiết Hà Nội"
- "Ai là tổng thống Mỹ"

Bot sẽ tự động tìm kiếm và trả lời dựa trên kết quả Google Search!

## Giới hạn

- Google Custom Search API miễn phí cho phép **100 requests/ngày**
- Nếu vượt quá, bạn sẽ nhận thông báo lỗi quota
- Có thể nâng cấp lên gói trả phí nếu cần nhiều hơn

## Troubleshooting

**Lỗi: "Google Search API key không hợp lệ"**
- Kiểm tra lại API Key trong `.env`
- Đảm bảo đã bật **Custom Search API** trong Google Cloud Console

**Lỗi: "CSE ID không hợp lệ"**
- Kiểm tra lại CSE ID trong `.env`
- Đảm bảo Search Engine đã được tạo và kích hoạt

**Lỗi: "Quota exceeded"**
- Bạn đã dùng hết 100 requests miễn phí trong ngày
- Đợi đến ngày hôm sau hoặc nâng cấp gói

