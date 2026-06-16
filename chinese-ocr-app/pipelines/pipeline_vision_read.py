"""
Pipeline: AI Vision reads the visible mark directly from the uploaded image.

This produces visual-text evidence for the final web verification layer. It is
not allowed to be the only proof for high-confidence final attribution.
"""
from typing import Any, Dict, Optional

from pipelines.base import BasePipeline, PipelineResult, PipelineStatus
from services.vision_service import analyze_mark_image, is_unknown_neifu_suffix


class PipelineVisionRead(BasePipeline):
    def __init__(self, provider: str = "", pipeline_name: str = "vision_read"):
        self.provider = provider
        self.pipeline_name = pipeline_name

    @property
    def name(self) -> str:
        return self.pipeline_name

    async def _run(self, image_bytes: bytes, **kwargs) -> PipelineResult:
        result = await analyze_mark_image(image_bytes, provider=self.provider, allow_fallback=False)
        status = result.get("status")
        if status == "failed":
            errors = result.get("errors") or []
            message = "; ".join(errors[:3]) if errors else "unknown cause"
            return PipelineResult(
                pipeline_name=self.name,
                status=PipelineStatus.FAILED,
                error_message=f"{self.name} could not read the image: " + message,
                extra_data=result,
            )

        chu_han = result.get("chu_han", "")
        if not chu_han:
            return PipelineResult(
                pipeline_name=self.name,
                status=PipelineStatus.PARTIAL,
                confidence=0.25,
                error_message=f"{self.name} could not clearly identify Chinese characters",
                llm_explanation=result.get("notes", ""),
                extra_data=result,
            )

        confidence = float(result.get("confidence") or 0.55)
        unknown_neifu_suffix = bool(result.get("unknown_neifu_suffix")) or is_unknown_neifu_suffix(chu_han)
        if unknown_neifu_suffix:
            confidence = min(confidence, 0.42)
            status = PipelineStatus.PARTIAL
            error_message = "AI Vision read an unsupported or uncertain Noi Phu suffix"
        elif _is_generic_short_mark(chu_han):
            confidence = min(confidence, 0.30)
            status = PipelineStatus.PARTIAL
            error_message = "AI Vision only read a dynasty fragment, not enough for a reign title"
        else:
            status = PipelineStatus.SUCCESS if confidence >= 0.55 else PipelineStatus.PARTIAL
            error_message = ""
        return PipelineResult(
            pipeline_name=self.name,
            status=status,
            confidence=max(0.25, min(confidence, 0.88)),
            chu_han=chu_han,
            trieu_dai=_infer_dynasty(result),
            nien_hieu=_infer_nien_hieu(result),
            phien_am=result.get("phien_am", ""),
            raw_ocr_text=chu_han,
            llm_explanation=result.get("notes", ""),
            error_message=error_message,
            extra_data={
                **result,
                "source": self.name,
                "provider": result.get("provider") or self.provider,
                "vision_candidates": result.get("chu_han_candidates") or [],
                "unknown_neifu_suffix": unknown_neifu_suffix,
                "allow_partial_db_match": False if unknown_neifu_suffix else result.get("allow_partial_db_match", True),
            },
        )


def _infer_dynasty(result: Dict[str, Any]) -> str:
    explicit = result.get("trieu_dai") or result.get("dynasty") or ""
    if explicit:
        return explicit
    text = result.get("chu_han", "")
    if "內府" in text or "内府" in text:
        return "Nguyen Dynasty (Vietnam)"
    if "大清" in text:
        return "Qing"
    if "大明" in text:
        return "Ming"
    if "大南" in text:
        return "Nguyen"
    return ""


def _is_generic_short_mark(text: str) -> bool:
    clean = "".join(ch for ch in (text or "") if "\u4e00" <= ch <= "\u9fff")
    clean = clean.translate(str.maketrans({
        "绪": "緒",
        "统": "統",
        "历": "曆",
        "万": "萬",
        "制": "製",
        "内": "內",
    }))
    return clean in {"大明", "大清", "大南", "年製", "年造", "大明年製", "大清年製", "大南年製"}


def _infer_nien_hieu(result: Dict[str, Any]) -> str:
    if result.get("unknown_neifu_suffix") or is_unknown_neifu_suffix(result.get("chu_han", "")):
        return ""
    explicit = result.get("nien_hieu") or result.get("reign") or ""
    if explicit:
        return explicit
    text = result.get("chu_han", "")
    if text.startswith("內府侍") or text.startswith("内府侍"):
        return "Nội Phủ Thị"
    return ""
