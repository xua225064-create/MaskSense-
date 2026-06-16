import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def is_quota_error(text: str) -> bool:
    lowered = (text or "").lower()
    return "429" in lowered or "quota" in lowered or "rate limit" in lowered or "resource_exhausted" in lowered


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--models",
        default="",
        help="Comma-separated model names. Defaults to VISION_MODEL plus common benchmark models.",
    )
    args = parser.parse_args()

    load_dotenv(ROOT / ".env", override=True)
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    vision_model = os.getenv("VISION_MODEL", "").strip()
    default_models = [
        vision_model,
        "gemini-3.1-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
    ]
    models = [item.strip() for item in (args.models.split(",") if args.models else default_models) if item.strip()]
    models = list(dict.fromkeys(models))

    if not api_key:
        print("GEMINI_API_KEY: missing")
        raise SystemExit(2)

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    for model in models:
        try:
            resp = client.models.generate_content(
                model=model,
                contents="Return only: ok",
                config=types.GenerateContentConfig(
                    temperature=0,
                    max_output_tokens=8,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
            text = (resp.text or "").strip() if resp else ""
            print(f"{model}: OK ({text[:20] or 'empty'})")
        except Exception as exc:
            raw = str(exc).replace("\n", " ")
            status = "QUOTA_OR_RATE_LIMIT" if is_quota_error(raw) else "ERROR"
            if len(raw) > 180:
                raw = raw[:177] + "..."
            print(f"{model}: {status} - {raw}")


if __name__ == "__main__":
    main()
