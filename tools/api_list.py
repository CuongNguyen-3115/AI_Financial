import json
import os
import pandas as pd

# 1. Import trực tiếp các class từ vnstock.api theo cấu trúc mới (v4.x)
from vnstock.api.company import Company
from vnstock.api.quote import Quote

def save_to_json(data, filename):
    """Hỗ trợ chuyển đổi DataFrame sang Dict và lưu file JSON"""
    if isinstance(data, pd.DataFrame):
        if data.empty:
            data = {"status": "success", "message": "No data returned (empty DataFrame)"}
        else:
            # Chuyển đổi các cột datetime sang string để tránh lỗi serialize JSON
            for col in data.columns:
                if pd.api.types.is_datetime64_any_dtype(data[col]):
                    data[col] = data[col].dt.strftime('%Y-%m-%d %H:%M:%S')
            data = data.to_dict(orient='records')
    elif data is None:
        data = {"status": "success", "message": "No data returned (None)"}
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def run_auto_export_v4(symbol="FPT", source="KBS"):
    print(f"=== Đang khởi tạo API cho mã {symbol} với nguồn {source} ===")
    
    # Tạo thư mục lưu trữ
    output_dir = f"data_{symbol}_{source}_v4"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 2. Khởi tạo các đối tượng API của bản 4.x
    try:
        modules = {
            "company": Company(symbol=symbol, source=source),
            "quote": Quote(symbol=symbol, source=source)
        }
    except Exception as e:
        print(f"Lỗi khởi tạo API: {e}")
        return

    # Quét và gọi tự động các hàm trong từng module
    for module_name, obj in modules.items():
        print(f"\n--- Đang quét module: {module_name.upper()} ---")
        
        # Lấy danh sách các hàm public (không bắt đầu bằng dấu '_')
        methods = [m for m in dir(obj) if callable(getattr(obj, m)) and not m.startswith('_')]
        
        for method_name in methods:
            try:
                method = getattr(obj, method_name)
                
                # Các hàm lịch sử giá thường bắt buộc truyền start/end
                if method_name in ['history', 'ohlcv']:
                    df = method(start='2024-01-01', end='2024-01-30')
                else:
                    df = method()
                
                # Lưu file JSON
                file_path = os.path.join(output_dir, f"{module_name}_{method_name}.json")
                save_to_json(df, file_path)
                print(f"[+] Đã xuất thành công: {file_path}")
                
            except Exception as e:
                print(f"[-] Lỗi hàm {method_name}: {e}")

if __name__ == "__main__":
    # Bạn có thể thử thay đổi source thành 'KBS' hoặc 'FMP' 
    # để xem nguồn nào cung cấp dữ liệu doanh nghiệp (Company) đầy đủ nhất.
    run_auto_export_v4(symbol="FPT", source="KBS")