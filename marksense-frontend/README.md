# MarkSense Frontend

Static frontend for the MarkSense web app.

## Backend URL

Set `MARKSENSE_API_BASE_URL` in the static hosting environment.

For Render Static Site, `render.yaml` writes this value into `frontend-config.js` during build:

```js
window.MARKSENSE_API_BASE_URL = "https://marksense-backend.onrender.com";
```

For local static testing, edit `frontend-config.js`:

```js
window.MARKSENSE_API_BASE_URL = "http://localhost:8000";
```
