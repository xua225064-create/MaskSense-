#!/usr/bin/env python3
"""
Diagnostic tool to test OCR robustness against various misidentifications
"""

import asyncio
import json
import os
from ocr_engine import (
    _get_required_confidence,
    _attempt_ocr_correction,
    _validate_against_database,
    _find_database_matches,
    SIMILAR_CHAR_GROUPS
)

print("=" * 90)
print("🔍 OCR MISIDENTIFICATION DIAGNOSTIC TEST")
print("=" * 90)

# Load database
db_path = os.path.join(os.path.dirname(__file__), "data", "hieu_de_database.json")
with open(db_path, 'r', encoding='utf-8') as f:
    database = json.load(f)

# Find all Vietnamese "Nội Phủ Thị" marks
noi_phu_marks = [entry for entry in database if 'Nội Phủ Thị' in entry.get('ten_viet', '')]
print(f"\n📦 Found {len(noi_phu_marks)} Vietnamese 'Nội Phủ Thị' marks:")
for entry in noi_phu_marks:
    chu_han = entry.get('chu_han', '')
    ten_viet = entry.get('ten_viet', '')
    print(f"   {chu_han} → {ten_viet}")

print("\n" + "=" * 90)
print("[SCENARIO 1] Testing character confusion for Nội Phủ marks")
print("=" * 90)

# Get all characters used in Vietnamese marks
all_chars_used = set()
for entry in noi_phu_marks:
    chu_han = entry.get('chu_han', '')
    for char in chu_han:
        if '\u4e00' <= char <= '\u9fff':
            all_chars_used.add(char)

print(f"\n✓ Characters in Vietnamese marks: {sorted(all_chars_used)}")

# Check which ones are in similarity groups
risky_chars = {}
for char in all_chars_used:
    for group in SIMILAR_CHAR_GROUPS:
        if char in group:
            risky_chars[char] = group
            break

print(f"\n⚠️  Risky characters (in similarity groups):")
for char, group in sorted(risky_chars.items()):
    threshold = SIMILAR_CHAR_GROUPS[group]
    alternatives = list(group - {char})
    print(f"   {char} → alternatives: {alternatives} (threshold: {threshold})")

print("\n" + "=" * 90)
print("[SCENARIO 2] Simulating common OCR errors")
print("=" * 90)

# For each Nội Phủ mark, simulate common OCR errors
test_scenarios = []

for entry in noi_phu_marks:
    chu_han = entry.get('chu_han', '')
    ten_viet = entry.get('ten_viet', '')
    
    # Collect all possible errors by replacing with similar chars
    for pos, char in enumerate(chu_han):
        if char in risky_chars:
            group = risky_chars[char]
            for alternative in (group - {char}):
                wrong_text = chu_han[:pos] + alternative + chu_han[pos+1:]
                test_scenarios.append({
                    'correct': chu_han,
                    'wrong': wrong_text,
                    'correct_char': char,
                    'wrong_char': alternative,
                    'position': pos,
                    'vietnamese': ten_viet
                })

print(f"✓ Generated {len(test_scenarios)} possible OCR error scenarios\n")

# Test first 20 scenarios
print("Testing first 20 scenarios:")
print("-" * 90)

success_count = 0
for i, scenario in enumerate(test_scenarios[:20], 1):
    correct = scenario['correct']
    wrong = scenario['wrong']
    vietnamese = scenario['vietnamese']
    correct_char = scenario['correct_char']
    wrong_char = scenario['wrong_char']
    pos = scenario['position']
    
    print(f"\n{i}. Testing: '{wrong}' (should be '{correct}')")
    print(f"   Error: Position {pos}: '{wrong_char}' → '{correct_char}'")
    print(f"   Vietnamese: {vietnamese}")
    
    # Step 1: Check confidence requirement
    req_conf = _get_required_confidence(wrong)
    print(f"   Required confidence: {req_conf:.2f}")
    
    # Step 2: Try correction
    corrected = _attempt_ocr_correction(wrong)
    if corrected == correct:
        print(f"   ✅ AUTO-CORRECTION: '{wrong}' → '{corrected}'")
        success_count += 1
    elif corrected != wrong:
        print(f"   ⚠️  PARTIAL: '{wrong}' → '{corrected}' (not exactly right)")
    else:
        print(f"   ❌ NO CORRECTION")
        
        # Step 3: Check if database can still find it
        matches = _find_database_matches(wrong)
        if matches:
            best = matches[0]
            if best['match_type'] in ['fuzzy_confusable', 'fuzzy_other']:
                print(f"   💡 BUT: Database fuzzy match found: '{best['matched_text']}' (score: {best['score']:.2f})")
        else:
            print(f"   ❌ Database no match either!")

print("\n" + "=" * 90)
print(f"✅ Auto-correction success rate: {success_count}/{min(20, len(test_scenarios))} = {success_count*100//min(20, len(test_scenarios))}%")
print("=" * 90)

print("\n[SCENARIO 3] Direct database lookup for specific marks")
print("-" * 90)

# Test specific marks that are most confusable
test_marks = [
    ('內府侍北', 'Nội Phủ Thị Bắc'),
    ('內府侍石', 'Simulated OCR error'),
    ('內府侍旨', 'Nội Phủ Thị Chỉ'),
    ('內府侍右', 'Nội Phủ Thị Hữu'),
    ('內府侍左', 'Nội Phủ Thị Tả'),
    ('內府侍中', 'Nội Phủ Thị Trung'),
]

for mark, description in test_marks:
    print(f"\n✓ Mark: {mark} ({description})")
    
    # Direct database lookup
    for entry in database:
        if mark == entry.get('chu_han', ''):
            print(f"   ✅ EXACT MATCH in database")
            print(f"      Vietnamese: {entry.get('ten_viet', '')}")
            print(f"      Dynasty: {entry.get('trieu_dai', '')}")
            break
    else:
        # Try fuzzy matching
        matches = _find_database_matches(mark, max_results=2)
        if matches:
            best = matches[0]
            print(f"   💡 Fuzzy match: {best['matched_text']} (type: {best['match_type']}, score: {best['score']:.2f})")
            entry = best.get('entry', {})
            print(f"      Vietnamese: {entry.get('ten_viet', '')}")
        else:
            print(f"   ❌ No match found")

print("\n" + "=" * 90)
print("✅ Diagnostic test completed")
print("=" * 90)

# Summary and recommendations
print("\n📊 SUMMARY & RECOMMENDATIONS:")
print("-" * 90)
print("""
1. OCR Confidence Requirements:
   - Vietnamese Nội Phủ marks require ULTRA-STRICT (0.72) confidence
   - This filters out most noise but may miss low-quality images
   
2. Character Correction:
   - System automatically corrects 北↔石 and 侍↔佚
   - Need to verify OCR is finding these characters at all
   
3. To fix "vẫn nhận dạng sai":
   a) Provide an actual image for testing
   b) Check if OCR is returning ANYTHING or failing entirely
   c) May need to adjust:
      - Preprocessing (contrast, sharpness, noise removal)
      - Detection parameters (det_limit_side_len, det_db_thresh)
      - Confidence thresholds (may be too strict)
   
4. Alternative approaches if current method fails:
   - Template matching for known mark patterns
   - ORB feature matching (already available in pipeline)
   - Optical character verification with multiple passes
   - Consider allowing lower confidence for clear/certain matches
""")
