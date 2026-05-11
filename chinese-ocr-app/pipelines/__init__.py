"""Pipelines package — chứa 4 pipeline xử lý chính và orchestrator."""
from .base import BasePipeline, PipelineResult, PipelineStatus
from .pipeline_ocr_llm import PipelineOcrLlm
from .pipeline_ocr_search import PipelineOcrSearch
from .pipeline_img_search import PipelineImgSearch
from .pipeline_ml_match import PipelineMlMatch
from .orchestrator import analyze_image, analyze_quick, analyze_deep

__all__ = [
    "BasePipeline", "PipelineResult", "PipelineStatus",
    "PipelineOcrLlm", "PipelineOcrSearch", "PipelineImgSearch", "PipelineMlMatch",
    "analyze_image", "analyze_quick", "analyze_deep",
]
