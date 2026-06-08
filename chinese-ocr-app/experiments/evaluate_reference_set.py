import csv
import argparse
import contextlib
import io
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ocr_engine  # noqa: E402
from ocr_engine import read_chinese_mark  # noqa: E402
from main import _find_match, find_best_matches, REIGN_DATABASE  # noqa: E402


REFERENCE_DIR = ROOT / "data" / "reference_library"
RESULT_DIR = ROOT / "experiments" / "results"
RESULT_DIR.mkdir(parents=True, exist_ok=True)

TRANS = str.maketrans({
    "绪": "緒",
    "统": "統",
    "历": "曆",
    "万": "萬",
    "制": "製",
    "内": "內",
})


def norm_cjk(value: str) -> str:
    return "".join(ch for ch in (value or "") if "\u4e00" <= ch <= "\u9fff").translate(TRANS)


def label_targets(meta: Dict[str, Any]) -> List[str]:
    values = [
        meta.get("chu_han", ""),
        meta.get("chu_han_4", ""),
        meta.get("chu_han_6", ""),
    ]
    values.extend(meta.get("bien_the") or [])
    targets: List[str] = []
    for value in values:
        clean = norm_cjk(str(value or ""))
        if clean and clean not in targets:
            targets.append(clean)
    return targets


def is_correct(predicted: str, targets: List[str]) -> bool:
    clean = norm_cjk(predicted)
    if not clean:
        return False
    return any(clean == target or clean in target or target in clean for target in targets)


def load_labeled_images() -> List[Dict[str, Any]]:
    suffix_to_json: Dict[str, Path] = {}
    for json_path in REFERENCE_DIR.glob("*.json"):
        suffix_to_json[json_path.stem.split("_")[-1]] = json_path

    samples: List[Dict[str, Any]] = []
    for image_path in sorted(list(REFERENCE_DIR.glob("*.jpg")) + list(REFERENCE_DIR.glob("*.png"))):
        json_path = image_path.with_suffix(".json")
        if not json_path.exists():
            json_path = suffix_to_json.get(image_path.stem.split("_")[-1], json_path)
        if not json_path.exists():
            continue
        meta = json.loads(json_path.read_text(encoding="utf-8"))
        targets = label_targets(meta)
        if not targets:
            continue
        samples.append({
            "image_path": image_path,
            "json_path": json_path,
            "meta": meta,
            "targets": targets,
            "label": targets[0],
        })
    return samples


def extract_orb(image_bytes: bytes):
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return None
    h, w = img.shape[:2]
    if h >= 80 and w >= 80:
        ratio = 0.62
        y1 = int((1.0 - ratio) * 0.5 * h)
        y2 = int((1.0 + ratio) * 0.5 * h)
        x1 = int((1.0 - ratio) * 0.5 * w)
        x2 = int((1.0 + ratio) * 0.5 * w)
        roi = img[y1:y2, x1:x2]
        if roi.size:
            img = roi
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    gray = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(gray)
    orb = cv2.ORB_create(nfeatures=2000)
    _, descriptors = orb.detectAndCompute(gray, None)
    return descriptors


def build_orb_index(samples: List[Dict[str, Any]]) -> None:
    for sample in samples:
        sample["image_bytes"] = sample["image_path"].read_bytes()
        sample["orb_descriptors"] = extract_orb(sample["image_bytes"])


def module_a_orb_loo(sample: Dict[str, Any], samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    start = time.time()
    query_desc = sample.get("orb_descriptors")
    if query_desc is None:
        return {"pred": "", "ok": False, "latency": time.time() - start, "detail": "no_query_desc"}

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    best_count = 0
    second_count = 0
    best_sample: Optional[Dict[str, Any]] = None
    for other in samples:
        if other["image_path"] == sample["image_path"]:
            continue
        ref_desc = other.get("orb_descriptors")
        if ref_desc is None:
            continue
        try:
            matches = sorted(bf.match(query_desc, ref_desc), key=lambda x: x.distance)
            count = len([m for m in matches if m.distance < 55])
        except Exception:
            continue
        if count > best_count:
            second_count = best_count
            best_count = count
            best_sample = other
        elif count > second_count:
            second_count = count

    pred = ""
    accepted = False
    if best_sample and best_count >= 18:
        gap = best_count - second_count
        ratio = best_count / max(second_count, 1)
        accepted = not (second_count >= 18 and (gap < 30 or ratio < 1.25))
        if accepted:
            pred = best_sample["label"]
    return {
        "pred": pred,
        "ok": is_correct(pred, sample["targets"]),
        "latency": time.time() - start,
        "detail": f"best={best_count};second={second_count};accepted={accepted}",
    }


def module_b_ocr(sample: Dict[str, Any], deep_mode: bool = False, quiet: bool = True) -> Dict[str, Any]:
    start = time.time()
    if quiet:
        with contextlib.redirect_stdout(io.StringIO()):
            result = read_chinese_mark(sample["image_bytes"], deep_mode=deep_mode)
    else:
        result = read_chinese_mark(sample["image_bytes"], deep_mode=deep_mode)
    pred = result.get("text", "") or ""
    candidates = result.get("candidates", []) or []
    return {
        "pred": pred,
        "ok": is_correct(pred, sample["targets"]),
        "candidate_ok": any(is_correct(c, sample["targets"]) for c in candidates),
        "latency": time.time() - start,
        "detail": ";".join(candidates[:5]),
    }


def module_c_fuzzy(ocr_pred: str, ocr_candidates: str, sample: Dict[str, Any]) -> Dict[str, Any]:
    start = time.time()
    texts = [ocr_pred] + [x for x in (ocr_candidates or "").split(";") if x]
    pred = ""
    detail = ""
    for text in texts:
        match, match_type = _find_match(text, REIGN_DATABASE)
        if not match:
            top = find_best_matches(text, REIGN_DATABASE, top_n=1)
            if top:
                match = top[0]
                match_type = "top1"
        if match:
            pred = match.get("chu_han", "") or match.get("chu_han_4", "")
            detail = f"{match_type}:{text}"
            break
    return {
        "pred": pred,
        "ok": is_correct(pred, sample["targets"]),
        "latency": time.time() - start,
        "detail": detail,
    }


def combined_offline(a: Dict[str, Any], c: Dict[str, Any], sample: Dict[str, Any]) -> Dict[str, Any]:
    start = time.time()
    if a.get("pred"):
        pred = a["pred"]
        source = "orb"
    else:
        pred = c.get("pred", "")
        source = "ocr_fuzzy"
    return {
        "pred": pred,
        "ok": is_correct(pred, sample["targets"]),
        "latency": time.time() - start,
        "detail": source,
    }


def summarize(rows: List[Dict[str, Any]], key: str) -> Dict[str, Any]:
    n = len(rows)
    ok = sum(1 for row in rows if row[f"{key}_ok"])
    latencies = [float(row[f"{key}_latency"]) for row in rows]
    return {
        "n": n,
        "correct": ok,
        "accuracy": ok / n if n else 0.0,
        "avg_latency": sum(latencies) / n if n else 0.0,
    }


def write_outputs(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    csv_path = RESULT_DIR / "reference_set_evaluation.csv"
    json_path = RESULT_DIR / "reference_set_summary.json"
    if rows:
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    summary = {
        "dataset": {
            "name": "reference_library_available_data",
            "images": len(rows),
            "note": (
                "Functional/reference-set experiment on labeled images available in the repository. "
                "Module A uses leave-one-out ORB matching; this is not an independent external benchmark."
            ),
        },
        "module_a_orb_leave_one_out": summarize(rows, "module_a"),
        "module_b_multi_variant_ocr": summarize(rows, "module_b"),
        "module_b_candidate_recall": {
            "n": len(rows),
            "correct": sum(1 for row in rows if row["module_b_candidate_ok"]),
            "accuracy": sum(1 for row in rows if row["module_b_candidate_ok"]) / len(rows) if rows else 0.0,
        },
        "module_c_ocr_plus_database_fuzzy": summarize(rows, "module_c"),
        "combined_offline_core": summarize(rows, "combined"),
        "outputs": {
            "csv": str(csv_path),
            "json": str(json_path),
        },
    }
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-variants", type=int, default=8)
    parser.add_argument("--deep-extra", type=int, default=0)
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--verbose-ocr", action="store_true")
    args = parser.parse_args()

    ocr_engine.MAX_VARIANTS_PER_REQUEST = args.max_variants
    ocr_engine.DEEP_EXTRA_VARIANTS = args.deep_extra

    samples = load_labeled_images()
    if args.max_samples:
        samples = samples[: args.max_samples]
    build_orb_index(samples)
    rows: List[Dict[str, Any]] = []

    for idx, sample in enumerate(samples, start=1):
        print(f"[{idx}/{len(samples)}] {sample['image_path'].name} label={sample['label']}", flush=True)
        a = module_a_orb_loo(sample, samples)
        b = module_b_ocr(sample, deep_mode=False, quiet=not args.verbose_ocr)
        c = module_c_fuzzy(b["pred"], b["detail"], sample)
        final = combined_offline(a, c, sample)
        rows.append({
            "image": sample["image_path"].name,
            "label": sample["label"],
            "module_a_pred": norm_cjk(a["pred"]),
            "module_a_ok": a["ok"],
            "module_a_latency": round(a["latency"], 4),
            "module_a_detail": a["detail"],
            "module_b_pred": norm_cjk(b["pred"]),
            "module_b_ok": b["ok"],
            "module_b_candidate_ok": b["candidate_ok"],
            "module_b_latency": round(b["latency"], 4),
            "module_b_detail": b["detail"],
            "module_c_pred": norm_cjk(c["pred"]),
            "module_c_ok": c["ok"],
            "module_c_latency": round(c["latency"], 4),
            "module_c_detail": c["detail"],
            "combined_pred": norm_cjk(final["pred"]),
            "combined_ok": final["ok"],
            "combined_latency": round(final["latency"] + a["latency"] + b["latency"] + c["latency"], 4),
            "combined_detail": final["detail"],
        })
        write_outputs(rows)

    summary = write_outputs(rows)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
