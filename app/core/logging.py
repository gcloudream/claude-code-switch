"""Structured logging configuration using structlog"""

import sys
import logging
from pathlib import Path
from typing import Any, Dict, Optional
import structlog
from structlog.processors import (
    CallsiteParameter,
    CallsiteParameterAdder,
    JSONRenderer,
    TimeStamper,
    add_log_level,
    dict_tracebacks,
    format_exc_info,
)
from structlog.stdlib import (
    BoundLogger,
    LoggerFactory,
    add_logger_name,
    filter_by_level,
    render_to_log_kwargs,
)
from app.core.config import settings


def setup_logging() -> None:
    """Configure structured logging for the application"""
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure Python's logging
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    
    # Configure structlog processors
    shared_processors = [
        # Add timestamp
        TimeStamper(fmt="iso"),
        # Add log level
        add_log_level,
        # Add logger name
        add_logger_name,
        # Add call site parameters
        CallsiteParameterAdder(
            parameters=[
                CallsiteParameter.FILENAME,
                CallsiteParameter.FUNC_NAME,
                CallsiteParameter.LINENO,
            ]
        ),
        # Format exceptions
        dict_tracebacks,
        format_exc_info,
    ]
    
    # Different processors for development vs production
    if settings.is_development:
        # Pretty console output for development
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        # JSON output for production
        renderer = JSONRenderer()
    
    # Configure structlog
    structlog.configure(
        processors=shared_processors + [
            # Filter by log level
            filter_by_level,
            # Prepare for standard library logging
            render_to_log_kwargs,
            # Final rendering
            renderer,
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: Optional[str] = None, **kwargs) -> BoundLogger:
    """Get a structured logger instance
    
    Args:
        name: Logger name (defaults to module name)
        **kwargs: Additional context to bind to the logger
        
    Returns:
        Configured logger instance
    """
    logger = structlog.get_logger(name)
    
    # Add application context
    logger = logger.bind(
        app_name=settings.app_name,
        environment=settings.app_env,
    )
    
    # Add any additional context
    if kwargs:
        logger = logger.bind(**kwargs)
    
    return logger


class LoggerMixin:
    """Mixin class to add logging capabilities to any class"""
    
    @property
    def logger(self) -> BoundLogger:
        """Get a logger instance for this class"""
        if not hasattr(self, "_logger"):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger
    
    def log_info(self, message: str, **kwargs) -> None:
        """Log an info message"""
        self.logger.info(message, **kwargs)
    
    def log_error(self, message: str, **kwargs) -> None:
        """Log an error message"""
        self.logger.error(message, **kwargs)
    
    def log_warning(self, message: str, **kwargs) -> None:
        """Log a warning message"""
        self.logger.warning(message, **kwargs)
    
    def log_debug(self, message: str, **kwargs) -> None:
        """Log a debug message"""
        self.logger.debug(message, **kwargs)


class RequestLogger:
    """Logger for HTTP requests with correlation IDs"""
    
    def __init__(self):
        self.logger = get_logger("request")
    
    def log_request(
        self,
        method: str,
        path: str,
        client_ip: str,
        request_id: str,
        api_key_id: Optional[str] = None,
        **kwargs
    ) -> BoundLogger:
        """Log an incoming request
        
        Args:
            method: HTTP method
            path: Request path
            client_ip: Client IP address
            request_id: Unique request ID
            api_key_id: API key ID if authenticated
            **kwargs: Additional context
            
        Returns:
            Logger bound with request context
        """
        return self.logger.bind(
            request_id=request_id,
            method=method,
            path=path,
            client_ip=client_ip,
            api_key_id=api_key_id,
            **kwargs
        )
    
    def log_response(
        self,
        logger: BoundLogger,
        status_code: int,
        response_time_ms: float,
        response_size: int = 0,
        **kwargs
    ) -> None:
        """Log a response
        
        Args:
            logger: Logger with request context
            status_code: HTTP status code
            response_time_ms: Response time in milliseconds
            response_size: Response size in bytes
            **kwargs: Additional context
        """
        log_method = logger.info if status_code < 400 else logger.error
        
        log_method(
            "request_completed",
            status_code=status_code,
            response_time_ms=response_time_ms,
            response_size=response_size,
            **kwargs
        )


class ProxyLogger:
    """Logger for proxy operations"""
    
    def __init__(self):
        self.logger = get_logger("proxy")
    
    def log_forward(
        self,
        request_id: str,
        upstream_url: str,
        method: str,
        api_key_id: str,
        **kwargs
    ) -> BoundLogger:
        """Log a forwarded request
        
        Args:
            request_id: Request ID
            upstream_url: Upstream URL
            method: HTTP method
            api_key_id: API key ID
            **kwargs: Additional context
            
        Returns:
            Logger bound with proxy context
        """
        return self.logger.bind(
            request_id=request_id,
            upstream_url=upstream_url,
            method=method,
            api_key_id=api_key_id,
            **kwargs
        )
    
    def log_token_usage(
        self,
        logger: BoundLogger,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        model: str,
        **kwargs
    ) -> None:
        """Log token usage
        
        Args:
            logger: Logger with proxy context
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            total_tokens: Total tokens
            model: Model name
            **kwargs: Additional context
        """
        logger.info(
            "token_usage",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            model=model,
            **kwargs
        )


# Initialize loggers
request_logger = RequestLogger()
proxy_logger = ProxyLogger()