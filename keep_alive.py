"""
Keep Alive Server cho Render.com
Sử dụng Flask để tạo web server đơn giản, giúp bot không bị ngủ trên Render
"""

from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    """Route chính - Render sẽ ping vào đây"""
    return "I am alive"

def run():
    """Chạy Flask server trên port 8080"""
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    """Khởi động Flask server trong thread riêng"""
    t = Thread(target=run)
    t.daemon = True
    t.start()

