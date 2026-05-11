"""
Base Pipeline — Lớp cơ sở cho tất cả pipeline trong hệ thống Multi-Pipeline.

Mỗi pipeline phải implement method `execute()` và trả về PipelineResult.
Thiết kế theo Abstract Base Class pattern để đảm bảo tính nhất quán
giữa 4 pipeline khác nhau.
"""
import time
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class PipelineStatus(Enum):
    """Trạng thái kết quả pipeline."""
    SUCCESS = "success"           # Pipeline chạy thành công, có kết quả
    PARTIAL = "partial"           # Chạy được nhưng thiếu thông tin
    FAILED = "failed"             # Pipeline lỗi, không có kết quả
    TIMEOUT = "timeout"           # Pipeline quá thời gian cho phép
    SKIPPED = "skipped"           # Pipeline bị bỏ qua (thiếu config, etc.)


@dataclass
class PipelineResult:
    """
    Kết quả trả về từ mỗi pipeline.
    
    Cấu trúc thống nhất để Voting Logic có thể tổng hợp dễ dàng,
    bất kể pipeline nào trả về.
    """
    pipeline_name: str                          # Tên pipeline: "ocr_llm", "ocr_search", ...
    status: PipelineStatus                      # Trạng thái
    confidence: float = 0.0                     # Độ tin cậy (0.0 → 1.0)
    execution_time: float = 0.0                 # Thời gian chạy (giây)
    
    # --- Thông tin hiệu đề ---
    chu_han: str = ""                           # Chữ Hán gốc (ví dụ: 大明宣德年製)
    trieu_dai: str = ""                         # Triều đại (Minh, Thanh, Nguyễn)
    nien_hieu: str = ""                         # Niên hiệu (Tuyên Đức, Khang Hy, ...)
    hoang_de: str = ""                          # Hoàng đế
    nam_bat_dau: Optional[int] = None           # Năm bắt đầu
    nam_ket_thuc: Optional[int] = None          # Năm kết thúc
    phien_am: str = ""                          # Phiên âm Hán-Việt
    y_nghia: str = ""                           # Ý nghĩa / mô tả
    
    # --- Metadata ---
    raw_ocr_text: str = ""                      # Text OCR thô (nếu có)
    llm_explanation: str = ""                    # Giải thích từ LLM
    search_sources: List[str] = field(default_factory=list)  # URL nguồn tham khảo
    extra_data: Dict[str, Any] = field(default_factory=dict) # Dữ liệu bổ sung
    error_message: str = ""                     # Thông báo lỗi (nếu có)

    def to_dict(self) -> Dict[str, Any]:
        """Chuyển kết quả thành dictionary để trả về API."""
        return {
            "pipeline_name": self.pipeline_name,
            "status": self.status.value,
            "confidence": round(self.confidence, 4),
            "execution_time": round(self.execution_time, 3),
            "chu_han": self.chu_han,
            "trieu_dai": self.trieu_dai,
            "nien_hieu": self.nien_hieu,
            "hoang_de": self.hoang_de,
            "nam_bat_dau": self.nam_bat_dau,
            "nam_ket_thuc": self.nam_ket_thuc,
            "phien_am": self.phien_am,
            "y_nghia": self.y_nghia,
            "raw_ocr_text": self.raw_ocr_text,
            "llm_explanation": self.llm_explanation,
            "search_sources": self.search_sources,
            "extra_data": self.extra_data,
            "error_message": self.error_message,
        }

    @property
    def is_valid(self) -> bool:
        """Kiểm tra kết quả có hợp lệ để tham gia voting không."""
        return (
            self.status in (PipelineStatus.SUCCESS, PipelineStatus.PARTIAL)
            and self.confidence > 0.0
            and bool(self.chu_han or self.trieu_dai or self.nien_hieu)
        )


class BasePipeline(ABC):
    """
    Abstract Base Class cho tất cả pipeline.
    
    Mỗi pipeline con phải implement:
        - `name` (property): tên pipeline
        - `_run(image_bytes, **kwargs)`: logic xử lý chính
    
    Lớp base tự động đo thời gian, bắt lỗi, và wrap kết quả.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Tên định danh của pipeline (dùng cho logging và voting)."""
        ...

    @abstractmethod
    async def _run(self, image_bytes: bytes, **kwargs) -> PipelineResult:
        """
        Logic xử lý chính của pipeline. Được implement bởi từng pipeline con.
        
        Args:
            image_bytes: Ảnh đầu vào dưới dạng bytes
            **kwargs: Tham số bổ sung (ocr_text sẵn có, database, etc.)
            
        Returns:
            PipelineResult chứa kết quả phân tích
        """
        ...

    async def execute(self, image_bytes: bytes, **kwargs) -> PipelineResult:
        """
        Entry point chính — gọi _run() với error handling và đo thời gian.
        
        Không cần override method này. Override _run() thay vì execute().
        """
        start_time = time.time()
        try:
            print(f"\n{'='*60}")
            print(f"[{self.name}] ▶ Bắt đầu xử lý...")
            
            result = await self._run(image_bytes, **kwargs)
            result.execution_time = time.time() - start_time
            
            print(f"[{self.name}] ✅ Hoàn thành ({result.execution_time:.2f}s)")
            print(f"  Status: {result.status.value}")
            print(f"  Confidence: {result.confidence:.2%}")
            if result.chu_han:
                print(f"  Chữ Hán: {result.chu_han}")
            if result.trieu_dai:
                print(f"  Triều đại: {result.trieu_dai}")
            print(f"{'='*60}")
            
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"[{self.name}] ❌ Lỗi sau {elapsed:.2f}s: {error_msg}")
            traceback.print_exc()
            
            return PipelineResult(
                pipeline_name=self.name,
                status=PipelineStatus.FAILED,
                confidence=0.0,
                execution_time=elapsed,
                error_message=error_msg,
            )
