#!/usr/bin/env python3
"""Test the API endpoint to verify auto-correction works end-to-end"""

import httpx
import json
import base64
from pathlib import Path

async def test_ocr_endpoint():
    """Test /ocr endpoint with diagnostic info"""
    
    # Check if there's a test image
    uploads_dir = Path("uploads")
    if not uploads_dir.exists():
        uploads_dir.mkdir(exist_ok=True)
    
    # Get any image file from uploads
    image_files = list(uploads_dir.glob("*.jpg")) + list(uploads_dir.glob("*.png"))
    
    if not image_files:
        print("❌ No image files found in uploads/")
        print("   Please upload an image first through the web UI")
        return
    
    image_path = image_files[0]
    print(f"📷 Using image: {image_path}")
    
    # Read image as bytes
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    
    # Prepare request
    client = httpx.AsyncClient(timeout=30.0)
    url = "http://localhost:5001/ocr"
    
    files = {
        "file": (image_path.name, image_bytes, "image/jpeg"),
    }
    
    data = {
        "crop_x": "0",
        "crop_y": "0",
        "crop_w": "1",
        "crop_h": "1",
    }
    
    try:
        print("\n🔄 Sending OCR request...")
        response = await client.post(url, files=files, data=data)
        
        print(f"📨 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n✅ OCR Response:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            # Check if auto-correction happened
            ocr_text = result.get("ocr_text", "")
            if ocr_text:
                print(f"\n🎯 OCR Text: {ocr_text}")
            
            # Check database validation
            database_valid = result.get("database_valid", False)
            print(f"🗄️  Database Valid: {database_valid}")
            
            if result.get("best_match"):
                match = result.get("best_match", {})
                mark = match.get("entry", {})
                print(f"✨ Best Match: {mark.get('ten_viet', '')} ({mark.get('chu_han', '')})")
            else:
                print("❌ No database match found")
                
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
    finally:
        await client.aclose()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_ocr_endpoint())
