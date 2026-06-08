"""
Evidence service for reign-mark verification.

DB/ML/OCR only propose candidates here. The final confidence is raised only
when external web sources support the same candidate.
"""
import difflib
import json
import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote, unquote, urlparse

from config import SEARCH_N_RESULTS
from services.google_search import SearchResult, search_google
from services.llm_service import call_llm, parse_llm_json
from services.web_scraper import ArticleContent


GENERIC_MARKS = {"大清", "大明", "大南", "年製", "年制", "年造"}
MIN_EVIDENCE_CONFIDENCE = 0.62
MAX_CANDIDATES_FOR_WEB = 5
MAX_QUERIES_PER_CANDIDATE = 8
MAX_RESULTS_PER_QUERY = 5
MAX_ARTICLES_PER_CANDIDATE = 8
NEIFU_IMAGE_ONLY_CONFIDENCE_CAP = 0.44
CJK_SOURCE_STOPWORDS = {"大", "清", "明", "南", "年", "製", "制", "造", "瓷", "陶"}
SOCIAL_SOURCE_DOMAINS = (
    "facebook.", "instagram.", "pinterest.", "tiktok.", "youtube.", "youtu.be", "reddit.",
    "lemon8.", "lemon8-app.",
)
LOW_TRUST_EVIDENCE_DOMAINS = (
    "facebook.", "instagram.", "tiktok.", "youtube.", "youtu.be",
    "lemon8.", "lemon8-app.",
)
HIGH_TRUST_SOURCE_DOMAINS = (
    "heritagevietnamairlines.com",
    "huengaynay.vn",
    "dsvh.gov.vn",
)
SPECIALIST_SOURCE_DOMAINS = (
    "gotheborg.com",
    "nghethuatxua.com",
    "carnetdephilippe.canalblog.com",
    "alaintruong.com",
    "asium-art.com",
    "millon.com",
    "adams.ie",
    "gazette-drouot.com",
    "cannes-encheres.com",
    "aaoarts.com",
)
IRRELEVANT_SOURCE_KEYWORDS = (
    "laughing buddha",
    "cotton flower",
    "100 smiles art",
    "rose porcelain figurines",
)

_CJK_TRANS = str.maketrans({
    "绪": "緒",
    "统": "統",
    "历": "曆",
    "万": "萬",
    "制": "製",
    "内": "內",
})


def normalize_cjk(value: Optional[str]) -> str:
    if not value:
        return ""
    return "".join(ch for ch in value if "\u4e00" <= ch <= "\u9fff").translate(_CJK_TRANS)


def _fold_latin(value: Optional[str]) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", str(value))
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def _safe_list(value: Any) -> List[Any]:
    if not value:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else [value]
        except Exception:
            return [value]
    return []


def _entry_targets(entry: Dict[str, Any]) -> List[str]:
    targets = [
        entry.get("chu_han", ""),
        entry.get("chu_han_4", ""),
        entry.get("chu_han_6", ""),
    ]
    targets.extend(str(v) for v in _safe_list(entry.get("bien_the")) if v)
    return [t for t in targets if t]


def _cjk_set_score(a: str, b: str) -> float:
    sa, sb = set(normalize_cjk(a)), set(normalize_cjk(b))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / max(len(sa | sb), 1)


def _rank_database_candidates(
    text: str,
    database: List[Dict[str, Any]],
    limit: int = 5,
) -> List[Tuple[float, Dict[str, Any], str]]:
    query = normalize_cjk(text)
    if not query or not database:
        return []

    ranked: List[Tuple[float, Dict[str, Any], str]] = []
    for entry in database:
        best_score = 0.0
        best_target = ""
        for target in _entry_targets(entry):
            target_norm = normalize_cjk(target)
            if not target_norm:
                continue
            if query == target_norm:
                score = 1.0
            elif query in GENERIC_MARKS or target_norm in GENERIC_MARKS:
                score = 0.0
            elif query in target_norm or target_norm in query:
                score = 0.84 * (min(len(query), len(target_norm)) / max(len(query), len(target_norm)))
            else:
                seq = difflib.SequenceMatcher(None, query, target_norm).ratio()
                overlap = _cjk_set_score(query, target_norm)
                score = (seq * 0.65) + (overlap * 0.35)
            if score > best_score:
                best_score = score
                best_target = target
        if best_score >= 0.42:
            ranked.append((best_score, entry, best_target))

    ranked.sort(key=lambda item: item[0], reverse=True)
    if ranked and ranked[0][0] >= 0.99:
        exact = [item for item in ranked if item[0] >= 0.99]
        return exact[:limit]
    return ranked[:limit]


def build_evidence_candidates(
    ocr_text: str,
    ocr_candidates: Iterable[str],
    pipeline_results: Iterable[Any],
    database: List[Dict[str, Any]],
    max_candidates: int = MAX_CANDIDATES_FOR_WEB,
) -> List[Dict[str, Any]]:
    """Build deduplicated candidates from OCR, ML, LLM, and DB hints."""
    candidates: Dict[str, Dict[str, Any]] = {}

    def add_candidate(
        chu_han: str,
        source: str,
        prior_score: float,
        db_entry: Optional[Dict[str, Any]] = None,
        matched_text: str = "",
        web_sources: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        norm = normalize_cjk(chu_han or matched_text or (db_entry or {}).get("chu_han", ""))
        if not norm:
            return
        entry = db_entry or {}
        canonical_chu_han = entry.get("chu_han") or chu_han or matched_text
        key = normalize_cjk(canonical_chu_han) or norm
        current = candidates.get(key)
        if not current:
            current = {
                "candidate_id": key,
                "chu_han": canonical_chu_han,
                "detected_chu_han": chu_han,
                "matched_text": matched_text,
                "prior_score": max(0.0, min(float(prior_score), 1.0)),
                "source_votes": [],
                "db_entry": entry,
                "pipeline_web_sources": [],
                "chu_han_4": entry.get("chu_han_4", ""),
                "chu_han_6": entry.get("chu_han_6", ""),
                "ten_viet": entry.get("ten_viet", ""),
                "hien_thi_chinh": entry.get("hien_thi_chinh", ""),
                "hieu_de_vi": entry.get("hieu_de_vi", ""),
                "phien_am": entry.get("phien_am", ""),
                "trieu_dai": entry.get("trieu_dai", ""),
                "nien_hieu": entry.get("nien_hieu", ""),
            }
            candidates[key] = current
        current["prior_score"] = max(current["prior_score"], max(0.0, min(float(prior_score), 1.0)))
        if source and source not in current["source_votes"]:
            current["source_votes"].append(source)
        if web_sources:
            seen_urls = {src.get("url") for src in current.get("pipeline_web_sources", []) if src.get("url")}
            for src in web_sources:
                url = src.get("url") if isinstance(src, dict) else ""
                if url and url not in seen_urls:
                    current["pipeline_web_sources"].append(src)
                    seen_urls.add(url)
        if db_entry and not current.get("db_entry"):
            current["db_entry"] = db_entry
            current["chu_han"] = db_entry.get("chu_han") or current.get("chu_han", "")
            current["chu_han_4"] = db_entry.get("chu_han_4", "")
            current["chu_han_6"] = db_entry.get("chu_han_6", "")
            current["ten_viet"] = db_entry.get("ten_viet", "")
            current["hien_thi_chinh"] = db_entry.get("hien_thi_chinh", "")
            current["hieu_de_vi"] = db_entry.get("hieu_de_vi", "")
            current["phien_am"] = db_entry.get("phien_am", "")
            current["trieu_dai"] = db_entry.get("trieu_dai", "")
            current["nien_hieu"] = db_entry.get("nien_hieu", "")

    raw_texts = [ocr_text] + [c for c in (ocr_candidates or []) if c]
    for idx, text in enumerate(raw_texts):
        if not text:
            continue
        add_candidate(text, "ocr" if idx == 0 else "ocr_candidate", 0.55 if idx == 0 else 0.45)
        neifu_layout = _neifu_candidate_from_text(text)
        if neifu_layout:
            add_candidate(
                neifu_layout,
                "ocr_layout_neifu" if idx == 0 else "ocr_candidate_layout_neifu",
                0.78 if idx == 0 else 0.68,
            )
        for score, entry, matched in _rank_database_candidates(text, database, limit=3):
            add_candidate(matched or entry.get("chu_han", ""), "db_hint_from_ocr", score, entry, matched)

    for result in pipeline_results or []:
        if not getattr(result, "is_valid", False):
            continue
        chu_han = getattr(result, "chu_han", "") or getattr(result, "raw_ocr_text", "")
        prior = float(getattr(result, "confidence", 0.0) or 0.0)
        source = getattr(result, "pipeline_name", "pipeline")
        web_sources = _pipeline_web_sources(result)
        add_candidate(chu_han, source, prior, web_sources=web_sources)
        extra = getattr(result, "extra_data", None) or {}
        for item in extra.get("vision_candidates") or []:
            if isinstance(item, dict):
                cand_text = item.get("text", "")
                cand_prior = float(item.get("confidence") or prior or 0.0)
            else:
                cand_text = str(item)
                cand_prior = prior
            add_candidate(
                cand_text,
                f"{source}_candidate",
                max(cand_prior, min(prior, 0.65)),
                web_sources=web_sources,
            )
            for score, entry, matched in _rank_database_candidates(cand_text, database, limit=2):
                add_candidate(
                    matched or entry.get("chu_han", ""),
                    f"db_hint_from_{source}_candidate",
                    max(score, cand_prior, prior),
                    entry,
                    matched,
                    web_sources=web_sources,
                )
        for score, entry, matched in _rank_database_candidates(chu_han, database, limit=2):
            add_candidate(
                matched or entry.get("chu_han", ""),
                f"db_hint_from_{source}",
                max(score, prior),
                entry,
                matched,
                web_sources=web_sources,
            )

    ordered = sorted(
        candidates.values(),
        key=lambda item: (item.get("prior_score", 0), len(item.get("source_votes", []))),
        reverse=True,
    )
    strong_exact = [
        item for item in ordered
        if item.get("db_entry")
        and float(item.get("prior_score") or 0.0) >= 0.9
        and len(normalize_cjk(item.get("chu_han", ""))) >= 6
    ]
    if strong_exact:
        return strong_exact[:1]
    return ordered[:max_candidates]


def _dedupe(items: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in items:
        clean = (item or "").strip()
        if clean and clean.lower() not in seen:
            out.append(clean)
            seen.add(clean.lower())
    return out


NEIFU_4TH_CHAR_MAP = {
    "左": "左", "右": "右", "旨": "旨", "南": "南", "中": "中",
    "東": "東", "东": "東", "束": "東",
    "北": "北", "石": "北", "白": "北",
    "兌": "兌", "兑": "兌", "從": "從", "从": "從",
}


def _neifu_candidate_from_text(text: str) -> str:
    clean = normalize_cjk(text)
    if not clean:
        return ""
    has_nei = "內" in clean
    has_fu = "府" in clean
    has_shi = any(ch in clean for ch in ("侍", "待", "特", "社"))
    if not (has_nei and has_fu and has_shi):
        return ""
    for ch in clean:
        fourth = NEIFU_4TH_CHAR_MAP.get(ch)
        if fourth:
            return f"內府侍{fourth}"
    return ""


def _is_neifu_variant(candidate: Dict[str, Any]) -> bool:
    clean = normalize_cjk(
        candidate.get("chu_han")
        or candidate.get("chu_han_4")
        or candidate.get("detected_chu_han")
        or ""
    )
    return clean.startswith("內府侍") and len(clean) >= 4


def _has_visual_text_support(candidate: Dict[str, Any]) -> bool:
    for source in candidate.get("source_votes") or []:
        source = str(source).lower()
        if source.startswith("ocr") or source.startswith("vision") or source in {"ml_match"}:
            return True
        if (
            source.startswith("db_hint_from_ocr")
            or source.startswith("db_hint_from_ml")
            or source.startswith("db_hint_from_vision")
        ):
            return True
    return False


def _is_image_only_neifu_variant(candidate: Dict[str, Any]) -> bool:
    return _is_neifu_variant(candidate) and not _has_visual_text_support(candidate)


def _neifu_search_queries(chu_han: str, ten_viet: str) -> List[str]:
    clean = normalize_cjk(chu_han)
    if not clean.startswith("\u5167\u5e9c\u4f8d"):
        return []

    display = (ten_viet or "").strip()
    display_ascii = _fold_latin(display).strip()
    queries = [
        f'"{clean}" porcelain mark',
        f'"{clean}" "Bleu de Hue"',
        f'"{display}"',
        f'"{display}" "Bleu de Hue"',
        f'"{display}" "đồ sứ ký kiểu"',
        f'"{display_ascii}" "Bleu de Hue"',
        f'"{display_ascii}" porcelain mark',
        f'"{display_ascii}" lotus crab',
        f'{display} sen cua',
    ]
    return [query for query in queries if '""' not in query]


def _build_candidate_queries(candidate: Dict[str, Any]) -> List[str]:
    chu_han = candidate.get("chu_han", "")
    chu_han_4 = candidate.get("chu_han_4", "")
    ten_viet = candidate.get("hien_thi_chinh") or candidate.get("hieu_de_vi") or candidate.get("ten_viet", "")
    nien_hieu = candidate.get("nien_hieu", "")
    phien_am = candidate.get("phien_am", "")
    phien_am_ascii = _fold_latin(phien_am)

    base_terms = _dedupe([chu_han, chu_han_4, phien_am, phien_am_ascii, nien_hieu, ten_viet])
    queries = []
    for term in base_terms[:4]:
        queries.append(f"{term} porcelain mark")
        queries.append(f'"{term}" porcelain mark')
    for term in base_terms[:4]:
        queries.append(f"{term} ceramic reign mark")
    for term in base_terms[:3]:
        queries.append(f"{term} gốm sứ hiệu đề")
    neifu_queries = _neifu_search_queries(chu_han or chu_han_4, ten_viet)
    return _dedupe(neifu_queries + queries)[:MAX_QUERIES_PER_CANDIDATE]


def _google_query_link(query: str) -> str:
    return f"https://www.google.com/search?q={quote(query)}&hl=vi"


def _source_quality(url: str) -> Tuple[str, float]:
    domain = urlparse(url or "").netloc.lower()
    if any(token in domain for token in LOW_TRUST_EVIDENCE_DOMAINS):
        return "low", 0.18
    if any(domain == trusted or domain.endswith(f".{trusted}") for trusted in HIGH_TRUST_SOURCE_DOMAINS):
        return "high", 0.95
    if any(domain == trusted or domain.endswith(f".{trusted}") for trusted in SPECIALIST_SOURCE_DOMAINS):
        return "medium", 0.84
    high_tokens = [
        "museum", "metmuseum", "britishmuseum", "vam.ac.uk", "npm.gov.tw",
        "sothebys", "christies", "bonhams", "harvard", "edu", "gov",
        "jstor", "cambridge", "oxford", "archive.org",
    ]
    medium_tokens = ["auction", "invaluable", "lot-art", "mutualart", "marks", "porcelain", "ceramic"]
    if any(token in domain for token in high_tokens):
        return "high", 0.95
    if any(token in domain for token in medium_tokens):
        return "medium", 0.72
    return "low", 0.52


def _source_payload(
    search_results: List[SearchResult],
    articles: List[ArticleContent],
) -> List[Dict[str, Any]]:
    article_by_url = {a.url: a for a in articles}
    payload = []
    for r in search_results:
        article = article_by_url.get(r.url)
        quality_label, quality_score = _source_quality(r.url)
        payload.append({
            "title": r.title,
            "url": r.url,
            "snippet": r.snippet,
            "content": (article.content[:1800] if article else ""),
            "source_quality": quality_label,
            "source_quality_score": quality_score,
        })
    return payload


def _dedupe_source_payload(sources: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    payload = []
    seen_urls = set()
    for src in sources or []:
        if not isinstance(src, dict):
            continue
        url = src.get("url") or src.get("source_url")
        if not url or url in seen_urls:
            continue
        quality_label, quality_score = _source_quality(url)
        payload.append({
            "title": src.get("title") or src.get("source_title") or "",
            "url": url,
            "snippet": src.get("snippet") or "",
            "content": (src.get("content") or "")[:1800],
            "source_quality": src.get("source_quality") or quality_label,
            "source_quality_score": float(src.get("source_quality_score") or quality_score),
            "source_pipeline": src.get("source_pipeline", ""),
            "search_type": src.get("search_type", ""),
        })
        seen_urls.add(url)
    return payload


def _pipeline_web_sources(result: Any) -> List[Dict[str, Any]]:
    extra = getattr(result, "extra_data", None) or {}
    sources = _dedupe_source_payload(extra.get("web_sources") or [])
    if sources:
        return sources
    return _dedupe_source_payload(
        {"url": url, "source_pipeline": getattr(result, "pipeline_name", "")}
        for url in (getattr(result, "search_sources", None) or [])
    )


def _merge_source_payloads(*groups: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged = []
    seen_urls = set()
    for group in groups:
        for src in _dedupe_source_payload(group):
            url = src.get("url")
            if url and url not in seen_urls:
                merged.append(src)
                seen_urls.add(url)
    return merged


SOURCE_MATCH_STOPWORDS = {
    "porcelain", "ceramic", "ceramics", "mark", "marks", "reign",
    "dynasty", "period", "made", "year", "nian", "zhi", "nien", "che",
    "qing", "ming", "nguyen", "chinese", "china", "vietnam", "vietnamese",
    "hieu", "gom", "dai", "thanh", "trieu", "nha",
}


def _is_specific_cjk_term(value: str) -> bool:
    term = normalize_cjk(value)
    if len(term) < 2 or term in GENERIC_MARKS:
        return False
    return any(ch not in CJK_SOURCE_STOPWORDS for ch in term)


def _source_domain(url: str) -> str:
    return urlparse(url or "").netloc.lower()


def _source_url(src: Dict[str, Any]) -> str:
    if not isinstance(src, dict):
        return ""
    return str(src.get("url") or src.get("source_url") or "")


def _is_social_source_url(url: str) -> bool:
    domain = _source_domain(url)
    return any(token in domain for token in SOCIAL_SOURCE_DOMAINS)


def _is_low_trust_evidence_url(url: str) -> bool:
    domain = _source_domain(url)
    return any(token in domain for token in LOW_TRUST_EVIDENCE_DOMAINS)


def _is_image_search_source(src: Dict[str, Any]) -> bool:
    return (
        str(src.get("source_pipeline") or "").lower() == "img_search"
        or str(src.get("search_type") or "").lower() == "image"
    )


def _has_irrelevant_source_text(src: Dict[str, Any]) -> bool:
    folded = _fold_latin(_source_text_for_matching(src))
    return any(keyword in folded for keyword in IRRELEVANT_SOURCE_KEYWORDS)


def _has_specific_latin_token(value: str) -> bool:
    tokens = re.findall(r"[a-z0-9]+", value or "")
    return any(len(token) >= 3 and token not in SOURCE_MATCH_STOPWORDS for token in tokens)


def _source_match_terms(
    candidate: Dict[str, Any],
    final: Optional[Dict[str, Any]] = None,
) -> Tuple[List[str], List[str]]:
    fields = (
        "chu_han",
        "hieu_de",
        "chu_han_4",
        "chu_han_6",
        "detected_chu_han",
        "matched_text",
        "ten_viet",
        "ten_viet_ngan",
        "hien_thi_chinh",
        "hieu_de_vi",
        "hieu_de_en",
        "nien_hieu",
        "phien_am",
    )
    raw_values: List[str] = []
    for obj in (candidate or {}, final or {}):
        for field in fields:
            value = obj.get(field) if isinstance(obj, dict) else ""
            if value:
                raw_values.append(str(value))

    cjk_terms: List[str] = []
    latin_terms: List[str] = []
    seen_cjk = set()
    seen_latin = set()

    for value in raw_values:
        cjk = normalize_cjk(value)
        if _is_specific_cjk_term(cjk) and cjk not in seen_cjk:
            cjk_terms.append(cjk)
            seen_cjk.add(cjk)

        for part in re.split(r"[,;|/()\[\]{}]+", value):
            folded = re.sub(r"\s+", " ", _fold_latin(part)).strip(" .:-_\"'")
            if (
                len(folded) >= 4
                and _has_specific_latin_token(folded)
                and folded not in seen_latin
            ):
                latin_terms.append(folded)
                seen_latin.add(folded)

            tokens = [
                token for token in re.findall(r"[a-z0-9]+", folded)
                if len(token) >= 4 and token not in SOURCE_MATCH_STOPWORDS
            ]
            for token in tokens:
                if token not in seen_latin:
                    latin_terms.append(token)
                    seen_latin.add(token)
            for idx in range(len(tokens) - 1):
                phrase = f"{tokens[idx]} {tokens[idx + 1]}"
                if phrase not in seen_latin:
                    latin_terms.append(phrase)
                    seen_latin.add(phrase)

    return cjk_terms, latin_terms


def _source_identity_text_for_matching(src: Dict[str, Any]) -> str:
    values = []
    for field in ("title", "source_title", "url", "source_url"):
        value = src.get(field) if isinstance(src, dict) else ""
        if value:
            values.append(str(value))
    return unquote(" ".join(values))


def _source_text_for_matching(src: Dict[str, Any]) -> str:
    values = []
    for field in (
        "title",
        "source_title",
        "snippet",
        "content",
        "url",
        "source_url",
    ):
        value = src.get(field) if isinstance(src, dict) else ""
        if value:
            values.append(str(value))
    return unquote(" ".join(values))


def _matched_source_terms(
    src: Dict[str, Any],
    candidate: Dict[str, Any],
    final: Optional[Dict[str, Any]] = None,
) -> Tuple[List[str], List[str]]:
    cjk_terms, latin_terms = _source_match_terms(candidate, final)
    text = _source_text_for_matching(src)
    text_cjk = normalize_cjk(text)
    text_latin = _fold_latin(text)
    cjk_matches = _dedupe(term for term in cjk_terms if term and term in text_cjk)
    latin_matches = _dedupe(term for term in latin_terms if term and term in text_latin)
    return cjk_matches, latin_matches


def _fold_phrase_text(value: str) -> str:
    folded = _fold_latin(value)
    return re.sub(r"[^a-z0-9]+", " ", folded).strip()


def _strict_candidate_identity_terms(
    candidate: Dict[str, Any],
    final: Optional[Dict[str, Any]] = None,
) -> Tuple[List[str], List[str]]:
    cjk_fields = ("chu_han", "hieu_de", "chu_han_4", "chu_han_6", "detected_chu_han", "matched_text")
    latin_fields = (
        "ten_viet",
        "ten_viet_ngan",
        "hien_thi_chinh",
        "hieu_de_vi",
        "hieu_de_en",
        "nien_hieu",
        "phien_am",
    )
    cjk_terms: List[str] = []
    latin_terms: List[str] = []

    for obj in (candidate or {}, final or {}):
        for field in cjk_fields:
            value = obj.get(field) if isinstance(obj, dict) else ""
            term = normalize_cjk(str(value or ""))
            if len(term) >= 4 and term not in cjk_terms:
                cjk_terms.append(term)
        for field in latin_fields:
            value = obj.get(field) if isinstance(obj, dict) else ""
            phrase = _fold_phrase_text(str(value or ""))
            tokens = [token for token in phrase.split() if token not in SOURCE_MATCH_STOPWORDS]
            if len(tokens) >= 2 and phrase not in latin_terms:
                latin_terms.append(phrase)
            for token in tokens:
                if len(token) >= 5 and token not in latin_terms:
                    latin_terms.append(token)

    return cjk_terms, latin_terms


def _matched_strict_identity_terms(
    src: Dict[str, Any],
    candidate: Dict[str, Any],
    final: Optional[Dict[str, Any]] = None,
) -> Tuple[List[str], List[str]]:
    cjk_terms, latin_terms = _strict_candidate_identity_terms(candidate, final)
    text = _source_text_for_matching(src)
    text_cjk = normalize_cjk(text)
    text_latin = _fold_phrase_text(text)
    cjk_matches = _dedupe(term for term in cjk_terms if term and term in text_cjk)
    latin_matches = _dedupe(term for term in latin_terms if term and term in text_latin)
    return cjk_matches, latin_matches


def _has_strong_identity_cjk_match(src: Dict[str, Any], cjk_terms: Iterable[str], min_len: int = 4) -> bool:
    text_cjk = normalize_cjk(_source_identity_text_for_matching(src))
    return any(len(term) >= min_len and term in text_cjk for term in cjk_terms)


def _source_supports_candidate(
    src: Dict[str, Any],
    candidate: Dict[str, Any],
    final: Optional[Dict[str, Any]] = None,
) -> bool:
    cjk_matches, latin_matches = _matched_strict_identity_terms(src, candidate, final)
    if not cjk_matches and not latin_matches:
        return False
    if _has_irrelevant_source_text(src):
        return False

    url = _source_url(src)
    if _is_low_trust_evidence_url(url) or _is_social_source_url(url):
        return False
    return True


def _filter_sources_for_candidate(
    sources: Iterable[Dict[str, Any]],
    candidate: Dict[str, Any],
    final: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    filtered = []
    seen_urls = set()
    for src in sources or []:
        if not isinstance(src, dict):
            continue
        url = src.get("url") or src.get("source_url")
        if not url or url in seen_urls:
            continue
        if _source_supports_candidate(src, candidate, final):
            cjk_terms, _ = _source_match_terms(candidate, final)
            if _is_social_source_url(url) and not _has_strong_identity_cjk_match(src, cjk_terms):
                continue
            filtered.append(src)
            seen_urls.add(url)
    return filtered


def _filter_evidence_for_candidate(
    evidence: Iterable[Dict[str, Any]],
    candidate: Dict[str, Any],
    final: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    filtered = []
    seen_urls = set()
    for item in evidence or []:
        if not isinstance(item, dict):
            continue
        matched_text = item.get("matched_text") or item.get("claim") or ""
        src = {
            "title": item.get("source_title") or item.get("title") or "",
            "url": item.get("source_url") or item.get("url") or "",
            "snippet": matched_text,
            "content": item.get("claim") or "",
        }
        url = src["url"]
        if url and url in seen_urls:
            continue
        if _source_supports_candidate(src, candidate, final):
            cjk_terms, _ = _source_match_terms(candidate, final)
            if _is_social_source_url(url) and not _has_strong_identity_cjk_match(src, cjk_terms):
                continue
            filtered.append(item)
            if url:
                seen_urls.add(url)
    return filtered


async def _llm_evaluate_candidate(
    candidate: Dict[str, Any],
    sources: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not sources:
        return None

    prompt = (
        "Bạn là chuyên gia kiểm chứng hiệu đề gốm sứ. Chỉ dùng các nguồn web được cung cấp, "
        "không tự suy đoán ngoài nguồn.\n\n"
        f"Ứng viên cần kiểm chứng:\n{json.dumps(candidate, ensure_ascii=False)}\n\n"
        f"Nguồn web:\n{json.dumps(sources, ensure_ascii=False)[:12000]}\n\n"
        "Hãy trả về JSON hợp lệ theo schema:\n"
        "{\n"
        '  "supported": true,\n'
        '  "confidence": 0.0,\n'
        '  "summary": "vì sao nguồn ủng hộ hoặc không ủng hộ ứng viên",\n'
        '  "evidence": [\n'
        '    {"source_url": "...", "source_title": "...", "claim": "...", "matched_text": "...", "source_quality": "high|medium|low"}\n'
        "  ],\n"
        '  "contradictions": [\n'
        '    {"source_url": "...", "claim": "..."}\n'
        "  ]\n"
        "}\n"
        "Quy tắc: supported=true chỉ khi nguồn có nhắc trực tiếp hiệu đề, niên hiệu, hoặc tên tương ứng. "
        "Nếu nguồn chỉ liên quan chung chung, confidence phải dưới 0.5."
    )
    response = await call_llm(prompt, temperature=0.1, max_tokens=1800)
    parsed = parse_llm_json(response or "")
    if not parsed:
        return None
    evidence = parsed.get("evidence") or []
    contradictions = parsed.get("contradictions") or []
    confidence = float(parsed.get("confidence") or 0.0)
    return {
        "supported": bool(parsed.get("supported")) and confidence >= 0.45,
        "evidence_confidence": max(0.0, min(confidence, 1.0)),
        "summary": parsed.get("summary", ""),
        "evidence": evidence if isinstance(evidence, list) else [],
        "contradictions": contradictions if isinstance(contradictions, list) else [],
    }


def _heuristic_evaluate_candidate(
    candidate: Dict[str, Any],
    sources: List[Dict[str, Any]],
) -> Dict[str, Any]:
    candidate_terms = _dedupe([
        normalize_cjk(candidate.get("chu_han", "")),
        normalize_cjk(candidate.get("chu_han_4", "")),
        candidate.get("ten_viet", ""),
        candidate.get("hien_thi_chinh", ""),
        candidate.get("hieu_de_vi", ""),
        candidate.get("nien_hieu", ""),
        candidate.get("phien_am", ""),
    ])
    cjk_terms, latin_terms = _source_match_terms(candidate)
    evidence = []
    weighted_score = 0.0
    for src in sources:
        if _has_irrelevant_source_text(src):
            continue
        if _is_low_trust_evidence_url(src.get("url", "")) or _is_social_source_url(src.get("url", "")):
            continue
        strict_cjk_matches, strict_latin_matches = _matched_strict_identity_terms(src, candidate)
        matched_terms = _dedupe(strict_cjk_matches + strict_latin_matches)
        matched_terms = _dedupe(matched_terms)
        if not matched_terms:
            continue
        quality_score = float(src.get("source_quality_score") or 0.5)
        strength = 0.72
        if strict_cjk_matches:
            strength = 1.0
        elif strict_latin_matches:
            strength = max(strength, 0.8)
        weighted_score += quality_score * strength
        evidence.append({
            "source_url": src.get("url", ""),
            "source_title": src.get("title", ""),
            "claim": "Nguồn có nhắc trực tiếp thuật ngữ liên quan đến ứng viên.",
            "matched_text": ", ".join(matched_terms[:4]),
            "source_quality": src.get("source_quality", "low"),
        })

    confidence = min(0.92, weighted_score / 1.25)
    return {
        "supported": confidence >= 0.45 and bool(evidence),
        "evidence_confidence": confidence,
        "summary": "Chấm bằng heuristic vì LLM không trả được JSON kiểm chứng.",
        "evidence": evidence,
        "contradictions": [],
    }


def _rank_sources_for_candidate(
    sources: Iterable[Dict[str, Any]],
    candidate: Dict[str, Any],
) -> List[Dict[str, Any]]:
    ranked = []
    for src in _dedupe_source_payload(sources):
        url = src.get("url", "")
        quality_label, quality_score = _source_quality(url)
        src["source_quality"] = quality_label
        src["source_quality_score"] = quality_score
        cjk_matches, latin_matches = _matched_source_terms(src, candidate)
        score = quality_score
        score += min(len(cjk_matches), 3) * 0.35
        score += min(len(latin_matches), 3) * 0.18
        if normalize_cjk(candidate.get("chu_han", "")) in normalize_cjk(_source_identity_text_for_matching(src)):
            score += 0.45
        if _is_low_trust_evidence_url(url):
            score -= 1.0
        ranked.append((score, src))

    ranked.sort(key=lambda item: item[0], reverse=True)
    return [src for _, src in ranked]


async def verify_candidates_with_web(
    candidates: List[Dict[str, Any]],
    search_method: Optional[str] = None,
) -> Dict[str, Any]:
    """Search and verify each candidate against web evidence."""
    evaluated = []
    for candidate in candidates[:MAX_CANDIDATES_FOR_WEB]:
        queries = _build_candidate_queries(candidate)
        query_links = [{"query": query, "url": _google_query_link(query)} for query in queries]
        existing_sources = _dedupe_source_payload(candidate.get("pipeline_web_sources") or [])
        search_results: List[SearchResult] = []
        articles: List[ArticleContent] = []
        sources = _rank_sources_for_candidate(existing_sources, candidate)[:MAX_ARTICLES_PER_CANDIDATE]
        evaluation = _heuristic_evaluate_candidate(candidate, sources) if sources else None
        if not evaluation:
            evaluation = {
                "supported": False,
                "evidence_confidence": 0.0,
                "summary": "Chưa có nguồn để kiểm chứng.",
                "evidence": [],
                "contradictions": [],
            }
        evidence_conf = float(evaluation.get("evidence_confidence") or 0.0)

        needs_more_sources = (
            not sources
            or not evaluation.get("supported")
            or evidence_conf < MIN_EVIDENCE_CONFIDENCE
        )
        if needs_more_sources:
            seen_urls = {src.get("url") for src in sources if src.get("url")}
            min_queries_before_stop = 4 if _is_neifu_variant(candidate) else 1
            for query_index, query in enumerate(queries):
                results = await search_google(
                    query,
                    num_results=MAX_RESULTS_PER_QUERY,
                    prefer_method=search_method,
                )
                for result in results:
                    if result.url and result.url not in seen_urls:
                        search_results.append(result)
                        seen_urls.add(result.url)
                if (
                    len(search_results) >= max(SEARCH_N_RESULTS, MAX_ARTICLES_PER_CANDIDATE)
                    and query_index + 1 >= min_queries_before_stop
                ):
                    break

            # Search snippets plus source quality are enough for fast voting.
            # Avoid Selenium/article scraping here because it can dominate API latency.
            articles = []
            fetched_sources = _source_payload(search_results, articles)
            if fetched_sources:
                sources = _rank_sources_for_candidate(
                    _merge_source_payloads(sources, fetched_sources),
                    candidate,
                )[:MAX_ARTICLES_PER_CANDIDATE]
                evaluation = _heuristic_evaluate_candidate(candidate, sources)

        evidence_conf = float(evaluation.get("evidence_confidence") or 0.0)
        image_only_neifu = _is_image_only_neifu_variant(candidate)
        if image_only_neifu:
            evidence_conf = min(evidence_conf, NEIFU_IMAGE_ONLY_CONFIDENCE_CAP)
            evaluation["supported"] = False
            note = (
                " Biến thể 內府侍X chỉ được nguồn tìm ảnh ủng hộ; "
                "cần OCR/ML đọc được chữ thứ 4 để xác nhận chính xác."
            )
            evaluation["summary"] = (evaluation.get("summary") or "") + note
        prior = float(candidate.get("prior_score") or 0.0)
        contradiction_penalty = 0.12 * len(evaluation.get("contradictions") or [])
        final_score = max(0.0, min(1.0, prior * 0.25 + evidence_conf * 0.75 - contradiction_penalty))
        public_candidate = dict(candidate)
        public_candidate["pipeline_web_source_count"] = len(candidate.get("pipeline_web_sources") or [])
        public_candidate["needs_visual_text_confirmation"] = image_only_neifu
        public_candidate.pop("pipeline_web_sources", None)
        evaluated.append({
            "candidate": public_candidate,
            "queries": queries,
            "query_links": query_links,
            "reused_source_count": len(existing_sources),
            "search_result_count": len(search_results),
            "article_count": len(articles),
            "supported": bool(evaluation.get("supported")) and evidence_conf >= 0.45,
            "evidence_confidence": round(evidence_conf, 4),
            "final_score": round(final_score, 4),
            "summary": evaluation.get("summary", ""),
            "evidence": evaluation.get("evidence", []),
            "contradictions": evaluation.get("contradictions", []),
            "sources": [
                {
                    "title": src.get("title", ""),
                    "url": src.get("url", ""),
                    "snippet": src.get("snippet", ""),
                    "source_quality": src.get("source_quality", "low"),
                    "source_pipeline": src.get("source_pipeline", ""),
                    "search_type": src.get("search_type", ""),
                }
                for src in sources
            ],
        })

    evaluated.sort(key=lambda item: item.get("final_score", 0), reverse=True)
    best = evaluated[0] if evaluated else None
    enough = bool(
        best
        and best.get("supported")
        and float(best.get("evidence_confidence") or 0.0) >= MIN_EVIDENCE_CONFIDENCE
        and len(best.get("evidence") or []) >= 1
    )
    all_source_links = []
    all_query_links = []
    for item in evaluated:
        for src in item.get("sources") or []:
            url = src.get("url")
            if url and url not in all_source_links:
                all_source_links.append(url)
        for link in item.get("query_links") or []:
            if link.get("url") and link not in all_query_links:
                all_query_links.append(link)

    return {
        "status": "web_verified" if enough else "insufficient_web_evidence",
        "enough_evidence": enough,
        "best_candidate": best,
        "candidates": evaluated,
        "all_source_links": all_source_links,
        "all_query_links": all_query_links,
        "min_required_confidence": MIN_EVIDENCE_CONFIDENCE,
    }


def _pick_vietnamese_name(candidate: Dict[str, Any]) -> str:
    cjk_len = len(normalize_cjk(candidate.get("chu_han", "")))
    full_name = candidate.get("hien_thi_chinh") or candidate.get("hieu_de_vi") or ""
    short_name = candidate.get("ten_viet") or ""
    return (full_name or short_name) if cjk_len >= 6 else (short_name or full_name)


def _best_visual_text_candidate(evidence_report: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    best = None
    best_score = -1.0
    for item in evidence_report.get("candidates") or []:
        candidate = item.get("candidate") or {}
        if candidate.get("needs_visual_text_confirmation"):
            continue
        source_votes = [str(v).lower() for v in (candidate.get("source_votes") or [])]
        has_visual_text = any(
            vote.startswith("vision") or vote.startswith("ocr") or vote.startswith("db_hint_from_vision")
            for vote in source_votes
        )
        if not has_visual_text:
            continue
        score = float(candidate.get("prior_score") or 0.0) + float(item.get("evidence_confidence") or 0.0) * 0.5
        if score > best_score:
            best = item
            best_score = score
    return best


def _collect_unverified_reference_sources(
    evidence_report: Dict[str, Any],
    verified_urls: Iterable[str],
    limit: int = 6,
) -> List[Dict[str, Any]]:
    """Expose discovered links separately from strict evidence sources."""
    payload: List[Dict[str, Any]] = []
    seen_urls = {url for url in verified_urls if url}
    items: List[Dict[str, Any]] = []
    best = evidence_report.get("best_candidate")
    if isinstance(best, dict):
        items.append(best)

    for item in items:
        candidate = item.get("candidate") or {}
        for src in item.get("sources") or []:
            if not isinstance(src, dict):
                continue
            url = src.get("url") or src.get("source_url")
            if not url or url in seen_urls:
                continue
            source_quality = src.get("source_quality") or _source_quality(url)[0]
            cjk_matches, latin_matches = _matched_strict_identity_terms(src, candidate)
            if not cjk_matches and not latin_matches:
                continue
            if source_quality == "low":
                continue
            if _has_irrelevant_source_text(src):
                continue
            if _is_social_source_url(url) or _is_low_trust_evidence_url(url):
                continue
            if _is_image_search_source(src):
                continue
            payload.append({
                "title": src.get("title") or src.get("source_title") or "",
                "url": url,
                "snippet": src.get("snippet") or "",
                "source_quality": source_quality,
                "source_pipeline": src.get("source_pipeline", ""),
                "search_type": src.get("search_type", ""),
            })
            seen_urls.add(url)
            if len(payload) >= limit:
                return payload
    return payload


def apply_evidence_to_final(
    final: Dict[str, Any],
    evidence_report: Dict[str, Any],
) -> Dict[str, Any]:
    """Make web evidence the deciding layer for the API response."""
    final = dict(final or {})
    final["web_verification"] = evidence_report
    final["web_verified"] = bool(evidence_report.get("enough_evidence"))
    final["verification_status"] = evidence_report.get("status", "not_verified")

    best = evidence_report.get("best_candidate") or {}
    best_candidate = best.get("candidate") or {}
    evidence = _filter_evidence_for_candidate(best.get("evidence") or [], best_candidate, final)
    sources = []
    for item in evidence:
        url = item.get("source_url") or item.get("url")
        if url and url not in sources:
            sources.append(url)
    source_payloads = _filter_sources_for_candidate(best.get("sources") or [], best_candidate, final)
    for src in source_payloads:
        if _is_image_search_source(src):
            continue
        url = src.get("url")
        if url and url not in sources:
            sources.append(url)

    final["candidate_evidence"] = evidence
    final["search_sources"] = sources
    final["cac_nguon_tham_khao"] = sources
    final["nguon_tham_khao"] = sources
    final["google_query_links"] = []
    unverified_sources = _collect_unverified_reference_sources(evidence_report, sources)
    final["unverified_search_sources"] = unverified_sources
    final["image_search_sources"] = unverified_sources

    filtered_enough_evidence = bool(evidence_report.get("enough_evidence") and evidence)
    final["web_verified"] = filtered_enough_evidence
    if evidence_report.get("enough_evidence") and not filtered_enough_evidence:
        final["verification_status"] = "insufficient_web_evidence"

    old_conf_global = float(final.get("confidence") or final.get("tin_cay") or 0.0)
    final_norm_global = normalize_cjk(final.get("chu_han") or final.get("hieu_de") or "")
    best_norm_global = normalize_cjk(best_candidate.get("chu_han") or "")
    best_agrees_with_final = (
        not best_norm_global
        or not final_norm_global
        or best_norm_global == final_norm_global
        or best_norm_global in final_norm_global
        or final_norm_global in best_norm_global
    )
    if (
        old_conf_global >= 0.75
        and final.get("data_source") == "database"
        and best_norm_global
        and not best_agrees_with_final
    ):
        final["web_verified"] = False
        final["verification_status"] = "web_conflict_or_insufficient"
        final["confidence"] = round(old_conf_global, 4)
        final["tin_cay"] = round(old_conf_global, 4)
        final["canh_bao"] = (
            "Nguồn web tìm được chưa khớp với kết quả OCR/DB/ML đang có độ tin cậy cao. "
            "Giữ kết quả nội bộ và chỉ dùng link nguồn để đối chiếu thêm."
        )
        return final

    if filtered_enough_evidence and best_candidate:
        db_entry = best_candidate.get("db_entry") or {}
        final.update({
            "chu_han": best_candidate.get("chu_han") or final.get("chu_han", ""),
            "hieu_de": best_candidate.get("chu_han") or final.get("hieu_de", ""),
            "ten_viet": _pick_vietnamese_name(best_candidate) or final.get("ten_viet", ""),
            "tên_việt": _pick_vietnamese_name(best_candidate) or final.get("tên_việt", ""),
            "ten_viet_ngan": best_candidate.get("ten_viet") or final.get("ten_viet_ngan", ""),
            "hien_thi_chinh": best_candidate.get("hien_thi_chinh") or final.get("hien_thi_chinh", ""),
            "hieu_de_vi": best_candidate.get("hieu_de_vi") or final.get("hieu_de_vi", ""),
            "trieu_dai": best_candidate.get("trieu_dai") or db_entry.get("trieu_dai") or final.get("trieu_dai", ""),
            "triều_đại": best_candidate.get("trieu_dai") or db_entry.get("trieu_dai") or final.get("triều_đại", ""),
            "nien_hieu": best_candidate.get("nien_hieu") or db_entry.get("nien_hieu") or final.get("nien_hieu", ""),
            "niên_hiệu": best_candidate.get("nien_hieu") or db_entry.get("nien_hieu") or final.get("niên_hiệu", ""),
            "phien_am": best_candidate.get("phien_am") or db_entry.get("phien_am") or final.get("phien_am", ""),
            "phiên_âm": best_candidate.get("phien_am") or db_entry.get("phien_am") or final.get("phiên_âm", ""),
            "hoang_de": db_entry.get("hoang_de") or final.get("hoang_de", ""),
            "hoàng_đế": db_entry.get("hoang_de") or final.get("hoàng_đế", ""),
            "nam_bat_dau": db_entry.get("nam_bat_dau") or final.get("nam_bat_dau"),
            "nam_ket_thuc": db_entry.get("nam_ket_thuc") or final.get("nam_ket_thuc"),
            "nien_dai": db_entry.get("nien_dai") or final.get("nien_dai", ""),
            "niên_đại": db_entry.get("nien_dai") or final.get("niên_đại", ""),
            "hieu_de_en": db_entry.get("hieu_de_en") or final.get("hieu_de_en", ""),
            "mo_ta": db_entry.get("mo_ta") or final.get("mo_ta", ""),
            "boi_canh": db_entry.get("mo_ta") or final.get("boi_canh", ""),
            "ghi_chu": best.get("summary") or final.get("ghi_chu", ""),
            "data_source": "web_evidence",
            "nguon_du_lieu": "Bằng chứng web + ứng viên OCR/ML",
        })
        final_score = float(best.get("final_score") or best.get("evidence_confidence") or 0.0)
        final["confidence"] = round(final_score, 4)
        final["tin_cay"] = round(final_score, 4)
        final["canh_bao"] = ""
    else:
        old_conf = float(final.get("confidence") or final.get("tin_cay") or 0.0)
        final_norm = normalize_cjk(final.get("chu_han") or final.get("hieu_de") or "")
        best_norm = normalize_cjk(best_candidate.get("chu_han") or "")
        source_votes = set(best_candidate.get("source_votes") or [])
        has_database_support = (
            final.get("data_source") == "database"
            or bool(best_candidate.get("db_entry"))
            or any(vote.startswith("db_hint") for vote in source_votes)
            or "ocr_search" in source_votes
            or "ml_match" in source_votes
        )
        candidate_agrees = (
            not best_norm
            or not final_norm
            or best_norm == final_norm
            or best_norm in final_norm
            or final_norm in best_norm
        )
        if (
            old_conf >= 0.75
            and has_database_support
            and candidate_agrees
            and not best_candidate.get("needs_visual_text_confirmation")
        ):
            final["confidence"] = round(old_conf, 4)
            final["tin_cay"] = round(old_conf, 4)
            if sources or unverified_sources:
                final["canh_bao"] = (
                    "Đã tìm được link nguồn để đối chiếu, nhưng nguồn web chưa đủ mạnh để xác nhận độc lập. "
                    "Giữ kết quả OCR/DB/ML vì các tầng nội bộ đang đồng thuận."
                )
            else:
                final["canh_bao"] = (
                    "Chưa tìm được link nguồn web đủ rõ để xác nhận độc lập. "
                    "Giữ kết quả OCR/DB/ML vì các tầng nội bộ đang đồng thuận."
                )
            return final

        visual_item = _best_visual_text_candidate(evidence_report)
        visual_candidate = (visual_item or {}).get("candidate") or {}
        if visual_candidate:
            db_entry = visual_candidate.get("db_entry") or {}
            visual_name = _pick_vietnamese_name(visual_candidate)
            final.update({
                "chu_han": visual_candidate.get("chu_han") or final.get("chu_han", ""),
                "hieu_de": visual_candidate.get("chu_han") or final.get("hieu_de", ""),
                "ten_viet": visual_name or final.get("ten_viet", ""),
                "tên_việt": visual_name or final.get("tên_việt", ""),
                "ten_viet_ngan": visual_candidate.get("ten_viet") or final.get("ten_viet_ngan", ""),
                "hien_thi_chinh": visual_candidate.get("hien_thi_chinh") or final.get("hien_thi_chinh", ""),
                "hieu_de_vi": visual_candidate.get("hieu_de_vi") or final.get("hieu_de_vi", ""),
                "trieu_dai": visual_candidate.get("trieu_dai") or db_entry.get("trieu_dai") or final.get("trieu_dai", ""),
                "triều_đại": visual_candidate.get("trieu_dai") or db_entry.get("trieu_dai") or final.get("triều_đại", ""),
                "nien_hieu": visual_candidate.get("nien_hieu") or db_entry.get("nien_hieu") or final.get("nien_hieu", ""),
                "niên_hiệu": visual_candidate.get("nien_hieu") or db_entry.get("nien_hieu") or final.get("niên_hiệu", ""),
                "phien_am": visual_candidate.get("phien_am") or db_entry.get("phien_am") or final.get("phien_am", ""),
                "phiên_âm": visual_candidate.get("phien_am") or db_entry.get("phien_am") or final.get("phiên_âm", ""),
                "hoang_de": db_entry.get("hoang_de") or final.get("hoang_de", ""),
                "hoàng_đế": db_entry.get("hoang_de") or final.get("hoàng_đế", ""),
                "nam_bat_dau": db_entry.get("nam_bat_dau") or final.get("nam_bat_dau"),
                "nam_ket_thuc": db_entry.get("nam_ket_thuc") or final.get("nam_ket_thuc"),
                "nien_dai": db_entry.get("nien_dai") or final.get("nien_dai", ""),
                "niên_đại": db_entry.get("nien_dai") or final.get("niên_đại", ""),
                "hieu_de_en": db_entry.get("hieu_de_en") or final.get("hieu_de_en", ""),
                "mo_ta": db_entry.get("mo_ta") or final.get("mo_ta", ""),
                "boi_canh": db_entry.get("mo_ta") or final.get("boi_canh", ""),
                "data_source": "visual_text_unverified_web",
            })
            visual_score = max(
                float(visual_candidate.get("prior_score") or 0.0),
                float((visual_item or {}).get("evidence_confidence") or 0.0),
            )
            capped = min(max(visual_score, 0.45), 0.62)
            final["confidence"] = round(capped, 4)
            final["tin_cay"] = round(capped, 4)
            final["canh_bao"] = (
                "AI đọc ảnh trực tiếp ra ứng viên này, nhưng chưa đủ nguồn web độc lập "
                "để xác nhận chắc chắn."
            )
            return final

        if best_candidate.get("needs_visual_text_confirmation"):
            final.update({
                "chu_han": "內府侍?",
                "hieu_de": "內府侍?",
                "ten_viet": "Nội Phủ Thị (chưa xác định chữ cuối)",
                "tên_việt": "Nội Phủ Thị (chưa xác định chữ cuối)",
                "ten_viet_ngan": "Nội Phủ Thị",
                "hien_thi_chinh": "Nội Phủ Thị (chưa xác định chữ cuối)",
                "hieu_de_vi": "Nội Phủ Thị (chưa xác định chữ cuối)",
                "trieu_dai": "Nhà Nguyễn (Việt Nam)",
                "triều_đại": "Nhà Nguyễn (Việt Nam)",
                "nien_hieu": "Nội Phủ Thị",
                "niên_hiệu": "Nội Phủ Thị",
                "phien_am": "Nội Phủ Thị",
                "phiên_âm": "Nội Phủ Thị",
                "hieu_de_en": "Nội Phủ Thị Mark (uncertain final character)",
                "data_source": "web_evidence_uncertain_variant",
            })
        old_conf = float(final.get("confidence") or final.get("tin_cay") or 0.0)
        capped = min(old_conf, 0.55) if old_conf else 0.35
        final["confidence"] = round(capped, 4)
        final["tin_cay"] = round(capped, 4)
        if best_candidate.get("needs_visual_text_confirmation"):
            final["canh_bao"] = (
                "Đã nhận ra nhóm Nội Phủ, nhưng chưa có OCR/ML xác nhận chữ thứ 4. "
                "Không dùng kết quả tìm ảnh để kết luận chắc biến thể 侍左/侍右/侍東/侍從."
            )
        else:
            if sources or unverified_sources or final.get("google_query_links"):
                final["canh_bao"] = (
                    "Đã đính kèm nguồn/truy vấn tham khảo để đối chiếu. "
                    "Các nguồn hiện có chưa đủ mạnh để xác nhận chắc chắn."
                )
            else:
                final["canh_bao"] = (
                    "Chưa tìm được nguồn web đủ rõ để xác nhận chắc chắn. "
                    "Kết quả hiện tại chỉ là dự đoán từ OCR/ML/DB."
                )
    return final
