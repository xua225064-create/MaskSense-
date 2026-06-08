from fastapi import FastAPI
from app.routers import google, crawler, proxy, freepik, ddgs, google_lens, google_images
import os
from fastapi.middleware.cors import CORSMiddleware

from app.models.db import init_db

init_db()


# Prefix API theo version
api_prefix = f"/api/{os.environ['VERSION_APP']}"

# Tạo instance của FastAPI
app = FastAPI(
    title=os.environ["TITLE_APP"],
    docs_url=f"{api_prefix}/docs",
    redoc_url=f"{api_prefix}/redoc",
    openapi_url=f"{api_prefix}/openapi.json",
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ["ALLOW_ORIGINS"],  # Cho phép tất cả nguồn (hoặc chỉ định danh sách ["http://example.com"])
    allow_credentials=True,
    allow_methods=["*"],  # Cho phép tất cả phương thức (GET, POST, PUT, DELETE, v.v.)
    allow_headers=["*"],  # Cho phép tất cả headers
)

# Include các router vào ứng dụng chính
app.include_router(google.router, prefix=api_prefix)
app.include_router(crawler.router, prefix=api_prefix)
app.include_router(proxy.router, prefix=api_prefix)
app.include_router(freepik.router, prefix=api_prefix)
app.include_router(ddgs.router, prefix=api_prefix)
app.include_router(google_lens.router, prefix=api_prefix)
app.include_router(google_images.router, prefix=api_prefix)


@app.get(f"{api_prefix}/")
def read_root():
    return {"message": f"Welcome to {os.environ['TITLE_APP']}"}
