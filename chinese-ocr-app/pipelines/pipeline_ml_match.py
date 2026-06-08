"""
Pipeline 4: ML/ORB Feature Matching → Thông tin cơ bản

Wrap code hiện tại (reference_matcher.py + main.py rule-based matching)
thành pipeline chuẩn để tham gia Voting.

Luồng xử lý:
1. Tiền xử lý ảnh
2. ORB Feature Matching (so sánh với thư viện tham chiếu)
3. Nếu không match ORB → Rule-based matching từ OCR text + database
4. Trả về PipelineResult với thông tin cơ bản
"""
import asyncio
from typing import Any, Dict, List, Optional

from pipelines.base import BasePipeline, PipelineResult, PipelineStatus


class PipelineMlMatch(BasePipeline):
    """
    Pipeline 4: ML/ORB Feature Matching
    
    Sử dụng ORB (reference_matcher.py) và rule-based matching (main.py)
    đã có sẵn, wrap thành pipeline chuẩn.
    """

    @property
    def name(self) -> str:
        return "ml_match"

    async def _run(self, image_bytes: bytes, **kwargs) -> PipelineResult:
        """
        Xử lý chính của Pipeline 4.
        
        Args:
            image_bytes: Ảnh gốc dưới dạng bytes
            **kwargs:
                ocr_text (str): Text OCR đã đọc sẵn (nếu có)
                database (list): Database hiệu đề (nếu có)
        """
        ocr_text = kwargs.get("ocr_text", "")
        database = kwargs.get("database", None)

        # =============================================
        # Bước 1: ORB Feature Matching
        # =============================================
        print(f"[{self.name}] 🔍 Bước 1: ORB Feature Matching...")
        
        orb_result = await self._run_orb_matching(image_bytes)
        
        if orb_result:
            print(f"[{self.name}] ✅ ORB match found! Type: {orb_result.get('match_type')}")
            return self._build_result_from_match(orb_result, source="orb")

        # =============================================
        # Bước 2: Rule-based matching từ OCR text
        # =============================================
        if not ocr_text:
            ocr_text = await self._run_ocr_text(image_bytes)

        if ocr_text and database:
            print(f"[{self.name}] 📊 Bước 2: Rule-based matching...")
            
            rule_result = await self._run_rule_matching(ocr_text, database)
            
            if rule_result:
                print(f"[{self.name}] ✅ Rule match found! Type: {rule_result.get('match_type')}")
                return self._build_result_from_match(rule_result, source="rule")

        # =============================================
        # Không tìm thấy kết quả
        # =============================================
        return PipelineResult(
            pipeline_name=self.name,
            status=PipelineStatus.FAILED,
            confidence=0.0,
            raw_ocr_text=ocr_text,
            error_message="Không tìm thấy match trong ORB library hoặc database",
        )

    async def _run_orb_matching(self, image_bytes: bytes) -> Optional[Dict[str, Any]]:
        """Chạy ORB matching sử dụng reference_matcher.py hiện có."""
        loop = asyncio.get_event_loop()
        
        def _orb_sync():
            try:
                from reference_matcher import match_image
                return match_image(image_bytes)
            except Exception as e:
                print(f"[{self.name}/ORB] ⚠ Error: {e}")
                return None
        
        return await loop.run_in_executor(None, _orb_sync)

    async def _run_ocr_text(self, image_bytes: bytes) -> str:
        """Read text for rule matching when OCR text was not provided."""
        loop = asyncio.get_event_loop()

        def _ocr_sync():
            try:
                from ocr_engine import read_chinese_mark
                result = read_chinese_mark(image_bytes, deep_mode=True)
                if result.get("error"):
                    print(f"[{self.name}/OCR] Skip rule OCR: {result.get('error')}")
                    return ""
                return result.get("text", "") or ""
            except Exception as e:
                print(f"[{self.name}/OCR] Error: {e}")
                return ""

        return await loop.run_in_executor(None, _ocr_sync)

    async def _run_rule_matching(
        self, ocr_text: str, database: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Chạy rule-based matching sử dụng logic từ main.py."""
        loop = asyncio.get_event_loop()
        
        def _rule_sync():
            try:
                # Import các hàm matching từ main.py
                import sys
                import os
                sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
                from main import _find_match, find_best_matches
                
                match, match_type = _find_match(ocr_text, database)
                
                if match:
                    norm_ocr = "".join(ch for ch in (ocr_text or "") if "\u4e00" <= ch <= "\u9fff")
                    generic_partials = {"年製", "年制", "年造", "大清", "大明", "大南"}
                    targets = [
                        match.get("chu_han", ""),
                        match.get("chu_han_4", ""),
                        match.get("chu_han_6", ""),
                    ]
                    targets.extend(match.get("bien_the", []) or [])
                    if len(norm_ocr) >= 2 and norm_ocr not in generic_partials:
                        for target in targets:
                            norm_target = "".join(ch for ch in (target or "") if "\u4e00" <= ch <= "\u9fff")
                            if norm_target and norm_ocr != norm_target and norm_ocr in norm_target:
                                match_type = "partial_ocr"
                                break
                    return {**match, "match_type": match_type}
                
                # Thử top matches
                top = find_best_matches(ocr_text, database, top_n=1)
                if top and top[0].get("raw_score", 0) > 0.5:
                    return {**top[0], "match_type": "fuzzy_top1"}
                
                return None
            except Exception as e:
                print(f"[{self.name}/Rule] ⚠ Error: {e}")
                return None
        
        return await loop.run_in_executor(None, _rule_sync)

    def _build_result_from_match(
        self, match: Dict[str, Any], source: str
    ) -> PipelineResult:
        """Chuyển kết quả match (ORB hoặc rule) thành PipelineResult."""
        match_type = match.get("match_type", "unknown")
        
        # Tính confidence dựa trên match_type
        confidence_map = {
            "exact": 0.95,
            "exact_orb_memory": 0.92,
            "substring": 0.80,
            "partial_ocr": 0.78,
            "fuzzy": 0.60,
            "fuzzy_tiedecision": 0.55,
            "fuzzy_top1": 0.50,
            "orb_memory_soft": 0.45,
        }
        confidence = confidence_map.get(match_type, 0.40)
        chu_han = match.get("chu_han", "")
        if self._is_generic_or_incomplete_mark(chu_han) and confidence < 0.85:
            return PipelineResult(
                pipeline_name=self.name,
                status=PipelineStatus.FAILED,
                confidence=0.0,
                chu_han=chu_han,
                raw_ocr_text=chu_han,
                error_message=(
                    "Bỏ qua kết quả generic thiếu niên hiệu "
                    f"({chu_han}) từ {source}/{match_type}"
                ),
                extra_data={
                    "match_type": match_type,
                    "source": source,
                },
            )
        
        # Xác định năm
        nam_bat_dau = None
        nam_ket_thuc = None
        try:
            if match.get("nam_bat_dau"):
                nam_bat_dau = int(match["nam_bat_dau"])
            if match.get("nam_ket_thuc"):
                nam_ket_thuc = int(match["nam_ket_thuc"])
        except (ValueError, TypeError):
            pass
        
        return PipelineResult(
            pipeline_name=self.name,
            status=PipelineStatus.SUCCESS,
            confidence=confidence,
            chu_han=chu_han,
            trieu_dai=match.get("trieu_dai", ""),
            nien_hieu=self._extract_nien_hieu(match),
            hoang_de=match.get("hoang_de", ""),
            nam_bat_dau=nam_bat_dau,
            nam_ket_thuc=nam_ket_thuc,
            phien_am=match.get("phien_am", ""),
            y_nghia=match.get("ghi_chu", ""),
            raw_ocr_text=match.get("chu_han", ""),
            extra_data={
                "match_type": match_type,
                "source": source,
                "orb_best": match.get("_orb_best"),
                "orb_second": match.get("_orb_second"),
                "match_score": match.get("match_score"),
            },
        )

    @staticmethod
    def _is_incomplete_dynasty_mark(value: str) -> bool:
        norm = "".join(ch for ch in (value or "") if "\u4e00" <= ch <= "\u9fff")
        norm = norm.translate(str.maketrans({
            "绪": "緒",
            "统": "統",
            "历": "曆",
            "万": "萬",
            "制": "製",
            "内": "內",
        }))
        return norm in {"大明年製", "大清年製", "大南年製"}

    @staticmethod
    def _is_generic_or_incomplete_mark(value: str) -> bool:
        norm = "".join(ch for ch in (value or "") if "\u4e00" <= ch <= "\u9fff")
        norm = norm.translate(str.maketrans({
            "绪": "緒",
            "统": "統",
            "历": "曆",
            "万": "萬",
            "制": "製",
            "内": "內",
        }))
        return norm in {"大明", "大清", "大南", "年製", "年造", "大明年製", "大清年製", "大南年製"}

    @staticmethod
    def _extract_nien_hieu(match: Dict[str, Any]) -> str:
        """Trích xuất niên hiệu từ kết quả match."""
        base = match.get("chu_han_4") or match.get("chu_han") or ""
        base = base.replace("大明", "").replace("大清", "").replace("大南", "")
        for suffix in ["年製", "年造", "年玩"]:
            if base.endswith(suffix):
                base = base[: -len(suffix)]
        return base or ""
