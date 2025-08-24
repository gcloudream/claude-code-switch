"""Core proxy service for forwarding requests to upstream API"""

import json
import time
from typing import Dict, Any, Optional, Tuple
from uuid import uuid4
import httpx
from fastapi import Request, Response, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.yaml_config import yaml_config
from app.core.logging import proxy_logger
from app.models.api_key import APIKey
from app.services.api_key_service import APIKeyService
from app.services.usage_log_service import UsageLogService
from app.services.token_counter import TokenCounter


class ProxyService:
    """Service for proxying requests to upstream API"""
    
    def __init__(self, db: AsyncSession):
        """Initialize proxy service
        
        Args:
            db: Database session
        """
        self.db = db
        self.api_key_service = APIKeyService(db)
        self.usage_log_service = UsageLogService(db)
        self.token_counter = TokenCounter()
        
        # Get upstream configuration
        upstream_config = yaml_config.get_upstream_config()
        self.upstream_url = upstream_config.get("url", settings.upstream_api_url)
        self.upstream_api_key = upstream_config.get("api_key", settings.upstream_api_key)
        self.upstream_timeout = upstream_config.get("timeout", settings.upstream_timeout)
        self.upstream_max_retries = upstream_config.get("max_retries", settings.upstream_max_retries)
        
        # Create HTTP client with retry configuration
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.upstream_timeout),
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
        )
    
    async def forward_request(
        self,
        api_key: APIKey,
        request: Request,
        path: str,
    ) -> Response:
        """Forward request to upstream API
        
        Args:
            api_key: Validated API key object
            request: FastAPI request object
            path: Request path to forward
            
        Returns:
            FastAPI response object
            
        Raises:
            HTTPException: If forwarding fails
        """
        # Generate request ID
        request_id = str(uuid4())
        
        # Start timing
        start_time = time.time()
        
        # Create logger with context
        logger = proxy_logger.log_forward(
            request_id=request_id,
            upstream_url=self.upstream_url,
            method=request.method,
            api_key_id=str(api_key.id),
        )
        
        try:
            # Check token quota before forwarding
            if api_key.is_quota_exceeded:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Token quota exceeded",
                )
            
            # Build upstream URL
            target_url = f"{self.upstream_url}{path}"
            if request.url.query:
                target_url = f"{target_url}?{request.url.query}"
            
            # Get request body
            request_body = await request.body()
            request_size = len(request_body) if request_body else 0
            
            # Build headers for upstream request
            forward_headers = await self._build_forward_headers(request)
            
            # Forward the request with retries
            response = await self._forward_with_retry(
                method=request.method,
                url=target_url,
                headers=forward_headers,
                content=request_body,
                logger=logger,
            )
            
            # Get response content
            response_content = response.content
            response_size = len(response_content) if response_content else 0
            
            # Calculate response time
            response_time_ms = (time.time() - start_time) * 1000
            
            # Extract token usage from response
            token_usage = await self._extract_token_usage(response, request_body, response_content)
            
            # Log token usage
            if token_usage["total_tokens"] > 0:
                proxy_logger.log_token_usage(
                    logger=logger,
                    prompt_tokens=token_usage["prompt_tokens"],
                    completion_tokens=token_usage["completion_tokens"],
                    total_tokens=token_usage["total_tokens"],
                    model=token_usage.get("model", "unknown"),
                )
                
                # Update API key token usage
                await self.api_key_service.update_token_usage(
                    api_key_id=api_key.id,
                    tokens_used=token_usage["total_tokens"],
                )
            
            # Create usage log
            await self.usage_log_service.create_usage_log(
                api_key_id=api_key.id,
                request_id=request_id,
                request_method=request.method,
                request_path=path,
                request_size=request_size,
                response_status=response.status_code,
                response_size=response_size,
                response_time_ms=response_time_ms,
                prompt_tokens=token_usage["prompt_tokens"],
                completion_tokens=token_usage["completion_tokens"],
                total_tokens=token_usage["total_tokens"],
                model=token_usage.get("model"),
                is_error=response.status_code >= 400,
                client_ip=request.client.host,
                user_agent=request.headers.get("User-Agent"),
            )
            
            # Build response to client
            return Response(
                content=response_content,
                status_code=response.status_code,
                headers=self._filter_response_headers(response.headers),
            )
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except httpx.TimeoutException as e:
            logger.error("upstream_timeout", error=str(e))
            
            # Log error
            await self._log_error(
                api_key_id=api_key.id,
                request_id=request_id,
                request_method=request.method,
                request_path=path,
                request_size=request_size if 'request_size' in locals() else 0,
                error_message="Upstream API timeout",
                error_code="TIMEOUT",
                response_time_ms=(time.time() - start_time) * 1000,
                client_ip=request.client.host,
                user_agent=request.headers.get("User-Agent"),
            )
            
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Upstream API timeout",
            )
        except Exception as e:
            logger.error("proxy_error", error=str(e))
            
            # Log error
            await self._log_error(
                api_key_id=api_key.id,
                request_id=request_id,
                request_method=request.method,
                request_path=path,
                request_size=request_size if 'request_size' in locals() else 0,
                error_message=str(e),
                error_code="PROXY_ERROR",
                response_time_ms=(time.time() - start_time) * 1000,
                client_ip=request.client.host,
                user_agent=request.headers.get("User-Agent"),
            )
            
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Proxy error occurred",
            )
    
    async def _build_forward_headers(self, request: Request) -> Dict[str, str]:
        """Build headers for forwarding to upstream
        
        Args:
            request: Original request
            
        Returns:
            Headers dictionary for upstream request
        """
        # Start with original headers
        headers = dict(request.headers)
        
        # Remove hop-by-hop headers
        hop_by_hop_headers = [
            "connection", "keep-alive", "proxy-authenticate",
            "proxy-authorization", "te", "trailers", "transfer-encoding",
            "upgrade", "host", "authorization", "x-api-key"
        ]
        
        for header in hop_by_hop_headers:
            headers.pop(header, None)
        
        # Add upstream API key (replacing user's relay key with third-party key)
        headers["Authorization"] = f"Bearer {self.upstream_api_key}"
        
        # Add forwarded headers
        if request.client.host:
            headers["X-Forwarded-For"] = request.client.host
            headers["X-Real-IP"] = request.client.host
        
        headers["X-Forwarded-Proto"] = request.url.scheme
        
        return headers
    
    def _filter_response_headers(self, headers: httpx.Headers) -> Dict[str, str]:
        """Filter response headers before sending to client
        
        Args:
            headers: Response headers from upstream
            
        Returns:
            Filtered headers dictionary
        """
        # Headers to exclude from response
        exclude_headers = [
            "connection", "keep-alive", "proxy-authenticate",
            "proxy-authorization", "te", "trailers", "transfer-encoding",
            "upgrade", "content-encoding", "content-length"
        ]
        
        filtered = {}
        for key, value in headers.items():
            if key.lower() not in exclude_headers:
                filtered[key] = value
        
        return filtered
    
    async def _forward_with_retry(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        content: bytes,
        logger,
    ) -> httpx.Response:
        """Forward request with retry logic
        
        Args:
            method: HTTP method
            url: Target URL
            headers: Request headers
            content: Request body
            logger: Logger instance
            
        Returns:
            HTTP response
            
        Raises:
            httpx.HTTPError: If all retries fail
        """
        last_error = None
        
        for attempt in range(self.upstream_max_retries):
            try:
                response = await self.client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    content=content,
                )
                
                # Return successful response or client errors (4xx)
                if response.status_code < 500:
                    return response
                
                # Log server error
                logger.warning(
                    "upstream_server_error",
                    attempt=attempt + 1,
                    status_code=response.status_code,
                )
                
                last_error = f"Upstream returned {response.status_code}"
                
            except httpx.HTTPError as e:
                logger.warning(
                    "upstream_request_failed",
                    attempt=attempt + 1,
                    error=str(e),
                )
                last_error = e
            
            # Wait before retry (exponential backoff)
            if attempt < self.upstream_max_retries - 1:
                await self._wait_before_retry(attempt)
        
        # All retries failed
        if isinstance(last_error, Exception):
            raise last_error
        else:
            raise httpx.HTTPError(last_error)
    
    async def _wait_before_retry(self, attempt: int) -> None:
        """Wait before retry with exponential backoff
        
        Args:
            attempt: Current attempt number (0-based)
        """
        import asyncio
        wait_time = min(2 ** attempt, 30)  # Max 30 seconds
        await asyncio.sleep(wait_time)
    
    async def _extract_token_usage(
        self,
        response: httpx.Response,
        request_body: bytes,
        response_body: bytes,
    ) -> Dict[str, Any]:
        """Extract token usage from response
        
        Args:
            response: HTTP response
            request_body: Request body
            response_body: Response body
            
        Returns:
            Token usage dictionary
        """
        print(f"[DEBUG] _extract_token_usage called, response status: {response.status_code}")
        print(f"[DEBUG] Response content-type: {response.headers.get('content-type', 'None')}")
        print(f"[DEBUG] Response body length: {len(response_body) if response_body else 0}")
        
        usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "model": None,
        }
        
        # Try to parse response as JSON or SSE
        try:
            content_type = response.headers.get("content-type", "")
            
            if content_type.startswith("application/json"):
                # Handle JSON response
                response_json = json.loads(response_body)
                
                # Debug: Print response structure directly 
                print(f"[DEBUG] JSON Response keys: {list(response_json.keys())}")
                print(f"[DEBUG] Has usage: {'usage' in response_json}")
                print(f"[DEBUG] Has content: {'content' in response_json}")
                if 'usage' in response_json:
                    print(f"[DEBUG] Usage data: {response_json['usage']}")
                
                # Debug: Log the response structure
                proxy_logger.logger.info("token_extraction_debug", 
                                        response_keys=list(response_json.keys()),
                                        has_usage=("usage" in response_json),
                                        has_content=("content" in response_json))
                
            elif content_type.startswith("text/event-stream"):
                # Handle SSE (Server-Sent Events) response
                response_text = response_body.decode('utf-8') if response_body else ""
                print(f"[DEBUG] SSE Response length: {len(response_text)}")
                
                # Parse SSE format to extract JSON data
                response_json = self._parse_sse_response(response_text)
                print(f"[DEBUG] Parsed SSE data keys: {list(response_json.keys()) if response_json else 'None'}")
                
            else:
                print(f"[DEBUG] Unsupported content-type: {content_type}")
                response_json = None
            
            # Extract usage from parsed response data
            if response_json and "usage" in response_json:
                usage_data = response_json["usage"]
                usage["prompt_tokens"] = usage_data.get("input_tokens", 0)
                usage["completion_tokens"] = usage_data.get("output_tokens", 0)
                usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]
                proxy_logger.logger.info("token_usage_from_api", 
                                        input_tokens=usage["prompt_tokens"],
                                        output_tokens=usage["completion_tokens"],
                                        total_tokens=usage["total_tokens"])
            
            # Extract model
            if response_json and "model" in response_json:
                usage["model"] = response_json["model"]
            
            # If no usage in response, estimate from content
            if usage["total_tokens"] == 0 and response_json:
                # Parse request to get messages
                try:
                    request_json = json.loads(request_body) if request_body else {}
                    messages = request_json.get("messages", [])
                    prompt_text = " ".join([m.get("content", "") for m in messages])
                    
                    # Get completion text
                    completion_text = ""
                    if "content" in response_json:
                        if isinstance(response_json["content"], list):
                            completion_text = " ".join([
                                c.get("text", "") for c in response_json["content"]
                                if c.get("type") == "text"
                            ])
                        else:
                            completion_text = response_json.get("content", "")
                    
                    # Estimate tokens
                    usage["prompt_tokens"] = self.token_counter.count_tokens(prompt_text)
                    usage["completion_tokens"] = self.token_counter.count_tokens(completion_text)
                    usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]
                    
                    proxy_logger.logger.info("token_usage_estimated", 
                                            prompt_text_len=len(prompt_text),
                                            completion_text_len=len(completion_text),
                                            prompt_tokens=usage["prompt_tokens"],
                                            completion_tokens=usage["completion_tokens"],
                                            total_tokens=usage["total_tokens"])
                    
                except Exception as e:
                    proxy_logger.logger.warning("token_estimation_error", error=str(e))
                        
        except json.JSONDecodeError:
            pass
        except Exception as e:
            proxy_logger.logger.warning("token_extraction_error", error=str(e))
        
        return usage
    
    def _parse_sse_response(self, sse_text: str) -> Dict[str, Any]:
        """Parse Server-Sent Events response to extract usage data
        
        Args:
            sse_text: SSE response text
            
        Returns:
            Parsed response data with usage information
        """
        result = {
            "usage": {"input_tokens": 0, "output_tokens": 0},
            "content": [],
            "model": None
        }
        
        try:
            lines = sse_text.strip().split('\n')
            content_parts = []
            
            for line in lines:
                if line.startswith('data: '):
                    data_str = line[6:]  # Remove 'data: ' prefix
                    if data_str.strip() and data_str != '[DONE]':
                        try:
                            data = json.loads(data_str)
                            
                            # Extract model
                            if "model" in data and not result["model"]:
                                result["model"] = data["model"]
                            
                            # Extract content
                            if "delta" in data and "text" in data["delta"]:
                                content_parts.append(data["delta"]["text"])
                            elif "content" in data and isinstance(data["content"], list):
                                for content_item in data["content"]:
                                    if content_item.get("type") == "text":
                                        content_parts.append(content_item.get("text", ""))
                            
                            # Extract usage information
                            if "usage" in data:
                                usage_data = data["usage"]
                                result["usage"]["input_tokens"] = usage_data.get("input_tokens", 0)
                                result["usage"]["output_tokens"] = usage_data.get("output_tokens", 0)
                        
                        except json.JSONDecodeError:
                            continue
            
            # Set content
            if content_parts:
                result["content"] = [{"type": "text", "text": "".join(content_parts)}]
            
            print(f"[DEBUG] SSE parsing result: input_tokens={result['usage']['input_tokens']}, output_tokens={result['usage']['output_tokens']}")
            
        except Exception as e:
            print(f"[DEBUG] SSE parsing error: {e}")
            
        return result
    
    async def _log_error(
        self,
        api_key_id,
        request_id: str,
        request_method: str,
        request_path: str,
        request_size: int,
        error_message: str,
        error_code: str,
        response_time_ms: float,
        client_ip: str,
        user_agent: str,
    ) -> None:
        """Log error to usage logs
        
        Args:
            Various error details
        """
        try:
            await self.usage_log_service.create_usage_log(
                api_key_id=api_key_id,
                request_id=request_id,
                request_method=request_method,
                request_path=request_path,
                request_size=request_size,
                response_status=500,
                response_size=0,
                response_time_ms=response_time_ms,
                is_error=True,
                error_message=error_message,
                error_code=error_code,
                client_ip=client_ip,
                user_agent=user_agent,
            )
            
            # Increment error count
            await self.api_key_service.increment_error_count(api_key_id)
        except Exception as e:
            proxy_logger.logger.error("error_logging_failed", error=str(e))
    
    async def close(self) -> None:
        """Close HTTP client"""
        await self.client.aclose()