# 🔍 OCR Diagnosis & Action Plan

## Current Status

### ✅ What's Been Fixed
1. **Character Auto-Correction System**
   - Detects confusable characters (北↔石, 侍↔佚)
   - Automatically corrects single-character OCR errors
   - Example: "內府侍石" → corrected to "內府侍北" ✓

2. **Fuzzy Database Matching**
   - Exact matches (score: 1.0)
   - Variant matches (score: 0.95)
   - Fuzzy confusable matches (score: 0.85)
   - Can find marks even with 1 wrong character

3. **Confidence Thresholds**
   - Ultra-strict (0.72): Vietnamese critical characters (侍, 北, etc.)
   - Strict (0.70): Other ambiguous characters
   - Normal (0.50): Standard characters
   - Fallback (0.35): Very blurry images

4. **Similarity Groups**
   - 14 character similarity groups defined
   - Each group mapped to appropriate confidence threshold
   - System raises threshold for risky characters

### ❌ Why System May Still Fail

**The problem is likely ONE of these:**

1. **OCR Returns Nothing**
   - Mark image is too dark/unclear for PaddleOCR
   - Mark is outside the detected text region
   - Image preprocessing removes the mark

2. **OCR Returns Low Confidence**
   - Confidence too low even with current MIN_CONF=0.50
   - Our filtering is still too strict
   - Real images have lower quality than expected

3. **Auto-Correction Breaks Valid Results**
   - Correction system attempts to "fix" correct text
   - Fuzzy matching returns wrong suggestions

4. **Database Issue**
   - Mark is not in hieu_de_database.json
   - Mark name is spelled differently

## How to Diagnose

### Step 1: Test with a Real Image
```bash
python test_ocr_real.py <path_to_ceramic_mark_image.jpg>
```

This will show:
- What raw OCR returns (exact text, confidence)
- Whether it passes confidence filtering
- What database matches it finds
- Why it passed or failed at each step

### Step 2: Understand the Output

The output will show:
- **[STEP 1]** Image loading status
- **[STEP 2]** Raw OCR results with confidence scores
- **Candidates** - all OCR variants
- **Best Match** - database lookup result
- **Status Report** - clear explanation of what happened

### Step 3: Interpret the Results

**Scenario A: No Text Detected**
```
❌ NO TEXT DETECTED
Possible causes:
  1. No ceramic mark in image
  2. Mark too small/unclear
  3. Mark outside expected region
  4. Image quality poor (dark/bright/blurry)
```
**Action:** Improve image - better lighting, clearer view of mark

**Scenario B: Text Detected But Not Confirmed**
```
⚠️ TEXT DETECTED BUT NOT CONFIRMED
   Detected: '內府侍石'
   Warning: OCR read '石' but should be '北'?
```
**Action:** System detected error and auto-correction should fix it. If it doesn't, may need to add more character pairs to SIMILAR_CHAR_GROUPS

**Scenario C: Success**
```
✅ SUCCESS - MARK IDENTIFIED
   Detected: '內府侍北'
   Confirmed: Nội Phủ Thị Bắc (內府侍北)
```
**Action:** ✓ Perfect - mark is identified correctly

## Available Testing Tools

### 1. test_ocr_real.py
**Best for:** Testing with real ceramic mark images
```bash
python test_ocr_real.py uploads/mark.jpg      # Single image
python test_ocr_real.py uploads/              # All images in folder
```

### 2. test_correction.py
**Best for:** Verifying character correction works
```bash
python test_correction.py
# Tests: 內府侍石 → 內府侍北, etc.
```

### 3. test_diagnostic.py
**Best for:** Understanding what errors are possible
```bash
python test_diagnostic.py
# Shows all possible OCR misidentifications for Vietnamese marks
```

### 4. test_system.py
**Best for:** Verifying entire system integration
```bash
python test_system.py
# 4 comprehensive tests with simulated scenarios
```

## What I Need From You

### Option 1: Quick Debug (Recommended)
1. Save a ceramic mark image to `uploads/mark.jpg`
2. Run: `python test_ocr_real.py uploads/mark.jpg`
3. Share the output with me
4. I'll tell you exactly what's wrong and fix it

### Option 2: Provide Image Details
- **Screenshot** of what you're seeing wrong
- **Original image** of the ceramic mark
- **Exact text** you expect OCR to return
- **Current error message** from the app

## Configuration Tuning

If you find issues, these are the knobs we can adjust:

### In `ocr_engine.py`:
- `MIN_CONF = 0.50` → Lower for more permissive, higher for strict
- `MIN_CONF_FALLBACK = 0.35` → Affects blurry image handling
- `SIMILAR_CHAR_GROUPS` → Add new confusable character pairs
- `_variant_sort_key()` → Change how variants are prioritized

### In `run_ocr()`:
- Detection parameters in PaddleOCR initialization
- Preprocessing parameters (contrast, sharpening, etc.)
- Fallback strategies for low confidence

### In `read_chinese_mark()`:
- ROI detection thresholds
- Image preprocessing pipeline
- Upscaling factors

## Quick Fix Commands

If image quality is the issue:
```bash
# Enable aggressive preprocessing
# Uncomment in ocr_engine.py:preprocess_google_image()

# Or adjust detection parameters:
# ocr = PaddleOCR(det_db_thresh=0.2)  # More sensitive detection
```

If confidence is still too strict:
```python
# Temporarily lower threshold for testing
MIN_CONF = 0.40  # More permissive
```

If specific character confusion persists:
```python
# Add to SIMILAR_CHAR_GROUPS in ocr_engine.py
frozenset(['new_char', 'confused_with']): 0.70,
```

## Next Steps

1. **Provide image** → Run test_ocr_real.py
2. **Share output** → I'll see the exact issue
3. **Apply fix** → Adjust parameters based on findings
4. **Verify** → Re-test with same image

---

**Status:** System is ready for real-world testing, awaiting ceramic mark image for debugging.

Last updated: 2025-05-11
