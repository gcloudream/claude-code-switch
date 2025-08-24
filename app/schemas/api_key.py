"""API key schemas for request/response validation"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class APIKeyCreateRequest(BaseModel):
    """Request schema for creating an API key"""
    
    name: str = Field(..., min_length=1, max_length=255, description="Name for the API key")
    description: Optional[str] = Field(None, max_length=1000, description="Description of the API key")
    token_limit: int = Field(1000000, gt=0, description="Token limit for the key")
    rate_limit_tier: str = Field("basic", description="Rate limiting tier")
    expires_in_days: Optional[int] = Field(None, gt=0, le=365, description="Expiration in days")
    allowed_ips: Optional[List[str]] = Field(None, description="List of allowed IP addresses")
    allowed_origins: Optional[List[str]] = Field(None, description="List of allowed origins")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    @field_validator("rate_limit_tier")
    @classmethod
    def validate_rate_limit_tier(cls, v: str) -> str:
        """Validate rate limit tier"""
        allowed_tiers = ["basic", "premium", "unlimited"]
        if v not in allowed_tiers:
            raise ValueError(f"Rate limit tier must be one of {allowed_tiers}")
        return v


class APIKeyCreateResponse(BaseModel):
    """Response schema for API key creation"""
    
    id: UUID = Field(..., description="API key ID")
    api_key: str = Field(..., description="The API key (only shown once)")
    name: str = Field(..., description="Name of the API key")
    description: Optional[str] = Field(None, description="Description")
    token_limit: int = Field(..., description="Token limit")
    rate_limit_tier: str = Field(..., description="Rate limiting tier")
    expires_at: Optional[datetime] = Field(None, description="Expiration time")
    created_at: datetime = Field(..., description="Creation time")


class APIKeyResponse(BaseModel):
    """Response schema for API key information (without the actual key)"""
    
    id: UUID = Field(..., description="API key ID")
    name: str = Field(..., description="Name of the API key")
    description: Optional[str] = Field(None, description="Description")
    key_prefix: str = Field(..., description="Key prefix for identification")
    token_limit: int = Field(..., description="Token limit")
    token_used: int = Field(..., description="Tokens used")
    token_remaining: int = Field(..., description="Tokens remaining")
    usage_percentage: float = Field(..., description="Usage percentage")
    rate_limit_tier: str = Field(..., description="Rate limiting tier")
    request_count: int = Field(..., description="Total request count")
    error_count: int = Field(..., description="Total error count")
    is_active: bool = Field(..., description="Whether the key is active")
    created_at: datetime = Field(..., description="Creation time")
    updated_at: datetime = Field(..., description="Last update time")
    last_used_at: Optional[datetime] = Field(None, description="Last usage time")
    expires_at: Optional[datetime] = Field(None, description="Expiration time")
    
    class Config:
        from_attributes = True


class APIKeyListResponse(BaseModel):
    """Response schema for listing API keys"""
    
    items: List[APIKeyResponse] = Field(..., description="List of API keys")
    total: int = Field(..., description="Total number of items")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Maximum items returned")


class APIKeyUpdateRequest(BaseModel):
    """Request schema for updating an API key"""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="New name")
    description: Optional[str] = Field(None, max_length=1000, description="New description")
    token_limit: Optional[int] = Field(None, gt=0, description="New token limit")
    rate_limit_tier: Optional[str] = Field(None, description="New rate limiting tier")
    allowed_ips: Optional[List[str]] = Field(None, description="New list of allowed IPs")
    allowed_origins: Optional[List[str]] = Field(None, description="New list of allowed origins")
    
    @field_validator("rate_limit_tier")
    @classmethod
    def validate_rate_limit_tier(cls, v: Optional[str]) -> Optional[str]:
        """Validate rate limit tier if provided"""
        if v is not None:
            allowed_tiers = ["basic", "premium", "unlimited"]
            if v not in allowed_tiers:
                raise ValueError(f"Rate limit tier must be one of {allowed_tiers}")
        return v


class APIKeyStatsResponse(BaseModel):
    """Response schema for API key statistics"""
    
    id: UUID = Field(..., description="API key ID")
    name: str = Field(..., description="Name of the API key")
    created_at: datetime = Field(..., description="Creation time")
    last_used_at: Optional[datetime] = Field(None, description="Last usage time")
    token_limit: int = Field(..., description="Token limit")
    token_used: int = Field(..., description="Tokens used")
    token_remaining: int = Field(..., description="Tokens remaining")
    usage_percentage: float = Field(..., description="Usage percentage")
    request_count: int = Field(..., description="Total request count")
    error_count: int = Field(..., description="Total error count")
    is_active: bool = Field(..., description="Whether the key is active")
    is_expired: bool = Field(..., description="Whether the key is expired")
    expires_at: Optional[datetime] = Field(None, description="Expiration time")