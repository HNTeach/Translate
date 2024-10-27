import gspread
from google.oauth2.service_account import Credentials
from googletrans import Translator
import time

def connect_to_gsheet(sheet_name):
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file('credentials.json', scopes=scope)
    client = gspread.authorize(creds)
    
    # Thay thế URL bằng URL của Google Sheet của bạn
    sheet_url = 'https://docs.google.com/spreadsheets/d/1tJAczQU7plUsH0ONJyJ7FVhWG9Y9aqqjMLKERtdyu50/edit'
    spreadsheet = client.open_by_url(sheet_url)
    
    # Mở sheet theo tên
    sheet = spreadsheet.worksheet(sheet_name)
    return sheet

def translate_and_update(sheet):
    translator = Translator()
    data = sheet.get_all_records()

    for idx, row in enumerate(data, start=2):  # Bắt đầu từ hàng thứ 2 vì hàng đầu tiên là tiêu đề
        vocab = row.get('Vocabulary')
        mean = row.get('Mean')

        if vocab and not mean:  # Chỉ dịch nếu 'Mean' trống
            translation = translator.translate(vocab, src='en', dest='vi').text
            sheet.update_cell(idx, 2, translation)  # idx là hàng, 2 là cột 'Mean'
            print(f"Translated '{vocab}' to '{translation}'")
            time.sleep(1)  # Để tránh quá tải API

if __name__ == '__main__':
    sheet_name = 'Translate'  # Thay thế bằng tên sheet cụ thể
    sheet = connect_to_gsheet(sheet_name)
    
    # Vòng lặp để chạy mã mỗi 3 giây
    while True:
        try:
            translate_and_update(sheet)
            time.sleep(2)  # Đợi 3 giây trước lần lặp tiếp theo
        except Exception as e:
            print(f"Lỗi xảy ra: {e}")
            time.sleep(2)  # Đợi 3 giây trước khi thử lại
