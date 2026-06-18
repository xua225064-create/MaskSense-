# MarkSense Frontend

Static frontend for the MarkSense web app.

## Backend URL

Set `MARKSENSE_API_BASE_URL` in the static hosting environment.

For Vercel, set `MARKSENSE_API_BASE_URL` to the Azure backend URL, then deploy with:

```text
Build Command: npm run build
Output Directory: .
Root Directory: marksense-frontend
```

The build writes this value into `frontend-config.js`:

```js
window.MARKSENSE_API_BASE_URL = "https://your-azure-backend.azurewebsites.net";
```

For local static testing, edit `frontend-config.js`:

```js
window.MARKSENSE_API_BASE_URL = "http://localhost:8000";
```
