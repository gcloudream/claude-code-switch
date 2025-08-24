"""Service for managing API keys"""

import json
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
from uuid import UUID
from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.api_key import APIKey
from app.core.security import generate_api_key, hash_api_key, get_key_prefix
from app.core.logging import get_logger


logger = get_logger(__name__)


class APIKeyService:
    """Service for managing API keys"""
    
    def __init__(self, db: AsyncSession):
        """Initialize the service
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def create_api_key(
        self,
        name: str,
        description: Optional[str] = None,
        token_limit: int = 1000000,
        rate_limit_tier: str = "basic",
        expires_in_days: Optional[int] = None,
        allowed_ips: Optional[List[str]] = None,
        allowed_origins: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[APIKey, str]:
        """Create a new API key
        
        Args:
            name: Name for the API key
            description: Optional description
            token_limit: Token limit for the key
            rate_limit_tier: Rate limiting tier
            expires_in_days: Optional expiration in days
            allowed_ips: Optional list of allowed IPs
            allowed_origins: Optional list of allowed origins
            metadata: Optional metadata dictionary
            
        Returns:
            Tuple of (APIKey model, plain text API key)
        """
        # Generate the API key
        plain_api_key = generate_api_key()
        api_key_hash = hash_api_key(plain_api_key)
        key_prefix = get_key_prefix(plain_api_key)
        
        # Calculate expiration if specified
        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        
        # Create the API key model
        api_key = APIKey(
            api_key_hash=api_key_hash,
            key_prefix=key_prefix,
            name=name,
            description=description,
            token_limit=token_limit,
            rate_limit_tier=rate_limit_tier,
            expires_at=expires_at,
            allowed_ips=allowed_ips,
            allowed_origins=allowed_origins,
            metadata_json=json.dumps(metadata) if metadata else None,
        )
        
        self.db.add(api_key)
        await self.db.commit()
        await self.db.refresh(api_key)
        
        logger.info(
            "api_key_created",
            api_key_id=str(api_key.id),
            name=name,
            token_limit=token_limit,
            rate_limit_tier=rate_limit_tier,
        )
        
        # Return both the model and the plain text key
        # The plain text key is only available at creation time
        return api_key, plain_api_key
    
    async def get_api_key_by_hash(self, api_key_hash: str) -> Optional[APIKey]:
        """Get an API key by its hash
        
        Args:
            api_key_hash: Hashed API key
            
        Returns:
            APIKey if found, None otherwise
        """
        result = await self.db.execute(
            select(APIKey).where(
                and_(
                    APIKey.api_key_hash == api_key_hash,
                    APIKey.is_deleted == False,
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_api_key_by_id(self, api_key_id: UUID) -> Optional[APIKey]:
        """Get an API key by its ID
        
        Args:
            api_key_id: API key UUID
            
        Returns:
            APIKey if found, None otherwise
        """
        result = await self.db.execute(
            select(APIKey).where(
                and_(
                    APIKey.id == api_key_id,
                    APIKey.is_deleted == False,
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def validate_api_key(
        self,
        plain_api_key: str,
        client_ip: Optional[str] = None,
        origin: Optional[str] = None,
    ) -> Tuple[bool, Optional[APIKey], Optional[str]]:
        """Validate an API key
        
        Args:
            plain_api_key: Plain text API key
            client_ip: Optional client IP for validation
            origin: Optional origin for validation
            
        Returns:
            Tuple of (is_valid, api_key, error_message)
        """
        # Hash the key for lookup
        api_key_hash = hash_api_key(plain_api_key)
        
        # Look up the key
        api_key = await self.get_api_key_by_hash(api_key_hash)
        
        if not api_key:
            return False, None, "Invalid API key"
        
        # Check if the key can be used
        can_use, error_msg = api_key.can_use()
        if not can_use:
            return False, api_key, error_msg
        
        # Check IP restrictions
        if client_ip and api_key.allowed_ips:
            if client_ip not in api_key.allowed_ips:
                return False, api_key, "IP address not allowed"
        
        # Check origin restrictions
        if origin and api_key.allowed_origins:
            if origin not in api_key.allowed_origins:
                return False, api_key, "Origin not allowed"
        
        # Note: last_used_at update should be handled separately to avoid 
        # transaction coupling with validation logic
        return True, api_key, None
    
    async def update_last_used(self, api_key_id: UUID) -> bool:
        """Update last used timestamp for an API key
        
        Args:
            api_key_id: API key ID
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            stmt = (
                update(APIKey)
                .where(APIKey.id == api_key_id)
                .values(last_used_at=datetime.now(timezone.utc))
            )
            await self.db.execute(stmt)
            await self.db.commit()
            return True
        except Exception:
            await self.db.rollback()
            return False
    
    async def update_token_usage(
        self,
        api_key_id: UUID,
        tokens_used: int,
        increment_request_count: bool = True,
    ) -> bool:
        """Update token usage for an API key
        
        Args:
            api_key_id: API key ID
            tokens_used: Number of tokens used
            increment_request_count: Whether to increment request count
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            # Build the update statement
            stmt = (
                update(APIKey)
                .where(APIKey.id == api_key_id)
                .values(
                    token_used=APIKey.token_used + tokens_used,
                    request_count=APIKey.request_count + (1 if increment_request_count else 0),
                    last_used_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            )
            
            await self.db.execute(stmt)
            await self.db.commit()
            
            logger.info(
                "token_usage_updated",
                api_key_id=str(api_key_id),
                tokens_used=tokens_used,
            )
            
            return True
        except Exception as e:
            logger.error(
                "token_usage_update_failed",
                api_key_id=str(api_key_id),
                error=str(e),
            )
            await self.db.rollback()
            return False
    
    async def increment_error_count(self, api_key_id: UUID) -> bool:
        """Increment error count for an API key
        
        Args:
            api_key_id: API key ID
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            stmt = (
                update(APIKey)
                .where(APIKey.id == api_key_id)
                .values(
                    error_count=APIKey.error_count + 1,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            
            await self.db.execute(stmt)
            await self.db.commit()
            return True
        except Exception:
            await self.db.rollback()
            return False
    
    async def list_api_keys(
        self,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
    ) -> List[APIKey]:
        """List all API keys
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_deleted: Whether to include deleted keys
            
        Returns:
            List of API keys
        """
        query = select(APIKey)
        
        if not include_deleted:
            query = query.where(APIKey.is_deleted == False)
        
        query = query.order_by(APIKey.created_at.desc()).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def disable_api_key(self, api_key_id: UUID) -> bool:
        """Disable an API key
        
        Args:
            api_key_id: API key ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            stmt = (
                update(APIKey)
                .where(APIKey.id == api_key_id)
                .values(
                    is_active=False,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            
            await self.db.execute(stmt)
            await self.db.commit()
            
            logger.info("api_key_disabled", api_key_id=str(api_key_id))
            return True
        except Exception as e:
            logger.error("api_key_disable_failed", api_key_id=str(api_key_id), error=str(e))
            await self.db.rollback()
            return False
    
    async def enable_api_key(self, api_key_id: UUID) -> bool:
        """Enable an API key
        
        Args:
            api_key_id: API key ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            stmt = (
                update(APIKey)
                .where(APIKey.id == api_key_id)
                .values(
                    is_active=True,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            
            await self.db.execute(stmt)
            await self.db.commit()
            
            logger.info("api_key_enabled", api_key_id=str(api_key_id))
            return True
        except Exception as e:
            logger.error("api_key_enable_failed", api_key_id=str(api_key_id), error=str(e))
            await self.db.rollback()
            return False
    
    async def delete_api_key(self, api_key_id: UUID, hard_delete: bool = False) -> bool:
        """Delete an API key
        
        Args:
            api_key_id: API key ID
            hard_delete: If True, permanently delete from database
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if hard_delete:
                # Permanently delete the key
                api_key = await self.get_api_key_by_id(api_key_id)
                if api_key:
                    await self.db.delete(api_key)
                    await self.db.commit()
                    logger.info("api_key_hard_deleted", api_key_id=str(api_key_id))
            else:
                # Soft delete (mark as deleted)
                stmt = (
                    update(APIKey)
                    .where(APIKey.id == api_key_id)
                    .values(
                        is_deleted=True,
                        is_active=False,
                        deleted_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                )
                
                await self.db.execute(stmt)
                await self.db.commit()
                logger.info("api_key_soft_deleted", api_key_id=str(api_key_id))
            
            return True
        except Exception as e:
            logger.error("api_key_delete_failed", api_key_id=str(api_key_id), error=str(e))
            await self.db.rollback()
            return False
    
    async def get_api_key_statistics(self, api_key_id: UUID) -> Optional[Dict[str, Any]]:
        """Get statistics for an API key
        
        Args:
            api_key_id: API key ID
            
        Returns:
            Dictionary with statistics or None if not found
        """
        api_key = await self.get_api_key_by_id(api_key_id)
        
        if not api_key:
            return None
        
        return {
            "id": str(api_key.id),
            "name": api_key.name,
            "created_at": api_key.created_at.isoformat(),
            "last_used_at": api_key.last_used_at.isoformat() if api_key.last_used_at else None,
            "token_limit": api_key.token_limit,
            "token_used": api_key.token_used,
            "token_remaining": api_key.token_remaining,
            "usage_percentage": api_key.usage_percentage,
            "request_count": api_key.request_count,
            "error_count": api_key.error_count,
            "is_active": api_key.is_active,
            "is_expired": api_key.is_expired,
            "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
        }