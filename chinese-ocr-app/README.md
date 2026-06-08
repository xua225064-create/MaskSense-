# Chinese Porcelain Reign Mark OCR

Ung dung web doc ky tu khac danh (款識) tren gom su Trung Hoa.

## Cai dat

1. Tao moi moi truong ao (khuyen nghi):

```bash
python -m venv .venv
.venv\Scripts\activate
```

2. Cai thu vien:

```bash
pip install -r requirements.txt
```

## Chay ung dung

```bash
uvicorn main:app --reload
```

Mo trinh duyet tai:

```
http://localhost:8000
```

## Ghi chu

- OCR dung EasyOCR voi `ch_sim` va `ch_tra`.
- Hinh anh co the bi cong/goc, he thong se tu dong tien xu ly va OCR.

## Cau hinh form Contact gui mail

Copy `.env.example` thanh `.env`, sau do dien SMTP:

```env
CONTACT_RECIPIENT=xuatruong30@gmail.com
CONTACT_SMTP_HOST=smtp.gmail.com
CONTACT_SMTP_PORT=587
CONTACT_SMTP_USER=your_gmail_address@gmail.com
CONTACT_SMTP_PASSWORD=your_gmail_app_password
CONTACT_FROM_EMAIL=your_gmail_address@gmail.com
```

Voi Gmail, `CONTACT_SMTP_PASSWORD` phai la App Password, khong phai mat khau dang nhap Gmail.
