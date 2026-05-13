# actions/company_info_action.py
import sys
import os
import json
import re
from metagpt.actions import Action

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.llm_rotator import smart_llm
from tools.fetch_market_data import INFO_DIR, fetch_company_information

class GetCompanyInfoAction(Action):
    name: str = "GetCompanyInfoAction"
    # Thêm chữ "hình thành" sau chữ lịch sử, và nghiêm cấm dùng cho dữ liệu giá
    description: str = "CHỈ sử dụng để tra cứu thông tin cơ bản, hồ sơ doanh nghiệp, lịch sử hình thành, hoặc vốn điều lệ. TUYỆT ĐỐI KHÔNG dùng hành động này nếu yêu cầu liên quan đến giá cổ phiếu hay thống kê giao dịch."
    
    async def run(self, instruction: str) -> str:
        # 1. Dùng LLM trích xuất mã chứng khoán từ câu lệnh
        extract_prompt = f"""
        Trích xuất mã chứng khoán từ yêu cầu: "{instruction}". 
        Chỉ trả về 1 từ duy nhất là mã chứng khoán viết hoa (VD: FPT). Nếu không thấy, trả về chữ NULL.
        TUYỆT ĐỐI KHÔNG TRẢ LỜI THÊM BẤT KỲ TỪ NÀO KHÁC BÊN NGOÀI MÃ CHỨNG KHOÁN.
        """
        response = await smart_llm.aask(extract_prompt)
        
        # Tiền xử lý để tránh trường hợp LLM lỡ output cả đoạn văn
        match = re.search(r'\b[A-Z0-9]{3}\b', response.upper())
        ticker = match.group(0) if match else "NULL"
        
        if ticker == "NULL" or not ticker:
            return "Vui lòng cung cấp mã chứng khoán để tôi có thể tra cứu thông tin."
            
        # 2. Kiểm tra và tải dữ liệu bằng Tool
        ticker_dir = os.path.join(INFO_DIR, ticker)
        info_file = os.path.join(ticker_dir, "company_info.json")
        
        if not os.path.exists(info_file):
            success = fetch_company_information(ticker)
            if not success:
                return f"Xin lỗi, tôi không thể tìm thấy dữ liệu thông tin cho mã {ticker}."
                
        # 3. Đọc dữ liệu JSON
        try:
            with open(info_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            return f"Lỗi đọc file dữ liệu của {ticker}: {e}"
            
        # 4. Gửi dữ liệu thô cho LLM để tổng hợp thành câu trả lời tự nhiên
        summary_prompt = f"""
        Bạn là chuyên gia dữ liệu chứng khoán. Dựa vào bộ dữ liệu JSON sau của mã {ticker}:
        {json.dumps(data, ensure_ascii=False)}
        
        Hãy trả lời trực tiếp và đầy đủ yêu cầu sau của người dùng: "{instruction}"
        """
        return await smart_llm.aask(summary_prompt)