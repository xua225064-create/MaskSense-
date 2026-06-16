from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi import Request
from fastapi.staticfiles import StaticFiles
import cv2
import numpy as np
from ocr_engine import read_chinese_mark
import json
import os
import smtplib
from email.message import EmailMessage
from html import escape
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import difflib
import sys
import unicodedata
from reference_matcher import match_image, match_image_by_prefix, save_reference

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

app = FastAPI(title="Chinese Porcelain Reign Mark OCR")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if not os.path.exists("uploads"):
    os.makedirs("uploads")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "hieu_de_database.json")
REFERENCE_LIBRARY_PATH = os.path.join(os.path.dirname(__file__), "data", "reference_library")
PAGE_OVERRIDES_PATH = os.path.join(os.path.dirname(__file__), "data", "page_overrides.json")
WEB_PAGE_IDS = {
    "home",
    "history",
    "library",
    "about",
    "contact",
    "pricing",
    "login",
    "register",
    "profile",
    "tx-history",
    "checkout",
    "guide",
    "privacy",
    "terms",
    "data-deletion",
    "support",
    "faq",
}
MOBILE_SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "hieude_mobile", "src", "screens"))
MOBILE_ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "hieude_mobile", "assets"))
APP_PAGE_FILES = {
    "app-home": "HomeScreen.js",
    "app-login": "LoginScreen.js",
    "app-register": "RegisterScreen.js",
    "app-library": "LibraryScreen.js",
    "app-history": "HistoryScreen.js",
    "app-pricing": "PricingScreen.js",
    "app-checkout": "CheckoutScreen.js",
    "app-profile": "ProfileScreen.js",
    "app-settings": "SettingsScreen.js",
    "app-language": "LanguageScreen.js",
    "app-chat": "ChatScreen.js",
    "app-about": "AboutScreen.js",
    "app-terms": "TermsScreen.js",
    "app-privacy": "PrivacyScreen.js",
}

# Auto-Learning: lưu tạm ảnh vừa phân tích để user xác nhận → lưu vào thư viện tham chiếu
_last_analyzed_images: Dict[str, bytes] = {}


from db import (fetch_all_marks, create_user, get_user_by_username, get_user_by_id, add_scan_history, 
    get_scan_history, get_or_create_social_user, ensure_credits_column, get_user_credits, 
    deduct_credit, add_credits, create_payment, get_payment, get_user_payments, complete_payment,
    ensure_admin_columns, create_admin_account, admin_login, get_all_users_admin,
    toggle_user_lock, admin_update_credits, admin_reset_password, get_all_payments_admin, 
    admin_approve_payment, get_all_scan_history_admin, get_dashboard_stats,
    admin_add_mark, admin_update_mark, admin_delete_mark, get_system_settings, update_system_setting,
    admin_delete_user, SQLITE_DB_PATH, apply_free_credits_to_unpaid_users)
from pydantic import BaseModel
from passlib.context import CryptContext
import httpx
import re

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserRegister(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

def _load_database() -> List[Dict[str, Any]]:
    print("[DB] Loading database...")
    db_marks = fetch_all_marks()
    if db_marks and len(db_marks) > 0:
        print(f"[DB] Successfully loaded {len(db_marks)} marks from SQLite.")
        return _merge_reference_library_entries(db_marks)
        
    print("[DB] SQLite unavailable or empty, falling back to JSON...")
    if not os.path.exists(DATA_PATH):
        return _merge_reference_library_entries([])
    with open(DATA_PATH, "r", encoding="utf-8") as file:
        return _merge_reference_library_entries(json.load(file))


def _merge_reference_library_entries(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged = list(entries or [])
    seen = set()

    def remember(entry: Dict[str, Any]) -> None:
        for target in _get_targets(entry):
            norm = _normalize_cjk(target)
            if norm:
                seen.add(norm)

    for entry in merged:
        remember(entry)

    added = 0
    if os.path.isdir(REFERENCE_LIBRARY_PATH):
        for filename in os.listdir(REFERENCE_LIBRARY_PATH):
            if not filename.lower().endswith(".json"):
                continue
            path = os.path.join(REFERENCE_LIBRARY_PATH, filename)
            try:
                with open(path, "r", encoding="utf-8") as file:
                    ref_entry = json.load(file)
            except Exception as exc:
                print(f"[DB] Skip reference entry {filename}: {exc}")
                continue
            targets = [_normalize_cjk(target) for target in _get_targets(ref_entry)]
            targets = [target for target in targets if target]
            if not targets or any(target in seen for target in targets):
                continue
            merged.append(ref_entry)
            remember(ref_entry)
            added += 1
    if added:
        print(f"[DB] Merged {added} reference-library entries into runtime database.")
    return merged


def _normalize_cjk(value: Optional[str]) -> str:
    if not value:
        return ""
    return "".join(ch for ch in value if "\u4e00" <= ch <= "\u9fff")


def _get_targets(entry: Dict[str, Any]) -> List[str]:
    targets = [entry.get("chu_han"), entry.get("chu_han_4"), entry.get("chu_han_6")]
    variants = entry.get("bien_the") or []
    targets.extend(variants)
    return [item for item in targets if item]


REIGN_DATABASE = _load_database()

# Đảm bảo cột scan_credits tồn tại
ensure_credits_column()

# Khởi tạo hệ thống Admin
ensure_admin_columns()
_admin_hash = pwd_context.hash("123@")
create_admin_account("admin", _admin_hash)
print("[Admin] Admin system initialized.")

# Sync database API keys with config
try:
    settings = get_system_settings()
    import config
    if not config.GEMINI_API_KEY and settings.get("gemini_api_key"):
        config.GEMINI_API_KEY = settings["gemini_api_key"]
        print("[Startup] Synced GEMINI_API_KEY from database because env is empty.")
    elif config.GEMINI_API_KEY:
        print("[Startup] Using GEMINI_API_KEY from environment.")
    if not config.OPENAI_API_KEY and settings.get("openai_api_key"):
        config.OPENAI_API_KEY = settings["openai_api_key"]
        print("[Startup] Synced OPENAI_API_KEY from database because env is empty.")
    elif config.OPENAI_API_KEY:
        print("[Startup] Using OPENAI_API_KEY from environment.")
except Exception as e:
    print(f"[Startup] Error syncing API keys from DB: {e}")


def _find_match(ocr_text: str, database: List[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], str]:
    ocr_clean = _normalize_cjk(ocr_text.strip())
    if not ocr_clean:
        return None, "none"

    if ocr_clean in {"大明年製", "大清年製", "大南年製"}:
        return None, "incomplete"

    # =====================================================
    # FIX 1: Bảng sửa lỗi OCR được làm lại cẩn thận.
    # NGUYÊN TẮC: Chỉ sửa khi lỗi OCR thực sự xảy ra
    # (nhầm nét do mực/ánh sáng), KHÔNG sửa một triều vua
    # thành triều vua khác. Ví dụ: 洪武 ≠ 弘治, KHÔNG được sửa!
    # =====================================================
    ocr_corrections = {
        # Lỗi OCR thường gặp: nhầm nét tương tự
        "宣得": "宣德",   # 得 vs 德 — nét gần nhau
        "宣徳": "宣德",   # biến thể chữ 德
        "成化": "成化",   # OK, giữ nguyên
        "嘉請": "嘉靖",   # 請 vs 靖 — nét gần
        "嘉清": "嘉靖",   # 清 vs 靖 — nét gần
        "萬厤": "萬曆",   # biến thể cổ của 曆
        "萬歴": "萬曆",   # biến thể cổ của 曆
        "乹隆": "乾隆",   # 乹 là biến thể của 乾
        "乹": "乾",
    }
    for bad, good in ocr_corrections.items():
        if bad in ocr_clean:
            print(f"  [correction] '{bad}' → '{good}'")
            ocr_clean = ocr_clean.replace(bad, good)

    # 1. Exact match
    for item in database:
        for target in _get_targets(item):
            if ocr_clean == _normalize_cjk(target):
                return item, "exact"

    # 2. Substring match
    if len(ocr_clean) >= 3:
        for item in database:
            for target in _get_targets(item):
                target_clean = _normalize_cjk(target)
                if ocr_clean in target_clean or target_clean in ocr_clean:
                    return item, "substring"

    # 3. Fuzzy match
    candidates = []
    for item in database:
        for target in _get_targets(item):
            target_clean = _normalize_cjk(target)
            score = difflib.SequenceMatcher(None, ocr_clean, target_clean).ratio()
            if score > 0.4:
                candidates.append((score, item, target_clean))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_score = candidates[0][0]
        top_ties = [c for c in candidates if abs(c[0] - best_score) < 0.01]

        if len(top_ties) == 1:
            return top_ties[0][1], "fuzzy"

        # FIX 4: Tie-breaker dựa trên số ký tự chính xác khớp,
        # KHÔNG dùng ID (ID không liên quan độ chính xác OCR).
        def _exact_char_overlap(ocr: str, target: str) -> int:
            """Đếm số vị trí mà ký tự OCR và target trùng nhau."""
            return sum(1 for a, b in zip(ocr, target) if a == b)

        top_ties.sort(
            key=lambda x: _exact_char_overlap(ocr_clean, x[2]),
            reverse=True,
        )
        return top_ties[0][1], "fuzzy_tiedecision"

    return None, "none"


def _extract_nien_hieu(match: Optional[Dict[str, Any]]) -> str:
    if not match:
        return "Chưa xác định"
    base = match.get("chu_han_4") or match.get("chu_han") or ""
    base = base.replace("大明", "").replace("大清", "").replace("大南", "")
    for suffix in ["年製", "年造", "年玩"]:
        if base.endswith(suffix):
            base = base[: -len(suffix)]
    return base or "Chưa xác định"


def _build_translation_list(ocr_text: str) -> List[Dict[str, str]]:
    translation_map = {
        "大": ("Đại", "lớn, vĩ đại"),
        "明": ("Minh", "sáng, triều Minh"),
        "清": ("Thanh", "trong sáng, triều Thanh"),
        "年": ("Niên", "năm"),
        "製": ("Chế", "chế tác, sản xuất"),
        "造": ("Tạo", "tạo ra, chế tạo"),
        "嘉": ("Gia", "tốt lành, đẹp đẽ"),
        "靖": ("Tĩnh", "yên tĩnh, bình ổn"),
        "康": ("Khang", "khỏe mạnh, thịnh vượng"),
        "熙": ("Hy", "hưng thịnh, hoan hỉ"),
        "乾": ("Càn", "trời, dương"),
        "隆": ("Long", "thịnh vượng, hưng long"),
        "萬": ("Vạn", "vạn, mười nghìn"),
        "曆": ("Lịch", "lịch, thời gian"),
        "歷": ("Lịch", "lịch, trải qua"),
        "宣": ("Tuyên", "tuyên bố, công bố"),
        "德": ("Đức", "đức hạnh, đạo đức"),
        "成": ("Thành", "hoàn thành, thành công"),
        "化": ("Hóa", "biến hóa, cảm hóa"),
        "正": ("Chính", "ngay thẳng, đúng đắn"),
        "統": ("Thống", "thống nhất, trị vì"),
        "弘": ("Hoằng", "rộng lớn, phát huy"),
        "治": ("Trị", "trị vì, cai trị"),
        "順": ("Thuận", "thuận lợi, thuận theo"),
        "雍": ("Ung", "hòa hợp, trang nhã"),
        "道": ("Đạo", "đạo lý, con đường"),
        "光": ("Quang", "ánh sáng, rực rỡ"),
        "同": ("Đồng", "cùng nhau, đồng lòng"),
        "緒": ("Tự", "kế thừa, mối"),
        "洪": ("Hồng", "lớn lao, to lớn"),
        "武": ("Vũ", "võ, dũng mãnh"),
        "永": ("Vĩnh", "mãi mãi, vĩnh cửu"),
        "樂": ("Lạc", "vui vẻ, âm nhạc"),
        "宏": ("Hoằng", "rộng lớn"),
        "景": ("Cảnh", "cảnh vật, phong cảnh"),
        "泰": ("Thái", "thái bình, an ổn"),
        "崇": ("Sùng", "tôn sùng, cao quý"),
        "禎": ("Trinh", "điềm lành, tốt đẹp"),
        "天": ("Thiên", "trời, thiên nhiên"),
        "啟": ("Khải", "mở ra, khởi đầu"),
        "內": ("Nội", "bên trong, nội cung"),
        "府": ("Phủ", "phủ quan, kho"),
        "侍": ("Thị", "hầu hạ, phục vụ"),
        "從": ("Tòng", "theo hầu, tùy tùng"),
        "御": ("Ngự", "của vua, hoàng gia"),
        "用": ("Dụng", "sử dụng"),
        "玩": ("Ngoạn", "thưởng ngoạn, vật quý"),
        "珍": ("Trân", "quý báu, trân quý"),
        "賞": ("Thưởng", "thưởng thức, ban thưởng"),
        "壽": ("Thọ", "sống lâu, trường thọ"),
        "福": ("Phúc", "phúc lộc, may mắn"),
        "祥": ("Tường", "điềm lành, may mắn"),
    }
    results: List[Dict[str, str]] = []
    for ch in ocr_text:
        if ch in translation_map:
            am, nghia = translation_map[ch]
            results.append({"chu": ch, "am_han_viet": am, "nghia": nghia})
    return results


def _build_response(
    match: Optional[Dict[str, Any]],
    match_type: str,
    ocr_text: str,
    confidence: float,
    top_matches: List[Dict[str, Any]],
) -> Dict[str, Any]:
    year_range = "Chưa xác định"
    if match and match.get("nam_bat_dau") and match.get("nam_ket_thuc"):
        year_range = f"{match['nam_bat_dau']} - {match['nam_ket_thuc']}"
    translation_list = _build_translation_list(ocr_text)
    if match:
        best_chu_han = match.get("chu_han")
        ocr_len = len(ocr_text.strip())
        candidates = []
        if match.get("chu_han_6"): candidates.append(match.get("chu_han_6"))
        if match.get("chu_han_4"): candidates.append(match.get("chu_han_4"))
        if match.get("chu_han"): candidates.append(match.get("chu_han"))
        if match.get("bien_the"): candidates.extend(match.get("bien_the"))
        found_exact = False
        for cand in candidates:
            if cand and len(cand.strip()) == ocr_len:
                best_chu_han = cand.strip()
                found_exact = True
                break
        
        if not found_exact and ocr_len >= 3:
            best_chu_han = ocr_text.strip()

        best_ten_viet = match.get("ten_viet") or ""
        if best_chu_han and best_ten_viet:
            words = best_ten_viet.strip().split()
            if len(best_chu_han) == 4 and len(words) >= 6:
                if words[0].lower() == "đại" and words[1].lower() in ["minh", "thanh", "nam"]:
                    best_ten_viet = " ".join(words[2:])

        return {
            "chu_han": best_chu_han,
            "chu_han_4": match.get("chu_han_4"),
            "chu_han_6": match.get("chu_han_6"),
            "bien_the": match.get("bien_the", []),
            "ten_viet": best_ten_viet,
            "trieu_dai": match.get("trieu_dai"),
            "hoang_de": match.get("hoang_de"),
            "nien_hieu": _extract_nien_hieu(match),
            "nien_dai": year_range,
            "phien_am": match.get("phien_am"),
            "ghi_chu": match.get("ghi_chu"),
            "thu_phap": match.get("thu_phap"),
            "nghe_thuat": match.get("nghe_thuat"),
            "hieu_de_en": match.get("hieu_de_en"),
            "confidence": confidence,
            "match_type": match_type,
            "dich_nghia_tung_chu": translation_list,
            "top_matches": top_matches,
        }
    return {
        "chu_han": ocr_text or "Không rõ",
        "trieu_dai": "Chưa xác định",
        "nien_hieu": "Chưa xác định",
        "dich_nghia_tung_chu": translation_list,
        "ghi_chu": "Không tìm thấy trong database. Dịch nghĩa tham khảo từng chữ.",
        "confidence": confidence,
        "match_type": match_type,
        "top_matches": top_matches,
    }


def find_best_matches(ocr_text: str, database: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
    normalized = _normalize_cjk(ocr_text)
    if not normalized:
        return []

    SIMILAR_GROUPS = [
        {"大", "天", "太", "夫", "犬"},
        {"明", "朋", "目", "月", "囧"},
        {"治", "冶", "始", "沿", "怡"},
        {"平", "干", "千", "年", "半"},
        {"順", "頓", "碩", "預", "煩"},
        {"年", "牛", "午", "平", "半"},
        {"製", "制", "脊"},
        {"隆", "降", "窿", "融"},
        {"慶", "麗", "廢", "應", "魔", "磨", "廣"},
        {"嘉", "喜", "家", "善", "嘗"},
        {"靖", "清", "情", "精", "請", "靜", "藏"},
        {"萬", "万"},
        {"曆", "歷", "厤", "歴"},
        {"宣", "官", "宜", "直"},
        {"德", "徳", "得"},
        {"洪", "鴻", "泓", "汪"},
        {"武", "式", "戊"},
        {"成", "戊", "戌", "戍"},
        {"弘", "宏", "泓"},
        {"正", "政", "証", "征"},
        {"統", "緒", "絲"},
        {"内", "內"},
        {"贵", "貴"},
        {"长", "長"},
        {"宝", "寶"},
        {"龙", "龍"},
        {"万", "萬"},
        {"春", "舂", "椿"},
        {"侍", "待", "持", "特", "恃"},
        {"左", "佐", "右", "石", "有"},
        {"中", "杜", "牡", "社", "址", "仲", "忠", "柱"},
        {"旨", "皆", "官"},
        {"東", "束", "柬", "棟"},
        {"南", "楠", "喃"},
        {"北", "背", "兆"},
        {"西", "曲", "酉"},
        {"府", "腐", "附"},
        {"康", "庚", "唐", "廉"},
        {"熙", "照", "熊", "然", "煕"},
        {"雍", "維", "雅"},
        {"乾", "幹", "軒"},
        {"道", "進", "適", "遒"},
        {"光", "先", "克", "充"},
        {"緒", "絲", "續", "紹"},
        {"同", "銅", "僮"},
        {"祥", "詳", "翔"},
        {"瑞", "端"},
        {"玉", "王", "主"},
        {"堂", "常", "當"},
        {"福", "富"},
        {"禄", "祿", "綠"},
        {"壽", "寿"},
        {"玄", "去", "云", "元", "亢"},
        {"窯", "窑"},
        {"造", "迴", "遭"},
    ]

    def similarity(ch1: str, ch2: str) -> float:
        if ch1 == ch2:
            return 1.0
        for group in SIMILAR_GROUPS:
            if ch1 in group and ch2 in group:
                return 0.6
        return 0.0

    def char_seq_score(s1: str, s2: str) -> float:
        if not s1 or not s2:
            return 0.0
        len1, len2 = len(s1), len(s2)
        max_len = max(len1, len2)
        positional_score = sum(similarity(s1[i], s2[i]) for i in range(min(len1, len2))) / max_len
        best_align = 0.0
        for offset in range(-2, 3):
            score = sum(
                similarity(s1[i], s2[i + offset])
                for i in range(len1)
                if 0 <= i + offset < len2
            )
            best_align = max(best_align, score / max_len)
        # Tỷ lệ ký tự s1 có mặt trong s2
        m1 = sum(max((similarity(c1, c2) for c2 in s2), default=0) for c1 in s1)
        # Tỷ lệ ký tự s2 có mặt trong s1
        m2 = sum(max((similarity(c2, c1) for c1 in s1), default=0) for c2 in s2)
        set_score = (m1 / len1 + m2 / len2) / 2

        base = positional_score * 0.20 + best_align * 0.30 + set_score * 0.50

        # CONTAINMENT BONUS: Nếu MỌI chữ OCR đọc được đều nằm trong target (fuzzy),
        # → rất có thể OCR chỉ đọc được 1 phần (3/6 chữ) nhưng đúng hiệu đề.
        s1_in_s2_count = sum(1 for c1 in s1 if max((similarity(c1, c2) for c2 in s2), default=0) >= 0.7)
        containment = s1_in_s2_count / len1  # 0.0 ~ 1.0
        
        # Chỉ áp dụng khi OCR đọc >= 3 chữ hợp lệ
        if len1 >= 3 and containment >= 0.9:
            # Cộng điểm phạt bu trừ cho "s2 có mặt trong s1" bị thấp do OCR đọc thiếu chữ
            # Và thưởng mạnh nếu đích (target s2) là chuỗi 6 chữ
            length_bonus = 0.15 if len2 == 6 else (0.05 if len2 == 4 else 0.0)
            base += 0.3 + length_bonus
        elif len1 >= 3 and containment >= 0.75:
            length_bonus = 0.10 if len2 == 6 else (0.02 if len2 == 4 else 0.0)
            base += 0.15 + length_bonus

        return base

    scored = []
    for item in database:
        targets = []
        for field in ["chu_han", "chu_han_4", "chu_han_6"]:
            val = item.get(field, "")
            if val:
                targets.append(_normalize_cjk(val))
        for bien_the in item.get("bien_the", []) or []:
            if bien_the:
                targets.append(_normalize_cjk(bien_the))
        best = max((char_seq_score(normalized, t) for t in targets if t), default=0.0)
        scored.append((best, item))

    if normalized:
        for idx, (score, item) in enumerate(scored):
            targets = [
                _normalize_cjk(item.get("chu_han", "")),
                _normalize_cjk(item.get("chu_han_4", "")),
                _normalize_cjk(item.get("chu_han_6", "")),
            ]
            if any(normalized in t for t in targets if t):
                scored[idx] = (score + 0.3, item)

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_n]
    max_score = top[0][0] if top and top[0][0] > 0 else 1.0

    return [
        {
            **item,
            "match_score": round((score / max_score) * 100, 1),
            "raw_score": round(score, 4),
        }
        for score, item in top
    ]


def rank_by_multi_candidates(
    candidates: List[str], database: List[Dict[str, Any]], top_n: int = 5
) -> List[Dict[str, Any]]:
    """Gộp nhiều candidate OCR để giảm sai lệch do 1 lần đọc nhầm."""
    raw_clean = []
    for c in candidates:
        norm = _normalize_cjk(c)
        if norm and norm not in raw_clean:
            raw_clean.append(norm)
    # Ưu tiên ứng viên có độ dài lớn hơn
    clean_candidates = sorted(raw_clean, key=len, reverse=True)
    
    if not clean_candidates:
        return []

    agg: Dict[int, Dict[str, Any]] = {}
    for idx, candidate in enumerate(clean_candidates):
        # Weight thấp cho candidate ở sau, và weight cực thấp nếu OCR chỉ đọc được 1-2 chữ
        base_weight = 1.0 if idx == 0 else 0.72
        len_weight = min(len(candidate) / 4.0, 1.2)
        weight = base_weight * len_weight
        
        ranked = find_best_matches(candidate, database, top_n=top_n)
        for rank, match in enumerate(ranked):
            item_id = match.get("id")
            if item_id is None:
                continue
            rank_decay = 1.0 / (1.0 + rank * 0.45)
            base_score = float(match.get("raw_score", 0.0))
            combined = base_score * weight * rank_decay

            if item_id not in agg:
                agg[item_id] = {**match, "agg_score": 0.0, "votes": 0}
            agg[item_id]["agg_score"] += combined
            agg[item_id]["votes"] += 1

    final = list(agg.values())
    final.sort(key=lambda x: (x.get("agg_score", 0.0), x.get("votes", 0)), reverse=True)
    top = final[:top_n]
    max_score = top[0]["agg_score"] if top and top[0]["agg_score"] > 0 else 1.0
    for row in top:
        row["match_score"] = round((row["agg_score"] / max_score) * 100, 1)
        row["raw_score"] = round(row["agg_score"], 4)
    return top


def _detect_dynasty_prefixes(texts: List[str]) -> List[str]:
    prefixes = []
    for raw in texts:
        text = _normalize_cjk(raw or "")
        if "大明" in text and "大明" not in prefixes:
            prefixes.append("大明")
        if "大清" in text and "大清" not in prefixes:
            prefixes.append("大清")
        if "大南" in text and "大南" not in prefixes:
            prefixes.append("大南")
    return prefixes


def _normalize_mark_candidate(raw: str) -> str:
    """
    Chuẩn hóa các lỗi OCR phổ biến theo ngữ cảnh hiệu đề.
    Giữ quy tắc bảo thủ: chỉ thay thế khi có pattern đặc trưng.
    """
    s = _normalize_cjk(raw or "")
    if not s:
        return s

    # Ký tự cuối thường bị OCR lệch khi gặp "年製"
    s = s.replace("年泉", "年製").replace("年型", "年製").replace("年装", "年製")
    s = s.replace("年盒", "年製").replace("年皿", "年製")

    # Một số ảnh mờ đọc nhầm 乾 -> 农/蓬 khi đi cùng 隆年
    if "隆年" in s:
        s = s.replace("农隆", "乾隆").replace("蓬隆", "乾隆")

    # Nếu chuỗi có 年 nhưng thiếu 製/造 thì thử bổ sung hậu tố phổ biến.
    if "年" in s and not any(x in s for x in ("製", "造", "玩")):
        if s.endswith("年"):
            s = s + "製"

    # Heuristic cho mẫu "內府侍X" khi OCR nhiễu chữ gần nét.
    # QUAN TRỌNG: Có nhiều biến thể (侍右, 侍旨, 侍南, 侍左, 侍中, 侍從) — KHÔNG được ép cố định!
    # Chỉ sửa ký tự thứ 3 khi bị OCR đọc sai (特→侍, 社→侍), GIỮ NGUYÊN ký tự thứ 4.
    # Ký tự thứ 4 sẽ được xử lý bởi _boost_neifu_match_score() thay vì normalize cứng.
    has_nei = any(ch in s for ch in ("內", "内"))
    has_fu = "府" in s
    if has_nei and has_fu:
        # Sửa ký tự thứ 3 bị OCR đọc nhầm: 特→侍, 社→侍, 待→侍
        for wrong_shi in ("特", "社", "待"):
            if wrong_shi in s:
                s = s.replace(wrong_shi, "侍", 1)
        # ĐÃ XÓA: Không normalize cứng ký tự thứ 4 nữa.
        # Lý do: các biến thể 侍左/侍右/侍旨/侍南/侍中 dễ bị nhầm lẫn khi dùng if-elif chain.
        # Thay bằng: _boost_neifu_match_score() sẽ điều chỉnh score dựa trên char thứ 4 OCR đọc được.

    qing_reigns = {"康熙", "雍正", "乾隆", "嘉慶", "道光", "咸豐", "同治", "光緒", "宣統"}
    nguyen_reigns = {"嘉隆", "明命", "紹治", "嗣德", "建福", "咸宜", "同慶", "成泰", "維新", "啟定", "保大"}

    # Fix dynasty confusion: 大南 + Qing reign -> 大清; 大清 + Nguyen reign -> 大南
    if s.startswith("大南") and any(r in s for r in qing_reigns):
        s = s.replace("大南", "大清", 1)
    if s.startswith("大清") and any(r in s for r in nguyen_reigns):
        s = s.replace("大清", "大南", 1)

    # Confusion pairs for Khangxi and dynasty chars
    if "雅" in s and "齋" in s and "年" in s:
        s = s.replace("雅", "康").replace("齋", "熙")
    if "鹿" in s and "年" in s:
        s = s.replace("鹿", "康")
    if "希" in s and "年" in s:
        s = s.replace("希", "熙")

    # Common confusion pairs for dynasty characters
    if s.startswith("太清"):
        s = s.replace("太清", "大清", 1)
    if s.startswith("太明"):
        s = s.replace("太明", "大明", 1)
    if s.startswith("太南"):
        s = s.replace("太南", "大南", 1)
    if "大太" in s:
        s = s.replace("大太", "大")
    # REMOVED: Overly aggressive rules that replaced 南→清 and 保→康
    # These caused misidentification by corrupting valid OCR readings.
    return s


def _inject_qing_kangxi_if_evidence(raw: str) -> Optional[str]:
    """
    Chỉ inject 大清康熙年製 khi có bằng chứng cụ thể rằng cả hai ký tự 康 VÀ 熙
    (hoặc biến thể OCR gần đúng) đều xuất hiện trong kết quả OCR.
    KHÔNG inject mặc định khi chỉ thấy 大清…年製 — đó là lỗi cũ gây nhầm triều đại.
    """
    s = _normalize_cjk(raw or "")
    if not s or "康熙" in s:
        return None
    # Chỉ inject khi có cả 康 VÀ (熙 hoặc biến thể gần nét)
    has_kang = "康" in s or "鹿" in s
    has_xi = "熙" in s or "希" in s
    if has_kang and has_xi and "年" in s:
        return "大清康熙年製"
    return None


def _is_incomplete_dynasty_mark(text: str) -> bool:
    clean = _normalize_cjk(text)
    return clean in {"大明年製", "大清年製", "大南年製"}


def _expand_incomplete_dynasty_candidates(text: str) -> List[str]:
    clean = _normalize_cjk(text)
    if clean == "大明年製":
        reigns = ["洪武", "永樂", "宣德", "成化", "嘉靖", "萬曆", "天順", "弘治", "正德", "景泰", "天啟", "崇禎"]
        return [f"大明{r}年製" for r in reigns]
    if clean == "大清年製":
        reigns = ["康熙", "雍正", "乾隆", "嘉慶", "道光", "咸豐", "同治", "光緒", "宣統"]
        return [f"大清{r}年製" for r in reigns]
    if clean == "大南年製":
        reigns = ["嘉隆", "明命", "紹治", "嗣德", "建福", "咸宜", "同慶", "成泰", "維新", "啟定", "保大"]
        return [f"大南{r}年製" for r in reigns]
    return []


def _column_reconstruction(text: str) -> List[str]:
    clean = _normalize_cjk(text)
    if len(clean) != 4 or not clean.endswith("年製"):
        return []
    a, b, c, d = clean
    if a in "大明大清大南":
        return []
    return ["".join([b, a, c, d])]


def _expand_ocr_candidates(primary: str, candidates: List[str], blur_score: Optional[float] = None) -> List[str]:
    base = [primary] + [c for c in candidates if c and c != primary]
    has_dynasty_prefix = False
    for item in base:
        clean = _normalize_cjk(item or "")
        if any(prefix in clean for prefix in ("大明", "大清", "大南")):
            has_dynasty_prefix = True
            break
    # Collect supplementary candidates (injections) — but do NOT prioritize them.
    # They will be appended at the end, after the actual OCR results.
    inject_extra: List[str] = []
    for item in base:
        norm = _normalize_mark_candidate(item or "")
        for raw in (item, norm):
            if not raw:
                continue
            inj = _inject_qing_kangxi_if_evidence(raw)
            if inj and inj not in inject_extra:
                inject_extra.append(inj)

            # Heuristic: small square mark can be misread as 建福年製 instead of 甲子年製.
            raw_clean = _normalize_cjk(raw)
            if (
                ("建福年製" in raw_clean or "建福年造" in raw_clean)
                and not has_dynasty_prefix
                and "甲子年製" not in inject_extra
            ):
                inject_extra.append("甲子年製")

    expanded: List[str] = []
    seen: set = set()

    for item in base:
        clean = _normalize_cjk(item or "")
        if clean and clean not in seen:
            expanded.append(clean)
            seen.add(clean)
        normalized = _normalize_mark_candidate(item or "")
        if normalized and normalized not in seen:
            expanded.append(normalized)
            seen.add(normalized)

        # Expand incomplete dynasty marks
        if _is_incomplete_dynasty_mark(clean):
            for c in _expand_incomplete_dynasty_candidates(clean):
                if c not in seen:
                    expanded.append(c)
                    seen.add(c)

        # Column reconstruction for 4-char XX年製
        for c in _column_reconstruction(clean):
            if c not in seen:
                expanded.append(c)
                seen.add(c)

    # Append injected candidates at the END (not front) so they don't
    # override actual OCR evidence.
    for inj in inject_extra:
        if inj not in seen:
            expanded.append(inj)
            seen.add(inj)

    return expanded


def _max_char_overlap(candidates: List[str], target: str) -> int:
    target_set = set(_normalize_cjk(target))
    if not target_set:
        return 0
    best = 0
    for c in candidates:
        c_set = set(_normalize_cjk(c))
        if not c_set:
            continue
        best = max(best, len(c_set & target_set))
    return best


def _support_votes_for_match(candidates: List[str], target: str) -> int:
    target_clean = _normalize_cjk(target)
    if not target_clean:
        return 0
    votes = 0
    for c in candidates:
        c_clean = _normalize_cjk(c)
        if not c_clean:
            continue
        overlap = len(set(c_clean) & set(target_clean))
        ratio = difflib.SequenceMatcher(None, c_clean, target_clean).ratio()
        if overlap >= 3 or ratio >= 0.56:
            votes += 1
    return votes


def _is_year_mark_text(text: str) -> bool:
    clean = _normalize_cjk(text or "")
    if not clean:
        return False
    return ("年" in clean) and any(s in clean for s in ("製", "造", "玩"))


def _is_can_chi_mark(text: str) -> bool:
    clean = _normalize_cjk(text or "")
    if not clean or "年" not in clean:
        return False
    stems = set("甲乙丙丁戊己庚辛壬癸")
    branches = set("子丑寅卯辰巳午未申酉戌亥")
    # Expect stem + branch + 年製/年造/年玩 (4 chars total or 2+suffix)
    if len(clean) < 4:
        return False
    has_stem = any(ch in stems for ch in clean)
    has_branch = any(ch in branches for ch in clean)
    return has_stem and has_branch and _is_year_mark_text(clean)


def _has_can_chi_evidence(candidates: List[str]) -> bool:
    stems = set("甲乙丙丁戊己庚辛壬癸")
    branches = set("子丑寅卯辰巳午未申酉戌亥")
    for c in candidates:
        clean = _normalize_cjk(c)
        if not clean:
            continue
        if any(ch in stems for ch in clean) and any(ch in branches for ch in clean):
            return True
    return False


def _char_overlap_ratio(a: str, b: str) -> float:
    a_clean = _normalize_cjk(a)
    b_clean = _normalize_cjk(b)
    if not a_clean or not b_clean:
        return 0.0
    sa, sb = set(a_clean), set(b_clean)
    inter = len(sa & sb)
    union = len(sa | sb)
    if union == 0:
        return 0.0
    return inter / union


NEIFU_4TH_CHAR_MAP = {
    # Các lỗi OCR phổ biến cho ký tự thứ 4 trong chuỗi "內府侍X"
    # Map: (ký tự OCR sai) -> (ký tự đúng)
    # --- 侍左 (Thị Tả) ---
    "生": "左", "在": "左", "左": "左", "址": "左", "注": "左", "庄": "左", "杜": "左",
    # --- 侍右 (Thị Hữu) ---
    "有": "右", "石": "右", "右": "右", "名": "右",
    # --- 侍旨 (Thị Chỉ) ---
    "血": "旨", "盒": "旨", "皿": "旨", "旨": "旨", "日": "旨", "曰": "旨",
    # --- 侍南 (Thị Nam) ---
    "南": "南", "雨": "南", "两": "南", "甬": "南",
    # --- 侍中 (Thị Trung) ---
    "中": "中", "申": "中", "巾": "中",
    # --- 侍從 (Thị Tòng) ---
    "從": "從", "从": "從",
}

NEIFU_VARIANTS_4TH = {
    "左": "內府侍左",
    "右": "內府侍右",
    "旨": "內府侍旨",
    "南": "內府侍南",
    "中": "內府侍中",
    "從": "內府侍從",
}


def _extract_neifu_4th_char(ocr_text: str) -> str:
    """
    Từ chuỗi OCR có chứa 內府侍, cố gắng xác định ký tự thứ 4.
    Không phụ thuộc vào thứ tự chuỗi do PaddleOCR thường sắp xếp lộn xộn các ký tự 
    của hiệu đề viết dọc / viết vuông 4 chữ.
    """
    s = "".join(ch for ch in (ocr_text or "") if "\u4e00" <= ch <= "\u9fff")
    
    # Kiểm tra xem có đủ các kí tự cấu thành "Nội Phủ Thị" không (bất kể thứ tự)
    has_nei = "内" in s or "內" in s
    has_fu = "府" in s
    # 侍 hay bị nhầm thành các chữ này
    has_shi = any(ch in s for ch in ("侍", "待", "特", "社", "挂", "诗"))
    
    if has_nei and has_fu:
        # Nếu có Nội và Phủ, ta quét tìm xem trong chuỗi có chữ nào 
        # map được với ký tự thứ 4 không.
        for ch in s:
            canonical = NEIFU_4TH_CHAR_MAP.get(ch, "")
            if canonical:
                return NEIFU_VARIANTS_4TH.get(canonical, "")
        
        # Nếu không có chữ nào khớp trong map, ta đành chịu
        return ""
    
    return ""


def _boost_neifu_match_score(
    candidates, scored_items, normalize_cjk_fn, sequence_matcher_fn
):
    """
    Tăng score cho entry Nội Phủ có chữ thứ 4 khớp với OCR,
    đồng thời phạt các entry Nội Phủ có chữ thứ 4 KHÔNG khớp.
    
    Args:
        candidates: list[str] — các chuỗi OCR đã normalize
        scored_items: list[dict] — kết quả từ rank_by_multi_candidates / find_best_matches
        normalize_cjk_fn: hàm _normalize_cjk
        sequence_matcher_fn: difflib.SequenceMatcher
    
    Returns:
        list[dict] đã được re-sort theo score mới
    """
    # Tìm chữ thứ 4 từ các candidates
    best_4th = ""
    best_neifu_candidate = ""
    for c in candidates:
        result = _extract_neifu_4th_char(c)
        if result:
            best_neifu_candidate = result
            # Lấy chữ thứ 4
            nc = normalize_cjk_fn(result)
            if len(nc) >= 4:
                best_4th = nc[3]
            break
    
    if not best_4th:
        return scored_items  # Không có tín hiệu Nội Phủ rõ ràng → giữ nguyên
    
    print(f"  [neifu_boost] detected 4th char='{best_4th}', expected='{best_neifu_candidate}'")
    
    adjusted = []
    for item in scored_items:
        chu_han = normalize_cjk_fn(item.get("chu_han", "") or "")
        is_neifu = ("內府" in chu_han) or ("内府" in chu_han)
        
        if not is_neifu:
            adjusted.append(item)
            continue
        
        # Lấy chữ thứ 4 của entry này
        entry_4th = chu_han[3] if len(chu_han) >= 4 else ""
        current_score = float(item.get("match_score", item.get("score", 50)) or 50)
        raw_score = float(item.get("raw_score", item.get("agg_score", 0)) or 0)
        
        if entry_4th == best_4th:
            # Khớp chữ thứ 4: boost mạnh
            boost = 25.0
            print(f"  [neifu_boost] BOOST +{boost} for {chu_han}")
        else:
            # Sai chữ thứ 4: phạt
            boost = -20.0
            print(f"  [neifu_boost] PENALIZE {boost} for {chu_han}")
        
        adjusted.append({
            **item,
            "match_score": min(100.0, max(0.0, current_score + boost)),
            "raw_score": raw_score,
            "_neifu_adjusted": True,
        })
    
    adjusted.sort(key=lambda x: float(x.get("match_score", x.get("score", 0)) or 0), reverse=True)
    return adjusted


def _choose_display_mark(
    selected_report: Optional[Dict[str, Any]],
    merged_candidates: List[str],
    ocr_text: str,
) -> str:
    """
    Chọn text hiển thị theo bằng chứng OCR:
    - Ảnh 4 chữ -> ưu tiên chu_han_4
    - Ảnh 6 chữ -> ưu tiên chu_han
    Tránh tự thêm tiền tố triều đại khi không có trong ảnh.
    """
    if not selected_report:
        return ocr_text

    mark4_raw = selected_report.get("chu_han_4") or selected_report.get("chu_han") or ""
    mark6_raw = selected_report.get("chu_han_6") or selected_report.get("chu_han") or ""
    mark4 = _normalize_cjk(mark4_raw)
    mark6 = _normalize_cjk(mark6_raw)
    if not mark4 and not mark6:
        return ocr_text

    evidence = [_normalize_cjk(x) for x in merged_candidates if _normalize_cjk(x)]
    if not evidence and _normalize_cjk(ocr_text):
        evidence = [_normalize_cjk(ocr_text)]

    if not evidence:
        return selected_report.get("chu_han_4") or selected_report.get("chu_han") or ocr_text

    best_len = max((len(x) for x in evidence), default=0)
    best4 = max((_char_overlap_ratio(x, mark4) for x in evidence), default=0.0) if mark4 else 0.0
    best6 = max((_char_overlap_ratio(x, mark6) for x in evidence), default=0.0) if mark6 else 0.0
    has_dynasty_hint = any(any(prefix in x for prefix in ("大明", "大清", "大南")) for x in evidence)

    # Có tín hiệu 6 chữ rõ -> hiển thị đủ 6 chữ.
    if mark6 and (has_dynasty_hint or best_len >= 5 or best6 >= 0.75):
        return mark6_raw

    # Có tín hiệu 4 chữ rõ -> hiển thị đúng 4 chữ.
    if mark4 and (best_len <= 4 or (best4 >= 0.5 and best6 < 0.7)):
        return mark4_raw

    # Fallback bảo thủ
    return mark4_raw or mark6_raw or ocr_text


def _get_top_matches_from_candidates(
    candidates: List[str], database: List[Dict[str, Any]], limit: int = 5
) -> List[Dict[str, Any]]:
    if not candidates:
        return []

    scored = []
    for item in database:
        targets = [item.get("chu_han"), item.get("chu_han_4", "")]
        targets += item.get("bien_the", []) or []
        targets = [t for t in targets if t]
        best = 0.0
        for candidate in candidates:
            for target in targets:
                ocr_set = set(candidate)
                tgt_set = set(target)
                common = ocr_set & tgt_set
                if not tgt_set:
                    continue
                overlap_score = len(common) / len(ocr_set | tgt_set)
                substr_bonus = 0.0
                for i in range(len(candidate) - 1):
                    if candidate[i: i + 2] in target:
                        substr_bonus += 0.15
                for i in range(len(candidate) - 2):
                    if candidate[i: i + 3] in target:
                        substr_bonus += 0.25
                seq = difflib.SequenceMatcher(None, candidate, target).ratio()
                score = overlap_score * 0.4 + seq * 0.4 + min(substr_bonus, 0.5) * 0.2
                if _is_incomplete_dynasty_mark(target):
                    score = max(0.0, score - 0.3)
                if score > best:
                    best = score
        scored.append((best, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:limit]
    max_score = top[0][0] if top and top[0][0] > 0 else 1

    results = []
    for score, item in top:
        results.append(
            {
                "chu_han": item.get("chu_han"),
                "ten_viet": item.get("ten_viet"),
                "trieu_dai": item.get("trieu_dai"),
                "nien_dai": (
                    f"{item.get('nam_bat_dau')} - {item.get('nam_ket_thuc')}"
                    if item.get("nam_bat_dau") and item.get("nam_ket_thuc")
                    else "Chua xac dinh"
                ),
                "score": round((score / max_score) * 100, 1),
                "match_score": round((score / max_score) * 100, 1),
            }
        )
    if results and len(results) > 1:
        top_item = results[0]
        runner = results[1]
        top_len = len(_normalize_cjk(top_item.get("chu_han", "")))
        runner_len = len(_normalize_cjk(runner.get("chu_han", "")))
        top_score = float(top_item.get("score", 0) or 0) / 100.0
        runner_score = float(runner.get("score", 0) or 0) / 100.0
        if top_len <= 3 and runner_len >= 6 and (top_score - runner_score) < 0.15:
            results = [runner] + [r for r in results if r is not runner]
    return results


def _apply_crop(image_bytes: bytes, crop: Dict[str, float]) -> bytes:
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return image_bytes
    height, width = img.shape[:2]
    x = int(max(0.0, min(1.0, crop["x"])) * width)
    y = int(max(0.0, min(1.0, crop["y"])) * height)
    w = int(max(0.0, min(1.0, crop["w"])) * width)
    h = int(max(0.0, min(1.0, crop["h"])) * height)
    if w <= 1 or h <= 1:
        return image_bytes
    x2 = min(width, x + w)
    y2 = min(height, y + h)
    cropped = img[y:y2, x:x2]
    if cropped.size == 0:
        return image_bytes
    success, encoded = cv2.imencode(".png", cropped)
    if not success:
        return image_bytes
    return encoded.tobytes()


def _estimate_blur_score(image_bytes: bytes) -> float:
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return 0.0
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def _auto_use_deep_mode(image_bytes: bytes) -> bool:
    # Laplacian variance thấp => ảnh mờ/thiếu chi tiết, nên dùng deep mode.
    blur_score = _estimate_blur_score(image_bytes)
    print(f"[auto_mode] blur_score={blur_score:.2f}")
    return blur_score < 120.0


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": f"Loi xu ly OCR: {exc}"})


@app.get("/")
def read_index():
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    return FileResponse(index_path, headers={"Cache-Control": "no-store"})

def _render_index_page(initial_page: str) -> HTMLResponse:
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        html = f.read()

    page_id = "auth" if initial_page in {"login", "register"} else initial_page
    html = html.replace('<div class="pg on" id="pg-home">', '<div class="pg" id="pg-home">')
    html = html.replace(f'<div class="pg" id="pg-{page_id}">', f'<div class="pg on" id="pg-{page_id}">')
    html = html.replace('<button class="nb on" id="nb-home"', '<button class="nb" id="nb-home"')
    html = html.replace(f'<button class="nb" id="nb-{initial_page}"', f'<button class="nb on" id="nb-{initial_page}"')

    if initial_page in {"login", "register"}:
        html = html.replace("<nav>", '<nav style="display:none">', 1)
        html = html.replace('<footer class="site-footer"', '<footer class="site-footer" style="display:none"', 1)
        if initial_page == "register":
            html = html.replace('<div class="auth-slider" id="authSlider">', '<div class="auth-slider show-register" id="authSlider">', 1)

    return HTMLResponse(content=html, headers={"Cache-Control": "no-store"})

@app.get("/login")
def read_login_page():
    return _render_index_page("login")

@app.get("/terms")
def read_terms_page():
    return _render_index_page("terms")

@app.get("/privacy")
def read_privacy_page():
    return _render_index_page("privacy")

@app.get("/history")
def read_history_page():
    return _render_index_page("history")

@app.get("/admin")
@app.get("/admin/")
def read_admin_page():
    admin_path = os.path.join(os.path.dirname(__file__), "admin.html")
    return FileResponse(admin_path, headers={"Cache-Control": "no-store"})

@app.get("/flow-test")
def read_flow_test_page():
    flow_test_path = os.path.join(os.path.dirname(__file__), "flow-test.html")
    return FileResponse(flow_test_path, headers={"Cache-Control": "no-store"})

@app.get("/logo.png")
def read_logo():
    logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
    if os.path.exists(logo_path):
        return FileResponse(logo_path)
    return JSONResponse(status_code=404, content={"message": "Logo not found"})

@app.get("/{page_name}")
def read_spa_page(page_name: str):
    if page_name in WEB_PAGE_IDS:
        return _render_index_page(page_name)
    return JSONResponse(status_code=404, content={"detail": "Not Found"})


@app.get("/data/hieu_de_database.json")
def read_reign_database():
    data_path = os.path.join(os.path.dirname(__file__), "data", "hieu_de_database.json")
    return FileResponse(data_path)


@app.post("/ocr")
async def ocr_endpoint(
    request: Request,
    file: UploadFile = File(...),
    crop_x: Optional[float] = Form(None),
    crop_y: Optional[float] = Form(None),
    crop_w: Optional[float] = Form(None),
    crop_h: Optional[float] = Form(None),
    deep_mode: Optional[bool] = Form(None),
):
    def _save_history(image_bytes, display_text, report_matched):
        user_id = request.headers.get("Authorization")
        if user_id and user_id.startswith("Bearer "):
            user_id = user_id.split("Bearer ")[1]
            try:
                import os as _os
                import uuid
                if not _os.path.exists("uploads"): _os.makedirs("uploads")
                unique_suffix = uuid.uuid4().hex[:8]
                hist_img_path = f"uploads/{user_id}_{unique_suffix}_scan.jpg"
                
                with open(hist_img_path, "wb") as f:
                    f.write(image_bytes)
                details = {
                    "matched": True if report_matched else False,
                    "top_mark": display_text
                }
                if isinstance(report_matched, dict):
                    details.update(report_matched)
                    
                add_scan_history(int(user_id), hist_img_path, display_text, details)
                # Trừ 1 lượt phân tích
                new_cr = deduct_credit(int(user_id))
                return new_cr
            except Exception as e:
                print("Failed to save history:", e)
        return None
    try:
        # === KIỂM TRA LƯỢT PHÂN TÍCH ===
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            uid = auth_header.split("Bearer ")[1]
            try:
                remaining = get_user_credits(int(uid))
                if remaining <= 0:
                    return JSONResponse(
                        status_code=403,
                        content={"success": False, "no_credits": True, "message": "Bạn đã hết lượt phân tích miễn phí.", "credits": 0}
                    )
            except:
                pass

        if not file:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Không tìm thấy tệp hình ảnh.", "chu_han": "", "top5": [], "report": None},
            )

        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Định dạng ảnh không được hỗ trợ.", "chu_han": "", "top5": [], "report": None},
            )

        image_bytes = await file.read()
        if None not in (crop_x, crop_y, crop_w, crop_h):
            image_bytes = _apply_crop(image_bytes, {"x": crop_x, "y": crop_y, "w": crop_w, "h": crop_h})

        # Lưu tạm ảnh để hỗ trợ Auto-Learning (xác nhận kết quả đúng → lưu vào thư viện)
        user_token = request.headers.get("Authorization", "anonymous")
        _last_analyzed_images[user_token] = image_bytes

        # 1. Kiểm tra thư viện tham chiếu (ORB)
        matched_report = match_image(image_bytes)

        # 2. Chạy OCR (auto deep cho ảnh mờ nếu client không chỉ định)
        blur_score = _estimate_blur_score(image_bytes)
        use_deep_mode = bool(deep_mode) if deep_mode is not None else _auto_use_deep_mode(image_bytes)
        result = read_chinese_mark(image_bytes, deep_mode=use_deep_mode)
        ocr_text = result.get("text", "")
        candidates = result.get("candidates", [])

        # Nếu pass nhanh chưa ra kết quả, tự fallback sang deep mode.
        if (not ocr_text and not candidates) and not use_deep_mode:
            print("[auto_mode] fast pass empty -> retry deep mode")
            result = read_chinese_mark(image_bytes, deep_mode=True)
            ocr_text = result.get("text", "")
            candidates = result.get("candidates", [])

        # 3. Xác minh ORB match bằng tỷ lệ best/second-best + OCR.
        if matched_report:
            orb_best = matched_report.pop("_orb_best", 0)
            orb_second = matched_report.pop("_orb_second", 0)
            ref_chu_han = _normalize_cjk(matched_report.get("chu_han", ""))
            
            # Nếu best >> second-best: rất có thể là cùng một ảnh → tin ORB ngay.
            # Ví dụ: cùng ảnh best=300, second=50 → ratio=6.0 → tin ORB
            # Ảnh khác nền giống: best=100, second=95 → ratio=1.05 → cần kiểm tra OCR
            orb_ratio = orb_best / max(orb_second, 1)
            print(f"[ORB verify] ref='{ref_chu_han}', best={orb_best}, second={orb_second}, ratio={orb_ratio:.2f}")
            
            if orb_ratio >= 1.5 and orb_best >= 50:
                # ORB rất tự tin: best vượt trội hẳn second → tin ORB không cần OCR
                print(f"[ORB verify] HIGH CONFIDENCE (ratio={orb_ratio:.2f}). Trusting ORB match.")
                new_cr = _save_history(image_bytes, matched_report.get("chu_han", ""), matched_report)
                if new_cr is not None: matched_report["credits"] = new_cr
                return JSONResponse(status_code=200, content=matched_report)
            
            # ORB match gần nhau → cần kiểm tra bằng OCR
            ref_chars = set(ref_chu_han)
            all_evidence_chars = set(_normalize_cjk(ocr_text))
            for c in candidates:
                all_evidence_chars.update(set(_normalize_cjk(c)))

            # Fuzzy overlap: tính cả ký tự tương tự (OCR hay nhầm)
            SIMILAR_GROUPS_ORB = [
                {"慶", "麗", "廢", "應", "魔", "磨", "廣"},
                {"春", "舂", "椿"},
                {"侍", "待", "持", "特", "恃"},
                {"左", "佐", "右", "石", "有"},
                {"中", "杜", "牡", "社", "址", "仲", "忠", "柱"},
                {"東", "束", "柬", "棟"}, {"南", "楠", "喃"},
                {"北", "背", "兆"}, {"西", "曲", "酉"},
                {"內", "内"}, {"府", "腐", "附"},
                {"大", "天", "太", "夫"}, {"明", "朋", "目", "月"},
                {"清", "靖", "情", "精", "請", "靜", "藏"},
                {"康", "庚", "唐", "廉"}, {"熙", "照", "熊", "煕"},
                {"雍", "維", "雅"}, {"乾", "幹", "軒"},
                {"萬", "万"}, {"曆", "歷", "厤", "歴"},
                {"年", "牛", "午", "平"}, {"製", "制", "脊"},
                {"隆", "降", "窿", "融"},
                {"宣", "官", "宜"}, {"德", "徳", "得"},
                {"嘉", "喜", "家", "善"},
                {"玄", "去", "云", "元", "亢"},
                {"正", "政", "証", "征"},
                {"光", "先", "克", "充"},
                {"祥", "詳", "翔"},
                {"瑞", "端"},
                {"玉", "王", "主"},
                {"造", "迴", "遭"},
                {"壽", "寿"}, {"福", "富"},
                {"堂", "常", "當"},
            ]
            def _fuzzy_char_match(c1, c2):
                if c1 == c2:
                    return True
                for g in SIMILAR_GROUPS_ORB:
                    if c1 in g and c2 in g:
                        return True
                return False

            exact_overlap = len(all_evidence_chars & ref_chars)
            fuzzy_overlap = 0
            for ec in all_evidence_chars:
                for rc in ref_chars:
                    if _fuzzy_char_match(ec, rc):
                        fuzzy_overlap += 1
                        break
            overlap = max(exact_overlap, fuzzy_overlap)
            total_ref = len(ref_chars)
            print(f"[ORB verify] ocr_evidence={all_evidence_chars}, exact_overlap={exact_overlap}, fuzzy_overlap={fuzzy_overlap}, total_ref={total_ref}")

            if not all_evidence_chars:
                # OCR không đọc được gì → chỉ tin ORB khi ratio đủ cao
                if orb_ratio >= 1.3 and orb_best >= 80:
                    print(f"[ORB verify] No OCR but ORB ratio={orb_ratio:.2f} >= 1.3, trusting ORB.")
                    new_cr = _save_history(image_bytes, matched_report.get("chu_han", ""), matched_report)
                    if new_cr is not None: matched_report["credits"] = new_cr
                    return JSONResponse(status_code=200, content=matched_report)
                else:
                    print(f"[ORB verify] No OCR evidence AND ORB ratio={orb_ratio:.2f} too low. Discarding ORB.")
                    matched_report = None
            elif total_ref > 0 and overlap >= max(3, total_ref - 2):
                # Đủ ký tự trùng (fuzzy) → tin ORB
                print(f"[ORB verify] PASS — overlap sufficient ({overlap}/{total_ref}). Returning ORB match.")
                new_cr = _save_history(image_bytes, matched_report.get("chu_han", ""), matched_report)
                if new_cr is not None: matched_report["credits"] = new_cr
                return JSONResponse(status_code=200, content=matched_report)
            else:
                # Ký tự OCR mâu thuẫn với ORB → bỏ qua ORB, tiếp tục OCR
                print(f"[ORB verify] FAIL — OCR contradicts ORB ({overlap}/{total_ref}). Falling through to OCR pipeline.")
                matched_report = None

        if not ocr_text and not candidates:
            return JSONResponse(
                content={"success": False, "message": "Không đọc được chữ trong ảnh. Thử chụp rõ hơn.", "chu_han": "", "top5": [], "report": None}
            )

        print(f"OCR text: '{ocr_text}'")
        merged_candidates = _expand_ocr_candidates(ocr_text, candidates, blur_score=blur_score)
        max_candidate_len = max((len(_normalize_cjk(c)) for c in merged_candidates), default=0)
        has_any_dynasty_hint = any(
            any(prefix in _normalize_cjk(c) for prefix in ("大明", "大清", "大南"))
            for c in merged_candidates
        )
        if max_candidate_len <= 1 and not has_any_dynasty_hint:
            return JSONResponse(
                content={
                    "success": False,
                    "message": "Ảnh quá mờ hoặc chữ quá nhỏ, không đủ dữ liệu để xác định hiệu đề.",
                    "chu_han": "",
                    "top5": [],
                    "report": None,
                }
            )
        matches = rank_by_multi_candidates(merged_candidates, REIGN_DATABASE, top_n=5)
        if not matches:
            matches = find_best_matches(ocr_text, REIGN_DATABASE, top_n=5)

        dynasty_prefixes = _detect_dynasty_prefixes(merged_candidates)
        if dynasty_prefixes:
            filtered_matches = [
                m for m in matches
                if any(_normalize_cjk(m.get("chu_han", "")).startswith(prefix) for prefix in dynasty_prefixes)
            ]
            if filtered_matches:
                matches = filtered_matches
        has_year_signal = any("年" in _normalize_cjk(c) for c in merged_candidates)
        if has_year_signal:
            reign_matches = [m for m in matches if _is_year_mark_text(m.get("chu_han", ""))]
            if reign_matches:
                matches = reign_matches

        can_chi_evidence = _has_can_chi_evidence(merged_candidates)
        if can_chi_evidence:
            can_chi_matches = [m for m in matches if _is_can_chi_mark(m.get("chu_han", ""))]
            if can_chi_matches:
                matches.sort(key=lambda m: float(m.get("match_score", m.get("score", 0)) or 0), reverse=True)
                best_can_chi = max(
                    can_chi_matches,
                    key=lambda m: float(m.get("match_score", m.get("score", 0)) or 0),
                )
                best_can_chi_score = float(best_can_chi.get("match_score", best_can_chi.get("score", 0)) or 0)
                best_overall_score = float(matches[0].get("match_score", matches[0].get("score", 0)) or 0)
                if not _is_can_chi_mark(matches[0].get("chu_han", "")) and (best_overall_score - best_can_chi_score) <= 8.0:
                    matches = [best_can_chi] + [m for m in matches if m is not best_can_chi]

        for m in matches[:3]:
            print(f"  Match: {m.get('chu_han', '')} score={m.get('raw_score', 0):.4f}")

        # FIX Nội Phủ: Điều chỉnh score dựa trên chữ thứ 4 OCR đọc được
        # QUAN TRỌNG: Phải boost trên danh sách đầy đủ `matches` trước,
        # bởi vì nếu biến thể đúng bị văng khỏi top 5 từ sớm (do nhiễu OCR),
        # nó sẽ không bao giờ được phục hồi.
        import difflib as _difflib
        neifu_in_matches = any(
            ("內府" in _normalize_cjk(m.get("chu_han", "") or ""))
            or ("内府" in _normalize_cjk(m.get("chu_han", "") or ""))
            for m in (matches or [])
        )
        if neifu_in_matches:
            matches = _boost_neifu_match_score(
                merged_candidates, matches,
                _normalize_cjk,
                _difflib.SequenceMatcher,
            )
            # Re-slice top 5 sau khi đã boost lại điểm
            top5 = matches[:5]
        else:
            top5 = matches[:5]
            
            if dynasty_prefixes:
                filtered_top5 = [
                    m for m in top5
                    if any(_normalize_cjk(m.get("chu_han", "")).startswith(prefix) for prefix in dynasty_prefixes)
                ]
                if filtered_top5:
                    top5 = filtered_top5
        if has_year_signal:
            reign_top5 = [m for m in top5 if _is_year_mark_text(m.get("chu_han", ""))]
            if reign_top5:
                top5 = reign_top5

        if can_chi_evidence:
            can_chi_top5 = [m for m in top5 if _is_can_chi_mark(m.get("chu_han", ""))]
            if can_chi_top5:
                top5.sort(key=lambda m: float(m.get("match_score", m.get("score", 0)) or 0), reverse=True)
                best_can_chi = max(
                    can_chi_top5,
                    key=lambda m: float(m.get("match_score", m.get("score", 0)) or 0),
                )
                best_can_chi_score = float(best_can_chi.get("match_score", best_can_chi.get("score", 0)) or 0)
                best_overall_score = float(top5[0].get("match_score", top5[0].get("score", 0)) or 0)
                if not _is_can_chi_mark(top5[0].get("chu_han", "")) and (best_overall_score - best_can_chi_score) <= 8.0:
                    top5 = [best_can_chi] + [m for m in top5 if m is not best_can_chi]

        ocr_clean = _normalize_cjk(ocr_text)
        ocr_len = len(ocr_clean)
        is_short_dynasty = ocr_clean in {"大明", "大清", "大南"}

        if is_short_dynasty:
            orb_match, orb_score = match_image_by_prefix(image_bytes, [ocr_clean])
            if orb_match:
                print(f"ORB Prefix Match: {orb_score} good matches for {ocr_clean}")
                new_cr = _save_history(image_bytes, orb_match.get("chu_han", ""), orb_match)
                if new_cr is not None: orb_match["credits"] = new_cr
                return JSONResponse(status_code=200, content=orb_match)
            return JSONResponse(
                content={"success": False, "message": "Khong du thong tin de xac dinh. Vui long chup lai ro hon.", "chu_han": "", "top5": [], "report": None}
            )

        if ocr_len > 2:
            longer_matches = [item for item in top5 if len(_normalize_cjk(item.get("chu_han", ""))) > 2]
            if longer_matches:
                top5 = longer_matches

        # Không đảo thứ hạng dựa trên tỷ lệ không rõ ràng (bỏ logic swap cũ dễ gây lỗi)

        selected_report = top5[0] if top5 else None
        if selected_report and not selected_report.get("hien_thi_chinh"):
            lookup_key = selected_report.get("chu_han")
            if lookup_key:
                for entry in REIGN_DATABASE:
                    if entry.get("chu_han") == lookup_key or entry.get("chu_han_4") == lookup_key:
                        selected_report = {**entry, **selected_report}
                        break

        if selected_report:
            if has_year_signal and not _is_year_mark_text(selected_report.get("chu_han", "")):
                return JSONResponse(
                    content={
                        "success": False,
                        "message": "Kết quả hiện tại không đủ dấu hiệu của hiệu đề niên chế (年製/年造). Vui lòng thử ảnh rõ hơn.",
                        "chu_han": "",
                        "top5": top5,
                        "report": None,
                    }
                )
            evidence_overlap = _max_char_overlap(merged_candidates, selected_report.get("chu_han", ""))
            model_score = float(selected_report.get("raw_score", selected_report.get("score", 0)) or 0)
            # Chặn trả sai khi OCR quá yếu (vd chỉ 1-2 ký tự nhiễu nhưng vẫn match vào DB).
            if evidence_overlap < 2 and model_score < 0.8:
                return JSONResponse(
                    content={
                        "success": False,
                        "message": "Không đủ bằng chứng để xác định chính xác hiệu đề. Vui lòng thử ảnh rõ hơn hoặc chụp thẳng, đủ sáng phần đáy.",
                        "chu_han": "",
                        "top5": top5,
                        "report": None,
                    }
                )
            # Deep mode thường sinh kết quả ngắn gây nhầm triều đại; yêu cầu chứng cứ mạnh hơn.
            if bool(deep_mode):
                selected_clean = _normalize_cjk(selected_report.get("chu_han", ""))
                has_dynasty_hint = bool(dynasty_prefixes) or any(
                    p in selected_clean for p in ("大明", "大清", "大南")
                )
                support_votes = _support_votes_for_match(merged_candidates, selected_clean)
                is_neifu_mark = ("內府" in selected_clean) or ("内府" in selected_clean)
                runner_up_score = 0.0
                if top5 and len(top5) > 1:
                    runner_up_score = float(top5[1].get("score", top5[1].get("match_score", 0)) or 0)
                selected_score = float(selected_report.get("score", selected_report.get("match_score", 0)) or 0)
                neifu_is_clear_winner = is_neifu_mark and (selected_score - runner_up_score >= 10.0)
                if neifu_is_clear_winner:
                    support_votes = max(support_votes, 2)
                print(
                    "[deep_gate]",
                    f"selected={selected_clean}",
                    f"overlap={evidence_overlap}",
                    f"votes={support_votes}",
                    f"score={selected_score:.1f}",
                    f"runner_up={runner_up_score:.1f}",
                    f"dynasty_hint={has_dynasty_hint}",
                )
                if is_neifu_mark and selected_score >= 70.0:
                    pass
                elif len(selected_clean) <= 4 and not has_dynasty_hint and (evidence_overlap < 3 and support_votes < 2):
                    return JSONResponse(
                        content={
                            "success": False,
                            "message": "Ảnh quá mờ, hệ thống chưa đủ chắc chắn để kết luận chính xác hiệu đề.",
                            "chu_han": "",
                            "top5": top5,
                            "report": None,
                        }
                    )

        display_text = _choose_display_mark(selected_report, merged_candidates, ocr_text)

        new_cr = _save_history(image_bytes, display_text, selected_report)

        response_content = {
            "success": True,
            "chu_han": display_text,
            "confidence": result.get("confidence", 0),
            "top5": top5,
            "report": selected_report,
        }
        if new_cr is not None:
            response_content["credits"] = new_cr

        return JSONResponse(content=response_content)

    except Exception as e:
        import traceback
        try:
            print("ERROR:", traceback.format_exc())
        except Exception:
            print("ERROR: (traceback contains unencodable characters)")
        err_msg = str(e).encode('ascii', errors='replace').decode('ascii')
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Loi xu ly OCR: {err_msg}", "chu_han": "", "error": err_msg},
        )


@app.post("/memorize")
async def memorize_endpoint(
    file: UploadFile = File(...),
    report_data: str = Form(...),
):
    try:
        if not file:
            return JSONResponse(status_code=400, content={"success": False, "message": "No image"})
        image_bytes = await file.read()
        json_data = json.loads(report_data)
        saved = save_reference(image_bytes, json_data)
        if saved:
            return JSONResponse(status_code=200, content={"success": True, "message": "Đã lưu thành công vào thư viện tham chiếu!"})
        else:
            return JSONResponse(status_code=500, content={"success": False, "message": "Không thể lưu ảnh mẫu."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

@app.post("/api/confirm-learning")
async def confirm_learning(request: Request):
    """Auto-Learning: Khi user xác nhận kết quả đúng, lưu ảnh vào thư viện tham chiếu.
    Lần sau gặp ảnh tương tự → ORB khớp ngay, không cần OCR."""
    try:
        body = await request.json()
        report_data = body.get("report", {})
        user_token = request.headers.get("Authorization", "anonymous")
        
        image_bytes = _last_analyzed_images.get(user_token)
        if not image_bytes:
            return JSONResponse(status_code=400, content={"success": False, "message": "Không tìm thấy ảnh. Vui lòng phân tích lại."})
        
        if not report_data or not report_data.get("chu_han"):
            return JSONResponse(status_code=400, content={"success": False, "message": "Thiếu dữ liệu hiệu đề."})
        
        saved = save_reference(image_bytes, report_data)
        if saved:
            # Xóa cache sau khi lưu
            _last_analyzed_images.pop(user_token, None)
            from reference_matcher import _reference_cache
            ref_count = len(_reference_cache)
            print(f"[Auto-Learning] Saved '{report_data.get('chu_han')}' to reference library. Total refs: {ref_count}")
            return JSONResponse(status_code=200, content={
                "success": True, 
                "message": f"Đã học thành công! Thư viện hiện có {ref_count} mẫu tham chiếu.",
                "ref_count": ref_count
            })
        else:
            return JSONResponse(status_code=500, content={"success": False, "message": "Không thể lưu mẫu."})
    except Exception as e:
        print(f"[Auto-Learning] Error: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

# API cho User
@app.post("/register")
def register_user(user: UserRegister):
    existing = get_user_by_username(user.username)
    if existing:
        return JSONResponse(status_code=400, content={"success": False, "message": "Tên người dùng đã tồn tại."})
    
    hashed_password = pwd_context.hash(user.password)
    success = create_user(user.username, hashed_password)
    if success:
        return {"success": True, "message": "Đăng ký thành công!"}
    return JSONResponse(status_code=500, content={"success": False, "message": "Lỗi hệ thống."})

@app.post("/login")
def login_user(user: UserLogin):
    db_user = get_user_by_username(user.username)
    if not db_user or not pwd_context.verify(user.password, db_user['password_hash']):
        return JSONResponse(status_code=401, content={"success": False, "message": "Sai tài khoản hoặc mật khẩu."})
    
    # Kiểm tra tài khoản bị khóa
    if db_user.get('locked'):
        return JSONResponse(status_code=403, content={"success": False, "message": "Tài khoản của bạn đã bị khóa. Vui lòng liên hệ quản trị viên."})
    
    credits = get_user_credits(db_user['id'])
    role = db_user.get('role', 'user') or 'user'
    return {"success": True, "token": str(db_user['id']), "username": db_user['username'], "credits": credits, "role": role}

class SocialLoginRequest(BaseModel):
    email: str
    name: str
    provider: str  # 'Google' hoặc 'Facebook'

@app.post("/social-login")
def social_login(data: SocialLoginRequest):
    """Đăng nhập bằng Google hoặc Facebook - tạo tài khoản tự động nếu chưa có."""
    user = get_or_create_social_user(data.email, data.name, data.provider)
    if user:
        credits = get_user_credits(user['id'])
        return {
            "success": True, 
            "token": str(user['id']), 
            "username": user['username'],
            "name": data.name,
            "credits": credits,
            "message": f"Đăng nhập {data.provider} thành công!"
        }
    return JSONResponse(status_code=500, content={"success": False, "message": "Lỗi hệ thống khi xử lý đăng nhập."})

@app.get("/api/history")
def get_history_api(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={"success": False, "message": "Chưa đăng nhập."},
            headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "Pragma": "no-cache"},
        )
    
    user_id = auth_header.split("Bearer ")[1]
    history = get_scan_history(user_id)
    return JSONResponse(
        content={"success": True, "history": history},
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "Pragma": "no-cache"},
    )

@app.get("/api/library")
def get_library_api():
    marks = _load_database()
    return JSONResponse(
        content=marks,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        },
    )

@app.get("/api/credits")
def get_credits(request: Request):
    """Lấy số lượt phân tích còn lại."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"success": False, "message": "Chưa đăng nhập."})
    user_id = auth_header.split("Bearer ")[1]
    credits = get_user_credits(int(user_id))
    return JSONResponse(content={"success": True, "credits": credits}, headers={"Cache-Control": "no-store"})

class BuyCreditsRequest(BaseModel):
    package: str  # 'pro' or 'enterprise'
    payment_method: str = "bank"  # bank, momo, atm

def get_packages_config():
    settings = get_system_settings()
    return {
        'pro': {
            'name': 'Phổ biến', 
            'credits': int(settings.get('pkg_pro_credits', 200)), 
            'amount': int(settings.get('pkg_pro_price', 499999))
        },
        'enterprise': {
            'name': 'Chuyên nghiệp', 
            'credits': int(settings.get('pkg_enterprise_credits', 99999)), 
            'amount': int(settings.get('pkg_enterprise_price', 2490000))
        }
    }

@app.get("/api/v1/packages")
def api_get_packages():
    return JSONResponse(
        content={"success": True, "packages": get_packages_config()},
        headers={"Cache-Control": "no-store"},
    )

# Cấu hình thanh toán SePay
SEPAY_API_KEY = "YOUR_SEPAY_API_KEY"
ACCOUNT_NUMBER = "0852641851"
BANK_ID = "OCB"
BANK_BIN = "970448"
ACCOUNT_NAME = "TRUONG XUA"
NAME_WEB = "HIEUDEAI"
SECRET_XOR_KEY = 0x5EAFB

def encode_payment_id(p_id: int) -> str:
    return hex(p_id ^ SECRET_XOR_KEY)[2:].upper()

def _emv_field(field_id: str, value: str) -> str:
    value = str(value or "")
    return f"{field_id}{len(value):02d}{value}"

def _crc16_ccitt_false(payload: str) -> str:
    crc = 0xFFFF
    for byte in payload.encode("ascii", errors="ignore"):
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"

def _build_vietqr_payload(amount: int, content: str) -> str:
    beneficiary = _emv_field("00", BANK_BIN) + _emv_field("01", ACCOUNT_NUMBER)
    merchant_account = (
        _emv_field("00", "A000000727")
        + _emv_field("01", beneficiary)
        + _emv_field("02", "QRIBFTTA")
    )
    payload = (
        _emv_field("00", "01")
        + _emv_field("01", "12")
        + _emv_field("38", merchant_account)
        + _emv_field("53", "704")
        + _emv_field("54", str(int(amount)))
        + _emv_field("58", "VN")
        + _emv_field("59", ACCOUNT_NAME[:25])
        + _emv_field("60", "CAN THO")
        + _emv_field("62", _emv_field("08", content[:99]))
    )
    payload_for_crc = payload + "6304"
    return payload_for_crc + _crc16_ccitt_false(payload_for_crc)

def _create_local_payment_qr(payment_id: int, amount: int, content: str) -> Optional[str]:
    try:
        qr_payload = _build_vietqr_payload(amount, content)
        encoder = cv2.QRCodeEncoder_create()
        qr = encoder.encode(qr_payload)
        if qr is None or getattr(qr, "size", 0) == 0:
            return None
        qr = cv2.copyMakeBorder(qr, 16, 16, 16, 16, cv2.BORDER_CONSTANT, value=255)
        qr = cv2.resize(qr, (620, 620), interpolation=cv2.INTER_NEAREST)
        qr_dir = os.path.join("uploads", "payment_qr")
        os.makedirs(qr_dir, exist_ok=True)
        filename = f"payment_{payment_id}.png"
        path = os.path.join(qr_dir, filename)
        if not cv2.imwrite(path, qr):
            return None
        return f"/uploads/payment_qr/{filename}"
    except Exception as exc:
        print(f"[Payment] Could not create local VietQR: {exc}")
        return None

@app.post("/api/v1/payment/create")
async def create_payment_api(req: BuyCreditsRequest, request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"success": False, "message": "Chưa đăng nhập."})
    user_id = int(auth_header.split("Bearer ")[1])
    if not get_user_by_id(user_id):
        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "session_expired": True,
                "message": "Phiên đăng nhập cũ không còn tồn tại sau khi chuyển sang SQLite. Vui lòng đăng nhập lại.",
            },
        )
    
    packages = get_packages_config()
    pkg = packages.get(req.package)
    if not pkg:
        return JSONResponse(status_code=400, content={"error": "Gói không hợp lệ"})
    
    payment_id = create_payment(user_id, pkg["amount"], pkg["credits"])
    if payment_id is None:
        return JSONResponse(status_code=500, content={"error": "Khong the luu giao dich vao SQLite database."})
    
    hex_id = encode_payment_id(payment_id)
    content = f"{NAME_WEB}NAPTOKEN{hex_id}"
    method_labels = {
        "bank": "Bank Transfer via SePay",
        "momo": "MoMo QR via SePay",
        "atm": "ATM / Internet Banking via SePay",
    }
    payment_method = (req.payment_method or "bank").lower().strip()
    if payment_method not in method_labels:
        payment_method = "bank"
    
    vietqr_url = f"https://img.vietqr.io/image/{BANK_ID}-{ACCOUNT_NUMBER}-compact2.png?amount={pkg['amount']}&addInfo={content}"
    qr_url = _create_local_payment_qr(payment_id, pkg["amount"], content) or vietqr_url
    
    return {
        "success": True,
        "payment_id": payment_id,
        "hex_id": hex_id,
        "amount": pkg["amount"],
        "content": content,
        "qr_url": qr_url,
        "vietqr_url": vietqr_url,
        "payment_method": payment_method,
        "payment_label": method_labels[payment_method]
    }

@app.get("/api/v1/payment/status/{payment_id}")
async def check_payment_status(payment_id: int):
    payment = get_payment(payment_id)
    if not payment: return JSONResponse(status_code=404, content={"error": "Không tìm thấy"})
    if payment['status'] == 'completed':
         return {"status": "completed"}
         
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get("https://my.sepay.vn/userapi/transactions/list", 
                headers={"Authorization": f"Bearer {SEPAY_API_KEY}"})
            data = resp.json()
            transactions = data.get("transactions", [])
        except Exception as e:
            return {"status": "pending", "message": "Đang kết nối ngân hàng..."}
        
        target_hex = encode_payment_id(payment_id)
        pattern = rf"{NAME_WEB}NAPTOKEN([A-Fa-f0-9]+)"
        
        for tx in transactions:
            content = tx.get("transaction_content", "")
            amount_in = float(tx.get("amount_in", 0))
            
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                found_hex = match.group(1).upper()
                if found_hex == target_hex and amount_in >= payment['amount_vnd']:
                    success = complete_payment(payment_id, tx.get("id"))
                    if success:
                        add_credits(payment['user_id'], payment['credits'])
                        return {"status": "completed"}
                        
    return {"status": "pending"}

@app.post("/api/v1/payment/mock/{payment_id}")
async def mock_payment(payment_id: int):
    """API giả lập thanh toán thành công dành cho Developer"""
    payment = get_payment(payment_id)
    if not payment: return JSONResponse(status_code=404, content={"error": "Hóa đơn không tồn tại"})
    
    if payment['status'] == 'pending':
        # Giả lập mã giao dịch ngân hàng là một số ngẫu nhiên lớn
        import random
        mock_tx_id = random.randint(10000000, 99999999)
        
        success = complete_payment(payment_id, mock_tx_id)
        if success:
            add_credits(payment['user_id'], payment['credits'])
            return {"status": "completed", "message": "Giả lập thanh toán thành công!"}
    
    return {"status": payment['status']}

@app.get("/api/v1/user/payments")
def user_payments_api(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"error": "Not authenticated"})
    
    user_id = auth_header.split("Bearer ")[1]
    payments = get_user_payments(user_id)
    return {"success": True, "payments": payments}

@app.post("/api/buy-credits")
def buy_credits(data: BuyCreditsRequest, request: Request):
    """Mua thêm lượt phân tích (giả lập thanh toán)."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"success": False, "message": "Chưa đăng nhập."})
    user_id = auth_header.split("Bearer ")[1]
    
    packages = get_packages_config()
    pkg = packages.get(data.package)
    if not pkg:
        return JSONResponse(status_code=400, content={"success": False, "message": "Gói không hợp lệ."})
    
    success = add_credits(int(user_id), pkg['credits'])
    if success:
        new_credits = get_user_credits(int(user_id))
        return {"success": True, "credits": new_credits, "added": pkg['credits'], "package_name": pkg['name'], "message": f"Đã thêm {pkg['credits']} lượt phân tích!"}
    return JSONResponse(status_code=500, content={"success": False, "message": "Lỗi hệ thống."})

class ChatMessage(BaseModel):
    message: str

class ContactMessage(BaseModel):
    name: str
    email: str
    message: str

def _chat_fold(text: str) -> str:
    text = (text or "").lower().strip()
    text = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")

def _fallback_chat_reply(msg: str) -> str:
    words = msg.split()
    if any(k in msg for k in ["hello", "xin chao", "chao"]) or "hi" in words:
        return "Hello! I am the HieuDe AI Assistant. I can help with ceramic mark recognition, scan credits, upgrade plans, account support, and image-capture tips."
    if any(k in msg for k in ["hieu de", "mark", "reign mark", "bottom mark", "chinese character", "chu han", "meaning"]):
        return "A ceramic reign mark is the inscription or seal usually found on the base of a porcelain object. It may show the dynasty, reign period, workshop, imperial attribution, or maker mark."
    if any(k in msg for k in ["how to", "guide", "scan", "analyze", "analysis", "kiem tra", "quet", "phan tich", "su dung", "lam sao"]):
        return "To analyze a mark, upload a clear photo of the base mark from the Home page, keep the camera square to the object, avoid glare, and make sure the seal or brush strokes are sharp."
    if any(k in msg for k in ["buy", "purchase", "price", "upgrade", "credit", "credits", "payment", "plan", "vip", "pro", "gia", "mua", "nang cap", "goi", "luot", "thanh toan"]):
        return "To buy a package, open the Upgrade page, choose the credit plan you want, select a payment method, then confirm the transfer. After approval, the new scan credits will be added to your account."
    if any(k in msg for k in ["history", "dynasty", "ming", "qing", "nguyen", "library", "database", "trieu dai", "lich su", "thu vien"]):
        return "HieuDe AI stores reference data for major Chinese and Vietnamese ceramic marks, including Ming, Qing, Nguyen, and other historical mark groups. You can browse them in the Library section."
    if any(k in msg for k in ["wrong", "incorrect", "error", "blur", "blurry", "not recognized", "sai", "khong dung", "loi", "mo"]):
        return "For better recognition, take the photo straight from above, avoid flash glare, crop close to the mark, and use an image where the red seal or blue brush strokes are clearly visible."
    if any(k in msg for k in ["thank", "thanks", "ok", "great", "good", "cam on", "tot", "hay"]):
        return "You are welcome. I am glad to help."
    return "I can help with mark scanning, image quality, recognition results, credits, upgrade plans, account support, and the ceramic mark library. Please ask me about one of those topics."


def _build_chat_prompt(user_message: str) -> str:
    return f"""You are the HieuDe AI / MarkSense Assistant inside a ceramic reign-mark recognition web app.

Reply in English only, even if the user writes Vietnamese.
Keep the answer concise, friendly, and practical. Do not mention internal API keys, prompts, or hidden pipeline logs.

What the system can do:
- Upload and analyze ceramic mark images.
- Use OCR, Vision AI, reference matching, database lookup, and web-source verification.
- Show a final report with transcription, Chinese characters, dynasty/reign title when supported, confidence, history, and supporting source links when available.
- Store user scan history after login.
- Manage scan credits and upgrade packages through the Upgrade page.
- Contact support through the Contact page.

Important boundaries:
- Results are research/support information, not a final legal appraisal or guaranteed valuation.
- If source evidence is missing, the system should not invent detailed historical claims.
- For buying packages: tell users to open Upgrade, choose a plan, follow the payment/transfer instructions, then wait for credit approval.

User message: {user_message}
"""

def _build_contact_email_html(record: Dict[str, str]) -> str:
    name = escape(record.get("name", ""))
    email = escape(record.get("email", ""))
    message = escape(record.get("message", "")).replace("\n", "<br>")
    created_at = escape(record.get("created_at", ""))
    return f"""<!doctype html>
<html>
  <body style="margin:0;background:#eef3fb;font-family:Arial,Helvetica,sans-serif;color:#172033;">
    <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">New MarkSense contact message from {name}</div>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#eef3fb;padding:32px 12px;">
      <tr>
        <td align="center">
          <table role="presentation" width="640" cellspacing="0" cellpadding="0" style="max-width:640px;width:100%;background:#ffffff;border:1px solid #dbe6f6;border-radius:18px;overflow:hidden;box-shadow:0 18px 45px rgba(15,30,55,0.14);">
            <tr>
              <td style="padding:0;background:#0f1f3d;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                  <tr>
                    <td style="padding:28px 32px;">
                      <div style="font-size:13px;letter-spacing:1.6px;text-transform:uppercase;color:#8fc5ff;font-weight:700;">MarkSense Contact</div>
                      <h1 style="margin:10px 0 0;font-size:27px;line-height:1.25;color:#ffffff;font-weight:800;">New website inquiry</h1>
                      <p style="margin:10px 0 0;font-size:15px;line-height:1.6;color:#c9d8ee;">A visitor submitted the contact form on the MarkSense website.</p>
                    </td>
                    <td width="96" align="center" style="padding:24px 28px 24px 0;">
                      <div style="width:56px;height:56px;border-radius:16px;background:#2563eb;color:#ffffff;font-size:24px;font-weight:800;line-height:56px;text-align:center;">M</div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:28px 32px 26px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                  <tr>
                    <td style="padding:18px 20px;background:#f6f9fe;border:1px solid #e0e9f7;border-radius:14px;">
                      <div style="font-size:12px;text-transform:uppercase;letter-spacing:1px;color:#64748b;font-weight:800;">Contact details</div>
                      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-top:14px;">
                        <tr>
                          <td style="font-size:13px;color:#718096;width:90px;padding:4px 0;">Name</td>
                          <td style="font-size:16px;color:#0f172a;font-weight:700;padding:4px 0;">{name}</td>
                        </tr>
                        <tr>
                          <td style="font-size:13px;color:#718096;width:90px;padding:4px 0;">Email</td>
                          <td style="font-size:15px;color:#2563eb;font-weight:700;padding:4px 0;"><a href="mailto:{email}" style="color:#2563eb;text-decoration:none;">{email}</a></td>
                        </tr>
                        <tr>
                          <td style="font-size:13px;color:#718096;width:90px;padding:4px 0;">Received</td>
                          <td style="font-size:14px;color:#334155;padding:4px 0;">{created_at}</td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                  <tr><td style="height:16px;"></td></tr>
                  <tr>
                    <td style="padding:20px 20px;background:#ffffff;border:1px solid #dbe6f6;border-radius:14px;">
                      <div style="font-size:12px;text-transform:uppercase;letter-spacing:1px;color:#64748b;font-weight:800;margin-bottom:12px;">Message</div>
                      <div style="font-size:16px;line-height:1.7;color:#172033;">{message}</div>
                    </td>
                  </tr>
                  <tr><td style="height:22px;"></td></tr>
                  <tr>
                    <td>
                      <a href="mailto:{email}" style="display:inline-block;background:#2563eb;color:#ffffff;text-decoration:none;font-weight:800;padding:13px 20px;border-radius:10px;">Reply to sender</a>
                      <span style="display:inline-block;margin-left:12px;font-size:13px;color:#64748b;">Sent from the MarkSense contact form</span>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:18px 32px;background:#f8fafc;color:#64748b;font-size:12px;line-height:1.55;border-top:1px solid #e2e8f0;">
                This automated email was generated by MarkSense. You can reply directly to the sender using the button above.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""


def _send_contact_email(record: Dict[str, str]) -> None:
    from config import (
        CONTACT_FROM_EMAIL,
        CONTACT_RECIPIENT,
        CONTACT_SMTP_HOST,
        CONTACT_SMTP_PASSWORD,
        CONTACT_SMTP_PORT,
        CONTACT_SMTP_USER,
    )

    if not CONTACT_SMTP_HOST or not CONTACT_SMTP_USER or not CONTACT_SMTP_PASSWORD:
        raise RuntimeError("SMTP is not configured. Please check CONTACT_SMTP_* in .env.")

    sender = CONTACT_FROM_EMAIL or CONTACT_SMTP_USER
    subject_name = (record.get("name") or "Website visitor").strip()
    msg = EmailMessage()
    msg["Subject"] = f"HieuDe AI Contact Request - {subject_name}"
    msg["From"] = f"HieuDe AI Contact <{sender}>"
    msg["To"] = CONTACT_RECIPIENT
    msg["Reply-To"] = record.get("email", "")
    text_body = (
        "New HieuDe AI contact message\n\n"
        f"Name: {record.get('name', '')}\n"
        f"Email: {record.get('email', '')}\n"
        f"Received: {record.get('created_at', '')}\n\n"
        f"{record.get('message', '')}\n"
    )
    msg.set_content(text_body)
    msg.add_alternative(_build_contact_email_html(record), subtype="html")

    with smtplib.SMTP(CONTACT_SMTP_HOST, CONTACT_SMTP_PORT, timeout=20) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(CONTACT_SMTP_USER, CONTACT_SMTP_PASSWORD)
        smtp.send_message(msg)

@app.post("/api/chat")
async def chat_bot(data: ChatMessage):
    msg = _chat_fold(data.message)
    resp = None
    try:
        from services.llm_service import call_llm
        resp = await call_llm(
            _build_chat_prompt(data.message.strip()),
            temperature=0.2,
            max_tokens=220,
            retry=0,
        )
    except Exception as exc:
        print(f"[Chat] LLM unavailable, using fallback: {exc}")
    if not resp:
        resp = _fallback_chat_reply(msg)
    return {"reply": resp}


@app.post("/contact/send")
async def send_contact_message(data: ContactMessage):
    name = (data.name or "").strip()
    email = (data.email or "").strip()
    message = (data.message or "").strip()
    if not name or not email or not message:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "Please fill in all contact fields."},
        )

    contact_path = os.path.join(os.path.dirname(__file__), "data", "contact_messages.jsonl")
    os.makedirs(os.path.dirname(contact_path), exist_ok=True)
    record = {
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "name": name,
        "email": email,
        "message": message,
        "to": "xuatruong30@gmail.com",
    }
    try:
        with open(contact_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Could not save message: {exc}"},
        )

    try:
        _send_contact_email(record)
    except Exception as exc:
        return JSONResponse(
            status_code=502,
            content={
                "success": False,
                "message": f"Message was saved, but email delivery failed: {exc}",
            },
        )

    return {"success": True, "message": "Message sent to xuatruong30@gmail.com."}


async def _unused_old_chat_block():
    msg = data.message.lower().strip()
    words = msg.split()
    if any(k in msg for k in ["chào", "hello", "xin chào"]) or "hi" in words:
        resp = "Chào bạn! Tôi là trợ lý HieuDe AI. Tôi có thể giúp bạn giải đáp các thông tin về nhận dạng hiệu đề gốm sứ và hỗ trợ sử dụng hệ thống."
    elif any(k in msg for k in ["hiệu đề là gì", "hiệu đề", "đáy gốm", "chữ hán", "khái niệm", "ý nghĩa"]):
        resp = "Hiệu đề là dòng chữ nhỏ in dưới đáy các món đồ gốm sứ (thường gồm 4 hoặc 6 chữ Hán/Nôm), chỉ rõ niên hiệu của triều đại hoàng đế trị vì hoặc phiên hiệu xưởng sản xuất."
    elif any(k in msg for k in ["cách dùng", "hướng dẫn", "giám định", "kiểm tra", "quét", "phân tích", "chỉ tôi", "làm sao", "làm thế nào", "sử dụng", "tìm hiểu"]):
        resp = "Rất đơn giản! Bạn chỉ cần ấn vào khu vực Khu Vực Tải Ảnh (Trang chủ) và chọn bức ảnh chụp rõ mặt chữ ở đáy gốm. Trí tuệ nhân tạo sẽ lập tức dịch từng mảng nhỏ và phân tích sâu vào bối cảnh lịch sử cho bạn!"
    elif any(k in msg for k in ["giá", "nâng cấp", "lượt", "bao nhiêu", "tiền", "mua", "vip", "pro", "thanh toán", "gói cước"]):
        resp = "Tài khoản mới sẽ có sẵn một số lượt phân tích. Nếu cần nhiều hơn, bạn có thể Nâng cấp tài khoản. Gói Chuyên Nghiệp (17$/tháng) tặng 200 lượt phân tích tốc độ cao. Gói Tối Đa (100$/tháng) cho phép quét không giới hạn."
    elif any(k in msg for k in ["lịch sử", "triều đại", "minh", "thanh", "nguyễn", "nhà minh", "nhà thanh", "thư viện", "dữ liệu"]):
        resp = "Dữ liệu HieuDe AI lưu trữ lịch sử hàng trăm hiệu đề lớn nhỏ suốt các triều Đại Minh, Đại Thanh (Trung Quốc) lẫn dòng gốm ngự dụng nhà Nguyễn (Việt Nam). Bạn có thể bấm sang 'Thư viện' để xem bộ Bách Khoa Toàn Thư nhé."
    elif any(k in msg for k in ["sai", "không đúng", "lỗi", "mờ", "không nhận ra", "không dịch được"]):
        resp = "Để tăng tối đa độ chính xác (OCR), bạn vui lòng chụp ảnh căn góc từ trên xuống, hạn chế ánh đèn flash chiếu lóa bề mặt sứ và đảm bảo các vết mực rạn phải rõ nét nhất có thể."
    elif any(k in msg for k in ["cảm ơn", "thanks", "ok", "tuyệt", "hay", "tốt", "hiểu rồi"]):
        resp = "Dạ, rất vui được hỗ trợ! Chúc bạn có những phiên tiếp cận cổ vật thật xuất sắc."
    else:
        resp = "Trợ lý ảo hiện đang ở phiên bản hỗ trợ cơ bản. Bạn hãy thử dùng lại các từ khoá đơn giản: 'cách phân tích', 'giá cước', 'hiệu đề là gì?', hoặc 'thông tin triều đại' để mình hỗ trợ nhé!"

    import asyncio
    await asyncio.sleep(0.6) # Giả lập delay suy nghĩ
    return {"reply": resp}


# ========== ADMIN API ENDPOINTS ==========

class AdminLogin(BaseModel):
    username: str
    password: str

class AdminCreditUpdate(BaseModel):
    user_id: int
    amount: int
    action: str = 'add'  # 'add', 'subtract', 'set'

class AdminResetPassword(BaseModel):
    user_id: int
    new_password: str

class AdminMarkData(BaseModel):
    chu_han: str = ''
    chu_han_4: str = ''
    chu_han_6: str = ''
    bien_the: list = []
    phien_am: str = ''
    ten_viet: str = ''
    hoang_de: str = ''
    trieu_dai: str = ''
    nam_bat_dau: Optional[int] = None
    nam_ket_thuc: Optional[int] = None
    ghi_chu: str = ''
    hien_thi_chinh: str = ''
    nien_hieu: str = ''
    nien_dai: str = ''
    hieu_de_en: str = ''
    mo_ta: str = ''
    hieu_de_vi: str = ''
    thu_phap: str = ''
    nghe_thuat: str = ''

class AdminSettingUpdate(BaseModel):
    key: str
    value: str

class AdminApplyFreeCredits(BaseModel):
    amount: int

class AdminPageOverridesUpdate(BaseModel):
    overrides: Dict[str, List[Dict[str, Any]]]

class AdminAppPageUpdate(BaseModel):
    edits: List[Dict[str, Any]]

def _load_page_overrides() -> Dict[str, List[Dict[str, Any]]]:
    try:
        if not os.path.exists(PAGE_OVERRIDES_PATH):
            return {}
        with open(PAGE_OVERRIDES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"[Admin] Error loading page overrides: {e}")
        return {}

def _save_page_overrides(overrides: Dict[str, List[Dict[str, Any]]]) -> bool:
    try:
        os.makedirs(os.path.dirname(PAGE_OVERRIDES_PATH), exist_ok=True)
        with open(PAGE_OVERRIDES_PATH, "w", encoding="utf-8") as f:
            json.dump(overrides, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[Admin] Error saving page overrides: {e}")
        return False

def _get_app_page_path(page_id: str) -> Optional[str]:
    filename = APP_PAGE_FILES.get(page_id)
    if not filename:
        return None
    path = os.path.abspath(os.path.join(MOBILE_SRC_DIR, filename))
    if not path.startswith(MOBILE_SRC_DIR + os.sep):
        return None
    return path if os.path.exists(path) else None

def _decode_js_string(value: str) -> str:
    try:
        import ast
        return ast.literal_eval("'" + value.replace("'", "\\'") + "'")
    except Exception:
        return value

def _extract_app_page_fields(source: str) -> List[Dict[str, Any]]:
    fields: List[Dict[str, Any]] = []
    seen = set()

    def add_field(kind: str, label: str, value: str, start: int, end: int):
        text = _decode_js_string(value)
        if not text or len(text.strip()) < 2:
            return
        if kind != "media" and text.startswith(("../", "./", "http://", "https://")):
            return
        if kind != "media" and re.fullmatch(r"[A-Za-z0-9_\-./]+", text) and (" " not in text and len(text) < 18):
            return
        key = (start, end)
        if key in seen:
            return
        seen.add(key)
        fields.append({
            "type": kind,
            "label": label,
            "rootSelector": "app-source",
            "path": f"source:{start}:{end}",
            "start": start,
            "end": end,
            "value": text,
            "current": text,
        })

    # L('English text', 'Vietnamese text')
    l_call = re.compile(r"\bL\(\s*(['\"])((?:\\.|(?!\1).)*?)\1\s*,\s*(['\"])((?:\\.|(?!\3).)*?)\3", re.S)
    for index, match in enumerate(l_call.finditer(source), 1):
        add_field("text", f"L en #{index}", match.group(2), match.start(2), match.end(2))
        add_field("text", f"L vi #{index}", match.group(4), match.start(4), match.end(4))

    # placeholder="..."
    placeholder = re.compile(r"\bplaceholder\s*=\s*(['\"])((?:\\.|(?!\1).)*?)\1", re.S)
    for index, match in enumerate(placeholder.finditer(source), 1):
        add_field("placeholder", f"placeholder #{index}", match.group(2), match.start(2), match.end(2))

    # import imageName from '../../assets/image.png'
    asset_import = re.compile(r"\bimport\s+\w+\s+from\s+(['\"])((?:\\.|(?!\1).)*?\.(?:png|jpe?g|webp|gif))\1", re.I | re.S)
    for index, match in enumerate(asset_import.finditer(source), 1):
        add_field("media", f"asset import #{index}", match.group(2), match.start(2), match.end(2))

    # require('../../assets/image.png')
    asset_require = re.compile(r"\brequire\(\s*(['\"])((?:\\.|(?!\1).)*?\.(?:png|jpe?g|webp|gif))\1\s*\)", re.I | re.S)
    for index, match in enumerate(asset_require.finditer(source), 1):
        add_field("media", f"asset require #{index}", match.group(2), match.start(2), match.end(2))

    # source={{ uri: 'https://...' }}
    image_uri = re.compile(r"\buri\s*:\s*(['\"])((?:\\.|(?!\1).)*?)\1", re.S)
    for index, match in enumerate(image_uri.finditer(source), 1):
        add_field("media", f"image uri #{index}", match.group(2), match.start(2), match.end(2))

    # <Text>Plain text</Text>
    text_node = re.compile(r"<Text\b[^>]*>\s*([^<>{}\n][^<>{}]*)\s*</Text>", re.S)
    for index, match in enumerate(text_node.finditer(source), 1):
        value = re.sub(r"\s+", " ", match.group(1)).strip()
        if value:
            add_field("text", f"Text #{index}", value, match.start(1), match.end(1))

    return sorted(fields, key=lambda item: int(item["start"]))

def _js_escape_text(value: str) -> str:
    return (
        value
        .replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )

def _apply_app_page_edits(source: str, edits: List[Dict[str, Any]]) -> str:
    clean_edits = []
    for edit in edits:
        try:
            start = int(edit.get("start"))
            end = int(edit.get("end"))
            value = str(edit.get("value", ""))
        except Exception:
            continue
        if start < 0 or end < start or end > len(source):
            continue
        clean_edits.append((start, end, value))

    for start, end, value in sorted(clean_edits, key=lambda item: item[0], reverse=True):
        clean_value = _js_escape_text(value)
        source = source[:start] + clean_value + source[end:]
    return source

def _verify_admin(request: Request):
    """Xác thực admin từ header Authorization."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Admin "):
        return None
    admin_id = auth.split("Admin ")[1]
    try:
        from db import get_db_connection
        conn = get_db_connection()
        if not conn: return None
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s AND role = 'admin'", (int(admin_id),))
            admin_user = cursor.fetchone()
        conn.close()
        return admin_user
    except:
        return None

@app.get("/admin")
def read_admin():
    admin_path = os.path.join(os.path.dirname(__file__), "admin.html")
    return FileResponse(admin_path, headers={"Cache-Control": "no-store"})

@app.get("/api/page-overrides")
def page_overrides():
    return JSONResponse(
        content={"success": True, "overrides": _load_page_overrides()},
        headers={"Cache-Control": "no-store"},
    )

@app.get("/api/app-assets/{asset_path:path}")
def app_asset_preview(asset_path: str):
    safe_path = asset_path.replace("\\", "/").lstrip("/")
    path = os.path.abspath(os.path.join(MOBILE_ASSETS_DIR, safe_path))
    if not path.startswith(MOBILE_ASSETS_DIR + os.sep) or not os.path.exists(path):
        return JSONResponse(status_code=404, content={"success": False, "message": "Asset not found"})
    ext = os.path.splitext(path)[1].lower()
    if ext not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        return JSONResponse(status_code=400, content={"success": False, "message": "Unsupported asset"})
    return FileResponse(path, headers={"Cache-Control": "no-store"})

@app.post("/api/admin/login")
def admin_login_endpoint(data: AdminLogin):
    user = admin_login(data.username, pwd_context.verify, data.password)
    if not user:
        return JSONResponse(status_code=401, content={"success": False, "message": "Sai tài khoản hoặc mật khẩu, hoặc không có quyền admin."})
    return {"success": True, "token": str(user['id']), "username": user['username']}

@app.get("/api/admin/dashboard")
def admin_dashboard(request: Request):
    admin = _verify_admin(request)
    if not admin:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    stats = get_dashboard_stats()
    return {"success": True, "stats": stats}

@app.get("/api/admin/users")
def admin_users(request: Request):
    admin = _verify_admin(request)
    if not admin:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    users = get_all_users_admin()
    return {"success": True, "users": users}

@app.post("/api/admin/users/lock/{user_id}")
def admin_lock_user(user_id: int, request: Request):
    admin = _verify_admin(request)
    if not admin:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    body_bytes = None
    try:
        import asyncio
        loop = asyncio.get_event_loop()
    except:
        pass
    success = toggle_user_lock(user_id, True)
    return {"success": success, "message": "Đã khóa tài khoản" if success else "Lỗi"}

@app.post("/api/admin/users/unlock/{user_id}")
def admin_unlock_user(user_id: int, request: Request):
    admin = _verify_admin(request)
    if not admin:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    success = toggle_user_lock(user_id, False)
    return {"success": success, "message": "Đã mở khóa tài khoản" if success else "Lỗi"}

@app.post("/api/admin/users/credits")
def admin_credits_endpoint(data: AdminCreditUpdate, request: Request):
    admin = _verify_admin(request)
    if not admin:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    success = admin_update_credits(data.user_id, data.amount, data.action)
    return {"success": success, "message": f"Đã cập nhật credits" if success else "Lỗi"}

@app.post("/api/admin/users/reset-password")
def admin_reset_pwd(data: AdminResetPassword, request: Request):
    admin = _verify_admin(request)
    if not admin:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    new_hash = pwd_context.hash(data.new_password)
    success = admin_reset_password(data.user_id, new_hash)
    return {"success": success, "message": "Đã reset mật khẩu" if success else "Lỗi"}

@app.delete("/api/admin/users/{user_id}")
def admin_delete_user_endpoint(user_id: int, request: Request):
    admin = _verify_admin(request)
    if not admin:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    if int(admin.get("id")) == user_id:
        return JSONResponse(status_code=400, content={"success": False, "message": "Khong the xoa tai khoan admin dang dang nhap"})
    success, message = admin_delete_user(user_id)
    return {"success": success, "message": message}

@app.get("/api/admin/payments")
def admin_payments(request: Request, status: Optional[str] = None):
    admin = _verify_admin(request)
    if not admin:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    payments = get_all_payments_admin(status)
    return {"success": True, "payments": payments}

@app.post("/api/admin/payments/approve/{payment_id}")
def admin_approve_payment_endpoint(payment_id: int, request: Request):
    admin = _verify_admin(request)
    if not admin:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    success, message = admin_approve_payment(payment_id)
    return {"success": success, "message": message}

@app.get("/api/admin/scans")
def admin_scans(request: Request):
    admin = _verify_admin(request)
    if not admin:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    scans = get_all_scan_history_admin()
    return {"success": True, "scans": scans}

@app.get("/api/admin/marks")
def admin_marks(request: Request):
    admin = _verify_admin(request)
    if not admin:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    marks = fetch_all_marks() or []
    return {"success": True, "marks": marks}

@app.post("/api/admin/marks")
def admin_add_mark_endpoint(data: AdminMarkData, request: Request):
    admin = _verify_admin(request)
    if not admin:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    new_id = admin_add_mark(data.dict())
    if new_id:
        # Reload database
        global REIGN_DATABASE
        REIGN_DATABASE = _load_database()
        return {"success": True, "id": new_id, "message": "Đã thêm hiệu đề mới"}
    return JSONResponse(status_code=500, content={"success": False, "message": "Lỗi thêm hiệu đề"})

@app.put("/api/admin/marks/{mark_id}")
def admin_update_mark_endpoint(mark_id: int, data: AdminMarkData, request: Request):
    admin = _verify_admin(request)
    if not admin:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    success = admin_update_mark(mark_id, data.dict())
    if success:
        global REIGN_DATABASE
        REIGN_DATABASE = _load_database()
        return {"success": True, "message": "Đã cập nhật hiệu đề"}
    return JSONResponse(status_code=500, content={"success": False, "message": "Lỗi cập nhật hiệu đề"})

@app.delete("/api/admin/marks/{mark_id}")
def admin_delete_mark_endpoint(mark_id: int, request: Request):
    admin = _verify_admin(request)
    if not admin:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    success = admin_delete_mark(mark_id)
    if success:
        global REIGN_DATABASE
        REIGN_DATABASE = _load_database()
        return {"success": True, "message": "Đã xóa hiệu đề"}
    return JSONResponse(status_code=500, content={"success": False, "message": "Lỗi xóa hiệu đề"})

@app.get("/api/admin/settings")
def admin_settings(request: Request):
    admin = _verify_admin(request)
    if not admin:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    settings = get_system_settings()
    return {"success": True, "settings": settings}

@app.get("/api/admin/database-info")
def admin_database_info(request: Request):
    admin = _verify_admin(request)
    if not admin:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    db_path = os.path.abspath(SQLITE_DB_PATH)
    app_dir = os.path.dirname(__file__)
    try:
        display_path = os.path.relpath(db_path, app_dir)
    except ValueError:
        display_path = db_path
    exists = os.path.exists(db_path)
    return {
        "success": True,
        "engine": "SQLite",
        "path": display_path.replace("\\", "/"),
        "absolute_path": db_path,
        "exists": exists,
        "size_bytes": os.path.getsize(db_path) if exists else 0,
        "xampp_required": False,
        "mysql_required": False,
    }

def update_env_file(key: str, value: str):
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return
    env_key = key.upper()
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        found = False
        new_lines = []
        for line in lines:
            if line.strip().startswith(f"{env_key}="):
                new_lines.append(f"{env_key}={value}\n")
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f"\n{env_key}={value}\n")
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
    except Exception as e:
        print(f"[Admin] Error updating .env file: {e}")

def apply_api_keys(key: str, value: str):
    import config
    import services.llm_service as llm_service
    if key == "gemini_api_key":
        config.GEMINI_API_KEY = value
        llm_service._gemini_client = None
        print(f"[Admin] Dynamic Gemini API Key updated.")
    elif key == "openai_api_key":
        config.OPENAI_API_KEY = value
        llm_service._openai_client = None
        print(f"[Admin] Dynamic OpenAI API Key updated.")

@app.post("/api/admin/settings")
def admin_update_settings(data: AdminSettingUpdate, request: Request):
    admin = _verify_admin(request)
    if not admin:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    success = update_system_setting(data.key, data.value)
    if success and data.key in ("gemini_api_key", "openai_api_key"):
        apply_api_keys(data.key, data.value)
        update_env_file(data.key, data.value)
    return {"success": success, "message": "Đã cập nhật cài đặt" if success else "Lỗi"}

@app.post("/api/admin/users/apply-free-credits")
def admin_apply_free_credits(data: AdminApplyFreeCredits, request: Request):
    admin = _verify_admin(request)
    if not admin:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    success, updated = apply_free_credits_to_unpaid_users(data.amount)
    return {
        "success": success,
        "updated": updated,
        "message": f"Applied free scan credits to {updated} unpaid users" if success else "Could not apply free credits",
    }


@app.post("/api/admin/page-overrides")
def admin_update_page_overrides(data: AdminPageOverridesUpdate, request: Request):
    admin = _verify_admin(request)
    if not admin:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    success = _save_page_overrides(data.overrides)
    return {"success": success, "message": "Da luu noi dung page" if success else "Loi luu noi dung page"}

@app.get("/api/admin/app-pages/{page_id}")
def admin_get_app_page(page_id: str, request: Request):
    admin = _verify_admin(request)
    if not admin:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    path = _get_app_page_path(page_id)
    if not path:
        return JSONResponse(status_code=404, content={"success": False, "message": "Khong tim thay man App"})
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    return {
        "success": True,
        "page_id": page_id,
        "file": APP_PAGE_FILES[page_id],
        "fields": _extract_app_page_fields(source),
    }

@app.post("/api/admin/app-pages/{page_id}")
def admin_save_app_page(page_id: str, data: AdminAppPageUpdate, request: Request):
    admin = _verify_admin(request)
    if not admin:
        return JSONResponse(status_code=401, content={"success": False, "message": "Unauthorized"})
    path = _get_app_page_path(page_id)
    if not path:
        return JSONResponse(status_code=404, content={"success": False, "message": "Khong tim thay man App"})
    with open(path, "r", encoding="utf-8") as f:
        source = f.read()
    next_source = _apply_app_page_edits(source, data.edits)
    with open(path, "w", encoding="utf-8") as f:
        f.write(next_source)
    return {
        "success": True,
        "message": "Da luu man App",
        "fields": _extract_app_page_fields(next_source),
    }


# ============================================================
# NCKH Multi-Pipeline API Endpoints
# ============================================================

def _slug_json_filename_part(value: str) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in str(value or "agent"))
    safe = "-".join(part for part in safe.split("-") if part)
    return safe or "agent"


def _attach_pipeline_json_manifest(result: Dict[str, Any]) -> None:
    """Expose one downloadable JSON payload per pipeline/agent in the API response."""
    details = result.get("pipeline_details") or result.get("pipeline_results") or []
    if not isinstance(details, list):
        return

    result["pipeline_results"] = details
    files = []
    for index, item in enumerate(details, start=1):
        if not isinstance(item, dict):
            continue
        pipeline_name = item.get("pipeline_name") or item.get("name") or f"pipeline_{index}"
        agent_name = item.get("agent_name") or item.get("agent") or pipeline_name
        files.append({
            "filename": f"marksense-{_slug_json_filename_part(agent_name)}.json",
            "pipeline_name": pipeline_name,
            "agent_name": agent_name,
            "content": {
                "pipeline_name": pipeline_name,
                "agent_name": agent_name,
                "result": item,
            },
        })

    result["pipeline_json_files"] = files
    result["agent_json_files"] = files


def _save_crop_artifact(
    image_bytes: bytes,
    crop: Dict[str, Any],
    run_id: str,
    pipeline_name: str,
) -> Optional[Dict[str, Any]]:
    try:
        artifact_dir = os.path.join("uploads", "nckh_artifacts")
        os.makedirs(artifact_dir, exist_ok=True)
        filename = f"{run_id}_{_slug_json_filename_part(pipeline_name)}_vision_crop.jpg"
        path = os.path.join(artifact_dir, filename)

        if crop.get("image_base64"):
            import base64
            with open(path, "wb") as f:
                f.write(base64.b64decode(crop["image_base64"]))
        else:
            arr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is None:
                return None
            h_img, w_img = img.shape[:2]
            x = int(max(0, min(w_img - 1, int(crop.get("x", 0)))))
            y = int(max(0, min(h_img - 1, int(crop.get("y", 0)))))
            w = int(max(1, int(crop.get("w", w_img))))
            h = int(max(1, int(crop.get("h", h_img))))
            x2 = min(w_img, x + w)
            y2 = min(h_img, y + h)
            cropped = img[y:y2, x:x2]
            if cropped.size == 0:
                return None
            scale = float(crop.get("scale") or 1.0)
            if scale > 1.05:
                cropped = cv2.resize(cropped, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            if not cv2.imwrite(path, cropped):
                return None

        meta = {k: v for k, v in crop.items() if k != "image_base64"}
        return {
            "label": "Vision crop used for analysis",
            "kind": "vision_crop",
            "url": f"/uploads/nckh_artifacts/{filename}",
            "meta": meta,
        }
    except Exception as exc:
        print("Failed to save vision crop artifact:", exc)
        return None


def _copy_ocr_debug_artifacts(run_id: str, image_bytes: bytes) -> List[Dict[str, Any]]:
    """Build OCR visual artifacts from the current request image only."""
    artifact_dir = os.path.join("uploads", "nckh_artifacts")
    os.makedirs(artifact_dir, exist_ok=True)
    artifacts: List[Dict[str, Any]] = []

    arr = np.frombuffer(image_bytes, np.uint8)
    original = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if original is None:
        return artifacts

    def save_artifact(label: str, kind: str, base_name: str, img) -> Optional[str]:
        if img is None or getattr(img, "size", 0) == 0:
            return None
        dest_name = f"{run_id}_{base_name}.jpg"
        dest = os.path.join(artifact_dir, dest_name)
        try:
            if cv2.imwrite(dest, img):
                artifacts.append({
                    "label": label,
                    "kind": kind,
                    "url": f"/uploads/nckh_artifacts/{dest_name}",
                })
                return dest
        except Exception as exc:
            print("Failed to save OCR artifact:", base_name, exc)
        return None

    def add_processed_variants(img, base_name: str) -> None:
        try:
            if img is None or getattr(img, "size", 0) == 0:
                return
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            gray_boost = clahe.apply(gray)
            blur = cv2.medianBlur(gray_boost, 3)
            adapt = cv2.adaptiveThreshold(
                blur,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                31,
                8,
            )
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 17))
            blackhat = cv2.morphologyEx(gray_boost, cv2.MORPH_BLACKHAT, kernel)
            _, blackhat_bw = cv2.threshold(blackhat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            variants = {
                "gray": gray_boost,
                "adaptive_bw": adapt,
                "blackhat_bw": blackhat_bw,
            }
            for variant_name, variant_img in variants.items():
                dest_name = f"{run_id}_{base_name}_{variant_name}.jpg"
                dest = os.path.join(artifact_dir, dest_name)
                if cv2.imwrite(dest, variant_img):
                    artifacts.append({
                        "label": f"OCR {base_name} {variant_name}",
                        "kind": "ocr_processed_bw",
                        "url": f"/uploads/nckh_artifacts/{dest_name}",
                    })
        except Exception as exc:
            print("Failed to create OCR processed variants:", base_name, exc)

    save_artifact("OCR original image", "ocr_debug", "00_current_original", original)

    try:
        from ocr_engine import (
            detect_yellow_mark_roi,
            detect_inner_mark_circle_roi,
            detect_center_square_roi,
            detect_ink_text_roi,
            extract_center_box_roi,
        )

        roi_builders = [
            ("OCR ROI candidate", "01_current_roi_candidate", detect_yellow_mark_roi),
            ("OCR circle ROI", "01_current_circle_roi", detect_inner_mark_circle_roi),
            ("OCR square ROI", "01_current_square_roi", detect_center_square_roi),
            ("OCR center box ROI", "01_current_center_box_roi", extract_center_box_roi),
            ("OCR ink/mark ROI", "01_current_ink_roi", detect_ink_text_roi),
        ]
        seen_shapes = set()
        for label, base_name, builder in roi_builders:
            roi = builder(original)
            if roi is None or getattr(roi, "size", 0) == 0:
                continue
            shape_key = (roi.shape[0], roi.shape[1], int(np.mean(roi)))
            if shape_key in seen_shapes:
                continue
            seen_shapes.add(shape_key)
            save_artifact(label, "ocr_debug", base_name, roi)
            add_processed_variants(roi, base_name)
    except Exception as exc:
        print("Failed to build current OCR ROI artifacts:", exc)

    return artifacts


def _attach_pipeline_image_artifacts(
    result: Dict[str, Any],
    image_bytes: bytes,
) -> None:
    """Attach per-pipeline crop/ROI images that the test UI can render."""
    import uuid

    details = result.get("pipeline_details") or result.get("pipeline_results") or []
    if not isinstance(details, list):
        return

    run_id = uuid.uuid4().hex[:10]
    ocr_artifacts = _copy_ocr_debug_artifacts(run_id, image_bytes)
    image_search_artifact = None

    artifact_dir = os.path.join("uploads", "nckh_artifacts")
    os.makedirs(artifact_dir, exist_ok=True)
    search_filename = f"{run_id}_img_search_input.jpg"
    search_path = os.path.join(artifact_dir, search_filename)
    try:
        with open(search_path, "wb") as f:
            f.write(image_bytes)
        image_search_artifact = {
            "label": "Image search input",
            "kind": "image_search_input",
            "url": f"/uploads/nckh_artifacts/{search_filename}",
        }
    except Exception as exc:
        print("Failed to save image search artifact:", exc)

    for item in details:
        if not isinstance(item, dict):
            continue
        pipeline_name = item.get("pipeline_name") or item.get("name") or "pipeline"
        images: List[Dict[str, Any]] = []
        extra = item.get("extra_data") if isinstance(item.get("extra_data"), dict) else {}

        if pipeline_name in {"ocr_llm", "ocr_search", "ml_match", "text_vote"}:
            images.extend(ocr_artifacts)

        if pipeline_name.startswith("vision"):
            crop = extra.get("crop")
            if isinstance(crop, dict):
                crop_artifact = _save_crop_artifact(image_bytes, crop, run_id, pipeline_name)
                if crop_artifact:
                    images.append(crop_artifact)

        if pipeline_name == "img_search" and image_search_artifact:
            images.append(image_search_artifact)

        item["analysis_images"] = images
        if extra is not item:
            extra["analysis_images"] = images
            item["extra_data"] = extra

    result["pipeline_details"] = details
    result["pipeline_results"] = details

@app.post("/api/nckh/analyze")
async def nckh_analyze_endpoint(
    request: Request,
    file: UploadFile = File(...),
    mode: Optional[str] = Form("quick"),
    pipelines: Optional[str] = Form(None),
):
    """
    API phân tích hiệu đề bằng Multi-Pipeline (NCKH).
    
    Args:
        file: Ảnh hiệu đề
        mode: "quick" (P1+P4, ~10s) hoặc "deep" (tất cả 4 pipeline, ~30-60s)
        pipelines: Danh sách pipeline cụ thể, phân cách bởi dấu phẩy
                   Ví dụ: "ocr_llm,ml_match" hoặc "ocr_llm,ocr_search,img_search,ml_match"
    """
    def _extract_display_text(payload):
        if not isinstance(payload, dict):
            return ""
        direct_keys = ("chu_han", "hieu_de", "text_ocr", "final_text", "hien_thi_chinh", "hieu_de_vi")
        for key in direct_keys:
            value = payload.get(key)
            if value:
                return str(value)
        for nested_key in ("report", "top_match", "best_match", "final_result", "best_candidate"):
            nested = payload.get(nested_key)
            if isinstance(nested, dict):
                text = _extract_display_text(nested)
                if text:
                    return text
        return ""

    def _save_nckh_history(image_bytes, result):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        try:
            import uuid
            user_id = int(auth_header.split("Bearer ")[1])
            if not os.path.exists("uploads"):
                os.makedirs("uploads")
            unique_suffix = uuid.uuid4().hex[:8]
            hist_img_path = f"uploads/{user_id}_{unique_suffix}_scan.jpg"
            with open(hist_img_path, "wb") as f:
                f.write(image_bytes)
            details = result.copy() if isinstance(result, dict) else {"result": result}
            display_text = _extract_display_text(details)
            details.setdefault("matched", bool(display_text))
            details.setdefault("top_mark", display_text)
            add_scan_history(user_id, hist_img_path, display_text, details)
            return deduct_credit(user_id)
        except Exception as e:
            print("Failed to save NCKH history:", e)
            return None

    try:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                uid = int(auth_header.split("Bearer ")[1])
                remaining = get_user_credits(uid)
                if remaining <= 0:
                    return JSONResponse(
                        status_code=403,
                        content={"success": False, "no_credits": True, "message": "Ban da het luot phan tich.", "credits": 0}
                    )
            except Exception:
                pass

        # Validate file
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            return JSONResponse(
                status_code=400,
                content={"error": f"File không hợp lệ. Chấp nhận: {ALLOWED_EXTENSIONS}"}
            )
        
        image_bytes = await file.read()
        if not image_bytes:
            return JSONResponse(status_code=400, content={"error": "File rỗng"})
        
        # Crop nếu có tham số
        # (tương thích với frontend hiện tại)
        
        # Import orchestrator
        from pipelines.orchestrator import analyze_image, analyze_quick, analyze_deep
        
        # Xác định pipeline cần chạy
        if pipelines:
            pipeline_list = [p.strip() for p in pipelines.split(",") if p.strip()]
            result = await analyze_image(
                image_bytes,
                database=REIGN_DATABASE,
                pipelines=pipeline_list,
                timeout=240,
            )
        elif mode == "deep":
            result = await analyze_deep(image_bytes, database=REIGN_DATABASE)
        else:
            result = await analyze_quick(image_bytes, database=REIGN_DATABASE)

        new_credits = _save_nckh_history(image_bytes, result)
        if isinstance(result, dict):
            result.setdefault("success", True)
            _attach_pipeline_image_artifacts(result, image_bytes)
            _attach_pipeline_json_manifest(result)
            if new_credits is not None:
                result["credits"] = new_credits

        return JSONResponse(content=result)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": f"Lỗi phân tích: {str(e)}"}
        )


@app.get("/api/nckh/status")
async def nckh_status():
    """Kiểm tra trạng thái hệ thống Multi-Pipeline."""
    from config import GEMINI_API_KEY, OPENAI_API_KEY, GOOGLE_CSE_API_KEY, PRIMARY_LLM, OLLAMA_VISION_MODEL, OPENCODE_VISION_MODEL
    
    status = {
        "system": "NCKH Multi-Pipeline",
        "version": "1.0.0",
        "primary_llm": PRIMARY_LLM,
        "gemini_configured": bool(GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here"),
        "openai_configured": bool(OPENAI_API_KEY and OPENAI_API_KEY != "your_openai_api_key_here"),
        "google_cse_configured": bool(GOOGLE_CSE_API_KEY and GOOGLE_CSE_API_KEY != "your_google_cse_api_key_here"),
        "opencode_vision_model": OPENCODE_VISION_MODEL,
        "ollama_vision_model": OLLAMA_VISION_MODEL,
        "pipelines": ["ocr_llm", "ocr_search", "vision_gemini", "vision_opencode", "text_vote", "img_search", "ml_match"],
        "database_size": len(REIGN_DATABASE),
    }
    
    # Kiểm tra Selenium
    try:
        from selenium import webdriver
        status["selenium_available"] = True
    except ImportError:
        status["selenium_available"] = False
    
    return status

