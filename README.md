"# HieuDe_Al" 
## save git 
git init
git status 
git add .
git commit -m "Update full system"  
git push -u origin main

## chạy web 
cd d:\HieuDe_AI\chinese-ocr-app
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
## chạy app
cd d:\HieuDe_AI\hieude_mobile
npm install
npx expo start
