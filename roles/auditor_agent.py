# roles/auditor_agent.py
import sys
import json
from pathlib import Path

# Thiết lập đường dẫn gốc
root_path = str(Path(__file__).parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger

# Import Action kiểm toán
from actions.audit_action import AuditAndOptimizeReportAction
from utils.llm_rotator import smart_llm

class QualityAuditor(Role):
    name: str = "QualityAuditor"
    profile: str = "Chuyên gia Kiểm điểm và Tối ưu hóa Bản thảo (Critic)"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Gán Action kiểm toán cho Agent
        self.set_actions([AuditAndOptimizeReportAction])
        
        # Sử dụng LLM cấu hình linh hoạt (Tier 1 để rà soát lỗi tốt nhất)
        self.llm = smart_llm
        
        # Chế độ thực hiện: by_order
        self._set_react_mode(react_mode="by_order")
        
        self.system_prompt = (
            "Bạn là một chuyên gia Kiểm toán chất lượng nội dung khắt khe (Quality Auditor). "
            "Nhiệm vụ của bạn là rà soát chống ảo giác (hallucination) cho các báo cáo được viết bởi trí tuệ nhân tạo, "
            "so sánh với dữ liệu thô gốc, đồng thời nén, cắt tỉa và tối ưu hóa câu chữ để tiết kiệm chữ (token) nhưng vẫn chuyên nghiệp."
        )

    async def _act(self) -> Message:
        """
        Hành động chính của Auditor: Nhận báo cáo nháp và bối cảnh gốc, thực hiện hàm kiểm tra.
        """
        logger.info(f"[{self.profile}]: Bắt đầu rà soát, kiểm tra chéo và tối ưu hóa báo cáo...")
        
        # Lấy thông điệp từ Manager truyền sang
        # Chúng ta quy ước Manager sẽ truyền một chuỗi Dictionary (JSON) chứa "draft" và "context"
        instruction = self.get_memories()[-1].content
        
        try:
            data = json.loads(instruction)
            draft_report = data.get("draft", "")
            original_context = data.get("context", "")
        except json.JSONDecodeError:
            # Fallback an toàn nếu Manager lỡ truyên chuỗi String thông thường
            logger.warning("[AUDITOR] Thông điệp đầu vào không phải định dạng JSON. Cố gắng xử lý như văn bản thô...")
            draft_report = instruction
            original_context = "Bối cảnh gốc không được cung cấp theo chuẩn."
            
        todo = self.rc.todo # AuditAndOptimizeReportAction
        final_optimized_report = await todo.run(draft_report=draft_report, original_context=original_context)
        
        return Message(content=final_optimized_report, role=self.profile, cause_by=type(todo))
