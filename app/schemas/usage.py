"""Usage schemas for request/response validation"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class UsageLogResponse(BaseModel):
    """Response schema for usage log"""
    
    id: UUID = Field(..., description="Usage log ID")
    api_key_id: UUID = Field(..., description="API key ID")
    request_id: str = Field(..., description="Request ID")
    request_method: str = Field(..., description="HTTP method")
    request_path: str = Field(..., description="Request path")
    request_size: int = Field(..., description="Request size in bytes")
    response_status: int = Field(..., description="Response status code")
    response_size: int = Field(..., description="Response size in bytes")
    response_time_ms: float = Field(..., description="Response time in milliseconds")
    prompt_tokens: int = Field(..., description="Prompt tokens")
    completion_tokens: int = Field(..., description="Completion tokens")
    total_tokens: int = Field(..., description="Total tokens")
    model: Optional[str] = Field(None, description="Model used")
    is_error: bool = Field(..., description="Whether this was an error")
    error_message: Optional[str] = Field(None, description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    total_cost: float = Field(..., description="Total cost")
    created_at: datetime = Field(..., description="Log creation time")
    
    class Config:
        from_attributes = True


class UsageStatisticsResponse(BaseModel):
    """Response schema for aggregated usage statistics"""
    
    total_requests: int = Field(..., description="Total number of requests")
    total_tokens: int = Field(..., description="Total tokens used")
    total_prompt_tokens: int = Field(..., description="Total prompt tokens")
    total_completion_tokens: int = Field(..., description="Total completion tokens")
    total_cost: float = Field(..., description="Total cost")
    avg_response_time_ms: float = Field(..., description="Average response time in ms")
    error_count: int = Field(..., description="Number of errors")
    error_rate: float = Field(..., description="Error rate percentage")
    model_usage: List[Dict[str, Any]] = Field(..., description="Usage breakdown by model")
    error_breakdown: List[Dict[str, Any]] = Field(..., description="Error breakdown by code")
    
    class Config:
        protected_namespaces = ()


class DailyUsageResponse(BaseModel):
    """Response schema for daily usage statistics"""
    
    date: str = Field(..., description="Date (ISO format)")
    requests: int = Field(..., description="Number of requests")
    tokens: int = Field(..., description="Tokens used")
    cost: float = Field(..., description="Cost for the day")
    errors: int = Field(..., description="Number of errors")


class UsageQueryRequest(BaseModel):
    """Request schema for querying usage"""
    
    start_date: Optional[datetime] = Field(None, description="Start date for filtering")
    end_date: Optional[datetime] = Field(None, description="End date for filtering")
    skip: int = Field(0, ge=0, description="Number of items to skip")
    limit: int = Field(100, ge=1, le=1000, description="Maximum items to return")