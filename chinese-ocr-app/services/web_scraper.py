"""
Web Scraper Service — Đọc nội dung bài viết từ URL bằng Selenium + BeautifulSoup.

Sử dụng Selenium để load trang (bao gồm JavaScript-rendered content),
sau đó dùng BeautifulSoup để extract text sạch.
"""
import asyncio
import re
import traceback
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ArticleContent:
    """Nội dung một bài viết đã được scrape."""
    url: str
    title: str
    content: str          # Nội dung text sạch
    word_count: int       # Số từ
    language: str = ""    # Ngôn ngữ phát hiện được
    
    def to_dict(self) -> Dict:
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content[:2000],  # Giới hạn để không quá dài cho LLM
            "word_count": self.word_count,
        }


def _clean_text(raw: str) -> str:
    """Làm sạch text: xóa khoảng trắng thừa, dòng trống."""
    text = re.sub(r'\s+', ' ', raw)
    text = re.sub(r'\n\s*\n', '\n', text)
    return text.strip()


def _extract_article_bs4(html: str, url: str) -> Optional[ArticleContent]:
    """
    Extract nội dung bài viết từ HTML bằng BeautifulSoup.
    Ưu tiên các tag chứa nội dung chính (article, main, .content, etc.)
    """
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html, "lxml")
    
    # Xóa các element không cần thiết
    for tag in soup.find_all(["script", "style", "nav", "footer", "header",
                              "aside", "iframe", "noscript", "form"]):
        tag.decompose()
    
    # Lấy title
    title = ""
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)
    h1 = soup.find("h1")
    if h1:
        title = h1.get_text(strip=True) or title
    
    # Thử tìm nội dung chính theo thứ tự ưu tiên
    content_text = ""
    
    # 1. Tag <article>
    article = soup.find("article")
    if article:
        content_text = article.get_text(separator="\n", strip=True)
    
    # 2. Tag có class/id chứa "content", "post", "article", "entry"
    if not content_text or len(content_text) < 100:
        for selector in ["[class*='content']", "[class*='post']", "[class*='article']",
                          "[class*='entry']", "[id*='content']", "[id*='post']",
                          "main", "[role='main']"]:
            el = soup.select_one(selector)
            if el:
                candidate = el.get_text(separator="\n", strip=True)
                if len(candidate) > len(content_text):
                    content_text = candidate
    
    # 3. Fallback: lấy toàn bộ body
    if not content_text or len(content_text) < 50:
        body = soup.find("body")
        if body:
            content_text = body.get_text(separator="\n", strip=True)
    
    if not content_text:
        return None
    
    content_text = _clean_text(content_text)
    
    # Giới hạn độ dài (tránh gửi quá nhiều text cho LLM)
    max_chars = 3000
    if len(content_text) > max_chars:
        content_text = content_text[:max_chars] + "..."
    
    word_count = len(content_text.split())
    
    return ArticleContent(
        url=url,
        title=title,
        content=content_text,
        word_count=word_count,
    )


async def scrape_url(url: str) -> Optional[ArticleContent]:
    """
    Đọc nội dung một URL bằng httpx (nhanh) hoặc Selenium (nếu cần JS).
    
    Thử httpx trước, nếu thất bại (trang cần JS) thì dùng Selenium.
    """
    # Thử httpx trước (nhanh hơn nhiều so với Selenium)
    result = await _scrape_with_httpx(url)
    if result and result.word_count > 50:
        return result
    
    # Fallback: Selenium
    return await _scrape_with_selenium(url)


async def _scrape_with_httpx(url: str) -> Optional[ArticleContent]:
    """Scrape bằng httpx (HTTP GET đơn giản)."""
    try:
        import httpx
        from config import SCRAPE_TIMEOUT, CHROME_USER_AGENT
        
        headers = {"User-Agent": CHROME_USER_AGENT}
        async with httpx.AsyncClient(
            timeout=SCRAPE_TIMEOUT,
            follow_redirects=True,
            headers=headers,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            # Chỉ xử lý HTML
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return None
            
            html = response.text
            return _extract_article_bs4(html, url)
            
    except Exception as e:
        print(f"[Scraper/httpx] ⚠ {url}: {e}")
        return None


async def _scrape_with_selenium(url: str) -> Optional[ArticleContent]:
    """Scrape bằng Selenium (cho trang cần JavaScript)."""
    try:
        from config import SCRAPE_TIMEOUT
        
        def _selenium_get():
            from services.google_search import _create_chrome_driver
            import time
            
            driver = _create_chrome_driver()
            try:
                driver.set_page_load_timeout(SCRAPE_TIMEOUT)
                driver.get(url)
                time.sleep(2)  # Đợi JS render
                
                html = driver.page_source
                return _extract_article_bs4(html, url)
            finally:
                driver.quit()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _selenium_get)
        return result
        
    except Exception as e:
        print(f"[Scraper/Selenium] ⚠ {url}: {e}")
        return None


async def scrape_multiple_urls(
    urls: List[str],
    max_concurrent: int = 3,
) -> List[ArticleContent]:
    """
    Scrape nhiều URL đồng thời (giới hạn concurrent để tránh bị block).
    
    Args:
        urls: Danh sách URL cần scrape
        max_concurrent: Số URL xử lý đồng thời tối đa
        
    Returns:
        Danh sách ArticleContent (chỉ trả về những URL scrape thành công)
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def _scrape_with_limit(url: str):
        async with semaphore:
            return await scrape_url(url)
    
    tasks = [_scrape_with_limit(u) for u in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    articles = []
    for r in results:
        if isinstance(r, ArticleContent) and r.word_count > 30:
            articles.append(r)
    
    print(f"[Scraper] ✅ Scrape thành công {len(articles)}/{len(urls)} bài viết")
    return articles
