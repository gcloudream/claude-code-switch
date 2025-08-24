"""Configuration management module"""

import os
from typing import Optional, Any
from functools import lru_cache
from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Application
    app_name: str = Field(default="claude-relay-station")
    app_env: str = Field(default="development")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    
    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    
    # Database
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/relay_station"
    )
    database_pool_size: int = Field(default=20)
    database_max_overflow: int = Field(default=10)
    database_echo: bool = Field(default=False)
    
    # Redis
    redis_url: RedisDsn = Field(default="redis://localhost:6379/0")
    redis_pool_size: int = Field(default=10)
    redis_ttl: int = Field(default=3600)  # 1 hour
    
    # Upstream API (Third-party API)
    upstream_api_url: str = Field(default="https://api.anthropic.com/v1")
    upstream_api_key: str = Field(default="")
    upstream_timeout: int = Field(default=60)  # seconds
    upstream_max_retries: int = Field(default=3)
    
    # Admin Configuration
    admin_username: str = Field(default="admin")
    admin_password: str = Field(default="")
    
    # Security
    secret_key: str = Field(default="")
    token_expire_minutes: int = Field(default=30)
    api_key_prefix: str = Field(default="sk-proxy-")
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=100)
    rate_limit_period: int = Field(default=60)  # seconds
    
    # Token Management
    default_token_limit: int = Field(default=1000000)  # 1M tokens
    token_warning_threshold: float = Field(default=0.8)  # 80%
    
    # Monitoring
    enable_metrics: bool = Field(default=True)
    metrics_port: int = Field(default=9090)
    
    # CORS
    cors_origins: list[str] = Field(default=["*"])
    cors_credentials: bool = Field(default=True)
    cors_methods: list[str] = Field(default=["*"])
    cors_headers: list[str] = Field(default=["*"])
    
    @field_validator("app_env")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate application environment"""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"app_env must be one of {allowed}")
        return v
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level"""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return v
    
    @field_validator("secret_key", "admin_password", "upstream_api_key")
    @classmethod
    def validate_required_in_production(cls, v: str, info) -> str:
        """Validate required fields in production"""
        if info.data.get("app_env") == "production" and not v:
            raise ValueError(f"{info.field_name} is required in production")
        return v
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.app_env == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.app_env == "development"
    
    def get_database_url(self) -> str:
        """Get database URL as string"""
        return str(self.database_url)
    
    def get_redis_url(self) -> str:
        """Get Redis URL as string"""
        return str(self.redis_url)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Create global settings instance
settings = get_settings()