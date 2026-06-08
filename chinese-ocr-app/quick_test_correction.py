#!/usr/bin/env python3
"""Quick test of auto-correction"""

from ocr_engine import (
    _attempt_ocr_correction, 
    _get_required_confidence, 
    _find_database_matches,
    read_chinese_mark
)

print("=" * 80)
print("🔧 DIRECT CORRECTION TEST")
print("=" * 80)

# Test 1: Direct correction function
print("\n[TEST 1] Auto-correction function")
wrong_text = '內府侍石'
print(f"Input: '{wrong_text}'")

corrected = _attempt_ocr_correction(wrong_text)
print(f"Corrected: '{corrected}'")

if corrected != wrong_text:
    print(f"✅ CORRECTION WORKED: '{wrong_text}' → '{corrected}'")
else:
    print(f"❌ NO CORRECTION")

# Test 2: Database lookup
print("\n[TEST 2] Database lookup after correction")
matches = _find_database_matches(corrected)
if matches:
    best = matches[0]
    entry = best.get('entry', {})
    print(f"✅ FOUND: {entry.get('chu_han', '')} ({entry.get('ten_viet', '')})")
else:
    print(f"❌ NOT FOUND in database")

# Test 3: Confidence check
print("\n[TEST 3] Confidence requirements")
conf_wrong = _get_required_confidence(wrong_text)
conf_correct = _get_required_confidence(corrected)
print(f"'{wrong_text}' requires: {conf_wrong:.2f}")
print(f"'{corrected}' requires: {conf_correct:.2f}")

print("\n" + "=" * 80)
print("✅ All tests completed")
print("=" * 80)
