"""Metrics collection middleware"""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.metrics import request_count, request_duration
from app.core.logging import get_logger


logger = get_logger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting request metrics"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics
        
        Args:
            request: FastAPI request
            call_next: Next middleware or endpoint
            
        Returns:
            Response from endpoint
        """
        # Skip metrics for metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)
        
        # Start timing
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Extract endpoint (first two parts of path)
        path_parts = request.url.path.strip("/").split("/")
        if len(path_parts) > 2:
            endpoint = f"/{path_parts[0]}/{path_parts[1]}/..."
        else:
            endpoint = request.url.path
        
        # Record metrics
        request_count.labels(
            method=request.method,
            endpoint=endpoint,
            status=response.status_code,
        ).inc()
        
        request_duration.labels(
            method=request.method,
            endpoint=endpoint,
        ).observe(duration)
        
        # Add response headers
        response.headers["X-Response-Time"] = f"{duration:.3f}"
        
        return response