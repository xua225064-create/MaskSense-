"""
OCR Corrections Module — Fix hiệu đề đọc sai thường gặp

Chiến lược:
1. Visual similarity mapping: các ký tự hay nhầm lẫn
2. Valid character set: chỉ ký tự thực sự có trên gốm Việt
3. Context-based correction: từ position trong hiệu đề
"""

# ============================================================
# PHẦN 1: Visual Similarity Mapping
# Những cặp ký tự thường bị OCR nhầm lẫn
# ============================================================

OCR_VISUAL_CONFUSIONS = {
    # Format: wrong_char → [correct_alternatives]
    # Sorted by likelihood
    
    "石": ["北", "白", "左"],           # 石 (shí) vs 北 (běi)
    "杜": ["右", "社", "左"],           # 杜 can be OCR noise for 右 in Nội Phủ marks
    "社": ["右", "杜", "左"],           # 社/杜/右 are often confused in blue marks
    "赶": ["右"],                       # 赶 is a common PaddleOCR false read for 右
    "佚": ["侍", "待", "保"],           # 佚 (yì) vs 侍 (shì)
    "待": ["侍"],                       # 待 vs 侍
    "特": ["侍"],                       # 特 vs 侍
    "停": ["侍"],                       # 停 vs 侍 (cùng bộ 亻, PaddleOCR thường nhầm)
    "仃": ["侍"],                       # 仃 vs 侍
    "亭": ["侍"],                       # 亭 vs 侍
    "康": ["庚"],                       # 康 vs 庚 (chỉ dùng khi database xác nhận)
    "泰": ["康"],                       # PaddleOCR có thể đọc 康 thành 泰
    "装": ["製"],                       # 装/裝 vs 製
    "裝": ["製"],                       # 裝 vs 製
    "结": ["緒"],                       # 结/結 vs 緒
    "結": ["緒"],                       # 結 vs 緒
    "旨": ["指", "志", "支"],           # 旨 (zhǐ) vs 指 (zhǐ)
    "東": ["東", "東"],                 # 東 (dōng) - orientation
    "左": ["右", "左"],                 # 左 (zuǒ) vs 右 (yòu)
    "白": ["北", "白", "自"],           # 白 (bái) vs 北 (běi)
    "亜": ["亞", "亜"],                 # 亜 vs 亞 (Traditional)
    "卜": ["卜", "ト"],                 # 卜 (bǔ) - rare
    "八": ["八", "入"],                 # 八 (bā) vs 入 (rù)
    "乙": ["乙", "己"],                 # 乙 (yǐ) vs 己 (jǐ)
    "二": ["二", "三"],                 # 二 (èr) vs 三 (sān)
    "土": ["士", "土"],                 # 土 (tǔ) vs 士 (shì)
    "寸": ["寸", "寺"],                 # 寸 (cùn) vs 寺 (sì)
    "艇": ["製", "制"],                 # PaddleOCR often reads 製 as 艇 on blue underglaze
    "象": ["製", "制"],                 # 製 bottom strokes can look like 象/艇 when blurred
    "口": ["囗", "口"],                 # 口 (kǒu) - variant
    "囗": ["口", "囗"],                 # 囗 variant
    "山": ["山", "屮"],                 # 山 (shān)
    "川": ["川", "巛"],                 # 川 (chuān)
}

# ============================================================
# PHẦN 2: Valid Character Set cho Vietnamese Ceramic Marks
# Chỉ những ký tự THỰC SỰ xuất hiện trên gốm Việt/Trung cổ
# ============================================================

VALID_MARKS_CHARS = {
    # Nội Phủ (Internal Palace marks)
    "內", "内", "府", "侍", "中", "北", "東", "东", "西", "南", "旨", "指",
    "右", "左", "從", "从", "兌", "兑",
    
    # Common dynasties & emperors
    "大", "明", "清", "康", "熙", "乾", "隆", "雍", "正", "嘉", "靖",
    "萬", "曆", "嘉", "慶", "道", "光", "緒", "绪", "宣", "統", "统",
    "咸", "豐", "同", "治", "光",
    
    # Year markers
    "年", "製", "制", "造", "庚", "仿", "式", "款", "期", "代",
    
    # Common characters in marks
    "永", "樂", "祥", "瑞", "符", "命", "生", "活", "福", "壽", "宝",
    "寶", "皇", "帝", "聖", "天", "地", "人", "時", "月", "日", "時",
    
    # Numbers
    "一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
    
    # Vietnamese dynasty marks
    "嘉", "隆", "景", "泰", "保", "保", "定", "順", "永", "保",
}

# ============================================================
# PHẦN 3: Multi-Character Pattern Validation
# Validates entire mark string patterns
# ============================================================

VALID_MARK_PATTERNS = {
    # Format: (length, pattern_description, example)
    4: ["Nội Phủ 4-char", "內府侍北"],
    6: ["Dynasty + Title (6-char)", "大明萬曆"],
    8: ["Extended marks", "乾隆年製款識"],
}

# ============================================================
# PHẦN 4: Correction Functions
# ============================================================

def is_valid_char(char: str) -> bool:
    """Kiểm tra ký tự có phải valid Vietnamese ceramic mark char không."""
    return char in VALID_MARKS_CHARS


def suggest_corrections(wrong_char: str) -> list:
    """
    Gợi ý các ký tự thay thế cho ký tự sai.
    
    Args:
        wrong_char: Ký tự bị OCR đọc sai
        
    Returns:
        Danh sách ký tự thay thế (sắp xếp theo likelihood)
    """
    if wrong_char not in OCR_VISUAL_CONFUSIONS:
        return []
    
    alternatives = OCR_VISUAL_CONFUSIONS[wrong_char]
    # Filter to only valid chars
    return [alt for alt in alternatives if is_valid_char(alt)]


def correct_ocr_text(ocr_text: str, database: list = None) -> dict:
    """
    Sửa OCR text bằng visual similarity + database validation.
    
    Strategy:
    1. Scan từng ký tự
    2. Nếu ký tự không valid → suggest corrections
    3. Kiểm tra database xem correction nào tồn tại
    4. Return top candidates
    
    Args:
        ocr_text: Text từ OCR
        database: Database marks để validate
        
    Returns:
        {
            "original": "內府侍石",
            "corrected": "內府侍北",
            "confidence": 0.95,
            "suggestions": ["內府侍北", "內府侍白"],
            "invalid_chars": ["石"],
            "matched_in_db": True
        }
    """
    result = {
        "original": ocr_text,
        "corrected": ocr_text,
        "confidence": 1.0,
        "suggestions": [ocr_text],  # Start with original
        "invalid_chars": [],
        "matched_in_db": False,
    }
    
    if not ocr_text:
        return result
    
    # 1. Scan invalid characters
    invalid_positions = []
    ambiguous_positions = []
    for i, char in enumerate(ocr_text):
        if not is_valid_char(char):
            invalid_positions.append((i, char))
            result["invalid_chars"].append(char)
        elif char in OCR_VISUAL_CONFUSIONS:
            ambiguous_positions.append((i, char))
    
    # Nếu không có ký tự invalid → accepted
    if not invalid_positions:
        if database:
            for entry in database:
                if entry.get("chu_han") == ocr_text:
                    result["matched_in_db"] = True
                    break
            if not result["matched_in_db"]:
                for pos, wrong_char in ambiguous_positions:
                    for correct_char in suggest_corrections(wrong_char):
                        candidate = ocr_text[:pos] + correct_char + ocr_text[pos+1:]
                        for entry in database:
                            if entry.get("chu_han") == candidate:
                                result["corrected"] = candidate
                                result["confidence"] = 0.82
                                result["matched_in_db"] = True
                                result["suggestions"] = [candidate]
                                return result
        return result
    
    # 2. Generate candidates by replacing invalid chars
    candidates = [ocr_text]  # Include original
    
    if len(invalid_positions) == 1:
        # Single invalid char → easy to fix
        pos, wrong_char = invalid_positions[0]
        corrections = suggest_corrections(wrong_char)
        
        for correct_char in corrections:
            candidate = ocr_text[:pos] + correct_char + ocr_text[pos+1:]
            candidates.append(candidate)
            result["confidence"] = 0.85  # Slightly lower confidence
    
    elif len(invalid_positions) <= 3:
        # Multiple invalid chars → try combinations
        # For now, just replace each independently
        for pos, wrong_char in invalid_positions:
            corrections = suggest_corrections(wrong_char)
            for correct_char in corrections[:2]:  # Top 2 suggestions
                candidate = ocr_text
                for p, wc in invalid_positions:
                    if p == pos:
                        candidate = candidate[:p] + correct_char + candidate[p+1:]
                candidates.append(candidate)
        result["confidence"] = 0.70  # Lower for multiple issues
    
    # 3. Validate candidates against database
    if database:
        for candidate in candidates:
            for entry in database:
                if entry.get("chu_han") == candidate:
                    result["corrected"] = candidate
                    result["matched_in_db"] = True
                    result["suggestions"] = [candidate]  # Top priority
                    return result
    
    # 4. If no database match, return best guess
    result["suggestions"] = candidates[:5]  # Top 5 candidates
    if len(candidates) > 1:
        result["corrected"] = candidates[1]  # First non-original candidate
    
    return result


def validate_and_correct_batch(ocr_texts: list, database: list = None) -> list:
    """
    Sửa batch OCR results.
    
    Args:
        ocr_texts: Danh sách OCR text
        database: Database marks
        
    Returns:
        Danh sách correction results
    """
    return [correct_ocr_text(text, database) for text in ocr_texts]


# ============================================================
# PHẦN 5: Statistics & Learning
# ============================================================

def get_correction_stats(corrections_list: list) -> dict:
    """Thống kê những lỗi OCR thường gặp."""
    stats = {
        "total": len(corrections_list),
        "corrected": sum(1 for c in corrections_list if c["corrected"] != c["original"]),
        "matched_in_db": sum(1 for c in corrections_list if c["matched_in_db"]),
        "invalid_chars_freq": {},
    }
    
    for corr in corrections_list:
        for char in corr["invalid_chars"]:
            stats["invalid_chars_freq"][char] = stats["invalid_chars_freq"].get(char, 0) + 1
    
    if stats["total"] > 0:
        stats["correction_rate"] = round(stats["corrected"] / stats["total"], 4)
        stats["db_match_rate"] = round(stats["matched_in_db"] / stats["total"], 4)
    
    return stats
