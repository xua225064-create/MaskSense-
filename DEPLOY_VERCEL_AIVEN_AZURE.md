# MarkSense Deploy: Vercel + Aiven + Azure

This deployment split keeps the web UI static and moves the API/database to managed services.

## 1. Backend on Azure

Use the existing Dockerfile in `chinese-ocr-app/Dockerfile`.

Recommended Azure environment variables:

```text
WEBSITES_PORT=10000
PORT=10000
PRIMARY_LLM=gemini
SEARCH_METHOD=api
SEARCH_ALLOW_API_FALLBACK=true
ENABLE_SELENIUM_IMAGE_SEARCH=false
ENABLE_GOOGLE_IMAGE_HTTP_UPLOAD=false
ENABLE_SERPAPI_IMAGE_SEARCH=false
MARKSENSE_DISABLE_PADDLE_OCR=true
MARKSENSE_CORS_ORIGINS=https://your-vercel-domain.vercel.app,http://localhost:3000
MARKSENSE_CORS_ORIGIN_REGEX=https://.*\.vercel\.app
GEMINI_API_KEY=...
OPENAI_API_KEY=...
GOOGLE_CSE_API_KEY=...
GOOGLE_CSE_CX=...
SERPAPI_KEY=...
APP_PUBLIC_BASE_URL=https://your-vercel-domain.vercel.app
CONTACT_SMTP_USER=...
CONTACT_SMTP_PASSWORD=...
```

After Azure is live, your backend URL will look like:

```text
https://your-backend-name.azurewebsites.net
```

## 2. Frontend on Vercel

Create a Vercel project from the same GitHub repo.

Use these settings:

```text
Framework Preset: Other
Root Directory: marksense-frontend
Build Command: npm run build
Output Directory: .
```

Set this Vercel environment variable:

```text
MARKSENSE_API_BASE_URL=https://your-backend-name.azurewebsites.net
```

The frontend build creates `frontend-config.js`, and `frontend-runtime.js` routes API calls to Azure.

## 3. SQL on Aiven

Use Aiven MySQL if you want the closest path to the existing repo because `database.sql` is already MySQL-flavored.

Create an Aiven MySQL service, then keep these values ready for backend migration:

```text
AIVEN_MYSQL_HOST=...
AIVEN_MYSQL_PORT=...
AIVEN_MYSQL_DATABASE=...
AIVEN_MYSQL_USER=...
AIVEN_MYSQL_PASSWORD=...
AIVEN_MYSQL_SSL_CA=...
```

Set these variables on Azure to enable Aiven MySQL:

```text
MARKSENSE_DB_BACKEND=mysql
AIVEN_MYSQL_HOST=...
AIVEN_MYSQL_PORT=...
AIVEN_MYSQL_DATABASE=defaultdb
AIVEN_MYSQL_USER=avnadmin
AIVEN_MYSQL_PASSWORD=...
MYSQL_SSL_MODE=REQUIRED
```

Local development still uses SQLite unless `MARKSENSE_DB_BACKEND=mysql` is set.

## 4. Deploy Order

1. Create Aiven SQL service.
2. Deploy Azure backend and confirm `/` returns OK.
3. Set Azure URL in Vercel `MARKSENSE_API_BASE_URL`.
4. Deploy Vercel frontend.
5. Add Vercel domain to Google OAuth authorized origins if Google login is used.
