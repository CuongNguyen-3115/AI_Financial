import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Thêm đường dẫn gốc vào sys.path để tránh lỗi import
root_path = str(Path(__file__).parent)
if root_path not in sys.path:
    sys.path.append(root_path)

load_dotenv()

from roles.manager_agent import OrchestratorManager
from metagpt.logs import logger

async def run_comprehensive_test():
    # 1. Khởi tạo Nhạc trưởng (Manager Agent)
    # Manager này đã bao gồm: SentimentAgent, QuantAgent, FundamentalAnalyst
    manager = OrchestratorManager()

    # 2. Câu lệnh "Trùm cuối" - Ép hệ thống hoạt động hết công suất
    # Yêu cầu này bao gồm:
    # - Tâm lý (News)
    # - Kỹ thuật (OHLCV, SMA/RSI)
    # - Cơ bản (Hồ sơ DN, Vốn điều lệ)
    # - Chuyên sâu (Đọc PDF từ Vietstock, lấy Target Price)
    # - Tổng hợp (Đưa ra lời khuyên)
    
    complex_request = (
        "Hãy thực hiện một báo cáo tư vấn đầu tư 360 độ CHUYÊN SÂU & CỰC KỲ CHI TIẾT cho mã cổ phiếu FPT. Yêu cầu:\n"
        "1. [Tâm lý thị trường]: Phân tích chi tiết sentiment. Liệt kê rõ các tin tức tích cực/tiêu cực/trung lập ảnh hưởng đến giá.\n"
        "2. [Phân tích Kỹ thuật]: Thống kê CHI TIẾT bảng dữ liệu giá OHLCV theo TỪNG NGÀY trong chuỗi khoảng thời gian thu thập được. Phân tích cụ thể xu hướng của SMA(20), RSI(14) và sự thay đổi vốn điều lệ.\n"
        "3. [Phân tích Cơ bản]: Tóm tắt SÂU báo cáo Vietstock. Trích xuất Mục tiêu giá (Target Price), trình bày cụ thể TỪNG luận điểm đầu tư cốt lõi rành mạch và ĐÁNH GIÁ CÁC RỦI RO tiềm ẩn.\n"
        "4. [Chiến lược]: Đưa ra chiến lược giao dịch cụ thể với các điểm mua/bán chi tiết.\n"
        "5. [Yêu cầu chất lượng]: Trình bày báo cáo theo format chuyên nghiệp, PHẢI dùng bảng biểu (table) cho dữ liệu giá và chỉ báo. Tuyệt đối trình bày RẤT CHI TIẾT mạch lạc (không rút gọn đoạn văn) và đính kèm danh sách Link Nguồn ở cuối cùng."
    )

    print("\n" + "="*80)
    print("BẮT ĐẦU QUY TRÌNH PHÂN TÍCH TỔNG LỰC (360-DEGREE ANALYSIS)")
    print("="*80)
    print(f"\n[USER REQUEST]: {complex_request}\n")

    try:
        # 3. Chạy hệ thốngwhere python
        # Manager sẽ tự lập kế hoạch (Plan) -> Phân phát cho Sub-agents -> Tổng hợp (Reduce)
        result = await manager.run(complex_request)

        # 4. Hiển thị kết quả cuối cùng
        print("\n" + "*"*80)
        print("BÁO CÁO TƯ VẤN ĐẦU TƯ TỔNG HỢP (FINAL REPORT)")
        print("*"*80)
        print(result.content)
        print("*"*80)

    except Exception as e:
        logger.error(f"Lỗi trong quá trình thực thi hệ thống: {e}")

if __name__ == "__main__":
    # Đảm bảo môi trường đã cài đặt đủ thư viện:
    # pip install google-genai pymupdf pymupdf4llm python-dotenv metagpt pandas vnstock
    
    asyncio.run(run_comprehensive_test())