#!/bin/bash

# Claude Relay Station Deployment Script

set -e

echo "🚀 Claude Relay Station Deployment Script"
echo "========================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file and set required variables:"
    echo "   - UPSTREAM_API_KEY (your Anthropic API key)"
    echo "   - ADMIN_PASSWORD (secure admin password)"
    echo "   - SECRET_KEY (run: openssl rand -hex 32)"
    echo ""
    echo "After editing, run this script again."
    exit 1
fi

# Load environment variables
source .env

# Check required variables
if [ -z "$UPSTREAM_API_KEY" ] || [ "$UPSTREAM_API_KEY" == "your-third-party-api-key-here" ]; then
    echo "❌ Error: UPSTREAM_API_KEY not set in .env file"
    exit 1
fi

if [ -z "$ADMIN_PASSWORD" ] || [ "$ADMIN_PASSWORD" == "change-this-password" ]; then
    echo "❌ Error: ADMIN_PASSWORD not set in .env file"
    exit 1
fi

if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" == "your-secret-key-here-generate-with-openssl-rand-hex-32" ]; then
    echo "❌ Error: SECRET_KEY not set in .env file"
    echo "Generate one with: openssl rand -hex 32"
    exit 1
fi

echo "✅ Environment variables validated"

# Check Docker and Docker Compose
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: Docker Compose is not installed"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"

# Build and start services
echo "🔨 Building Docker images..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo "🏥 Checking service health..."

# Check PostgreSQL
if docker-compose exec -T postgres pg_isready -U relay_user -d relay_station &> /dev/null; then
    echo "✅ PostgreSQL is ready"
else
    echo "❌ PostgreSQL is not ready"
    exit 1
fi

# Check Redis
if docker-compose exec -T redis redis-cli ping &> /dev/null; then
    echo "✅ Redis is ready"
else
    echo "❌ Redis is not ready"
    exit 1
fi

# Run database migrations
echo "🗄️ Running database migrations..."
docker-compose exec -T relay-station alembic upgrade head

# Check application health
echo "🏥 Checking application health..."
if curl -f http://localhost:8000/health &> /dev/null; then
    echo "✅ Application is healthy"
else
    echo "❌ Application health check failed"
    exit 1
fi

echo ""
echo "🎉 Deployment completed successfully!"
echo "========================================="
echo ""
echo "📋 Service URLs:"
echo "   - API: http://localhost:8000"
echo "   - Admin Docs: http://localhost:8000/admin/docs (debug mode only)"
echo "   - Prometheus: http://localhost:9090"
echo "   - Grafana: http://localhost:3000 (admin/admin)"
echo ""
echo "🔑 Next steps:"
echo "   1. Login as admin: http://localhost:8000/admin/login"
echo "   2. Create API keys for users"
echo "   3. Configure Claude Code with relay URL and API key"
echo ""
echo "📖 See README.md for detailed usage instructions"