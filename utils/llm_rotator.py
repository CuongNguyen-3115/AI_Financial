# utils/llm_rotator.py
import os
import time
from metagpt.configs.llm_config import LLMConfig
from metagpt.provider.llm_provider_registry import create_llm_instance
from metagpt.logs import logger

class SmartLLMRotator:
    def __init__(self):
        # Lưu trữ model theo 3 phân lớp (Tiers) ưu tiên
        self.tiers = {
            1: [], # Tier 1: High Quality (Chất lượng cao nhất)
            2: [], # Tier 2: Good & Fast (Nhanh, xịn, rate limit rộng)
            3: []  # Tier 3: Fallbacks (Dự phòng cuối cùng)
        }
        self.cooldowns = {}
        self.cooldown_duration = 300
        
        # Lưu lại vị trí đang xoay vòng (Round-Robin) của từng Tier để cân bằng tải
        self.tier_indices = {1: 0, 2: 0, 3: 0}

        self._build_pools()

    def _load_env_models(self, prefix: str, max_count: int, api_type: str, api_key_env: str, base_url: str = None) -> list:
        """Hàm tự động quét các biến môi trường theo chuỗi Prefix."""
        models = []
        api_key = os.getenv(api_key_env)
        if not api_key: return models
        
        for i in range(1, max_count + 1):
            model_id = os.getenv(f"{prefix}_{i}")
            if model_id:
                config_args = {"api_type": api_type, "api_key": api_key, "model": model_id}
                if base_url:
                    config_args["base_url"] = base_url
                models.append(LLMConfig(**config_args))
        return models

    def _build_pools(self):
        kb_endpoint = "https://models.inference.ai.azure.com"
        groq_endpoint = "https://api.groq.com/openai/v1"
        hf_endpoint = "https://api-inference.huggingface.co/v1"

        # 1. Quét tự động TẤT CẢ các model từ .env thay vì gọi cứng từng biến
        github_models = self._load_env_models("GITHUB_MODEL_ID", 4, "openai", "GITHUB_TOKEN", kb_endpoint)
        groq_models = self._load_env_models("GROQ_MODEL_ID", 7, "openai", "GROQ_API_KEY", groq_endpoint)
        gemini_models = self._load_env_models("MODEL_ID", 5, "gemini", "GEMINI_API_KEY")
        hf_models = self._load_env_models("HF_MODEL_ID", 5, "openai", "HF_TOKEN", hf_endpoint)

        # 2. Phân loại vào các Tier một cách thông minh
        # --- TIER 1: HIGH QUALITY ---
        if len(github_models) >= 2:
            self.tiers[1].extend(github_models[:2])  # GITHUB 1-2 (GPT-4o, Llama 405B)
        self.tiers[1].extend(groq_models[:3])        # GROQ 1-3 (Llama 3.3 70B, GPT-OSS 120B, v.v)

        # --- TIER 2: GOOD QUALITY & FAST ---
        if len(github_models) >= 4:
            self.tiers[2].extend(github_models[2:4]) # GITHUB 3-4 (GPT-4o-mini, Llama 8B)
        self.tiers[2].extend(groq_models[3:])        # GROQ 4-7
        self.tiers[2].extend(gemini_models)          # Toàn bộ GEMINI 1-5
        if len(hf_models) >= 2:
            self.tiers[2].extend(hf_models[:2])      # HF 1-2 (Qwen 72B, Llama 70B)

        # --- TIER 3: FINAL FALLBACKS ---
        if len(hf_models) >= 5:
            self.tiers[3].extend(hf_models[2:])      # HF 3-5

        # Dự phòng cứng cho Gemini (đảm bảo hệ thống luôn có fallback an toàn)
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            self.tiers[2].append(LLMConfig(api_type="gemini", api_key=gemini_key, model="gemini-1.5-flash"))
            self.tiers[2].append(LLMConfig(api_type="gemini", api_key=gemini_key, model="gemini-1.5-pro"))

        # 3. Lọc trùng lặp Model cho từng Tier để tiết kiệm Request
        for tier_level in self.tiers:
            seen = set()
            filtered = []
            for c in self.tiers[tier_level]:
                if not c.model: continue
                key = f"{c.api_type}-{c.model}"
                if key not in seen:
                    seen.add(key)
                    filtered.append(c)
            self.tiers[tier_level] = filtered

        total_models = sum(len(tier) for tier in self.tiers.values())
        if total_models == 0:
            logger.warning("⚠️ KHÔNG TÌM THẤY MODEL NÀO ĐƯỢC LOAD VÀO ROTATOR. HÃY KIỂM TRA LẠI FILE .ENV!")
        else:
            logger.info(f"✅ Đã nạp thành công {total_models} models. (T1: {len(self.tiers[1])}, T2: {len(self.tiers[2])}, T3: {len(self.tiers[3])})")

    async def aask(self, prompt: str, system_msgs: list = None) -> str:
        last_exception = None
        current_time = time.time()

        # Kiểm tra nhanh xem toàn bộ hệ thống có đang bị cooldown hết không
        all_cooldown = True
        for tier_level, models in self.tiers.items():
            for config in models:
                key = f"{config.api_type}-{config.model}"
                if key not in self.cooldowns or self.cooldowns[key] < current_time:
                    all_cooldown = False
                    break
        
        if all_cooldown:
            logger.warning("🔄 Toàn bộ Model ở mọi Tier đều đang Cooldown. Làm mới danh sách để ép chạy!")
            self.cooldowns.clear()

        # Thử lần lượt từ Tier 1 -> Tier 2 -> Tier 3
        for tier_level in sorted(self.tiers.keys()):
            pool = self.tiers[tier_level]
            if not pool:
                continue
            
            pool_size = len(pool)
            # Chạy Round-Robin bên trong Tier này để dàn đều tải (tránh đập liên tục vào 1 API)
            for _ in range(pool_size):
                # Lấy model hiện tại và dịch chuyển index sang model tiếp theo ngay lập tức
                current_idx = self.tier_indices[tier_level]
                config = pool[current_idx]
                self.tier_indices[tier_level] = (current_idx + 1) % pool_size

                key = f"{config.api_type}-{config.model}"

                # Bỏ qua nếu model đang bị khóa trong ngăn đá (Cooldown)
                if key in self.cooldowns and self.cooldowns[key] > current_time:
                    continue

                try:
                    llm = create_llm_instance(config)
                    logger.info(f"🔄 [LLM ROTATOR - TIER {tier_level}] Đang thử Model: {config.model} ({config.api_type})")
                    
                    response = await llm.aask(prompt, system_msgs)
                    logger.info(f"✅ [LLM ROTATOR] THÀNH CÔNG với Model: {config.model}")
                    return response
                    
                except Exception as e:
                    err_str = str(e)
                    
                    # Xử lý các lỗi liên quan đến Rate Limit / Quota
                    if any(code in err_str for code in ["429", "RateLimit", "503", "Too Many Requests", "Quota"]):
                        logger.warning(f"⚠️ Model {config.model} bị giới hạn Quota. Cooldown {self.cooldown_duration}s...")
                        self.cooldowns[key] = time.time() + self.cooldown_duration
                        
                    # Xử lý các lỗi nghiêm trọng (Không tồn tại model, sai API Key)
                    elif any(code in err_str for code in ["404", "401", "403"]):
                        logger.error(f"❌ Model {config.model} lỗi xác thực hoặc không tồn tại. Cấm 1 giờ!")
                        self.cooldowns[key] = time.time() + 3600
                        
                    # Các lỗi mạng lặt vặt (Timeout)
                    else:
                        logger.warning(f"⚠️ Model {config.model} gặp lỗi ({e.__class__.__name__}). Bỏ qua tạm thời...")
                        self.cooldowns[key] = time.time() + 60
                        
                    last_exception = e
                    continue # Di chuyển sang model kế tiếp trong cùng Tier

        raise Exception(f"🚨 TẤT CẢ MODEL ĐÃ SẬP hoặc ĐANG TRONG COOLDOWN! Lỗi cuối cùng: {last_exception}") from last_exception

# Khởi tạo instance dùng chung
smart_llm = SmartLLMRotator()