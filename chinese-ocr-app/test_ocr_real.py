#!/usr/bin/env python3
"""
Complete OCR Testing Framework
Test OCR with real images and see exactly what happens at each step
"""

import sys
import cv2
import numpy as np
import json
import os
from pathlib import Path

# Import our modules
from ocr_engine import (
    read_chinese_mark,
    _get_required_confidence,
    _attempt_ocr_correction,
    _validate_against_database,
)

def test_image_ocr(image_path: str):
    """
    Test an image through complete OCR pipeline
    """
    
    print("\n" + "=" * 90)
    print(f"🔍 OCR TESTING: {image_path}")
    print("=" * 90)
    
    # Check file exists
    if not os.path.exists(image_path):
        print(f"❌ File not found: {image_path}")
        return
    
    # Load image
    print(f"\n[STEP 1] Loading image...")
    try:
        image_data = open(image_path, 'rb').read()
        img = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)
        
        if img is None:
            print(f"❌ Failed to decode image")
            return
        
        h, w = img.shape[:2]
        print(f"✅ Image loaded: {w}x{h} pixels")
        
    except Exception as e:
        print(f"❌ Error loading image: {e}")
        return
    
    # Run OCR
    print(f"\n[STEP 2] Running OCR...")
    try:
        result = read_chinese_mark(image_data, deep_mode=True)
        
        print(f"✅ OCR completed")
        print(f"\n📊 OCR Results:")
        print(f"   Text: {result.get('text', 'NONE')}")
        print(f"   Confidence: {result.get('confidence', 0):.2f}")
        print(f"   Database Valid: {result.get('database_valid', False)}")
        print(f"   Warning: {result.get('warning', 'None')}")
        
        candidates = result.get('candidates', [])
        if candidates:
            print(f"\n   Candidates ({len(candidates)}):")
            for i, cand in enumerate(candidates[:5], 1):
                print(f"     {i}. {cand}")
        
        # Check suggestions
        suggestions = result.get('suggestions', [])
        if suggestions:
            print(f"\n   Suggestions:")
            for sugg in suggestions[:3]:
                print(f"     - {sugg}")
        
        # If there's a best_match
        best_match = result.get('best_match', {})
        if best_match:
            entry = best_match.get('entry', {})
            print(f"\n   Best Match:")
            print(f"     Chinese: {entry.get('chu_han', 'N/A')}")
            print(f"     Vietnamese: {entry.get('ten_viet', 'N/A')}")
            print(f"     Dynasty: {entry.get('trieu_dai', 'N/A')}")
            print(f"     Match type: {best_match.get('match_type', 'N/A')}")
            print(f"     Score: {best_match.get('score', 0):.2f}")
        
        print(f"\n📋 All Results:")
        all_results = result.get('all_results', [])
        for i, res in enumerate(all_results[:10], 1):
            print(f"   {i}. Text: {res.get('text')}, Conf: {res.get('confidence'):.2f}, Variant: {res.get('variant')}")
        
    except Exception as e:
        print(f"❌ OCR Error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Status report
    print(f"\n" + "-" * 90)
    print("📊 STATUS REPORT:")
    print("-" * 90)
    
    text = result.get('text', '')
    is_valid = result.get('database_valid', False)
    
    if not text:
        print("❌ NO TEXT DETECTED")
        print("   Possible causes:")
        print("   1. No ceramic mark in image")
        print("   2. Mark is too small/unclear")
        print("   3. Mark is outside expected region")
        print("   4. Image quality is poor (too dark, too bright, blurry)")
        
    elif not is_valid:
        print("⚠️  TEXT DETECTED BUT NOT CONFIRMED")
        print(f"   Detected: '{text}'")
        print(f"   Warning: {result.get('warning', 'Not in database')}")
        print("   Possible causes:")
        print("   1. OCR misidentified a character (e.g., 北→石, 侍→佚)")
        print("   2. Mark is a variant not in database")
        print("   3. Mark is rare/newly added")
        print("   Recommendations:")
        print("   - Check if similar marks exist in database")
        print("   - Manually verify the OCR result")
        print("   - Consider image quality improvement")
        
    else:
        print("✅ SUCCESS - MARK IDENTIFIED")
        print(f"   Detected: '{text}'")
        best_match = result.get('best_match', {})
        entry = best_match.get('entry', {})
        print(f"   Confirmed: {entry.get('ten_viet', 'N/A')} ({entry.get('chu_han', 'N/A')})")
    
    print("=" * 90)


def main():
    """
    Main test runner
    Usage:
        python test_ocr_real.py <image_path>
        python test_ocr_real.py uploads/
        python test_ocr_real.py uploads/test.jpg
    """
    
    print("\n🚀 OCR Testing Framework")
    print("=" * 90)
    
    if len(sys.argv) < 2:
        print("\n❓ Usage:")
        print("   python test_ocr_real.py <image_or_folder>")
        print("\nExamples:")
        print("   python test_ocr_real.py uploads/mark.jpg")
        print("   python test_ocr_real.py uploads/")
        print("\nSupported formats: JPG, PNG, BMP, WEBP, etc.")
        
        # Try to find sample images
        uploads_dir = "uploads"
        if os.path.exists(uploads_dir):
            files = list(Path(uploads_dir).glob("*.*"))
            if files:
                print(f"\n💡 Found {len(files)} files in {uploads_dir}:")
                for f in files[:5]:
                    print(f"   - {f}")
        
        return
    
    target = sys.argv[1]
    
    # Check if it's a directory
    if os.path.isdir(target):
        print(f"\n📁 Testing all images in: {target}")
        image_files = list(Path(target).glob("*.*"))
        image_files = [f for f in image_files if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.webp']]
        
        if not image_files:
            print(f"❌ No image files found in {target}")
            return
        
        print(f"Found {len(image_files)} images\n")
        
        for image_file in image_files:
            test_image_ocr(str(image_file))
            input("\n⏸️  Press Enter to test next image...")
    
    else:
        # Single file
        test_image_ocr(target)


if __name__ == "__main__":
    main()
