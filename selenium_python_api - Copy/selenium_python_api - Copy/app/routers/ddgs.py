from fastapi import APIRouter, Form, Depends
from app.security.security import verify_api_key
from ddgs import DDGS
from typing import Optional
from app.utils.proxy import get_proxy_from_file

import random

router = APIRouter(prefix="/ddgs", tags=["DDGS Search"])

@router.post("/text/")
async def search_text(
    # api_key: str = Depends(verify_api_key),
    query: str = Form(...),
    max_results: int = Form(10),
    region: str = Form("us-en"),
    safesearch: str = Form("moderate"),
    timelimit: Optional[str] = Form(None),
):
    """Tìm kiếm văn bản/trang web sử dụng DDGS."""
    try:
        proxy = get_proxy_from_file()
        ddgs = DDGS(proxy=proxy)
        results = ddgs.text(
            query, 
            region=region, 
            safesearch=safesearch, 
            timelimit=timelimit, 
            max_results=max_results
        )
        
        # Trích xuất danh sách URL từ kết quả
        urls = [r['href'] for r in results] if results else []
        
        data = {
            "status_code": 200,
            "url": random.choice(urls) if urls else "",
            "urls": urls,
            "html": str(results), # Lưu kết quả gốc vào html để tham khảo
        }
        return data
    except Exception as e:
        return {"status_code": 500, "url": "", "urls": [], "html": "", "error": str(e)}

@router.post("/images/")
async def search_images(
    api_key: str = Depends(verify_api_key),
    query: str = Form(...),
    max_results: int = Form(10),
    region: str = Form("us-en"),
    safesearch: str = Form("moderate"),
):
    """Tìm kiếm hình ảnh sử dụng DDGS."""
    try:
        proxy = get_proxy_from_file()
        ddgs = DDGS(proxy=proxy)
        results = ddgs.images(
            query, 
            region=region, 
            safesearch=safesearch, 
            max_results=max_results
        )
        return {"status_code": 200, "results": results}
    except Exception as e:
        return {"status_code": 500, "error": str(e)}

@router.post("/news/")
async def search_news(
    api_key: str = Depends(verify_api_key),
    query: str = Form(...),
    max_results: int = Form(10),
    region: str = Form("us-en"),
    safesearch: str = Form("moderate"),
):
    """Tìm kiếm tin tức sử dụng DDGS."""
    try:
        proxy = get_proxy_from_file()
        ddgs = DDGS(proxy=proxy)
        results = ddgs.news(
            query, 
            region=region, 
            safesearch=safesearch, 
            max_results=max_results
        )
        return {"status_code": 200, "results": results}
    except Exception as e:
        return {"status_code": 500, "error": str(e)}

@router.post("/extract/")
async def extract_content(
    # api_key: str = Depends(verify_api_key),
    url: str = Form(...),
    fmt: str = Form("text_markdown"),
):
    """Trích xuất nội dung từ một URL."""
    try:
        proxy = get_proxy_from_file()
        ddgs = DDGS(proxy=proxy)
        result = ddgs.extract(url, fmt=fmt)
        return {"status_code": 200, "result": result}
    except Exception as e:
        return {"status_code": 500, "error": str(e)}
