# roles/investment_advisor.py
import sys
from pathlib import Path

# Thiết lập đường dẫn gốc
root_path = str(Path(__file__).parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger

# Import Action tổng hợp
from actions.synthesis_action import SynthesizeAnalysisAction
from utils.llm_rotator import smart_llm

class InvestmentAdvisor(Role):
    name: str = "InvestmentAdvisor"
    profile: str = "Chuyên gia Tư vấn Đầu tư"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Gán Action tổng hợp cho Agent
        self.set_actions([SynthesizeAnalysisAction])
        
        # Sử dụng LLM mạnh nhất (Tier 1) để đưa ra tư vấn cuối cùng
        self.llm = smart_llm
        
        # Chế độ thực hiện: by_order
        self._set_react_mode(react_mode="by_order")
        
        self.system_prompt = (
            "Bạn là một Chuyên gia Tư vấn Đầu tư cao cấp, người đưa ra kết luận cuối cùng. "
            "Nhiệm vụ của bạn là tổng hợp tất cả các phân tích từ các chuyên gia (Tâm lý, Kỹ thuật, Cơ bản) "
            "để xây dựng một báo cáo tư vấn đầu tư hoàn chỉnh, có tính đến khẩu vị rủi ro của khách hàng."
        )

    async def _act(self) -> Message:
        """
        Hành động chính của Agent: Nhận toàn bộ bối cảnh và chạy Action tổng hợp.
        """
        logger.info(f"[{self.profile}]: Bắt đầu tổng hợp báo cáo tư vấn cuối cùng.")
        
        # Lấy toàn bộ bối cảnh đã được Manager tổng hợp
        context_message = self.get_memories()[-1]
        context = context_message.content
        
        # Trích xuất khẩu vị rủi ro từ context (nếu có, mặc định là 'Cân bằng')
        # Tạm thời hardcode, trong tương lai có thể dùng LLM để trích xuất
        risk_profile = "Cân bằng" 
        
        # Chạy Action tổng hợp
        todo = self.rc.todo # SynthesizeAnalysisAction
        final_report = await todo.run(context=context, risk_profile=risk_profile)
        
        return Message(content=final_report, role=self.profile, cause_by=type(todo))
