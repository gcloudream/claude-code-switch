"""Web interface routes for the Claude API Relay Station"""

from fastapi import APIRouter, Request, Depends, HTTPException, status, Form, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import get_db
from app.api.deps import get_api_key, get_admin_token
from app.models.api_key import APIKey
from app.services.api_key_service import APIKeyService
from app.services.usage_log_service import UsageLogService
from app.core.security import verify_admin_credentials, create_access_token, verify_access_token
from app.core.logging import get_logger
from datetime import timedelta
from typing import Optional

logger = get_logger(__name__)
templates = Jinja2Templates(directory="app/templates")

# Add custom filters
def format_number(value):
    """Format large numbers with K/M suffixes"""
    if value >= 1000000:
        return f"{value/1000000:.1f}M"
    elif value >= 1000:
        return f"{value/1000:.1f}K"
    return str(value)

def round_number(value, precision=0):
    """Round number to specified precision"""
    return round(value, precision)

templates.env.filters['format_number'] = format_number
templates.env.filters['round'] = round_number
router = APIRouter(tags=["Web Interface"])


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Home page - redirect to appropriate dashboard"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "page_title": "首页"
    })


@router.get("/user-login", response_class=HTMLResponse)
async def user_login_page(request: Request):
    """User login page for API key input"""
    return templates.TemplateResponse("user_login.html", {
        "request": request,
        "page_title": "用户登录"
    })


@router.get("/user-dashboard", response_class=HTMLResponse)
async def user_dashboard_page(request: Request):
    """User dashboard page (no API key needed - uses session storage)"""
    return templates.TemplateResponse("dashboard/user_dashboard.html", {
        "request": request,
        "page_title": "用户仪表板"
    })


async def get_admin_token_from_cookie(
    admin_token: Optional[str] = Cookie(None)
) -> str:
    """Get admin token from cookie"""
    if not admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要管理员登录"
        )
    
    token_data = verify_access_token(admin_token)
    
    if not token_data or token_data.get("type") != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的管理员令牌"
        )
    
    return token_data.get("username")


# User Dashboard Routes (API Key Authentication)
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    api_key: APIKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db),
):
    """User dashboard page"""
    usage_service = UsageLogService(db)
    
    # Get basic usage statistics
    stats = await usage_service.get_usage_statistics(api_key.id)
    daily_usage = await usage_service.get_daily_usage(api_key.id, days=7)
    
    return templates.TemplateResponse("dashboard/index.html", {
        "request": request,
        "api_key": api_key,
        "stats": stats,
        "daily_usage": daily_usage,
        "page_title": "用户仪表板"
    })


@router.get("/dashboard/stats", response_class=HTMLResponse)
async def dashboard_stats(
    request: Request,
    api_key: APIKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Usage statistics page"""
    usage_service = UsageLogService(db)
    
    # Get detailed statistics
    stats = await usage_service.get_usage_statistics(api_key.id)
    daily_usage = await usage_service.get_daily_usage(api_key.id, days=30)
    
    return templates.TemplateResponse("dashboard/stats.html", {
        "request": request,
        "api_key": api_key,
        "stats": stats,
        "daily_usage": daily_usage,
        "page_title": "使用统计"
    })


@router.get("/dashboard/logs", response_class=HTMLResponse)
async def dashboard_logs(
    request: Request,
    page: int = 1,
    api_key: APIKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Usage logs page"""
    usage_service = UsageLogService(db)
    
    # Get usage logs with pagination
    limit = 50
    skip = (page - 1) * limit
    logs = await usage_service.get_usage_logs_by_api_key(
        api_key.id, skip=skip, limit=limit
    )
    
    return templates.TemplateResponse("dashboard/logs.html", {
        "request": request,
        "api_key": api_key,
        "logs": logs,
        "current_page": page,
        "page_title": "使用日志"
    })


# Admin Routes (JWT Authentication)
@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Admin login page"""
    return templates.TemplateResponse("admin/login.html", {
        "request": request,
        "page_title": "管理员登录"
    })


@router.post("/admin/login", response_class=HTMLResponse)
async def admin_login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    """Process admin login"""
    if not verify_admin_credentials(username, password):
        return templates.TemplateResponse("admin/login.html", {
            "request": request,
            "page_title": "管理员登录",
            "error": "用户名或密码错误"
        })
    
    # Create access token
    access_token = create_access_token(
        data={"username": username, "type": "admin"},
        expires_delta=timedelta(hours=24),
    )
    
    # Create response with redirect
    response = RedirectResponse(url="/admin/dashboard", status_code=302)
    response.set_cookie("admin_token", access_token, httponly=True, max_age=86400)
    
    logger.info("admin_web_login_success", username=username)
    return response


@router.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    admin_user: str = Depends(get_admin_token_from_cookie),
    db: AsyncSession = Depends(get_db),
):
    """Admin dashboard page"""
    api_key_service = APIKeyService(db)
    
    # Get system statistics
    api_keys = await api_key_service.list_api_keys(limit=1000)
    active_keys = [key for key in api_keys if key.is_active]
    
    total_tokens = sum(key.token_used for key in api_keys)
    total_requests = sum(key.request_count for key in api_keys)
    
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "admin_user": admin_user,
        "total_keys": len(api_keys),
        "active_keys": len(active_keys),
        "total_tokens": total_tokens,
        "total_requests": total_requests,
        "page_title": "管理员仪表板"
    })


@router.get("/admin/keys", response_class=HTMLResponse)
async def admin_keys(
    request: Request,
    admin_user: str = Depends(get_admin_token_from_cookie),
    db: AsyncSession = Depends(get_db),
):
    """Admin API keys management page"""
    from datetime import datetime, timezone
    
    api_key_service = APIKeyService(db)
    
    # Get all API keys
    api_keys = await api_key_service.list_api_keys(limit=1000)
    
    return templates.TemplateResponse("admin/keys.html", {
        "request": request,
        "admin_user": admin_user,
        "api_keys": api_keys,
        "page_title": "API密钥管理",
        "now": datetime.now(timezone.utc)
    })


@router.get("/admin/logout")
async def admin_logout():
    """Admin logout"""
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie("admin_token")
    return response