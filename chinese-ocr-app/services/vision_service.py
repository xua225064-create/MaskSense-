"""
Vision service for direct mark reading from the uploaded image.

This is intentionally separate from web search: the model reads visible
characters from the image, then evidence_service decides whether web sources
confirm the candidate.
"""
import asyncio
import base64
import json
from typing import Any, Dict, List, Optional, Tuple

from services.llm_service import parse_llm_json


VISION_MARK_PROMPT = """You are reading a ceramic reign/workshop mark from an image.

Task:
- Read ALL visible Chinese/Han characters in the mark. Do NOT skip any character.
- Ceramic marks are often written in vertical columns. Read right column first, top-to-bottom, then left column top-to-bottom.
- Do not replace a visible character with a more common mark from memory.
- For 內府侍X marks, keep the fourth character as seen. If it looks like 東, return 內府侍東; do not change 東 to 從.
- If a character is uncertain, return candidates instead of pretending certainty.
- Common OCR confusions on blue-and-white ceramics:
  停/待/仃/亭 are ALWAYS 侍 (shi) on ceramics — there is no mark containing 停
  石/白 are often 北 (bei)
  杜/社 are often 右 (you)
  泰 is often 康 (kang)
  装/裝 are often 製 (zhi)

IMPORTANT: Count the characters visible in the mark. Most marks have exactly 2, 4, or 6 characters.
If you see traces of a character but cannot fully read it, still include your best guess with low confidence.

Return valid JSON only:
{
  "visible_text_raw": "characters exactly as visually arranged if possible",
  "char_count": 4,
  "chu_han": "best reading in correct order (MUST have the correct number of characters)",
  "chu_han_candidates": [
    {"text": "candidate 1", "confidence": 0.0, "reason": "visual reason"}
  ],
  "reading_order": "right-to-left vertical | left-to-right | unknown",
  "uncertain_chars": ["char position / reason"],
  "is_neifu": true,
  "not_enough_detail": false,
  "confidence": 0.0,
  "notes": "short explanation"
}
"""

_CJK_TRANS = str.maketrans({
    "绪": "緒",
    "统": "統",
    "历": "曆",
    "万": "萬",
    "制": "製",
    "内": "內",
    "东": "東",
    "从": "從",
})


def normalize_cjk(value: Optional[str]) -> str:
    if not value:
        return ""
    return "".join(ch for ch in value if "\u4e00" <= ch <= "\u9fff").translate(_CJK_TRANS)


def _mime_from_bytes(image_bytes: bytes) -> str:
    if image_bytes.startswith(b"\x89PNG"):
        return "image/png"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def _center_crop_for_mark(image_bytes: bytes) -> Tuple[bytes, Dict[str, Any]]:
    """Create a conservative center crop for mark reading."""
    try:
        import cv2
        import numpy as np

        arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return image_bytes, {"used": False, "reason": "decode_failed"}

        h, w = img.shape[:2]
        side = int(min(h, w) * 0.72)
        side = max(180, min(side, min(h, w)))
        cx, cy = w // 2, h // 2
        x1 = max(0, cx - side // 2)
        y1 = max(0, cy - side // 2)
        x2 = min(w, x1 + side)
        y2 = min(h, y1 + side)
        crop = img[y1:y2, x1:x2]
        if crop.size == 0:
            return image_bytes, {"used": False, "reason": "empty_crop"}

        scale = max(1.0, min(3.0, 900.0 / max(crop.shape[:2])))
        if scale > 1.05:
            crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        ok, encoded = cv2.imencode(".jpg", crop, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        if not ok:
            return image_bytes, {"used": False, "reason": "encode_failed"}
        return encoded.tobytes(), {
            "used": True,
            "x": x1,
            "y": y1,
            "w": x2 - x1,
            "h": y2 - y1,
            "scale": round(scale, 3),
        }
    except Exception as exc:
        return image_bytes, {"used": False, "reason": str(exc)}


def _extract_candidates(parsed: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates = []
    seen = set()

    def add(text: str, confidence: float, reason: str = "") -> None:
        clean = normalize_cjk(text)
        if not clean or clean in seen:
            return
        seen.add(clean)
        candidates.append({
            "text": clean,
            "confidence": max(0.0, min(float(confidence or 0.0), 1.0)),
            "reason": reason,
        })

    add(parsed.get("chu_han", ""), parsed.get("confidence", 0.0), "primary")
    for item in parsed.get("chu_han_candidates") or []:
        if isinstance(item, dict):
            add(item.get("text", ""), item.get("confidence", 0.0), item.get("reason", ""))
        else:
            add(str(item), 0.45, "candidate")
    return candidates


def _short_error(provider: str, exc: Exception) -> str:
    raw = str(exc)
    lowered = raw.lower()
    if "429" in raw or "resource_exhausted" in lowered or "quota" in lowered or "rate limit" in lowered:
        return f"{provider}: hết quota hoặc bị rate limit (429)"
    if "401" in raw or "api key" in lowered or "unauthorized" in lowered:
        return f"{provider}: API key không hợp lệ hoặc chưa được cấp quyền"
    if "timeout" in lowered:
        return f"{provider}: timeout"
    if "model" in lowered and ("not found" in lowered or "does not exist" in lowered):
        return f"{provider}: model không khả dụng"
    compact = raw.replace("\n", " ").strip()
    if len(compact) > 180:
        compact = compact[:177] + "..."
    return f"{provider}: {compact or exc.__class__.__name__}"


async def analyze_mark_image(
    image_bytes: bytes,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """Read visible mark text using a multimodal model."""
    crop_bytes, crop_meta = _center_crop_for_mark(image_bytes)
    provider_order = _provider_order(provider)
    errors = []
    for name in provider_order:
        try:
            if name == "gemini":
                response = await _call_gemini_vision(image_bytes, crop_bytes)
            elif name == "openai":
                response = await _call_openai_vision(image_bytes, crop_bytes)
            elif name == "ollama":
                response = await _call_ollama_vision(image_bytes, crop_bytes)
            else:
                continue
            if not response:
                errors.append(f"{name}: empty response")
                continue
            parsed = parse_llm_json(response)
            if not parsed:
                errors.append(f"{name}: invalid JSON")
                continue
            candidates = _extract_candidates(parsed)
            primary = candidates[0]["text"] if candidates else normalize_cjk(parsed.get("chu_han", ""))
            confidence = float(parsed.get("confidence") or (candidates[0]["confidence"] if candidates else 0.0))
            parsed.update({
                "provider": name,
                "chu_han": primary,
                "chu_han_candidates": candidates,
                "confidence": max(0.0, min(confidence, 1.0)),
                "crop": crop_meta,
                "status": "success" if primary else "partial",
            })
            return parsed
        except Exception as exc:
            short = _short_error(name, exc)
            print(f"[Vision] {short}")
            errors.append(short)
    return {
        "status": "failed",
        "chu_han": "",
        "chu_han_candidates": [],
        "confidence": 0.0,
        "crop": crop_meta,
        "errors": errors,
    }


def _provider_order(provider: Optional[str]) -> List[str]:
    from config import GEMINI_API_KEY, OPENAI_API_KEY, VISION_PROVIDER

    requested = (provider or VISION_PROVIDER or "auto").lower()
    order = []
    if requested == "ollama":
        order.append("ollama")
        if OPENAI_API_KEY:
            order.append("openai")
        if GEMINI_API_KEY:
            order.append("gemini")
        return order
    if requested == "gemini":
        if GEMINI_API_KEY:
            order.append("gemini")
        if OPENAI_API_KEY:
            order.append("openai")
        order.append("ollama")
        return order or ["gemini", "openai", "ollama"]
    if requested == "openai":
        if OPENAI_API_KEY:
            order.append("openai")
        if GEMINI_API_KEY:
            order.append("gemini")
        order.append("ollama")
        return order or ["openai", "gemini", "ollama"]
    if GEMINI_API_KEY:
        order.append("gemini")
    if OPENAI_API_KEY:
        order.append("openai")
    order.append("ollama")
    return order or ["gemini", "openai", "ollama"]


async def _call_gemini_vision(image_bytes: bytes, crop_bytes: bytes) -> Optional[str]:
    from google import genai
    from google.genai import types
    from config import GEMINI_API_KEY, VISION_MODEL

    if not GEMINI_API_KEY:
        return None

    def _call() -> Optional[str]:
        client = genai.Client(api_key=GEMINI_API_KEY)
        config = types.GenerateContentConfig(
            temperature=0.05,
            max_output_tokens=1600,
            response_mime_type="application/json",
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        )
        contents = [
            VISION_MARK_PROMPT,
            types.Part.from_bytes(data=image_bytes, mime_type=_mime_from_bytes(image_bytes)),
            types.Part.from_bytes(data=crop_bytes, mime_type="image/jpeg"),
        ]
        resp = client.models.generate_content(
            model=VISION_MODEL,
            contents=contents,
            config=config,
        )
        return resp.text.strip() if resp and resp.text else None

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _call)


async def _call_openai_vision(image_bytes: bytes, crop_bytes: bytes) -> Optional[str]:
    from openai import OpenAI
    from config import OPENAI_API_KEY, OPENAI_VISION_MODEL

    if not OPENAI_API_KEY:
        return None

    def data_url(data: bytes, mime: str) -> str:
        return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"

    def _call() -> Optional[str]:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=OPENAI_VISION_MODEL,
            temperature=0.05,
            max_tokens=1600,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_MARK_PROMPT},
                    {"type": "image_url", "image_url": {"url": data_url(image_bytes, _mime_from_bytes(image_bytes))}},
                    {"type": "image_url", "image_url": {"url": data_url(crop_bytes, "image/jpeg")}},
                ],
            }],
        )
        if response and response.choices:
            content = response.choices[0].message.content
            return content.strip() if content else None
        return None

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _call)


async def _call_ollama_vision(image_bytes: bytes, crop_bytes: bytes) -> Optional[str]:
    from urllib import error as urllib_error
    from urllib import request as urllib_request
    from config import OLLAMA_BASE_URL, OLLAMA_TIMEOUT, OLLAMA_VISION_MODEL

    endpoint = OLLAMA_BASE_URL.rstrip("/") + "/api/generate"
    image_payload = [
        base64.b64encode(image_bytes).decode("ascii"),
        base64.b64encode(crop_bytes).decode("ascii"),
    ]
    payload = {
        "model": OLLAMA_VISION_MODEL,
        "prompt": VISION_MARK_PROMPT,
        "images": image_payload,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.05,
            "num_predict": 1600,
        },
    }

    def _call() -> Optional[str]:
        body = json.dumps(payload).encode("utf-8")
        req = urllib_request.Request(
            endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib_request.urlopen(req, timeout=max(30, OLLAMA_TIMEOUT)) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib_error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(detail or f"Ollama HTTP {exc.code}") from exc
        except urllib_error.URLError as exc:
            raise RuntimeError(f"Cannot connect to Ollama at {OLLAMA_BASE_URL}: {exc.reason}") from exc

        if isinstance(data, dict) and data.get("error"):
            raise RuntimeError(str(data.get("error")))
        return (data.get("response") or "").strip() if isinstance(data, dict) else None

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _call)
