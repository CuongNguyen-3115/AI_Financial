# tools/fetch_report_data.py
import os
import requests
import json
from datetime import datetime

# --- Cấu hình thư mục ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_DIR = os.path.join(BASE_DIR, "data", "financial_reports")
os.makedirs(REPORT_DIR, exist_ok=True)

# Header giả lập trình duyệt để tránh bị chặn
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Referer': 'https://finance.vietstock.vn/'
}

def search_latest_reports(ticker: str, limit: int = 2) -> list:
    """
    Sử dụng API Vietstock để lấy danh sách ReportID của mã chứng khoán.
    """
    # API Search e-docs bạn tìm thấy
    url = f"https://finance.vietstock.vn/search-edocs?query={ticker}&page=1&pageSize={limit}&skip=0&filterTime=all&languageId=1"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") == 0 and "data" in data:
            reports = []
            for item in data["data"]:
                reports.append({
                    "report_id": item.get("ReportID"),
                    "title": item.get("Title"),
                    "source": item.get("SourceCode"),
                    "release_date": item.get("ReleaseDate")
                })
            return reports
        return []
    except Exception as e:
        print(f"[-] Lỗi khi tìm kiếm báo cáo cho {ticker}: {e}")
        return []

def download_vietstock_pdf(report_id: int, ticker: str, source: str, release_date: str) -> str:
    """
    Tải file PDF dựa trên ReportID (Không cần đăng nhập).
    """
    # Đường dẫn tải trực tiếp
    download_url = f"https://finance.vietstock.vn/downloadedoc/{report_id}"
    
    # Chuẩn hóa ngày để đặt tên file
    try:
        date_obj = datetime.strptime(release_date, "%d/%m/%Y")
        date_str = date_obj.strftime("%Y%m%d")
    except:
        date_str = "unknown"
        
    # Đặt tên file theo chuẩn: TICKER_NGUỒN_NGÀY_ID.pdf
    filename = f"{ticker}_{source}_{date_str}_{report_id}.pdf"
    filepath = os.path.join(REPORT_DIR, filename)
    
    if os.path.exists(filepath):
        print(f"[*] Báo cáo {filename} đã tồn tại trong bộ nhớ tạm.")
        return filepath
        
    try:
        # Thực hiện tải file
        response = requests.get(download_url, headers=HEADERS, allow_redirects=True, timeout=20)
        
        # Kiểm tra file hợp lệ (Header hoặc 4 byte đầu của file PDF)
        if response.status_code == 200 and (b'%PDF' in response.content[:100]):
            with open(filepath, 'wb') as f:
                f.write(response.content)
            print(f"[+] Đã tải báo cáo mới: {filename}")
            return filepath
        else:
            print(f"[-] Lỗi: Không thể tải PDF cho ReportID {report_id} (Có thể link đã thay đổi).")
            return ""
            
    except Exception as e:
        print(f"[-] Lỗi trong quá trình tải file {report_id}: {e}")
        return ""

def fetch_and_get_report_path(ticker: str) -> str:
    """
    Hàm tổng hợp để các Action/Agent gọi tới.
    Trả về đường dẫn file PDF mới nhất.
    """
    reports = search_latest_reports(ticker, limit=1)
    if not reports:
        print(f"[!] Không tìm thấy báo cáo nào cho mã {ticker}.")
        return ""
        
    latest = reports[0]
    return download_vietstock_pdf(
        report_id=latest["report_id"],
        ticker=ticker,
        source=latest["source"],
        release_date=latest["release_date"]
    )

# Cập nhật hàm này trong tools/fetch_report_data.py
def fetch_and_get_report_metadata(ticker: str) -> dict:
    reports = search_latest_reports(ticker, limit=1)
    if not reports:
        return None
        
    latest = reports[0]
    pdf_path = download_vietstock_pdf(
        report_id=latest["report_id"],
        ticker=ticker,
        source=latest["source"],
        release_date=latest["release_date"]
    )
    
    # Trả về thêm link để Agent có thông tin trích dẫn
    report_url = f"https://finance.vietstock.vn/bao-cao-phan-tich/{latest['report_id']}/"
    
    return {
        "pdf_path": pdf_path,
        "url": report_url,
        "title": latest["title"],
        "release_date": latest["release_date"],
        "source": latest["source"]
    }

if __name__ == "__main__":
    # Chạy thử nghiệm trực tiếp
    ticker = "FPT"
    path = fetch_and_get_report_path(ticker)
    if path:
        print(f"==> FILE PDF SẴN SÀNG TẠI: {path}")