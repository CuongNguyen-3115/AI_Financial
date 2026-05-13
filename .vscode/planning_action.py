# actions/planning_action.py
import json
import re
from metagpt.actions import Action
from metagpt.logs import logger
from utils.llm_rotator import smart_llm

class CreateExecutionPlan(Action):
    name: str = "CreateExecutionPlan"
    description: str = "Phân tích yêu cầu người dùng và lập kế hoạch phối hợp giữa SentimentAgent, QuantAgent và FundamentalAnalyst."

    async def run(self, instruction: str) -> list:
        prompt = f"""
        Bạn là một Quản lý hệ thống AI (Orchestrator) chuyên nghiệp trong lĩnh vực tài chính. 
        Nhiệm vụ của bạn là phân tích yêu cầu của người dùng và chia nhỏ nó thành các bước thực thi tuần tự.

        Bạn đang quản lý đội ngũ gồm 3 Sub-agents chuyên biệt:
        1. "SentimentAgent": Chuyên gia xử lý tin tức, đánh giá tâm lý thị trường (Tích cực/Tiêu cực) và trích xuất khoảng thời gian (timeframe) mà tin tức đó đề cập.
        2. "QuantAgent": Chuyên gia về dữ liệu số. Tra cứu thông tin doanh nghiệp (vốn điều lệ, lĩnh vực), truy xuất dữ liệu giá lịch sử (OHLCV) và tính toán các chỉ báo kỹ thuật (SMA, RSI).
        3. "FundamentalAnalyst": Chuyên gia phân tích chuyên sâu. Đọc các báo cáo phân tích PDF từ các công ty chứng khoán để trích xuất giá mục tiêu (Target Price), luận điểm đầu tư và các rủi ro cốt lõi.
        4. "InvestmentAdvisor": Chuyên gia tư vấn đầu tư. Tổng hợp tất cả các phân tích để đưa ra khuyến nghị cuối cùng (MUA/BÁN/GIỮ) và chiến lược hành động.

        Yêu cầu của người dùng: "{instruction}"

        HƯỚNG DẪN LẬP KẾ HOẠCH:
        - Phân tích kỹ yêu cầu để xác định mã cổ phiếu chính (ticker).
        - CHIA NHỎ CÁC CÔNG VIỆC CỦA QUANT AGENT: Nếu yêu cầu vừa có Thống kê giá OHLCV, vừa có Tính SMA/RSI, vừa có Lấy Hồ sơ công ty/Vốn điều lệ, BẮT BUỘC phải tách ra thành 3 bước (task) RIÊNG BIỆT cho QuantAgent.
        - LUÔN LUÔN để "InvestmentAdvisor" là bước cuối cùng với nhiệm vụ "Tổng hợp tất cả các phân tích và đưa ra khuyến nghị đầu tư cuối cùng."
        - Nếu một bước cần dữ liệu từ bước trước, hãy ghi chú rõ trong phần "task".

        HÃY TRẢ VỀ DUY NHẤT MỘT MẢNG JSON các bước. Mỗi bước gồm 3 trường:
        - "agent": Tên Agent (chỉ chọn: "SentimentAgent", "QuantAgent", "FundamentalAnalyst", hoặc "InvestmentAdvisor").
        - "task": Chỉ thị công việc chi tiết cho agent.
        - "ticker": Mã cổ phiếu được đề cập trong yêu cầu (VD: "FPT"). Nếu không có, để là null.

        Mẫu JSON trả về (Ví dụ cho yêu cầu đầy đủ):
        [
            {{"agent": "SentimentAgent", "task": "Phân tích tâm lý tin tức trong 1 tháng qua", "ticker": "FPT"}},
            {{"agent": "QuantAgent", "task": "Tra cứu hồ sơ doanh nghiệp, vốn điều lệ", "ticker": "FPT"}},
            {{"agent": "QuantAgent", "task": "Thống kê giá cổ phiếu OHLCV", "ticker": "FPT"}},
            {{"agent": "QuantAgent", "task": "Tính toán chỉ báo kỹ thuật SMA, RSI", "ticker": "FPT"}},
            {{"agent": "FundamentalAnalyst", "task": "Tóm tắt báo cáo phân tích tài chính mới nhất và lấy giá mục tiêu", "ticker": "FPT"}},
            {{"agent": "InvestmentAdvisor", "task": "Tổng hợp tất cả các phân tích và đưa ra khuyến nghị đầu tư cuối cùng.", "ticker": "FPT"}}
        ]
        """
        
        try:
            # 1. Gọi LLM để lập kế hoạch
            response = await smart_llm.aask(prompt)
            
            # 2. Làm sạch kết quả và bóc tách mảng JSON bằng Regex
            # Loại bỏ các ký tự xuống dòng và khoảng trắng thừa để tránh lỗi parse
            clean_response = response.replace('\n', ' ').strip()
            match = re.search(r'\[\s*\{.*\}\s*\]', clean_response, re.DOTALL)
            
            if match:
                json_str = match.group(0)
                plan = json.loads(json_str)
            else:
                # Nếu không tìm thấy cấu trúc mảng, thử parse trực tiếp response
                plan = json.loads(response)
                
            logger.info(f"[PLANNING] Kế hoạch đã lập: {len(plan)} bước.")
            return plan

        except Exception as e:
            logger.error(f"[Planning Error] Lỗi khi lập kế hoạch hoặc parse JSON: {e}")
            # Fallback an toàn: Nếu lỗi, giao cho QuantAgent xử lý yêu cầu gốc
            return [{"agent": "QuantAgent", "task": instruction}]
        