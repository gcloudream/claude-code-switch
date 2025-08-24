"""Usage API endpoints for users to query their own usage"""

from typing import Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import get_db
from app.api.deps import get_api_key
from app.models.api_key import APIKey
from app.services.usage_log_service import UsageLogService
from app.schemas.usage import (
    UsageLogResponse,
    UsageStatisticsResponse,
    DailyUsageResponse,
)
from app.core.logging import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["使用统计"])


@router.get("/usage", response_model=UsageStatisticsResponse)
async def get_usage_statistics(
    start_date: Optional[datetime] = Query(None, description="筛选开始日期"),
    end_date: Optional[datetime] = Query(None, description="筛选结束日期"),
    api_key: APIKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db),
) -> UsageStatisticsResponse:
    """Get usage statistics for your API key
    
    Args:
        start_date: Optional start date filter
        end_date: Optional end date filter
        api_key: Authenticated API key
        db: Database session
        
    Returns:
        Aggregated usage statistics
    """
    usage_log_service = UsageLogService(db)
    
    # Get statistics
    stats = await usage_log_service.get_usage_statistics(
        api_key_id=api_key.id,
        start_date=start_date,
        end_date=end_date,
    )
    
    logger.info(
        "usage_statistics_retrieved",
        api_key_id=str(api_key.id),
        start_date=start_date.isoformat() if start_date else None,
        end_date=end_date.isoformat() if end_date else None,
    )
    
    return UsageStatisticsResponse(**stats)


@router.get("/usage/daily", response_model=list[DailyUsageResponse])
async def get_daily_usage(
    days: int = Query(30, ge=1, le=365, description="检索天数"),
    api_key: APIKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db),
) -> list[DailyUsageResponse]:
    """Get daily usage statistics for your API key
    
    Args:
        days: Number of days to retrieve (default 30)
        api_key: Authenticated API key
        db: Database session
        
    Returns:
        List of daily usage statistics
    """
    usage_log_service = UsageLogService(db)
    
    # Get daily usage
    daily_stats = await usage_log_service.get_daily_usage(
        api_key_id=api_key.id,
        days=days,
    )
    
    logger.info(
        "daily_usage_retrieved",
        api_key_id=str(api_key.id),
        days=days,
    )
    
    return [DailyUsageResponse(**stat) for stat in daily_stats]


@router.get("/usage/logs", response_model=list[UsageLogResponse])
async def get_usage_logs(
    start_date: Optional[datetime] = Query(None, description="筛选开始日期"),
    end_date: Optional[datetime] = Query(None, description="筛选结束日期"),
    skip: int = Query(0, ge=0, description="跳过项目数"),
    limit: int = Query(100, ge=1, le=1000, description="返回最大项目数"),
    api_key: APIKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db),
) -> list[UsageLogResponse]:
    """Get detailed usage logs for your API key
    
    Args:
        start_date: Optional start date filter
        end_date: Optional end date filter
        skip: Number of items to skip
        limit: Maximum items to return
        api_key: Authenticated API key
        db: Database session
        
    Returns:
        List of usage logs
    """
    usage_log_service = UsageLogService(db)
    
    # Get usage logs
    logs = await usage_log_service.get_usage_logs_by_api_key(
        api_key_id=api_key.id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )
    
    logger.info(
        "usage_logs_retrieved",
        api_key_id=str(api_key.id),
        count=len(logs),
    )
    
    return [
        UsageLogResponse(
            id=log.id,
            api_key_id=log.api_key_id,
            request_id=log.request_id,
            request_method=log.request_method,
            request_path=log.request_path,
            request_size=log.request_size,
            response_status=log.response_status,
            response_size=log.response_size,
            response_time_ms=log.response_time_ms,
            prompt_tokens=log.prompt_tokens,
            completion_tokens=log.completion_tokens,
            total_tokens=log.total_tokens,
            model=log.model,
            is_error=log.is_error,
            error_message=log.error_message,
            error_code=log.error_code,
            total_cost=float(log.total_cost),
            created_at=log.created_at,
        )
        for log in logs
    ]


@router.get("/usage/quota", response_model=dict)
async def get_quota_status(
    api_key: APIKey = Depends(get_api_key),
) -> dict:
    """Get current quota status for your API key
    
    Args:
        api_key: Authenticated API key
        
    Returns:
        Current quota status
    """
    return {
        "token_limit": api_key.token_limit,
        "token_used": api_key.token_used,
        "token_remaining": api_key.token_remaining,
        "usage_percentage": api_key.usage_percentage,
        "is_quota_exceeded": api_key.is_quota_exceeded,
        "rate_limit_tier": api_key.rate_limit_tier,
        "is_active": api_key.is_active,
        "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
        "is_expired": api_key.is_expired,
    }