"""
Pipeline 1: OCR → LLM Extract → LLM Verify

Luồng xử lý:
1. Tiền xử lý ảnh (OpenCV) — sử dụng ocr_engine.py hiện có
2. PaddleOCR nhận dạng chữ Hán
3. LLM #1 (Extract): Phân tích text OCR → thông tin hiệu đề
4. LLM #2 (Verify): Kiểm tra chéo, sửa lỗi nếu có
5. Trả về PipelineResult

Đây là pipeline chính xác nhất khi OCR đọc được text rõ ràng.
"""
import json
from typing import Any, Dict, List, Optional

from pipelines.base import BasePipeline, PipelineResult, PipelineStatus
from services.llm_service import (
    call_llm,
    parse_llm_json,
    PROMPT_EXTRACT_INFO,
    PROMPT_VERIFY_INFO,
)


class PipelineOcrLlm(BasePipeline):
    """
    Pipeline 1: OCR + LLM Extract + LLM Verify
    
    Sử dụng PaddleOCR (đã có) để đọc chữ Hán,
    sau đó dùng LLM phân tích và kiểm tra chéo.
    """

    @property
    def name(self) -> str:
        return "ocr_llm"

    async def _run(self, image_bytes: bytes, **kwargs) -> PipelineResult:
        """
        Xử lý chính của Pipeline 1.
        
        Args:
            image_bytes: Ảnh gốc dưới dạng bytes
            **kwargs:
                ocr_text (str): Text OCR đã đọc sẵn (nếu có, bỏ qua bước OCR)
                ocr_candidates (list): Danh sách candidate OCR
                skip_verify (bool): Bỏ qua bước LLM Verify (mặc định False)
        """
        ocr_text = kwargs.get("ocr_text", "")
        ocr_candidates = kwargs.get("ocr_candidates", [])
        skip_verify = kwargs.get("skip_verify", False)
        database = kwargs.get("database") or []
        allow_db_short_circuit = kwargs.get("allow_db_short_circuit", True)

        # =============================================
        # Bước 1: OCR — Đọc chữ Hán từ ảnh
        # =============================================
        if not ocr_text:
            print(f"[{self.name}] 📷 Bước 1: Chạy OCR...")
            ocr_text, ocr_candidates = await self._run_ocr(image_bytes)
        
        if not ocr_text:
            return PipelineResult(
                pipeline_name=self.name,
                status=PipelineStatus.FAILED,
                error_message="OCR không đọc được chữ nào từ ảnh",
                raw_ocr_text="",
            )
        
        print(f"[{self.name}] 📝 OCR text: '{ocr_text}'")
        if ocr_candidates:
            print(f"[{self.name}] 📝 Candidates: {ocr_candidates[:5]}")

        db_match, match_type = self._match_database(ocr_text, database)
        if allow_db_short_circuit and db_match:
            print(f"[{self.name}] Database short-circuit: {db_match.get('ten_viet', '')} ({match_type})")
            return self._build_result_from_db(db_match, match_type, ocr_text, ocr_candidates)

        # =============================================
        # Bước 2: LLM Extract — Phân tích thông tin
        # =============================================
        print(f"[{self.name}] 🤖 Bước 2: LLM Extract Info...")
        
        extract_prompt = PROMPT_EXTRACT_INFO.format(ocr_text=ocr_text)
        extract_response = await call_llm(extract_prompt)
        
        if not extract_response:
            return PipelineResult(
                pipeline_name=self.name,
                status=PipelineStatus.PARTIAL,
                confidence=0.3,
                raw_ocr_text=ocr_text,
                chu_han=ocr_text,
                error_message="LLM Extract không phản hồi",
            )
        
        extracted = parse_llm_json(extract_response)
        if not extracted:
            return PipelineResult(
                pipeline_name=self.name,
                status=PipelineStatus.PARTIAL,
                confidence=0.3,
                raw_ocr_text=ocr_text,
                chu_han=ocr_text,
                llm_explanation=extract_response[:500],
                error_message="Không parse được JSON từ LLM Extract",
            )
        
        print(f"[{self.name}] ✅ LLM Extract: {json.dumps(extracted, ensure_ascii=False)[:200]}")

        # =============================================
        # Bước 3: LLM Verify — Kiểm tra chéo
        # =============================================
        if not skip_verify:
            print(f"[{self.name}] 🔍 Bước 3: LLM Verify...")
            
            verify_prompt = PROMPT_VERIFY_INFO.format(
                analysis_json=json.dumps(extracted, ensure_ascii=False, indent=2),
                ocr_text=ocr_text,
            )
            verify_response = await call_llm(verify_prompt)
            
            if verify_response:
                verified = parse_llm_json(verify_response)
                if verified:
                    print(f"[{self.name}] 🔍 Verify result: correct={verified.get('is_correct')}, "
                          f"confidence={verified.get('confidence')}")
                    
                    # Nếu có corrections, dùng verified_result
                    verified_result = verified.get("verified_result", {})
                    if verified_result:
                        extracted = {**extracted, **verified_result}
                    
                    # Cập nhật confidence từ verify
                    if verified.get("confidence") is not None:
                        extracted["do_tin_cay"] = verified["confidence"]
                    
                    # Lưu explanation
                    extracted["_verify_explanation"] = verified.get("explanation", "")
        
        # =============================================
        # Bước 4: Build PipelineResult
        # =============================================
        confidence = float(extracted.get("do_tin_cay", 0.5))
        
        return PipelineResult(
            pipeline_name=self.name,
            status=PipelineStatus.SUCCESS,
            confidence=confidence,
            chu_han=extracted.get("chu_han", ocr_text),
            trieu_dai=extracted.get("trieu_dai", ""),
            nien_hieu=extracted.get("nien_hieu", ""),
            hoang_de=extracted.get("hoang_de", ""),
            nam_bat_dau=self._safe_int(extracted.get("nam_bat_dau")),
            nam_ket_thuc=self._safe_int(extracted.get("nam_ket_thuc")),
            phien_am=extracted.get("phien_am", ""),
            y_nghia=extracted.get("y_nghia", ""),
            raw_ocr_text=ocr_text,
            llm_explanation=extracted.get("_verify_explanation", extracted.get("ghi_chu", "")),
            extra_data={
                "ocr_candidates": ocr_candidates[:5],
                "llm_raw_extract": extracted,
            },
        )

    async def _run_ocr(self, image_bytes: bytes) -> tuple:
        """
        Chạy PaddleOCR sử dụng ocr_engine.py hiện có.
        
        Returns:
            (primary_text, candidates_list)
        """
        import asyncio
        
        def _ocr_sync():
            from ocr_engine import read_chinese_mark
            result = read_chinese_mark(image_bytes, deep_mode=True)
            
            if result.get("error"):
                return "", []
            
            # read_chinese_mark trả về: {"text": "...", "candidates": [...], "confidence": ..., "all_results": [...]}
            primary = result.get("text", "")
            candidates = result.get("candidates", [])
            
            return primary, candidates
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _ocr_sync)

    def _match_database(self, ocr_text: str, database: List[Dict[str, Any]]) -> tuple:
        query = self._norm_cjk(ocr_text)
        if not query or not database:
            return None, "none"

        generic_partials = {"年製", "年制", "年造", "大清", "大明", "大南"}
        partial_matches = []

        for entry in database:
            for target in self._entry_targets(entry):
                target_norm = self._norm_cjk(target)
                if target_norm == query:
                    return entry, "exact"

            if len(query) >= 2 and query not in generic_partials:
                for target in self._entry_targets(entry):
                    target_norm = self._norm_cjk(target)
                    if target_norm and query in target_norm:
                        score = len(query) / max(len(target_norm), 1)
                        partial_matches.append((score, entry))

        if partial_matches:
            partial_matches.sort(key=lambda x: x[0], reverse=True)
            return partial_matches[0][1], "partial"
        return None, "none"

    def _build_result_from_db(
        self,
        match: Dict[str, Any],
        match_type: str,
        ocr_text: str,
        ocr_candidates: List[str],
    ) -> PipelineResult:
        confidence_map = {
            "exact": 0.94,
            "partial": 0.78,
        }
        return PipelineResult(
            pipeline_name=self.name,
            status=PipelineStatus.SUCCESS,
            confidence=confidence_map.get(match_type, 0.70),
            chu_han=ocr_text,
            trieu_dai=match.get("trieu_dai", ""),
            nien_hieu=match.get("nien_hieu", ""),
            hoang_de=match.get("hoang_de", ""),
            nam_bat_dau=self._safe_int(match.get("nam_bat_dau")),
            nam_ket_thuc=self._safe_int(match.get("nam_ket_thuc")),
            phien_am=match.get("phien_am", ""),
            y_nghia=match.get("ghi_chu", ""),
            raw_ocr_text=ocr_text,
            extra_data={
                "match_type": match_type,
                "source": "database_short_circuit",
                "ocr_candidates": ocr_candidates[:5],
            },
        )

    @staticmethod
    def _norm_cjk(value: str) -> str:
        normalized = "".join(ch for ch in (value or "") if "\u4e00" <= ch <= "\u9fff")
        return normalized.translate(str.maketrans({
            "绪": "緒",
            "统": "統",
            "历": "曆",
            "万": "萬",
            "制": "製",
            "内": "內",
        }))

    @staticmethod
    def _entry_targets(entry: Dict[str, Any]) -> List[str]:
        fields = [
            entry.get("chu_han", ""),
            entry.get("chu_han_4", ""),
            entry.get("chu_han_6", ""),
        ]
        fields.extend([bt for bt in (entry.get("bien_the") or []) if bt])
        return [field for field in fields if field]
    
    @staticmethod
    def _safe_int(value) -> Optional[int]:
        """Chuyển giá trị thành int an toàn."""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
