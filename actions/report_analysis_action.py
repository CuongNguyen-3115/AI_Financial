# actions/report_analysis_action.py
import sys
import os
import json
import re
import asyncio
from pathlib import Path

from matplotlib import ticker
from metagpt.actions import Action
from metagpt.logs import logger

# Import các tools đã xây dựngfetch_and_get_report_metadata, 
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tools.fetch_report_data import fetch_and_get_report_metadata, fetch_and_get_report_path
from tools.report_processor import process_report_for_llm
from utils.llm_rotator import smart_llm # Import bộ xoay vòng

class AnalyzeFinancialReport(Action):
    name: str = "AnalyzeFinancialReport"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ngưỡng an toàn cho mỗi chunk (để tránh lỗi 6000 TPM của Groq)
        self.token_limit_per_chunk = 2500 

    def _estimate_tokens(self, text: str) -> int:
        """Ước lượng số token dựa trên độ dài ký tự"""
        return len(text) // 4

    async def run(self, instruction: str) -> str:
        # 1. Trích xuất mã chứng khoán một cách chặt chẽ
        extract_prompt = f"""
        Từ yêu cầu sau, hãy trích xuất DUY NHẤT mã cổ phiếu (viết hoa, 3 chữ cái).
        Ví dụ: "Mã cổ phiếu: FPT. Nhiệm vụ: Tóm tắt báo cáo..." -> "FPT"
        Yêu cầu: "{instruction}"
        """
        ticker = await smart_llm.aask(extract_prompt)
        ticker = ticker.strip().upper()

        if not re.match(r'^[A-Z]{3}$', ticker):
            return f"Lỗi trích xuất mã cổ phiếu từ chỉ thị: '{instruction}'"
        
        logger.info(f"[FUNDAMENTAL ACTION] Đã xác định mã cổ phiếu là: {ticker}")

        # 2. Tải PDF, lấy metadata và chuyển đổi sang Markdown
        report_info = fetch_and_get_report_metadata(ticker)
        if not report_info or not report_info.get("pdf_path"):
            return f"Không tìm thấy báo cáo hoặc metadata cho mã {ticker}."
        
        pdf_path = report_info["pdf_path"]
        release_date = report_info.get("release_date", "không xác định") # Lấy ngày phát hành
        report_url = report_info.get("url", "")
        report_title = report_info.get("title", "Báo cáo phân tích")

        chunks = process_report_for_llm(pdf_path)
        if not chunks:
            return "Lỗi trong quá trình xử lý nội dung báo cáo."

        # 3. Lập kế hoạch phân phối (Map Phase)
        execution_plan = self._create_swarm_plan(chunks)
        logger.info(f"[SWARM] Đã lập kế hoạch phân phối {len(execution_plan)} nhiệm vụ cho các Model.")

        # 4. Thực thi song song (Async Map)
        tasks = [self._worker_summarize(item['content'], item['model_id'], item['provider']) 
                 for item in execution_plan]
        
        summaries = await asyncio.gather(*tasks)

        # 5. Tổng hợp (Reduce Phase)
        final_report = await self._master_reduce(ticker, summaries, release_date, report_url, report_title)
        return final_report

    def _create_swarm_plan(self, chunks: list) -> list:
        """
        Phân phối động các mảnh Markdown cho danh sách Model trong .env
        """
        # Danh sách model chiến lược từ .env của bạn
        models = [
            {"id": os.getenv("MODEL_ID_1"), "provider": "gemini"},
            {"id": os.getenv("GROQ_MODEL_ID_1"), "provider": "groq"},
            {"id": os.getenv("GITHUB_MODEL_ID_3"), "provider": "github"},
            {"id": os.getenv("HF_MODEL_ID_5"), "provider": "huggingface"},
            {"id": os.getenv("MODEL_ID_5"), "provider": "gemini"},
            {"id": os.getenv("GROQ_MODEL_ID_6"), "provider": "groq"}
        ]
        
        plan = []
        for i, chunk in enumerate(chunks):
            # Chọn model xoay vòng (Round-robin)
            model_info = models[i % len(models)]
            plan.append({
                "content": chunk,
                "model_id": model_info["id"],
                "provider": model_info["provider"]
            })
        return plan

    async def _worker_summarize(self, content: str, model_id: str, provider: str) -> str:
        """Nhiệm vụ của các Worker: Tóm tắt mảnh nhỏ"""
        prompt = f"""
        Bạn là trợ lý phân tích tài chính. Hãy tóm tắt các ý chính và số liệu quan trọng nhất 
        trong đoạn văn bản báo cáo sau. Chú ý các con số về tăng trưởng, doanh thu, lợi nhuận và giá mục tiêu.
        
        Nội dung:
        {content}
        
        Yêu cầu: Trả về kết quả ngắn gọn, súc tích dưới dạng gạch đầu dòng.
        """
        # Sử dụng model cụ thể từ .env
        # Lưu ý: Trong MetaGPT thực tế, bạn cần config LLM instance cho từng model_id
        # Ở đây ta sử dụng _aask của Action hiện tại (tạm thời dùng model chính của Agent)
        # Để tối ưu, bạn nên khởi tạo các LLM instance riêng cho từng provider.
        return await smart_llm.aask(prompt)

    async def _master_reduce(self, ticker: str, summaries: list, release_date: str, report_url: str, report_title: str) -> str:
        """Nhiệm vụ của Master: Tổng hợp các tóm tắt thành một báo cáo phân tích cơ bản duy nhất."""
        combined_summaries = "\n".join(summaries)
        
        # Sử dụng Model mạnh nhất (Tier 1) để Reduce
        master_model = os.getenv("GITHUB_MODEL_ID_1", "gpt-4o")
        
        reduce_prompt = f"""
        Bạn là một Chuyên gia Phân tích Cơ bản. Dựa vào các tóm tắt chi tiết dưới đây về mã {ticker} từ báo cáo ngày {release_date}, 
        hãy viết một bản tóm tắt phân tích tài chính chuyên nghiệp.
        
        Dữ liệu tóm tắt:
        {combined_summaries}
        
        YÊU CẦU BÁO CÁO TÓM TẮT PHẢI CÓ:
        1. Giá mục tiêu (Target Price).
        2. Luận điểm đầu tư chính (Top 3).
        3. Các rủi ro tiềm tàng.
        
        LƯU Ý QUAN TRỌNG: Nhiệm vụ của bạn chỉ là tóm tắt báo cáo phân tích cơ bản. KHÔNG đưa ra khuyến nghị MUA/BÁN/GIỮ cuối cùng. Việc đó sẽ do Chuyên gia Tư vấn Đầu tư quyết định ở bước sau.
        Cuối báo cáo tóm tắt, BẮT BUỘC liệt kê Nguồn báo cáo theo cấu trúc Markdown sau:
        **Nguồn báo cáo gốc:** [{report_title}]({report_url})
        
        Định dạng kết quả trả về: Markdown chuyên nghiệp.
        """
        # Gọi Master Model
        return await smart_llm.aask(reduce_prompt)