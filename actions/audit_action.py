# actions/audit_action.py
import sys
import os
from metagpt.actions import Action

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.llm_rotator import smart_llm
from metagpt.logs import logger

class AuditAndOptimizeReportAction(Action):
    name: str = "AuditAndOptimizeReportAction"
    description: str = "Kiểm tra chéo (Cross-check) báo cáo nháp với dữ liệu gốc để chống ảo giác (Hallucination) và cắt tỉa văn bản giúp tiết kiệm token."

    async def run(self, draft_report: str, original_context: str) -> str:
        """
        Thực hiện kiểm tra chất lượng báo cáo.
        Args:
            draft_report (str): Báo cáo tư vấn đầu tư nháp do Investment Advisor viết.
            original_context (str): Dữ liệu thô gốc từ các Agent (Sentiment, Quant, Fundamental) để đối chiếu.
        """
        
        prompt = f"""
        Bạn là một "Quality Auditor" (Kiểm toán viên chất lượng) vô cùng khắt khe và tỉ mỉ trong lĩnh vực tài chính.
        Nhiệm vụ của bạn là rà soát BẢN BÁO CÁO NHÁP dưới đây, đối chiếu nó với DỮ LIỆU GỐC để phát hiện lỗi sai, sau đó tối ưu hóa câu chữ.

        === BẢN BÁO CÁO NHÁP CẦN KIỂM TRA ===
        {draft_report}

        === DỮ LIỆU GỐC (DÙNG ĐỂ ĐỐI CHIẾU) ===
        {original_context}

        HƯỚNG DẪN KIỂM TOÁN VÀ TỐI ƯU HÓA:
        1. KIỂM TRA ẢO GIÁC SỐ LIỆU (Fact-checking):
           - Đọc kỹ các con số (Giá mục tiêu, Chỉ số SMA/RSI, Thông tin vốn điều lệ, Số ngày, Số tin tức).
           - Nếu Bản sao nháp có bất kỳ số liệu nào KHÔNG TỒN TẠI hoặc SAI LỆCH so với Dữ liệu gốc -> Bạn PHẢI ép nó về đúng số liệu của Dữ liệu gốc.

        2. BẢO TOÀN SỰ CHI TIẾT VÀ TỐI ƯU VĂN PHONG FORMAT:
           - Xóa bỏ những câu từ giao tiếp AI thừa thãi (ví dụ: "Dưới đây là báo cáo...", "Chúng tôi xin trình bày...").
           - KHÔNG ĐƯỢC rút gọn hay lược bỏ bất kỳ số liệu, bảng biểu thống kê giá (OHLCV, SMA, RSI), hay chi tiết luận điểm nào từ bản nháp. 
           - Đảm bảo văn phong lạnh lùng, dứt khoát, chuyên sâu đúng chuẩn báo cáo tài chính chuyên nghiệp.

        3. BẢO TOÀN TRÍCH DẪN:
           - Giữ NGUYÊN VẸN 100% mục "Tài liệu Tham khảo (Reference Links)" ở cuối báo cáo cùng tất cả các đường link URL. Tuyệt đối không được cắt bỏ các đường link này.
           - Giữ NGUYÊN VẸN khuyến nghị cuối cùng (MUA/BÁN/GIỮ) và mức giá mục tiêu chính xác.

        Trả về kết quả là BẢN BÁO CÁO ĐÃ ĐƯỢC TỐI ƯU, sử dụng định dạng Markdown. Không cần giải thích thêm về những gì bạn đã sửa.
        """
        
        logger.info("[AUDITOR] Đang tiến hành kiểm toán chức năng và đối chiếu số liệu...")
        final_optimized_report = await smart_llm.aask(prompt)
        return final_optimized_report
