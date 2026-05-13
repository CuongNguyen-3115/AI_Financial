# roles/fundamental_agent.py
import sys
import os
from pathlib import Path

# Thiết lập đường dẫn gốc để import các module trong project
root_path = str(Path(__file__).parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger

# Import Action xử lý báo cáo đa tầng (Map-Reduce)
from actions.report_analysis_action import AnalyzeFinancialReport
from utils.llm_rotator import smart_llm

class FundamentalAnalystAgent(Role):
    name: str = "FundamentalAnalyst"
    profile: str = "Chuyên gia Phân tích Cơ bản"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Gán Action phân tích báo cáo cho Agent
        self.set_actions([AnalyzeFinancialReport])
        
        # Cấu hình LLM mặc định cho Agent (Dùng để suy nghĩ và giao tiếp)
        self.llm = smart_llm
        
        # Chế độ thực hiện: by_order (vì Agent này tập trung vào quy trình xử lý báo cáo)
        self._set_react_mode(react_mode="by_order")
        
        self.system_prompt = (
            "Bạn là một Chuyên gia Phân tích Cơ bản kỳ cựu. "
            "Nhiệm vụ của bạn là đọc hiểu các báo cáo phân tích từ các công ty chứng khoán, "
            "trích xuất các luận điểm kinh doanh, rủi ro và giá mục tiêu. "
            "Bạn phối hợp với hệ thống đa model (Swarm) để tóm tắt các tài liệu dài một cách chính xác."
        )

    async def _act(self) -> Message:
        logger.info(f"{self._setting}: chuẩn bị thực hiện {self.rc.todo.name}")
        todo = self.rc.todo
        
        # Lấy yêu cầu mới nhất từ bộ nhớ (Memory)
        # Nếu được gọi từ Manager, instruction sẽ chứa context về mã cổ phiếu
        user_messages = [msg for msg in self.get_memories() if msg.role == "user"]
        instruction = user_messages[-1].content if user_messages else self.get_memories()[-1].content
        
        # Thực hiện Action (Bao gồm việc tải PDF -> Chuyển Markdown -> Map-Reduce)
        result = await todo.run(instruction=instruction)
        
        return Message(content=result, role=self.profile, cause_by=type(todo))