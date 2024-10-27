from flask import Flask, jsonify, request
import gspread
from google.oauth2.service_account import Credentials
from googletrans import Translator
import threading
import time
import os
import json
from dotenv import load_dotenv

# Tải các biến môi trường từ file .env
load_dotenv()

app = Flask(__name__)

# Lấy thông tin từ biến môi trường
sheet_id = os.getenv("GOOGLE_SHEET_ID")
sheet_name = os.getenv("GOOGLE_SHEET_NAME")


# Biến để kiểm soát trạng thái dịch
is_running = False
credentials = None  # Biến lưu credentials

# Hàm để lưu credentials vào file JSON
def save_credentials_to_file(credentials_data):
    with open("credentials.json", "w") as json_file:
        json.dump(credentials_data, json_file)

# Hàm kết nối đến Google Sheets
def connect_to_gsheet():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
        client = gspread.authorize(creds)

        sheet_url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/edit'
        spreadsheet = client.open_by_url(sheet_url)
        sheet = spreadsheet.worksheet(sheet_name)
        return sheet
    except Exception as e:
        app.logger.error(f"Failed to connect to Google Sheets: {e}")
        return None

# Hàm dịch và cập nhật Google Sheets
def translate_and_update(sheet):
    translator = Translator()
    data = sheet.get_all_records()

    for idx, row in enumerate(data, start=2):  # Bắt đầu từ hàng thứ 2 vì hàng đầu tiên là tiêu đề
        vocab = row.get('Vocabulary')
        mean = row.get('Mean')

        if vocab and not mean:  # Chỉ dịch nếu 'Mean' trống
            translation = translator.translate(vocab, src='en', dest='vi').text
            sheet.update_cell(idx, 2, translation)
            print(f"Translated '{vocab}' to '{translation}'")
            time.sleep(1)  # Để tránh quá tải API

# Vòng lặp để dịch Google Sheets mỗi 3 giây
def translation_loop():
    global is_running
    sheet = connect_to_gsheet()
    
    while is_running and sheet:
        translate_and_update(sheet)
        time.sleep(3)  # Đợi 3 giây trước lần lặp tiếp theo

@app.route('/health/liveness', methods=['GET'])
def liveness():
    # Kiểm tra xem Flask có đang chạy không, trả về trạng thái UP
    return jsonify({"status": "UP"}), 200

# Readiness Check
@app.route('/health/readiness', methods=['GET'])
def readiness():
    # Kiểm tra xem ứng dụng có thể kết nối với Google Sheets không
    sheet = connect_to_gsheet()
    if sheet:
        return jsonify({"status": "READY"}), 200
    else:
        return jsonify({"status": "NOT READY"}), 503
# Endpoint để kiểm tra và lưu credentials JSON
@app.route('/validate-credentials', methods=['POST'])
def validate_credentials():
    print(sheet_id)	
    global credentials
    data = request.get_json()
    credentials = data.get("credentials")
    print(sheet_id)	

    # Lưu credentials vào file JSON và kiểm tra tính hợp lệ
    save_credentials_to_file(credentials)
    sheet = connect_to_gsheet()
    if sheet:
        return jsonify({"success": True, "message": "Credentials are valid and saved."})
    else:
        os.remove("credentials.json")  # Xóa file nếu credentials không hợp lệ
        return jsonify({"success": False, "message": "Invalid credentials. Please try again."})

# Endpoint để bắt đầu quá trình dịch
@app.route('/start-translation', methods=['POST'])
def start_translation():
    global is_running
    if not credentials:
        return jsonify({'success': False, 'message': 'Please enter credentials first.'})
    
    if not is_running:
        is_running = True
        translation_thread = threading.Thread(target=translation_loop)
        translation_thread.start()
        return jsonify({'success': True, 'message': 'Translation started!'})
    else:
        return jsonify({'success': False, 'message': 'Translation is already running.'})

# Endpoint để dừng quá trình dịch
@app.route('/stop-translation', methods=['POST'])
def stop_translation():
    global is_running
    is_running = False
    return jsonify({'success': True, 'message': 'Translation stopped.'})
@app.route('/')
def index():
    return app.send_static_file('index.html')
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
