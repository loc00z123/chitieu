"""
Flask API Server cho ExpenseBot
Cung cấp API endpoints để truy cập dữ liệu chi tiêu

Copyright (c) 2025 Lộc
All rights reserved.
"""

import os
from flask import Flask, jsonify, request
from threading import Thread
import logging
from dotenv import load_dotenv

# Load biến môi trường
load_dotenv()

# Import services
from services import (
    init_google_sheets,
    get_expenses_data,
    get_report_data,
    get_worksheet
)

app = Flask(__name__)

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# API Key từ biến môi trường
API_KEY = os.getenv('API_KEY', '')


def check_api_key():
    """Middleware để kiểm tra API key"""
    api_key = request.headers.get('x-api-key', '')
    if not API_KEY:
        # Nếu không có API_KEY trong env, cho phép truy cập (development mode)
        logger.warning("⚠️ API_KEY chưa được cấu hình, cho phép truy cập tự do (development mode)")
        return True
    if api_key != API_KEY:
        return False
    return True


@app.route('/')
def home():
    """Route chính - Render sẽ ping vào đây"""
    return "I am alive - ExpenseBot API Server"


@app.route('/api/expenses', methods=['GET'])
def api_expenses():
    """
    API endpoint: GET /api/expenses
    Trả về JSON danh sách chi tiêu hôm nay và tháng này
    """
    # Kiểm tra API key
    if not check_api_key():
        return jsonify({
            'success': False,
            'error': 'Unauthorized: Invalid API key'
        }), 401
    
    try:
        # Đảm bảo worksheet đã được khởi tạo
        get_worksheet()
        
        # Lấy dữ liệu
        data = get_expenses_data()
        
        if data['success']:
            return jsonify(data), 200
        else:
            return jsonify(data), 500
            
    except Exception as e:
        logger.error(f"❌ Lỗi API /api/expenses: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }), 500


@app.route('/api/report', methods=['GET'])
def api_report():
    """
    API endpoint: GET /api/report
    Trả về JSON báo cáo tổng quan (như hàm get_financial_context)
    """
    # Kiểm tra API key
    if not check_api_key():
        return jsonify({
            'success': False,
            'error': 'Unauthorized: Invalid API key'
        }), 401
    
    try:
        # Đảm bảo worksheet đã được khởi tạo
        get_worksheet()
        
        # Lấy dữ liệu
        data = get_report_data()
        
        if data['success']:
            return jsonify(data), 200
        else:
            return jsonify(data), 500
            
    except Exception as e:
        logger.error(f"❌ Lỗi API /api/report: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        ws = get_worksheet()
        if ws is None:
            return jsonify({
                'status': 'error',
                'message': 'Google Sheets not initialized'
            }), 503
        
        return jsonify({
            'status': 'healthy',
            'message': 'API Server is running'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 503


def run():
    """Chạy Flask server trên port 8080"""
    # Tắt cảnh báo development server
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    # Chạy server với debug=False để tắt cảnh báo
    app.run(host='0.0.0.0', port=8080, debug=False)


def keep_alive():
    """Khởi động Flask server trong thread riêng"""
    # Khởi tạo Google Sheets khi start server
    try:
        init_google_sheets()
        logger.info("✅ Đã khởi tạo Google Sheets cho API Server")
    except Exception as e:
        logger.warning(f"⚠️ Không thể khởi tạo Google Sheets: {e}")
        logger.warning("⚠️ API Server vẫn chạy nhưng các endpoint có thể lỗi")
    
    t = Thread(target=run)
    t.daemon = True
    t.start()
    logger.info("✅ Flask API Server đã khởi động trên port 8080")
