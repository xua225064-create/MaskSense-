import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = ROOT / "experiments" / "results"
CSV_PATH = RESULT_DIR / "reference_set_evaluation.csv"
OUT_JSON = RESULT_DIR / "paper_benchmark_metrics.json"
OUT_MD = RESULT_DIR / "paper_benchmark_report.md"

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


def edit_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            cur.append(min(
                prev[j] + 1,
                cur[j - 1] + 1,
                prev[j - 1] + (0 if ca == cb else 1),
            ))
        prev = cur
    return prev[-1]


def char_accuracy(rows, pred_key):
    total_chars = 0
    correct_chars = 0
    for row in rows:
        label = norm_cjk(row["label"])
        pred = norm_cjk(row[pred_key])
        total_chars += len(label)
        correct_chars += max(0, len(label) - edit_distance(label, pred))
    return correct_chars / total_chars if total_chars else 0.0


def exact_accuracy(rows, pred_key):
    return sum(norm_cjk(r[pred_key]) == norm_cjk(r["label"]) for r in rows) / len(rows) if rows else 0.0


def bool_accuracy(rows, key):
    return sum(str(r[key]).lower() == "true" for r in rows) / len(rows) if rows else 0.0


def latency_stats(rows, key):
    values = sorted(float(r[key]) for r in rows)
    if not values:
        return {"avg": 0.0, "median": 0.0, "p95": 0.0, "min": 0.0, "max": 0.0}
    p95_index = min(len(values) - 1, int(round(0.95 * (len(values) - 1))))
    return {
        "avg": sum(values) / len(values),
        "median": values[len(values) // 2],
        "p95": values[p95_index],
        "min": values[0],
        "max": values[-1],
    }


def macro_f1_exact(rows, pred_key):
    labels = sorted({norm_cjk(r["label"]) for r in rows} | {norm_cjk(r[pred_key]) for r in rows if norm_cjk(r[pred_key])})
    f1s = []
    for label in labels:
        tp = sum(norm_cjk(r["label"]) == label and norm_cjk(r[pred_key]) == label for r in rows)
        fp = sum(norm_cjk(r["label"]) != label and norm_cjk(r[pred_key]) == label for r in rows)
        fn = sum(norm_cjk(r["label"]) == label and norm_cjk(r[pred_key]) != label for r in rows)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        f1s.append(f1)
    return sum(f1s) / len(f1s) if f1s else 0.0


def confusion_rows(rows, pred_key):
    counts = Counter((norm_cjk(r["label"]), norm_cjk(r[pred_key])) for r in rows if norm_cjk(r["label"]) != norm_cjk(r[pred_key]))
    return [
        {"ground_truth": label, "prediction": pred or "(empty)", "count": count}
        for (label, pred), count in counts.most_common()
    ]


def family(label: str) -> str:
    text = norm_cjk(label)
    if text.startswith("大明") or text in {"永樂年製", "康熙年製", "乾隆年製"}:
        return "Chinese imperial marks"
    if text.startswith("大清"):
        return "Chinese imperial marks"
    if text.startswith("內府") or text in {"明命年製", "慶春侍左"}:
        return "Vietnamese court marks"
    return "Auspicious / studio marks"


def family_accuracy(rows, pred_key):
    grouped = defaultdict(list)
    for row in rows:
        grouped[family(row["label"])].append(row)
    return {
        name: {
            "n": len(items),
            "relaxed_accuracy": bool_accuracy(items, "combined_ok" if pred_key == "combined_pred" else "module_b_ok"),
            "strict_exact_accuracy": exact_accuracy(items, pred_key),
        }
        for name, items in sorted(grouped.items())
    }


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    metrics = {
        "dataset": {
            "name": "reference_library_available_data",
            "n_images": len(rows),
            "scope": "Labeled reference images available in the repository; not an external public benchmark.",
        },
        "ocr_only": {
            "relaxed_mark_accuracy": bool_accuracy(rows, "module_b_ok"),
            "candidate_recall": bool_accuracy(rows, "module_b_candidate_ok"),
            "strict_exact_mark_accuracy": exact_accuracy(rows, "module_b_pred"),
            "character_accuracy": char_accuracy(rows, "module_b_pred"),
            "latency_seconds": latency_stats(rows, "module_b_latency"),
        },
        "ocr_plus_database_fuzzy": {
            "relaxed_mark_accuracy": bool_accuracy(rows, "module_c_ok"),
            "strict_exact_mark_accuracy": exact_accuracy(rows, "module_c_pred"),
            "character_accuracy": char_accuracy(rows, "module_c_pred"),
            "macro_f1_strict_exact": macro_f1_exact(rows, "module_c_pred"),
            "latency_seconds": latency_stats(rows, "module_c_latency"),
        },
        "combined_offline_core": {
            "relaxed_mark_accuracy": bool_accuracy(rows, "combined_ok"),
            "strict_exact_mark_accuracy": exact_accuracy(rows, "combined_pred"),
            "character_accuracy": char_accuracy(rows, "combined_pred"),
            "macro_f1_strict_exact": macro_f1_exact(rows, "combined_pred"),
            "latency_seconds": latency_stats(rows, "combined_latency"),
            "family_breakdown": family_accuracy(rows, "combined_pred"),
        },
        "orb_leave_one_out": {
            "relaxed_mark_accuracy": bool_accuracy(rows, "module_a_ok"),
            "strict_exact_mark_accuracy": exact_accuracy(rows, "module_a_pred"),
            "latency_seconds": latency_stats(rows, "module_a_latency"),
        },
        "confusion_matrix_strict_exact": confusion_rows(rows, "combined_pred"),
        "failed_cases_relaxed": [
            {
                "image": row["image"],
                "ground_truth": norm_cjk(row["label"]),
                "ocr_prediction": norm_cjk(row["module_b_pred"]) or "(empty)",
                "final_prediction": norm_cjk(row["combined_pred"]) or "(empty)",
                "detail": row["module_c_detail"],
            }
            for row in rows
            if str(row["combined_ok"]).lower() != "true"
        ],
    }
    OUT_JSON.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    def pct(value):
        return f"{value * 100:.2f}%"

    md = [
        "# MarkSense Benchmark Report",
        "",
        "## Dataset",
        f"- Dataset: `{metrics['dataset']['name']}`",
        f"- Images: **{len(rows)}** labeled ceramic-mark images",
        "- Scope note: this is a functional benchmark on the labeled images currently available in the repository, not an independent public benchmark.",
        "",
        "## Main Results",
        "| Method | Relaxed Mark Accuracy | Strict Exact Mark Accuracy | Character Accuracy | Macro-F1 (strict) | Avg Latency | P95 Latency |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| OCR only | {pct(metrics['ocr_only']['relaxed_mark_accuracy'])} | {pct(metrics['ocr_only']['strict_exact_mark_accuracy'])} | {pct(metrics['ocr_only']['character_accuracy'])} | - | {metrics['ocr_only']['latency_seconds']['avg']:.2f}s | {metrics['ocr_only']['latency_seconds']['p95']:.2f}s |",
        f"| OCR candidate recall | {pct(metrics['ocr_only']['candidate_recall'])} | - | - | - | - | - |",
        f"| OCR + database fuzzy | {pct(metrics['ocr_plus_database_fuzzy']['relaxed_mark_accuracy'])} | {pct(metrics['ocr_plus_database_fuzzy']['strict_exact_mark_accuracy'])} | {pct(metrics['ocr_plus_database_fuzzy']['character_accuracy'])} | {pct(metrics['ocr_plus_database_fuzzy']['macro_f1_strict_exact'])} | {metrics['ocr_plus_database_fuzzy']['latency_seconds']['avg']:.3f}s | {metrics['ocr_plus_database_fuzzy']['latency_seconds']['p95']:.3f}s |",
        f"| Combined offline core | {pct(metrics['combined_offline_core']['relaxed_mark_accuracy'])} | {pct(metrics['combined_offline_core']['strict_exact_mark_accuracy'])} | {pct(metrics['combined_offline_core']['character_accuracy'])} | {pct(metrics['combined_offline_core']['macro_f1_strict_exact'])} | {metrics['combined_offline_core']['latency_seconds']['avg']:.2f}s | {metrics['combined_offline_core']['latency_seconds']['p95']:.2f}s |",
        f"| ORB leave-one-out | {pct(metrics['orb_leave_one_out']['relaxed_mark_accuracy'])} | {pct(metrics['orb_leave_one_out']['strict_exact_mark_accuracy'])} | - | - | {metrics['orb_leave_one_out']['latency_seconds']['avg']:.3f}s | {metrics['orb_leave_one_out']['latency_seconds']['p95']:.3f}s |",
        "",
        "## Family Breakdown",
        "| Group | N | Relaxed Accuracy | Strict Exact Accuracy |",
        "|---|---:|---:|---:|",
    ]
    for name, item in metrics["combined_offline_core"]["family_breakdown"].items():
        md.append(f"| {name} | {item['n']} | {pct(item['relaxed_accuracy'])} | {pct(item['strict_exact_accuracy'])} |")
    md.extend([
        "",
        "## Failed Cases Under Relaxed Matching",
    ])
    if metrics["failed_cases_relaxed"]:
        md.append("| Image | Ground Truth | OCR Prediction | Final Prediction | Detail |")
        md.append("|---|---|---|---|---|")
        for item in metrics["failed_cases_relaxed"]:
            md.append(f"| {item['image']} | {item['ground_truth']} | {item['ocr_prediction']} | {item['final_prediction']} | {item['detail']} |")
    else:
        md.append("- None.")
    md.extend([
        "",
        "## Notes For Paper Writing",
        "- Use `Relaxed Mark Accuracy` to describe operational correctness under the current matching policy, where accepted variants or shortened marks can be counted as correct.",
        "- Use `Strict Exact Mark Accuracy` when the predicted inscription must exactly match the full ground-truth inscription.",
        "- The current dataset is small. For a publishable benchmark, extend it to at least 100 images with balanced countries/periods and image conditions.",
    ])
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(f"\nWrote:\n- {OUT_JSON}\n- {OUT_MD}")


if __name__ == "__main__":
    main()
