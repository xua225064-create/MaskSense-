import argparse
import asyncio
import contextlib
import csv
import io
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ocr_engine import read_chinese_mark  # noqa: E402
from services.vision_service import analyze_mark_image, normalize_cjk  # noqa: E402


RESULT_DIR = ROOT / "experiments" / "results"
RESULT_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_GEMINI_MODELS = "gemini-3.1-flash-lite,gemini-2.5-flash,gemini-2.5-flash-lite"


def is_quota_error(value: str) -> bool:
    lowered = (value or "").lower()
    return "429" in lowered or "quota" in lowered or "rate limit" in lowered or "resource_exhausted" in lowered


def image_paths(input_dir: Path) -> List[Path]:
    exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    return sorted(path for path in input_dir.iterdir() if path.is_file() and path.suffix.lower() in exts)


def run_local_system(image_bytes: bytes) -> Dict[str, Any]:
    start = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):
        result = read_chinese_mark(image_bytes, deep_mode=False)
    elapsed = time.perf_counter() - start
    candidates = result.get("candidates") or []
    return {
        "text": normalize_cjk(result.get("text") or ""),
        "confidence": result.get("confidence", ""),
        "candidates": ";".join(normalize_cjk(str(item)) for item in candidates if item),
        "latency": elapsed,
        "status": "success" if result.get("text") or candidates else "partial",
        "error": "",
    }


async def run_voting_system(
    image_bytes: bytes,
    pipelines: List[str],
    timeout: int,
    verify_with_web: bool,
    gemini_model: str = "",
) -> Dict[str, Any]:
    from main import REIGN_DATABASE
    from pipelines.orchestrator import analyze_image
    import config
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=True)
    config.GEMINI_API_KEY = __import__("os").getenv("GEMINI_API_KEY", config.GEMINI_API_KEY)
    config.OPENAI_API_KEY = __import__("os").getenv("OPENAI_API_KEY", config.OPENAI_API_KEY)
    config.VISION_MODEL = __import__("os").getenv("VISION_MODEL", config.VISION_MODEL)
    if gemini_model:
        config.VISION_MODEL = gemini_model

    start = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):
        result = await analyze_image(
            image_bytes,
            database=REIGN_DATABASE,
            pipelines=pipelines,
            timeout=timeout,
            verify_with_web=verify_with_web,
        )
    elapsed = time.perf_counter() - start
    details = result.get("pipeline_details") or []
    quota_errors = [
        f"{item.get('pipeline_name', '')}: {item.get('error_message', '')}"
        for item in details
        if is_quota_error(str(item.get("error_message", "")))
    ]
    valid = [
        item.get("pipeline_name", "")
        for item in details
        if str(item.get("status", "")).lower() == "success"
    ]
    if quota_errors:
        return {
            "text": normalize_cjk(result.get("chu_han") or result.get("hieu_de") or ""),
            "confidence": result.get("confidence", ""),
            "aggregated_confidence": result.get("aggregated_confidence", ""),
            "primary_pipeline": result.get("primary_pipeline", ""),
            "valid_pipelines": ";".join(valid),
            "num_valid_pipelines": result.get("num_valid_pipelines", ""),
            "latency": elapsed,
            "status": "failed_quota",
            "error": " | ".join(quota_errors),
            "gemini_model": config.VISION_MODEL,
            "raw": result,
        }
    return {
        "text": normalize_cjk(result.get("chu_han") or result.get("hieu_de") or ""),
        "confidence": result.get("confidence", ""),
        "aggregated_confidence": result.get("aggregated_confidence", ""),
        "primary_pipeline": result.get("primary_pipeline", ""),
        "valid_pipelines": ";".join(valid),
        "num_valid_pipelines": result.get("num_valid_pipelines", ""),
        "latency": elapsed,
        "status": result.get("status", ""),
        "error": result.get("message", "") or result.get("canh_bao", ""),
        "gemini_model": config.VISION_MODEL,
        "raw": result,
    }


async def run_vision_provider(image_bytes: bytes, provider: str) -> Dict[str, Any]:
    start = time.perf_counter()
    result = await analyze_mark_image(image_bytes, provider=provider, allow_fallback=False)
    elapsed = time.perf_counter() - start
    candidates = result.get("chu_han_candidates") or []
    return {
        "text": normalize_cjk(result.get("chu_han") or ""),
        "confidence": result.get("confidence", ""),
        "candidates": ";".join(normalize_cjk(str(item.get("text") or "")) for item in candidates if isinstance(item, dict)),
        "latency": elapsed,
        "status": result.get("status", ""),
        "error": "; ".join(result.get("errors") or []),
        "raw": result,
    }


async def run_gemini_with_model_rotation(
    image_bytes: bytes,
    models: List[str],
    start_index: int = 0,
) -> Dict[str, Any]:
    import config

    if not models:
        models = [config.VISION_MODEL]
    original_model = config.VISION_MODEL
    attempts = []
    try:
        for offset in range(len(models)):
            model = models[(start_index + offset) % len(models)]
            config.VISION_MODEL = model
            result = await run_vision_provider(image_bytes, "gemini")
            attempts.append({
                "model": model,
                "status": result.get("status", ""),
                "error": result.get("error", ""),
            })
            if result.get("status") in {"success", "partial"} and result.get("text"):
                result["model"] = model
                result["attempts"] = attempts
                return result
        failed = attempts[-1] if attempts else {}
        return {
            "text": "",
            "confidence": "",
            "candidates": "",
            "latency": 0.0,
            "status": "failed",
            "error": " | ".join(
                f"{item.get('model')}: {item.get('error') or item.get('status')}"
                for item in attempts
            ),
            "model": failed.get("model", ""),
            "attempts": attempts,
            "raw": {},
        }
    finally:
        config.VISION_MODEL = original_model


def load_existing_rows(output_prefix: str) -> Dict[str, Dict[str, Any]]:
    csv_path = RESULT_DIR / f"{output_prefix}.csv"
    if not csv_path.exists():
        return {}
    with csv_path.open("r", newline="", encoding="utf-8-sig") as fh:
        return {row.get("relative_path") or row.get("image"): row for row in csv.DictReader(fh)}


def parse_list(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def is_row_complete(row: Optional[Dict[str, Any]], providers: List[str]) -> bool:
    if not row:
        return False
    for provider in providers:
        if not provider_complete(row, provider):
            return False
    return True


def provider_complete(row: Optional[Dict[str, Any]], provider: str, force_providers: Optional[List[str]] = None) -> bool:
    if provider in (force_providers or []):
        return False
    if not row:
        return False
    status = str(row.get(f"{provider}_status") or "").lower()
    if provider == "gemini" and status and not str(row.get("gemini_model") or "").strip():
        return False
    return bool(status) and status not in {"failed", "failed_quota"}


async def evaluate(args: argparse.Namespace) -> List[Dict[str, Any]]:
    input_dir = Path(args.input_dir)
    if not input_dir.is_absolute():
        input_dir = PROJECT_ROOT / input_dir
    paths = image_paths(input_dir)
    if args.max_samples:
        paths = paths[: args.max_samples]

    providers = [item.strip().lower() for item in args.providers.split(",") if item.strip()]
    force_providers = [item.strip().lower() for item in args.force_providers.split(",") if item.strip()]
    gemini_models = parse_list(args.gemini_models)
    existing = load_existing_rows(args.output_prefix) if args.resume else {}
    rows: List[Dict[str, Any]] = []
    for index, path in enumerate(paths, start=1):
        row_key = str(path.relative_to(PROJECT_ROOT))
        old_row = existing.get(row_key) or existing.get(path.name)
        if args.resume and not force_providers and is_row_complete(old_row, providers):
            print(f"[{index}/{len(paths)}] {path.name} (resume skip)", flush=True)
            rows.append(old_row or {})
            continue
        print(f"[{index}/{len(paths)}] {path.name}", flush=True)
        image_bytes = path.read_bytes()
        row: Dict[str, Any] = dict(old_row or {})
        row.update({
            "image": path.name,
            "relative_path": str(path.relative_to(PROJECT_ROOT)),
        })

        if "local" in providers and not provider_complete(old_row, "local", force_providers):
            try:
                local = run_local_system(image_bytes)
            except Exception as exc:
                local = {"text": "", "confidence": "", "candidates": "", "latency": 0.0, "status": "failed", "error": str(exc)}
            row.update({
                "local_text": local["text"],
                "local_confidence": local["confidence"],
                "local_candidates": local["candidates"],
                "local_latency": round(float(local["latency"]), 4),
                "local_status": local["status"],
                "local_error": local["error"],
            })

        if "system" in providers and not provider_complete(old_row, "system", force_providers):
            system = None
            system_models = parse_list(args.system_gemini_models) or parse_list(args.gemini_models)
            if not system_models:
                system_models = [""]
            errors = []
            for model_offset in range(len(system_models)):
                model = system_models[(index - 1 + model_offset) % len(system_models)]
                try:
                    candidate_system = await run_voting_system(
                        image_bytes,
                        parse_list(args.system_pipelines),
                        args.system_timeout,
                        args.system_verify_web,
                        gemini_model=model,
                    )
                except Exception as exc:
                    candidate_system = {
                        "text": "",
                        "confidence": "",
                        "aggregated_confidence": "",
                        "primary_pipeline": "",
                        "valid_pipelines": "",
                        "num_valid_pipelines": "",
                        "latency": 0.0,
                        "status": "failed",
                        "error": str(exc),
                        "gemini_model": model,
                        "raw": {},
                    }
                if candidate_system["status"] != "failed_quota":
                    system = candidate_system
                    break
                errors.append(candidate_system["error"])
            if system is None:
                system = {
                    "text": "",
                    "confidence": "",
                    "aggregated_confidence": "",
                    "primary_pipeline": "",
                    "valid_pipelines": "",
                    "num_valid_pipelines": "",
                    "latency": 0.0,
                    "status": "failed_quota",
                    "error": " || ".join(errors),
                    "gemini_model": ";".join(system_models),
                    "raw": {},
                }
            row.update({
                "system_text": system["text"],
                "system_confidence": system["confidence"],
                "system_aggregated_confidence": system["aggregated_confidence"],
                "system_primary_pipeline": system["primary_pipeline"],
                "system_valid_pipelines": system["valid_pipelines"],
                "system_num_valid_pipelines": system["num_valid_pipelines"],
                "system_latency": round(float(system["latency"]), 4),
                "system_gemini_model": system.get("gemini_model", ""),
                "system_status": system["status"],
                "system_error": system["error"],
            })
            if system["status"] == "failed_quota":
                rows.append(row)
                write_outputs(rows, args.output_prefix)
                raise RuntimeError(f"System quota/rate limit reached on {path.name}: {system['error']}")

        for provider in providers:
            if provider in {"local", "system"}:
                continue
            if provider_complete(old_row, provider, force_providers):
                continue
            try:
                if provider == "gemini":
                    vision = await run_gemini_with_model_rotation(
                        image_bytes,
                        gemini_models,
                        start_index=index - 1,
                    )
                else:
                    vision = await run_vision_provider(image_bytes, provider)
            except Exception as exc:
                vision = {"text": "", "confidence": "", "candidates": "", "latency": 0.0, "status": "failed", "error": str(exc), "raw": {}}
            row.update({
                f"{provider}_text": vision["text"],
                f"{provider}_confidence": vision["confidence"],
                f"{provider}_candidates": vision["candidates"],
                f"{provider}_latency": round(float(vision["latency"]), 4),
                f"{provider}_model": vision.get("model", ""),
                f"{provider}_status": vision["status"],
                f"{provider}_error": vision["error"],
            })
        rows.append(row)
        write_outputs(rows, args.output_prefix)
        if args.sleep_seconds > 0 and index < len(paths):
            await asyncio.sleep(args.sleep_seconds)
    return rows


def write_outputs(rows: List[Dict[str, Any]], output_prefix: str) -> None:
    csv_path = RESULT_DIR / f"{output_prefix}.csv"
    json_path = RESULT_DIR / f"{output_prefix}.json"
    merged: Dict[str, Dict[str, Any]] = {}
    if csv_path.exists():
        with csv_path.open("r", newline="", encoding="utf-8-sig") as fh:
            for old_row in csv.DictReader(fh):
                key = old_row.get("relative_path") or old_row.get("image")
                if key:
                    merged[key] = old_row
    for row in rows:
        key = row.get("relative_path") or row.get("image")
        if not key:
            continue
        merged[key] = {**merged.get(key, {}), **row}
    rows = list(merged.values())
    fieldnames: List[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with csv_path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="ảnh thực nghiệm")
    parser.add_argument("--providers", default="local,gemini", help="Comma-separated: system,local,gemini,openai")
    parser.add_argument("--gemini-models", default=DEFAULT_GEMINI_MODELS)
    parser.add_argument("--system-pipelines", default="ocr_llm,ocr_search,vision_gemini,ml_match")
    parser.add_argument("--system-gemini-models", default=DEFAULT_GEMINI_MODELS)
    parser.add_argument("--system-timeout", type=int, default=150)
    parser.add_argument("--system-verify-web", action="store_true")
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--output-prefix", default="experiment_images_benchmark")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--force-providers", default="", help="Comma-separated providers to recompute even when resume data exists")
    args = parser.parse_args()
    rows = asyncio.run(evaluate(args))
    write_outputs(rows, args.output_prefix)
    print(f"Wrote {len(rows)} rows to {RESULT_DIR / (args.output_prefix + '.csv')}")


if __name__ == "__main__":
    main()
