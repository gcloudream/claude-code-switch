"""Main FastAPI application"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from prometheus_client import make_asgi_app
from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.db.base import init_db, close_db
from app.api import admin, usage, proxy, web


# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("启动Claude API中转站", version="0.1.0", env=settings.app_env)
    
    # Initialize database
    await init_db()
    logger.info("数据库初始化完成")
    
    yield
    
    # Shutdown
    logger.info("关闭Claude API中转站")
    await close_db()


# Create FastAPI app
app = FastAPI(
    title="Claude API 中转站",
    description="Claude API 中转服务，提供令牌管理和使用统计功能",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/admin/docs" if settings.debug else None,  # Only show docs in debug mode
    redoc_url="/admin/redoc" if settings.debug else None,
    openapi_url="/admin/openapi.json" if settings.debug else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_credentials,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)

# Add GZip middleware for response compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="app/templates")


# Custom exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(
        "unhandled_exception",
        method=request.method,
        path=request.url.path,
        error=str(exc),
        exc_info=exc,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "服务器内部错误"},
    )


# Root endpoint is handled by web.router now
# Keeping this for API compatibility if accessed via API key
@app.get("/api", tags=["根目录"])
async def api_root():
    """API根目录端点"""
    return {
        "service": "Claude API 中转站",
        "version": "0.1.0",
        "status": "运行中",
        "documentation": "/admin/docs" if settings.debug else None,
    }


# Health check endpoint
@app.get("/health", tags=["健康检查"])
async def health_check():
    """健康检查端点"""
    return {
        "status": "健康",
        "service": "claude-api-中转站",
        "version": "0.1.0",
        "environment": settings.app_env,
    }


# Mount metrics endpoint
if settings.enable_metrics:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)


# Include routers
app.include_router(admin.router)
app.include_router(usage.router)
app.include_router(web.router)

# Proxy router must be last (catch-all)
app.include_router(proxy.router)