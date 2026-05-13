# actions/technical_analysis_action.py
from metagpt.actions import Action
import json
import sys
import os
import re
import pandas as pd
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tools.calculate_SMA_RSI import calculate_sma_rsi 
from tools.fetch_market_data import fetch_ohlcv, OHLCV_DIR # Bổ sung tool lấy OHLCV

from utils.llm_rotator import smart_llm

# ==========================================
# ACTION 1: TÍNH TOÁN CHỈ BÁO KỸ THUẬT (Giữ nguyên của bạn)
# ==========================================
class CalculateTechnicalIndicators(Action):
    name: str = "CalculateTechnicalIndicators"
    description: str = "Sử dụng khi người dùng yêu cầu tính toán các chỉ số kỹ thuật cụ thể như SMA (Simple Moving Average), RSI."
    
    async def run(self, instruction: str) -> str:
        prompt = f"""
        Trích xuất tham số từ yêu cầu sau thành JSON chuẩn: {{"ticker": "MÃ", "sma_window": SỐ, "rsi_window": SỐ}}
        Mặc định: sma_window=20, rsi_window=14.
        CHỈ TRẢ VỀ JSON. Không markdown, không giải thích.
        
        Yêu cầu: {instruction}
        """
        
        try:
            llm_response = await smart_llm.aask(prompt)
            match = re.search(r'\{.*\}', llm_response.replace('\n', ''))
            json_str = match.group(0) if match else llm_response
            params = json.loads(json_str)
            
            ticker = params.get("ticker", "").upper()
            sma_window = int(params.get("sma_window", 20))
            rsi_window = int(params.get("rsi_window", 14))
            
            print(f"\n--> [Action Debug] Trích xuất thành công: Ticker={ticker}, SMA={sma_window}, RSI={rsi_window}")
            
            result_json_str = calculate_sma_rsi(ticker, sma_window, rsi_window)
            return f"Báo cáo phân tích kỹ thuật (SMA, RSI) cho mã {ticker}:\n{result_json_str}"
            
        except json.JSONDecodeError:
            return f"Lỗi Action: LLM không trả về JSON hợp lệ. LLM Output: {llm_response}"
        except Exception as e:
            return f"Lỗi Action: {str(e)}"

# ==========================================
# ACTION 2: THỐNG KÊ DỮ LIỆU GIÁ LỊCH SỬ (OHLCV)
# ==========================================
class GetPriceHistoryAction(Action):
    name: str = "GetPriceHistoryAction"
    # Đưa hẳn từ khóa "giá lịch sử" vào đây
    description: str = "CHỈ sử dụng khi người dùng yêu cầu thống kê DỮ LIỆU GIÁ LỊCH SỬ (giá đóng cửa, mở cửa, cao nhất, thấp nhất, khối lượng) hoặc lọc dữ liệu giao dịch trong một khoảng thời gian."
    
    async def run(self, instruction: str) -> str:
        # 1. Trích xuất tham số bằng JSON
        extract_prompt = f"""
        Phân tích yêu cầu: "{instruction}"
        Trả về DUY NHẤT một chuỗi JSON hợp lệ theo cấu trúc sau:
        {{
            "ticker": "Mã chứng khoán (VD: FPT)",
            "days_lookback": Số ngày lùi lại tính từ hôm nay để lọc dữ liệu (VD: 1 tháng = 30, 3 tháng = 90). Nếu người dùng KHÔNG chỉ định cụ thể thời gian, hãy HIỂU NGẦM là 30 ngày (Giá trị mặc định).
        }}
        """
        try:
            ext_str = await smart_llm.aask(extract_prompt)
            ext_str = re.sub(r'```json\n|\n```|```', '', ext_str).strip()
            params = json.loads(ext_str)
            ticker = params.get("ticker", "").upper()
            days = params.get("days_lookback", 30)
            
            try:
                days = int(days)
            except:
                days = 30
            
            if days <= 0:
                days = 30
                
        except Exception as e:
            return f"Lỗi Action: Không thể hiểu yêu cầu về mã chứng khoán hoặc thời gian. Chi tiết: {e}"
            
        # 2. Tải dữ liệu OHLCV
        file_path = os.path.join(OHLCV_DIR, f"{ticker}.parquet")
        if not os.path.exists(file_path):
            fetch_ohlcv(ticker)
            
        if not os.path.exists(file_path):
            return f"Không có dữ liệu giá giao dịch cho mã {ticker}."
            
        # 3. Xử lý thống kê siêu tốc bằng Pandas
        try:
            df = pd.read_parquet(file_path)
            df['time'] = pd.to_datetime(df['time'])
            
            cutoff_date = datetime.now() - timedelta(days=days)
            df_filtered = df[df['time'] >= cutoff_date]
            
            if df_filtered.empty:
                return f"Không có phiên giao dịch nào cho {ticker} trong {days} ngày qua."
                
            stats = {
                "thoi_gian": f"Từ {df_filtered['time'].min().strftime('%d/%m/%Y')} đến {df_filtered['time'].max().strftime('%d/%m/%Y')}",
                "gia_cao_nhat": float(df_filtered['high'].max()),
                "gia_thap_nhat": float(df_filtered['low'].min()),
                "gia_dong_cua_trung_binh": round(float(df_filtered['close'].mean()), 2),
                "tong_khoi_luong_giao_dich": int(df_filtered['volume'].sum())
            }
        except Exception as e:
            return f"Lỗi xử lý dữ liệu Pandas: {e}"
            
        # 4. Tạo câu trả lời tự nhiên
        ans_prompt = f"""
        Kết quả tính toán dữ liệu giao dịch của mã {ticker}:
        {json.dumps(stats, ensure_ascii=False)}
        
        Dựa vào số liệu trên, hãy trả lời ngắn gọn yêu cầu: "{instruction}". Trình bày các con số thật rõ ràng.
        """
        return await smart_llm.aask(ans_prompt)