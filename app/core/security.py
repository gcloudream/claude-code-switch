"""Security utilities for API key management and authentication"""

import hashlib
import secrets
import string
from typing import Tuple, Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from app.core.config import settings


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_api_key(prefix: str = None) -> str:
    """Generate a secure API key
    
    Args:
        prefix: Optional prefix for the key
        
    Returns:
        Generated API key in format: sk-proxy-{random_string}
    """
    if prefix is None:
        prefix = settings.api_key_prefix
    
    # Generate 32 bytes of random data
    random_bytes = secrets.token_bytes(32)
    # Convert to URL-safe string
    random_string = secrets.token_urlsafe(32)
    
    return f"{prefix}{random_string}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA256
    
    Args:
        api_key: Plain text API key
        
    Returns:
        Hashed API key
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def get_key_prefix(api_key: str, length: int = 12) -> str:
    """Extract prefix from API key for identification
    
    Args:
        api_key: Full API key
        length: Length of prefix to extract
        
    Returns:
        Key prefix
    """
    return api_key[:min(length, len(api_key))]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token
    
    Args:
        data: Data to encode in the token
        expires_delta: Optional expiration time delta
        
    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    return encoded_jwt


def verify_access_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT access token
    
    Args:
        token: JWT token to verify
        
    Returns:
        Decoded token data if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return payload
    except JWTError:
        return None


def verify_admin_credentials(username: str, password: str) -> bool:
    """Verify admin credentials against configuration
    
    Args:
        username: Admin username
        password: Admin password
        
    Returns:
        True if credentials are valid, False otherwise
    """
    # Get admin credentials from configuration
    correct_username = settings.admin_username
    
    # Use timing-safe comparison to prevent timing attacks
    import secrets
    username_matches = secrets.compare_digest(username, correct_username)
    
    # Check if admin password is already hashed (production) or plain text (development)
    if settings.admin_password.startswith('$2b$'):
        # Password is already hashed (bcrypt format)
        password_matches = verify_password(password, settings.admin_password)
    else:
        # Plain text password (development only - should be hashed in production)
        password_matches = secrets.compare_digest(password, settings.admin_password)
    
    return username_matches and password_matches


def check_ip_allowed(api_key_ips: Optional[list], client_ip: str) -> bool:
    """Check if client IP is allowed for the API key
    
    Args:
        api_key_ips: List of allowed IPs for the API key (None means all allowed)
        client_ip: Client's IP address
        
    Returns:
        True if IP is allowed, False otherwise
    """
    if api_key_ips is None or len(api_key_ips) == 0:
        return True  # No IP restrictions
    
    return client_ip in api_key_ips


def check_origin_allowed(api_key_origins: Optional[list], origin: str) -> bool:
    """Check if origin is allowed for the API key
    
    Args:
        api_key_origins: List of allowed origins for the API key (None means all allowed)
        origin: Request origin
        
    Returns:
        True if origin is allowed, False otherwise
    """
    if api_key_origins is None or len(api_key_origins) == 0:
        return True  # No origin restrictions
    
    return origin in api_key_origins