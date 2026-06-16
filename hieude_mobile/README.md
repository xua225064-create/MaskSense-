# HieuDe Mobile

Mobile app built with Expo and React Native.

## Run App

Install dependencies:

```powershell
cd D:\HieuDe_AI\hieude_mobile
npm install
```

Start Expo:

```powershell
npm start
```

Or run directly:

```powershell
npx expo start
```

## Common Commands

Run on Android:

```powershell
npm run android
```

Run on iOS:

```powershell
npm run ios
```

Run on web:

```powershell
npm run web
```

Build iOS preview IPA with EAS:

```powershell
npm run build:ios:preview
```
## chaỵ app 
cd D:\HieuDe_AI\chinese-ocr-app
D:\HieuDe_AI\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
## Khi thấy dòng kiểu:
Uvicorn running on http://0.0.0.0:8000
thì để nguyên cửa sổ đó, không tắt. Sau đó mở app trên điện thoại.
## Nếu muốn kiểm tra, mở trên điện thoại:
http://10.215.74.132:8000/api/nckh/status