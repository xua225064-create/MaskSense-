"""
Google Search Service — Tìm kiếm Google bằng cả 2 phương pháp:
1. Google Custom Search API (nhanh, ổn định, có giới hạn quota)
2. Selenium trực tiếp (không giới hạn, chậm hơn, cần Chrome)

Hệ thống tự động chọn: thử API trước, nếu không có key thì dùng Selenium.
"""
import asyncio
import traceback
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class SearchResult:
    """Một kết quả tìm kiếm từ Google."""
    title: str
    url: str
    snippet: str  # Mô tả ngắn

    def to_dict(self) -> Dict[str, str]:
        return {"title": self.title, "url": self.url, "snippet": self.snippet}


# ============================================================
# Phương pháp 1: Google Custom Search API
# ============================================================

async def search_google_api(
    query: str,
    num_results: int = 5,
) -> List[SearchResult]:
    """
    Tìm kiếm bằng Google Custom Search JSON API.
    
    Ưu điểm: Nhanh, ổn định, không cần Chrome
    Nhược điểm: Giới hạn 100 request/ngày (free tier)
    
    Docs: https://developers.google.com/custom-search/v1/overview
    """
    from config import GOOGLE_CSE_API_KEY, GOOGLE_CSE_CX
    
    if not GOOGLE_CSE_API_KEY or not GOOGLE_CSE_CX:
        print("[GoogleSearch/API] ⚠ Thiếu GOOGLE_CSE_API_KEY hoặc GOOGLE_CSE_CX")
        return []
    
    try:
        import httpx
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": GOOGLE_CSE_API_KEY,
            "cx": GOOGLE_CSE_CX,
            "q": query,
            "num": min(num_results, 10),  # API giới hạn tối đa 10
            "lr": "lang_vi|lang_en|lang_zh-CN",  # Tìm tiếng Việt, Anh, Trung
        }
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        results = []
        for item in data.get("items", []):
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("link", ""),
                snippet=item.get("snippet", ""),
            ))
        
        print(f"[GoogleSearch/API] ✅ Tìm được {len(results)} kết quả cho: '{query}'")
        return results
        
    except Exception as e:
        print(f"[GoogleSearch/API] ❌ Error: {e}")
        traceback.print_exc()
        return []


# ============================================================
# Phương pháp 2: Selenium Google Search
# ============================================================

def _create_chrome_driver():
    """Tạo Chrome WebDriver với cấu hình headless."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from config import SELENIUM_HEADLESS, CHROME_USER_AGENT
    
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
    except Exception:
        # Fallback: dùng ChromeDriver có sẵn trên PATH
        service = Service()
    
    options = Options()
    if SELENIUM_HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument(f"--user-agent={CHROME_USER_AGENT}")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    # Giảm log noise
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(20)
    return driver


async def search_google_selenium(
    query: str,
    num_results: int = 5,
) -> List[SearchResult]:
    """
    Tìm kiếm Google bằng Selenium (mở Chrome headless).
    
    Ưu điểm: Không giới hạn quota, có thể bypass nhiều restriction
    Nhược điểm: Chậm hơn API, cần cài Chrome
    """
    from config import SEARCH_TIMEOUT
    
    def _selenium_search():
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        driver = _create_chrome_driver()
        results = []
        
        try:
            # Mở Google
            search_url = f"https://www.google.com/search?q={query}&hl=vi&num={num_results + 3}"
            driver.get(search_url)
            
            # Đợi kết quả tải xong
            WebDriverWait(driver, SEARCH_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div#search"))
            )
            
            # Parse kết quả tìm kiếm
            search_divs = driver.find_elements(By.CSS_SELECTOR, "div.g")
            
            for div in search_divs[:num_results + 5]:
                try:
                    # Tìm link
                    link_el = div.find_element(By.CSS_SELECTOR, "a[href]")
                    url = link_el.get_attribute("href")
                    if not url or "google.com" in url:
                        continue
                    
                    # Tìm tiêu đề
                    try:
                        title_el = div.find_element(By.CSS_SELECTOR, "h3")
                        title = title_el.text
                    except Exception:
                        title = link_el.text or url
                    
                    # Tìm snippet
                    snippet = ""
                    try:
                        # Google thường đặt snippet trong div có class chứa "VwiC3b"
                        snippet_el = div.find_element(
                            By.CSS_SELECTOR,
                            "div[data-sncf], div.VwiC3b, span.aCOpRe"
                        )
                        snippet = snippet_el.text
                    except Exception:
                        pass
                    
                    if url and title:
                        results.append(SearchResult(
                            title=title,
                            url=url,
                            snippet=snippet,
                        ))
                    
                    if len(results) >= num_results:
                        break
                        
                except Exception:
                    continue
            
        finally:
            driver.quit()
        
        return results
    
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, _selenium_search)
        print(f"[GoogleSearch/Selenium] ✅ Tìm được {len(results)} kết quả cho: '{query}'")
        return results
    except Exception as e:
        print(f"[GoogleSearch/Selenium] ❌ Error: {e}")
        traceback.print_exc()
        return []


# ============================================================
# Entry Point — Tự động chọn phương pháp tốt nhất
# ============================================================

async def search_google(
    query: str,
    num_results: int = 5,
    prefer_method: Optional[str] = None,
) -> List[SearchResult]:
    """
    Tìm kiếm Google với fallback tự động.
    
    Thứ tự ưu tiên:
    1. Google Custom Search API (nếu có key)
    2. Selenium (fallback)
    
    Args:
        query: Từ khóa tìm kiếm
        num_results: Số kết quả mong muốn
        prefer_method: "api", "selenium", hoặc None (tự động)
        
    Returns:
        Danh sách SearchResult
    """
    from config import GOOGLE_CSE_API_KEY, SEARCH_N_RESULTS
    
    n = num_results or SEARCH_N_RESULTS
    
    if prefer_method == "selenium":
        return await search_google_selenium(query, n)
    
    if prefer_method == "api":
        return await search_google_api(query, n)
    
    # Tự động: thử API trước
    if GOOGLE_CSE_API_KEY:
        results = await search_google_api(query, n)
        if results:
            return results
        print("[GoogleSearch] API không trả kết quả, thử Selenium...")
    
    # Fallback sang Selenium
    return await search_google_selenium(query, n)


async def search_google_image(
    image_path: str,
    num_results: int = 5,
) -> List[SearchResult]:
    """
    Tìm kiếm Google bằng hình ảnh (Google Lens).
    Sử dụng Selenium để upload ảnh lên Google Images.
    
    Args:
        image_path: Đường dẫn file ảnh trên disk
        num_results: Số kết quả mong muốn
        
    Returns:
        Danh sách SearchResult từ Google Image Search
    """
    import os
    from config import SEARCH_TIMEOUT
    
    if not os.path.exists(image_path):
        print(f"[GoogleImageSearch] ❌ File không tồn tại: {image_path}")
        return []
    
    def _selenium_image_search():
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time
        
        driver = _create_chrome_driver()
        results = []
        
        try:
            # Mở Google Images
            driver.get("https://images.google.com/")
            time.sleep(2)
            
            # Click nút tìm kiếm bằng hình ảnh (icon camera)
            try:
                camera_btn = WebDriverWait(driver, SEARCH_TIMEOUT).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div[aria-label='Search by image'], div.nDcEnd"))
                )
                camera_btn.click()
                time.sleep(1)
            except Exception as e:
                print(f"[GoogleImageSearch] Không tìm thấy nút camera: {e}")
                driver.quit()
                return []
            
            # Upload file ảnh
            try:
                # Tìm input file (có thể ẩn)
                upload_input = WebDriverWait(driver, SEARCH_TIMEOUT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
                )
                abs_path = os.path.abspath(image_path)
                upload_input.send_keys(abs_path)
                time.sleep(3)
            except Exception as e:
                print(f"[GoogleImageSearch] Không thể upload ảnh: {e}")
                driver.quit()
                return []
            
            # Đợi kết quả
            time.sleep(3)
            
            # Parse kết quả - tìm các link bài viết liên quan
            link_elements = driver.find_elements(By.CSS_SELECTOR, "a[href]")
            seen_urls = set()
            
            for link_el in link_elements:
                try:
                    url = link_el.get_attribute("href")
                    if not url or "google.com" in url or url in seen_urls:
                        continue
                    if not url.startswith("http"):
                        continue
                    
                    title = link_el.text.strip()
                    if not title or len(title) < 5:
                        continue
                    
                    seen_urls.add(url)
                    results.append(SearchResult(
                        title=title,
                        url=url,
                        snippet="",
                    ))
                    
                    if len(results) >= num_results:
                        break
                except Exception:
                    continue
        
        finally:
            driver.quit()
        
        return results
    
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, _selenium_image_search)
        print(f"[GoogleImageSearch] ✅ Tìm được {len(results)} kết quả")
        return results
    except Exception as e:
        print(f"[GoogleImageSearch] ❌ Error: {e}")
        traceback.print_exc()
        return []
