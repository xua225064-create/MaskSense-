#!/usr/bin/env python3
"""
Test OCR character correction system
Kiểm tra hệ thống sửa chữ tự động khi OCR nhầm ký tự
"""

from ocr_engine import (
    _get_required_confidence,
    _attempt_ocr_correction,
    _find_database_matches,
    _validate_against_database,
    SIMILAR_CHAR_GROUPS
)
import json
import os

print("=" * 80)
print("🔬 OCR CHARACTER CORRECTION TEST SYSTEM")
print("=" * 80)

# ===== TEST 1: Character Similarity Groups =====
print("\n[TEST 1] Character Similarity Groups")
print("-" * 80)
print(f"✅ Total similarity groups: {len(SIMILAR_CHAR_GROUPS)}")

# Find the group containing 侍 and 佚
for group in SIMILAR_CHAR_GROUPS:
    if '侍' in group:
        print(f"✅ Found group containing 侍 (thị): {group}")
        print(f"   Threshold: {SIMILAR_CHAR_GROUPS[group]}")

for group in SIMILAR_CHAR_GROUPS:
    if '北' in group:
        print(f"✅ Found group containing 北 (bắc): {group}")
        print(f"   Threshold: {SIMILAR_CHAR_GROUPS[group]}")

# ===== TEST 2: Confidence Requirements =====
print("\n[TEST 2] Confidence Requirements")
print("-" * 80)

test_cases = [
    ('內府侍北', "正确的字符"),
    ('內府侍石', "錯誤: 北→石 (dễ nhầm)"),
    ('內府佚北', "錯誤: 侍→佚 (dễ nhầm)"),
    ('康熙年製', "Ký tự thông thường"),
    ('大清乾隆年製', "Nhiều ký tự"),
]

for text, description in test_cases:
    conf = _get_required_confidence(text)
    status = "🔴 ULTRA-STRICT" if conf >= 0.72 else "🟡 STRICT" if conf >= 0.70 else "🟢 NORMAL"
    print(f"  {text:12} → {conf:.2f}  {status:15}  ({description})")

# ===== TEST 3: Database Matching =====
print("\n[TEST 3] Database Matching (with Fuzzy Search)")
print("-" * 80)

test_cases_db = [
    ('內府侍北', "正確"),
    ('內府侍石', "OCR nhầm: 北→石"),
    ('內府佚北', "OCR nhầm: 侍→佚"),
    ('內府侍旨', "Biến thể hợp lệ"),
]

for text, description in test_cases_db:
    print(f"\n  Input: '{text}' ({description})")
    matches = _find_database_matches(text, max_results=3)
    
    if not matches:
        print(f"    ❌ No matches found")
    else:
        for i, match in enumerate(matches, 1):
            match_type = match.get('match_type', '')
            score = match.get('score', 0)
            matched_text = match.get('matched_text', '')
            entry = match.get('entry', {})
            
            if match_type == 'exact':
                print(f"    {i}. ✅ EXACT MATCH")
            elif match_type == 'variant':
                print(f"    {i}. 🔄 VARIANT")
            elif match_type == 'fuzzy_confusable':
                wrong_char = match.get('wrong_char', '')
                correct_char = match.get('correct_char', '')
                pos = match.get('position', 0)
                print(f"    {i}. 💡 FUZZY (confusable) - '{wrong_char}'→'{correct_char}' @ pos {pos}")
            else:
                print(f"    {i}. 💭 FUZZY (other)")
            
            print(f"       Text: '{matched_text}' | Score: {score:.2f}")
            vietnamese_name = entry.get('ten_viet', '')
            if vietnamese_name:
                print(f"       Vietnamese: {vietnamese_name}")

# ===== TEST 4: Auto-Correction =====
print("\n[TEST 4] Auto-Correction System")
print("-" * 80)

correction_tests = [
    ('內府侍石', "Should correct 石→北"),
    ('內府佚北', "Should correct 佚→侍"),
    ('內府侍北', "Already correct"),
    ('康熙年製', "No correction needed"),
]

for text, description in correction_tests:
    print(f"\n  Input: '{text}' ({description})")
    corrected = _attempt_ocr_correction(text)
    
    if corrected == text:
        print(f"    → No change: '{corrected}' ✓")
    else:
        print(f"    → CORRECTED: '{text}' → '{corrected}' ✅")

# ===== TEST 5: Full Validation Pipeline =====
print("\n[TEST 5] Full Validation Pipeline")
print("-" * 80)

pipeline_tests = [
    ('內府侍北', "Correct input"),
    ('內府侍石', "OCR error - should correct"),
    ('內府佚北', "OCR error - should correct"),
]

for text, description in pipeline_tests:
    print(f"\n  ➜ Processing: '{text}' ({description})")
    print(f"    Step 1: Auto-correct...")
    corrected = _attempt_ocr_correction(text)
    if corrected != text:
        print(f"             ✅ Corrected to: '{corrected}'")
        text = corrected
    else:
        print(f"             ✓ No correction needed")
    
    print(f"    Step 2: Database validation...")
    validation = _validate_against_database(text)
    
    print(f"             Valid: {validation.get('database_valid', False)}")
    print(f"             Warning: {validation.get('warning', 'None')}")
    
    best_match = validation.get('best_match', {})
    if best_match:
        entry = best_match.get('entry', {})
        print(f"             Match: {entry.get('chu_han', '')} ({entry.get('ten_viet', '')})")

print("\n" + "=" * 80)
print("✅ All correction tests completed!")
print("=" * 80)
