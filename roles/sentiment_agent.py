# roles/sentiment_agent.py
import sys
import os
from pathlib import Path

root_path = str(Path(__file__).parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger
from actions.news_analysis_action import AnalyzeNewsSentiment
from utils.llm_rotator import smart_llm # Import bộ xoay vòng dùng chung

class NewsSentimentAgent(Role):
    name: str = "SentimentAnalyst"
    profile: str = "Chuyên gia phân tích tâm lý thị trường và tin tức"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.set_actions([AnalyzeNewsSentiment])
        # Sử dụng smart_llm thay vì khởi tạo một llm cố định
        self.llm = smart_llm
        self._set_react_mode(react_mode="react")
        
        self.system_prompt = (
            "Bạn là chuyên gia phân tích tâm lý thị trường (Sentiment Analyst) trên thị trường chứng khoán Việt Nam. "
            "Nhiệm vụ cốt lõi của bạn là đọc hiểu tin tức tài chính, tổng hợp thông tin đa chiều và đưa ra "
            "đánh giá định lượng về mức độ tích cực/tiêu cực một cách khách quan, chính xác."
        )

    async def _act(self) -> Message:
        logger.info(f"{self._setting}: chuẩn bị thực hiện {self.rc.todo.name}")
        todo = self.rc.todo
        
        # Lấy nguyên văn yêu cầu mới nhất từ người dùng / Orchestrator
        instruction = self.get_memories()[-1].content
            
        # Truyền toàn bộ câu lệnh vào Action
        # Action bây giờ sẽ sử dụng smart_llm
        result = await todo.run(instruction=instruction)
        
        return Message(content=result, role=self.profile, cause_by=type(todo))