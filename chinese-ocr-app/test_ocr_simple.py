#!/usr/bin/env python3
"""
Test OCR bằng FastAPI endpoint
"""
import asyncio
import json
import sys
from pathlib import Path

# Add current dir to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_ocr_from_file(image_path):
    """Test OCR on an image file"""
    from ocr_engine import read_chinese_mark
    
    image_path = Path(image_path)
    if not image_path.exists():
        print(f"❌ File not found: {image_path}")
        print(f"\n💡 Hướng dẫn:")
        print(f"   1. Save ảnh vào: {image_path}")
        print(f"   2. Hoặc dùng:")
        print(f"      python {__file__} <path_to_image>")
        return
    
    print(f"📷 Đang đọc ảnh: {image_path}")
    with open(image_path, 'rb') as f:
        img_bytes = f.read()
    
    print(f"✓ Size: {len(img_bytes) / 1024:.1f} KB")
    print("\n🚀 Chạy OCR...\n")
    
    result = read_chinese_mark(img_bytes, deep_mode=False)
    
    # In kết quả
    print("\n" + "="*70)
    print("📊 KẾT QUẢ OCR")
    print("="*70)
    
    text = result.get('text', '')
    confidence = result.get('confidence', 0)
    db_valid = result.get('database_valid', False)
    warning = result.get('warning', '')
    
    if text:
        print(f"\n✅ HIỆU ĐỀ: {text}")
        print(f"📈 Confidence: {confidence:.1%}")
        print(f"✓ Database valid: {'YES ✓' if db_valid else 'NO - Need review ⚠'}")
        if warning:
            print(f"⚠️  {warning}")
    else:
        print(f"\n❌ Không đọc được ký tự nào")
        print(f"   Confidence: {confidence:.1%}")
    
    # Candidates
    candidates = result.get('candidates', [])
    if candidates:
        print(f"\n🔍 Ký tự khác (candidates): {', '.join(candidates[:5])}")
    
    # Details
    all_results = result.get('all_results', [])
    if all_results:
        print(f"\n📋 Top 3 variants:")
        for i, item in enumerate(all_results[:3], 1):
            print(f"   {i}. {item['text']}: {item.get('confidence', 0):.1%} (from {item.get('variant', '?')})")
    
    print("\n" + "="*70)

# Main
if __name__ == "__main__":
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        image_path = "uploads/test_mark.jpg"
    
    asyncio.run(test_ocr_from_file(image_path))
