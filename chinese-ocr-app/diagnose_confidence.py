#!/usr/bin/env python3
"""
Quick test: What happens when OCR returns results?
Kiểm tra xem confidence filtering có quá nghiêm ngặt không
"""

import cv2
import numpy as np
from paddleocr import PaddleOCR
import re

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

# Create a simple image with Chinese text (for testing)
print("\n[TEST] Creating test image with Chinese characters...")

# Create blank white image
img = np.ones((400, 800, 3), dtype=np.uint8) * 255

# Add some marks/characters (just for OCR to try)
# This is a simplified test
cv2.putText(img, 'Mark', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

print("Running OCR on test image...")
result = ocr.ocr(img, cls=True)

if result and result[0]:
    print(f"\n✓ OCR returned {len(result[0])} detections:")
    for i, line in enumerate(result[0], 1):
        text = line[1][0]
        conf = line[1][1]
        print(f"  {i}. Text: '{text}' | Confidence: {conf:.4f}")
        
        # Check filtering
        from ocr_engine import _get_required_confidence
        
        chinese = re.sub(r"[^\u4e00-\u9fff]", "", text)
        if chinese:
            req_conf = _get_required_confidence(chinese)
            
            MIN_CONF = 0.55
            if conf < req_conf:
                print(f"     ❌ FILTERED OUT: conf {conf:.2f} < required {req_conf:.2f}")
            elif conf < MIN_CONF:
                print(f"     ⚠️  WOULD BE FILTERED: conf {conf:.2f} < MIN_CONF {MIN_CONF:.2f}")
            else:
                print(f"     ✅ ACCEPTED: conf {conf:.2f} >= required {req_conf:.2f}")
else:
    print("❌ No OCR detections!")

print("\n" + "=" * 80)
print("⚠️  KEY INSIGHT:")
print("=" * 80)
print("""
The issue might be that:

1. OCR is not finding ANY text (returning empty)
   → Image quality issue / no mark visible

2. OCR finds text but with low confidence (e.g., 0.50)
   → Our MIN_CONF=0.55 filter removes it!
   → This is TOO STRICT for real images

3. OCR finds text with good confidence but we correct it wrong
   → Auto-correction might break valid results

SOLUTION: We need to see what OCR ACTUALLY returns
Then adjust the filtering accordingly
""")

print("\n💡 Next steps:")
print("1. Provide a ceramic mark image")
print("2. Run: python test_ocr_real.py <image>")
print("3. We'll see exactly what OCR returns")
print("4. Then adjust confidence thresholds if needed")
