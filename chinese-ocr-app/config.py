"""
Cấu hình chung cho hệ thống Multi-Pipeline HieuDe AI (NCKH).
Tất cả API keys và thresholds được quản lý tập trung tại đây.
"""
import os
from dotenv import load_dotenv

# Load .env file nếu có
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# ============================================================
# LLM Configuration
# ============================================================
# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# LLM chính được sử dụng: "gemini" hoặc "openai"
# Hệ thống sẽ fallback sang cái còn lại nếu cái chính lỗi
PRIMARY_LLM = os.getenv("PRIMARY_LLM", "gemini")

# Nhiệt độ LLM (0.0 = deterministic, 1.0 = creative)
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2048"))

# ============================================================
# Google Search Configuration
# ============================================================
# Google Custom Search API
GOOGLE_CSE_API_KEY = os.getenv("GOOGLE_CSE_API_KEY", "")
GOOGLE_CSE_CX = os.getenv("GOOGLE_CSE_CX", "")  # Custom Search Engine ID

# Selenium Google Search
SEARCH_N_RESULTS = int(os.getenv("SEARCH_N_RESULTS", "5"))  # Số bài viết lấy từ Google
SEARCH_TIMEOUT = int(os.getenv("SEARCH_TIMEOUT", "15"))  # Timeout (giây)
SCRAPE_TIMEOUT = int(os.getenv("SCRAPE_TIMEOUT", "10"))  # Timeout đọc bài viết

# ============================================================
# Selenium Configuration
# ============================================================
SELENIUM_HEADLESS = os.getenv("SELENIUM_HEADLESS", "true").lower() == "true"
CHROME_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# ============================================================
# Pipeline & Voting Configuration
# ============================================================
PIPELINE_WEIGHTS = {
    "ocr_llm": float(os.getenv("WEIGHT_OCR_LLM", "0.30")),
    "ocr_search": float(os.getenv("WEIGHT_OCR_SEARCH", "0.30")),
    "img_search": float(os.getenv("WEIGHT_IMG_SEARCH", "0.20")),
    "ml_match": float(os.getenv("WEIGHT_ML_MATCH", "0.20")),
}

# Timeout cho mỗi pipeline (giây)
PIPELINE_TIMEOUT = int(os.getenv("PIPELINE_TIMEOUT", "30"))

# Số pipeline tối thiểu phải trả về kết quả để voting hợp lệ
MIN_PIPELINE_RESPONSES = int(os.getenv("MIN_PIPELINE_RESPONSES", "2"))

# ============================================================
# Logging
# ============================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_PIPELINE_DETAILS = os.getenv("LOG_PIPELINE_DETAILS", "true").lower() == "true"
