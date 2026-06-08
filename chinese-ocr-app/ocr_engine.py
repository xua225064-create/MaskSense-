import cv2
import numpy as np
import re
import os
import json
from paddleocr import PaddleOCR
from typing import List, Tuple
from ocr_corrections import correct_ocr_text, is_valid_char, get_correction_stats

DEBUG_DIR = "debug"
os.makedirs(DEBUG_DIR, exist_ok=True)

print("Loading PaddleOCR...")
ocr = PaddleOCR(
    use_angle_cls=True,
    lang="ch",
    use_gpu=False,
    show_log=False,
    det_limit_side_len=2048,
    det_db_unclip_ratio=1.6,
    det_db_thresh=0.3,
    det_db_box_thresh=0.5,
)
print("PaddleOCR ready!")

MAX_OCR_DIM = 1600
MIN_CONF = 0.35  # Lowered: base threshold to capture all characters (was 0.55)
MIN_CONF_FALLBACK = 0.28  # Lowered: fallback for blurry images (was 0.45)
MIN_CONF_AMBIGUOUS = 0.50  # Lowered: still strict for confusable characters (was 0.72)
EARLY_ACCEPT_SCORE = 5.0  # Increased: require higher score before early stopping
EARLY_ACCEPT_LEN = 6  # Six-character reign marks are complete enough to stop early.
MAX_VARIANTS_PER_REQUEST = 12  # Increased: allow more variants for better results (was 8)
DEEP_EXTRA_VARIANTS = 6  # Increased: more deep variants (was 4)
SAVE_DEBUG_VARIANTS = False  # Tắt ghi file debug để tăng tốc

# ============================================================
# Bản đồ ký tự tương tự để tránh nhầm lẫn
# ============================================================
SIMILAR_CHAR_GROUPS = {
    # Các ký tự tương tự cần confidence cao
    frozenset(['内', '乾', '干', '土']): 0.45,      # 内(nội) vs 乾(kiền/khiền)
    frozenset(['府', '甲', '甲', '申']): 0.45,      # 府(phủ) vs các ký tự tương tự
    frozenset(['蓝', '篮', '监']): 0.45,            # Các ký tự "blue-like"
    frozenset(['蒙', '蒙', '艹']): 0.45,            # Các ký tự với "艹" radical
    frozenset(['康', '吊', '口']): 0.45,            # 康 vs các ký tự khác
    frozenset(['正', '止', '工']): 0.45,            # 正(chính) vs các ký tự khác
    frozenset(['嘉', '嘉', '口']): 0.45,            # 嘉(gia) vs các ký tự khác
    
    # Nội Phủ Thị series - ký tự từ hệ thống kiểu Nguyễn
    frozenset(['侍', '佚', '待', '寺', '停', '仃', '亭']): 0.50,  # 侍(thị) - cực kỳ dễ nhầm (停/亭/仃 cùng bộ 亻)
    frozenset(['北', '石', '北', '白']): 0.50,      # 北(bắc) vs 石(thạch) - dễ nhầm
    frozenset(['東', '东', '夫']): 0.50,            # 東(đông) - traditional vs simplified
    frozenset(['南', '男', '闵']): 0.50,            # 南(nam) vs 男(nam - khác nghĩa)
    frozenset(['中', '巾', '中']): 0.48,            # 中(trung) - viết dễ bị mờ
    frozenset(['右', '右', '左']): 0.48,            # 右(hữu/tây)
    frozenset(['左', '左', '右']): 0.48,            # 左(tả/đông)
    frozenset(['兌', '兑', '充']): 0.50,            # 兌(đoài) - traditional vs simplified
}


def _attempt_ocr_correction(ocr_text: str) -> str:
    """
    Sửa hiệu đề OCR nhầm sử dụng module ocr_corrections.
    
    Chiến lược:
    1. Kiểm tra ký tự valid
    2. Nếu có ký tự invalid → suggest corrections
    3. Validate với database
    4. Return best candidate
    
    Args:
        ocr_text: Text từ OCR
    
    Returns:
        str: Text đã sửa hoặc text gốc
    """
    if not ocr_text:
        return ocr_text
    
    try:
        # Load database
        db_path = os.path.join(os.path.dirname(__file__), "data", "hieu_de_database.json")
        with open(db_path, 'r', encoding='utf-8') as f:
            database = json.load(f)
    except Exception as e:
        print(f"  [Correction] Lỗi load database: {e}")
        database = []
    
    # Sử dụng module ocr_corrections
    correction_result = correct_ocr_text(ocr_text, database)
    
    # Log chi tiết
    if correction_result["invalid_chars"]:
        print(f"  [Validation] '{ocr_text}' chứa ký tự invalid: {correction_result['invalid_chars']}")
        print(f"  [Suggestions] {correction_result['suggestions'][:3]}")
    
    if correction_result["matched_in_db"]:
        print(f"  [✓ Database Match] '{ocr_text}' → '{correction_result['corrected']}' (tín cậy: {correction_result['confidence']:.2f})")
        return correction_result["corrected"]
    
    if correction_result["corrected"] != ocr_text:
        print(f"  [⚠ Corrected] '{ocr_text}' → '{correction_result['corrected']}' (tín cậy: {correction_result['confidence']:.2f})")
        return correction_result["corrected"]
    
    return ocr_text


def _plausible_reign_ocr_string(s: str) -> bool:
    """
    True nếu chuỗi có dạng hiệu niên hào hợp lệ (đủ tín hiệu 年製/年造/年玩 hoặc 內府…).
    Dùng để KHÔNG dừng sớm / KHÔNG ưu tiên các chuỗi OCR lộn cột kiểu 「盛大年清银康」.
    """
    t = re.sub(r"[^\u4e00-\u9fff]", "", s or "")
    if not t:
        return False
    if any(x in t for x in ("年製", "年造", "年玩")):
        return True
    if "內府" in t or "内府" in t:
        return True
    if "御製" in t or "御制" in t:
        return True
    return False


def _is_incomplete_dynasty_mark(text: str) -> bool:
    clean = _canonicalize_reign_mark_text(text)
    clean = re.sub(r"[^\u4e00-\u9fff]", "", clean or "")
    return clean in {"大明年製", "大清年製", "大南年製"}


def _derive_qing_guangxu_from_ocr_evidence(texts: List[str]) -> str:
    """
    Recover common Qing six-character marks when OCR sees the right glyphs in
    separate blocks. This is conservative: require dynasty + reign evidence +
    year/manufacture evidence, and avoid conflicting reign signals.
    """
    normalized = [_canonicalize_reign_mark_text(t) for t in texts if t]
    joined = "".join(normalized).translate(_OCR_CANONICAL_CHARS)
    has_qing = "大清" in joined or ("大" in joined and "清" in joined)
    has_year_mark = "年" in joined and "製" in joined
    guangxu_conflicts = any(ch in joined for ch in "康熙雍正乾隆嘉慶道咸豐同治宣統")
    if has_qing and "光" in joined and "緒" in joined and has_year_mark:
        return "大清光緒年製"
    if has_qing and "光" in joined and "緒" in joined and "年" in joined and not guangxu_conflicts:
        return "大清光緒年製"
    if has_qing and "光" in joined and has_year_mark and not guangxu_conflicts:
        return "大清光緒年製"

    kangxi_conflicts = any(ch in joined for ch in "雍正乾隆嘉慶道光緒咸豐同治宣統")
    has_kang_hint = "康" in joined or "泰" in joined  # Paddle often reads 康 as 泰 in small marks.
    if has_qing and "熙" in joined and has_year_mark and not kangxi_conflicts:
        return "大清康熙年製"
    if has_qing and "熙" in joined and "年" in joined and has_kang_hint and not kangxi_conflicts:
        return "大清康熙年製"
    return ""


_EVIDENCE_CANONICAL_CHARS = str.maketrans({
    "装": "製",
    "裝": "製",
    "制": "製",
    "万": "萬",
    "历": "曆",
    "暦": "曆",
    "歴": "曆",
    "厤": "曆",
    "结": "緒",
    "結": "緒",
    "绪": "緒",
    "泰": "康",
})


_WANLI_EVIDENCE_CANONICAL_CHARS = str.maketrans({
    "万": "萬",
    "历": "曆",
    "暦": "曆",
    "歴": "曆",
    "厤": "曆",
    "唐": "曆",  # PaddleOCR often reads the top-left 萬曆 glyph as 唐 on blue marks.
    "装": "製",
    "裝": "製",
    "制": "製",
})


def _derive_ming_wanli_from_ocr_evidence(texts: List[str]) -> str:
    """
    Recover 大明萬曆年製 when OCR sees enough scattered glyph evidence.

    Blue underglaze Wanli marks often split into columns and the 曆 glyph is
    read as 唐/暦/歴 or dropped. Require dynasty + 萬 + 年 + 製 and reject
    obvious conflicting Ming reign signals.
    """
    normalized = [_canonicalize_reign_mark_text(t) for t in texts if t]
    evidence = re.sub(r"[^\u4e00-\u9fff]", "", "".join(normalized))
    evidence = evidence.translate(_WANLI_EVIDENCE_CANONICAL_CHARS)
    if not evidence:
        return ""

    evidence_set = set(evidence)
    has_ming = "大明" in evidence or {"大", "明"}.issubset(evidence_set)
    has_year_mark = "年" in evidence_set and any(ch in evidence_set for ch in ("製", "造"))
    if not (has_ming and "萬" in evidence_set and has_year_mark):
        return ""

    conflicting_ming_reigns = set("洪武永樂宣德正統景泰天順成化弘治正德嘉靖隆慶泰昌天啟崇禎")
    if conflicting_ming_reigns & evidence_set:
        return ""

    # Prefer explicit 曆 evidence, but allow recovery when OCR missed only that
    # one hard glyph and all other required Wanli mark characters are present.
    if "曆" in evidence_set or len(set("大明萬年製") & evidence_set) >= 5:
        return "大明萬曆年製"
    return ""


def _derive_database_mark_from_ocr_evidence(texts: List[str]) -> str:
    """
    Recover a known database mark from scattered OCR glyph evidence.

    This is intentionally stricter than normal fuzzy matching: it requires the
    dynasty characters, 年, a manufacture marker, and most unique characters of
    the target to appear in the combined OCR evidence.
    """
    evidence = "".join(_canonicalize_reign_mark_text(t) for t in texts if t)
    evidence = re.sub(r"[^\u4e00-\u9fff]", "", evidence).translate(_EVIDENCE_CANONICAL_CHARS)
    if not evidence or "年" not in evidence:
        return ""

    try:
        db_path = os.path.join(os.path.dirname(__file__), "data", "hieu_de_database.json")
        with open(db_path, "r", encoding="utf-8") as f:
            database = json.load(f)
    except Exception:
        return ""

    evidence_set = set(evidence)
    best = ("", 0.0)
    qing_reign_chars = set("康熙雍正乾隆嘉慶道光緒咸豐同治宣統")

    for entry in database:
        target = entry.get("chu_han", "")
        target_norm = _canonicalize_reign_mark_text(target)
        target_norm = re.sub(r"[^\u4e00-\u9fff]", "", target_norm).translate(_EVIDENCE_CANONICAL_CHARS)
        if len(target_norm) < 4 or "年" not in target_norm:
            continue
        if not any(marker in target_norm for marker in ("製", "造", "玩")):
            continue
        dynasty = target_norm[:2] if target_norm.startswith(("大清", "大明", "大南")) else ""
        if dynasty and not set(dynasty).issubset(evidence_set):
            continue
        if not any(marker in evidence_set for marker in ("製", "造", "玩")):
            continue

        target_set = set(target_norm)
        coverage = len(target_set & evidence_set) / max(len(target_set), 1)
        if coverage < 0.82:
            continue

        if target_norm.startswith("大清"):
            target_reigns = qing_reign_chars & target_set
            evidence_reigns = qing_reign_chars & evidence_set
            unrelated = evidence_reigns - target_reigns
            if unrelated:
                continue
            if target_reigns and len(target_reigns & evidence_set) < max(1, min(2, len(target_reigns))):
                continue

        score = coverage + (0.1 if target_norm in evidence else 0.0)
        if score > best[1]:
            best = (target_norm, score)

    return best[0]


def _variant_sort_key(text: str, score: float) -> Tuple[int, int, float]:
    """
    (tier, -len_cjk, -score):
    - tier 0: đã có 年製/年造/…
    - tier 1: chưa đủ — ưu tiên chuỗi DÀI hơn (OCR lộn cột vẫn còn nhiều ký tự để khớp DB),
      tránh chọn mẫu quá ngắn kiểu 「派大年」.
    """
    canonical = _canonicalize_reign_mark_text(text)
    t = re.sub(r"[^\u4e00-\u9fff]", "", canonical or "")
    if _is_incomplete_dynasty_mark(canonical):
        tier = 2
    else:
        tier = 0 if _plausible_reign_ocr_string(canonical) else 1
    return (tier, -len(t), -score)


_OCR_CANONICAL_CHARS = str.maketrans({
    "绪": "緒",
    "结": "緒",
    "結": "緒",
    "统": "統",
    "历": "曆",
    "暦": "曆",
    "歴": "曆",
    "厤": "曆",
    "万": "萬",
    "制": "製",
    "装": "製",
    "裝": "製",
    "内": "內",
})

_NEIFU_MARK_SUFFIXES = {"旨", "中", "右", "左", "東", "东", "南", "北", "兌", "兑", "從", "从"}
_NEIFU_OCR_CONFUSIONS = {
    "内": "內",
    "待": "侍",
    "特": "侍",
    "持": "侍",
    "停": "侍",    # PaddleOCR rất hay nhầm 侍→停 (cùng bộ 亻)
    "仃": "侍",    # 仃 vs 侍
    "亭": "侍",    # 亭 vs 侍 (phần dưới giống)
    "杜": "右",
    "社": "右",
    "赶": "右",
    "柱": "右",    # 柱 bị nhầm khi nét mờ
    "石": "北",
    "白": "北",
    "东": "東",
    "兑": "兌",
    "从": "從",
    "男": "南",    # 男 vs 南 trên men mờ
    "宕": "旨",    # 宕 vs 旨
}


def _canonicalize_neifu_mark_text(raw: str) -> str:
    """Normalize common OCR order/noise for Nguyen Nội Phủ workshop marks."""
    if not raw:
        return ""

    mapped = "".join(_NEIFU_OCR_CONFUSIONS.get(ch, ch) for ch in raw)

    def _pick_suffix(text: str) -> str:
        candidates = [ch for ch in text if ch in _NEIFU_MARK_SUFFIXES]
        if not candidates:
            return ""
        s = candidates[0]
        if s == "东":
            s = "東"
        elif s == "兑":
            s = "兌"
        elif s == "从":
            s = "從"
        return s

    # Case 1: Đủ 3 ký tự core 內 + 府 + 侍
    if "內" in mapped and "府" in mapped and "侍" in mapped:
        suffix = _pick_suffix(mapped)
        if suffix:
            return "內府侍" + suffix
        # Chỉ có 內府侍 không suffix (3 char mark)
        cjk_only = [ch for ch in mapped if '\u4e00' <= ch <= '\u9fff']
        if len(cjk_only) == 3:
            return "內府侍"
        return ""

    # Case 2: OCR thiếu 侍 — chỉ đọc 內 + 府 + 1 suffix
    # → Suy luận đây là 內府侍X bị thiếu chữ thứ 3
    if "內" in mapped and "府" in mapped and "侍" not in mapped:
        suffix = _pick_suffix(mapped)
        if suffix:
            cjk_only = [ch for ch in mapped if '\u4e00' <= ch <= '\u9fff']
            if len(cjk_only) <= 3:
                return "內府侍" + suffix

    return ""


def _canonicalize_reign_mark_text(text: str) -> str:
    """
    Normalize common PaddleOCR output for vertical reign marks.

    Six-character marks are written in two vertical columns and read from the
    right column first. OCR often concatenates the left column before the right,
    e.g. 緒年製大清光 -> 大清光緒年製.
    """
    raw = re.sub(r"[^\u4e00-\u9fff]", "", text or "").translate(_OCR_CANONICAL_CHARS)
    if not raw:
        return text

    neifu_mark = _canonicalize_neifu_mark_text(raw)
    if neifu_mark:
        return neifu_mark

    for prefix in ("大清", "大明", "大南"):
        pos = raw.find(prefix)
        if pos > 0:
            rotated = raw[pos:] + raw[:pos]
            if len(rotated) >= 6:
                raw = rotated
            break

    # Common OCR order for two columns: 大清製光緒年 -> 大清光緒年製.
    for prefix in ("大清", "大明", "大南"):
        if raw.startswith(prefix) and len(raw) == 6 and raw[2] in {"製", "造"} and raw[-1] == "年":
            raw = raw[:2] + raw[3:5] + raw[-1] + raw[2]
            break

    # Keep incomplete 5-char dynasty marks intact for evidence/database
    # recovery later. Example: 大清光年製 may still recover to 大清光緒年製
    # when other OCR variants provide the missing reign character.
    if len(raw) == 5:
        for prefix in ("大清", "大明", "大南"):
            if raw.startswith(prefix) and "年" in raw and ("製" in raw or "造" in raw):
                break

    return raw


def _is_ambiguous_char(char: str) -> bool:
    """
    Kiểm tra xem ký tự có phải là ký tự tương tự/nhầm lẫn cao không.
    Các ký tự này cần confidence cao hơn bình thường.
    """
    for group in SIMILAR_CHAR_GROUPS:
        if char in group:
            return True
    return False


def _get_required_confidence(text: str) -> float:
    """
    Tính toán confidence threshold cần thiết cho text dựa trên ký tự trong đó.
    Nếu có ký tự tương tự, cần confidence cao hơn.
    
    Strategy:
    - Kiểm tra TẤT CẢ ký tự
    - Trả về threshold CAO NHẤT cần thiết
    - Ký tự "cực kỳ nguy hiểm" (侍, 北, etc.) → 0.50
    - Ký tự "tương tự" khác → 0.48
    - Bình thường → 0.35
    """
    # Ký tự cực kỳ nguy hiểm (thường nhầm lẫn)
    ultra_risky_chars = {'侍', '北', '東', '东', '兌', '兑'}
    
    max_required = MIN_CONF
    
    for c in text:
        if '\u4e00' <= c <= '\u9fff':  # Chữ Hán
            if c in ultra_risky_chars:
                max_required = max(max_required, 0.50)  # More permissive now
            elif _is_ambiguous_char(c):
                max_required = max(max_required, 0.48)  # Slightly stricter than normal
    
    return max_required


def _find_database_matches(ocr_text: str, max_results: int = 5) -> List[dict]:
    """
    Tìm các khớp trong database theo tiêu chí:
    1. Khớp chính xác
    2. Khớp trong biến thể (bien_the)
    3. Khớp fuzzy (cho phép sai 1-2 ký tự - dành cho OCR nhầm lẫn)
    
    Returns:
        List[dict] với structure: [{'match': 'exact'|'variant'|'fuzzy', 'entry': {...}, 'score': float}]
    """
    if not ocr_text:
        return []
    
    try:
        db_path = os.path.join(os.path.dirname(__file__), "data", "hieu_de_database.json")
        with open(db_path, 'r', encoding='utf-8') as f:
            database = json.load(f)
        
        matches = []
        ocr_len = len(ocr_text)
        
        for entry in database:
            chu_han = entry.get('chu_han', '')
            bien_the = entry.get('bien_the', [])
            
            # 1. Khớp chính xác
            if ocr_text == chu_han:
                matches.append({
                    'match_type': 'exact',
                    'entry': entry,
                    'score': 1.0,
                    'matched_text': chu_han
                })
                continue
            
            # 2. Khớp trong biến thể
            for variant in bien_the:
                if ocr_text == variant:
                    matches.append({
                        'match_type': 'variant',
                        'entry': entry,
                        'score': 0.95,
                        'matched_text': variant
                    })
                    continue
            
            # 3. Khớp fuzzy - cho phép sai 1 ký tự (OCR nhầm)
            if len(chu_han) == ocr_len:
                diff_count = 0
                for i in range(ocr_len):
                    if chu_han[i] != ocr_text[i]:
                        diff_count += 1
                
                if diff_count == 1:  # Chỉ sai 1 ký tự
                    # Kiểm tra xem ký tự bị nhầm có nằm trong SIMILAR_CHAR_GROUPS không
                    wrong_pos = -1
                    for i in range(ocr_len):
                        if chu_han[i] != ocr_text[i]:
                            wrong_pos = i
                            break
                    
                    if wrong_pos >= 0:
                        correct_char = chu_han[wrong_pos]
                        wrong_char = ocr_text[wrong_pos]
                        # Kiểm tra xem đây có phải là cặp ký tự dễ nhầm không
                        is_confusable = False
                        for group in SIMILAR_CHAR_GROUPS:
                            if correct_char in group and wrong_char in group:
                                is_confusable = True
                                break
                        
                        if is_confusable:
                            matches.append({
                                'match_type': 'fuzzy_confusable',
                                'entry': entry,
                                'score': 0.85,  # Độ tin cậy cao hơn fuzzy thường
                                'matched_text': chu_han,
                                'wrong_char': wrong_char,
                                'correct_char': correct_char,
                                'position': wrong_pos
                            })
                        else:
                            matches.append({
                                'match_type': 'fuzzy_other',
                                'entry': entry,
                                'score': 0.70,  # Độ tin cậy thấp hơn
                                'matched_text': chu_han,
                                'wrong_char': wrong_char,
                                'correct_char': correct_char,
                                'position': wrong_pos
                            })
        
        # Sắp xếp theo score (cao nhất trước)
        matches.sort(key=lambda x: x['score'], reverse=True)
        
        return matches[:max_results]
    
    except Exception as e:
        print(f"  [DB] Lỗi tìm kiếm: {e}")
        return []


def _validate_against_database(ocr_text: str) -> dict:
    """
    Kiểm tra xem OCR text có khớp với database không.
    
    Returns:
        dict với:
        - database_valid: bool
        - warning: str (cảnh báo nếu có)
        - best_match: dict hoặc None
        - suggestions: list[dict] (các gợi ý nếu không khớp chính xác)
    """
    if not ocr_text:
        return {
            'database_valid': False,
            'warning': 'Không có OCR result',
            'best_match': None,
            'suggestions': []
        }
    
    try:
        matches = _find_database_matches(ocr_text)
        
        if not matches:
            return {
                'database_valid': False,
                'warning': f"Hiệu đề '{ocr_text}' không tìm thấy trong cơ sở dữ liệu",
                'best_match': None,
                'suggestions': []
            }
        
        best = matches[0]
        
        if best['match_type'] == 'exact':
            return {
                'database_valid': True,
                'warning': '',
                'best_match': best,
                'suggestions': []
            }
        
        elif best['match_type'] == 'variant':
            return {
                'database_valid': True,
                'warning': f"Là biến thể của '{best['matched_text']}'",
                'best_match': best,
                'suggestions': []
            }
        
        elif best['match_type'] == 'fuzzy_confusable':
            # Đây là trường hợp OCR nhầm ký tự dễ nhầm lẫn
            suggestion_text = f"OCR đọc '{best['wrong_char']}' nhưng có thể là '{best['correct_char']}'?"
            return {
                'database_valid': False,
                'warning': suggestion_text,
                'best_match': best,
                'suggestions': matches[1:] if len(matches) > 1 else []
            }
        
        else:  # fuzzy_other
            return {
                'database_valid': False,
                'warning': f"Gợi ý: Có thể là '{best['matched_text']}' (sai ký tự vị trí {best['position']})?",
                'best_match': best,
                'suggestions': matches[1:] if len(matches) > 1 else []
            }
    
    except Exception as e:
        print(f"  [DB] Lỗi validate: {e}")
        return {
            'database_valid': False,
            'warning': f'Database validation error: {str(e)}',
            'best_match': None,
            'suggestions': []
        }


# ============================================================
# Hàm tiện ích
# ============================================================
def _safe_resize(img: np.ndarray, max_dim: int = MAX_OCR_DIM) -> np.ndarray:
    h, w = img.shape[:2]
    if max(h, w) <= max_dim:
        return img
    scale = max_dim / max(h, w)
    return cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)


def _is_already_zoomed(image: np.ndarray) -> bool:
    """
    FIX 2: Phát hiện ảnh đã được zoom cận cảnh vào hiệu đề (từ Google/search).
    Nếu vùng viền ngoài 20% hầu như không có nội dung tối (trắng/sáng), thì đây là
    ảnh bát to, cần crop. Nếu vùng viền có nhiều nội dung, ảnh đã zoom sẵn → KHÔNG crop.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # Kiểm tra viền: 4 dải ngoài cùng (20% mỗi chiều)
    border_pixels = np.concatenate([
        gray[:int(h * 0.20), :].flatten(),         # viền trên
        gray[int(h * 0.80):, :].flatten(),          # viền dưới
        gray[:, :int(w * 0.20)].flatten(),           # viền trái
        gray[:, int(w * 0.80):].flatten(),           # viền phải
    ])

    # Nếu viền chứa nhiều pixel tối (< 100) → chữ nằm gần biên → ảnh đã zoom
    dark_ratio = np.mean(border_pixels < 100)
    print(f"  [zoom_detect] dark_ratio_in_border={dark_ratio:.3f}")
    return dark_ratio > 0.12   # > 12% pixel tối ở viền → không crop


def auto_center_crop(
    image: np.ndarray,
    save_debug: bool = True,
    debug_name: str = "debug_crop.jpg",
) -> np.ndarray:
    """
    FIX 2: Chỉ crop nếu ảnh là ảnh bát to (chưa zoom).
    Nếu ảnh đã zoom cận cảnh, trả về nguyên ảnh.
    """
    if _is_already_zoomed(image):
        print("  [crop] Ảnh đã zoom sẵn → KHÔNG cắt")
        if save_debug:
            try:
                cv2.imwrite(debug_name, image)
            except Exception:
                pass
        return image

    h, w = image.shape[:2]
    start_y = int(h * 0.20)
    end_y = int(h * 0.80)
    start_x = int(w * 0.20)
    end_x = int(w * 0.80)

    cropped_img = image[start_y:end_y, start_x:end_x]
    if cropped_img.size == 0:
        return image

    if save_debug:
        try:
            cv2.imwrite(debug_name, cropped_img)
        except Exception as e:
            print("Lỗi khi lưu ảnh debug:", e)

    return cropped_img


def enhance_image_for_ocr(image):
    try:
        cv2.imwrite("debug_enhanced.jpg", image)
    except Exception:
        pass
    return image


def detect_google_image(image: np.ndarray) -> bool:
    """
    Phát hiện xem ảnh có phải từ Google Search không.
    Google images thường có:
    - Watermark ở góc
    - Compression artifacts
    - Chất lượng khác nhau
    """
    h, w = image.shape[:2]
    # Kiểm tra watermark ở góc
    corner_size = int(min(h, w) * 0.15)
    corners = [
        image[:corner_size, :corner_size],
        image[:corner_size, w-corner_size:],
        image[h-corner_size:, :corner_size],
        image[h-corner_size:, w-corner_size:],
    ]
    
    # Nếu nhiều góc có pixel rất sáng/trắng → có thể là watermark Google
    bright_corners = 0
    for corner in corners:
        bright_ratio = np.mean(corner) > 200
        if bright_ratio:
            bright_corners += 1
    
    return bright_corners >= 2


def preprocess_google_image(image: np.ndarray) -> np.ndarray:
    """
    Preprocessing tối ưu cho ảnh Google Search.
    - Giảm watermark
    - Cải thiện contrast
    - Khử nhiễu compression
    """
    # Khử nhiễu bilateral filter (giữ cạnh)
    denoised = cv2.bilateralFilter(image, d=9, sigmaColor=75, sigmaSpace=75)
    
    # Cải thiện contrast với CLAHE trên LAB
    lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    
    clahe = cv2.createCLAHE(clipLimit=3.5, tileGridSize=(8, 8))
    l_clahe = clahe.apply(l)
    
    enhanced = cv2.cvtColor(cv2.merge([l_clahe, a, b]), cv2.COLOR_LAB2BGR)
    
    # Slight unsharp mask để làm nét chữ
    blur = cv2.GaussianBlur(enhanced, (0, 0), 1.0)
    sharpened = cv2.addWeighted(enhanced, 1.5, blur, -0.5, 0)
    
    return np.clip(sharpened, 0, 255).astype(np.uint8)


# ============================================================
# Preprocessing functions
# ============================================================
def remove_red_stamp(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    m1 = cv2.inRange(hsv, (0, 60, 60), (15, 255, 255))
    m2 = cv2.inRange(hsv, (155, 60, 60), (180, 255, 255))
    red_mask = cv2.bitwise_or(m1, m2)

    # Phát hiện hồng đề (chữ đỏ): nếu pixel đỏ tập trung ở trung tâm ảnh
    # → đây là chữ đỏ, KHÔNG xóa
    h, w = red_mask.shape[:2]
    center_region = red_mask[int(h*0.2):int(h*0.8), int(w*0.2):int(w*0.8)]
    total_red = np.count_nonzero(red_mask)
    center_red = np.count_nonzero(center_region)
    
    if total_red > 0:
        center_ratio = center_red / max(total_red, 1)
        red_density = total_red / max(h * w, 1)
        print(f"  [red_detect] total_red_ratio={red_density:.3f}, center_ratio={center_ratio:.3f}")
        
        # Nếu đỏ tập trung ở trung tâm (>40%) VÀ mật độ đỏ đáng kể (>0.5%)
        # → hồng đề, không xóa
        if center_ratio > 0.40 and red_density > 0.005:
            print("  [red_detect] Hồng đề detected (red text). Skipping red removal.")
            return img

    mask = cv2.dilate(red_mask, np.ones((9, 9), np.uint8), iterations=2)
    return cv2.inpaint(img, mask, 5, cv2.INPAINT_TELEA)

def red_channel_best(img_bgr):
    # Dành cho chữ đen trên nền vàng (như men gốm vàng)
    _, _, r = cv2.split(img_bgr)
    r_inv = cv2.bitwise_not(r)
    clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4, 4))
    r_enhanced = clahe.apply(r_inv)
    _, binary = cv2.threshold(r_enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = np.ones((3, 3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    if np.mean(binary) < 128:
        binary = cv2.bitwise_not(binary)
    return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

def blue_channel_best(img_bgr):
    b, g, r = cv2.split(img_bgr)
    b_inv = cv2.bitwise_not(b)
    clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4, 4))
    b_enhanced = clahe.apply(b_inv)
    _, binary = cv2.threshold(b_enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = np.ones((3, 3), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    if np.mean(binary) < 128:
        binary = cv2.bitwise_not(binary)
    return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)


def clahe_color(img_bgr):
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(4, 4))
    lab2 = cv2.merge([clahe.apply(l), a, b])
    enhanced = cv2.cvtColor(lab2, cv2.COLOR_LAB2BGR)
    blur = cv2.GaussianBlur(enhanced, (0, 0), 2)
    sharp = np.clip(cv2.addWeighted(enhanced, 2.0, blur, -1.0, 0), 0, 255).astype(np.uint8)
    return sharp


def gray_contrast(img_bgr):
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(6, 6))
    enhanced = clahe.apply(gray)
    return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)


def adaptive_threshold(img_bgr):
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    blur = cv2.medianBlur(gray, 3)
    binary = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 8,
    )
    return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)


def denoise_sharpen(img_bgr):
    """Giảm nhiễu rồi làm nét nhẹ cho ảnh mờ/out-focus."""
    denoised = cv2.fastNlMeansDenoisingColored(img_bgr, None, 6, 6, 7, 21)
    blur = cv2.GaussianBlur(denoised, (0, 0), 1.4)
    sharp = cv2.addWeighted(denoised, 1.8, blur, -0.8, 0)
    return np.clip(sharp, 0, 255).astype(np.uint8)


def blackhat_text_boost(img_bgr):
    """Nhấn mạnh nét chữ tối trên nền men sáng/vàng."""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel)
    boosted = cv2.normalize(blackhat, None, 0, 255, cv2.NORM_MINMAX)
    _, bw = cv2.threshold(boosted, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)


def super_resolve_for_ocr(img_bgr: np.ndarray, scale: float = 2.0) -> np.ndarray:
    """
    Super-resolution nhẹ cho OCR:
    - upscale bằng bicubic
    - khử nhiễu giữ biên
    - tăng tương phản kênh sáng + làm nét nhẹ
    """
    h, w = img_bgr.shape[:2]
    if min(h, w) < 200:
        target = max(300, max(h, w))
        scale = max(scale, target / max(h, w))
    new_w = max(32, int(w * scale))
    new_h = max(32, int(h * scale))
    up = cv2.resize(img_bgr, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

    # Khử nhiễu nhưng giữ contour chữ
    denoise = cv2.bilateralFilter(up, d=7, sigmaColor=50, sigmaSpace=50)

    # CLAHE trên kênh sáng để làm nổi nét mực
    lab = cv2.cvtColor(denoise, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l2 = clahe.apply(l)
    boosted = cv2.cvtColor(cv2.merge([l2, a, b]), cv2.COLOR_LAB2BGR)

    # Unsharp nhẹ
    blur = cv2.GaussianBlur(boosted, (0, 0), 1.2)
    sharp = cv2.addWeighted(boosted, 1.7, blur, -0.7, 0)
    return np.clip(sharp, 0, 255).astype(np.uint8)


def detect_yellow_mark_roi(img_bgr: np.ndarray):
    """
    Tìm vùng bát/đĩa men vàng trong ảnh lớn (kể cả screenshot), sau đó crop ROI
    để OCR không bị loãng do chữ quá nhỏ so với toàn ảnh.
    """
    h, w = img_bgr.shape[:2]
    if h < 300 or w < 300:
        return None

    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    # Dải vàng men gốm thường gặp
    mask = cv2.inRange(hsv, (12, 45, 45), (45, 255, 255))
    mask = cv2.medianBlur(mask, 5)
    kernel = np.ones((7, 7), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    center_x, center_y = w * 0.5, h * 0.5
    best = None
    best_score = -1.0

    for c in contours:
        area = cv2.contourArea(c)
        if area < (h * w) * 0.005:
            continue
        x, y, cw, ch = cv2.boundingRect(c)
        aspect = cw / max(ch, 1)
        if aspect < 0.5 or aspect > 2.2:
            continue
        cx = x + cw * 0.5
        cy = y + ch * 0.5
        # Ưu tiên contour lớn và gần trung tâm khung hình
        dist = ((cx - center_x) ** 2 + (cy - center_y) ** 2) ** 0.5
        dist_norm = dist / (max(w, h) + 1e-6)
        score = (area / (h * w)) * 2.4 + (1.0 - min(1.0, dist_norm))
        if score > best_score:
            best_score = score
            best = (x, y, cw, ch)

    if not best:
        return None

    x, y, cw, ch = best
    pad_x = int(cw * 0.18)
    pad_y = int(ch * 0.18)
    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)
    x2 = min(w, x + cw + pad_x)
    y2 = min(h, y + ch + pad_y)
    roi = img_bgr[y1:y2, x1:x2]
    if roi.size == 0:
        return None
    return roi


def detect_inner_mark_circle_roi(img_bgr: np.ndarray):
    """
    Dò vòng tròn đáy bát (concentric ring) và cắt vùng trung tâm chứa hiệu đề.
    Hữu ích khi chữ rất nhỏ trong ảnh toàn cảnh.
    """
    h, w = img_bgr.shape[:2]
    if h < 220 or w < 220:
        return None

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (9, 9), 1.6)
    circles = cv2.HoughCircles(
        gray,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=min(h, w) * 0.20,
        param1=120,
        param2=28,
        minRadius=int(min(h, w) * 0.06),
        maxRadius=int(min(h, w) * 0.42),
    )
    if circles is None:
        return None

    circles = np.round(circles[0]).astype(int)
    cx0, cy0 = w * 0.5, h * 0.5
    best = None
    best_score = -1.0
    for (x, y, r) in circles:
        if r <= 10:
            continue
        # Ưu tiên vòng gần trung tâm ảnh
        dist = ((x - cx0) ** 2 + (y - cy0) ** 2) ** 0.5
        dist_norm = dist / (max(h, w) + 1e-6)
        size_bonus = min(1.0, r / (min(h, w) * 0.25))
        score = (1.0 - min(1.0, dist_norm)) * 1.3 + size_bonus
        if score > best_score:
            best_score = score
            best = (x, y, r)
    if best is None:
        return None

    x, y, r = best
    # Crop sát vùng chữ trong lòng vòng tròn
    inner = int(max(18, r * 0.62))
    x1 = max(0, x - inner)
    y1 = max(0, y - inner)
    x2 = min(w, x + inner)
    y2 = min(h, y + inner)
    roi = img_bgr[y1:y2, x1:x2]
    if roi.size == 0:
        return None
    return roi


def detect_center_square_roi(img_bgr: np.ndarray):
    """
    Try to locate the small square cartouche at the center of the base.
    Useful when the mark is tiny and surrounded by a larger circular ring.
    """
    h, w = img_bgr.shape[:2]
    if h < 120 or w < 120:
        return None

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    kernel = np.ones((3, 3), np.uint8)
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, kernel, iterations=1)
    bw = cv2.morphologyEx(bw, cv2.MORPH_DILATE, kernel, iterations=1)

    contours, _ = cv2.findContours(bw, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    cx0, cy0 = w * 0.5, h * 0.5
    best = None
    best_score = -1.0
    min_area = (h * w) * 0.001
    max_area = (h * w) * 0.08

    for c in contours:
        x, y, cw, ch = cv2.boundingRect(c)
        area = cw * ch
        if area < min_area or area > max_area:
            continue
        aspect = cw / max(ch, 1)
        if aspect < 0.7 or aspect > 1.4:
            continue
        cx = x + cw * 0.5
        cy = y + ch * 0.5
        dist = ((cx - cx0) ** 2 + (cy - cy0) ** 2) ** 0.5
        dist_norm = dist / (max(h, w) + 1e-6)
        score = (area / (h * w)) * 2.0 + (1.0 - min(1.0, dist_norm))
        if score > best_score:
            best_score = score
            best = (x, y, cw, ch)

    if not best:
        return None

    x, y, cw, ch = best
    pad_x = int(cw * 0.20)
    pad_y = int(ch * 0.20)
    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)
    x2 = min(w, x + cw + pad_x)
    y2 = min(h, y + ch + pad_y)
    roi = img_bgr[y1:y2, x1:x2]
    if roi.size == 0:
        return None
    return roi


def extract_center_box_roi(img_bgr: np.ndarray, ratio: float = 0.22):
    """
    Simple center crop box without thresholding, useful when square mark is tiny
    and segmentation introduces blur.
    """
    h, w = img_bgr.shape[:2]
    if h < 80 or w < 80:
        return None
    box = int(min(h, w) * ratio)
    if box < 24:
        return None
    pad = int(box * 0.18)
    cx, cy = w // 2, h // 2
    x1 = max(0, cx - box // 2 - pad)
    y1 = max(0, cy - box // 2 - pad)
    x2 = min(w, cx + box // 2 + pad)
    y2 = min(h, cy + box // 2 + pad)
    roi = img_bgr[y1:y2, x1:x2]
    if roi.size == 0:
        return None
    return roi


def detect_ink_text_roi(img_bgr: np.ndarray):
    """
    Dò trực tiếp vùng mực chữ (đỏ hoặc đen) để tách ROI chữ khỏi nền bát.
    Hiệu quả cho ảnh nền trắng/vàng có chữ nhỏ.
    """
    h, w = img_bgr.shape[:2]
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    red1 = cv2.inRange(hsv, (0, 55, 45), (15, 255, 255))
    red2 = cv2.inRange(hsv, (160, 55, 45), (180, 255, 255))
    red_mask = cv2.bitwise_or(red1, red2)

    dark_mask = cv2.inRange(gray, 0, 110)
    mask = cv2.bitwise_or(red_mask, dark_mask)

    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel, iterations=2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    cx0, cy0 = w * 0.5, h * 0.5
    pts = []
    for c in contours:
        x, y, cw, ch = cv2.boundingRect(c)
        area = cw * ch
        if area < (h * w) * 0.00012 or area > (h * w) * 0.08:
            continue
        cx = x + cw * 0.5
        cy = y + ch * 0.5
        dist = ((cx - cx0) ** 2 + (cy - cy0) ** 2) ** 0.5
        if dist > max(h, w) * 0.42:
            continue
        pts.append((x, y, cw, ch))

    if not pts:
        return None

    x1 = max(0, min(p[0] for p in pts) - 18)
    y1 = max(0, min(p[1] for p in pts) - 18)
    x2 = min(w, max(p[0] + p[2] for p in pts) + 18)
    y2 = min(h, max(p[1] + p[3] for p in pts) + 18)

    if x2 - x1 < 20 or y2 - y1 < 20:
        return None
    roi = img_bgr[y1:y2, x1:x2]
    if roi.size == 0:
        return None
    return roi


def auto_detect_text_region(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    margin_h = int(h * 0.15)
    margin_w = int(w * 0.15)
    inner = gray[margin_h:h - margin_h, margin_w:w - margin_w]

    best_crop = None
    best_area = 0
    real_coords = None

    for thresh_val in [60, 80, 100, 120]:
        _, dark_mask = cv2.threshold(inner, thresh_val, 255, cv2.THRESH_BINARY_INV)
        kernel = np.ones((5, 5), np.uint8)
        dark_mask = cv2.dilate(dark_mask, kernel, iterations=3)
        contours, _ = cv2.findContours(dark_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue
        min_area = (inner.shape[0] * inner.shape[1]) * 0.005
        valid = [c for c in contours if cv2.contourArea(c) > min_area]
        if not valid:
            continue
        all_points = np.vstack(valid)
        x, y, fw, fh = cv2.boundingRect(all_points)
        area = fw * fh
        if area > best_area:
            best_area = area
            pad_x = int(fw * 0.25)
            pad_y = int(fh * 0.25)
            x1 = max(0, x - pad_x)
            y1 = max(0, y - pad_y)
            x2 = min(inner.shape[1], x + fw + pad_x)
            y2 = min(inner.shape[0], y + fh + pad_y)
            # Tạo crop rộng hơn một chút phòng dính nét
            pad = 20
            y1_p = max(0, y1 - pad)
            y2_p = min(inner.shape[0], y2 + pad)
            x1_p = max(0, x1 - pad)
            x2_p = min(inner.shape[1], x2 + pad)
            best_crop = inner[y1_p:y2_p, x1_p:x2_p]
            real_coords = (x1_p + margin_w, y1_p + margin_h, x2_p + margin_w, y2_p + margin_h)

    if best_crop is None:
        cx1, cy1 = int(w * 0.2), int(h * 0.2)
        cx2, cy2 = int(w * 0.8), int(h * 0.8)
        best_crop = gray[cy1:cy2, cx1:cx2]
        real_coords = (cx1, cy1, cx2, cy2)

    crop_bgr = cv2.cvtColor(best_crop, cv2.COLOR_GRAY2BGR)
    return crop_bgr, real_coords


# ============================================================
# Sắp xếp block theo thứ tự đọc hiệu đề (cột dọc RTL)
# ============================================================
def sort_blocks_vertical_rtl(ocr_lines: List, x_tolerance: int = 30) -> List:
    if not ocr_lines:
        return []
    blocks: List[Tuple[float, float, list]] = []
    for line in ocr_lines:
        box = line[0]
        cx = sum(p[0] for p in box) / 4.0
        cy = sum(p[1] for p in box) / 4.0
        blocks.append((cx, cy, line))
    blocks.sort(key=lambda b: -b[0])
    columns: List[List[Tuple[float, float, list]]] = []
    for cx, cy, line in blocks:
        placed = False
        for col in columns:
            col_x_avg = sum(b[0] for b in col) / len(col)
            if abs(cx - col_x_avg) <= x_tolerance:
                col.append((cx, cy, line))
                placed = True
                break
        if not placed:
            columns.append([(cx, cy, line)])
    columns.sort(key=lambda col: -(sum(b[0] for b in col) / len(col)))
    sorted_lines = []
    for col in columns:
        col.sort(key=lambda b: b[1])
        for _, _, line in col:
            sorted_lines.append(line)
    return sorted_lines


# ============================================================
# Chạy OCR trên 1 ảnh — trả về (text, score tổng hợp)
# FIX 3: Có thêm score = len(text) * avg_conf để chọn kết quả tốt hơn
# ============================================================
def run_ocr(img: np.ndarray, name: str = "") -> Tuple[str, float]:
    """
    Returns:
        (chu_han_string, quality_score)
        quality_score = tổng conf * len → ưu tiên kết quả nhiều chữ VÀ tin cậy cao
    """
    try:
        safe_img = _safe_resize(img)
        h, w = safe_img.shape[:2]
        use_tiny_det = min(h, w) < 280 or name == "tiny_upscale"
        old_limit = getattr(ocr, "det_limit_side_len", None)
        if use_tiny_det:
            try:
                ocr.det_limit_side_len = 32
            except Exception:
                pass
        result = ocr.ocr(safe_img, cls=True)
        if use_tiny_det and old_limit is not None:
            try:
                ocr.det_limit_side_len = old_limit
            except Exception:
                pass

        if not result or result[0] is None or len(result[0]) == 0:
            print(f"  [{name}]: Không phát hiện chữ nào")
            return "", 0.0

        lines = result[0]
        h, w = safe_img.shape[:2]
        x_tolerance = max(30, min(120, int(w * 0.05)))
        sorted_lines = sort_blocks_vertical_rtl(lines, x_tolerance=x_tolerance)

        all_chinese = ""
        total_conf = 0.0
        char_count = 0

        fallback_pool = []
        for line in sorted_lines:
            text = line[1][0]
            conf = line[1][1]
            chars = re.sub(r"[^\u4e00-\u9fff]", "", text)
            if chars:
                fallback_pool.append((chars, conf))

            # Pass 1: ngưỡng chuẩn - kiểm tra strict hơn cho ký tự tương tự
            required_conf = _get_required_confidence(chars)
            if conf < required_conf:
                print(f"    -> SKIP '{text}' conf={conf:.2f} (< required {required_conf:.2f})")
                continue

            if chars:
                all_chinese += chars
                total_conf += conf * len(chars)
                char_count += len(chars)
                print(f"    -> '{chars}' conf={conf:.2f} (required: {required_conf:.2f})")

        # Pass 2: ảnh mờ - nếu chưa lấy được gì, nới ngưỡng nhưng vẫn kiểm tra ký tự tương tự.
        if not all_chinese and fallback_pool:
            for chars, conf in fallback_pool:
                if conf < MIN_CONF_FALLBACK:
                    continue
                # Để fallback vẫn strict cho ký tự tương tự/nguy hiểm
                required_conf = _get_required_confidence(chars)
                if conf < required_conf:
                    continue
                all_chinese += chars
                total_conf += conf * len(chars)
                char_count += len(chars)
                print(f"    -> fallback '{chars}' conf={conf:.2f} (required: {required_conf:.2f})")

        quality = total_conf  # sum(conf * char_len) — thưởng cả số chữ lẫn conf
        return all_chinese, quality

    except Exception as e:
        print(f"  OCR error [{name}]: {e}")
        return "", 0.0


# ============================================================
# Kiểm tra xem ảnh có phải ảnh gốm sứ với hiệu đề không
# ============================================================
def is_ceramic_mark_image(img: np.ndarray) -> bool:
    """
    CÙNG CẮT: Chỉ accept ảnh hiệu đề HOÀN HẢO.
    Reject tất cả ảnh tượng, con người, hoa văn phức tạp.
    
    Returns:
        bool: True ONLY nếu 100% confirm là mark
    """
    try:
        h, w = img.shape[:2]
        
        # Size check
        if h < 150 or w < 150 or h > 2400 or w > 2400:
            print("[VALIDATION] ❌ Size reject")
            return False
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # === STEP 1: KIỂM TRA KẾT CẤU ===
        # Tính Laplacian để đo độ chi tiết
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        texture_score = np.mean(np.abs(laplacian))
        
        # NGẶT: texture > 5.0 = reject ngay (không phải mark)
        if texture_score > 45.0:
            print(f"[VALIDATION] Reject: texture too high ({texture_score:.2f})")
            return False
        if texture_score > 5.0:
            print(f"[VALIDATION] Texture high but continuing ({texture_score:.2f})")
        
        # === STEP 2: BINARY THRESHOLD NGẶT ===
        # Chỉ lấy pixel RẤT tối (< 100)
        _, binary = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)
        
        # Xóa nhiễu MẠNH
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=3)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
        
        # === STEP 3: TÌM CONTOUR ===
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours or len(contours) == 0:
            print("[VALIDATION] No contours found; allowing OCR fallback")
            return texture_score < 25.0
        
        # === STEP 4: FILTER CONTOUR NGẶT ===
        char_regions = []
        for c in contours:
            area = cv2.contourArea(c)
            if area < 150:  # quá nhỏ
                continue
            if area > (h * w) * 0.08:  # quá lớn
                continue
            
            x, y, cw, ch = cv2.boundingRect(c)
            aspect = cw / max(ch, 1)
            
            # Aspect ratio NGẶT
            if aspect < 0.5 or aspect > 2.0:
                continue
            
            # Solidity NGẶT (> 0.5)
            hull = cv2.convexHull(c)
            hull_area = cv2.contourArea(hull)
            if hull_area > 0:
                solidity = area / hull_area
                if solidity < 0.50:  # NGẶT
                    continue
            
            char_regions.append((x, y, cw, ch, area, solidity))
        
        num_chars = len(char_regions)
        print(f"[VALIDATION] Found {num_chars} chars")
        
        # === STEP 5: SỐ LƯỢNG NGẶT ===
        # Hiệu đề: 2-6 ký tự (KHÔNG 7-8)
        if num_chars < 1:
            print(f"[VALIDATION] ❌ Char count invalid: {num_chars}")
            return texture_score < 25.0
        if num_chars > 18:
            print(f"[VALIDATION] Many contours ({num_chars}); allowing OCR fallback")
        
        # === STEP 6: KIỂM TRA ALIGNMENT NGẶT ===
        ys = [r[1] for r in char_regions]
        y_std = np.std(ys)
        avg_height = np.mean([r[3] for r in char_regions])
        
        # Y alignment NGẶT: y_std < 15% height
        if y_std > avg_height * 0.18:
            print(f"[VALIDATION] Y alignment loose for vertical mark: std={y_std:.1f}")
        
        # === STEP 7: KẾ THỐNG KHOẢNG CÁCH ===
        xs = sorted([r[0] for r in char_regions])
        x_gaps = [xs[i+1] - xs[i] for i in range(len(xs)-1)] if len(xs) > 1 else []
        
        if x_gaps:
            min_gap = min(x_gaps)
            avg_width = np.mean([r[2] for r in char_regions])
            
            # Khoảng cách tối thiểu > 20% width
            if min_gap < avg_width * 0.18:
                print(f"[VALIDATION] Close character contours: gap={min_gap:.0f}")
        
        # === STEP 8: KIỂM TRA TỈ LỆ ===
        min_x = min(r[0] for r in char_regions)
        max_x = max(r[0] + r[2] for r in char_regions)
        min_y = min(r[1] for r in char_regions)
        max_y = max(r[1] + r[3] for r in char_regions)
        
        text_width = max_x - min_x
        text_height = max_y - min_y
        text_area = text_width * text_height
        image_area = h * w
        text_ratio = text_area / image_area
        
        # Hiệu đề trong ảnh gốc thường nhỏ, nhưng ảnh upload có thể là crop cận
        # cảnh/screenshot đã phóng to. Không loại các ảnh này chỉ vì chữ lớn.
        if text_ratio < 0.0002:
            print(f"[VALIDATION] ❌ Text too small: {text_ratio:.4f}")
            return False
        if text_ratio > 0.65:
            print(f"[VALIDATION] ❌ Text dominates image: {text_ratio:.4f}")
            return False
        if text_ratio > 0.25:
            print(f"[VALIDATION] Text large/cropped but allowed: {text_ratio:.4f}")
        
        # === STEP 9: KIỂM TRA VÀNH TRÒN ===
        blurred = cv2.GaussianBlur(gray, (13, 13), 2)
        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=min(h, w) * 0.25,
            param1=140,
            param2=30,
            minRadius=int(min(h, w) * 0.12),
            maxRadius=int(min(h, w) * 0.42),
        )
        
        has_circle = circles is not None and len(circles[0]) > 0
        
        # === STEP 10: VỊ TRÍ ===
        text_center_x = (min_x + max_x) * 0.5
        text_center_y = (min_y + max_y) * 0.5
        
        img_center_x = w * 0.5
        img_center_y = h * 0.5
        
        dist = ((text_center_x - img_center_x) ** 2 + (text_center_y - img_center_y) ** 2) ** 0.5
        
        is_centered = dist < max(h, w) * 0.35
        is_bottom = text_center_y > h * 0.58 and text_center_y < h * 0.85
        
        # === KẾT LUẬN ===
        if has_circle:
            print("[VALIDATION] ✅ PASS: Has circle base")
            return True
        
        if is_centered or is_bottom:
            print(f"[VALIDATION] ✅ PASS: Position OK (centered:{is_centered}, bottom:{is_bottom})")
            return True
        
        print(f"[VALIDATION] ❌ Position bad (dist:{dist:.0f})")
        return False
        
    except Exception as e:
        print(f"[VALIDATION] ❌ Exception: {str(e)[:100]}")
        return False


# ============================================================
# Hàm chính: đọc hiệu đề từ ảnh gốm sứ
# ============================================================
def read_chinese_mark(img_bytes: bytes, deep_mode: bool = False, cancel_event=None) -> dict:
    try:
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return {"error": "Invalid image format"}

        # === VALIDATION: chỉ dùng làm tín hiệu cảnh báo, không chặn OCR ===
        validation_warning = ""
        if not is_ceramic_mark_image(img):
            validation_warning = (
                "Ảnh không giống bố cục hiệu đề chuẩn, hệ thống vẫn thử OCR "
                "vì có thể là ảnh crop cận cảnh hoặc screenshot."
            )
            print(f"[VALIDATION] ⚠ {validation_warning}")

        # Phát hiện và xử lý ảnh Google Search
        if detect_google_image(img):
            print("[Google Image Detected] Áp dụng preprocessing tối ưu...")
            img = preprocess_google_image(img)

        img = remove_red_stamp(img)
        cv2.imwrite(os.path.join(DEBUG_DIR, "00_original.jpg"), img)
        roi_candidate = detect_yellow_mark_roi(img)
        circle_roi = detect_inner_mark_circle_roi(img)
        ink_roi = detect_ink_text_roi(img)
        square_roi = None
        if circle_roi is not None:
            square_roi = detect_center_square_roi(circle_roi)
        if square_roi is None:
            square_roi = detect_center_square_roi(img)
        center_box_roi = extract_center_box_roi(img, ratio=0.22)
        center_box_roi_small = extract_center_box_roi(img, ratio=0.16)
        if roi_candidate is not None:
            try:
                cv2.imwrite(os.path.join(DEBUG_DIR, "01_roi_candidate.jpg"), roi_candidate)
            except Exception:
                pass
        if circle_roi is not None:
            try:
                cv2.imwrite(os.path.join(DEBUG_DIR, "01_circle_roi.jpg"), circle_roi)
            except Exception:
                pass
        if square_roi is not None:
            try:
                cv2.imwrite(os.path.join(DEBUG_DIR, "01_square_roi.jpg"), square_roi)
            except Exception:
                pass
        if center_box_roi is not None:
            try:
                cv2.imwrite(os.path.join(DEBUG_DIR, "01_center_box_roi.jpg"), center_box_roi)
            except Exception:
                pass
        if ink_roi is not None:
            try:
                cv2.imwrite(os.path.join(DEBUG_DIR, "01_ink_roi.jpg"), ink_roi)
            except Exception:
                pass

        # FIX 2: Chỉ crop nếu ảnh chưa zoom sẵn
        img_raw = img.copy()
        _ = auto_center_crop(img_raw, save_debug=True)

        # Upscale nếu ảnh nhỏ
        h, w = img.shape[:2]
        if max(h, w) < 1600:
            scale = 1600 / max(h, w)
            img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
            h, w = img.shape[:2]

        # FIX 2: Dùng _is_already_zoomed để quyết định có crop không
        img_center = auto_center_crop(img, save_debug=False)
        text_region_center, _ = auto_detect_text_region(img_center)
        text_region_full, _ = auto_detect_text_region(img)

        # CROP ÉP BUỘC: Đề phòng viền tối ở background gây nhầm lẫn là zoom
        h_f, w_f = img.shape[:2]
        forced_center = img[int(h_f*0.25):int(h_f*0.75), int(w_f*0.25):int(w_f*0.75)]
        text_region_forced, _ = auto_detect_text_region(forced_center)

        variants = {}

        tr_h, tr_w = text_region_center.shape[:2]
        if tr_h > 0 and tr_w > 0:
            scale1 = max(1.5, 2400.0 / max(tr_h, tr_w))
            big_center = cv2.resize(
                text_region_center,
                (int(tr_w * scale1), int(tr_h * scale1)),
                interpolation=cv2.INTER_LANCZOS4,
            )
            variants["center_clahe"] = clahe_color(big_center)
            variants["center_gray"] = gray_contrast(big_center)
            variants["center_adapt"] = adaptive_threshold(big_center)
            variants["center_denoise"] = denoise_sharpen(big_center)
            variants["center_blackhat"] = blackhat_text_boost(big_center)

        tr_h2, tr_w2 = text_region_full.shape[:2]
        if tr_h2 > 0 and tr_w2 > 0:
            scale2 = max(1.2, 2000.0 / max(tr_h2, tr_w2))
            big_full = cv2.resize(
                text_region_full,
                (int(tr_w2 * scale2), int(tr_h2 * scale2)),
                interpolation=cv2.INTER_LANCZOS4,
            )
            variants["full_raw"] = big_full
            variants["full_blue"] = blue_channel_best(big_full)
            variants["full_adapt"] = adaptive_threshold(big_full)
            variants["full_denoise"] = denoise_sharpen(big_full)

        tr_h3, tr_w3 = text_region_forced.shape[:2]
        if tr_h3 > 0 and tr_w3 > 0:
            scale3 = max(1.5, 2400.0 / max(tr_h3, tr_w3))
            big_forced = cv2.resize(
                text_region_forced,
                (int(tr_w3 * scale3), int(tr_h3 * scale3)),
                interpolation=cv2.INTER_LANCZOS4,
            )
            variants["forced_raw"] = big_forced
            variants["forced_red"] = red_channel_best(big_forced)
            variants["forced_gray"] = gray_contrast(big_forced)
            variants["forced_blackhat"] = blackhat_text_boost(big_forced)

        # Bổ sung một variant: Không dùng auto_detect_text_region, chỉ Crop cố định ngay lõi trung tâm (35% - 65%)
        # Đề phòng auto_detect_text_region bắt nhầm vành bát thay vì chữ
        h_ct, w_core = img.shape[:2]
        core_crop = img[int(h_ct*0.35):int(h_ct*0.65), int(w_core*0.35):int(w_core*0.65)]
        scale4 = max(1.5, 2000.0 / max(core_crop.shape[0], core_crop.shape[1]))
        big_core = cv2.resize(
            core_crop, 
            (int(core_crop.shape[1] * scale4), int(core_crop.shape[0] * scale4)),
            interpolation=cv2.INTER_LANCZOS4,
        )
        variants["core_raw"] = big_core
        variants["core_red"] = red_channel_best(big_core)
        variants["core_clahe"] = clahe_color(big_core)
        variants["core_denoise"] = denoise_sharpen(big_core)

        # Tiny-text fallback: quét cửa sổ trung tâm, phóng đại rất mạnh.
        # Dành cho ảnh mà hiệu đề chỉ chiếm vài % khung hình.
        for i, ratio in enumerate([0.58, 0.45]):
            x1 = int((1.0 - ratio) * 0.5 * w)
            y1 = int((1.0 - ratio) * 0.5 * h)
            x2 = int((1.0 + ratio) * 0.5 * w)
            y2 = int((1.0 + ratio) * 0.5 * h)
            tiny = img[y1:y2, x1:x2]
            if tiny.size == 0:
                continue
            th, tw = tiny.shape[:2]
            scale_tiny = max(1.9, 2400.0 / max(th, tw))
            tiny_big = cv2.resize(
                tiny,
                (int(tw * scale_tiny), int(th * scale_tiny)),
                interpolation=cv2.INTER_LANCZOS4,
            )
            variants[f"tiny_{i}_raw"] = tiny_big
            variants[f"tiny_{i}_gray"] = gray_contrast(tiny_big)
            variants[f"tiny_{i}_denoise"] = denoise_sharpen(tiny_big)
            variants[f"tiny_{i}_blackhat"] = blackhat_text_boost(tiny_big)
            variants[f"tiny_{i}_adapt"] = adaptive_threshold(tiny_big)

        # Fallback quan trọng cho ảnh screenshot: OCR trên ROI bát vàng.
        if roi_candidate is not None:
            rh, rw = roi_candidate.shape[:2]
            scale_roi = max(1.6, 2600.0 / max(rh, rw))
            roi_big = cv2.resize(
                roi_candidate,
                (int(rw * scale_roi), int(rh * scale_roi)),
                interpolation=cv2.INTER_LANCZOS4,
            )
            roi_text_region, _ = auto_detect_text_region(roi_big)
            variants["roi_raw"] = roi_big
            variants["roi_gray"] = gray_contrast(roi_big)
            variants["roi_blackhat"] = blackhat_text_boost(roi_big)
            variants["roi_denoise"] = denoise_sharpen(roi_big)
            variants["roi_text_adapt"] = adaptive_threshold(roi_text_region)

        # Fallback vòng tròn đáy bát: ưu tiên chữ nhỏ nằm giữa tâm.
        if circle_roi is not None:
            ch, cw = circle_roi.shape[:2]
            scale_c = max(1.8, 2200.0 / max(ch, cw))
            circle_big = cv2.resize(
                circle_roi,
                (int(cw * scale_c), int(ch * scale_c)),
                interpolation=cv2.INTER_LANCZOS4,
            )
            circle_text_region, _ = auto_detect_text_region(circle_big)
            variants["circle_raw"] = circle_big
            variants["circle_gray"] = gray_contrast(circle_big)
            variants["circle_blue"] = blue_channel_best(circle_big)
            variants["circle_denoise"] = denoise_sharpen(circle_big)
            variants["circle_blackhat"] = blackhat_text_boost(circle_big)
            variants["circle_text_adapt"] = adaptive_threshold(circle_text_region)
            try:
                cbh, cbw = circle_big.shape[:2]
                margin_y = int(cbh * 0.17)
                margin_x = int(cbw * 0.17)
                circle_core = circle_big[margin_y:cbh - margin_y, margin_x:cbw - margin_x]
                if circle_core.size:
                    variants["circle_core_raw"] = circle_core
                    variants["circle_core_gray"] = gray_contrast(circle_core)
                    variants["circle_core_blue"] = blue_channel_best(circle_core)
            except Exception:
                pass

        for name, roi in (("center_box", center_box_roi), ("center_box_small", center_box_roi_small)):
            if roi is None:
                continue
            bh, bw = roi.shape[:2]
            scale_b = max(3.0, 3200.0 / max(bh, bw))
            box_big = cv2.resize(
                roi,
                (int(bw * scale_b), int(bh * scale_b)),
                interpolation=cv2.INTER_LANCZOS4,
            )
            variants[f"{name}_raw"] = box_big
            variants[f"{name}_gray"] = gray_contrast(box_big)
            variants[f"{name}_blue"] = blue_channel_best(box_big)
            variants[f"{name}_denoise"] = denoise_sharpen(box_big)
            variants[f"{name}_blackhat"] = blackhat_text_boost(box_big)

        if square_roi is not None:
            sh, sw = square_roi.shape[:2]
            scale_s = max(2.6, 3000.0 / max(sh, sw))
            square_big = cv2.resize(
                square_roi,
                (int(sw * scale_s), int(sh * scale_s)),
                interpolation=cv2.INTER_LANCZOS4,
            )
            variants["square_raw"] = square_big
            variants["square_gray"] = gray_contrast(square_big)
            variants["square_adapt"] = adaptive_threshold(square_big)
            variants["square_blackhat"] = blackhat_text_boost(square_big)

        # Tiny upscale variant: aggressive zoom + unsharp for very small marks
        try:
            tiny_up = cv2.resize(img, None, fx=4.0, fy=4.0, interpolation=cv2.INTER_LANCZOS4)
            blur = cv2.GaussianBlur(tiny_up, (0, 0), 1.6)
            sharp = cv2.addWeighted(tiny_up, 1.6, blur, -0.6, 0)
            variants["tiny_upscale"] = np.clip(sharp, 0, 255).astype(np.uint8)
        except Exception:
            pass

        if ink_roi is not None:
            ih, iw = ink_roi.shape[:2]
            scale_i = max(2.4, 2600.0 / max(ih, iw))
            ink_big = cv2.resize(
                ink_roi,
                (int(iw * scale_i), int(ih * scale_i)),
                interpolation=cv2.INTER_CUBIC,
            )
            variants["ink_raw"] = ink_big
            variants["ink_gray"] = gray_contrast(ink_big)
            variants["ink_denoise"] = denoise_sharpen(ink_big)
            variants["ink_blackhat"] = blackhat_text_boost(ink_big)

        # Chỉ bật khi người dùng chọn deep mode: SR variants cho ảnh cực mờ/chữ nhỏ.
        if deep_mode:
            try:
                sr_core = super_resolve_for_ocr(big_core, scale=2.2)
                variants["sr_core_raw"] = sr_core
                variants["sr_core_gray"] = gray_contrast(sr_core)
                variants["sr_core_blackhat"] = blackhat_text_boost(sr_core)
            except Exception:
                pass

            if roi_candidate is not None:
                try:
                    sr_roi = super_resolve_for_ocr(roi_candidate, scale=2.6)
                    variants["sr_roi_raw"] = sr_roi
                    variants["sr_roi_denoise"] = denoise_sharpen(sr_roi)
                    variants["sr_roi_adapt"] = adaptive_threshold(sr_roi)
                except Exception:
                    pass

            if circle_roi is not None:
                try:
                    sr_circle = super_resolve_for_ocr(circle_roi, scale=2.8)
                    variants["sr_circle_raw"] = sr_circle
                    variants["sr_circle_gray"] = gray_contrast(sr_circle)
                    variants["sr_circle_blackhat"] = blackhat_text_boost(sr_circle)
                except Exception:
                    pass

            # Invert fallback for dark background or inverted marks
            try:
                variants["invert_core"] = cv2.bitwise_not(big_core)
            except Exception:
                pass
            if square_roi is not None:
                try:
                    variants["invert_square"] = cv2.bitwise_not(square_big)
                except Exception:
                    pass

        # Ưu tiên ROI vòng tròn / mực chữ (đáy sứ) trước crop 25–75% để tránh OCR lộn khi chữ xếp 2 cột.
        priority_names = [
            "center_box_raw", "center_box_gray", "center_box_blue", "center_box_denoise", "center_box_blackhat",
            "center_box_small_raw", "center_box_small_gray", "center_box_small_blue", "center_box_small_denoise", "center_box_small_blackhat",
            "circle_core_blue", "circle_core_gray", "circle_core_raw",
            "tiny_upscale",
            "square_raw", "square_gray", "square_adapt", "square_blackhat",
            "circle_raw", "circle_blue", "circle_denoise", "circle_gray", "circle_blackhat", "circle_text_adapt",
            "ink_raw", "ink_gray", "ink_denoise", "ink_blackhat",
            "center_clahe", "center_gray", "center_denoise",
            "full_raw", "full_denoise", "full_blue",
            "forced_raw", "forced_gray",
            "core_raw", "core_denoise",
            "roi_raw", "roi_denoise", "roi_gray",
            "sr_core_raw", "sr_core_gray",
            "sr_roi_raw", "sr_roi_denoise",
            "sr_circle_raw", "sr_circle_gray",
            "invert_core", "invert_square",
        ]
        ordered_variants = []
        seen = set()
        for name in priority_names:
            if name in variants:
                ordered_variants.append((name, variants[name]))
                seen.add(name)
        for name, img_v in variants.items():
            if name not in seen:
                ordered_variants.append((name, img_v))

        # FIX 3 & 5: Thu thập tất cả (text, score) từ các variant
        all_candidates = []
        variant_results = []

        base_fast_limit = MAX_VARIANTS_PER_REQUEST + (2 if deep_mode else 0)
        base_deep_extra = DEEP_EXTRA_VARIANTS + (4 if deep_mode else 0)
        fast_phase_cut = min(base_fast_limit, len(ordered_variants))
        deep_phase_cut = min(len(ordered_variants), fast_phase_cut + base_deep_extra)

        # Smart skip: theo dõi các prefix ROI liên tiếp không đọc được
        _empty_streak = {}  # prefix -> số lần liên tiếp không đọc được
        _SKIP_THRESHOLD = 2  # Skip các variant cùng prefix nếu 2 liên tiếp rỗng

        for idx, (vname, vimg) in enumerate(ordered_variants[:fast_phase_cut]):
            if cancel_event and cancel_event.is_set():
                print(f"  [{vname}] SKIPPED (Client disconnected)")
                break
            # Smart skip: nếu cùng 1 ROI prefix đã trống 2 lần liên tiếp, bỏ qua
            prefix = vname.rsplit('_', 1)[0] if '_' in vname else vname
            if _empty_streak.get(prefix, 0) >= _SKIP_THRESHOLD:
                print(f"  [{vname}] SKIPPED (prefix '{prefix}' empty {_empty_streak[prefix]}x)")
                continue

            if SAVE_DEBUG_VARIANTS:
                cv2.imwrite(os.path.join(DEBUG_DIR, f"03_{vname}.jpg"), vimg)
            text, score = run_ocr(vimg, vname)
            if text:
                all_candidates.append(text)
                variant_results.append((text, score, vname))
                print(f"  [{vname}] text='{text}' score={score:.2f}")
                _empty_streak[prefix] = 0  # reset streak
                # Dừng sớm: KHÔNG yêu cầu _plausible (để dừng cho cả hiệu đề Nội Phủ, Khánh Xuân...)
                cjk_len = len(re.sub(r"[^\u4e00-\u9fff]", "", text))
                if (
                    score >= EARLY_ACCEPT_SCORE
                    and len(text) >= EARLY_ACCEPT_LEN
                    and not _is_incomplete_dynasty_mark(text)
                    and cjk_len >= 4  # Không dừng sớm nếu chưa đủ 4 ký tự CJK
                ):
                    print(f"  [early-stop] accept '{text}' from '{vname}' score={score:.2f}")
                    break
            else:
                _empty_streak[prefix] = _empty_streak.get(prefix, 0) + 1

        # Nếu pass nhanh không đủ thông tin thì mới chạy pass sâu (nặng hơn) cho ảnh mờ.
        fast_texts = [t for t, _, _ in variant_results]
        best_len_fast = max((len(re.sub(r"[^\u4e00-\u9fff]", "", t or "")) for t in fast_texts), default=0)
        fast_canonical = [_canonicalize_reign_mark_text(t) for t in fast_texts]
        has_complete_fast = any(
            len(re.sub(r"[^\u4e00-\u9fff]", "", t or "")) >= 6 and _plausible_reign_ocr_string(t)
            for t in fast_canonical
        )
        has_reign_signal_fast = any(
            any(ch in t for ch in "大明清南萬曆年製造光緒康熙乾隆嘉慶宣統")
            for t in fast_canonical
        )
        needs_more_reign_evidence = has_reign_signal_fast and not has_complete_fast and best_len_fast < 6
        if (best_len_fast < 3 or needs_more_reign_evidence) and fast_phase_cut < deep_phase_cut:
            print(f"  [deep-pass] fast result weak/incomplete (len={best_len_fast}), trying extra variants")
            for vname, vimg in ordered_variants[fast_phase_cut:deep_phase_cut]:
                if cancel_event and cancel_event.is_set():
                    print(f"  [{vname}] SKIPPED (Client disconnected)")
                    break
                if SAVE_DEBUG_VARIANTS:
                    cv2.imwrite(os.path.join(DEBUG_DIR, f"03_{vname}.jpg"), vimg)
                text, score = run_ocr(vimg, vname)
                if text:
                    all_candidates.append(text)
                    variant_results.append((text, score, vname))
                    print(f"  [{vname}] text='{text}' score={score:.2f}")
                    deep_cjk_len = len(re.sub(r"[^\u4e00-\u9fff]", "", text))
                    if (
                        score >= EARLY_ACCEPT_SCORE
                        and len(text) >= EARLY_ACCEPT_LEN
                        and not _is_incomplete_dynasty_mark(text)
                        and deep_cjk_len >= 4  # Không dừng sớm nếu chưa đủ 4 ký tự CJK
                    ):
                        print(f"  [deep-early-stop] accept '{text}' from '{vname}' score={score:.2f}")
                        break

        # FIX 3 & 5: Chọn best_text — ưu tiên chuỗi có 年製/年造, rồi mới theo score
        best_text = ""
        best_score = -1.0
        recovered_mark = _derive_ming_wanli_from_ocr_evidence(all_candidates)
        if not recovered_mark:
            recovered_mark = _derive_database_mark_from_ocr_evidence(all_candidates)
        recovered_guangxu = _derive_qing_guangxu_from_ocr_evidence(all_candidates)
        if not recovered_mark:
            recovered_mark = recovered_guangxu
        if variant_results:
            variant_results.sort(key=lambda x: _variant_sort_key(x[0], x[1]))
            best_text, best_score, best_name = variant_results[0]
            print(f"WINNER: '{best_text}' from '{best_name}' score={best_score:.2f}")
        if recovered_mark:
            print(f"[EVIDENCE-RECOVERED] OCR glyph evidence -> '{recovered_mark}'")
            best_text = recovered_mark
            best_score = max(best_score, 5.0)

        print(f"FINAL: '{best_text}'")

        # Chặn kết quả quá ngắn và điểm thấp (thường là ký tự nhiễu đơn lẻ).
        if len(best_text) <= 1 and best_score < 1.3:
            best_text = ""

        if not best_text:
            return {
                "text": "",
                "confidence": 0,
                "candidates": all_candidates,
                "all_results": [],
                "database_valid": False,
                "warning": validation_warning or "OCR không đọc được chữ Hán rõ ràng từ ảnh.",
            }

        # === NEW: Cố gắng sửa chữ OCR nhầm ===
        canonical_text = _canonicalize_reign_mark_text(best_text)
        if canonical_text != best_text:
            print(f"[ORDER-CORRECTED] OCR column order: '{best_text}' -> '{canonical_text}'")
            best_text = canonical_text

        corrected_text = _attempt_ocr_correction(best_text)
        if corrected_text != best_text:
            best_text = corrected_text
            print(f"[AUTO-CORRECTED] OCR nhầm, sửa thành: '{best_text}'")

        # Kiểm tra kết quả với database (bao gồm gợi ý sửa nếu OCR nhầm ký tự)
        db_validation = _validate_against_database(best_text)

        # Confidence estimate dựa trên score tương đối
        max_possible = best_score if best_score > 0 else 1.0
        conf_estimate = min(0.99, best_score / (max_possible + 0.001 * 10))

        # Xây dựng thông điệp cảnh báo chi tiết
        warning_msg = db_validation.get('warning', '')
        if validation_warning and not warning_msg:
            warning_msg = validation_warning
        suggestions = db_validation.get('suggestions', [])
        
        # Nếu có gợi ý (là fuzzy match hoặc không tìm thấy), thêm vào warning
        if suggestions:
            best_suggestion = suggestions[0]
            suggestion_text = best_suggestion.get('entry', {}).get('chu_han', '')
            if suggestion_text:
                warning_msg += f"\n💡 Gợi ý: Có thể là '{suggestion_text}' (score: {best_suggestion.get('score', 0):.2f})"

        return {
            "text": best_text,
            "confidence": round(conf_estimate, 3),
            "candidates": list(dict.fromkeys(all_candidates)),  # deduplicate, giữ thứ tự
            "all_results": [{"text": t, "confidence": s, "variant": n} for t, s, n in variant_results],
            "database_valid": db_validation.get('database_valid', False),
            "warning": warning_msg,
            "best_match": db_validation.get('best_match', None),
            "suggestions": [{"text": s.get('matched_text', ''), "score": s.get('score', 0)} for s in suggestions],
        }

    except Exception as e:
        import traceback
        print("OCR ERROR:", traceback.format_exc())
        return {
            "text": "",
            "confidence": 0,
            "candidates": [],
            "all_results": [],
            "error": str(e),
        }
