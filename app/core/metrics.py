"""Prometheus metrics for monitoring"""

from prometheus_client import Counter, Histogram, Gauge, Info
from app.core.config import settings


# Application info
app_info = Info(
    "relay_station_info",
    "Application information"
)
app_info.info({
    "version": "0.1.0",
    "environment": settings.app_env,
})

# Request metrics
request_count = Counter(
    "relay_requests_total",
    "Total number of requests",
    ["method", "endpoint", "status"],
)

request_duration = Histogram(
    "relay_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint"],
)

# Proxy metrics
proxy_requests = Counter(
    "proxy_requests_total",
    "Total number of proxied requests",
    ["method", "status", "api_key_id"],
)

proxy_duration = Histogram(
    "proxy_duration_seconds",
    "Proxy request duration in seconds",
    ["method"],
)

upstream_errors = Counter(
    "upstream_errors_total",
    "Total number of upstream errors",
    ["error_type"],
)

# Token metrics
tokens_used = Counter(
    "tokens_used_total",
    "Total tokens used",
    ["api_key_id", "model"],
)

token_quota_usage = Gauge(
    "token_quota_usage_ratio",
    "Token quota usage ratio (0-1)",
    ["api_key_id"],
)

# API key metrics
active_api_keys = Gauge(
    "active_api_keys",
    "Number of active API keys",
)

api_key_requests = Counter(
    "api_key_requests_total",
    "Requests per API key",
    ["api_key_id", "status"],
)

# Database metrics
db_connections = Gauge(
    "db_connections_active",
    "Active database connections",
)

db_query_duration = Histogram(
    "db_query_duration_seconds",
    "Database query duration",
    ["operation"],
)

# Rate limiting metrics
rate_limit_exceeded = Counter(
    "rate_limit_exceeded_total",
    "Number of rate limit exceeded events",
    ["api_key_id"],
)

# Error metrics
error_count = Counter(
    "errors_total",
    "Total number of errors",
    ["error_type", "api_key_id"],
)