"""
Cấu hình chung cho hệ thống Multi-Pipeline HieuDe AI (NCKH).
Tất cả API keys và thresholds được quản lý tập trung tại đây.
"""
import os
import re
from dotenv import load_dotenv

# Load .env file nếu có
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# ============================================================
# LLM Configuration
# ============================================================
# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
VISION_MODEL = os.getenv("VISION_MODEL", GEMINI_MODEL)

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_VISION_MODEL = os.getenv("OPENAI_VISION_MODEL", OPENAI_MODEL)

# Vision provider: "gemini", "openai", or "auto"
VISION_PROVIDER = os.getenv("VISION_PROVIDER", "auto")

# LLM chính được sử dụng: "gemini", "openai", hoặc "ollama"
# Hệ thống sẽ fallback sang cái còn lại nếu cái chính lỗi
PRIMARY_LLM = os.getenv("PRIMARY_LLM", "ollama")

# Ollama Configuration (Local LLM)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "neural-chat")  # hoặc mistral, llama2, etc.
OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "qwen3-vl:4b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))  # 2 minutes for local inference

# OpenCode Vision Configuration
OPENCODE_VISION_MODEL = os.getenv("OPENCODE_VISION_MODEL", "opencode/mimo-v2.5-free")
OPENCODE_TIMEOUT = int(os.getenv("OPENCODE_TIMEOUT", "120"))

# Nhiệt độ LLM (0.0 = deterministic, 1.0 = creative)
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2048"))

# ============================================================
# Google Search Configuration
# ============================================================
# Google Custom Search API
GOOGLE_CSE_API_KEY = os.getenv("GOOGLE_CSE_API_KEY", "")


def _normalize_google_cse_cx(value: str) -> str:
    """Accept either a raw CX id or a pasted Google CSE script/url."""
    raw = (value or "").strip().strip('"').strip("'")
    if not raw:
        return ""
    match = re.search(r"[?&]cx=([A-Za-z0-9:_-]+)", raw) or re.search(
        r"\bcx=([A-Za-z0-9:_-]+)",
        raw,
    )
    if match:
        return match.group(1)
    return raw.strip("<> ")


GOOGLE_CSE_CX = _normalize_google_cse_cx(os.getenv("GOOGLE_CSE_CX", ""))  # Custom Search Engine ID

# Selenium Google Search
SEARCH_METHOD = os.getenv("SEARCH_METHOD", "selenium").strip().lower()
SEARCH_ALLOW_API_FALLBACK = os.getenv("SEARCH_ALLOW_API_FALLBACK", "false").lower() == "true"
SEARCH_N_RESULTS = int(os.getenv("SEARCH_N_RESULTS", "5"))  # Số bài viết lấy từ Google
SEARCH_TIMEOUT = int(os.getenv("SEARCH_TIMEOUT", "15"))  # Timeout (giây)
SCRAPE_TIMEOUT = int(os.getenv("SCRAPE_TIMEOUT", "10"))  # Timeout đọc bài viết

# ============================================================
# Selenium Configuration
# ============================================================
SELENIUM_HEADLESS = os.getenv("SELENIUM_HEADLESS", "true").lower() == "true"
ENABLE_SELENIUM_IMAGE_SEARCH = os.getenv("ENABLE_SELENIUM_IMAGE_SEARCH", "true").lower() == "true"
ENABLE_GOOGLE_IMAGE_HTTP_UPLOAD = os.getenv("ENABLE_GOOGLE_IMAGE_HTTP_UPLOAD", "false").lower() == "true"
CHROME_PATH = os.getenv("CHROME_PATH", "").strip()
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "").strip()
SELENIUM_USE_ROTATING_PROXY = os.getenv("SELENIUM_USE_ROTATING_PROXY", "false").lower() == "true"
SELENIUM_PROXY_FILE = os.getenv("SELENIUM_PROXY_FILE", "proxy.data").strip()
SELENIUM_USED_PROXY_FILE = os.getenv("SELENIUM_USED_PROXY_FILE", "proxy_used.data").strip()
CHROME_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# ============================================================
# Pipeline & Voting Configuration
# ============================================================
PIPELINE_WEIGHTS = {
    "vision_read": float(os.getenv("WEIGHT_VISION_READ", "0.35")),
    "vision_gemini": float(os.getenv("WEIGHT_VISION_GEMINI", "0.40")),
    "vision_opencode": float(os.getenv("WEIGHT_VISION_OPENCODE", "0.40")),
    "vision_ollama": float(os.getenv("WEIGHT_VISION_OLLAMA", "0.38")),
    "text_vote": float(os.getenv("WEIGHT_TEXT_VOTE", "0.55")),
    "ocr_llm": float(os.getenv("WEIGHT_OCR_LLM", "0.30")),
    "ocr_search": float(os.getenv("WEIGHT_OCR_SEARCH", "0.30")),
    "img_search": float(os.getenv("WEIGHT_IMG_SEARCH", "0.20")),
    "ml_match": float(os.getenv("WEIGHT_ML_MATCH", "0.20")),
}

# Timeout cho mỗi pipeline (giây)
PIPELINE_TIMEOUT = int(os.getenv("PIPELINE_TIMEOUT", "90"))

# Số pipeline tối thiểu phải trả về kết quả để voting hợp lệ
MIN_PIPELINE_RESPONSES = int(os.getenv("MIN_PIPELINE_RESPONSES", "2"))

# ============================================================
# Logging
# ============================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_PIPELINE_DETAILS = os.getenv("LOG_PIPELINE_DETAILS", "true").lower() == "true"

# ============================================================
# Contact Form Email
# ============================================================
CONTACT_RECIPIENT = os.getenv("CONTACT_RECIPIENT", "xuatruong30@gmail.com").strip()
CONTACT_SMTP_HOST = os.getenv("CONTACT_SMTP_HOST", "smtp.gmail.com").strip()
CONTACT_SMTP_PORT = int(os.getenv("CONTACT_SMTP_PORT", "587"))
CONTACT_SMTP_USER = os.getenv("CONTACT_SMTP_USER", "").strip()
CONTACT_SMTP_PASSWORD = os.getenv("CONTACT_SMTP_PASSWORD", "").strip()
CONTACT_FROM_EMAIL = os.getenv("CONTACT_FROM_EMAIL", CONTACT_SMTP_USER).strip()
