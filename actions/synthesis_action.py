# actions/synthesis_action.py
import sys
import os
from metagpt.actions import Action
from utils.llm_rotator import smart_llm

class SynthesizeAnalysisAction(Action):
    name: str = "SynthesizeAnalysisAction"
    description: str = "Tổng hợp kết quả phân tích từ các chuyên gia khác nhau (Tâm lý, Kỹ thuật, Cơ bản) để đưa ra một báo cáo tư vấn đầu tư cuối cùng, có tính đến khẩu vị rủi ro của người dùng."

    async def run(self, context: str, risk_profile: str = "Cân bằng") -> str:
        """
        Args:
            context (str): Chuỗi chứa toàn bộ kết quả phân tích từ các agent trước đó.
            risk_profile (str): Khẩu vị rủi ro của nhà đầu tư ('Thận trọng', 'Cân bằng', 'Mạo hiểm').
        """
        
        prompt = f"""
        Bạn là một Chuyên gia Tư vấn Đầu tư cao cấp, người đưa ra kết luận cuối cùng.
        Dựa trên các báo cáo chi tiết từ các bộ phận phân tích dưới đây và khẩu vị rủi ro của khách hàng, hãy viết một BÁO CÁO TƯ VẤN ĐẦU TƯ hoàn chỉnh.

        ### BỐI CẢNH THỊ TRƯỜNG VÀ CỔ PHIẾU
        {context}

        ### KHẨU VỊ RỦI RO CỦA NHÀ ĐẦU TƯ
        {risk_profile}

        ### YÊU CẦU BÁO CÁO
        Báo cáo của bạn phải có cấu trúc rõ ràng, chuyên nghiệp và bao gồm các phần sau:
        1.  **Tóm tắt Nhanh (Executive Summary):** Nêu bật những điểm chính và kết luận cốt lõi trong 3-4 câu.
        2.  **Đánh giá Tâm lý Thị trường:** Tổng hợp lại tâm lý thị trường, TRÌNH BÀY RÕ SỐ LƯỢNG TIN TỨC đã được phân tích. Ví dụ: "Theo tổng hợp số lượng tin tức về cổ phiếu và thị trường, ...". 
        3.  **Tổng hợp Các Luận điểm Đầu tư:** Kết hợp thông tin từ phân tích cơ bản, kỹ thuật và tâm lý để đưa ra các luận điểm hỗ trợ (bull case) và các luận điểm phản biện (bear case). Trong phần Tóm tắt báo cáo phân tích, hãy trích dẫn rõ nguồn báo cáo (link) nếu có.
        4.  **Đánh giá Rủi ro:** Liệt kê các rủi ro chính đã được xác định và đánh giá mức độ ảnh hưởng của chúng.
        5.  **Khuyến nghị Đầu tư Cuối cùng:** Dựa trên tất cả các phân tích và có cân nhắc đến khẩu vị rủi ro của khách hàng, hãy đưa ra một trong ba khuyến nghị: **MUA**, **BÁN**, hoặc **NẮM GIỮ**. Giải thích rõ ràng lý do đằng sau khuyến nghị này.
        6.  **Chiến lược Hành động (Actionable Strategy):**
            *   Nếu khuyến nghị MUA: Đề xuất vùng giá mua hợp lý.
            *   Nếu khuyến nghị BÁN: Đề xuất vùng giá bán để chốt lời hoặc cắt lỗ.
            *   Nếu khuyến nghị NẮM GIỮ: Giải thích lý do tại sao nên tiếp tục giữ và các tín hiệu cần theo dõi.
        7.  **Tài liệu Tham khảo (Reference Links):** Ở cuỗi báo cáo, bắt buộc trích xuất toàn bộ các link tin tức (reference_links) từ dữ liệu json Tâm lý thị trường và link báo cáo gốc (Nguồn báo cáo) từ phân tích cơ bản để tạo thành danh sách trích dẫn rõ ràng, ví dụ "Nguồn tin tức được lấy từ: ...".

        Hãy trình bày một cách mạch lạc, chuyên nghiệp và dễ hiểu cho nhà đầu tư.
        """
        
        final_report = await smart_llm.aask(prompt)
        return final_report
