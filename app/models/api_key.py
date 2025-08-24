"""API Key model for managing relay station keys"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column, String, BigInteger, Boolean, DateTime, 
    Integer, Text, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from app.db.base import Base


class APIKey(Base):
    """API Key model for user authentication and quota management"""
    
    __tablename__ = "api_keys"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Key information (store hash, not plain text)
    api_key_hash = Column(String(64), unique=True, nullable=False, index=True)
    key_prefix = Column(String(20), nullable=False)  # First few chars for identification
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Token limits and usage
    token_limit = Column(BigInteger, nullable=False, default=1000000)  # 1M tokens
    token_used = Column(BigInteger, nullable=False, default=0)
    
    # Rate limiting tier
    rate_limit_tier = Column(String(50), nullable=False, default="basic")
    
    # Status flags
    is_active = Column(Boolean, nullable=False, default=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    
    # Timestamps (timezone-aware)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)  # Soft delete timestamp
    
    # Statistics
    request_count = Column(BigInteger, nullable=False, default=0)
    error_count = Column(BigInteger, nullable=False, default=0)
    
    # Metadata and security
    metadata_json = Column(Text, nullable=True)  # JSON string for additional metadata
    allowed_ips = Column(ARRAY(String), nullable=True)  # IP whitelist
    allowed_origins = Column(ARRAY(String), nullable=True)  # Origin whitelist
    
    # Relationships
    usage_logs = relationship("UsageLog", back_populates="api_key", cascade="all, delete-orphan")
    
    # Indexes and constraints
    __table_args__ = (
        Index("idx_api_key_hash_active", "api_key_hash", "is_active"),
        Index("idx_key_prefix", "key_prefix"),
        Index("idx_created_at", "created_at"),
        Index("idx_token_usage", "token_used", "token_limit"),
        Index("idx_active_not_deleted", "is_active", "is_deleted"),
        CheckConstraint("token_used >= 0", name="check_token_used_positive"),
        CheckConstraint("token_limit > 0", name="check_token_limit_positive"),
        CheckConstraint("request_count >= 0", name="check_request_count_positive"),
        CheckConstraint("error_count >= 0", name="check_error_count_positive"),
    )
    
    @property
    def token_remaining(self) -> int:
        """Calculate remaining tokens"""
        return max(0, self.token_limit - self.token_used)
    
    @property
    def usage_percentage(self) -> float:
        """Calculate usage percentage"""
        if self.token_limit == 0:
            return 0.0
        return (self.token_used / self.token_limit) * 100
    
    @property
    def is_expired(self) -> bool:
        """Check if key is expired"""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    @property
    def is_quota_exceeded(self) -> bool:
        """Check if quota is exceeded"""
        return self.token_used >= self.token_limit
    
    def can_use(self) -> tuple[bool, Optional[str]]:
        """Check if API key can be used
        
        Returns:
            Tuple of (can_use, error_message)
        """
        if not self.is_active:
            return False, "API key is disabled"
        if self.is_deleted:
            return False, "API key has been deleted"
        if self.is_expired:
            return False, "API key has expired"
        if self.is_quota_exceeded:
            return False, "Token quota exceeded"
        return True, None
    
    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, name={self.name}, usage={self.usage_percentage:.1f}%)>"