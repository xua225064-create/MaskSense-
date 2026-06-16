"""
Vision service for direct mark reading from the uploaded image.

This is intentionally separate from web search: the model reads visible
characters from the image, then evidence_service decides whether web sources
confirm the candidate.
"""
import asyncio
import base64
import json
import os
import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from services.llm_service import parse_llm_json


VISION_MARK_PROMPT = """You are reading the visible Chinese/Han characters in a ceramic mark.

Use image evidence only. Do not guess a famous mark from memory. Do not let examples or prior knowledge override visible strokes.

Rules:
- Read every visible character in the mark.
- Many square seal marks have 4 characters arranged as two vertical columns. For those, read the right column top-to-bottom, then the left column top-to-bottom.
- If the layout is uncertain, provide candidates and lower confidence.
- Count visible characters. Most marks have 2, 4, or 6 characters.
- Do not invent dynasty, emperor, period, or historical details. This step only reads text.

Return valid JSON only:
{
  "visible_text_raw": "characters as visually arranged if possible",
  "char_count": 4,
  "chu_han": "best reading in correct order",
  "chu_han_candidates": [
    {"text": "candidate 1", "confidence": 0.0, "reason": "visual stroke reason"}
  ],
  "reading_order": "one of: right-to-left vertical, left-to-right, unknown",
  "uncertain_chars": ["char position / reason"],
  "is_neifu": false,
  "not_enough_detail": false,
  "confidence": 0.0,
  "notes": "short visual explanation"
}
"""

_CJK_TRANS = str.maketrans({
    "\u7eea": "\u7dd2",
    "\u7edf": "\u7d71",
    "\u5386": "\u66c6",
    "\u4e07": "\u842c",
    "\u5236": "\u88fd",
    "\u5185": "\u5167",
    "\u4e1c": "\u6771",
    "\u4ece": "\u5f9e",
})

_NEIFU_SUFFIXES = {"左", "右", "旨", "南", "中", "東", "北", "兌", "兼", "從"}
_NEIFU_CONFUSIONS = str.maketrans({
    "内": "內",
    "东": "東",
    "从": "從",
    "兑": "兌",
    "待": "侍",
    "持": "侍",
    "特": "侍",
    "寺": "侍",
    "停": "侍",
    "仃": "侍",
    "亭": "侍",
})


def normalize_cjk(value: Optional[str]) -> str:
    if not value:
        return ""
    return "".join(ch for ch in value if "\u4e00" <= ch <= "\u9fff").translate(_CJK_TRANS)


def _canonicalize_neifu_order(value: str) -> str:
    clean = normalize_cjk(value).translate(_NEIFU_CONFUSIONS)
    if not clean:
        return ""
    if not all(ch in clean for ch in ("內", "府", "侍")):
        return clean
    suffixes = [ch for ch in clean if ch in _NEIFU_SUFFIXES]
    if not suffixes:
        return clean
    return "內府侍" + suffixes[0]


def is_unknown_neifu_suffix(value: str) -> bool:
    clean = normalize_cjk(value).translate(_NEIFU_CONFUSIONS)
    if not clean.startswith("內府侍"):
        return False
    if len(clean) < 4:
        return False
    return clean[3] not in _NEIFU_SUFFIXES


def _mime_from_bytes(image_bytes: bytes) -> str:
    if image_bytes.startswith(b"\x89PNG"):
        return "image/png"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def _resolve_opencode_command() -> str:
    appdata = os.environ.get("APPDATA")
    candidates = [
        os.path.join(appdata, "npm", "opencode.cmd") if appdata else "",
        shutil.which("opencode.exe"),
        shutil.which("opencode.cmd"),
        os.path.join(appdata, "npm", "node_modules", "opencode-ai", "bin", "opencode.exe") if appdata else "",
        shutil.which("opencode"),
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate) and not candidate.lower().endswith(".ps1"):
            return candidate
    return "opencode.cmd" if os.name == "nt" else "opencode"


def _center_crop_for_mark(image_bytes: bytes) -> Tuple[bytes, Dict[str, Any]]:
    """Create a crop optimized for mark reading."""
    try:
        import cv2
        import numpy as np

        arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return image_bytes, {"used": False, "reason": "decode_failed"}

        ocr_style_crop = _ocr_style_crop_for_vision(img)
        if ocr_style_crop:
            return ocr_style_crop

        red_crop = _red_mark_crop_for_vision(img)
        if red_crop:
            return red_crop

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
            "strategy": "center_crop",
            "x": x1,
            "y": y1,
            "w": x2 - x1,
            "h": y2 - y1,
            "scale": round(scale, 3),
            "image_base64": base64.b64encode(encoded.tobytes()).decode("ascii"),
        }
    except Exception as exc:
        return image_bytes, {"used": False, "reason": str(exc)}


def _encode_vision_crop(crop: Any, meta: Dict[str, Any], quality: int = 94) -> Optional[Tuple[bytes, Dict[str, Any]]]:
    try:
        import cv2

        if crop is None or crop.size == 0:
            return None
        scale = max(1.0, min(5.0, 1000.0 / max(crop.shape[:2])))
        if scale > 1.05:
            crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        ok, encoded = cv2.imencode(".jpg", crop, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if not ok:
            return None
        data = encoded.tobytes()
        return data, {
            **meta,
            "used": True,
            "scale": round(scale, 3),
            "image_base64": base64.b64encode(data).decode("ascii"),
        }
    except Exception:
        return None


def _ocr_style_crop_for_vision(img: Any) -> Optional[Tuple[bytes, Dict[str, Any]]]:
    """Prefer OCR's text-focused ROIs so vision models see the mark, not the bowl rim."""
    try:
        from ocr_engine import (
            detect_ink_text_roi,
            detect_center_square_roi,
            detect_inner_mark_circle_roi,
            extract_center_box_roi,
        )

        detectors = [
            ("ink_text_roi", detect_ink_text_roi),
            ("center_square_roi", detect_center_square_roi),
            ("inner_circle_roi", detect_inner_mark_circle_roi),
            ("center_box_roi", lambda source: extract_center_box_roi(source, ratio=0.30)),
        ]
        for strategy, detector in detectors:
            crop = detector(img)
            encoded = _encode_vision_crop(crop, {"strategy": strategy}, quality=95)
            if encoded:
                return encoded
    except Exception:
        return None
    return None


def _red_mark_crop_for_vision(img: Any) -> Optional[Tuple[bytes, Dict[str, Any]]]:
    """Find a red/orange seal near image center and return a tight enlarged crop."""
    try:
        import cv2
        import numpy as np

        h, w = img.shape[:2]
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        mask_red1 = cv2.inRange(hsv, np.array([0, 35, 45]), np.array([18, 255, 255]))
        mask_red2 = cv2.inRange(hsv, np.array([168, 35, 45]), np.array([180, 255, 255]))
        mask_orange = cv2.inRange(hsv, np.array([10, 30, 55]), np.array([32, 255, 255]))
        mask = cv2.bitwise_or(cv2.bitwise_or(mask_red1, mask_red2), mask_orange)

        cx, cy = w / 2.0, h / 2.0
        central = np.zeros_like(mask)
        margin_x = int(w * 0.18)
        margin_y = int(h * 0.16)
        central[margin_y:h - margin_y, margin_x:w - margin_x] = 255
        mask = cv2.bitwise_and(mask, central)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = cv2.dilate(mask, kernel, iterations=2)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        best = None
        for contour in contours:
            x, y, bw, bh = cv2.boundingRect(contour)
            area = bw * bh
            if area < max(35, (w * h) * 0.00008):
                continue
            if area > (w * h) * 0.08:
                continue
            squareness = min(bw, bh) / max(bw, bh)
            if squareness < 0.35:
                continue
            mx = x + bw / 2.0
            my = y + bh / 2.0
            center_dist = ((mx - cx) ** 2 + (my - cy) ** 2) ** 0.5
            if center_dist > max(h, w) * 0.32:
                continue
            score = center_dist - min(area, 5000) * 0.02 - squareness * 80
            if best is None or score < best[0]:
                best = (score, x, y, bw, bh)
        if not best:
            return None

        _, x, y, bw, bh = best
        side = int(max(bw, bh) * 2.25)
        side = max(side, 160)
        mx = x + bw // 2
        my = y + bh // 2
        x1 = max(0, mx - side // 2)
        y1 = max(0, my - side // 2)
        x2 = min(w, x1 + side)
        y2 = min(h, y1 + side)
        x1 = max(0, x2 - side)
        y1 = max(0, y2 - side)
        crop = img[y1:y2, x1:x2]
        if crop.size == 0:
            return None

        scale = max(1.0, min(5.0, 1000.0 / max(crop.shape[:2])))
        if scale > 1.05:
            crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        ok, encoded = cv2.imencode(".jpg", crop, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        if not ok:
            return None
        return encoded.tobytes(), {
            "used": True,
            "strategy": "red_mark_center",
            "x": x1,
            "y": y1,
            "w": x2 - x1,
            "h": y2 - y1,
            "mark_box": {"x": x, "y": y, "w": bw, "h": bh},
            "scale": round(scale, 3),
            "image_base64": base64.b64encode(encoded.tobytes()).decode("ascii"),
        }
    except Exception:
        return None


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
        return f"{provider}: háº¿t quota hoáº·c bá»‹ rate limit (429)"
    if "401" in raw or "api key" in lowered or "unauthorized" in lowered:
        return f"{provider}: API key khÃ´ng há»£p lá»‡ hoáº·c chÆ°a Ä‘Æ°á»£c cáº¥p quyá»n"
    if "timeout" in lowered:
        return f"{provider}: timeout"
    if "model" in lowered and ("not found" in lowered or "does not exist" in lowered):
        return f"{provider}: model khÃ´ng kháº£ dá»¥ng"
    compact = raw.replace("\n", " ").strip()
    if len(compact) > 180:
        compact = compact[:177] + "..."
    return f"{provider}: {compact or exc.__class__.__name__}"


async def analyze_mark_image(
    image_bytes: bytes,
    provider: Optional[str] = None,
    allow_fallback: bool = True,
) -> Dict[str, Any]:
    """Read visible mark text using a multimodal model."""
    crop_bytes, crop_meta = _center_crop_for_mark(image_bytes)
    provider_order = _provider_order(provider)
    if provider and not allow_fallback:
        requested = provider.lower()
        provider_order = [name for name in provider_order if name == requested] or [requested]
    errors = []
    for name in provider_order:
        try:
            if name == "gemini":
                response = await _call_gemini_vision(image_bytes, crop_bytes)
            elif name == "openai":
                response = await _call_openai_vision(image_bytes, crop_bytes)
            elif name == "opencode":
                response = await _call_opencode_vision(image_bytes, crop_bytes)
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
            canonical_primary = _canonicalize_neifu_order(primary)
            if canonical_primary and canonical_primary != primary:
                parsed["chu_han_before_order_normalize"] = primary
                primary = canonical_primary
                if candidates:
                    candidates[0] = {**candidates[0], "text": primary, "reason": (candidates[0].get("reason", "") + "; normalized Nội Phủ order").strip("; ")}
            unknown_neifu_suffix = is_unknown_neifu_suffix(primary)
            for idx, item in enumerate(candidates):
                fixed_text = _canonicalize_neifu_order(item.get("text", ""))
                if fixed_text and fixed_text != item.get("text", ""):
                    candidates[idx] = {**item, "text": fixed_text, "reason": (item.get("reason", "") + "; normalized Nội Phủ order").strip("; ")}
                if is_unknown_neifu_suffix(fixed_text or item.get("text", "")):
                    unknown_neifu_suffix = True
            raw_confidence = float(parsed.get("confidence") or 0.0)
            candidate_confidence = candidates[0]["confidence"] if candidates else 0.0
            confidence = raw_confidence or candidate_confidence
            if primary and confidence <= 0.0:
                confidence = 0.55
                parsed["confidence_was_defaulted"] = True
            if unknown_neifu_suffix:
                confidence = min(confidence, 0.42)
                parsed["unknown_neifu_suffix"] = True
                parsed["allow_partial_db_match"] = False
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
    if requested == "opencode":
        order.append("opencode")
        if GEMINI_API_KEY:
            order.append("gemini")
        if OPENAI_API_KEY:
            order.append("openai")
        return order or ["opencode", "gemini", "openai"]
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
    order.append("opencode")
    if OPENAI_API_KEY:
        order.append("openai")
    order.append("ollama")
    return order or ["gemini", "opencode", "openai", "ollama"]


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


async def _call_opencode_vision(image_bytes: bytes, crop_bytes: bytes) -> Optional[str]:
    from config import OPENCODE_TIMEOUT, OPENCODE_VISION_MODEL

    app_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    project_root = os.path.abspath(os.path.join(app_root, ".."))
    def _rel(path: str) -> str:
        return os.path.relpath(path, project_root).replace(os.sep, "/")

    def _strip_ansi(text: str) -> str:
        return re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text or "")

    def _call() -> Optional[str]:
        original_path = os.path.join(app_root, "opencode_vision_original.jpg")
        crop_path = os.path.join(app_root, "opencode_vision_crop.jpg")
        try:
            with open(original_path, "wb") as fh:
                fh.write(image_bytes)
            with open(crop_path, "wb") as fh:
                fh.write(crop_bytes)

            prompt = (
                f"You are a JSON API. Look at @{_rel(crop_path)}. "
                "Reply with raw JSON only. First character must be {. "
                "Schema: {\"visible_text_raw\":\"\",\"char_count\":0,"
                "\"chu_han\":\"\",\"chu_han_candidates\":[{\"text\":\"\",\"confidence\":0.0,\"reason\":\"\"}],"
                "\"reading_order\":\"one of: right-to-left vertical, left-to-right, unknown\","
                "\"uncertain_chars\":[],\"is_neifu\":false,\"not_enough_detail\":false,"
                "\"confidence\":0.0,\"notes\":\"\"}. "
                "Do not use markdown. Do not explain. Read only visible Chinese/Han characters."
            )
            opencode_command = _resolve_opencode_command()
            runtime_root = os.path.join(app_root, ".opencode-runtime")
            opencode_env = os.environ.copy()
            opencode_env.setdefault("XDG_CONFIG_HOME", os.path.join(runtime_root, "config"))
            opencode_env.setdefault("XDG_CACHE_HOME", os.path.join(runtime_root, "cache"))
            opencode_env.setdefault("XDG_DATA_HOME", os.path.join(runtime_root, "data"))
            for env_path in (
                opencode_env["XDG_CONFIG_HOME"],
                opencode_env["XDG_CACHE_HOME"],
                opencode_env["XDG_DATA_HOME"],
            ):
                os.makedirs(env_path, exist_ok=True)
            completed = subprocess.run(
                [opencode_command, "run", "-m", OPENCODE_VISION_MODEL, prompt],
                cwd=project_root,
                env=opencode_env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=max(30, OPENCODE_TIMEOUT),
            )
            output = _strip_ansi((completed.stdout or "") + "\n" + (completed.stderr or ""))
            if completed.returncode != 0:
                raise RuntimeError(output.strip() or f"opencode exited with {completed.returncode}")
            return output.strip()
        finally:
            for path in (original_path, crop_path):
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except OSError:
                    pass

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
            "num_predict": 900,
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
            with urllib_request.urlopen(req, timeout=max(180, OLLAMA_TIMEOUT)) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib_error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(detail or f"Ollama HTTP {exc.code}") from exc
        except urllib_error.URLError as exc:
            raise RuntimeError(f"Cannot connect to Ollama at {OLLAMA_BASE_URL}: {exc.reason}") from exc

        if isinstance(data, dict) and data.get("error"):
            raise RuntimeError(str(data.get("error")))
        if not isinstance(data, dict):
            return None
        return (data.get("response") or data.get("thinking") or "").strip()

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _call)
