"""API dependencies for authentication and authorization"""

from typing import Optional, Tuple
from fastapi import Depends, HTTPException, status, Header, Request, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import get_db
from app.core.security import verify_access_token, verify_admin_credentials, hash_api_key
from app.models.api_key import APIKey
from app.services.api_key_service import APIKeyService
from app.core.logging import get_logger


logger = get_logger(__name__)

# Security scheme for Bearer token
bearer_scheme = HTTPBearer(auto_error=False)


async def get_admin_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    admin_token: Optional[str] = Cookie(None)
) -> str:
    """Verify admin JWT token from Bearer header or cookie
    
    Args:
        credentials: Bearer token credentials
        admin_token: Admin token from cookie
        
    Returns:
        Admin username from token
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    token = None
    
    # Try Bearer token first
    if credentials and credentials.credentials:
        token = credentials.credentials
    # Then try cookie
    elif admin_token:
        token = admin_token
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要管理员身份验证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = verify_access_token(token)
    
    if not token_data or token_data.get("type") != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的管理员令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token_data.get("username")


async def get_api_key(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
) -> APIKey:
    """Get and validate API key from request headers
    
    Args:
        authorization: Authorization header
        x_api_key: X-API-Key header
        request: FastAPI request object
        db: Database session
        
    Returns:
        Validated APIKey object
        
    Raises:
        HTTPException: If API key is invalid or missing
    """
    # Extract API key from headers
    api_key = None
    
    # Check Authorization header (Bearer token)
    if authorization and authorization.startswith("Bearer "):
        api_key = authorization[7:]  # Remove "Bearer " prefix
    # Check X-API-Key header
    elif x_api_key:
        api_key = x_api_key
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要API密钥",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get client IP and origin for validation
    client_ip = request.client.host if request else None
    origin = request.headers.get("Origin") if request else None
    
    # Validate the API key
    api_key_service = APIKeyService(db)
    is_valid, api_key_obj, error_msg = await api_key_service.validate_api_key(
        api_key,
        client_ip=client_ip,
        origin=origin,
    )
    
    if not is_valid:
        logger.warning(
            "api_key_validation_failed",
            error=error_msg,
            client_ip=client_ip,
            origin=origin,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_msg or "无效的API密钥",
        )
    
    return api_key_obj


async def get_optional_api_key(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
) -> Optional[APIKey]:
    """Get API key if provided (optional)
    
    Args:
        authorization: Authorization header
        x_api_key: X-API-Key header
        request: FastAPI request object
        db: Database session
        
    Returns:
        APIKey object if valid, None if not provided
    """
    # Extract API key from headers
    api_key = None
    
    # Check Authorization header (Bearer token)
    if authorization and authorization.startswith("Bearer "):
        api_key = authorization[7:]  # Remove "Bearer " prefix
    # Check X-API-Key header
    elif x_api_key:
        api_key = x_api_key
    
    if not api_key:
        return None
    
    # Get client IP and origin for validation
    client_ip = request.client.host if request else None
    origin = request.headers.get("Origin") if request else None
    
    # Validate the API key
    api_key_service = APIKeyService(db)
    is_valid, api_key_obj, error_msg = await api_key_service.validate_api_key(
        api_key,
        client_ip=client_ip,
        origin=origin,
    )
    
    if not is_valid:
        return None
    
    return api_key_obj