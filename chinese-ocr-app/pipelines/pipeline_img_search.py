"""
Pipeline 3: Image → Google Image Search (Selenium) → LLM Synthesize

Luồng xử lý:
1. Tiền xử lý ảnh
2. Google Image Search / Google Lens (Selenium) — tìm bằng hình ảnh
3. Thu thập N bài viết liên quan
4. Scrape nội dung bài viết
5. LLM tổng hợp thông tin → kết quả cuối

Pipeline này KHÔNG dùng OCR — tìm kiếm trực tiếp bằng hình ảnh.
Rất hữu ích khi ảnh bị mờ, chữ bị phai mà OCR không đọc được.
"""
import os
import uuid
import asyncio
import tempfile
from typing import Any, Dict, List, Optional

from pipelines.base import BasePipeline, PipelineResult, PipelineStatus
from services.llm_service import call_llm, parse_llm_json, PROMPT_SYNTHESIZE_SEARCH
from services.google_search import search_google_image, search_google
from services.web_scraper import scrape_multiple_urls


class PipelineImgSearch(BasePipeline):
    """
    Pipeline 3: Google Image Search → LLM Synthesize
    
    Tìm kiếm bằng hình ảnh trực tiếp, không phụ thuộc OCR.
    """

    @property
    def name(self) -> str:
        return "img_search"

    async def _run(self, image_bytes: bytes, **kwargs) -> PipelineResult:
        """
        Args:
            image_bytes: Ảnh gốc
            **kwargs:
                fallback_ocr_text (str): Text OCR làm fallback keyword (nếu image search thất bại)
        """
        fallback_ocr_text = kwargs.get("fallback_ocr_text", "")

        # =============================================
        # Bước 1: Lưu ảnh tạm để upload
        # =============================================
        temp_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
        os.makedirs(temp_dir, exist_ok=True)
        temp_filename = f"search_{uuid.uuid4().hex[:8]}.jpg"
        temp_path = os.path.join(temp_dir, temp_filename)
        
        with open(temp_path, "wb") as f:
            f.write(image_bytes)
        
        print(f"[{self.name}] 📷 Ảnh tạm: {temp_path}")

        try:
            # =============================================
            # Bước 2: Google Image Search
            # =============================================
            print(f"[{self.name}] 🖼️ Bước 2: Google Image Search...")
            
            search_results = await search_google_image(temp_path, num_results=5)
            
            # Nếu image search thất bại, thử text search với OCR text
            if not search_results and fallback_ocr_text:
                print(f"[{self.name}] ⚠ Image search thất bại, thử text search...")
                search_results = await search_google(
                    f"{fallback_ocr_text} ceramic mark gốm sứ hiệu đề",
                    num_results=5,
                )
            
            if not search_results:
                return PipelineResult(
                    pipeline_name=self.name,
                    status=PipelineStatus.FAILED,
                    error_message="Google Image Search không tìm thấy kết quả",
                )
            
            print(f"[{self.name}] 🖼️ Tìm được {len(search_results)} kết quả")

            # =============================================
            # Bước 3: Scrape nội dung bài viết
            # =============================================
            print(f"[{self.name}] 📖 Bước 3: Đọc nội dung bài viết...")
            
            urls = [r.url for r in search_results[:5]]
            articles = await scrape_multiple_urls(urls, max_concurrent=3)
            
            if not articles:
                articles_text = "\n\n".join(
                    f"### {r.title}\n{r.snippet}" for r in search_results[:5]
                )
            else:
                articles_text = "\n\n".join(
                    f"### {a.title}\n**URL:** {a.url}\n{a.content}" for a in articles
                )

            # =============================================
            # Bước 4: LLM tổng hợp
            # =============================================
            print(f"[{self.name}] 🤖 Bước 4: LLM tổng hợp thông tin...")
            
            synth_prompt = PROMPT_SYNTHESIZE_SEARCH.format(
                ocr_text=fallback_ocr_text or "(không có OCR text — tìm bằng hình ảnh)",
                articles=articles_text,
            )
            
            synth_response = await call_llm(synth_prompt)
            
            if not synth_response:
                return PipelineResult(
                    pipeline_name=self.name,
                    status=PipelineStatus.PARTIAL,
                    confidence=0.2,
                    search_sources=[r.url for r in search_results[:5]],
                    error_message="LLM Synthesize không phản hồi",
                )
            
            synthesized = parse_llm_json(synth_response)
            if not synthesized:
                return PipelineResult(
                    pipeline_name=self.name,
                    status=PipelineStatus.PARTIAL,
                    confidence=0.2,
                    search_sources=[r.url for r in search_results[:5]],
                    llm_explanation=synth_response[:500],
                    error_message="Không parse được JSON từ LLM",
                )

            # =============================================
            # Build kết quả
            # =============================================
            confidence = float(synthesized.get("do_tin_cay", 0.4))
            sources = synthesized.get("nguon_tham_khao", []) or [r.url for r in search_results[:5]]
            
            return PipelineResult(
                pipeline_name=self.name,
                status=PipelineStatus.SUCCESS,
                confidence=confidence,
                chu_han=synthesized.get("chu_han", ""),
                trieu_dai=synthesized.get("trieu_dai", ""),
                nien_hieu=synthesized.get("nien_hieu", ""),
                hoang_de=synthesized.get("hoang_de", ""),
                nam_bat_dau=self._safe_int(synthesized.get("nam_bat_dau")),
                nam_ket_thuc=self._safe_int(synthesized.get("nam_ket_thuc")),
                phien_am=synthesized.get("phien_am", ""),
                y_nghia=synthesized.get("y_nghia", ""),
                search_sources=sources,
                llm_explanation=synthesized.get("ghi_chu", ""),
                extra_data={
                    "search_type": "image",
                    "num_articles_scraped": len(articles) if articles else 0,
                },
            )
        
        finally:
            # Dọn file tạm
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass

    @staticmethod
    def _safe_int(value) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
