#!/usr/bin/env python3
"""Directly test OCR on uploaded images"""

from ocr_engine import read_chinese_mark
from pathlib import Path
import cv2

# Get images - prioritize larger ones
uploads_dir = Path("uploads")
all_images = [f for f in uploads_dir.glob("*.jpg") if f.stat().st_size > 50000]  # At least 50KB
all_images.sort(key=lambda x: x.stat().st_size, reverse=True)

if not all_images:
    print("No large images found, trying any images...")
    all_images = sorted([f for f in uploads_dir.glob("*.jpg")])[:5]

if not all_images:
    print("No images found")
    exit(1)

# Test first 2 images
for img_file in all_images[:2]:
    print(f"\n{'='*80}")
    print(f"Testing: {img_file.name} ({img_file.stat().st_size} bytes)")
    print('='*80)
    
    with open(img_file, 'rb') as f:
        img_bytes = f.read()
    
    # Also check image with OpenCV
    img = cv2.imread(str(img_file))
    if img is not None:
        print(f"Image size: {img.shape}")
    else:
        print("❌ Failed to load with OpenCV")
    
    # Test OCR
    result = read_chinese_mark(img_bytes, deep_mode=False)
    
    text = result.get("text", "")
    confidence = result.get("confidence", 0)
    candidates = result.get("candidates", [])
    database_valid = result.get("database_valid", False)
    
    print(f"\nResult:")
    print(f"  Text: '{text}'")
    print(f"  Confidence: {confidence}")
    print(f"  Database Valid: {database_valid}")
    print(f"  Candidates ({len(candidates)}): {candidates[:3] if len(candidates) > 3 else candidates}")
    
    if result.get("best_match"):
        match = result["best_match"]["entry"]
        print(f"  Best Match: {match.get('ten_viet', '')} ({match.get('chu_han', '')})")
