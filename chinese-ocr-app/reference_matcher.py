import cv2
import numpy as np
import os
import json
import re
import unicodedata
from typing import Dict, Any, Optional, Sequence, Tuple

REFERENCE_DIR = os.path.join(os.path.dirname(__file__), "data", "reference_library")
os.makedirs(REFERENCE_DIR, exist_ok=True)

# Cache lưu trữ đặc điểm (descriptors) của các ảnh mẫu để so sánh nhanh
# Format: { "filename": { "keypoints": [...], "descriptors": [...], "json_data": {...} } }
_reference_cache = {}

# Khởi tạo thuật toán ORB (Oriented FAST and Rotated BRIEF)
orb = cv2.ORB_create(nfeatures=2000)

# Khởi tạo Brute-Force Matcher với khoảng cách NORM_HAMMING chuyên cho ORB
bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

# Ngưỡng (Threshold) cấu hình: Mức độ tương đồng tối thiểu để xác nhận là 1 ảnh.
# Hạ nhẹ để nhận diện được ảnh chụp nghiêng/thiếu sáng.
MIN_GOOD_MATCHES = 18
MIN_ORB_UNIQUE_GAP = 30
MIN_ORB_UNIQUE_RATIO = 1.25
ORB_TEXT_ROI_RATIO = 0.62


def _center_roi(image: np.ndarray, ratio: float = ORB_TEXT_ROI_RATIO) -> np.ndarray:
    """Use the center mark area so ORB does not match mostly on bowl rims/background."""
    if image is None or image.size == 0:
        return image
    h, w = image.shape[:2]
    if h < 80 or w < 80:
        return image
    ratio = min(max(ratio, 0.35), 1.0)
    y1 = int((1.0 - ratio) * 0.5 * h)
    y2 = int((1.0 + ratio) * 0.5 * h)
    x1 = int((1.0 - ratio) * 0.5 * w)
    x2 = int((1.0 + ratio) * 0.5 * w)
    roi = image[y1:y2, x1:x2]
    return roi if roi.size else image

def _extract_orb(image: np.ndarray):
    """Trích xuất keypoints và descriptors từ ảnh bằng hệ quy chiếu xám"""
    image = _center_roi(image)
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
        
    # Cân bằng biểu đồ thu nhỏ độ chênh lệch ánh sáng (CLAHE) giúp bắt nét tốt hơn trên bát gốm trơn bóng
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    
    keypoints, descriptors = orb.detectAndCompute(gray, None)
    return keypoints, descriptors


def load_references():
    """Đọc thư mục reference_library và nạp toàn bộ ảnh mẫu vào RAM dưới dạng Descriptors"""
    global _reference_cache
    _reference_cache = {}

    # Build lookup map for json files by suffix (last token after underscore)
    json_by_suffix = {}
    for filename in os.listdir(REFERENCE_DIR):
        if filename.lower().endswith(".json"):
            base = os.path.splitext(filename)[0]
            suffix = base.split("_")[-1]
            json_by_suffix[suffix] = filename
    
    for filename in os.listdir(REFERENCE_DIR):
        if filename.lower().endswith(".jpg") or filename.lower().endswith(".png"):
            img_path = os.path.join(REFERENCE_DIR, filename)
            json_path = os.path.splitext(img_path)[0] + ".json"
            if not os.path.exists(json_path):
                base = os.path.splitext(filename)[0]
                suffix = base.split("_")[-1]
                json_name = json_by_suffix.get(suffix)
                if json_name:
                    json_path = os.path.join(REFERENCE_DIR, json_name)
            
            if not os.path.exists(json_path):
                continue
                
            try:
                # Đọc cấu trúc JSON
                with open(json_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    
                # Đọc ảnh và trích xuất đặc điểm
                nparr = np.fromfile(img_path, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is None:
                    continue
                    
                _, descriptors = _extract_orb(img)
                if descriptors is None:
                    continue
                    
                _reference_cache[filename] = {
                    "descriptors": descriptors,
                    "json_data": json_data
                }
            except Exception as e:
                print(f"Error loading reference {filename}: {e}")
    print(f"[Reference Library] Loaded {len(_reference_cache)} reference samples into memory.")

# Khởi chạy nạp dữ liệu ở lần chạy đầu tiên
load_references()


def match_image(input_img_bytes: bytes) -> Optional[Dict[str, Any]]:
    """
    So sánh ảnh người dùng truyền lên với thư viện mẫu.
    Nếu tìm thấy ảnh mẫu siêu khớp (> MIN_GOOD_MATCHES), trả về ngay lập tức JSON phân tích
    của ảnh mẫu đó. Nếu không, trả về None (thuật toán sẽ đẩy tiếp vào PaddleOCR).
    """
    if not _reference_cache:
        return None
        
    nparr = np.frombuffer(input_img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return None
        
    _, input_descriptors = _extract_orb(img)
    if input_descriptors is None:
        return None
        
    best_match_count = 0
    second_best_count = 0
    best_json_data = None
    best_filename = ""
    second_filename = ""
    
    for filename, ref_data in _reference_cache.items():
        ref_descriptors = ref_data["descriptors"]
        
        # So khớp
        try:
            matches = bf.match(input_descriptors, ref_descriptors)
            # Sắp xếp matches theo khoảng cách (càng nhỏ càng giống)
            matches = sorted(matches, key=lambda x: x.distance)
            
            # Lọc 'good' matches: Khoảng cách Hamming nhỏ hơn ngưỡng
            good_matches = [m for m in matches if m.distance < 55]
            count = len(good_matches)
            
            if count > best_match_count:
                second_best_count = best_match_count
                second_filename = best_filename
                best_match_count = count
                best_json_data = ref_data["json_data"]
                best_filename = filename
            elif count > second_best_count:
                second_best_count = count
                second_filename = filename
                
        except Exception as e:
            continue
            
    print(f"ORB Match Result: best={best_match_count}, second_best={second_best_count} (Threshold {MIN_GOOD_MATCHES})")
            
    if best_match_count >= MIN_GOOD_MATCHES and best_json_data:
        gap = best_match_count - second_best_count
        ratio = best_match_count / max(second_best_count, 1)
        if (
            second_best_count >= MIN_GOOD_MATCHES
            and (gap < MIN_ORB_UNIQUE_GAP or ratio < MIN_ORB_UNIQUE_RATIO)
        ):
            print(
                "[WARN] Ambiguous ORB match ignored: "
                f"best={best_filename} ({best_match_count}), "
                f"second={second_filename} ({second_best_count}), "
                f"gap={gap}, ratio={ratio:.2f}"
            )
            return None

        print(f"[OK] Reference match found!")
        # Chỉnh match_type để front-end biết là nhận diện từ Memory
        best_json_data["match_type"] = "exact_orb_memory"
        best_json_data["_orb_best"] = best_match_count
        best_json_data["_orb_second"] = second_best_count
        return best_json_data
        
    return None


def match_image_by_prefix(
    input_img_bytes: bytes,
    prefixes: Sequence[str],
) -> Tuple[Optional[Dict[str, Any]], int]:
    """Find the best ORB match among references whose chu_han starts with a prefix."""
    if not _reference_cache or not prefixes:
        return None, 0

    nparr = np.frombuffer(input_img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return None, 0

    _, input_descriptors = _extract_orb(img)
    if input_descriptors is None:
        return None, 0

    best_match_count = 0
    best_json_data = None

    for ref_data in _reference_cache.values():
        json_data = ref_data.get("json_data", {})
        chu_han = json_data.get("chu_han") or ""
        if not any(chu_han.startswith(prefix) for prefix in prefixes):
            continue

        ref_descriptors = ref_data.get("descriptors")
        if ref_descriptors is None:
            continue

        try:
            matches = bf.match(input_descriptors, ref_descriptors)
            matches = sorted(matches, key=lambda x: x.distance)
            good_matches = [m for m in matches if m.distance < 55]
            if len(good_matches) > best_match_count:
                best_match_count = len(good_matches)
                best_json_data = json_data
        except Exception:
            continue

    if best_json_data:
        if best_match_count >= MIN_GOOD_MATCHES:
            best_json_data["match_type"] = "exact_orb_memory"
        else:
            best_json_data["match_type"] = "orb_memory_soft"
    return best_json_data, best_match_count

def save_reference(input_img_bytes: bytes, json_data: dict) -> bool:
    """Lưu ảnh và kết quả OCR thành 1 cặp mẫu trong thư viện tham chiếu"""
    import uuid
    try:
        nparr = np.frombuffer(input_img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return False
            
        unique_id = str(uuid.uuid4())[:8]
        # Gom tên triều đại hoặc vua để dễ nhìn (ví dụ hong_vu_1234abcd)
        prefix = "unknown"
        if "phien_am" in json_data and json_data["phien_am"]:
            prefix = json_data["phien_am"].lower().replace(" ", "_").replace("-", "")
        elif "chu_han" in json_data and json_data["chu_han"]:
            prefix = json_data["chu_han"]

        # Make filename ASCII-safe to avoid encoding issues on Windows
        prefix_norm = unicodedata.normalize("NFKD", prefix)
        prefix_ascii = prefix_norm.encode("ascii", "ignore").decode("ascii")
        prefix_ascii = re.sub(r"[^a-zA-Z0-9_]+", "", prefix_ascii) or "mark"
            
        base_name = f"{prefix_ascii}_{unique_id}"
        img_path = os.path.join(REFERENCE_DIR, f"{base_name}.jpg")
        json_path = os.path.join(REFERENCE_DIR, f"{base_name}.json")
        
        cv2.imwrite(img_path, img)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
            
        # Nạp lại RAM
        load_references()
        return True
    except Exception as e:
        print(f"Error saving reference: {e}")
        return False
