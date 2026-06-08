"""
Google Search Service — Tìm kiếm Google bằng cả 2 phương pháp:
1. Google Custom Search API (nhanh, ổn định, có giới hạn quota)
2. Selenium trực tiếp (không giới hạn, chậm hơn, cần Chrome)

Hệ thống tự động chọn: thử API trước, nếu không có key thì dùng Selenium.
"""
import asyncio
import atexit
import os
import random
import shutil
import tempfile
import traceback
import unicodedata
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse


@dataclass
class SearchResult:
    """Một kết quả tìm kiếm từ Google."""
    title: str
    url: str
    snippet: str  # Mô tả ngắn

    def to_dict(self) -> Dict[str, str]:
        return {"title": self.title, "url": self.url, "snippet": self.snippet}


SELENIUM_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]
LENS_SOCIAL_DOMAINS = (
    "facebook.", "instagram.", "pinterest.", "tiktok.", "reddit.", "youtube.", "youtu.be",
    "lemon8.", "lemon8-app.",
)
LENS_CONTEXT_KEYWORDS = (
    "porcelain", "ceramic", "mark", "marks", "reign", "dynasty", "kiln",
    "auction", "antique", "hieu de", "gom",
)
LENS_CJK_CONTEXT_KEYWORDS = ("瓷", "窯", "窑", "陶")


def _project_path(value: str) -> Path:
    path = Path(value or "")
    if path.is_absolute():
        return path
    return Path(__file__).resolve().parents[1] / path


def _read_proxy_file(proxy_file: str) -> List[Dict[str, str]]:
    path = _project_path(proxy_file)
    if not path.exists():
        return []

    proxies: List[Dict[str, str]] = []
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "|" in line:
                proxy_type, host = line.split("|", 1)
            else:
                proxy_type, host = "HTTP", line
            proxy_type = proxy_type.strip().upper()
            host = host.strip()
            if proxy_type and host:
                proxies.append({"type": proxy_type, "host": host})
    except Exception as exc:
        print(f"[Selenium/Proxy] Cannot read proxy file {path}: {exc}")
    return proxies


def _load_used_proxy_hosts(used_file: str) -> set:
    path = _project_path(used_file)
    if not path.exists():
        return set()
    try:
        return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}
    except Exception:
        return set()


def _save_used_proxy_host(used_file: str, host: str) -> None:
    if not host:
        return
    path = _project_path(used_file)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(f"{host}\n")
    except Exception as exc:
        print(f"[Selenium/Proxy] Cannot update used proxy file {path}: {exc}")


def _pick_rotating_proxy() -> Optional[Dict[str, str]]:
    from config import SELENIUM_PROXY_FILE, SELENIUM_USED_PROXY_FILE, SELENIUM_USE_ROTATING_PROXY

    if not SELENIUM_USE_ROTATING_PROXY:
        return None

    proxies = _read_proxy_file(SELENIUM_PROXY_FILE)
    if not proxies:
        print("[Selenium/Proxy] No proxy file or empty proxy pool; using direct IP")
        return None

    used_hosts = _load_used_proxy_hosts(SELENIUM_USED_PROXY_FILE)
    available = [proxy for proxy in proxies if proxy["host"] not in used_hosts]
    if not available:
        used_path = _project_path(SELENIUM_USED_PROXY_FILE)
        try:
            used_path.unlink(missing_ok=True)
        except Exception:
            pass
        available = proxies[:]

    proxy = random.choice(available)
    _save_used_proxy_host(SELENIUM_USED_PROXY_FILE, proxy["host"])
    proxy["user_agent"] = random.choice(SELENIUM_USER_AGENTS)
    return proxy


def _selenium_proxy_arg(proxy: Dict[str, str]) -> str:
    proxy_type = (proxy.get("type") or "HTTP").upper()
    scheme = "socks5" if "SOCKS" in proxy_type else "http"
    return f"{scheme}://{proxy.get('host', '').strip()}"


def _external_result_url(raw_url: str) -> str:
    """Unwrap Google redirect/image-result URLs and keep only external pages."""
    if not raw_url:
        return ""
    url = raw_url.strip()
    if url.startswith("//"):
        url = "https:" + url
    parsed = urlparse(url)
    if parsed.netloc.endswith("google.com") or "google." in parsed.netloc:
        params = parse_qs(parsed.query)
        for key in ("url", "q", "imgrefurl"):
            value = params.get(key, [""])[0]
            if value.startswith("http"):
                url = unquote(value)
                break
        else:
            return ""
    elif parsed.netloc.endswith("duckduckgo.com") or "duckduckgo." in parsed.netloc:
        params = parse_qs(parsed.query)
        value = params.get("uddg", [""])[0]
        if value.startswith("http"):
            url = unquote(value)
        else:
            return ""
    parsed = urlparse(url)
    if not parsed.scheme.startswith("http"):
        return ""
    blocked_domains = (
        "google.", "gstatic.", "googleusercontent.", "accounts.google.",
        "support.google.", "policies.google.", "tiktok.", "reddit.", "tumblr.",
        "lemon8.", "lemon8-app.",
    )
    if any(token in parsed.netloc.lower() for token in blocked_domains):
        return ""
    return url


def _fold_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def _lens_item_text(item: Dict[str, Any]) -> str:
    return " ".join([
        item.get("text", ""),
        item.get("aria", ""),
        item.get("title", ""),
        item.get("parent_text", ""),
        item.get("img_alt", ""),
    ]).strip()


def _has_lens_context_keyword(text: str) -> bool:
    folded = _fold_text(text)
    lower = (text or "").lower()
    return (
        any(keyword in folded for keyword in LENS_CONTEXT_KEYWORDS)
        or any(keyword in lower for keyword in LENS_CJK_CONTEXT_KEYWORDS)
    )


def _has_cjk_chars(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in text or "")


def _title_from_url(url: str) -> str:
    parsed = urlparse(url)
    title = parsed.netloc.replace("www.", "")
    path = parsed.path.strip("/").replace("-", " ").replace("_", " ")
    if path:
        title = f"{title} - {path[:80]}"
    return title


def _dedupe_results(results: List[SearchResult], limit: int) -> List[SearchResult]:
    out = []
    seen = set()
    for item in results:
        url = _external_result_url(item.url)
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(SearchResult(
            title=item.title or _title_from_url(url),
            url=url,
            snippet=item.snippet or "",
        ))
        if len(out) >= limit:
            break
    return out


def _looks_like_lens_visual_match(item: Dict[str, Any]) -> bool:
    """Keep source links from Google Lens visual-result cards."""
    url = _external_result_url(item.get("href", ""))
    if not url:
        return False
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if not domain or any(token in domain for token in ("google.", "gstatic.", "googleusercontent.")):
        return False
    if any(token in domain for token in LENS_SOCIAL_DOMAINS):
        return False

    text = _lens_item_text(item)
    if len(text) < 20 or not _has_lens_context_keyword(text):
        return False
    has_image = bool(item.get("has_image"))
    rect = item.get("rect") or {}
    visible_size = float(rect.get("width") or 0) >= 40 and float(rect.get("height") or 0) >= 30

    # Lens visual matches are usually clickable cards with thumbnails. Some
    # source buttons have no nested img but sit next to result-card text.
    return has_image or visible_size


def _lens_candidate_score(item: Dict[str, Any]) -> float:
    score = 0.0
    if item.get("has_image"):
        score += 3.0
    rect = item.get("rect") or {}
    width = float(rect.get("width") or 0)
    height = float(rect.get("height") or 0)
    if width >= 120 and height >= 90:
        score += 2.0
    if width >= 60 and height >= 45:
        score += 1.0

    text = _lens_item_text(item)
    if text:
        score += min(len(text), 120) / 120
    if _has_cjk_chars(text):
        score += 1.5

    url = _external_result_url(item.get("href", ""))
    domain = urlparse(url).netloc.lower()
    if any(token in domain for token in ("sothebys", "christies", "bonhams", "lawsons", "catawiki", "auction")):
        score += 1.5
    if any(token in domain for token in LENS_SOCIAL_DOMAINS):
        score -= 2.0
    return score


def _extract_lens_visual_matches(driver, num_results: int) -> List[SearchResult]:
    """Extract source URLs from Google Lens visual-match cards."""
    script = """
        const anchors = Array.from(document.querySelectorAll('a[href]'));
        return anchors.map((a) => {
            const rect = a.getBoundingClientRect();
            const img = a.querySelector('img');
            const card = a.closest('[data-attrid], [data-hveid], [jsname], div');
            const parentText = card ? (card.innerText || '').trim() : '';
            return {
                href: a.href || a.getAttribute('href') || '',
                text: (a.innerText || '').trim(),
                aria: a.getAttribute('aria-label') || '',
                title: a.getAttribute('title') || '',
                has_image: Boolean(img),
                img_alt: img ? (img.alt || img.getAttribute('aria-label') || '') : '',
                rect: {width: rect.width || 0, height: rect.height || 0, top: rect.top || 0},
                parent_text: parentText.slice(0, 500),
            };
        });
    """
    try:
        raw_items = driver.execute_script(script) or []
    except Exception:
        raw_items = []

    candidates = []
    for item in raw_items:
        if not isinstance(item, dict) or not _looks_like_lens_visual_match(item):
            continue
        url = _external_result_url(item.get("href", ""))
        title = (
            (item.get("text") or "").strip()
            or (item.get("aria") or "").strip()
            or (item.get("title") or "").strip()
            or (item.get("parent_text") or "").strip().split("\n")[0]
            or _title_from_url(url)
        )
        snippet = (item.get("parent_text") or "").strip()
        candidates.append((
            _lens_candidate_score(item),
            SearchResult(title=title[:180], url=url, snippet=snippet[:500]),
        ))

    candidates.sort(key=lambda pair: pair[0], reverse=True)
    return _dedupe_results([result for _, result in candidates], num_results)


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
        response = getattr(e, "response", None)
        status_code = getattr(response, "status_code", None)
        if status_code:
            body = (getattr(response, "text", "") or "").replace("\n", " ")[:240]
            print(f"[GoogleSearch/API] ❌ HTTP {status_code}: {body}")
        else:
            print(f"[GoogleSearch/API] ❌ Error: {type(e).__name__}: {e}")
            traceback.print_exc()
        return []


# ============================================================
# Phương pháp 2: Selenium Google Search
# ============================================================

def _create_chrome_driver():
    """Create Chrome WebDriver with Selenium API helper hardening."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from config import (
        CHROME_PATH,
        CHROMEDRIVER_PATH,
        CHROME_USER_AGENT,
        SEARCH_TIMEOUT,
        SELENIUM_HEADLESS,
    )

    options = Options()
    user_data_dir = tempfile.mkdtemp(prefix="hieude_chrome_")
    atexit.register(lambda: shutil.rmtree(user_data_dir, ignore_errors=True))

    if SELENIUM_HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--lang=en-US,en;q=0.9,vi;q=0.8")
    options.add_argument("--disable-features=IsolateOrigins,site-per-process")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"--window-size={random.choice(['1920,1080', '1366,768', '1536,864', '1440,900', '1280,720', '1600,900'])}")

    proxy = _pick_rotating_proxy()
    user_agent = (proxy or {}).get("user_agent") or random.choice([CHROME_USER_AGENT] + SELENIUM_USER_AGENTS)
    options.add_argument(f"--user-agent={user_agent}")
    if proxy:
        proxy_arg = _selenium_proxy_arg(proxy)
        if proxy_arg:
            options.add_argument(f"--proxy-server={proxy_arg}")
            print(f"[Selenium/Proxy] Using rotating proxy: {proxy_arg}")

    if CHROME_PATH:
        if os.path.exists(CHROME_PATH):
            options.binary_location = CHROME_PATH
        else:
            print(f"[Selenium] Chrome path not found: {CHROME_PATH}")

    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    options.add_experimental_option("useAutomationExtension", False)

    service = None
    if CHROMEDRIVER_PATH:
        if os.path.exists(CHROMEDRIVER_PATH):
            service = Service(CHROMEDRIVER_PATH)
        else:
            print(f"[Selenium] ChromeDriver path not found: {CHROMEDRIVER_PATH}")
    if service is None:
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            print("[Selenium] Resolving ChromeDriver...")
            service = Service(ChromeDriverManager().install())
        except Exception as e:
            print(f"[Selenium] ChromeDriverManager failed: {e}; using Selenium Manager/PATH")
            service = Service()

    print("[Selenium] Starting Chrome WebDriver...")
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(max(SEARCH_TIMEOUT, 20))
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    window.navigator.chrome = { runtime: {}, app: {} };
                    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en', 'vi']});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
                    Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
                """,
            },
        )
        driver.delete_all_cookies()
    except Exception as exc:
        print(f"[Selenium] Stealth bootstrap warning: {exc}")
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
    from config import SEARCH_TIMEOUT, ENABLE_SELENIUM_IMAGE_SEARCH
    
    def _selenium_search():
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
        from urllib.parse import quote
        
        driver = None
        results = []
        
        try:
            # Tạo Chrome driver
            driver = _create_chrome_driver()
            print(f"[GoogleSearch/Selenium] 🌐 Tìm: '{query}'")
            
            # Mở Google (URL-encode query để hỗ trợ CJK characters)
            encoded_query = quote(query, safe='')
            search_url = f"https://www.google.com/search?q={encoded_query}&hl=vi&num={num_results + 3}"
            print(f"[GoogleSearch/Selenium] → {search_url}")
            driver.get(search_url)
            
            # Đợi kết quả tải xong
            try:
                WebDriverWait(driver, SEARCH_TIMEOUT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div#search"))
                )
            except TimeoutException:
                print("[GoogleSearch/Selenium] Standard result container timeout; trying fallback link extraction")
            
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

            if not results:
                for link_el in driver.find_elements(By.CSS_SELECTOR, "a[href]"):
                    try:
                        url = _external_result_url(link_el.get_attribute("href") or "")
                        title = (link_el.text or "").strip()
                        if not url or not title:
                            continue
                        results.append(SearchResult(title=title[:180], url=url, snippet=""))
                        if len(results) >= num_results:
                            break
                    except Exception:
                        continue
        
        except WebDriverException as e:
            error_msg = str(e)
            if "executable_path" in error_msg or "chromedriver" in error_msg.lower():
                print(f"[GoogleSearch/Selenium] ❌ Chrome không tìm thấy. Cài Chrome hoặc ChromeDriver.")
            elif "Chrome not found" in error_msg or "chrome" in error_msg.lower():
                print(f"[GoogleSearch/Selenium] ❌ Chrome browser không cài đặt. Cài Google Chrome.")
            else:
                print(f"[GoogleSearch/Selenium] ❌ WebDriver error: {error_msg}")
            traceback.print_exc()
            
        except TimeoutException:
            print(f"[GoogleSearch/Selenium] ⏱ Timeout tìm kết quả Google")
            
        except Exception as e:
            print(f"[GoogleSearch/Selenium] ❌ Error: {e}")
            traceback.print_exc()
        
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
        
        return results
    
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, _selenium_search)
        if results:
            print(f"[GoogleSearch/Selenium] ✅ Tìm được {len(results)} kết quả")
        else:
            print(f"[GoogleSearch/Selenium] ⚠ Không có kết quả hoặc Chrome lỗi")
        return results
    except Exception as e:
        print(f"[GoogleSearch/Selenium] ❌ Executor error: {e}")
        return []


async def search_duckduckgo_html(
    query: str,
    num_results: int = 5,
) -> List[SearchResult]:
    """Fallback source discovery when Google API/Selenium is blocked."""
    try:
        import httpx
        from bs4 import BeautifulSoup
        from config import CHROME_USER_AGENT

        def _parse_duckduckgo(html: str) -> List[SearchResult]:
            soup = BeautifulSoup(html, "lxml")
            parsed: List[SearchResult] = []
            for node in soup.select(".result"):
                link = node.select_one("a.result__a")
                if not link:
                    continue
                url = _external_result_url(link.get("href") or "")
                if not url:
                    continue
                snippet_node = node.select_one(".result__snippet")
                parsed.append(SearchResult(
                    title=link.get_text(" ", strip=True) or _title_from_url(url),
                    url=url,
                    snippet=(snippet_node.get_text(" ", strip=True) if snippet_node else ""),
                ))
            if parsed:
                return parsed

            for link in soup.select("a.result-link, a.result__a"):
                url = _external_result_url(link.get("href") or "")
                if not url:
                    continue
                parsed.append(SearchResult(
                    title=link.get_text(" ", strip=True) or _title_from_url(url),
                    url=url,
                    snippet="",
                ))
            return parsed

        results: List[SearchResult] = []
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={"User-Agent": CHROME_USER_AGENT},
        ) as client:
            for endpoint in ("https://duckduckgo.com/html/", "https://lite.duckduckgo.com/lite/"):
                response = await client.get(endpoint, params={"q": query})
                response.raise_for_status()
                results = _dedupe_results(_parse_duckduckgo(response.text), num_results)
                if results:
                    break

        if results:
            print(f"[WebSearch/DDG] ✅ Tìm được {len(results)} nguồn fallback")
        else:
            print("[WebSearch/DDG] ⚠ Không có kết quả fallback")
        return results
    except Exception as e:
        print(f"[WebSearch/DDG] ❌ Error: {type(e).__name__}: {e}")
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
    
    Thứ tự ưu tiên mặc định lấy từ SEARCH_METHOD.
    Với dự án này Selenium là chính để tránh Google CSE API 403.
    
    Args:
        query: Từ khóa tìm kiếm
        num_results: Số kết quả mong muốn
        prefer_method: "api", "selenium", hoặc None (tự động)
        
    Returns:
        Danh sách SearchResult (có thể empty nếu cả 2 cách đều fail)
    """
    from config import GOOGLE_CSE_API_KEY, SEARCH_ALLOW_API_FALLBACK, SEARCH_METHOD, SEARCH_N_RESULTS
    
    n = num_results or SEARCH_N_RESULTS
    method = (prefer_method or SEARCH_METHOD or "selenium").lower()
    
    # Selenium là đường chính: mở Chrome thật, đọc kết quả Google trực tiếp.
    if method in {"selenium", "selenium_only"}:
        print(f"[GoogleSearch] 🔍 Cố gắng Selenium cho: '{query}'")
        results = await search_google_selenium(query, n)
        if results:
            return results
        if method == "selenium_only":
            print("[GoogleSearch] Selenium-only mode: no API or HTTP fallback")
            return []
        if method != "selenium_only" and SEARCH_ALLOW_API_FALLBACK and GOOGLE_CSE_API_KEY:
            print(f"[GoogleSearch] ⚠ Selenium lỗi, fallback API...")
            results = await search_google_api(query, n)
            if results:
                return results
        print(f"[GoogleSearch] ⚠ Google không trả nguồn, dùng web fallback...")
        return await search_duckduckgo_html(query, n)
    
    # Nếu yêu cầu API
    if prefer_method == "api":
        print(f"[GoogleSearch] 🔍 Dùng API cho: '{query}'")
        results = await search_google_api(query, n)
        if results:
            return results
        print(f"[GoogleSearch] ⚠ Google API không trả nguồn, dùng web fallback...")
        return await search_duckduckgo_html(query, n)
    
    if method in {"api_then_selenium", "auto"}:
        print(f"[GoogleSearch] 🔍 Thử API cho: '{query}'")
        if GOOGLE_CSE_API_KEY:
            results = await search_google_api(query, n)
            if results:
                return results
            print(f"[GoogleSearch] ⚠ API không trả kết quả, thử Selenium...")
        print(f"[GoogleSearch] 🔍 Thử Selenium...")
        results = await search_google_selenium(query, n)
        if not results:
            print(f"[GoogleSearch] ⚠ Cả API và Selenium đều fail hoặc không có kết quả, dùng web fallback...")
            return await search_duckduckgo_html(query, n)
        return results

    # Fallback cho giá trị cấu hình lạ: dùng Selenium, không dùng API 403.
    print(f"[GoogleSearch] ⚠ SEARCH_METHOD='{method}' không hợp lệ, dùng Selenium")
    results = await search_google_selenium(query, n)
    if not results:
        return await search_duckduckgo_html(query, n)
    return results

    # Unreachable legacy guard kept intentionally out of default flow.
    if False and GOOGLE_CSE_API_KEY:
        results = await search_google_api(query, n)
        if results:
            return results


async def search_google_image(
    image_path: str,
    num_results: int = 5,
    force_selenium: bool = False,
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
    from config import ENABLE_GOOGLE_IMAGE_HTTP_UPLOAD, ENABLE_SELENIUM_IMAGE_SEARCH, SEARCH_TIMEOUT
    
    if not os.path.exists(image_path):
        print(f"[GoogleImageSearch] ❌ File không tồn tại: {image_path}")
        return []

    if ENABLE_GOOGLE_IMAGE_HTTP_UPLOAD and not force_selenium:
        http_results = await _search_google_image_upload_http(image_path, num_results=num_results)
        if http_results:
            print(f"[GoogleImageSearch/HTTP] ✅ Tìm được {len(http_results)} kết quả")
            return http_results
    if not ENABLE_SELENIUM_IMAGE_SEARCH and not force_selenium:
        print("[GoogleImageSearch] ⚠ HTTP upload không có kết quả; bỏ qua Selenium image search để tránh timeout")
        return []
    if force_selenium:
        print("[GoogleImageSearch] Selenium image search is forced; skipping image-search API/HTTP upload")
    
    def _selenium_image_search():
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time
        
        driver = _create_chrome_driver()
        results = []
        
        try:
            # Mở Google Images
            driver.get("https://images.google.com/?hl=vi")
            time.sleep(1.5)
            
            # Click nút tìm kiếm bằng hình ảnh (icon camera)
            try:
                camera_selectors = [
                    "div[aria-label*='Search by image']",
                    "button[aria-label*='Search by image']",
                    "span[aria-label*='Search by image']",
                    "div[aria-label*='Tìm kiếm bằng hình ảnh']",
                    "button[aria-label*='Tìm kiếm bằng hình ảnh']",
                    "span[aria-label*='Tìm kiếm bằng hình ảnh']",
                    "div[aria-label*='Tìm bằng hình ảnh']",
                    "button[aria-label*='Tìm bằng hình ảnh']",
                    "div[jsname='R5mgy']",
                    "div[aria-label='Search by image']",
                    "div[aria-label='TÃ¬m kiáº¿m báº±ng hÃ¬nh áº£nh']",
                    "div.nDcEnd",
                ]
                camera_btn = None
                for selector in camera_selectors:
                    try:
                        camera_btn = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        if camera_btn:
                            break
                    except Exception:
                        continue
                if not camera_btn:
                    raise RuntimeError("Không tìm thấy nút Google Lens/camera")
                driver.execute_script("arguments[0].click();", camera_btn)
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
            except Exception as e:
                print(f"[GoogleImageSearch] Không thể upload ảnh: {e}")
                driver.quit()
                return []
            
            # Đợi Google Lens render grid kết quả và parse các visual-match cards.
            deadline = time.time() + max(SEARCH_TIMEOUT + 10, 25)
            while time.time() < deadline:
                time.sleep(1.5)
                current_url = driver.current_url or ""
                if "/sorry/" in current_url or "google.com/sorry" in current_url:
                    print("[GoogleImageSearch] Google Lens is blocked by sorry/captcha page; switching to text fallback")
                    break
                results = _extract_lens_visual_matches(driver, num_results)
                if len(results) >= num_results:
                    break
                try:
                    driver.execute_script("window.scrollBy(0, Math.max(500, window.innerHeight * 0.7));")
                except Exception:
                    pass

            if not results:
                print(f"[GoogleImageSearch] Không parse được visual matches. URL hiện tại: {driver.current_url}")
        
        finally:
            driver.quit()
        
        return results
    
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, _selenium_image_search)
        results = _dedupe_results(results, num_results)
        print(f"[GoogleImageSearch] ✅ Tìm được {len(results)} kết quả")
        return results
    except Exception as e:
        print(f"[GoogleImageSearch] ❌ Error: {e}")
        traceback.print_exc()
        return []


async def _search_google_image_upload_http(
    image_path: str,
    num_results: int = 5,
) -> List[SearchResult]:
    """
    Try the legacy Google Search-by-Image upload endpoint before Selenium.
    This is often more stable than clicking through the changing Lens UI.
    """
    def _sync_upload() -> List[SearchResult]:
        try:
            import requests
            from bs4 import BeautifulSoup
            from config import CHROME_USER_AGENT

            with open(image_path, "rb") as fh:
                files = {
                    "encoded_image": (
                        os.path.basename(image_path),
                        fh,
                        "image/jpeg",
                    )
                }
                response = requests.post(
                    "https://www.google.com/searchbyimage/upload",
                    params={"hl": "vi"},
                    files=files,
                    headers={"User-Agent": CHROME_USER_AGENT},
                    allow_redirects=True,
                    timeout=25,
                )
            if response.status_code >= 400:
                print(f"[GoogleImageSearch/HTTP] ⚠ status={response.status_code}")
                return []

            soup = BeautifulSoup(response.text, "lxml")
            results: List[SearchResult] = []
            for a in soup.select("a[href]"):
                url = _external_result_url(a.get("href") or "")
                if not url:
                    continue
                title = a.get_text(" ", strip=True) or _title_from_url(url)
                results.append(SearchResult(title=title, url=url, snippet=""))
            return _dedupe_results(results, num_results)
        except Exception as exc:
            print(f"[GoogleImageSearch/HTTP] ⚠ {exc}")
            return []

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_upload)
