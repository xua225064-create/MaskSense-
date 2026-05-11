"""
Pipeline 2: OCR → LLM Extract Keywords → Google Search (N bài) → LLM Synthesize

Luồng xử lý:
1. PaddleOCR nhận dạng chữ Hán
2. LLM tạo keyword tìm kiếm từ OCR text
3. Google Search (API hoặc Selenium) tìm N bài viết
4. Web Scraper đọc nội dung N bài
5. LLM tổng hợp thông tin từ N bài → kết quả cuối
"""
import json
from typing import Any, Dict, List, Optional

from pipelines.base import BasePipeline, PipelineResult, PipelineStatus
from services.llm_service import (
    call_llm,
    parse_llm_json,
    PROMPT_EXTRACT_INFO,
    PROMPT_SYNTHESIZE_SEARCH,
)
from services.google_search import search_google
from services.web_scraper import scrape_multiple_urls


# Prompt riêng để LLM tạo search keyword
PROMPT_GENERATE_KEYWORDS = """Từ text chữ Hán dưới đây (được OCR từ đáy gốm sứ), 
hãy tạo 2-3 câu tìm kiếm Google để tra cứu thông tin về hiệu đề này.

**Chữ Hán OCR:** "{ocr_text}"

Trả về JSON:
```json
{{
    "keywords": [
        "câu tìm kiếm 1 (tiếng Việt hoặc tiếng Anh)",
        "câu tìm kiếm 2",
        "câu tìm kiếm 3"
    ],
    "chu_han_clean": "chữ Hán đã sửa lỗi OCR nếu có"
}}
```

Gợi ý keyword hiệu quả:
- "{ocr_text} ceramic reign mark"
- "{ocr_text} gốm sứ hiệu đề"  
- "{ocr_text} porcelain mark meaning"
Trả về JSON hợp lệ, không markdown.
"""


class PipelineOcrSearch(BasePipeline):
    """
    Pipeline 2: OCR → Google Search → LLM Synthesize
    
    Kết hợp OCR text với thông tin từ web để có kết quả đầy đủ hơn.
    Đặc biệt mạnh khi database nội bộ không có hiệu đề cần tìm.
    """

    @property
    def name(self) -> str:
        return "ocr_search"

    async def _run(self, image_bytes: bytes, **kwargs) -> PipelineResult:
        """
        Args:
            image_bytes: Ảnh gốc
            **kwargs:
                ocr_text (str): Text OCR đã đọc sẵn
                search_method (str): "api", "selenium", hoặc None (auto)
        """
        ocr_text = kwargs.get("ocr_text", "")
        search_method = kwargs.get("search_method", None)

        # =============================================
        # Bước 1: Lấy OCR text (nếu chưa có)
        # =============================================
        if not ocr_text:
            print(f"[{self.name}] 📷 Bước 1: Chạy OCR...")
            ocr_text, _ = await self._run_ocr(image_bytes)
        
        if not ocr_text:
            return PipelineResult(
                pipeline_name=self.name,
                status=PipelineStatus.FAILED,
                error_message="OCR không đọc được chữ → không thể tìm kiếm",
            )
        
        print(f"[{self.name}] 📝 OCR text: '{ocr_text}'")

        # =============================================
        # Bước 2: LLM tạo search keywords
        # =============================================
        print(f"[{self.name}] 🔑 Bước 2: Tạo search keywords...")
        
        keywords = await self._generate_search_keywords(ocr_text)
        if not keywords:
            # Fallback: dùng OCR text trực tiếp
            keywords = [
                f"{ocr_text} ceramic reign mark",
                f"{ocr_text} gốm sứ hiệu đề",
            ]
        
        print(f"[{self.name}] 🔑 Keywords: {keywords}")

        # =============================================
        # Bước 3: Google Search
        # =============================================
        print(f"[{self.name}] 🌐 Bước 3: Google Search...")
        
        all_search_results = []
        for keyword in keywords[:3]:
            results = await search_google(keyword, num_results=3, prefer_method=search_method)
            all_search_results.extend(results)
        
        if not all_search_results:
            return PipelineResult(
                pipeline_name=self.name,
                status=PipelineStatus.PARTIAL,
                confidence=0.2,
                raw_ocr_text=ocr_text,
                chu_han=ocr_text,
                error_message="Google Search không trả về kết quả",
            )
        
        # Loại bỏ URL trùng
        seen_urls = set()
        unique_results = []
        for r in all_search_results:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                unique_results.append(r)
        
        print(f"[{self.name}] 🌐 Tìm được {len(unique_results)} kết quả unique")

        # =============================================
        # Bước 4: Scrape nội dung bài viết
        # =============================================
        print(f"[{self.name}] 📖 Bước 4: Đọc nội dung bài viết...")
        
        urls = [r.url for r in unique_results[:5]]
        articles = await scrape_multiple_urls(urls, max_concurrent=3)
        
        if not articles:
            # Vẫn dùng snippet từ Google nếu scrape thất bại
            articles_text = "\n\n".join(
                f"### {r.title}\n{r.snippet}" for r in unique_results[:5]
            )
        else:
            articles_text = "\n\n".join(
                f"### {a.title}\n**URL:** {a.url}\n{a.content}" for a in articles
            )

        # =============================================
        # Bước 5: LLM tổng hợp thông tin
        # =============================================
        print(f"[{self.name}] 🤖 Bước 5: LLM tổng hợp thông tin...")
        
        synthesize_prompt = PROMPT_SYNTHESIZE_SEARCH.format(
            ocr_text=ocr_text,
            articles=articles_text,
        )
        
        synth_response = await call_llm(synthesize_prompt)
        
        if not synth_response:
            return PipelineResult(
                pipeline_name=self.name,
                status=PipelineStatus.PARTIAL,
                confidence=0.3,
                raw_ocr_text=ocr_text,
                chu_han=ocr_text,
                search_sources=[r.url for r in unique_results[:5]],
                error_message="LLM Synthesize không phản hồi",
            )
        
        synthesized = parse_llm_json(synth_response)
        if not synthesized:
            return PipelineResult(
                pipeline_name=self.name,
                status=PipelineStatus.PARTIAL,
                confidence=0.3,
                raw_ocr_text=ocr_text,
                chu_han=ocr_text,
                search_sources=[r.url for r in unique_results[:5]],
                llm_explanation=synth_response[:500],
                error_message="Không parse được JSON từ LLM Synthesize",
            )

        # =============================================
        # Build kết quả
        # =============================================
        confidence = float(synthesized.get("do_tin_cay", 0.5))
        sources = synthesized.get("nguon_tham_khao", []) or [r.url for r in unique_results[:5]]
        
        return PipelineResult(
            pipeline_name=self.name,
            status=PipelineStatus.SUCCESS,
            confidence=confidence,
            chu_han=synthesized.get("chu_han", ocr_text),
            trieu_dai=synthesized.get("trieu_dai", ""),
            nien_hieu=synthesized.get("nien_hieu", ""),
            hoang_de=synthesized.get("hoang_de", ""),
            nam_bat_dau=self._safe_int(synthesized.get("nam_bat_dau")),
            nam_ket_thuc=self._safe_int(synthesized.get("nam_ket_thuc")),
            phien_am=synthesized.get("phien_am", ""),
            y_nghia=synthesized.get("y_nghia", ""),
            raw_ocr_text=ocr_text,
            search_sources=sources,
            llm_explanation=synthesized.get("ghi_chu", ""),
            extra_data={
                "num_articles_scraped": len(articles) if articles else 0,
                "keywords_used": keywords,
            },
        )

    async def _generate_search_keywords(self, ocr_text: str) -> List[str]:
        """Dùng LLM tạo keyword tìm kiếm từ OCR text."""
        prompt = PROMPT_GENERATE_KEYWORDS.format(ocr_text=ocr_text)
        response = await call_llm(prompt, temperature=0.2)
        
        if not response:
            return []
        
        parsed = parse_llm_json(response)
        if parsed and "keywords" in parsed:
            return parsed["keywords"]
        return []

    async def _run_ocr(self, image_bytes: bytes) -> tuple:
        """Chạy OCR (reuse từ Pipeline 1)."""
        import asyncio
        
        def _ocr_sync():
            from ocr_engine import read_chinese_mark
            result = read_chinese_mark(image_bytes, deep_mode=False)
            if result.get("error"):
                return "", []
            primary = result.get("primary_text", "")
            candidates = result.get("candidates", [])
            if not primary and "all_texts" in result:
                texts = result["all_texts"]
                if texts:
                    primary = texts[0] if isinstance(texts[0], str) else str(texts[0])
                    candidates = texts[1:] if len(texts) > 1 else []
            return primary, candidates
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _ocr_sync)

    @staticmethod
    def _safe_int(value) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
