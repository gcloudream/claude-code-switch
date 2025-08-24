"""Proxy API endpoints for forwarding requests to upstream"""

from fastapi import APIRouter, Request, Response, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import get_db
from app.api.deps import get_api_key
from app.models.api_key import APIKey
from app.services.proxy_service import ProxyService
from app.core.logging import get_logger


logger = get_logger(__name__)
router = APIRouter(tags=["代理"])


# Catch-all route for proxying requests
@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    include_in_schema=False,  # Don't show in API docs
)
async def proxy_request(
    path: str,
    request: Request,
    response: Response,
    api_key: APIKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Proxy all requests to upstream API
    
    This endpoint catches all requests not handled by other routes
    and forwards them to the configured upstream API.
    
    Args:
        path: Request path
        request: FastAPI request object
        response: FastAPI response object
        api_key: Validated API key
        db: Database session
        
    Returns:
        Proxied response from upstream API
    """
    # Skip root path, health check and metrics endpoints
    if path in ["", "health", "metrics", "api/usage", "api/usage/logs", "api/usage/quota", "api/usage/daily", "api"]:
        raise HTTPException(status_code=404, detail="未找到")
    
    # Skip admin endpoints
    if path.startswith("admin/"):
        raise HTTPException(status_code=404, detail="未找到")
    
    # Skip web interface endpoints
    if (path.startswith("dashboard") or path.startswith("static/") or 
        path.startswith("user-login") or path.startswith("user-dashboard")):
        raise HTTPException(status_code=404, detail="未找到")
    
    # Create proxy service
    proxy_service = ProxyService(db)
    
    try:
        # Forward the request
        proxy_response = await proxy_service.forward_request(
            api_key=api_key,
            request=request,
            path=f"/{path}" if not path.startswith("/") else path,
        )
        
        return proxy_response
        
    finally:
        # Close proxy service
        await proxy_service.close()