#!/usr/bin/env python3
"""
Test OCR trên ảnh được upload
"""
import sys
import json
import base64
from ocr_engine import read_chinese_mark

# Lấy path ảnh từ argument
if len(sys.argv) < 2:
    print("Usage: python test_ocr_image.py <image_path>")
    sys.exit(1)

image_path = sys.argv[1]

# Đọc ảnh
try:
    with open(image_path, 'rb') as f:
        img_bytes = f.read()
    print(f"✓ Đã load ảnh: {image_path} ({len(img_bytes)} bytes)")
except Exception as e:
    print(f"✗ Lỗi đọc ảnh: {e}")
    sys.exit(1)

# Chạy OCR
print("\n" + "="*70)
print("🚀 CHẠY OCR...")
print("="*70 + "\n")

try:
    result = read_chinese_mark(img_bytes, deep_mode=False)
    
    print("\n" + "="*70)
    print("📊 KẾT QUẢ OCR")
    print("="*70)
    
    print(f"\n✅ Hiệu đề: '{result.get('text', '')}'")
    print(f"📈 Confidence: {result.get('confidence', 0):.1%}")
    print(f"✓ Database valid: {result.get('database_valid', False)}")
    
    if result.get('warning'):
        print(f"⚠️  {result['warning']}")
    
    if result.get('candidates'):
        print(f"\n🔍 Candidates khác:")
        for i, cand in enumerate(result['candidates'][:5], 1):
            print(f"  {i}. {cand}")
    
    if result.get('all_results'):
        print(f"\n📋 Chi tiết các variants:")
        for item in result['all_results'][:5]:
            print(f"  - {item['text']}: confidence={item.get('confidence', 0):.1%} (from {item.get('variant', 'unknown')})")
    
    print("\n" + "="*70)
    print("Full Result (JSON):")
    print("="*70)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
except Exception as e:
    import traceback
    print(f"\n✗ OCR Error: {e}")
    print(traceback.format_exc())
    sys.exit(1)
