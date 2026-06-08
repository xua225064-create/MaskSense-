"""
Ollama Service — Tích hợp local LLM từ Ollama.

Ollama cho phép chạy LLM trên máy local (không cần API key):
- Miễn phí (chỉ cần GPU/CPU)
- Mất ~5-30s per request (tùy model + hardware)
- Bảo mật cao (dữ liệu không gửi cloud)
- Hỗ trợ nhiều model: neural-chat, mistral, llama2, qwen, etc.

Cài đặt: https://ollama.ai
Pull model: ollama pull neural-chat

Sử dụng:
  async result = await call_ollama(prompt="Xác định hiệu đề: ...")
"""
import asyncio
import traceback
from typing import Optional


async def call_ollama(
    prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    timeout: int = 120,
) -> Optional[str]:
    """
    Gọi Ollama API (local inference) sử dụng ollama Python library.
    
    Args:
        prompt: Nội dung prompt
        temperature: Nhiệt độ (0.0-1.0)
        max_tokens: Số token tối đa output
        timeout: Timeout (giây) - để cao vì inference local chậm
        
    Returns:
        Text response hoặc None nếu lỗi
    """
    from config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT
    import ollama
    
    try:
        # Tính timeout thực tế
        actual_timeout = max(timeout, OLLAMA_TIMEOUT)
        
        # Hệ thống prompt cho chuyên gia gốm sứ
        system_prompt = (
            "Bạn là chuyên gia về gốm sứ cổ Trung Quốc và Việt Nam. "
            "Bạn có kiến thức sâu về hiệu đề (reign marks) trên đáy bát, "
            "đĩa, lọ hoa gốm sứ qua các triều đại. Trả lời ngắn gọn, chính xác."
        )
        
        # Gọi Ollama (chạy trong executor vì blocking)
        loop = asyncio.get_event_loop()
        
        async def _call_ollama():
            def _sync_call():
                # Tạo client (library ollama tự kết nối tới localhost:11434)
                client = ollama.Client(host=OLLAMA_BASE_URL)
                
                response = client.generate(
                    model=OLLAMA_MODEL,
                    prompt=prompt,
                    system=system_prompt,
                    stream=False,
                    options={
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    }
                )
                
                if "response" in response:
                    return response["response"].strip()
                return None
            
            return await loop.run_in_executor(None, _sync_call)
        
        # Thực hiện call với timeout
        result = await asyncio.wait_for(_call_ollama(), timeout=actual_timeout)
        
        if result:
            print(f"[LLM/Ollama] ✅ Response ({len(result)} chars)")
            return result
        return None
        
    except asyncio.TimeoutError:
        print(f"[LLM/Ollama] ⏱️ Timeout sau {actual_timeout}s")
        print(f"[LLM/Ollama] 💡 Model {OLLAMA_MODEL} chậm, thử model nhẹ hơn (e.g., mistral, orca-mini)")
        return None
    except (ConnectionError, Exception) as e:
        err_str = str(e)
        if "Connection" in err_str or "refused" in err_str:
            print(f"[LLM/Ollama] ❌ Không thể kết nối Ollama ({OLLAMA_BASE_URL})")
            print(f"[LLM/Ollama] 💡 Hãy cài Ollama: https://ollama.ai")
            print(f"[LLM/Ollama] 💡 Sau đó chạy: ollama serve")
        else:
            print(f"[LLM/Ollama] ❌ Error: {e}")
            traceback.print_exc()
        return None


async def health_check() -> bool:
    """
    Kiểm tra Ollama server có chạy không.
    
    Returns:
        True nếu Ollama chạy và model available, False nếu không
    """
    from config import OLLAMA_BASE_URL, OLLAMA_MODEL
    import ollama
    
    try:
        # Kiểm tra server live + list models
        client = ollama.Client(host=OLLAMA_BASE_URL)
        models = client.list()
        
        model_names = [m.get("name", "") for m in models.get("models", [])]
        
        if not model_names:
            print(f"[Ollama] ⚠ Không có model nào được pull")
            print(f"[Ollama] 💡 Chạy: ollama pull {OLLAMA_MODEL}")
            return False
        
        # Kiểm tra model cụ thể
        if any(OLLAMA_MODEL in name for name in model_names):
            print(f"[Ollama] ✅ Model '{OLLAMA_MODEL}' ready")
            print(f"[Ollama] 📦 Available models: {', '.join([n.split(':')[0] for n in model_names[:5]])}")
            return True
        else:
            print(f"[Ollama] ⚠ Model '{OLLAMA_MODEL}' chưa được pull")
            print(f"[Ollama] 💡 Chạy: ollama pull {OLLAMA_MODEL}")
            print(f"[Ollama] 📦 Available: {', '.join([n.split(':')[0] for n in model_names[:5]])}")
            return False
                
    except ConnectionError:
        print(f"[Ollama] ❌ Không thể kết nối {OLLAMA_BASE_URL}")
        print(f"[Ollama] 💡 Ollama chưa chạy. Chạy lệnh:")
        print(f"[Ollama]    ollama serve")
        return False
    except Exception as e:
        print(f"[Ollama] ❌ Health check lỗi: {e}")
        traceback.print_exc()
        return False


# Dùng cho startup check
async def initialize_ollama():
    """
    Khởi tạo Ollama khi app start.
    Kiểm tra server + model availability.
    """
    print("[Ollama] 🚀 Initializing Ollama...")
    is_healthy = await health_check()
    
    if is_healthy:
        print("[Ollama] ✅ Ollama ready to use!")
        return True
    else:
        print("[Ollama] ⚠ Ollama not available - will fallback to Gemini/OpenAI")
        return False
