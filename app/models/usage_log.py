"""Usage log model for tracking API usage"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column, String, BigInteger, Boolean, DateTime,
    Integer, Text, ForeignKey, Index, Float, DECIMAL
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class UsageLog(Base):
    """Usage log model for tracking API requests and token consumption"""
    
    __tablename__ = "usage_logs"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to API key
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False)
    
    # Request information
    request_id = Column(String(100), nullable=True, index=True)
    request_method = Column(String(10), nullable=False)
    request_path = Column(String(500), nullable=False)
    request_size = Column(Integer, nullable=False, default=0)
    
    # Response information
    response_status = Column(Integer, nullable=False)
    response_size = Column(Integer, nullable=False, default=0)
    response_time_ms = Column(Float, nullable=False)  # Response time in milliseconds
    
    # Token usage
    prompt_tokens = Column(BigInteger, nullable=False, default=0)
    completion_tokens = Column(BigInteger, nullable=False, default=0)
    total_tokens = Column(BigInteger, nullable=False, default=0)
    
    # Model information
    model = Column(String(100), nullable=True)
    
    # Error tracking
    is_error = Column(Boolean, nullable=False, default=False)
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)
    
    # Client information
    client_ip = Column(String(45), nullable=True)  # Support IPv6
    user_agent = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Metadata
    metadata_json = Column(Text, nullable=True)  # JSON string for additional metadata
    
    # Relationships
    api_key = relationship("APIKey", back_populates="usage_logs")
    
    # Cost tracking
    input_cost = Column(DECIMAL(10, 6), nullable=False, default=0)
    output_cost = Column(DECIMAL(10, 6), nullable=False, default=0)
    total_cost = Column(DECIMAL(10, 6), nullable=False, default=0)
    
    # Indexes
    __table_args__ = (
        Index("idx_api_key_created", "api_key_id", "created_at"),
        Index("idx_created_at", "created_at"),
        Index("idx_request_id", "request_id"),
        Index("idx_is_error", "is_error"),
        Index("idx_model", "model"),
        Index("idx_error_analysis", "api_key_id", "is_error", "created_at"),
        Index("idx_model_usage", "model", "created_at"),
        Index("idx_token_cost", "total_tokens", "created_at"),
    )
    
    @property
    def cost_estimate(self) -> float:
        """Estimate cost based on token usage (placeholder for actual pricing)"""
        # Example pricing: $0.01 per 1K tokens
        return (self.total_tokens / 1000) * 0.01
    
    def __repr__(self) -> str:
        return f"<UsageLog(id={self.id}, tokens={self.total_tokens}, status={self.response_status})>"