"""
Voting Aggregator — Tổng hợp kết quả từ 4 pipeline thành kết quả cuối cùng.

Sử dụng weighted voting:
- Mỗi pipeline có trọng số (weight) riêng
- Kết quả cuối = pipeline có tổng điểm (confidence × weight) cao nhất
- Thông tin bổ sung được cross-reference từ các pipeline khác
"""
from typing import Any, Dict, List, Optional
from pipelines.base import PipelineResult, PipelineStatus
from config import PIPELINE_WEIGHTS, MIN_PIPELINE_RESPONSES


def aggregate_results(results: List[PipelineResult]) -> Dict[str, Any]:
    """
    Tổng hợp kết quả từ tất cả pipeline.
    
    Logic:
    1. Lọc bỏ pipeline failed/skipped
    2. Tính weighted score cho mỗi kết quả
    3. Voting theo triều đại (majority wins)
    4. Chọn thông tin chi tiết từ pipeline có confidence cao nhất
    5. Bổ sung thông tin từ pipeline khác (cross-reference)
    
    Args:
        results: Danh sách PipelineResult từ các pipeline
        
    Returns:
        Dictionary chứa kết quả tổng hợp cuối cùng
    """
    # 1. Lọc kết quả hợp lệ
    valid_results = [r for r in results if r.is_valid]
    all_results_dict = [r.to_dict() for r in results]
    
    if not valid_results:
        return {
            "status": "no_valid_results",
            "message": "Không có pipeline nào trả về kết quả hợp lệ",
            "pipeline_details": all_results_dict,
            "confidence": 0.0,
        }
    
    if len(valid_results) < MIN_PIPELINE_RESPONSES:
        print(f"[Voting] ⚠ Chỉ có {len(valid_results)} pipeline hợp lệ "
              f"(yêu cầu tối thiểu {MIN_PIPELINE_RESPONSES})")
    
    # 2. Tính weighted score
    scored = []
    for r in valid_results:
        weight = PIPELINE_WEIGHTS.get(r.pipeline_name, 0.1)
        weighted_score = r.confidence * weight
        scored.append((weighted_score, r))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    
    # 3. Voting theo triều đại
    dynasty_votes: Dict[str, float] = {}
    for score, r in scored:
        dynasty = r.trieu_dai.strip()
        if dynasty:
            dynasty_votes[dynasty] = dynasty_votes.get(dynasty, 0.0) + score
    
    voted_dynasty = ""
    if dynasty_votes:
        voted_dynasty = max(dynasty_votes, key=dynasty_votes.get)
    
    # 4. Chọn pipeline chính (highest weighted score)
    best_score, best_result = scored[0]
    
    # 5. Xây dựng kết quả cuối cùng
    # Bổ sung thông tin từ pipeline khác nếu pipeline chính thiếu
    final = {
        "status": "success",
        "confidence": round(best_result.confidence, 4),
        "voted_dynasty": voted_dynasty,
        "dynasty_votes": dynasty_votes,
        
        # Thông tin chính từ pipeline tốt nhất
        "chu_han": best_result.chu_han,
        "trieu_dai": best_result.trieu_dai or voted_dynasty,
        "nien_hieu": best_result.nien_hieu,
        "hoang_de": best_result.hoang_de,
        "nam_bat_dau": best_result.nam_bat_dau,
        "nam_ket_thuc": best_result.nam_ket_thuc,
        "phien_am": best_result.phien_am,
        "y_nghia": best_result.y_nghia,
        
        # Metadata
        "primary_pipeline": best_result.pipeline_name,
        "num_valid_pipelines": len(valid_results),
        "search_sources": [],
        "llm_explanation": best_result.llm_explanation,
        
        # Chi tiết từng pipeline
        "pipeline_details": all_results_dict,
    }
    
    # Cross-reference: bổ sung thông tin thiếu từ pipeline khác
    for _, r in scored[1:]:
        if not final["hoang_de"] and r.hoang_de:
            final["hoang_de"] = r.hoang_de
        if not final["phien_am"] and r.phien_am:
            final["phien_am"] = r.phien_am
        if not final["y_nghia"] and r.y_nghia:
            final["y_nghia"] = r.y_nghia
        if r.search_sources:
            final["search_sources"].extend(r.search_sources)
    
    # Tính confidence tổng hợp
    total_weight = sum(PIPELINE_WEIGHTS.get(r.pipeline_name, 0.1) for r in valid_results)
    if total_weight > 0:
        agg_confidence = sum(
            r.confidence * PIPELINE_WEIGHTS.get(r.pipeline_name, 0.1)
            for r in valid_results
        ) / total_weight
        final["aggregated_confidence"] = round(agg_confidence, 4)
    
    print(f"\n[Voting] 🗳️ Kết quả tổng hợp:")
    print(f"  Primary: {best_result.pipeline_name} (score={best_score:.4f})")
    print(f"  Triều đại (voted): {voted_dynasty}")
    print(f"  Confidence: {final['confidence']}")
    print(f"  Pipelines hợp lệ: {len(valid_results)}/{len(results)}")
    
    return final
