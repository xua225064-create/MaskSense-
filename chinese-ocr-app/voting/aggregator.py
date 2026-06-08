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


def aggregate_results(results: List[PipelineResult], database: Optional[List[dict]] = None) -> Dict[str, Any]:
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
    def _norm_cjk(val: str) -> str:
        """Chỉ giữ ký tự CJK và chuẩn hóa biến thể giản/phồn thể phổ biến."""
        if not val:
            return ""
        normalized = "".join(ch for ch in val if "\u4e00" <= ch <= "\u9fff")
        return normalized.translate(str.maketrans({
            "绪": "緒",
            "统": "統",
            "历": "曆",
            "万": "萬",
            "制": "製",
            "内": "內",
        }))

    def _is_incomplete_dynasty_mark(value: str) -> bool:
        return _norm_cjk(value) in {"大明年製", "大清年製", "大南年製"}

    def _is_generic_short_mark(value: str) -> bool:
        return _norm_cjk(value) in {"大明", "大清", "大南", "年製", "年造"}

    def _is_weak_generic_result(result: PipelineResult) -> bool:
        if not (_is_incomplete_dynasty_mark(result.chu_han) or _is_generic_short_mark(result.chu_han)):
            return False
        match_type = (result.extra_data or {}).get("match_type", "")
        source = (result.extra_data or {}).get("source", "")
        strong_source = source in {"database_short_circuit", "orb"} and match_type in {"exact", "exact_orb_memory"}
        return result.confidence < 0.85 or not strong_source

    # 1. Lọc kết quả hợp lệ, đồng thời loại kết luận generic yếu kiểu 大明年製.
    valid_results = [r for r in results if r.is_valid and not _is_weak_generic_result(r)]
    all_results_dict = [r.to_dict() for r in results]
    
    if not valid_results:
        return {
            "status": "no_valid_results",
            "message": "Không có pipeline nào trả về kết quả hợp lệ; đã bỏ qua kết luận generic thiếu niên hiệu nếu confidence thấp.",
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
        dynasty = (r.trieu_dai or "").strip()
        if dynasty:
            dynasty_votes[dynasty] = dynasty_votes.get(dynasty, 0.0) + score
    
    voted_dynasty = ""
    if dynasty_votes:
        voted_dynasty = max(dynasty_votes, key=dynasty_votes.get)
    
    # 4. Chọn pipeline chính (highest weighted score)
    best_score, best_result = scored[0]

    def _dynasty_key(value: str) -> str:
        raw = (value or "").lower()
        if "thanh" in raw or "qing" in raw or "清" in raw:
            return "qing"
        if "minh" in raw or "ming" in raw or "明" in raw:
            return "ming"
        if "nguyen" in raw or "nguyễn" in raw or "nam" in raw or "南" in raw:
            return "nguyen"
        return raw.strip()

    voted_key = _dynasty_key(voted_dynasty)
    best_key = _dynasty_key(best_result.trieu_dai)
    if voted_key and best_key and voted_key != best_key:
        consensus = [
            (score, r)
            for score, r in scored[1:]
            if _dynasty_key(r.trieu_dai) == voted_key and r.confidence >= 0.65
        ]
        if consensus and (
            best_result.pipeline_name == "ml_match"
            or consensus[0][0] >= best_score * 0.75
        ):
            print(
                "[Voting] Consensus override: "
                f"{best_result.pipeline_name}/{best_result.trieu_dai} -> "
                f"{consensus[0][1].pipeline_name}/{consensus[0][1].trieu_dai}"
            )
            best_score, best_result = consensus[0]
            voted_dynasty = best_result.trieu_dai or voted_dynasty

    if best_result.pipeline_name == "ml_match" and best_result.extra_data.get("source") == "orb":
        orb_best = float(best_result.extra_data.get("orb_best") or 0)
        orb_second = float(best_result.extra_data.get("orb_second") or 0)
        orb_ratio = orb_best / max(orb_second, 1.0)
        weak_orb = bool(orb_second) and ((orb_best - orb_second) < 30 or orb_ratio < 1.25)
        challengers = [
            (score, r)
            for score, r in scored[1:]
            if r.pipeline_name != "ml_match"
            and r.confidence >= 0.80
            and _dynasty_key(r.trieu_dai)
            and _dynasty_key(r.trieu_dai) != _dynasty_key(best_result.trieu_dai)
            and score >= best_score * 0.70
        ]
        if weak_orb and challengers:
            print(
                "[Voting] Weak ORB override: "
                f"orb_best={orb_best:.0f}, orb_second={orb_second:.0f}, "
                f"ratio={orb_ratio:.2f}"
            )
            best_score, best_result = challengers[0]
            voted_dynasty = best_result.trieu_dai or voted_dynasty
    
    # Tìm database entry tương ứng để lấy thông tin chi tiết
    # FIX: Normalize CJK để match cả 内 (simplified) vs 內 (traditional)
    db_entry = None
    db_match_type = "none"
    db_matched_text = ""
    best_chu_han = best_result.chu_han  # Will be refined below
    
    def _entry_targets(entry: dict) -> List[str]:
        fields = [
            entry.get("chu_han", ""),
            entry.get("chu_han_4", ""),
            entry.get("chu_han_6", ""),
        ]
        fields.extend([bt for bt in (entry.get("bien_the") or []) if bt])
        return [field for field in fields if field]
    
    if database and best_result.chu_han:
        ocr_norm = _norm_cjk(best_result.chu_han)
        
        for entry in database:
            # Thử match theo nhiều field
            match_fields = [
                entry.get("chu_han", ""),
                entry.get("chu_han_4", ""),
                entry.get("chu_han_6", ""),
            ]
            # Thêm biến thể
            for bt in (entry.get("bien_the") or []):
                if bt:
                    match_fields.append(bt)
            
            for field_val in match_fields:
                if field_val and _norm_cjk(field_val) == ocr_norm:
                    db_entry = entry
                    db_match_type = "exact"
                    db_matched_text = field_val
                    break
            if db_entry:
                break

        if not db_entry and len(ocr_norm) >= 2:
            generic_partials = {"年製", "年制", "年造", "大清", "大明", "大南"}
            if ocr_norm not in generic_partials:
                partial_matches = []
                for entry in database:
                    for field_val in _entry_targets(entry):
                        target_norm = _norm_cjk(field_val)
                        if target_norm and ocr_norm in target_norm:
                            score = len(ocr_norm) / max(len(target_norm), 1)
                            partial_matches.append((score, entry, field_val))
                if partial_matches:
                    partial_matches.sort(key=lambda x: x[0], reverse=True)
                    _, db_entry, db_matched_text = partial_matches[0]
                    db_match_type = "partial"
        
        # Logic: Nếu database có chu_han_4 và chu_han_6 khác nhau
        # Hãy chọn version phù hợp với độ dài OCR
        # (tránh trường hợp trả 6 chữ khi ảnh chỉ có 4 chữ)
        if db_entry:
            full_chu_han = db_entry.get("chu_han") or ""
            chu_han_4 = db_entry.get("chu_han_4") or db_entry.get("chu_han") or ""
            chu_han_6 = db_entry.get("chu_han_6") or ""
            if not chu_han_6 and len(_norm_cjk(full_chu_han)) >= 6:
                chu_han_6 = full_chu_han
            
            # Nếu OCR có tín hiệu >=6 chữ, ưu tiên 6 chữ; ngược lại dùng 4 chữ
            # (Tránh thêm tiền tố Dynasty khi ảnh chỉ có Mark phần chính)
            if db_match_type == "partial" and len(ocr_norm) <= 2 and full_chu_han:
                best_chu_han = full_chu_han
            elif len(chu_han_4) == 4 and len(chu_han_6) == 6:
                # Có cả 2 version -> quyết định dựa trên OCR length
                ocr_len = len(_norm_cjk(best_result.chu_han))
                if ocr_len <= 4:
                    best_chu_han = chu_han_4
                else:
                    best_chu_han = chu_han_6
            elif len(chu_han_4) == 4:
                # Chỉ có 4-char version
                best_chu_han = chu_han_4
            
            print(f"[Voting] 📚 Database match found: {db_entry.get('ten_viet', '')} "
                  f"(id={db_entry.get('id')})")
    
    # ================================================================
    # 5. Xây dựng kết quả cuối cùng
    # NGUYÊN TẮC: Database là nguồn ưu tiên cao nhất cho thông tin lịch sử.
    # LLM chỉ bổ sung khi database không có hoặc thiếu field.
    # ================================================================
    
    # Helper: lấy giá trị ưu tiên db_entry > best_result > default
    def _db_or_pipeline(db_field, pipeline_val, default=""):
        """Ưu tiên database, fallback pipeline, fallback default."""
        if db_entry:
            val = db_entry.get(db_field)
            if val is not None and val != "" and val != "Chưa xác định":
                return val
        if pipeline_val is not None and pipeline_val != "" and pipeline_val != "Chưa xác định":
            return pipeline_val
        return default
    
    # Lấy thông tin ưu tiên từ DB
    final_trieu_dai = _db_or_pipeline("trieu_dai", best_result.trieu_dai, voted_dynasty)
    final_nien_hieu = _db_or_pipeline("nien_hieu", best_result.nien_hieu, "")
    final_hoang_de = _db_or_pipeline("hoang_de", best_result.hoang_de, "")
    final_phien_am = _db_or_pipeline("phien_am", best_result.phien_am, "")
    final_ten_viet_short = _db_or_pipeline("ten_viet", "", "")
    final_hien_thi_chinh = _db_or_pipeline("hien_thi_chinh", "", "")
    final_hieu_de_vi = _db_or_pipeline("hieu_de_vi", "", "")
    if len(_norm_cjk(best_chu_han)) >= 6:
        final_ten_viet = final_hien_thi_chinh or final_hieu_de_vi or final_ten_viet_short
    else:
        final_ten_viet = final_ten_viet_short or final_hien_thi_chinh or final_hieu_de_vi
    final_nam_bat_dau = _db_or_pipeline("nam_bat_dau", best_result.nam_bat_dau, None)
    final_nam_ket_thuc = _db_or_pipeline("nam_ket_thuc", best_result.nam_ket_thuc, None)
    final_nien_dai = _db_or_pipeline("nien_dai", "", "")
    final_hieu_de_en = _db_or_pipeline("hieu_de_en", "", "")
    final_y_nghia = _db_or_pipeline("ghi_chu", best_result.y_nghia, "")
    
    final = {
        "status": "success",
        "tin_cay": round(best_result.confidence, 4),  # Tiếng Việt
        "confidence": round(best_result.confidence, 4),  # English
        "voted_dynasty": voted_dynasty,
        "dynasty_votes": dynasty_votes,
        
        # Thông tin chính (ưu tiên database > pipeline)
        "chu_han": best_chu_han,
        "hieu_de": best_chu_han,  # Hiệu đề = Chu Hán (Vietnamese name)
        
        "trieu_dai": final_trieu_dai,
        "triều_đại": final_trieu_dai,
        
        "nien_hieu": final_nien_hieu,
        "niên_hiệu": final_nien_hieu,
        
        "hoang_de": final_hoang_de,
        "hoàng_đế": final_hoang_de,
        
        "nam_bat_dau": final_nam_bat_dau,
        "nam_bat_dau_vn": f"{final_nam_bat_dau}" if final_nam_bat_dau else "",
        
        "nam_ket_thuc": final_nam_ket_thuc,
        "nam_ket_thuc_vn": f"{final_nam_ket_thuc}" if final_nam_ket_thuc else "",
        
        "nien_dai": final_nien_dai,
        "niên_đại": final_nien_dai,
        
        "ten_viet": final_ten_viet,
        "tên_việt": final_ten_viet,
        "ten_viet_ngan": final_ten_viet_short,
        "tên_việt_ngắn": final_ten_viet_short,
        "hien_thi_chinh": final_hien_thi_chinh,
        "hieu_de_vi": final_hieu_de_vi or final_hien_thi_chinh,
        
        "phien_am": final_phien_am,
        "phiên_âm": final_phien_am,
        
        "y_nghia": final_y_nghia,
        "ý_nghĩa": final_y_nghia,
        
        "hieu_de_en": final_hieu_de_en,
        
        # Database fields (Mô tả chi tiết - Vietnamese descriptions)
        "mo_ta": db_entry.get("mo_ta", "Đang cập nhật...") if db_entry else "Đang cập nhật...",
        "boi_canh": db_entry.get("mo_ta", "Đang cập nhật...") if db_entry else "Đang cập nhật...",  # Bối cảnh
        
        "nghe_thuat": db_entry.get("nghe_thuat", "Đang cập nhật...") if db_entry else "Đang cập nhật...",
        "dac_diem_nghe_thuat": db_entry.get("nghe_thuat", "Đang cập nhật...") if db_entry else "Đang cập nhật...",  # Đặc điểm nghệ thuật
        
        "thu_phap": db_entry.get("thu_phap", "Đang cập nhật...") if db_entry else "Đang cập nhật...",
        "thu_phap_dac_biet": db_entry.get("thu_phap", "Đang cập nhật...") if db_entry else "Đang cập nhật...",  # Thư pháp đặc biệt
        
        "ghi_chu": db_entry.get("ghi_chu", "") if db_entry else "",
        "ghi_chu_them": db_entry.get("ghi_chu", "") if db_entry else "",  # Ghi chú thêm
        
        # Metadata
        "primary_pipeline": best_result.pipeline_name,
        "pipeline_chinh": best_result.pipeline_name,  # Pipeline chính (Vietnamese)
        
        "num_valid_pipelines": len(valid_results),
        "so_pipeline_hop_le": len(valid_results),  # Số pipeline hợp lệ (Vietnamese)
        
        "search_sources": [],
        "cac_nguon_tham_khao": [],  # Các nguồn tham khảo (Vietnamese)
        
        "llm_explanation": best_result.llm_explanation,
        "giai_thich_llm": best_result.llm_explanation,  # Giải thích LLM (Vietnamese)
        
        # Nguồn dữ liệu chính
        "data_source": "database" if db_entry else "llm_pipeline",
        "nguon_du_lieu": "Cơ sở dữ liệu hiệu đề" if db_entry else "Phân tích AI",
        
        # Chi tiết từng pipeline
        "pipeline_details": all_results_dict,
    }
    
    # Collect search_sources from the best result first
    if best_result.search_sources:
        final["search_sources"].extend(best_result.search_sources)
        final["cac_nguon_tham_khao"].extend(best_result.search_sources)

    # Cross-reference: bổ sung thông tin thiếu từ pipeline khác
    for _, r in scored[1:]:
        if not final["hoang_de"] and r.hoang_de:
            final["hoang_de"] = r.hoang_de
            final["hoàng_đế"] = r.hoang_de
        if not final["phien_am"] and r.phien_am:
            final["phien_am"] = r.phien_am
            final["phiên_âm"] = r.phien_am
        if not final["y_nghia"] and r.y_nghia:
            final["y_nghia"] = r.y_nghia
            final["ý_nghĩa"] = r.y_nghia
        if r.search_sources:
            final["search_sources"].extend(r.search_sources)
            final["cac_nguon_tham_khao"].extend(r.search_sources)
    
    # Tính confidence tổng hợp
    total_weight = sum(PIPELINE_WEIGHTS.get(r.pipeline_name, 0.1) for r in valid_results)
    if total_weight > 0:
        agg_confidence = sum(
            r.confidence * PIPELINE_WEIGHTS.get(r.pipeline_name, 0.1)
            for r in valid_results
        ) / total_weight
        final["aggregated_confidence"] = round(agg_confidence, 4)
    
    # Thêm Vietnamese summary field
    summary_parts = []
    if final.get("chu_han"):
        summary_parts.append(f"Hiệu đề: {final['chu_han']}")
    if final.get("trieu_dai"):
        summary_parts.append(f"Triều: {final['trieu_dai']}")
    if final.get("nien_hieu"):
        summary_parts.append(f"Niên hiệu: {final['nien_hieu']}")
    if final.get("hoang_de"):
        summary_parts.append(f"Hoàng đế: {final['hoang_de']}")
    if final.get("nam_bat_dau") and final.get("nam_ket_thuc"):
        summary_parts.append(f"Giai đoạn: {final['nam_bat_dau']}-{final['nam_ket_thuc']}")
    
    final["tom_tat_tieng_viet"] = " | ".join(summary_parts) if summary_parts else "Không xác định"
    
    print(f"\n[Voting] 🗳️ Kết quả tổng hợp:")
    print(f"  Pipeline chính: {best_result.pipeline_name} (score={best_score:.4f})")
    print(f"  Triều đại: {voted_dynasty}")
    print(f"  Tín cậy: {final['confidence']:.2%}")
    print(f"  Pipeline hợp lệ: {len(valid_results)}/{len(results)}")
    
    return final
