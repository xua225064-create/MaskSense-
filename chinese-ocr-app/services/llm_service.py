"""
LLM Service — Kết nối và gọi LLM (Gemini + OpenAI) cho hệ thống Multi-Pipeline.

Hỗ trợ:
- Google Gemini API (primary) — sử dụng google-genai SDK mới
- OpenAI GPT API (fallback)
- Tự động fallback khi API chính lỗi
- Retry logic với exponential backoff
- Prompt template cho phân tích hiệu đề
"""
import json
import sys
import asyncio
import traceback
from typing import Any, Dict, Optional

# Fix Windows console encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Lazy imports — chỉ import khi thật sự cần dùng
_gemini_client = None
_openai_client = None

# Import Ollama service
try:
    from services.ollama_service import call_ollama as _call_ollama_impl
    _ollama_available = True
except ImportError:
    _ollama_available = False


def _get_gemini_client():
    """Lazy init Gemini client (google-genai SDK mới)."""
    global _gemini_client
    if _gemini_client is None:
        try:
            from google import genai
            from config import GEMINI_API_KEY
            
            if not GEMINI_API_KEY:
                print("[LLM] ⚠ GEMINI_API_KEY chưa được cấu hình")
                return None
                
            _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
            from config import GEMINI_MODEL
            print(f"[LLM] ✅ Gemini client đã sẵn sàng (model: {GEMINI_MODEL})")
        except Exception as e:
            print(f"[LLM] ❌ Không thể khởi tạo Gemini: {e}")
            return None
    return _gemini_client


def _get_openai_client():
    """Lazy init OpenAI client."""
    global _openai_client
    if _openai_client is None:
        try:
            from openai import OpenAI
            from config import OPENAI_API_KEY
            
            if not OPENAI_API_KEY:
                print("[LLM] ⚠ OPENAI_API_KEY chưa được cấu hình")
                return None
                
            _openai_client = OpenAI(api_key=OPENAI_API_KEY)
            print("[LLM] ✅ OpenAI client đã sẵn sàng")
        except Exception as e:
            print(f"[LLM] ❌ Không thể khởi tạo OpenAI: {e}")
            return None
    return _openai_client


# ============================================================
# Core LLM Calls
# ============================================================

async def call_gemini(prompt: str, temperature: float = 0.3, max_tokens: int = 2048, timeout: int = 30) -> Optional[str]:
    """
    Gọi Gemini API (google-genai SDK mới) với retry cho lỗi 503.
    """
    client = _get_gemini_client()
    if client is None:
        return None
    
    from google.genai import types
    from config import GEMINI_MODEL
    import time as _time
    
    config = types.GenerateContentConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )
    
    def _call_with_retry():
        """Blocking call với retry cho 503/429."""
        last_err = None
        for attempt in range(4):  # max 4 attempts
            try:
                resp = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                    config=config,
                )
                if resp and resp.text:
                    return resp.text.strip()
                return None
            except Exception as e:
                last_err = e
                err_str = str(e)
                if "503" in err_str or "429" in err_str or "UNAVAILABLE" in err_str:
                    wait = 3 * (attempt + 1)  # 3s, 6s, 9s, 12s
                    print(f"[LLM/Gemini] Retry {attempt+1}/3 sau {wait}s...")
                    _time.sleep(wait)
                    continue
                else:
                    print(f"[LLM/Gemini] Error: {e}")
                    return None
        print(f"[LLM/Gemini] Failed after 4 attempts: {last_err}")
        return None
    
    try:
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(None, _call_with_retry),
            timeout=timeout,
        )
        return result
    
    except asyncio.TimeoutError:
        print(f"[LLM/Gemini] Timeout sau {timeout}s")
        return None
    except Exception as e:
        print(f"[LLM/Gemini] Error: {e}")
        return None


async def call_openai(prompt: str, temperature: float = 0.3, max_tokens: int = 2048) -> Optional[str]:
    """
    Gọi OpenAI GPT API.
    
    Args:
        prompt: Nội dung prompt
        temperature: Nhiệt độ
        max_tokens: Số token tối đa
        
    Returns:
        Text response hoặc None nếu lỗi
    """
    client = _get_openai_client()
    if client is None:
        return None
    
    try:
        from config import OPENAI_MODEL
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Bạn là chuyên gia về gốm sứ cổ Trung Quốc và Việt Nam. "
                            "Bạn có kiến thức sâu về hiệu đề (reign marks) trên đáy bát, "
                            "đĩa, lọ hoa gốm sứ qua các triều đại."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
        )
        
        if response and response.choices:
            content = response.choices[0].message.content
            return content.strip() if content else None
        return None
        
    except Exception as e:
        print(f"[LLM/OpenAI] ❌ Error: {e}")
        traceback.print_exc()
        return None


async def call_ollama_wrapper(prompt: str, temperature: float = 0.3, max_tokens: int = 2048) -> Optional[str]:
    """Wrapper để gọi Ollama service."""
    if not _ollama_available:
        return None
    return await _call_ollama_impl(prompt, temperature=temperature, max_tokens=max_tokens)


async def call_llm(
    prompt: str,
    provider: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    retry: int = 1,
) -> Optional[str]:
    """
    Gọi LLM với fallback tự động.
    
    Nếu provider chính lỗi, tự động thử provider phụ.
    Hỗ trợ: Ollama (local), Gemini (cloud), OpenAI (cloud)
    
    Args:
        prompt: Nội dung prompt
        provider: "ollama", "gemini", "openai", hoặc None (dùng PRIMARY_LLM từ config)
        temperature: Override nhiệt độ (None = dùng config)
        max_tokens: Override max tokens (None = dùng config)
        retry: Số lần retry khi lỗi
        
    Returns:
        Text response hoặc None nếu cả 3 provider đều lỗi
    """
    from config import PRIMARY_LLM, LLM_TEMPERATURE, LLM_MAX_TOKENS
    
    _provider = provider or PRIMARY_LLM
    _temp = temperature if temperature is not None else LLM_TEMPERATURE
    _max = max_tokens if max_tokens is not None else LLM_MAX_TOKENS
    
    # Xác định thứ tự thử (primary provider trước, sau đó fallback)
    if _provider == "ollama":
        providers = [
            ("ollama", call_ollama_wrapper),
            ("gemini", call_gemini),
            ("openai", call_openai),
        ]
    elif _provider == "openai":
        providers = [
            ("openai", call_openai),
            ("gemini", call_gemini),
            ("ollama", call_ollama_wrapper),
        ]
    else:  # gemini (default)
        providers = [
            ("gemini", call_gemini),
            ("openai", call_openai),
            ("ollama", call_ollama_wrapper),
        ]
    
    for name, call_fn in providers:
        for attempt in range(retry + 1):
            try:
                result = await call_fn(prompt, temperature=_temp, max_tokens=_max)
                if result:
                    if name != _provider:
                        print(f"[LLM] ⚠ Fallback sang {name} thành công")
                    else:
                        print(f"[LLM] ✅ {name.upper()} response ok")
                    return result
            except Exception as e:
                print(f"[LLM/{name}] Error: {e}")
            
            if attempt < retry:
                wait = 3 * (attempt + 1)  # 3s, 6s...
                print(f"[LLM/{name}] ⏳ Retry sau {wait}s...")
                await asyncio.sleep(wait)
    
    print("[LLM] ❌ Tất cả provider đều lỗi!")
    return None


# ============================================================
# Prompt Templates — Chuyên biệt cho phân tích hiệu đề
# ============================================================

PROMPT_EXTRACT_INFO = """Bạn là chuyên gia phân tích hiệu đề (reign marks) trên gốm sứ cổ Trung Quốc và Việt Nam.

CRITICAL LAYOUT RULE:
Chinese reign marks on ceramic bases are ALWAYS written in vertical columns, read RIGHT-TO-LEFT, TOP-TO-BOTTOM.
- 4-character mark: Column RIGHT (char1 top + char2 bottom), Column LEFT (char3 top + char4 bottom)
- 6-character mark: Column RIGHT (char1, char2, char3), Column LEFT (char4, char5, char6)
NEVER read left-to-right as horizontal text.

CERAMIC OCR CONFUSION TABLE (common misreads on small blue-and-white script):
  杜 ↔ 右 (stroke density similar)    社 ↔ 礼 (radical confusion)
  内 ↔ 肉 (nearly identical)          府 ↔ 付 (missing strokes)
  侍 ↔ 待 ↔ 停 ↔ 仃 ↔ 亭 (bộ 亻, PaddleOCR rất hay nhầm — 停 trên gốm LUÔN là 侍)
  石 ↔ 北 (stroke pattern)            大 ↔ 太/天 (extra/missing stroke)
  製 ↔ 制 ↔ 装 ↔ 裝 (variant forms)   緒 ↔ 绪 ↔ 结 ↔ 結 (variant forms)
  康 ↔ 泰 (PaddleOCR thường đọc sai)  造 ↔ 遣 (radical similarity)
  南 ↔ 男 (stroke similarity)          旨 ↔ 宕 (radical confusion)
  統 ↔ 统 (traditional/simplified)     曆 ↔ 历 (traditional/simplified)

CRITICAL INCOMPLETE OCR RECOVERY:
  OCR engines frequently MISS characters, especially:
  - The 4th character of 4-char marks (內府侍X → OCR reads only 內府侍 or 府停内)
  - The 3rd-4th characters of 6-char marks (大清XX年製 → OCR reads 大清年製)
  - Characters at the edge of the image or in blurred areas

  When OCR text is SHORTER than expected mark length:
  - If 2-3 chars contain 內/府 → this is likely 內府侍X (4-char workshop mark), find the missing suffix
  - If 4-5 chars contain 大清/大明/大南 + 年/製 → this is likely 6-char dynasty mark, find the missing reign chars
  - ALWAYS return the COMPLETE mark in "chu_han", inferring missing characters from context
  - Flag inferred characters in "ghi_chu"

KNOWN MARK TYPES to validate against:
  - 大明XX年製 / 大清XX年製 / 大南XX年製 = Dynasty reign marks (6 chars)
  - 内府侍X = Vietnamese Nguyễn dynasty Imperial workshop marks:
    內府侍東, 內府侍南, 內府侍北, 內府侍右, 內府侍左, 內府侍中, 內府侍從, 內府侍旨, 內府侍兌
  - 停 trên gốm sứ Huế LUÔN LUÔN là 侍 bị OCR đọc sai. Không tồn tại hiệu đề nào chứa 停.
  - Nếu OCR text dạng 府停内 / 内府停 / 停内府 → đây là 內府侍X bị sai thứ tự + thiếu ký tự cuối
  - Với nhóm 內府侍X, KHÔNG đổi 東 thành 從 nếu OCR/ảnh vẫn thấy nét của chữ 東
  - 4-char marks: XX年製, XX年造, 天下太平, 萬壽無疆, 福壽康寧, 若深珍藏, etc.
  - 2-char marks: 內府, 御製, 清玩, 珍玩, 雅玉, etc.
  - If assembled mark is NOT found in known types → flag which characters are uncertain

Dưới đây là text chữ Hán được OCR đọc từ đáy một món gốm sứ:

**Chữ Hán OCR: "{ocr_text}"**

Hãy phân tích và trả về thông tin dưới dạng JSON (CHỈNH SỬA TRƯỚC KHI TRẢ VỀ nếu có lỗi OCR rõ ràng):

```json
{{
    "chu_han": "Chữ Hán đúng (đã sửa lỗi OCR + KHÔI PHỤC ký tự thiếu nếu có)",
    "trieu_dai": "Triều đại (Minh Triều / Thanh Triều / Nhà Nguyễn (Việt Nam) / Đặc biệt - Cung đình / Khác)",
    "nien_hieu": "Niên hiệu (ví dụ: Tuyên Đức, Khang Hy, Càn Long, Nội Phủ Thị Tòng...)",
    "hoang_de": "Tên hoàng đế",
    "nam_bat_dau": "Năm bắt đầu niên hiệu (số nguyên hoặc null)",
    "nam_ket_thuc": "Năm kết thúc niên hiệu (số nguyên hoặc null)",
    "phien_am": "Phiên âm Hán-Việt đầy đủ",
    "y_nghia": "Ý nghĩa của hiệu đề, mô tả ngắn gọn",
    "do_tin_cay": "Độ tin cậy của phân tích (0.0 → 1.0)",
    "ghi_chu": "Ghi chú thêm (lỗi OCR đã sửa, ký tự đã khôi phục, ký tự không chắc chắn)",
    "layout": "2-col vertical / 3-col vertical / horizontal / unknown"
}}
```

Lưu ý:
- Nếu text quá ngắn hoặc thiếu ký tự, hãy CỐ GẮNG SUY LUẬN mark đầy đủ từ ngữ cảnh hiệu đề gốm sứ.
- Nếu phát hiện lỗi OCR phổ biến (ví dụ: 得→德, 請→靖, 厤→曆, 杜→右, 待→侍, 停→侍), hãy sửa trong "chu_han".
- Nếu mark chứa 内府 hoặc 內府, đây là hiệu đề xưởng gốm Nội Phủ (Imperial Household Bureau) thuộc triều Nguyễn Việt Nam.
- QUAN TRỌNG: chu_han phải trả về ĐÚNG SỐ KÝ TỰ theo dạng mark (4 hoặc 6 ký tự), không được thiếu.
- Trả về JSON hợp lệ, không thêm markdown hay text thừa bên ngoài JSON.
"""

PROMPT_VERIFY_INFO = """Bạn là chuyên gia lịch sử gốm sứ cổ. Hãy kiểm tra lại thông tin phân tích hiệu đề dưới đây:

**Thông tin cần kiểm tra:**
{analysis_json}

**Chữ Hán OCR gốc:** "{ocr_text}"

Hãy kiểm tra tính chính xác và trả về JSON:

```json
{{
    "is_correct": true/false,
    "confidence": 0.0 → 1.0,
    "corrections": {{
        "field_name": "giá trị đúng"
    }},
    "explanation": "Giải thích ngắn gọn lý do xác nhận/sửa chữa",
    "verified_result": {{
        "chu_han": "...",
        "trieu_dai": "...",
        "nien_hieu": "...",
        "hoang_de": "...",
        "nam_bat_dau": null,
        "nam_ket_thuc": null,
        "phien_am": "...",
        "y_nghia": "..."
    }}
}}
```

Kiểm tra các điểm sau:
1. Niên hiệu có đúng triều đại không? (ví dụ: Tuyên Đức thuộc Minh, không phải Thanh)
2. Năm bắt đầu/kết thúc có chính xác không?
3. Phiên âm Hán-Việt có đúng không?
4. Chữ Hán có bị nhầm lẫn với hiệu đề khác không?
"""

PROMPT_SYNTHESIZE_SEARCH = """Bạn là chuyên gia gốm sứ cổ. Dưới đây là thông tin thu thập từ nhiều nguồn web về một hiệu đề gốm sứ.

**Chữ Hán OCR (nếu có):** "{ocr_text}"

**Các bài viết tham khảo:**
{articles}

Dựa trên các bài viết trên, hãy tổng hợp thông tin về hiệu đề này và trả về JSON:

```json
{{
    "chu_han": "Chữ Hán chính xác",
    "trieu_dai": "Triều đại",
    "nien_hieu": "Niên hiệu",
    "hoang_de": "Hoàng đế",
    "nam_bat_dau": null,
    "nam_ket_thuc": null,
    "phien_am": "Phiên âm Hán-Việt",
    "y_nghia": "Ý nghĩa tổng hợp từ các bài viết",
    "do_tin_cay": 0.0 → 1.0,
    "nguon_tham_khao": ["URL1", "URL2", ...]
}}
```

Lưu ý:
- Ưu tiên thông tin từ nguồn học thuật/bảo tàng hơn blog cá nhân.
- Nếu các nguồn mâu thuẫn nhau, chọn thông tin phổ biến nhất và ghi chú sự khác biệt.
- Trả về JSON hợp lệ, không markdown.
"""


# ============================================================
# Helper — Parse JSON response từ LLM
# ============================================================

def parse_llm_json(response: str) -> Optional[Dict[str, Any]]:
    """
    Parse JSON từ response LLM (có thể chứa markdown code block).
    
    LLM thường trả về:
        ```json
        { ... }
        ```
    Hàm này tự động strip markdown wrapper.
    """
    if not response:
        return None
    
    text = response.strip()
    
    # Xóa markdown code block nếu có
    if text.startswith("```"):
        # Tìm dòng đầu tiên kết thúc bằng ``` và dòng cuối cùng bắt đầu bằng ```
        lines = text.split("\n")
        start = 0
        end = len(lines)
        for i, line in enumerate(lines):
            if line.strip().startswith("```") and i == 0:
                start = 1
            elif line.strip() == "```":
                end = i
                break
        text = "\n".join(lines[start:end])
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Thử tìm JSON object trong text
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            try:
                return json.loads(text[brace_start:brace_end + 1])
            except json.JSONDecodeError:
                pass
    
    print(f"[LLM] ⚠ Không thể parse JSON từ response: {text[:200]}...")
    return None
