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
hãy tạo 3-5 câu tìm kiếm Google để tra cứu thông tin về hiệu đề này.

**Chữ Hán OCR:** "{ocr_text}"

QUAN TRỌNG — Character disambiguation context:
OCR trên gốm sứ thường đọc nhầm các ký tự sau:
  杜 ↔ 右, 社 ↔ 礼, 侍 ↔ 待, 石 ↔ 北, 内 ↔ 肉, 府 ↔ 付
  
Nếu text chứa 内府 / 內府:
  → Đây là hiệu đề xưởng gốm Nội Phủ (Imperial Household Bureau), triều Nguyễn Việt Nam
  → Tạo keyword cả dạng gốc VÀ các biến thể sửa lỗi OCR

Trả về JSON:
```json
{{
    "keywords": [
        "câu tìm kiếm 1 (chữ Hán + tiếng Anh)",
        "câu tìm kiếm 2 (phiên âm Hán-Việt)",
        "câu tìm kiếm 3 (tiếng Việt)",
        "câu tìm kiếm 4 (biến thể OCR nếu có)",
        "câu tìm kiếm 5 (ngữ cảnh triều đại)"
    ],
    "chu_han_clean": "chữ Hán đã sửa lỗi OCR nếu có",
    "ocr_corrections": ["ký tự gốc → ký tự sửa", "..."]
}}
```

Ví dụ với "內府侍東":
  → "內府侍東 ceramic mark Vietnamese"
  → "Nội Phủ Thị Đông hiệu đề gốm sứ"
  → "內府侍東 gốm sứ triều Nguyễn"
  → "内府 Nguyen dynasty ceramic workshop mark"
  → "Vietnamese imperial kiln marks 内府"

Ví dụ với "大清康熙年製":
  → "大清康熙年製 ceramic reign mark"
  → "Kangxi period porcelain mark"
  → "Đại Thanh Khang Hy niên chế gốm sứ"

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
        database = kwargs.get("database") or []

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

        db_match, match_type = self._match_database(ocr_text, database)
        if db_match:
            print(f"[{self.name}] Database short-circuit: {db_match.get('ten_viet', '')} ({match_type})")
            return self._build_result_from_db(db_match, match_type, ocr_text)

        # =============================================
        # Bước 2: LLM tạo search keywords
        # =============================================
        print(f"[{self.name}] 🔑 Bước 2: Tạo search keywords...")
        
        keywords = await self._generate_search_keywords(ocr_text)
        if not keywords:
            # Fallback: dùng OCR text trực tiếp với nhiều biến thể
            keywords = [
                f"{ocr_text} ceramic reign mark",
                f"{ocr_text} gốm sứ hiệu đề",
                f"{ocr_text} porcelain mark meaning",
            ]
            # Special 内府 workshop mark queries
            has_neifu = any(ch in ocr_text for ch in ("内", "內")) and "府" in ocr_text
            if has_neifu:
                keywords.extend([
                    "Nội Phủ hiệu đề gốm sứ triều Nguyễn",
                    f"{ocr_text} Nguyen dynasty ceramic workshop mark",
                ])
        
        print(f"[{self.name}] 🔑 Keywords: {keywords}")

        # =============================================
        # Bước 3: Google Search
        # =============================================
        print(f"[{self.name}] 🌐 Bước 3: Google Search...")
        
        all_search_results = []
        for keyword in keywords[:5]:  # Tăng lên 5 keywords cho coverage tốt hơn
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
        web_sources = self._build_web_sources(unique_results[:5], articles)

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
                extra_data={"web_sources": web_sources, "keywords_used": keywords},
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
                extra_data={"web_sources": web_sources, "keywords_used": keywords},
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
                "web_sources": web_sources,
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
            result = read_chinese_mark(image_bytes, deep_mode=True)
            if result.get("error"):
                return "", []
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

            if len(query) >= 3 and query not in generic_partials:
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
    ) -> PipelineResult:
        confidence_map = {
            "exact": 0.90,
            "partial": 0.72,
        }
        return PipelineResult(
            pipeline_name=self.name,
            status=PipelineStatus.SUCCESS,
            confidence=confidence_map.get(match_type, 0.65),
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
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _build_web_sources(search_results, articles) -> List[Dict[str, str]]:
        article_by_url = {a.url: a for a in articles or []}
        payload = []
        for result in search_results or []:
            article = article_by_url.get(result.url)
            payload.append({
                "title": result.title,
                "url": result.url,
                "snippet": result.snippet,
                "content": (article.content[:1800] if article else ""),
                "source_pipeline": "ocr_search",
            })
        return payload
