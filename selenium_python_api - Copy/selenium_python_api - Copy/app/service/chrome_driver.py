import os
import random
import tempfile
import shutil
import atexit
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from app.config import settings
from app.utils.proxy import test_proxy


class ProxyManager:
    def __init__(self):
        self.proxy_file = "proxy.data"
        self.used_file = "proxy_used.data"

    # ======== Random UA ========
    def random_user_agent(self):
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
            "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
        ]
        return random.choice(user_agents)

    # ======== File Handling ========
    def load_used_proxies(self):
        if not os.path.exists(self.used_file):
            return set()
        with open(self.used_file, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())

    def save_used_proxy(self, proxy_host):
        with open(self.used_file, "a", encoding="utf-8") as f:
            f.write(f"{proxy_host}\n")

    def read_all_proxies(self):
        if not os.path.exists(self.proxy_file):
            print("⚠️ Không có file proxy.data, dùng IP gốc.")
            return []

        proxies = []
        with open(self.proxy_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "|" in line:
                    typ, host = line.split("|", 1)
                else:
                    typ, host = "HTTP", line
                proxies.append({"type": typ.strip().upper(), "host": host.strip()})
        return proxies

    # ======== Core ========
    def get_next_proxy(self):
        all_proxies = self.read_all_proxies()
        if not all_proxies:
            print("🌐 Không có proxy, dùng IP gốc.")
            return None

        used = self.load_used_proxies()
        available = [p for p in all_proxies if p["host"] not in used]

        if not available:
            print("⚠️ Hết proxy mới, reset lại danh sách...")
            if os.path.exists(self.used_file):
                os.remove(self.used_file)
            return self.get_next_proxy()

        # Kiểm tra proxy sống trước khi trả về
        random.shuffle(available)
        for proxy in available:
            scheme = proxy["type"].lower()
            if scheme == "https": scheme = "http" # Selenium thường dùng http scheme cho proxy host
            
            proxy_url = f"{scheme}://{proxy['host']}"
            print(f"📡 Đang kiểm tra proxy: {proxy_url}...")
            
            if test_proxy(proxy_url):
                self.save_used_proxy(proxy["host"])
                proxy["user_agent"] = self.random_user_agent()
                print(f"✅ Proxy OK: {proxy['host']} | UA: {proxy['user_agent']}")
                return proxy
            else:
                print(f"❌ Proxy chết hoặc chậm: {proxy['host']}")
                self.save_used_proxy(proxy["host"]) # Đánh dấu là đã dùng để bốc cái khác
        
        print("⚠️ Tất cả proxy đều không phản hồi, thử dùng IP gốc.")
        return None


# ===============================
# ChromeDriver wrapper
# ===============================
class ChromeDriver:
    def __init__(self):
        self.chromedriver_path = os.environ.get("CHROMEDRIVER_PATH", "").strip()
        self.chrome_path = os.environ.get("CHROME_PATH", "").strip()
        self.proxy_manager = ProxyManager()

    def get_driver(self):
        chrome_options = Options()
        user_data_dir = tempfile.mkdtemp(prefix="chrome_user_")
        atexit.register(lambda: shutil.rmtree(user_data_dir, ignore_errors=True))
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")

        # ===== CÁC CỜ CHỐNG NHẬN DIỆN ROBOT (ANTI-DETECT) =====
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # Random kích thước cửa sổ để giống người dùng thật
        window_sizes = ["1920,1080", "1366,768", "1536,864", "1440,900", "1280,720", "1600,900"]
        chrome_options.add_argument(f"--window-size={random.choice(window_sizes)}")
        
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--lang=en-US,en;q=0.9,vi;q=0.8")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--ignore-certificate-errors")
        
        # Tắt một số cơ chế sandbox có thể làm trang web phát hiện Chrome
        chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")
        # ========================================================

        proxy = self.proxy_manager.get_next_proxy()
        if proxy:
            scheme = "http" if proxy["type"] == "HTTP" else "socks5"
            chrome_options.add_argument(f"--proxy-server={scheme}://{proxy['host']}")
            chrome_options.add_argument(f"--user-agent={proxy['user_agent']}")
        else:
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            print("🌐 Dùng IP gốc")

        if self.chrome_path:
            if os.path.exists(self.chrome_path):
                chrome_options.binary_location = self.chrome_path
            else:
                print(f"⚠️ Không tìm thấy Chrome tại: {self.chrome_path}")

        if self.chromedriver_path and os.path.exists(self.chromedriver_path):
            service = Service(self.chromedriver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            if self.chromedriver_path:
                print(f"⚠️ Không tìm thấy ChromeDriver tại: {self.chromedriver_path}. Đang thử tự động...")
            # Nếu không cấu hình hoặc không tìm thấy, để Selenium tự xử lý
            driver = webdriver.Chrome(options=chrome_options)
            
        # Tiêm mã JavaScript xóa cờ 'webdriver' trước khi trang tải
        stealth_js = """
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.navigator.chrome = { runtime: {}, app: {} };
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en', 'vi']});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
            Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": stealth_js
            },
        )
        
        timeout = int(os.environ.get("PAGE_LOAD_TIMEOUT", 35))
        driver.set_page_load_timeout(timeout)
        
        driver.delete_all_cookies()
        return driver
