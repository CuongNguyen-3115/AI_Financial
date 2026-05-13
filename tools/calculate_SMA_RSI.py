import pandas as pd
import numpy as np
import os

def calculate_sma_rsi(ticker: str, sma_window: int = 20, rsi_window: int = 14, start_date: str = None, end_date: str = None) -> str:
    """
    Truy xuất dữ liệu OHLCV từ file parquet và tính toán SMA, RSI.
    Đầu vào khớp với schema: time, ticker, open, high, low, close, volume.
    """
    # Đường dẫn thư mục chứa data
    base_path = r"C:\1. Project\5_Intern\Goline\data\raw_data\ohlcv"
    file_path = os.path.join(base_path, f"{ticker}.parquet")
    
    if not os.path.exists(file_path):
        return f"Error: Data for ticker {ticker} not found."
    
    try:
        # Đọc dữ liệu từ file Parquet
        df = pd.read_parquet(file_path)
        
        # Mapping đúng tên cột từ schema của bạn
        time_col = 'time'
        close_col = 'close'
        
        # Chuyển đổi cột time sang định dạng datetime để sắp xếp và lọc
        df[time_col] = pd.to_datetime(df[time_col])
        df = df.sort_values(by=time_col)
        
        # Tính toán SMA
        df[f'SMA_{sma_window}'] = df[close_col].rolling(window=sma_window).mean()
        
        # Tính toán RSI (Dùng Exponential Moving Average theo công thức chuẩn)
        delta = df[close_col].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.ewm(alpha=1/rsi_window, min_periods=rsi_window, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/rsi_window, min_periods=rsi_window, adjust=False).mean()
        
        rs = avg_gain / avg_loss
        df[f'RSI_{rsi_window}'] = 100 - (100 / (1 + rs))
        
        # Lọc dữ liệu theo khoảng thời gian nếu người dùng yêu cầu
        if start_date:
            df = df[df[time_col] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df[time_col] <= pd.to_datetime(end_date)]
            
        # Nếu không có bộ lọc thời gian, lấy 5 ngày gần nhất để tiết kiệm token cho Agent
        if not start_date and not end_date:
            df = df.tail(5)
            
        # Trích xuất các cột cần thiết cho output
        result_df = df[[time_col, close_col, f'SMA_{sma_window}', f'RSI_{rsi_window}']].copy()
        
        # Format lại cột time thành chuỗi YYYY-MM-DD cho dễ đọc
        result_df[time_col] = result_df[time_col].dt.strftime('%Y-%m-%d')
        
        # Làm tròn các chỉ số kỹ thuật và giá (2 chữ số thập phân)
        result_df = result_df.round(2)
        
        # Trả về chuỗi JSON để Quant Agent có thể parse dễ dàng
        return result_df.to_json(orient="records", force_ascii=False)
        
    except Exception as e:
        return f"Error processing data for {ticker}: {str(e)}"

# Đoạn code để bạn test thử trực tiếp:
# if __name__ == "__main__":
#     print(calculate_sma_rsi("FPT", sma_window=20, rsi_window=14, start_date="2025-09-28", end_date="2025-09-29"))