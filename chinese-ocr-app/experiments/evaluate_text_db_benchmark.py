import csv
import json
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import REIGN_DATABASE, _find_match, find_best_matches  # noqa: E402


RESULT_DIR = ROOT / "experiments" / "results"
RESULT_DIR.mkdir(parents=True, exist_ok=True)
CSV_PATH = RESULT_DIR / "text_db_benchmark.csv"
JSON_PATH = RESULT_DIR / "text_db_benchmark_summary.json"
MD_PATH = RESULT_DIR / "text_db_benchmark_report.md"

TRANS = str.maketrans({
    "绪": "緒",
    "统": "統",
    "历": "曆",
    "万": "萬",
    "制": "製",
    "内": "內",
})

CONFUSION_PAIRS = {
    "製": "制",
    "制": "製",
    "萬": "万",
    "曆": "歴",
    "歷": "曆",
    "緒": "绪",
    "統": "统",
    "內": "内",
    "侍": "待",
    "右": "石",
    "左": "杜",
    "康": "庚",
    "熙": "照",
    "雍": "雄",
    "正": "王",
    "乾": "輪",
    "隆": "蓬",
    "道": "遺",
    "光": "先",
    "同": "司",
    "治": "冶",
    "成": "咸",
    "化": "花",
    "弘": "弓",
    "靖": "青",
    "宣": "宜",
    "德": "徳",
}

UNKNOWN_FAKE_MARKS = [
    "青雲龍瑞年製",
    "玄德寶光年造",
    "天華永安年製",
    "瑞雲堂藏",
    "明月清風製",
    "玉海長春",
    "東山雅製",
    "龍泉新造",
    "雲水珍玩",
    "景和太平年製",
    "永福長樂年造",
    "春山秋月",
    "寶光堂製",
    "清雅閣造",
    "萬瑞堂藏",
    "德壽永昌",
    "天寶新製",
    "華春年造",
    "瑞德堂印",
    "玉堂清玩",
]


def norm_cjk(value: str) -> str:
    return "".join(ch for ch in (value or "") if "\u4e00" <= ch <= "\u9fff").translate(TRANS)


def record_label(row: Dict[str, Any]) -> str:
    for key in ("chu_han", "chu_han_6", "chu_han_4"):
        value = norm_cjk(str(row.get(key) or ""))
        if value:
            return value
    return ""


def variants_for(row: Dict[str, Any]) -> List[Tuple[str, str]]:
    label = record_label(row)
    short = norm_cjk(str(row.get("chu_han_4") or ""))
    variants: List[Tuple[str, str]] = []
    if label:
        variants.append(("exact_full", label))
    if short and short != label:
        variants.append(("short_mark", short))
    if label.startswith(("大清", "大明", "大南")) and len(label) > 4:
        variants.append(("missing_dynasty_prefix", label[2:]))
    if len(label) >= 4:
        variants.append(("drop_last_char", label[:-1]))
        variants.append(("drop_first_char", label[1:]))
    replaced = list(label)
    for idx, char in enumerate(replaced):
        if char in CONFUSION_PAIRS:
            replaced[idx] = CONFUSION_PAIRS[char]
            noisy = "".join(replaced)
            if noisy != label:
                variants.append(("single_confusion", noisy))
            break
    if len(label) >= 6:
        swapped = list(label)
        swapped[0], swapped[1] = swapped[1], swapped[0]
        variants.append(("wrong_order_pair", "".join(swapped)))
    unique = []
    seen = set()
    for kind, text in variants:
        text = norm_cjk(text)
        if text and text not in seen:
            unique.append((kind, text))
            seen.add(text)
    return unique


def is_expected_match(pred: Dict[str, Any], row: Dict[str, Any]) -> bool:
    if not pred:
        return False
    expected = {record_label(row)}
    for key in ("chu_han_4", "chu_han_6"):
        value = norm_cjk(str(row.get(key) or ""))
        if value:
            expected.add(value)
    for value in row.get("bien_the") or []:
        clean = norm_cjk(str(value or ""))
        if clean:
            expected.add(clean)
    pred_values = {
        norm_cjk(str(pred.get("chu_han") or "")),
        norm_cjk(str(pred.get("chu_han_4") or "")),
        norm_cjk(str(pred.get("chu_han_6") or "")),
    }
    pred_values = {value for value in pred_values if value}
    return bool(expected & pred_values)


def group_for(row: Dict[str, Any]) -> str:
    text = " ".join(str(row.get(k) or "") for k in ("trieu_dai", "hieu_de_en", "ten_viet", "hien_thi_chinh")).lower()
    chu = record_label(row)
    if any(token in text for token in ("nhật", "japan", "satsuma", "arita", "imari", "dai nippon")):
        return "Japan"
    if any(token in text for token in ("korea", "korean", "goryeo", "joseon", "hàn")):
        return "Korea"
    if any(token in text for token in ("việt", "vietnam", "nguyễn", "lê", "trịnh")) or chu.startswith(("大南", "內府")):
        return "Vietnam"
    if any(token in text for token in ("qing", "ming", "china", "trung")) or chu.startswith(("大清", "大明")):
        return "China"
    return "Other"


def run_known_cases() -> List[Dict[str, Any]]:
    rows = []
    for row in REIGN_DATABASE:
        label = record_label(row)
        if not label:
            continue
        for variant_type, query in variants_for(row):
            start = time.perf_counter()
            match, match_type = _find_match(query, REIGN_DATABASE)
            if not match:
                top = find_best_matches(query, REIGN_DATABASE, top_n=3)
                match = top[0] if top else None
                match_type = "top1_fuzzy" if match else "none"
            else:
                top = find_best_matches(query, REIGN_DATABASE, top_n=3)
            latency = time.perf_counter() - start
            top3_ok = any(is_expected_match(item, row) for item in (top or []))
            rows.append({
                "case_type": "known",
                "group": group_for(row),
                "variant_type": variant_type,
                "query": query,
                "ground_truth": label,
                "prediction": record_label(match or {}),
                "match_type": match_type,
                "top1_ok": is_expected_match(match, row),
                "top3_ok": top3_ok or is_expected_match(match, row),
                "latency": round(latency, 6),
            })
    return rows


def run_unknown_cases(repeats: int = 5) -> List[Dict[str, Any]]:
    rows = []
    fake_pool = []
    for _ in range(repeats):
        fake_pool.extend(UNKNOWN_FAKE_MARKS)
    random.seed(42)
    random.shuffle(fake_pool)
    for query in fake_pool:
        start = time.perf_counter()
        match, match_type = _find_match(query, REIGN_DATABASE)
        if not match:
            top = find_best_matches(query, REIGN_DATABASE, top_n=3)
            match = top[0] if top else None
            match_type = "top1_fuzzy" if match else "none"
        latency = time.perf_counter() - start
        rows.append({
            "case_type": "unknown",
            "group": "Unknown",
            "variant_type": "fake_no_db",
            "query": query,
            "ground_truth": "(unknown)",
            "prediction": record_label(match or {}),
            "match_type": match_type,
            "top1_ok": False,
            "top3_ok": False,
            "false_positive": bool(match),
            "latency": round(latency, 6),
        })
    return rows


def summarize(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    known = [row for row in rows if row["case_type"] == "known"]
    unknown = [row for row in rows if row["case_type"] == "unknown"]

    def pct(num, den):
        return num / den if den else 0.0

    by_variant = {}
    for variant in sorted({row["variant_type"] for row in known}):
        items = [row for row in known if row["variant_type"] == variant]
        by_variant[variant] = {
            "n": len(items),
            "top1_accuracy": pct(sum(bool(row["top1_ok"]) for row in items), len(items)),
            "top3_accuracy": pct(sum(bool(row["top3_ok"]) for row in items), len(items)),
        }

    by_group = {}
    for group in sorted({row["group"] for row in known}):
        items = [row for row in known if row["group"] == group]
        by_group[group] = {
            "n": len(items),
            "top1_accuracy": pct(sum(bool(row["top1_ok"]) for row in items), len(items)),
            "top3_accuracy": pct(sum(bool(row["top3_ok"]) for row in items), len(items)),
        }

    latencies = sorted(float(row["latency"]) for row in rows)
    p95 = latencies[int(round(0.95 * (len(latencies) - 1)))] if latencies else 0.0
    confusion = Counter(
        (row["ground_truth"], row["prediction"] or "(empty)")
        for row in known
        if not row["top1_ok"]
    )
    return {
        "dataset": {
            "database_records": len(REIGN_DATABASE),
            "known_cases": len(known),
            "unknown_fake_cases": len(unknown),
            "note": "Text-only database retrieval benchmark. This evaluates mark normalization/fuzzy matching, not image OCR or Vision AI.",
        },
        "known_retrieval": {
            "top1_accuracy": pct(sum(bool(row["top1_ok"]) for row in known), len(known)),
            "top3_accuracy": pct(sum(bool(row["top3_ok"]) for row in known), len(known)),
        },
        "unknown_rejection": {
            "false_positive_rate": pct(sum(bool(row.get("false_positive")) for row in unknown), len(unknown)),
            "rejection_rate": pct(sum(not bool(row.get("false_positive")) for row in unknown), len(unknown)),
        },
        "latency_seconds": {
            "avg": sum(latencies) / len(latencies) if latencies else 0.0,
            "p95": p95,
            "max": max(latencies) if latencies else 0.0,
        },
        "by_variant": by_variant,
        "by_group": by_group,
        "top_confusions": [
            {"ground_truth": truth, "prediction": pred, "count": count}
            for (truth, pred), count in confusion.most_common(20)
        ],
    }


def write_report(summary: Dict[str, Any]) -> None:
    def fmt(value):
        return f"{value * 100:.2f}%"

    lines = [
        "# Text-Only Database Retrieval Benchmark",
        "",
        "This benchmark uses the mark database as ground truth and generates OCR-like text variants. It measures database matching and noise tolerance, not visual recognition.",
        "",
        "## Overall",
        f"- Database records: **{summary['dataset']['database_records']}**",
        f"- Known synthetic text cases: **{summary['dataset']['known_cases']}**",
        f"- Unknown/fake text cases: **{summary['dataset']['unknown_fake_cases']}**",
        f"- Top-1 retrieval accuracy: **{fmt(summary['known_retrieval']['top1_accuracy'])}**",
        f"- Top-3 retrieval accuracy: **{fmt(summary['known_retrieval']['top3_accuracy'])}**",
        f"- Unknown false-positive rate: **{fmt(summary['unknown_rejection']['false_positive_rate'])}**",
        f"- Avg latency: **{summary['latency_seconds']['avg']:.6f}s**",
        f"- P95 latency: **{summary['latency_seconds']['p95']:.6f}s**",
        "",
        "## Accuracy By Variant",
        "| Variant | N | Top-1 | Top-3 |",
        "|---|---:|---:|---:|",
    ]
    for variant, item in summary["by_variant"].items():
        lines.append(f"| {variant} | {item['n']} | {fmt(item['top1_accuracy'])} | {fmt(item['top3_accuracy'])} |")
    lines.extend([
        "",
        "## Accuracy By Region/Group",
        "| Group | N | Top-1 | Top-3 |",
        "|---|---:|---:|---:|",
    ])
    for group, item in summary["by_group"].items():
        lines.append(f"| {group} | {item['n']} | {fmt(item['top1_accuracy'])} | {fmt(item['top3_accuracy'])} |")
    lines.extend([
        "",
        "## Main Confusions",
        "| Ground Truth | Prediction | Count |",
        "|---|---|---:|",
    ])
    for item in summary["top_confusions"]:
        lines.append(f"| {item['ground_truth']} | {item['prediction']} | {item['count']} |")
    MD_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    rows = run_known_cases() + run_unknown_cases(repeats=5)
    with CSV_PATH.open("w", newline="", encoding="utf-8-sig") as f:
        fieldnames = []
        for row in rows:
            for key in row.keys():
                if key not in fieldnames:
                    fieldnames.append(key)
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    summary = summarize(rows)
    JSON_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nWrote:\n- {CSV_PATH}\n- {JSON_PATH}\n- {MD_PATH}")


if __name__ == "__main__":
    main()
