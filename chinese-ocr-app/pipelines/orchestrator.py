"""
Pipeline Orchestrator — Điều phối chạy 4 pipeline song song và gọi Voting.

Entry point chính cho hệ thống Multi-Pipeline NCKH.
Nhận ảnh đầu vào → chạy đồng thời 4 pipeline → tổng hợp kết quả.
"""
import asyncio
import time
from typing import Any, Dict, List, Optional

from pipelines.base import PipelineResult, PipelineStatus
from pipelines.pipeline_ocr_llm import PipelineOcrLlm
from pipelines.pipeline_ocr_search import PipelineOcrSearch
from pipelines.pipeline_img_search import PipelineImgSearch
from pipelines.pipeline_ml_match import PipelineMlMatch
from voting.aggregator import aggregate_results
from config import PIPELINE_TIMEOUT


# Khởi tạo 4 pipeline instances
_pipeline_ocr_llm = PipelineOcrLlm()
_pipeline_ocr_search = PipelineOcrSearch()
_pipeline_img_search = PipelineImgSearch()
_pipeline_ml_match = PipelineMlMatch()


async def analyze_image(
    image_bytes: bytes,
    database: Optional[List[Dict[str, Any]]] = None,
    pipelines: Optional[List[str]] = None,
    timeout: Optional[int] = None,
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
    active_pipelines = pipelines or ["ocr_llm", "ocr_search", "img_search", "ml_match"]
    
    # Tạo danh sách task
    tasks = []
    task_names = []
    
    if "ocr_llm" in active_pipelines:
        tasks.append(_run_with_timeout(
            _pipeline_ocr_llm.execute(image_bytes),
            _timeout,
            "ocr_llm",
        ))
        task_names.append("ocr_llm")
    
    if "ocr_search" in active_pipelines:
        tasks.append(_run_with_timeout(
            _pipeline_ocr_search.execute(image_bytes),
            _timeout,
            "ocr_search",
        ))
        task_names.append("ocr_search")
    
    if "img_search" in active_pipelines:
        tasks.append(_run_with_timeout(
            _pipeline_img_search.execute(image_bytes),
            _timeout,
            "img_search",
        ))
        task_names.append("img_search")
    
    if "ml_match" in active_pipelines:
        tasks.append(_run_with_timeout(
            _pipeline_ml_match.execute(image_bytes, database=database or []),
            _timeout,
            "ml_match",
        ))
        task_names.append("ml_match")
    
    if not tasks:
        return {"status": "error", "message": "Không có pipeline nào được chọn"}
    
    # Chạy tất cả pipeline đồng thời
    print(f"\n⚡ Chạy {len(tasks)} pipeline đồng thời: {task_names}")
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Thu thập kết quả
    pipeline_results: List[PipelineResult] = []
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
    final = aggregate_results(pipeline_results)
    
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


async def analyze_quick(
    image_bytes: bytes,
    database: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Phân tích nhanh — chỉ chạy Pipeline 1 (OCR+LLM) + Pipeline 4 (ML).
    Không tìm kiếm Google, nhanh hơn nhiều.
    """
    return await analyze_image(
        image_bytes,
        database=database,
        pipelines=["ocr_llm", "ml_match"],
        timeout=60,
    )


async def analyze_deep(
    image_bytes: bytes,
    database: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Phân tích sâu — chạy tất cả 4 pipeline.
    Chậm hơn nhưng chính xác hơn nhờ cross-reference nhiều nguồn.
    """
    return await analyze_image(
        image_bytes,
        database=database,
        pipelines=["ocr_llm", "ocr_search", "img_search", "ml_match"],
        timeout=120,
    )
