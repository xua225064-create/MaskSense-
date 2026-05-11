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
import asyncio
import traceback
from typing import Any, Dict, Optional

# Lazy imports — chỉ import khi thật sự cần dùng
_gemini_client = None
_openai_client = None


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

async def call_gemini(prompt: str, temperature: float = 0.3, max_tokens: int = 2048) -> Optional[str]:
    """
    Gọi Gemini API (google-genai SDK mới).
    
    Args:
        prompt: Nội dung prompt
        temperature: Nhiệt độ (0.0 = chính xác, 1.0 = sáng tạo)
        max_tokens: Số token tối đa trả về
        
    Returns:
        Text response hoặc None nếu lỗi
    """
    client = _get_gemini_client()
    if client is None:
        return None
    
    try:
        from google.genai import types
        from config import GEMINI_MODEL
        
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        
        # Chạy blocking call trong thread pool để không block async event loop
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=config,
            )
        )
        
        if response and response.text:
            return response.text.strip()
        return None
        
    except Exception as e:
        print(f"[LLM/Gemini] ❌ Error: {e}")
        traceback.print_exc()
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
            return response.choices[0].message.content.strip()
        return None
        
    except Exception as e:
        print(f"[LLM/OpenAI] ❌ Error: {e}")
        traceback.print_exc()
        return None


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
    
    Args:
        prompt: Nội dung prompt
        provider: "gemini", "openai", hoặc None (dùng PRIMARY_LLM từ config)
        temperature: Override nhiệt độ (None = dùng config)
        max_tokens: Override max tokens (None = dùng config)
        retry: Số lần retry khi lỗi
        
    Returns:
        Text response hoặc None nếu cả 2 provider đều lỗi
    """
    from config import PRIMARY_LLM, LLM_TEMPERATURE, LLM_MAX_TOKENS
    
    _provider = provider or PRIMARY_LLM
    _temp = temperature if temperature is not None else LLM_TEMPERATURE
    _max = max_tokens if max_tokens is not None else LLM_MAX_TOKENS
    
    # Xác định thứ tự thử
    if _provider == "openai":
        providers = [("openai", call_openai), ("gemini", call_gemini)]
    else:
        providers = [("gemini", call_gemini), ("openai", call_openai)]
    
    for name, call_fn in providers:
        for attempt in range(retry + 1):
            result = await call_fn(prompt, temperature=_temp, max_tokens=_max)
            if result:
                if name != _provider:
                    print(f"[LLM] ℹ Fallback sang {name} thành công")
                return result
            
            if attempt < retry:
                wait = 2 ** attempt  # exponential backoff: 1s, 2s, 4s...
                print(f"[LLM/{name}] ⏳ Retry sau {wait}s...")
                await asyncio.sleep(wait)
    
    print("[LLM] ❌ Tất cả provider đều lỗi!")
    return None


# ============================================================
# Prompt Templates — Chuyên biệt cho phân tích hiệu đề
# ============================================================

PROMPT_EXTRACT_INFO = """Bạn là chuyên gia phân tích hiệu đề (reign marks) trên gốm sứ cổ Trung Quốc và Việt Nam.

Dưới đây là text chữ Hán được OCR đọc từ đáy một món gốm sứ:

**Chữ Hán OCR: "{ocr_text}"**

Hãy phân tích và trả về thông tin dưới dạng JSON (CHỈNH SỬA TRƯỚC KHI TRẢ VỀ nếu có lỗi OCR rõ ràng):

```json
{{
    "chu_han": "Chữ Hán đúng (đã sửa lỗi OCR nếu có)",
    "trieu_dai": "Triều đại (Minh / Thanh / Nguyễn / Khác)",
    "nien_hieu": "Niên hiệu (ví dụ: Tuyên Đức, Khang Hy, Càn Long...)",
    "hoang_de": "Tên hoàng đế",
    "nam_bat_dau": "Năm bắt đầu niên hiệu (số nguyên hoặc null)",
    "nam_ket_thuc": "Năm kết thúc niên hiệu (số nguyên hoặc null)",
    "phien_am": "Phiên âm Hán-Việt đầy đủ",
    "y_nghia": "Ý nghĩa của hiệu đề, mô tả ngắn gọn",
    "do_tin_cay": "Độ tin cậy của phân tích (0.0 → 1.0)",
    "ghi_chu": "Ghi chú thêm nếu có (lỗi OCR đã sửa, biến thể, etc.)"
}}
```

Lưu ý:
- Nếu text quá ngắn hoặc không rõ, hãy cố gắng suy luận từ ngữ cảnh hiệu đề gốm sứ.
- Nếu phát hiện lỗi OCR phổ biến (ví dụ: 得→德, 請→靖, 厤→曆), hãy sửa trong "chu_han".
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
