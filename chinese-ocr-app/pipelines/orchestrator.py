"""
Pipeline Orchestrator — Điều phối chạy 4 pipeline song song và gọi Voting.

Entry point chính cho hệ thống Multi-Pipeline NCKH.
Nhận ảnh đầu vào → chạy đồng thời 4 pipeline → tổng hợp kết quả.
"""
import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

from pipelines.base import PipelineResult, PipelineStatus
from pipelines.pipeline_ocr_llm import PipelineOcrLlm
from pipelines.pipeline_ocr_search import PipelineOcrSearch
from pipelines.pipeline_img_search import PipelineImgSearch
from pipelines.pipeline_ml_match import PipelineMlMatch
from pipelines.pipeline_vision_read import PipelineVisionRead
from config import PIPELINE_TIMEOUT


# Khởi tạo 4 pipeline instances
_pipeline_ocr_llm = PipelineOcrLlm()
_pipeline_ocr_search = PipelineOcrSearch()
_pipeline_vision_read = PipelineVisionRead()
_pipeline_img_search = PipelineImgSearch()
_pipeline_ml_match = PipelineMlMatch()


async def analyze_image(
    image_bytes: bytes,
    database: Optional[List[Dict[str, Any]]] = None,
    pipelines: Optional[List[str]] = None,
    timeout: Optional[int] = None,
    verify_with_web: bool = True,
    cancel_event: Optional[asyncio.Event] = None,
) -> Dict[str, Any]:
    """
    Entry point chính — Phân tích ảnh hiệu đề bằng Multi-Pipeline.
    
    Args:
        image_bytes: Ảnh đầu vào dưới dạng bytes
        database: Database hiệu đề (cho Pipeline 4)
        pipelines: Danh sách pipeline cần chạy (None = chạy tất cả)
                   Ví dụ: ["ocr_llm", "ml_match"]
        timeout: Timeout tổng (giây). None = dùng config
        
    Returns:
        Dictionary kết quả tổng hợp từ Voting Logic
    """
    _timeout = timeout or PIPELINE_TIMEOUT
    start = time.time()
    
    print("\n" + "=" * 70)
    print("🚀 MULTI-PIPELINE ANALYSIS — Bắt đầu phân tích")
    print("=" * 70)
    
    # Xác định pipeline nào cần chạy
    active_pipelines = pipelines or ["ocr_llm", "vision_read", "img_search", "ml_match"]
    shared_ocr_text, shared_ocr_candidates = await _run_shared_ocr(image_bytes)
    shared_db_entry, shared_db_match_type = _find_database_entry_for_text(shared_ocr_text, database or [])
    strong_local_match = bool(shared_db_entry and shared_db_match_type == "exact")
    if shared_ocr_text:
        print(f"[Orchestrator] Shared OCR text: {shared_ocr_text}")
    if shared_ocr_candidates:
        print(f"[Orchestrator] Shared OCR candidates: {shared_ocr_candidates[:5]}")
    if shared_db_entry:
        print(
            "[Orchestrator] Shared OCR matched database: "
            f"{shared_db_entry.get('ten_viet', '')} ({shared_db_match_type})"
        )
    
    # Tạo danh sách task
    tasks = []
    task_names = []
    precomputed_results: List[PipelineResult] = []

    if "ocr_llm" in active_pipelines:
        tasks.append(_run_with_timeout(
            _pipeline_ocr_llm.execute(
                image_bytes,
                database=database or [],
                ocr_text=shared_ocr_text,
                ocr_candidates=shared_ocr_candidates,
                allow_db_short_circuit=True,
            ),
            min(_timeout, 60),
            "ocr_llm",
        ))
        task_names.append("ocr_llm")
    
    if "ocr_search" in active_pipelines:
        tasks.append(_run_with_timeout(
            _pipeline_ocr_search.execute(
                image_bytes,
                database=database or [],
                ocr_text=shared_ocr_text,
            ),
            min(_timeout, 75),
            "ocr_search",
        ))
        task_names.append("ocr_search")

    if "vision_read" in active_pipelines:
        tasks.append(_run_with_timeout(
            _pipeline_vision_read.execute(
                image_bytes,
            ),
            min(_timeout, 75),
            "vision_read",
        ))
        task_names.append("vision_read")
    
    if "img_search" in active_pipelines:
        tasks.append(_run_with_timeout(
            _pipeline_img_search.execute(
                image_bytes,
                fallback_ocr_text=shared_ocr_text,
                database=database or [],
            ),
            min(_timeout, 90),
            "img_search",
        ))
        task_names.append("img_search")
    
    if "ml_match" in active_pipelines:
        tasks.append(_run_with_timeout(
            _pipeline_ml_match.execute(
                image_bytes,
                database=database or [],
                ocr_text=shared_ocr_text,
            ),
            min(_timeout, 45),
            "ml_match",
        ))
        task_names.append("ml_match")
    
    if not tasks and not precomputed_results:
        return {"status": "error", "message": "Không có pipeline nào được chọn"}
    
    # Check if client already disconnected before running pipelines
    if cancel_event and cancel_event.is_set():
        print("[Orchestrator] ⛔ Cancelled before pipeline execution")
        return {"status": "cancelled", "message": "Analysis cancelled by user"}

    # Chạy tất cả pipeline đồng thời
    print(f"\n⚡ Chạy {len(tasks)} pipeline đồng thời: {task_names}")
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Check if client disconnected during pipeline execution
    if cancel_event and cancel_event.is_set():
        print("[Orchestrator] ⛔ Cancelled after pipeline execution — skipping voting")
        return {"status": "cancelled", "message": "Analysis cancelled by user"}
    
    # Thu thập kết quả
    pipeline_results: List[PipelineResult] = list(precomputed_results)
    for i, result in enumerate(results):
        if isinstance(result, PipelineResult):
            pipeline_results.append(result)
        elif isinstance(result, Exception):
            print(f"[Orchestrator] ❌ Pipeline '{task_names[i]}' exception: {result}")
            pipeline_results.append(PipelineResult(
                pipeline_name=task_names[i],
                status=PipelineStatus.FAILED,
                error_message=str(result),
            ))
    
    # Voting
    print(f"\n🗳️ Bắt đầu Voting với {len(pipeline_results)} kết quả...")
    # Import locally to avoid circular import
    from voting.aggregator import aggregate_results
    final = aggregate_results(pipeline_results, database=database)

    if verify_with_web:
        from services.evidence_service import (
            apply_evidence_to_final,
            build_evidence_candidates,
            verify_candidates_with_web,
        )

        evidence_candidates = build_evidence_candidates(
            shared_ocr_text,
            shared_ocr_candidates,
            pipeline_results,
            database or [],
        )
        final["evidence_candidates"] = evidence_candidates
        if evidence_candidates:
            print(f"\n[Evidence] Verifying {len(evidence_candidates)} candidates with web sources...")
            evidence_report = await verify_candidates_with_web(
                evidence_candidates,
                search_method="selenium_only",
            )
            final = apply_evidence_to_final(final, evidence_report)
        else:
            final["web_verified"] = False
            final["verification_status"] = "no_candidates"
            final["canh_bao"] = "Không có ứng viên đủ rõ để kiểm chứng bằng web."
    
    elapsed = time.time() - start
    final["total_execution_time"] = round(elapsed, 3)
    
    print(f"\n{'=' * 70}")
    print(f"✅ PHÂN TÍCH HOÀN TẤT — Tổng thời gian: {elapsed:.2f}s")
    print(f"   Kết quả: {final.get('trieu_dai', '?')} / {final.get('nien_hieu', '?')}")
    print(f"   Confidence: {final.get('confidence', 0):.2%}")
    print(f"{'=' * 70}\n")
    
    return final


async def _run_with_timeout(
    coro,
    timeout: int,
    pipeline_name: str,
) -> PipelineResult:
    """Chạy pipeline với timeout."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        print(f"[Orchestrator] ⏱️ Pipeline '{pipeline_name}' timeout sau {timeout}s")
        return PipelineResult(
            pipeline_name=pipeline_name,
            status=PipelineStatus.TIMEOUT,
            error_message=f"Timeout sau {timeout}s",
        )


async def _run_shared_ocr(image_bytes: bytes) -> Tuple[str, List[str]]:
    """Run OCR once so all branches use the same text evidence."""
    def _ocr_sync():
        try:
            from ocr_engine import read_chinese_mark
            result = read_chinese_mark(image_bytes, deep_mode=True)
            if result.get("error"):
                print(f"[Orchestrator/OCR] {result.get('error')}")
                return "", []
            return result.get("text", "") or "", result.get("candidates", []) or []
        except Exception as exc:
            print(f"[Orchestrator/OCR] Error: {exc}")
            return "", []

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _ocr_sync)


def _find_database_entry_for_text(
    ocr_text: str,
    database: List[Dict[str, Any]],
) -> Tuple[Optional[Dict[str, Any]], str]:
    """Fast local lookup used to decide whether expensive web/image search is needed."""
    query = _normalize_cjk(ocr_text)
    if not query or not database:
        return None, "none"

    generic_partials = {"年製", "年制", "年造", "大清", "大明", "大南"}
    partial_matches = []

    for entry in database:
        for target in _entry_targets(entry):
            target_norm = _normalize_cjk(target)
            if target_norm == query:
                return entry, "exact"

        if len(query) >= 4 and query not in generic_partials:
            for target in _entry_targets(entry):
                target_norm = _normalize_cjk(target)
                if target_norm and query in target_norm:
                    score = len(query) / max(len(target_norm), 1)
                    partial_matches.append((score, entry))

    if partial_matches:
        partial_matches.sort(key=lambda x: x[0], reverse=True)
        return partial_matches[0][1], "partial"
    return None, "none"


def _entry_targets(entry: Dict[str, Any]) -> List[str]:
    fields = [
        entry.get("chu_han", ""),
        entry.get("chu_han_4", ""),
        entry.get("chu_han_6", ""),
    ]
    fields.extend([bt for bt in (entry.get("bien_the") or []) if bt])
    return [field for field in fields if field]


def _normalize_cjk(value: str) -> str:
    normalized = "".join(ch for ch in (value or "") if "\u4e00" <= ch <= "\u9fff")
    return normalized.translate(str.maketrans({
        "绪": "緒",
        "统": "統",
        "历": "曆",
        "万": "萬",
        "制": "製",
        "内": "內",
    }))


async def analyze_quick(
    image_bytes: bytes,
    database: Optional[List[Dict[str, Any]]] = None,
    cancel_event: Optional[asyncio.Event] = None,
) -> Dict[str, Any]:
    """
    Phân tích nhanh — chỉ chạy Pipeline 1 (OCR+LLM) + Pipeline 4 (ML).
    Không tìm kiếm Google, nhanh hơn nhiều.
    """
    return await analyze_image(
        image_bytes,
        database=database,
        pipelines=["ocr_llm", "vision_read", "ml_match"],
        timeout=60,
        cancel_event=cancel_event,
    )


async def analyze_deep(
    image_bytes: bytes,
    database: Optional[List[Dict[str, Any]]] = None,
    cancel_event: Optional[asyncio.Event] = None,
) -> Dict[str, Any]:
    """
    Phân tích sâu — chạy tất cả 4 pipeline.
    Chậm hơn nhưng chính xác hơn nhờ cross-reference nhiều nguồn.
    """
    return await analyze_image(
        image_bytes,
        database=database,
        pipelines=["ocr_llm", "vision_read", "img_search", "ml_match"],
        timeout=120,
        cancel_event=cancel_event,
    )
