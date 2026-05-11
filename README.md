# HieuDe AI - Hệ thống nhận diện hiệu đề gốm sứ cổ

## 📌 Cấu trúc nhánh Git

| Nhánh | Mục đích |
|-------|----------|
| `main` | Nhánh chính ổn định |
| `thuc-tap` | Phiên bản cho báo cáo thực tập |
| `nckh` | Phiên bản phát triển NCKH |

---

## 🔄 Chuyển phiên bản

### Khi cần chạy phiên bản BÁO CÁO THỰC TẬP:
```bash
git stash
git checkout thuc-tap
```

### Khi cần quay lại phiên bản NCKH:
```bash
git stash
git checkout nckh
```

> **Lưu ý:** Lệnh `git stash` sẽ tạm cất những thay đổi chưa commit, tránh xung đột khi chuyển nhánh.
> Sau khi chuyển nhánh, dùng `git stash pop` nếu muốn lấy lại những thay đổi đã cất.

---

## 🚀 Hướng dẫn chạy dự án

### Chạy Backend (Web API)
```bash
cd d:\HieuDe_AI\chinese-ocr-app
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Chạy Mobile App
```bash
cd d:\HieuDe_AI\hieude_mobile
npm install
npx expo start
```

---

## 📋 Save & Push code lên GitHub
```bash
git add .
git commit -m "Mô tả thay đổi"
git push origin <tên-nhánh>
```

---

## 📝 TODO
- [ ] Sửa lại trang giới thiệu
- [ ] Làm thêm trang liên hệ ở trên thanh header
- [ ] Sửa lại database về nguồn gốc của từng hiệu đề cho chính xác
- [ ] Làm hiệu ứng cho trang web
- [ ] Làm thêm giao diện ở trang chủ
