from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.core.rate_limit import limiter
from app.routers import analytics, auth, catalog, inventory, messages, sales

app = FastAPI(title="Public Market POS")

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": "Too many requests. Please try again later."})


app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

app.include_router(auth.router, prefix="/api/v1")
app.include_router(inventory.router, prefix="/api/v1")
app.include_router(sales.router, prefix="/api/v1")
app.include_router(catalog.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(messages.router, prefix="/api/v1")


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}
