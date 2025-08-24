# Claude API Relay Station

A high-performance proxy service for Claude API that provides API key management, usage tracking, quota controls, and request forwarding capabilities.

## Features

### Core Functionality
- 🔑 **API Key Management**: Create and manage proxy API keys with independent billing
- 🔄 **Request Forwarding**: Seamless proxy to Anthropic Claude API with retry logic
- 📊 **Usage Tracking**: Comprehensive token usage monitoring and request logging
- 🎯 **Quota Controls**: Per-key token limits and rate limiting with configurable tiers
- 🔒 **Security**: Hashed API key storage with IP/domain whitelisting support
- 📈 **Monitoring**: Prometheus metrics export for Grafana visualization

### Admin Features
- JWT-based admin authentication
- Create, disable, and delete API keys
- View usage statistics across all keys
- Configure rate limiting tiers

### User Features
- Query personal API key usage statistics
- Get daily usage breakdowns
- Access detailed request logs
- Real-time quota status monitoring

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 6+ (optional)
- Docker & Docker Compose (optional)

### Installation

#### Docker Deployment (Recommended)

1. Clone and configure:
```bash
git clone <repository-url>
cd claude-code-switch
cp .env.example .env
# Edit .env with required environment variables
```

2. Deploy using automated script:
```bash
chmod +x deploy.sh
./deploy.sh
```

3. Or manually with Docker Compose:
```bash
docker-compose up -d
docker-compose exec relay-station alembic upgrade head
```

#### Manual Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env file with your settings
```

3. Run database migrations:
```bash
alembic upgrade head
```

4. Start the server:
```bash
python run.py
```

## Configuration

### Environment Variables

Configure the following key variables in `.env`:

```env
# Core Configuration
UPSTREAM_API_KEY=your-anthropic-api-key-here
ADMIN_PASSWORD=your-secure-password
SECRET_KEY=your-jwt-secret-key

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:15432/relay_station

# Redis (optional)
REDIS_URL=redis://localhost:16379/0

# External Services (Docker)
# PostgreSQL: localhost:15432 (user: postgres, password: postgres)
# Redis: localhost:16379 (password: 123456)
```

### Secret Key Generation

Generate a secure JWT secret key:
```bash
openssl rand -hex 32
```

### Advanced Configuration

Edit `config.yaml` for detailed settings:

```yaml
upstream:
  primary:
    url: "https://api.anthropic.com/v1"
    api_key: "${UPSTREAM_API_KEY}"
    timeout: 60
    max_retries: 3

rate_limit:
  by_tier:
    basic:
      requests: 100
      period: 60
    premium:
      requests: 1000
      period: 60
```

## Usage Guide

### Admin Operations

1. **Login to get admin token**:
```bash
curl -X POST http://localhost:8000/admin/login \
  -u admin:your-admin-password
```

2. **Create API key for users**:
```bash
curl -X POST http://localhost:8000/admin/api-keys \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "User Name",
    "description": "Description",
    "token_limit": 1000000,
    "rate_limit_tier": "basic"
  }'
```

Response includes the generated API key (shown only once):
```json
{
  "id": "uuid",
  "api_key": "sk-proxy-xxx...",
  "name": "User Name",
  "token_limit": 1000000,
  "tokens_used": 0,
  "is_active": true
}
```

### Client Configuration

**For Claude Code users**, configure environment variables:
```bash
export ANTHROPIC_API_KEY="sk-proxy-xxx..."  # Your relay-generated key
export ANTHROPIC_BASE_URL="http://localhost:8000"  # Relay URL
```

### User API Operations

1. **Check usage statistics**:
```bash
curl -X GET http://localhost:8000/api/usage \
  -H "Authorization: Bearer sk-proxy-xxx..."
```

2. **Check quota status**:
```bash
curl -X GET http://localhost:8000/api/usage/quota \
  -H "Authorization: Bearer sk-proxy-xxx..."
```

3. **Get daily usage breakdown**:
```bash
curl -X GET http://localhost:8000/api/usage/daily \
  -H "Authorization: Bearer sk-proxy-xxx..."
```

## API Endpoints

### Admin Endpoints (Require Admin Authentication)
- `POST /admin/login` - Admin login
- `POST /admin/api-keys` - Create API key
- `GET /admin/api-keys` - List all keys
- `GET /admin/api-keys/{id}` - Get key details
- `POST /admin/api-keys/{id}/disable` - Disable key
- `POST /admin/api-keys/{id}/enable` - Enable key
- `DELETE /admin/api-keys/{id}` - Delete key

### User Endpoints (Require API Key)
- `GET /api/usage` - Get usage statistics
- `GET /api/usage/daily` - Get daily usage breakdown
- `GET /api/usage/logs` - Get usage logs
- `GET /api/usage/quota` - Get quota status

### Proxy Endpoints
- `/*` - All other requests are forwarded to upstream API

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Claude Code   │───▶│   Relay Proxy   │───▶│  Anthropic API  │
│     Client      │    │    Service      │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   PostgreSQL    │
                       │   Database      │
                       └─────────────────┘
```

### Core Components

- **API Layer** (`app/api/`): REST endpoints for admin and proxy operations
- **Service Layer** (`app/services/`): Business logic for API keys, usage tracking, and proxying
- **Data Layer** (`app/models/`): SQLAlchemy models for database entities
- **Core Layer** (`app/core/`): Configuration, security, logging, and metrics

### Key Features

1. **Proxy Service** (`app/services/proxy_service.py`):
   - Replaces user's proxy key with real Anthropic API key
   - Implements retry logic with exponential backoff
   - Extracts token usage from API responses
   - Falls back to tiktoken estimation when needed

2. **Token Management**:
   - Uses tiktoken for accurate token counting
   - Tracks prompt_tokens, completion_tokens, total_tokens
   - Enforces per-key quotas and rate limits

3. **Security**:
   - API keys hashed using bcrypt before storage
   - JWT tokens for admin authentication
   - Request/response filtering to prevent data leakage

## Monitoring & Metrics

### Prometheus Metrics
The service exports the following metrics:
- `relay_requests_total` - Total number of requests
- `proxy_duration_seconds` - Proxy request latency
- `tokens_used_total` - Total tokens consumed
- `token_quota_usage_ratio` - Quota usage percentage

Access metrics at: `http://localhost:8000/metrics`

### Health Check
Monitor service health:
```bash
curl http://localhost:8000/health
```

## Security Best Practices

### Production Configuration
- Use strong passwords and complex SECRET_KEY
- Enable HTTPS with reverse proxy (Nginx/Apache)
- Restrict admin endpoint access by IP
- Set up proper firewall rules

### API Key Management
- Rotate admin passwords regularly
- Create separate API keys for different applications
- Set reasonable token limits and expiration times
- Monitor for unusual usage patterns

### Monitoring & Alerting
- Set up quota usage alerts
- Monitor for suspicious request patterns
- Regular audit of usage logs
- Track failed authentication attempts

## Troubleshooting

### Common Issues

**Database Connection Failed**:
- Verify PostgreSQL is running
- Check DATABASE_URL configuration
- Ensure database user has proper permissions

**Upstream API Timeout**:
- Verify UPSTREAM_API_KEY is valid
- Check network connectivity
- Adjust timeout configuration in config.yaml

**Inaccurate Token Counting**:
- Ensure tiktoken is installed: `pip install tiktoken`
- Verify model names are correctly identified

## Development

### Testing
```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=app tests/
```

### Code Quality
```bash
# Format code
black app/

# Linting
flake8 app/

# Type checking
mypy app/
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

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- Create an issue in the repository
- Check existing documentation
- Contact maintainers