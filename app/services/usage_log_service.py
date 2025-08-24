"""Service for tracking API usage logs"""

import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from uuid import UUID
from decimal import Decimal
from sqlalchemy import select, func, and_, or_, Integer
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.usage_log import UsageLog
from app.models.api_key import APIKey
from app.core.logging import get_logger


logger = get_logger(__name__)


class UsageLogService:
    """Service for managing usage logs"""
    
    def __init__(self, db: AsyncSession):
        """Initialize the service
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def create_usage_log(
        self,
        api_key_id: UUID,
        request_id: str,
        request_method: str,
        request_path: str,
        request_size: int,
        response_status: int,
        response_size: int,
        response_time_ms: float,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        model: Optional[str] = None,
        is_error: bool = False,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UsageLog:
        """Create a usage log entry
        
        Args:
            api_key_id: API key ID
            request_id: Unique request ID
            request_method: HTTP method
            request_path: Request path
            request_size: Request size in bytes
            response_status: HTTP response status
            response_size: Response size in bytes
            response_time_ms: Response time in milliseconds
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            total_tokens: Total tokens used
            model: Model name
            is_error: Whether this was an error
            error_message: Error message if applicable
            error_code: Error code if applicable
            client_ip: Client IP address
            user_agent: User agent string
            metadata: Additional metadata
            
        Returns:
            Created UsageLog instance
        """
        # Calculate costs (example pricing)
        input_cost = Decimal(prompt_tokens) / 1000 * Decimal("0.01")  # $0.01 per 1K tokens
        output_cost = Decimal(completion_tokens) / 1000 * Decimal("0.03")  # $0.03 per 1K tokens
        total_cost = input_cost + output_cost
        
        usage_log = UsageLog(
            api_key_id=api_key_id,
            request_id=request_id,
            request_method=request_method,
            request_path=request_path,
            request_size=request_size,
            response_status=response_status,
            response_size=response_size,
            response_time_ms=response_time_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            model=model,
            is_error=is_error,
            error_message=error_message,
            error_code=error_code,
            client_ip=client_ip,
            user_agent=user_agent,
            metadata_json=json.dumps(metadata) if metadata else None,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
        )
        
        self.db.add(usage_log)
        await self.db.commit()
        await self.db.refresh(usage_log)
        
        logger.info(
            "usage_log_created",
            usage_log_id=str(usage_log.id),
            api_key_id=str(api_key_id),
            request_id=request_id,
            total_tokens=total_tokens,
            is_error=is_error,
        )
        
        return usage_log
    
    async def get_usage_logs_by_api_key(
        self,
        api_key_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[UsageLog]:
        """Get usage logs for an API key
        
        Args:
            api_key_id: API key ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of usage logs
        """
        query = select(UsageLog).where(UsageLog.api_key_id == api_key_id)
        
        if start_date:
            query = query.where(UsageLog.created_at >= start_date)
        
        if end_date:
            query = query.where(UsageLog.created_at <= end_date)
        
        query = query.order_by(UsageLog.created_at.desc()).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_usage_statistics(
        self,
        api_key_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get aggregated usage statistics for an API key
        
        Args:
            api_key_id: API key ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Dictionary with aggregated statistics
        """
        # Build the base query
        query = select(
            func.count(UsageLog.id).label("total_requests"),
            func.sum(UsageLog.total_tokens).label("total_tokens"),
            func.sum(UsageLog.prompt_tokens).label("total_prompt_tokens"),
            func.sum(UsageLog.completion_tokens).label("total_completion_tokens"),
            func.sum(UsageLog.total_cost).label("total_cost"),
            func.avg(UsageLog.response_time_ms).label("avg_response_time_ms"),
            func.sum(func.cast(UsageLog.is_error, type_=Integer)).label("error_count"),
        ).where(UsageLog.api_key_id == api_key_id)
        
        if start_date:
            query = query.where(UsageLog.created_at >= start_date)
        
        if end_date:
            query = query.where(UsageLog.created_at <= end_date)
        
        result = await self.db.execute(query)
        stats = result.one()
        
        # Get model usage breakdown
        model_query = select(
            UsageLog.model,
            func.count(UsageLog.id).label("request_count"),
            func.sum(UsageLog.total_tokens).label("total_tokens"),
        ).where(
            and_(
                UsageLog.api_key_id == api_key_id,
                UsageLog.model.isnot(None),
            )
        )
        
        if start_date:
            model_query = model_query.where(UsageLog.created_at >= start_date)
        
        if end_date:
            model_query = model_query.where(UsageLog.created_at <= end_date)
        
        model_query = model_query.group_by(UsageLog.model)
        model_result = await self.db.execute(model_query)
        model_stats = model_result.all()
        
        # Get error breakdown
        error_query = select(
            UsageLog.error_code,
            func.count(UsageLog.id).label("count"),
        ).where(
            and_(
                UsageLog.api_key_id == api_key_id,
                UsageLog.is_error == True,
                UsageLog.error_code.isnot(None),
            )
        )
        
        if start_date:
            error_query = error_query.where(UsageLog.created_at >= start_date)
        
        if end_date:
            error_query = error_query.where(UsageLog.created_at <= end_date)
        
        error_query = error_query.group_by(UsageLog.error_code)
        error_result = await self.db.execute(error_query)
        error_stats = error_result.all()
        
        return {
            "total_requests": stats.total_requests or 0,
            "total_tokens": stats.total_tokens or 0,
            "total_prompt_tokens": stats.total_prompt_tokens or 0,
            "total_completion_tokens": stats.total_completion_tokens or 0,
            "total_cost": float(stats.total_cost or 0),
            "avg_response_time_ms": float(stats.avg_response_time_ms or 0),
            "error_count": stats.error_count or 0,
            "error_rate": (stats.error_count or 0) / (stats.total_requests or 1) * 100,
            "model_usage": [
                {
                    "model": row.model,
                    "request_count": row.request_count,
                    "total_tokens": row.total_tokens,
                }
                for row in model_stats
            ],
            "error_breakdown": [
                {
                    "error_code": row.error_code,
                    "count": row.count,
                }
                for row in error_stats
            ],
        }
    
    async def get_daily_usage(
        self,
        api_key_id: UUID,
        days: int = 30,
    ) -> List[Dict[str, Any]]:
        """Get daily usage statistics
        
        Args:
            api_key_id: API key ID
            days: Number of days to retrieve (default 30)
            
        Returns:
            List of daily usage statistics
        """
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Query for daily aggregates
        query = select(
            func.date(UsageLog.created_at).label("date"),
            func.count(UsageLog.id).label("requests"),
            func.sum(UsageLog.total_tokens).label("tokens"),
            func.sum(UsageLog.total_cost).label("cost"),
            func.sum(func.cast(UsageLog.is_error, type_=Integer)).label("errors"),
        ).where(
            and_(
                UsageLog.api_key_id == api_key_id,
                UsageLog.created_at >= start_date,
            )
        ).group_by(
            func.date(UsageLog.created_at)
        ).order_by(
            func.date(UsageLog.created_at).desc()
        )
        
        result = await self.db.execute(query)
        daily_stats = result.all()
        
        return [
            {
                "date": row.date.isoformat(),
                "requests": row.requests,
                "tokens": row.tokens or 0,
                "cost": float(row.cost or 0),
                "errors": row.errors or 0,
            }
            for row in daily_stats
        ]
    
    async def cleanup_old_logs(self, retention_days: int = 90, batch_size: int = 1000) -> int:
        """Clean up old usage logs in batches to avoid memory issues
        
        Args:
            retention_days: Number of days to retain logs
            batch_size: Number of records to delete per batch
            
        Returns:
            Number of deleted records
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        total_deleted = 0
        
        while True:
            # Delete in batches to avoid memory issues
            query = select(UsageLog.id).where(UsageLog.created_at < cutoff_date).limit(batch_size)
            result = await self.db.execute(query)
            ids_to_delete = [row[0] for row in result.fetchall()]
            
            if not ids_to_delete:
                break
            
            # Delete batch
            delete_query = select(UsageLog).where(UsageLog.id.in_(ids_to_delete))
            result = await self.db.execute(delete_query)
            logs_to_delete = result.scalars().all()
            
            for log in logs_to_delete:
                await self.db.delete(log)
            
            await self.db.commit()
            total_deleted += len(logs_to_delete)
            
            logger.info(
                "batch_logs_cleaned",
                batch_deleted=len(logs_to_delete),
                total_deleted=total_deleted,
                retention_days=retention_days,
            )
        
        logger.info(
            "old_logs_cleaned_complete",
            total_deleted=total_deleted,
            retention_days=retention_days,
        )
        
        return total_deleted