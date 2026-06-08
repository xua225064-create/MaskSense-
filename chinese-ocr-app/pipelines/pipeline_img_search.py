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
import unicodedata
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from pipelines.base import BasePipeline, PipelineResult, PipelineStatus
from services.google_search import search_google_image, search_google
from config import GOOGLE_CSE_API_KEY, GOOGLE_CSE_CX

PREFERRED_SOURCE_DOMAINS = (
    "heritagevietnamairlines.com",
    "huengaynay.vn",
    "dsvh.gov.vn",
    "gotheborg.com",
    "nghethuatxua.com",
    "carnetdephilippe.canalblog.com",
    "alaintruong.com",
    "asium-art.com",
    "millon.com",
    "adams.ie",
    "gazette-drouot.com",
)
LOW_TRUST_SOURCE_DOMAINS = (
    "facebook.", "instagram.", "pinterest.", "tiktok.", "youtube.", "youtu.be",
    "reddit.", "lemon8.", "lemon8-app.",
)


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
        database = kwargs.get("database") or []
        fallback_terms = self._build_fallback_terms(fallback_ocr_text, database)
        fallback_label = fallback_terms[0] if fallback_terms else fallback_ocr_text

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
            
            search_type = "image"
            fallback_queries: List[str] = []
            try:
                search_results = await asyncio.wait_for(
                    search_google_image(temp_path, num_results=5, force_selenium=True),
                    timeout=60,
                )
            except asyncio.TimeoutError:
                print(f"[{self.name}] ⚠ Google Image Search timeout, chuyển sang text search từ OCR")
                search_results = []
            
            # Nếu image search thất bại, thử text search với OCR text
            if not search_results and fallback_terms:
                print(f"[{self.name}] ⚠ Image search thất bại, thử text search...")
                fallback_queries = self._build_fallback_queries(fallback_terms)
                search_results = await self._fallback_text_search(fallback_queries, limit=5)
                search_type = "text_fallback"
            elif search_results and fallback_label:
                search_results = self._filter_sources_by_ocr_context(
                    search_results,
                    fallback_label,
                    limit=5,
                )
            
            if not search_results:
                return PipelineResult(
                    pipeline_name=self.name,
                    status=PipelineStatus.FAILED,
                    error_message="Google Image/Text Search không tìm thấy link nguồn phù hợp",
                )
            
            print(f"[{self.name}] 🖼️ Tìm được {len(search_results)} kết quả")

            # =============================================
            # Bước 3: Trả link nguồn nhanh
            # =============================================
            print(f"[{self.name}] 📖 Bước 3: Chuẩn hóa link nguồn...")
            articles = []
            web_sources = self._build_web_sources(search_results[:5], articles, search_type=search_type)
            source_urls = self._source_urls(search_results[:5])

            # Keep source discovery fast. The evidence layer evaluates these
            # links together with OCR/DB/ML candidates for final voting.
            return PipelineResult(
                pipeline_name=self.name,
                status=PipelineStatus.PARTIAL,
                confidence=0.45,
                chu_han=fallback_label or "",
                search_sources=source_urls,
                llm_explanation="Đã tìm được link nguồn; kiểm chứng chi tiết ở evidence/voting.",
                extra_data={
                    "search_type": search_type,
                    "num_articles_scraped": len(articles) if articles else 0,
                    "web_sources": web_sources,
                    "fallback_queries": fallback_queries,
                },
            )
        
        finally:
            # Dọn file tạm
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass

    async def _fallback_text_search(self, queries: List[str], limit: int = 5):
        results = []
        seen_urls = set()
        if not queries:
            return results

        # Slide flow C must use Selenium as the primary search path, not CSE/API.
        prefer_method = "selenium_only"
        for query in queries[:6]:
            try:
                batch = await search_google(query, num_results=limit, prefer_method=prefer_method)
            except Exception as exc:
                print(f"[{self.name}] Text search lỗi với query '{query}': {exc}")
                batch = []
            for item in batch or []:
                url = getattr(item, "url", "")
                if url and url not in seen_urls:
                    results.append(item)
                    seen_urls.add(url)
            if len(results) >= limit * 3:
                break

        return self._rank_search_results(results)[:limit]

    @staticmethod
    def _rank_search_results(search_results):
        def score(result) -> float:
            domain = urlparse(getattr(result, "url", "") or "").netloc.lower()
            value = 0.0
            if any(token in domain for token in LOW_TRUST_SOURCE_DOMAINS):
                value -= 20.0
            if any(domain == preferred or domain.endswith(f".{preferred}") for preferred in PREFERRED_SOURCE_DOMAINS):
                value += 20.0
            if any(token in domain for token in ("museum", "gov", "edu", "auction", "porcelain", "ceramic")):
                value += 6.0
            text = " ".join([
                getattr(result, "title", "") or "",
                getattr(result, "snippet", "") or "",
                getattr(result, "url", "") or "",
            ])
            folded = PipelineImgSearch._fold_latin(text).lower()
            if "noi phu thi" in folded or "nội phủ thị" in text.lower():
                value += 8.0
            if "bleu de hue" in folded or "do su ky kieu" in folded:
                value += 5.0
            return value

        return sorted(search_results or [], key=score, reverse=True)

    @staticmethod
    def _filter_sources_by_ocr_context(search_results, fallback_ocr_text: str, limit: int = 5):
        expected = PipelineImgSearch._expected_source_terms(fallback_ocr_text)
        if not expected:
            return search_results[:limit]

        expected_terms = expected["terms"]
        conflict_terms = expected["conflicts"]
        scored = []
        dropped = []

        for result in search_results or []:
            haystack = " ".join([
                getattr(result, "title", "") or "",
                getattr(result, "snippet", "") or "",
                getattr(result, "url", "") or "",
            ]).lower()
            cjk = PipelineImgSearch._normalize_cjk(haystack)
            score = 0
            for term in expected_terms:
                term_lower = term.lower()
                term_cjk = PipelineImgSearch._normalize_cjk(term)
                if term_lower in haystack or (term_cjk and term_cjk in cjk):
                    score += 4
            conflict = False
            for term in conflict_terms:
                term_cjk = PipelineImgSearch._normalize_cjk(term)
                if term.lower() in haystack or (term_cjk and term_cjk in cjk):
                    conflict = True
                    break
            if conflict:
                score -= 10
            if score < 0:
                dropped.append(result)
                continue
            scored.append((score, result))

        scored.sort(key=lambda item: item[0], reverse=True)
        filtered = [result for _, result in scored]
        if len(filtered) < 2:
            # Keep Lens matches if filtering is too strict, but put non-conflicting
            # candidates before dropped ones.
            filtered.extend(r for r in (search_results or []) if r not in filtered and r not in dropped)
        return filtered[:limit]

    @staticmethod
    def _expected_source_terms(fallback_ocr_text: str) -> Dict[str, List[str]]:
        compact = "".join((fallback_ocr_text or "").split())
        if "光緒" in compact or "光绪" in compact:
            return {
                "terms": ["光緒", "光绪", "大清光緒", "guangxu", "kuang-hsu", "kuang hsu", "quang tự", "quang tu"],
                "conflicts": [
                    "同治", "tongzhi", "道光", "daoguang", "康熙", "kangxi",
                    "乾隆", "qianlong", "宣德", "xuande", "內府", "内府",
                    "nội phủ", "noi phu", "noi-phu", "noi_phu",
                ],
            }
        if "同治" in compact:
            return {
                "terms": ["同治", "tongzhi"],
                "conflicts": ["光緒", "光绪", "guangxu", "kuang-hsu", "道光", "daoguang"],
            }
        return {}

    @staticmethod
    def _normalize_cjk(value: str) -> str:
        trans = str.maketrans({"绪": "緒", "制": "製", "内": "內"})
        return "".join(ch for ch in (value or "") if "\u4e00" <= ch <= "\u9fff").translate(trans)

    @staticmethod
    def _fold_latin(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", value or "")
        return "".join(ch for ch in normalized if not unicodedata.combining(ch))

    @staticmethod
    def _build_fallback_terms(
        fallback_ocr_text: str,
        database: List[Dict[str, Any]],
    ) -> List[str]:
        terms: List[str] = []

        def add(value: Any) -> None:
            value = str(value or "").strip()
            if value and value not in terms:
                terms.append(value)

        match = PipelineImgSearch._find_database_fallback(fallback_ocr_text, database)
        if match:
            for field in (
                "chu_han",
                "chu_han_6",
                "chu_han_4",
                "phien_am",
                "hien_thi_chinh",
                "hieu_de_vi",
                "hieu_de_en",
                "ten_viet",
                "nien_hieu",
            ):
                value = match.get(field)
                add(value)
                folded = PipelineImgSearch._fold_latin(str(value or "")).strip()
                if folded != str(value or "").strip():
                    add(folded)
        add(fallback_ocr_text)
        return terms[:10]

    @staticmethod
    def _find_database_fallback(
        ocr_text: str,
        database: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if not ocr_text or not database:
            return None
        try:
            import sys
            sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
            from main import _find_match, find_best_matches

            match, _ = _find_match(ocr_text, database)
            if match:
                return match
            top = find_best_matches(ocr_text, database, top_n=1)
            if top and float(top[0].get("raw_score") or 0.0) > 0.45:
                return top[0]
        except Exception as exc:
            print(f"[img_search] Database fallback lookup failed: {exc}")
        return None

    @staticmethod
    def _build_fallback_queries(fallback_terms: List[str]) -> List[str]:
        terms = [str(term or "").strip() for term in fallback_terms or [] if str(term or "").strip()]
        compact = "".join((terms[0] if terms else "").split())
        if not compact:
            return []

        neifu_queries: List[str] = []
        if PipelineImgSearch._normalize_cjk(compact).startswith("內府侍"):
            display = ""
            display_ascii = ""
            for term in terms:
                folded = PipelineImgSearch._fold_latin(term).strip()
                if "noi phu thi" in folded.lower():
                    display = term
                    display_ascii = folded
                    break
            neifu_queries.extend([
                f'"{compact}" porcelain mark',
                f'"{compact}" "Bleu de Hue"',
                f'"{display}"',
                f'"{display}" "Bleu de Hue"',
                f'"{display}" "đồ sứ ký kiểu"',
                f'"{display_ascii}" "Bleu de Hue"',
                f'"{display_ascii}" porcelain mark',
                f"{display} sen cua",
                f"{display_ascii} lotus crab",
            ])

        queries = [
            f"{compact} porcelain mark",
            f"{compact} ceramic mark",
            f'"{compact}" porcelain mark',
            f'"{compact}" ceramic mark',
            f"{compact} reign mark porcelain",
            f"{compact} gốm sứ hiệu đề",
        ]
        if "光緒" in compact or "光绪" in compact:
            queries.extend([
                '"大清光緒年製" porcelain mark',
                "Da Qing Guangxu Nian Zhi porcelain mark",
                '"Da Qing Guangxu Nian Zhi" porcelain mark',
                "Guangxu porcelain mark Da Qing",
                '"Guangxu" porcelain mark "Da Qing"',
                "Đại Thanh Quang Tự niên chế gốm sứ",
            ])
        elif "大清" in compact:
            queries.extend([
                f'"{compact}" Qing porcelain mark',
                f"{compact} Qing dynasty reign mark",
            ])
        if "大明" in compact:
            queries.extend([
                f'"{compact}" Ming porcelain mark',
                f"{compact} Ming dynasty reign mark",
            ])

        for term in terms[1:6]:
            clean = " ".join(term.split())
            if not clean:
                continue
            queries.extend([
                f"{clean} porcelain mark",
                f"{clean} ceramic mark",
                f'"{clean}" porcelain mark',
            ])

        deduped = []
        seen = set()
        for query in neifu_queries + queries:
            if query and '""' not in query and query not in seen:
                deduped.append(query)
                seen.add(query)
        return deduped

    @staticmethod
    def _safe_int(value) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _source_urls(search_results, extra_sources=None) -> List[str]:
        urls: List[str] = []

        def add(value: Any) -> None:
            if isinstance(value, dict):
                value = value.get("url") or value.get("source_url") or ""
            value = str(value or "").strip()
            if value.startswith("http") and value not in urls:
                urls.append(value)

        for result in search_results or []:
            add(getattr(result, "url", ""))
        for source in extra_sources or []:
            add(source)
        return urls

    @staticmethod
    def _build_web_sources(search_results, articles, search_type: str = "image") -> List[Dict[str, str]]:
        article_by_url = {a.url: a for a in articles or []}
        payload = []
        for result in search_results or []:
            article = article_by_url.get(result.url)
            payload.append({
                "title": result.title,
                "url": result.url,
                "snippet": result.snippet,
                "content": (article.content[:1800] if article else ""),
                "source_pipeline": "img_search",
                "search_type": search_type,
            })
        return payload
