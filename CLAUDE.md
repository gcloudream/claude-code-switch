# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Claude API relay station (Claude Code 中转站) - a proxy service that manages and forwards Claude API requests with features like API key management, usage tracking, and quota controls. The service acts as an intermediary between Claude Code users and the Anthropic API.

## Development Commands

### Environment Setup
```bash
# Copy environment template and configure
cp .env.example .env
# Edit .env file with required variables (UPSTREAM_API_KEY, ADMIN_PASSWORD, SECRET_KEY)

# Generate SECRET_KEY
openssl rand -hex 32

# Create database in external PostgreSQL container
docker exec -it <postgres-container> psql -U postgres -c "CREATE DATABASE relay_station;"
```

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start development server
python run.py
```

### Docker Deployment
```bash
# Deploy with automated setup script
chmod +x deploy.sh
./deploy.sh

# Manual Docker commands
docker-compose up -d
docker-compose exec relay-station alembic upgrade head
```

### Database Operations
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Testing & Quality
```bash
# Run tests
pytest tests/

# Code formatting
black app/

# Linting
flake8 app/

# Type checking
mypy app/
```

## Architecture Overview

This is a FastAPI-based relay service with the following key components:

### Core Request Flow
1. **Authentication**: API keys are validated via `app/api/deps.py`
2. **Proxy Service**: Requests are forwarded through `app/services/proxy_service.py`
3. **Token Counting**: Usage tracked with tiktoken in `app/services/token_counter.py`
4. **Usage Logging**: All requests logged via `app/services/usage_log_service.py`

### Key Services Architecture
- **API Layer** (`app/api/`): Handles admin management, user usage queries, and proxying
- **Core Layer** (`app/core/`): Configuration, security (JWT), logging, and metrics
- **Service Layer** (`app/services/`): Business logic for API keys, usage tracking, and proxying
- **Data Layer** (`app/models/`): SQLAlchemy models for API keys and usage logs

### Configuration System
- Environment variables via Pydantic settings (`app/core/config.py`)
- YAML configuration for complex settings (`config.yaml`)
- Settings support multiple upstream APIs and rate limiting tiers

### Database Design
- **api_keys**: Stores proxy API keys with quotas and rate limits
- **usage_logs**: Detailed request/response logging with token counting

## Key Implementation Details

### Proxy Service (`app/services/proxy_service.py`)
- Replaces user's proxy key with real Anthropic API key
- Implements retry logic with exponential backoff
- Extracts token usage from Anthropic API responses
- Falls back to tiktoken estimation when usage data unavailable

### Token Management
- Uses tiktoken library for accurate token counting
- Tracks prompt_tokens, completion_tokens, and total_tokens
- Enforces per-key quotas and rate limits

### Security
- API keys are hashed using bcrypt before database storage
- JWT tokens for admin authentication
- Request/response filtering to prevent data leakage

### Monitoring
- Prometheus metrics exported at `/metrics`
- Structured logging with request IDs for tracing
- Health check endpoint at `/health`

## Important Configuration

### Required Environment Variables
- `UPSTREAM_API_KEY`: Your real Anthropic API key (critical)
- `ADMIN_PASSWORD`: Admin access password
- `SECRET_KEY`: JWT signing key (generate with openssl rand -hex 32)
- `DATABASE_URL`: PostgreSQL connection string for external database
- `REDIS_URL`: Redis connection string for external cache

### External Database Configuration
This project is configured to use external Docker containers:
- **PostgreSQL**: localhost:15432, user: postgres, password: postgres
- **Redis**: localhost:16379, password: 123456

The docker-compose.yml uses `host.docker.internal` to connect to these external services.

### Admin Operations
Create API keys for users via admin endpoints:
```bash
# Login to get admin token
curl -X POST http://localhost:8000/admin/login -u admin:password

# Create user API key
curl -X POST http://localhost:8000/admin/api-keys \
  -H "Authorization: Bearer <token>" \
  -d '{"name": "User", "token_limit": 1000000}'
```

### User Configuration
Users configure Claude Code to use the relay:
```bash
export ANTHROPIC_API_KEY="sk-proxy-xxx"  # Relay-generated key
export ANTHROPIC_BASE_URL="http://relay-station:8000"  # Relay URL
```

## Development Notes

- The proxy service maintains compatibility with Anthropic's API format
- Rate limiting is implemented per-key with configurable tiers
- All database operations use async SQLAlchemy
- Error handling includes proper HTTP status codes and detailed logging
- The service supports both development and production configurations