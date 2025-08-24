"""Admin API endpoints for managing API keys"""

from typing import Optional
from datetime import timedelta
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import get_db
from app.api.deps import get_admin_token
from app.core.security import (
    verify_admin_credentials,
    create_access_token,
    hash_api_key,
)
from app.services.api_key_service import APIKeyService
from app.schemas.api_key import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyResponse,
    APIKeyListResponse,
    APIKeyUpdateRequest,
    APIKeyStatsResponse,
)
from app.core.logging import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["管理员"])

# Basic authentication for admin login
basic_auth = HTTPBasic()


@router.post("/api/login", response_model=dict)
async def admin_api_login(
    credentials: HTTPBasicCredentials = Depends(basic_auth)
) -> dict:
    """Admin login endpoint
    
    Args:
        credentials: Basic auth credentials
        
    Returns:
        Access token for admin operations
    """
    # Verify admin credentials
    if not verify_admin_credentials(credentials.username, credentials.password):
        logger.warning(
            "admin_login_failed",
            username=credentials.username,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="管理员凭据无效",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    # Create access token
    access_token = create_access_token(
        data={"username": credentials.username, "type": "admin"},
        expires_delta=timedelta(hours=24),  # Admin tokens valid for 24 hours
    )
    
    logger.info(
        "admin_login_success",
        username=credentials.username,
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 86400,  # 24小时有效期
    }


@router.post("/api-keys", response_model=APIKeyCreateResponse)
async def create_api_key(
    request: APIKeyCreateRequest,
    admin_user: str = Depends(get_admin_token),
    db: AsyncSession = Depends(get_db),
) -> APIKeyCreateResponse:
    """Create a new API key (admin only)
    
    Args:
        request: API key creation request
        admin_user: Authenticated admin username
        db: Database session
        
    Returns:
        Created API key with the plain text key (only shown once)
    """
    api_key_service = APIKeyService(db)
    
    # Create the API key
    api_key_obj, plain_key = await api_key_service.create_api_key(
        name=request.name,
        description=request.description,
        token_limit=request.token_limit,
        rate_limit_tier=request.rate_limit_tier,
        expires_in_days=request.expires_in_days,
        allowed_ips=request.allowed_ips,
        allowed_origins=request.allowed_origins,
        metadata=request.metadata,
    )
    
    logger.info(
        "api_key_created_by_admin",
        admin_user=admin_user,
        api_key_id=str(api_key_obj.id),
        name=request.name,
    )
    
    return APIKeyCreateResponse(
        id=api_key_obj.id,
        api_key=plain_key,  # Return the plain text key (only time it's available)
        name=api_key_obj.name,
        description=api_key_obj.description,
        token_limit=api_key_obj.token_limit,
        rate_limit_tier=api_key_obj.rate_limit_tier,
        expires_at=api_key_obj.expires_at,
        created_at=api_key_obj.created_at,
    )


@router.get("/api-keys", response_model=APIKeyListResponse)
async def list_api_keys(
    skip: int = 0,
    limit: int = 100,
    include_deleted: bool = False,
    admin_user: str = Depends(get_admin_token),
    db: AsyncSession = Depends(get_db),
) -> APIKeyListResponse:
    """List all API keys (admin only)
    
    Args:
        skip: Number of items to skip
        limit: Maximum items to return
        include_deleted: Whether to include deleted keys
        admin_user: Authenticated admin username
        db: Database session
        
    Returns:
        List of API keys
    """
    api_key_service = APIKeyService(db)
    
    # Get API keys
    api_keys = await api_key_service.list_api_keys(
        skip=skip,
        limit=limit,
        include_deleted=include_deleted,
    )
    
    # Convert to response format
    items = [
        APIKeyResponse(
            id=key.id,
            name=key.name,
            description=key.description,
            key_prefix=key.key_prefix,
            token_limit=key.token_limit,
            token_used=key.token_used,
            token_remaining=key.token_remaining,
            usage_percentage=key.usage_percentage,
            rate_limit_tier=key.rate_limit_tier,
            request_count=key.request_count,
            error_count=key.error_count,
            is_active=key.is_active,
            created_at=key.created_at,
            updated_at=key.updated_at,
            last_used_at=key.last_used_at,
            expires_at=key.expires_at,
        )
        for key in api_keys
    ]
    
    return APIKeyListResponse(
        items=items,
        total=len(items),
        skip=skip,
        limit=limit,
    )


@router.get("/api-keys/{api_key_id}", response_model=APIKeyResponse)
async def get_api_key(
    api_key_id: UUID,
    admin_user: str = Depends(get_admin_token),
    db: AsyncSession = Depends(get_db),
) -> APIKeyResponse:
    """Get details of a specific API key (admin only)
    
    Args:
        api_key_id: API key ID
        admin_user: Authenticated admin username
        db: Database session
        
    Returns:
        API key details
    """
    api_key_service = APIKeyService(db)
    
    # Get the API key
    api_key = await api_key_service.get_api_key_by_id(api_key_id)
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API密钥未找到",
        )
    
    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        description=api_key.description,
        key_prefix=api_key.key_prefix,
        token_limit=api_key.token_limit,
        token_used=api_key.token_used,
        token_remaining=api_key.token_remaining,
        usage_percentage=api_key.usage_percentage,
        rate_limit_tier=api_key.rate_limit_tier,
        request_count=api_key.request_count,
        error_count=api_key.error_count,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        updated_at=api_key.updated_at,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at,
    )


@router.post("/api-keys/{api_key_id}/disable", response_model=dict)
async def disable_api_key(
    api_key_id: UUID,
    admin_user: str = Depends(get_admin_token),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Disable an API key (admin only)
    
    Args:
        api_key_id: API key ID
        admin_user: Authenticated admin username
        db: Database session
        
    Returns:
        Success message
    """
    api_key_service = APIKeyService(db)
    
    success = await api_key_service.disable_api_key(api_key_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found or operation failed",
        )
    
    logger.info(
        "api_key_disabled_by_admin",
        admin_user=admin_user,
        api_key_id=str(api_key_id),
    )
    
    return {"message": "API密钥已成功禁用"}


@router.post("/api-keys/{api_key_id}/enable", response_model=dict)
async def enable_api_key(
    api_key_id: UUID,
    admin_user: str = Depends(get_admin_token),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Enable an API key (admin only)
    
    Args:
        api_key_id: API key ID
        admin_user: Authenticated admin username
        db: Database session
        
    Returns:
        Success message
    """
    api_key_service = APIKeyService(db)
    
    success = await api_key_service.enable_api_key(api_key_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found or operation failed",
        )
    
    logger.info(
        "api_key_enabled_by_admin",
        admin_user=admin_user,
        api_key_id=str(api_key_id),
    )
    
    return {"message": "API密钥已成功启用"}


@router.delete("/api-keys/{api_key_id}", response_model=dict)
async def delete_api_key(
    api_key_id: UUID,
    hard_delete: bool = False,
    admin_user: str = Depends(get_admin_token),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete an API key (admin only)
    
    Args:
        api_key_id: API key ID
        hard_delete: If True, permanently delete from database
        admin_user: Authenticated admin username
        db: Database session
        
    Returns:
        Success message
    """
    api_key_service = APIKeyService(db)
    
    success = await api_key_service.delete_api_key(api_key_id, hard_delete=hard_delete)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found or operation failed",
        )
    
    logger.info(
        "api_key_deleted_by_admin",
        admin_user=admin_user,
        api_key_id=str(api_key_id),
        hard_delete=hard_delete,
    )
    
    delete_type = "永久删除" if hard_delete else "软删除"
    return {"message": f"API密钥已成功{delete_type}"}


@router.get("/api-keys/{api_key_id}/stats", response_model=APIKeyStatsResponse)
async def get_api_key_stats(
    api_key_id: UUID,
    admin_user: str = Depends(get_admin_token),
    db: AsyncSession = Depends(get_db),
) -> APIKeyStatsResponse:
    """Get statistics for an API key (admin only)
    
    Args:
        api_key_id: API key ID
        admin_user: Authenticated admin username
        db: Database session
        
    Returns:
        API key statistics
    """
    api_key_service = APIKeyService(db)
    
    stats = await api_key_service.get_api_key_statistics(api_key_id)
    
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API密钥未找到",
        )
    
    return APIKeyStatsResponse(**stats)