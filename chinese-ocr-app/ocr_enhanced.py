#!/usr/bin/env python3
"""
Enhanced OCR with multiple detection strategies as fallbacks
Khi strict confidence không tìm được, thử chiến lược khác
"""

import cv2
import numpy as np
from paddleocr import PaddleOCR
import re

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

def ocr_aggressive_fallback(image: np.ndarray) -> tuple:
    """
    Khi strict confidence không tìm được gì, thử chiến lược aggressive
    - Giảm threshold
    - Thử nhiều preprocessing
    - Lấy mọi kết quả
    """
    print("\n[FALLBACK] Trying aggressive OCR strategies...")
    
    results = []
    
    # Strategy 1: Reduce strict threshold, accept ANY detection
    print("  Strategy 1: No confidence filter (accept all)")
    h, w = image.shape[:2]
    if max(h, w) < 800:
        img = cv2.resize(image, None, fx=2, fy=2, interpolation=cv2.INTER_LANCZOS4)
    else:
        img = image
    
    try:
        ocr_result = ocr.ocr(img, cls=True)
        if ocr_result and ocr_result[0]:
            for line in ocr_result[0]:
                text = line[1][0]
                conf = line[1][1]
                chinese = re.sub(r"[^\u4e00-\u9fff]", "", text)
                if chinese:
                    results.append({
                        'text': chinese,
                        'confidence': conf,
                        'source': 'no_filter'
                    })
                    print(f"    Found: '{chinese}' (conf: {conf:.2f})")
    except Exception as e:
        print(f"    Error: {e}")
    
    # Strategy 2: Enhance contrast aggressively
    print("  Strategy 2: High contrast enhancement")
    enhanced = cv2.convertScaleAbs(cv2.Laplacian(image, cv2.CV_64F))
    clahe = cv2.createCLAHE(clipLimit=5.0, tileGridSize=(4, 4))
    enhanced = clahe.apply(cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY))
    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
    
    try:
        ocr_result = ocr.ocr(enhanced, cls=True)
        if ocr_result and ocr_result[0]:
            for line in ocr_result[0]:
                text = line[1][0]
                conf = line[1][1]
                chinese = re.sub(r"[^\u4e00-\u9fff]", "", text)
                if chinese and conf >= 0.40:  # Very permissive
                    results.append({
                        'text': chinese,
                        'confidence': conf,
                        'source': 'high_contrast'
                    })
                    print(f"    Found: '{chinese}' (conf: {conf:.2f})")
    except Exception as e:
        print(f"    Error: {e}")
    
    # Strategy 3: Bilateral denoise + CLAHE
    print("  Strategy 3: Denoise + CLAHE")
    denoised = cv2.bilateralFilter(image, 9, 75, 75)
    lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    enhanced = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
    
    try:
        ocr_result = ocr.ocr(enhanced, cls=True)
        if ocr_result and ocr_result[0]:
            for line in ocr_result[0]:
                text = line[1][0]
                conf = line[1][1]
                chinese = re.sub(r"[^\u4e00-\u9fff]", "", text)
                if chinese and conf >= 0.45:
                    results.append({
                        'text': chinese,
                        'confidence': conf,
                        'source': 'denoise_clahe'
                    })
                    print(f"    Found: '{chinese}' (conf: {conf:.2f})")
    except Exception as e:
        print(f"    Error: {e}")
    
    # Return best result or all candidates
    if not results:
        print("  ⚠️  No results from any strategy!")
        return "", 0.0, []
    
    # Sort by confidence
    results.sort(key=lambda x: x['confidence'], reverse=True)
    best = results[0]
    
    print(f"\n  ✅ Best result: '{best['text']}' (conf: {best['confidence']:.2f}, source: {best['source']})")
    
    return best['text'], best['confidence'], results


def ocr_spatial_analysis(image: np.ndarray, expected_size_range=(20, 200)) -> list:
    """
    Phân tích vị trí và kích thước của các bounding box
    Có thể lọc được noise dựa trên vị trí, kích thước
    """
    print("\n[SPATIAL] Analyzing text locations and sizes...")
    
    h, w = image.shape[:2]
    center_h, center_w = h // 2, w // 2
    
    try:
        ocr_result = ocr.ocr(image, cls=True)
        if not ocr_result or not ocr_result[0]:
            return []
        
        candidates = []
        for line in ocr_result[0]:
            text = line[1][0]
            conf = line[1][1]
            points = line[0]
            
            # Calculate bounding box size
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            box_w = max(xs) - min(xs)
            box_h = max(ys) - min(ys)
            box_size = max(box_w, box_h)
            
            # Calculate distance from center
            box_cx = (max(xs) + min(xs)) / 2
            box_cy = (max(ys) + min(ys)) / 2
            dist_from_center = ((box_cx - center_w)**2 + (box_cy - center_h)**2) ** 0.5
            
            # Marks are usually in center, medium-sized
            is_centered = dist_from_center < max(h, w) * 0.3
            is_good_size = expected_size_range[0] <= box_size <= expected_size_range[1]
            
            chinese = re.sub(r"[^\u4e00-\u9fff]", "", text)
            
            if chinese:
                candidates.append({
                    'text': chinese,
                    'confidence': conf,
                    'size': box_size,
                    'distance_from_center': dist_from_center,
                    'is_centered': is_centered,
                    'is_good_size': is_good_size,
                    'score': conf * (1.5 if is_centered else 1.0) * (1.2 if is_good_size else 0.8)
                })
                
                print(f"  Text: '{chinese}'")
                print(f"    Conf: {conf:.2f}, Size: {box_size:.0f}, Center dist: {dist_from_center:.0f}")
                print(f"    Centered: {is_centered}, Good size: {is_good_size}, Score: {candidates[-1]['score']:.2f}")
        
        # Sort by adjusted score
        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates
    
    except Exception as e:
        print(f"  Error: {e}")
        return []


if __name__ == "__main__":
    print("=" * 80)
    print("📋 Enhanced OCR Fallback Strategies")
    print("=" * 80)
    print("""
This module provides additional OCR fallback strategies:

1. Aggressive confidence reduction (accept even low-confidence results)
2. Aggressive contrast enhancement (Laplacian + CLAHE)
3. Denoising + CLAHE enhancement
4. Spatial analysis (filter based on location and size)

When to use:
- If strict confidence filtering finds nothing
- If OCR is completely failing
- If quality image shows no results

Functions:
- ocr_aggressive_fallback(image): Try multiple strategies, return best
- ocr_spatial_analysis(image): Analyze text location/size, filter noise

Example:
    text, conf, candidates = ocr_aggressive_fallback(image)
    spatial_results = ocr_spatial_analysis(image)
""")
    
    print("\n✅ Module loaded successfully")
    print("   Ready to use with real images")
