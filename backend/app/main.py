import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.router import api_router

# Initialize Loguru intercept logging configuration
setup_logging()

from app.core.config import settings
logger.info(f"Loaded configurations. Whisper model: {settings.WHISPER_MODEL}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware configuration
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Middleware for request timing and request logging via Loguru
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = (time.time() - start_time) * 1000
    logger.info(
        f"Method={request.method} Path={request.url.path} Status={response.status_code} Duration={duration:.2f}ms"
    )
    return response

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception encountered: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal Server Error",
            "errors": [str(exc)]
        }
    )

# Register API Router
app.include_router(api_router, prefix=settings.API_V1_STR)
