import os
import json
from datetime import datetime
import sys
import pandas as pd
from vnstock import Quote
from vnstock.api.company import Company
from dotenv import load_dotenv
import numpy as np # Đảm bảo đã import numpy ở đầu file

load_dotenv()
# --- Cấu trúc thư mục ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INFO_DIR = os.path.join(BASE_DIR, "data", "raw_data", "company_information")
# --- Cấu trúc thư mục cho OHLCV ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OHLCV_DIR = os.path.join(BASE_DIR, "data", "raw_data", "ohlcv")
os.makedirs(OHLCV_DIR, exist_ok=True)

os.makedirs(INFO_DIR, exist_ok=True)

import numpy as np # Đảm bảo đã import numpy ở đầu file

def save_to_json(data, filepath):
    """Xử lý triệt để NaN, Inf và NaT cho mọi loại dữ liệu"""
    if isinstance(data, pd.DataFrame):
        if data.empty:
            data_to_save = []
        else:
            # Chuyển datetime sang string trước
            for col in data.columns:
                if pd.api.types.is_datetime64_any_dtype(data[col]):
                    data[col] = data[col].dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # BƯỚC QUAN TRỌNG: 
            # 1. replace các giá trị vô cực và không xác định
            # 2. infer_objects để tối ưu kiểu dữ liệu
            # 3. Chuyển thành list dict, lúc này các giá trị NaN của numpy sẽ tự thành None của Python
            data_to_save = data.replace({np.nan: None, np.inf: None, -np.inf: None}).to_dict(orient='records')
            
    elif isinstance(data, dict):
        # Đệ quy xử lý từng phần tử trong dict để đảm bảo không còn NaN
        data_to_save = {
            k: (v if (pd.notnull(v) and not (isinstance(v, float) and np.isinf(v))) else None) 
            for k, v in data.items()
        }
    elif data is None:
        data_to_save = []
    else:
        data_to_save = data

    with open(filepath, 'w', encoding='utf-8') as f:
        # allow_nan=False sẽ bắt Python báo lỗi ngay nếu còn sót NaN thay vì ghi file lỗi
        try:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4, allow_nan=False)
        except ValueError:
            # Nếu vẫn còn sót (do lồng ghép phức tạp), dùng cách thủ công cuối cùng
            clean_json = json.dumps(data_to_save, ignore_nan=True) # Cần thư viện simplejson hoặc xử lý chuỗi
            # Cách đơn giản nhất là ép kiểu tất cả sang string nếu quá khó
            json.dump(json.loads(pd.Series([data_to_save]).to_json(orient='records'))[0], f, ensure_ascii=False, indent=4)
            
def fetch_company_information(ticker: str):
    print(f"[*] Đang lấy dữ liệu cho doanh nghiệp: {ticker}")
    
    # Tạo folder riêng cho ticker (Ví dụ: .../company_information/FPT/)
    ticker_dir = os.path.join(INFO_DIR, ticker)
    os.makedirs(ticker_dir, exist_ok=True)
    
    try:
        # Khởi tạo API từ 2 nguồn
        cp_vci = Company(symbol=ticker, source='VCI')
        cp_kbs = Company(symbol=ticker, source='KBS')
        
        # 1. --- Lấy và lưu các hàm rời rạc từ nguồn VCI ---
        vci_methods = ['affiliate', 'events', 'officers', 'shareholders', 'subsidiaries']
        for method_name in vci_methods:
            try:
                df = getattr(cp_vci, method_name)()
                filepath = os.path.join(ticker_dir, f"company_{method_name}.json")
                save_to_json(df, filepath)
            except Exception as e:
                print(f"  [!] Lỗi khi lấy VCI {method_name} ({ticker}): {e}")

        # 2. --- Lấy và lưu hàm rời rạc từ nguồn KBS ---
        try:
            df_capital = cp_kbs.capital_history()
            filepath = os.path.join(ticker_dir, "company_capital_history.json")
            save_to_json(df_capital, filepath)
        except Exception as e:
            print(f"  [!] Lỗi khi lấy KBS capital_history ({ticker}): {e}")

        # 3. --- Gộp thông tin hàm info() từ VCI và KBS ---
        merged_info = {
            "ticker": ticker,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 3.1 Trích xuất từ VCI
        try:
            df_info_vci = cp_vci.info()
            if df_info_vci is not None and not df_info_vci.empty:
                vci_dict = df_info_vci.iloc[0].to_dict()
                # Dùng get() và fallback cho trường hợp API trả về key dạng camelCase hoặc snake_case
                merged_info["company_profile"] = vci_dict.get("company_profile") or vci_dict.get("companyProfile") or "N/A"
                merged_info["organ_name"] = vci_dict.get("organ_name") or vci_dict.get("organName") or "N/A"
                merged_info["organ_short_name"] = vci_dict.get("organ_short_name") or vci_dict.get("organShortName") or "N/A"
                merged_info["sector"] = vci_dict.get("sector") or vci_dict.get("icbName3") or "N/A"
        except Exception as e:
            print(f"  [!] Lỗi khi lấy VCI info ({ticker}): {e}")

        # 3.2 Trích xuất từ KBS
        try:
            df_info_kbs = cp_kbs.info()
            if df_info_kbs is not None and not df_info_kbs.empty:
                kbs_dict = df_info_kbs.iloc[0].to_dict()
                merged_info["company_type"] = kbs_dict.get("company_type") or kbs_dict.get("companyType") or "N/A"
                merged_info["address"] = kbs_dict.get("address", "N/A")
                merged_info["website"] = kbs_dict.get("website", "N/A")
                merged_info["branches"] = kbs_dict.get("branches", "N/A")
                merged_info["history"] = kbs_dict.get("history", "N/A")
                merged_info["founded_date"] = kbs_dict.get("founded_date") or kbs_dict.get("foundedDate") or "N/A"
                merged_info["listing_date"] = kbs_dict.get("listing_date") or kbs_dict.get("listingDate") or "N/A"
        except Exception as e:
            print(f"  [!] Lỗi khi lấy KBS info ({ticker}): {e}")
            
        # 3.3 Lưu file company_info.json đã gộp
        info_filepath = os.path.join(ticker_dir, "company_info.json")
        with open(info_filepath, 'w', encoding='utf-8') as f:
            json.dump(merged_info, f, ensure_ascii=False, indent=4)

        print(f"[+] Lấy dữ liệu thành công cho: {ticker}")
        return True

    except Exception as e:
        print(f"[!] Lỗi tổng quát quá trình fetch dữ liệu cho {ticker}: {e}")
        return False

# Test thử hàm với mã FPT
if __name__ == "__main__":
    fetch_company_information("FPT")

def fetch_ohlcv(ticker: str, start_date: str = "2021-01-01"):
    """
    Sử dụng hàm history() của lớp Quote từ nguồn VCI để lấy dữ liệu giá
    """
    print(f"[*] Đang lấy dữ liệu OHLCV cho doanh nghiệp: {ticker}")
    try:
        # Khởi tạo API từ nguồn VCI cho lớp Quote
        q = Quote(symbol=ticker, source='VCI')
        end_date = datetime.now().strftime("%Y-%m-%d")
        
        # Gọi hàm lấy lịch sử giá
        df = q.history(start=start_date, end=end_date)
        
        if df is not None and not df.empty:
            # Chuẩn hóa tên cột về chữ thường
            df.columns = [col.lower() for col in df.columns]
            
            # Format lại cột thời gian (xử lý an toàn nếu cột 'time' tồn tại)
            if 'time' in df.columns:
                df['time'] = pd.to_datetime(df['time']).dt.strftime('%Y-%m-%d')
            
            # Bổ sung cột ticker nếu chưa có
            if 'ticker' not in df.columns: 
                df['ticker'] = ticker
            
            # Chỉ lấy các trường quan trọng theo yêu cầu
            required_cols = ['time', 'ticker', 'open', 'high', 'low', 'close', 'volume']
            df = df[[c for c in required_cols if c in df.columns]]
            
            # Lưu file parquet trực tiếp vào folder ohlcv
            path = os.path.join(OHLCV_DIR, f"{ticker}.parquet")
            df.to_parquet(path, index=False)
            
            print(f"[+] Lấy dữ liệu OHLCV thành công cho: {ticker}")
            return True
        else:
            print(f"  [!] Không có dữ liệu OHLCV trả về cho {ticker}")
            return False
            
    except Exception as e:
        print(f"  [!] Lỗi khi lấy dữ liệu OHLCV ({ticker}): {e}")
        return False

# --- Khối chạy thực thi chính ---
if __name__ == "__main__":
    # Hỗ trợ lấy mã từ terminal (Ví dụ: python tools/fetch_market_data.py HPG MSN)
    tickers = sys.argv[1:] if len(sys.argv) > 1 else ["FPT", "VCB", "VNM"]
    
    for t in tickers:
        t = t.upper()
        print(f"\n{'='*40}")
        print(f"--- BẮT ĐẦU TẢI DỮ LIỆU: {t} ---")
        print(f"{'='*40}")
        
        # 1. Gọi hàm fetch_company_information (Đã cập nhật ở block trước)
        info_status = fetch_company_information(t)
        if info_status: 
            print(f"  [+] Info Data: OK")
        else:
            print(f"  [-] Info Data: Failed")
            
        # 2. Gọi hàm fetch_ohlcv
        ohlcv_status = fetch_ohlcv(t)
        if ohlcv_status: 
            print(f"  [+] OHLCV Data: OK")
        else:
            print(f"  [-] OHLCV Data: Failed")
            
        print("-" * 40)

