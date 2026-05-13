# roles/manager_agent.py
import sys
import os
from pathlib import Path

root_path = str(Path(__file__).parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

from metagpt.roles import Role
from metagpt.configs.llm_config import LLMConfig
from metagpt.provider.llm_provider_registry import create_llm_instance
from metagpt.schema import Message
from metagpt.logs import logger

# Import Action lập kế hoạch
from actions.planning_action import CreateExecutionPlan

# Import các Sub-agents
from roles.sentiment_agent import NewsSentimentAgent
from roles.quant_agent import MarketDataQuantAgent
from roles.fundamental_agent import FundamentalAnalystAgent
from roles.investment_advisor import InvestmentAdvisor # Import agent mới
from roles.auditor_agent import QualityAuditor # Import Auditor
from utils.llm_rotator import smart_llm
import json

class OrchestratorManager(Role):
    name: str = "Cerebrum"
    profile: str = "Giám đốc điều phối (Manager/Orchestrator)"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Manager sử dụng smart_llm để có khả năng phục hồi tốt nhất
        self.llm = smart_llm
        
        # Manager sở hữu 1 Action duy nhất là Lập kế hoạch
        self.set_actions([CreateExecutionPlan])
        
        # Khởi tạo các Sub-agents (Cấp dưới)
        self.sentiment_agent = NewsSentimentAgent()
        self.quant_agent = MarketDataQuantAgent()
        self.fundamental_agent = FundamentalAnalystAgent()
        self.investment_advisor = InvestmentAdvisor() # Khởi tạo agent mới
        self.auditor_agent = QualityAuditor() # Khởi tạo auditor

    async def _act(self) -> Message:
        instruction = self.get_memories()[-1].content
        logger.info(f"\n[MANAGER] Tiếp nhận yêu cầu: {instruction}")
        
        # 1. Lập kế hoạch
        plan_action = self.rc.todo
        plan = await plan_action.run(instruction=instruction)
        logger.info(f"[MANAGER] Kế hoạch thực thi:\n{plan}")
        
        global_context = "" # Bộ nhớ dùng chung giữa các bước
        draft_report = ""   # Lưu bản nháp từ Investment Advisor
        
        # 2. Thực thi từng bước
        for step_idx, step in enumerate(plan, 1):
            agent_name = step.get("agent")
            task = step.get("task")
            ticker = step.get("ticker") # Lấy ticker từ kế hoạch
            
            # Giao cho Investment Advisor lập báo cáo nháp dựa trên bối cảnh
            if agent_name == "InvestmentAdvisor":
                logger.info(f"\n[MANAGER] ---> Đang chạy Bước {step_idx}: Giao cho {agent_name} tổng hợp báo cáo nháp.")
                res_msg = await self.investment_advisor.run(global_context)
                draft_report = res_msg.content
                logger.info(f"[MANAGER] Kết quả từ {agent_name}: Biên soạn nháp thành công.")
                continue # Investment Advisor xuất nháp, không nhồi thêm vào dòng global_context nữa

            # Bước cuối cùng giao cho Auditor rà soát lại
            if agent_name == "QualityAuditor":
                logger.info(f"\n[MANAGER] ---> Bước cuối: Giao cho {agent_name} kiểm toán và đánh giá.")
                payload = json.dumps({
                    "draft": draft_report,
                    "context": global_context
                }, ensure_ascii=False)
                final_res_msg = await self.auditor_agent.run(payload)
                return Message(content=final_res_msg.content, role=self.profile)

            logger.info(f"\n[MANAGER] ---> Đang chạy Bước {step_idx}: Giao cho {agent_name} làm nhiệm vụ: {task} (Mã: {ticker})")
            
            # Gắn thêm context từ bước trước và ticker vào câu lệnh
            enriched_task = f"Mã cổ phiếu: {ticker}. Nhiệm vụ: {task}\n\nThông tin bối cảnh từ các bước trước (nếu cần dùng): {global_context}" if global_context else f"Mã cổ phiếu: {ticker}. Nhiệm vụ: {task}"
            
            # Gọi đúng Sub-agent
            step_result = ""
            if agent_name == "SentimentAgent":
                res_msg = await self.sentiment_agent.run(enriched_task)
                step_result = res_msg.content
            elif agent_name == "QuantAgent":
                res_msg = await self.quant_agent.run(enriched_task)
                step_result = res_msg.content
            elif agent_name == "FundamentalAnalyst":
                res = await self.fundamental_agent.run(enriched_task)
                step_result = res.content
            else:
                step_result = f"Agent '{agent_name}' không hợp lệ trong kế hoạch."

            logger.info(f"[MANAGER] Kết quả từ {agent_name}: Thành công.")
            
            # Lưu kết quả vào bộ nhớ dùng chung
            global_context += f"\n--- Báo cáo từ {agent_name} ---\n{step_result}\n"

        # Fallback: Nếu kế hoạch không có InvestmentAdvisor, trả về context thô
        logger.warning("[MANAGER] Kế hoạch không có bước InvestmentAdvisor cuối cùng. Trả về context đã tổng hợp.")
        return Message(content=global_context, role=self.profile)