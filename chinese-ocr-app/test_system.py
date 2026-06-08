"""
Test script for HieuDe AI Ceramic Mark Recognition System
Kiểm tra hệ thống OCR, LLM, và database validation
"""
import asyncio
import json
from ocr_engine import _get_required_confidence
from services.llm_service import call_llm

print("=" * 70)
print("🧪 HIEUDE AI - Ceramic Mark Recognition System Test")
print("=" * 70)

# ============================================================
# Test 1: Confidence Threshold System
# ============================================================
print("\n[TEST 1] Confidence Threshold for Vietnamese Ceramics")
print("-" * 70)

test_marks = [
    "內府侍北",  # Nội Phủ Thị Bắc (ID 90 in database)
    "內府侍旨",  # Nội Phủ Thị Chỉ (ID 84)
    "內府侍中",  # Nội Phủ Thị Trung (ID 86)
    "康熙年製",  # Kangxi Period
    "乾隆年製",  # Qianlong Period
]

for mark in test_marks:
    conf = _get_required_confidence(mark)
    status = "🔴 ULTRA-STRICT" if conf >= 0.70 else "🟡 STRICT" if conf >= 0.65 else "🟢 NORMAL"
    print(f"  {mark:<12} → Confidence: {conf:.2f}  {status}")

# ============================================================
# Test 2: Database Validation
# ============================================================
print("\n[TEST 2] Database Lookup")
print("-" * 70)

try:
    with open("data/hieu_de_database.json", "r", encoding="utf-8") as f:
        db = json.load(f)
    
    # Find Vietnamese ceramics
    viet_marks = [item for item in db if "Nội Phủ" in item.get("ten_viet", "")]
    
    print(f"✅ Database loaded: {len(db)} marks total")
    print(f"✅ Vietnamese 'Nội Phủ' series: {len(viet_marks)} marks")
    
    # Show specific mark
    target_mark = next((item for item in db if "內府侍北" in item.get("chu_han", "")), None)
    if target_mark:
        print(f"\n📍 Found: {target_mark['chu_han']}")
        print(f"   ID: {target_mark['id']}")
        print(f"   Vietnamese: {target_mark['ten_viet']}")
        print(f"   Dynasty: {target_mark['trieu_dai']}")
        print(f"   Period: {target_mark['nien_dai']}")
except Exception as e:
    print(f"❌ Database error: {e}")

# ============================================================
# Test 3: LLM Integration (Ollama)
# ============================================================
print("\n[TEST 3] LLM Integration Test (Ollama)")
print("-" * 70)

async def test_llm():
    print("Testing Ollama LLM...")
    result = await call_llm(
        prompt="Hiệu đề gốm: 內府侍北 là gì? (Vietnamese ceramic mark)",
        provider="ollama"
    )
    if result:
        print(f"✅ Ollama Response ({len(result)} chars):")
        print(f"   {result[:150]}...")
    else:
        print("⚠️  Ollama không sẵn sàng, thử Gemini...")
        result = await call_llm(
            prompt="Hiệu đề gốm: 內府侍北 là gì?",
            provider="gemini"
        )
        if result:
            print(f"✅ Gemini Response ({len(result)} chars):")
            print(f"   {result[:150]}...")
        else:
            print("❌ Không có LLM nào sẵn sàng")

asyncio.run(test_llm())

# ============================================================
# Test 4: Full Pipeline Simulation
# ============================================================
print("\n[TEST 4] Full Pipeline Simulation")
print("-" * 70)

async def full_pipeline_test():
    """Simulate end-to-end processing"""
    
    # Simulate OCR result
    ocr_text = "內府侍北"
    print(f"📸 Simulated OCR Result: {ocr_text}")
    
    # Step 1: Confidence check
    conf = _get_required_confidence(ocr_text)
    print(f"🔍 Required Confidence: {conf:.2f}")
    
    # Step 2: Database lookup
    try:
        with open("data/hieu_de_database.json", "r", encoding="utf-8") as f:
            db = json.load(f)
        db_match = next((item for item in db if ocr_text in item.get("chu_han", "")), None)
        if db_match:
            print(f"✅ Database Match: {db_match['ten_viet']} (ID {db_match['id']})")
            db_valid = True
        else:
            print(f"⚠️  Not found in database")
            db_valid = False
    except Exception as e:
        print(f"❌ Database error: {e}")
        db_valid = False
    
    # Step 3: LLM verification
    print(f"🤖 LLM Verification...")
    result = await call_llm(
        prompt=f"Xác định hiệu đề gốm: {ocr_text} - thuộc triều đại nào?",
        provider="ollama"
    )
    if result:
        print(f"✅ LLM Result:")
        print(f"   {result[:100]}...")
    
    # Final result
    print(f"\n📊 Final Result:")
    print(f"   OCR Text: {ocr_text}")
    print(f"   Confidence Required: {conf:.2f}")
    print(f"   Database Valid: {db_valid}")
    print(f"   Status: {'✅ PASS' if db_valid else '❌ NEEDS REVIEW'}")

asyncio.run(full_pipeline_test())

print("\n" + "=" * 70)
print("✅ All tests completed!")
print("=" * 70)
