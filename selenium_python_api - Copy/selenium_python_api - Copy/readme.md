# Selenium Python API Automation 🚀


`https://googlechromelabs.github.io/chrome-for-testing/`

Một hệ thống Server API mạnh mẽ được xây dựng bằng **FastAPI** và **Selenium / Crawl4ai**, hỗ trợ tự động hoá các thao tác trình duyệt, crawl dữ liệu web, vượt Captcha bằng âm thanh (Speech-to-Text), và quản lý Proxy xoay vòng.

Đặc biệt, đi kèm với hệ thống là công cụ quản lý giao diện đồ họa (GUI) trực quan giúp điều phối mọi thứ từ cài đặt bảo mật đến quản lý Proxy, hạn chế tối đa việc phải thay đổi mã nguồn hay tự sửa file config.

---

## Tính Năng Chính 🌟

- **⚡ Fast API Backend**: Xử lý đa luồng, hỗ trợ đầy đủ bộ OpenAPI docs tích hợp sẵn (`/docs`).
- **🛡️ Multi-Client Auth**: Cấp phát API Keys độc lập cho nhiều khách hàng, chặn quyền truy cập bằng 1 click từ giao diện.
- **🌐 Proxy Rotation**: Tự động xoay vòng proxy không giới hạn từ tệp dữ liệu, giảm thiểu nguy cơ bị chặn IP, tự động loại bỏ proxy hỏng.
- **🤖 Captcha Solver**: Cấu trúc bóc tách sẵn Audio Text tích hợp gửi đến STT API hỗ trợ nhận diện và vượt qua các trang ReCaptcha.
- **🕹️ GUI Manager App**: Bảng điều khiển Desktop được xây bằng giao diện `ttkbootstrap` Darkmode siêu đẹp, cấu hình mọi thứ bằng tương tác chuột thay vì gõ dòng lệnh.
- **⚙️ Plug & Play Browser**: Khai báo linh hoạt các thư mục Chrome Portable hoặc để Selenium tự động tải phiên bản tương thích mà không crash.

---

## Hướng Dẫn Cài Đặt Khởi Tạo 🛠️

### 1. Cài Đặt Môi Trường
Yêu cầu bạn đã cài đặt Python 3.10 trở lên.
```bash
# Tạo môi trường ảo (Khuyến nghị)
python -m venv .venv

# Kích hoạt môi trường (trên Windows)
.venv\Scripts\activate

# Cài đặt thư viện yêu cầu
pip install -r requirements.txt
```

### 2. Quản Lý Hệ Thống Qua GUI (Quan Trọng)
Trước khi khởi động API, hãy mở bảng điều khiển quản lý:
```bash
python gui_manager.py
```
> **Trong phần Giao Diện Trung Tâm này, bạn hãy thiết lập các tab**:
> - **Tab 1 (Proxy)**: Dán danh sách Proxy chuẩn theo định dạng `HTTP|IP:PORT`.
> - **Tab 2 (Client Keys)**: Sinh các mã xác thực API Key để gửi cho người dùng. Người dùng sẽ gọi lệnh API lên server của bạn đính kèm mã này trong tham số `Authorization Bearer <KEY>`.
> - **Tab 3 (STT Config)**: Thiết lập cổng URL giải mã âm thanh Captcha.
> - **Tab 4 (Chrome Config)**: Khai báo đường dẫn `chrome.exe` và `chromedriver.exe` nội bộ, dọn đường cho việc tải trang của Selenium. Bạn có thể nhấn cái link hỗ trợ ở trong đó để tải gói trình duyệt chuyên biệt dành cho Automation. Trống ô cấu hình thì máy tự nhận diện. Ở đây cũng chứa Time Out cho số giây Load Page.
> - **Tab 5 (.env)**: Kiểm tra lại toàn bộ file `.env` đã được thay đổi trước khi chạy.

### 3. Vận Hành Khởi Chạy Server API 🚦
Sau khi cấu hình đã đầy đủ, chạy lệnh sau để kéo máy chủ lên hoạt động ở port `52514`:
```bash
python run_api.py
```

Tra cứu toàn bộ danh sách API, tham số gửi nhận tại trang: 
`http://127.0.0.1:52514/docs`

---

## Cấu Trúc Các Tệp Tin 📁

- `run_api.py`: Tập lệnh kéo server Uvicorn chạy FastAPI.
- `gui_manager.py`: Phần mềm quản lý Backend API trực quan (Xóa/thêm Key, tải Proxy).
- `proxy.data` / `proxy_used.data`: Cơ sở dữ liệu chữ xoay vòng Proxy.
- `apikeys.data`: Nơi chứa thông tin xác thực danh tính Clients gọi ngầm.
- `app/routers`: Các module chức năng đã chia nhỏ tách biệt của Server (`google.py`, `crawler.py`, v.v..).
- `app/service/chrome_driver.py`: Nhân lõi Bot Browser điều phối trình duyệt, tự động giả lập Proxy, User Agent qua từng luồng.
- `requirements.txt`: Bộ thư viện cốt lõi gọn nhẹ nhất trích lọc ra. 

**Enjoy coding! 🚀**