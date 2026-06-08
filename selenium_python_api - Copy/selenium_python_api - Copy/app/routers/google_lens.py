from fastapi import APIRouter, Form, Depends
from app.security.security import verify_api_key
from app.config import settings
from app import create_app
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import re

router = APIRouter(prefix="/google-lens", tags=["Google Lens"])

@router.post("/search/")
async def google_lens_search(
    api_key: str = Depends(verify_api_key),
    image_url: str = Form(...),
    max_results: int = Form(10),
):
    try:
        if settings.driver is not None:
            try:
                settings.driver.quit()
            except Exception:
                pass

        settings.driver = create_app()
        driver = settings.driver
        
        driver.get("https://www.google.com")
        wait = WebDriverWait(driver, 10)

        # 1. Click Lens icon
        print("📸 Đang tìm icon Lens bằng Smart Selectors...")
        selectors = [
            (By.CSS_SELECTOR, "div[aria-label='Tìm kiếm bằng hình ảnh']"),
            (By.CSS_SELECTOR, "div[aria-label='Search by image']"),
            (By.CSS_SELECTOR, "div[jsname='R5mgy']"),
            (By.XPATH, "//div[@role='button' and contains(@aria-label, 'hình ảnh')]"),
            (By.XPATH, "//div[@role='button' and contains(@aria-label, 'image')]"),
            (By.XPATH, "/html/body/div[2]/div[6]/form/div[1]/div/div[1]/div[3]/div[3]/div[2]/div[3]/svg") # Backup cuối cùng
        ]
        
        lens_button = None
        for by, selector in selectors:
            try:
                lens_button = wait.until(EC.element_to_be_clickable((by, selector)))
                print(f"✅ Tìm thấy Lens bằng: {selector}")
                break
            except:
                continue
        
        if not lens_button:
            raise Exception("❌ Không thể tìm thấy nút Google Lens bằng bất kỳ selector nào.")

        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", lens_button)
            time.sleep(0.5)
            lens_button.click()
        except Exception as e:
            print(f"⚠️ Click thường lỗi, thử JS click: {e}")
            driver.execute_script("arguments[0].click();", lens_button)
        
        time.sleep(1)

        # 2. Nhập URL ảnh
        print("🔗 Đang nhập URL hình ảnh...")
        input_selectors = [
            (By.CSS_SELECTOR, "input[jsname='W7hAGe']"),
            (By.CSS_SELECTOR, "input[placeholder*='hình ảnh']"),
            (By.CSS_SELECTOR, "input[placeholder*='image']"),
            (By.XPATH, "//input[contains(@placeholder, 'hình ảnh')]")
        ]
        
        url_input = None
        for by, selector in input_selectors:
            try:
                url_input = wait.until(EC.presence_of_element_located((by, selector)))
                print(f"✅ Tìm thấy ô nhập bằng: {selector}")
                break
            except:
                continue
        
        if not url_input:
            raise Exception("❌ Không tìm thấy ô nhập URL hình ảnh.")
            
        url_input.clear()
        url_input.send_keys(image_url)
        time.sleep(1)

        # 3. Click nút Tìm kiếm
        print("🔍 Đang nhấn nút Tìm kiếm...")
        btn_selectors = [
            (By.CSS_SELECTOR, "div[jsname='ZtOxCb']"),
            (By.XPATH, "//div[@role='button' and contains(text(), 'Tìm kiếm')]"),
            (By.XPATH, "//div[@role='button' and contains(text(), 'Search')]")
        ]
        
        search_button = None
        for by, selector in btn_selectors:
            try:
                search_button = wait.until(EC.element_to_be_clickable((by, selector)))
                print(f"✅ Tìm thấy nút Search bằng: {selector}")
                break
            except:
                continue

        if search_button:
            search_button.click()
        else:
            print("⚠️ Không thấy nút Search, thử nhấn Enter...")
            url_input.send_keys(Keys.ENTER)

        # Wait for results to load
        time.sleep(5) # Give it some time to load Lens results

        # Extract results
        results = []
        
        # Strategy 1: Smart result extraction
        result_elements = driver.find_elements(By.CSS_SELECTOR, "div[role='listitem'], div.GNCY8c, div.VCOFK")
        for el in result_elements:
            try:
                title_el = el.find_element(By.CSS_SELECTOR, "div[data-item-title='true'], .m76pS, .fXU79e")
                title = title_el.text.strip()
                link_el = el.find_element(By.TAG_NAME, "a")
                href = link_el.get_attribute("href")
                
                if href and title and {"title": title, "url": href} not in results:
                    results.append({"title": title, "url": href})
            except:
                continue

        # Strategy 2: Fallback to all external links
        if not results:
            all_links = driver.find_elements(By.TAG_NAME, "a")
            for link in all_links:
                try:
                    href = link.get_attribute("href")
                    title = link.text.strip()
                    if href and "google.com" not in href and title and len(title) > 5:
                        if {"title": title, "url": href} not in results:
                            results.append({"title": title, "url": href})
                    if len(results) >= max_results:
                        break
                except:
                    continue

        # Chuẩn hóa dữ liệu trả về theo format của dự án
        urls = [r['url'] for r in results]
        
        return {
            "status_code": 200,
            "url": random.choice(urls) if urls else "",
            "urls": urls,
            "results": results[:max_results],
            "total": len(urls)
        }

    except Exception as e:
        return {"status_code": 500, "error": str(e), "url": "", "urls": [], "results": []}
    finally:
        if settings.driver:
            try:
                settings.driver.quit()
            except:
                pass
            settings.driver = None
