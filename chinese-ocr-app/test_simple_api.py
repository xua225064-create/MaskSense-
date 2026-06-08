#!/usr/bin/env python3
"""Simple API test to check ORB matching"""

import httpx
import asyncio
from pathlib import Path

async def test_api():
    # Get a larger image file
    uploads_dir = Path("uploads")
    images = sorted([f for f in uploads_dir.glob("*.jpg") if f.stat().st_size > 50000])
    
    if not images:
        print("No large images found")
        return
    
    image_path = images[0]
    print(f"Testing with: {image_path.name}")
    
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    
    client = httpx.AsyncClient(timeout=60)
    try:
        response = await client.post(
            "http://localhost:5001/ocr",
            files={"file": (image_path.name, image_bytes, "image/jpeg")},
            data={}
        )
        
        print(f"\nResponse Status: {response.status_code}")
        result = response.json()
        
        # Check key fields
        print(f"Success: {result.get('success', False)}")
        print(f"Mark (chu_han): {result.get('chu_han', 'N/A')}")
        print(f"Vietnamese: {result.get('ten_viet', 'N/A')}")
        print(f"Message: {result.get('message', 'N/A')}")
        
        if result.get('top5'):
            print(f"\nTop 5 matches:")
            for i, m in enumerate(result['top5'][:3], 1):
                print(f"  {i}. {m.get('chu_han', '')} - {m.get('ten_viet', '')}")
    
    finally:
        await client.aclose()

asyncio.run(test_api())
