# actions/news_analysis_action.py
import sys
import os
import json
import re
from metagpt.actions import Action

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tools.fetch_news_data import get_latest_news 
from utils.llm_rotator import smart_llm # Import bộ xoay vòng

class AnalyzeNewsSentiment(Action):
    name: str = "AnalyzeNewsSentiment"
    
    async def run(self, instruction: str) -> str:
        """
        Phân tích yêu cầu, lấy tin tức và sử dụng LLM để đánh giá sentiment trả về dạng JSON.
        """
        # ---------------------------------------------------------
        # BƯỚC 1: Trích xuất tham số từ câu lệnh của người dùng
        # ---------------------------------------------------------
        extract_prompt = f"""
        Bạn là hệ thống trích xuất thông số dữ liệu. Đọc yêu cầu sau: "{instruction}"
        Hãy trả về MỘT CHUỖI JSON DUY NHẤT chứa các thông tin sau (Không kèm markdown, không giải thích):
        {{
            "ticker": "Mã cổ phiếu (ví dụ: FPT). Nếu không chắc chắn, trả về null",
            "ticker_limit": 10,
            "market_limit": 5
        }}
        Lưu ý: Nếu người dùng không chỉ định số lượng tin (limit), hãy mặc định lấy ticker_limit=10 và market_limit=5 để luôn có dữ liệu.
        """
        
        extracted_str = await smart_llm.aask(extract_prompt)
        # Làm sạch chuỗi JSON (Đề phòng LLM bọc kết quả trong markdown ```json ```)
        extracted_str = re.sub(r'```json\n|\n```|```', '', extracted_str).strip()
        
        try:
            params = json.loads(extracted_str)
        except json.JSONDecodeError:
            # Fallback an toàn nếu LLM trả về lỗi định dạng
            params = {"ticker": None, "ticker_limit": 10, "market_limit": 5}

        # ---------------------------------------------------------
        # BƯỚC 2: Gọi Tool Fetch Data
        # ---------------------------------------------------------
        ticker = params.get("ticker")
        if ticker in ["null", "None", "NULL", ""]:
            ticker = None
            
        try:
            ticker_limit = int(params.get("ticker_limit", 10))
        except:
            ticker_limit = 10
            
        try:
            market_limit = int(params.get("market_limit", 5))
        except:
            market_limit = 5
        
        # Đảm bảo luôn lấy ít nhất vài tin tức nếu limit là 0
        if ticker_limit == 0: ticker_limit = 10
        if market_limit == 0: market_limit = 5

        all_news = []
        # Lấy tin cổ phiếu
        if ticker:
            all_news.extend(get_latest_news(ticker, ticker_limit))
        # Lấy tin thị trường
        all_news.extend(get_latest_news(None, market_limit))
            
        if not all_news:
            return json.dumps({
                "error": f"Không tìm thấy dữ liệu tin tức phù hợp với yêu cầu."
            }, ensure_ascii=False)
        
        # Format dữ liệu để đưa vào Prompt (Loại bỏ link để tiết kiệm token)
        news_text = ""
        reference_links = []
        
        for i, news in enumerate(all_news, 1):
            news_text += f"[{i}] Ngày: {news.get('date')} | Nguồn/Mã: {news.get('ticker')} | Tiêu đề: {news.get('title')} | Tóm tắt: {news.get('summary')}\n"
            if news.get('link'):
                reference_links.append(news.get('link'))
        
        # ---------------------------------------------------------
        # BƯỚC 3: Đánh giá Sentiment và Format Output thành JSON
        # ---------------------------------------------------------
        eval_prompt = f"""
        Bạn là chuyên gia phân tích tài chính định lượng.
        Dựa vào các tin tức mới nhất dưới đây, hãy đánh giá tâm lý thị trường (sentiment).
        
        Tin tức:
        {news_text}
        
        YÊU CẦU ĐẦU RA (OUTPUT FORMAT):
        Trả về DUY NHẤT một chuỗi JSON hợp lệ theo đúng cấu trúc sau (không kèm markdown, không giải thích):
        {{
            "sentiment_score": [Điểm từ 1 đến 10. 1 = Cực kỳ tiêu cực, 10 = Cực kỳ tích cực],
            "sentiment_label": "[Tích cực / Tiêu cực / Trung lập]",
            "sentiment_text": "Đoạn văn ngắn tổng hợp đánh giá và gạch đầu dòng 3 luận điểm chính.",
            "timeframe_analyzed": {{
                "start": "YYYY-MM-DD", 
                "end": "YYYY-MM-DD"
            }}
        }}
        Lưu ý: timeframe_analyzed là khoảng thời gian (ngày cũ nhất và ngày mới nhất) dựa vào dữ liệu 'Ngày' trong các tin tức trên.
        """
        
        analysis_result_str = await smart_llm.aask(eval_prompt)
        analysis_result_str = re.sub(r'```json\n|\n```|```', '', analysis_result_str).strip()
        
        try:
            final_result = json.loads(analysis_result_str)
            # Chèn thêm danh sách link vào kết quả JSON cuối cùng
            final_result["reference_links"] = reference_links
            return json.dumps(final_result, ensure_ascii=False, indent=4)
        except Exception as e:
            # Xử lý trường hợp ngoại lệ
            return json.dumps({
                "error": f"Lỗi parse JSON từ LLM: {str(e)}",
                "raw_output": analysis_result_str,
                "reference_links": reference_links
            }, ensure_ascii=False, indent=4)