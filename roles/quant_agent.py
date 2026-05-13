# roles/quant_agent.py
import sys
import os
import re
from pathlib import Path

root_path = str(Path(__file__).parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

from metagpt.roles import Role
from metagpt.schema import Message
from metagpt.logs import logger

from actions.company_info_action import GetCompanyInfoAction
from actions.technical_analysis_action import GetPriceHistoryAction, CalculateTechnicalIndicators
from utils.llm_rotator import smart_llm

class MarketDataQuantAgent(Role):
    name: str = "QuantSpecialist"
    profile: str = "Chuyên gia dữ liệu thị trường và phân tích định lượng"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Mảng Index: 0 -> Info, 1 -> Price History, 2 -> Indicators
        self.set_actions([
            GetCompanyInfoAction, 
            GetPriceHistoryAction, 
            CalculateTechnicalIndicators
        ])
        
        self.llm = smart_llm
        self._set_react_mode(react_mode="react")
        
        self.system_prompt = "Bạn là chuyên gia phân tích định lượng chứng khoán."

    # BƯỚC 1: GHI ĐÈ HÀM _THINK ĐỂ ÉP LLM CHỌN ĐÚNG ACTION
    async def _think(self) -> bool:
        # Tránh vòng lặp vô hạn của react mode
        if self.rc.todo is not None:
            self._set_state(-1)
            return False
            
        user_messages = [msg for msg in self.get_memories() if msg.role == "user"]
        instruction = user_messages[-1].content if user_messages else self.get_memories()[-1].content
        
        # Prompt Tường Minh (Explicit Routing)
        prompt = f"""
        Phân loại yêu cầu của người dùng vào 1 trong 3 nhóm sau:
        0 - Tra cứu thông tin doanh nghiệp, hồ sơ, vốn điều lệ.
        1 - Thống kê dữ liệu giá cổ phiếu lịch sử (OHLCV), giá cao/thấp, khối lượng.
        2 - Tính toán chỉ báo kỹ thuật (SMA, RSI).
        
        Yêu cầu người dùng: "{instruction}"
        
        TRẢ VỀ DUY NHẤT 1 CHỮ SỐ (0, 1 hoặc 2) tương ứng với công cụ. Không giải thích.
        """
        response = await self.llm.aask(prompt)
        
        try:
            # Ép kiểu để lấy đúng số LLM chọn
            idx = int(re.search(r'\d', response).group(0))
            if idx not in [0, 1, 2]:
                idx = 1 # Nếu LLM lỗi, mặc định cho vào thống kê giá
        except:
            idx = 1
            
        logger.info(f"---> [ROUTER] Agent phân tích và chủ động CHỌN CÔNG CỤ SỐ: {idx}")
        self._set_state(idx)
        return True

    # BƯỚC 2: CHẠY HÀM _ACT THEO CÔNG CỤ ĐÃ ĐƯỢC ÉP CHỌN
    async def _act(self) -> Message:
        logger.info(f"{self._setting}: bắt đầu thực thi {self.rc.todo.name}")
        todo = self.rc.todo
        
        user_messages = [msg for msg in self.get_memories() if msg.role == "user"]
        instruction = user_messages[-1].content if user_messages else self.get_memories()[0].content
        
        result = await todo.run(instruction=instruction)
        
        # Reset lại todo để chuẩn bị cho câu hỏi tiếp theo của người dùng
        self.rc.todo = None 
        
        return Message(content=result, role=self.profile, cause_by=type(todo))
    