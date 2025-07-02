#!/bin/bash

# Debug deployment script to test individual components
set -e

TENANT_ID="$1"
API_KEY="$2"
DOMAIN="${3:-test.local}"

if [ -z "$TENANT_ID" ] || [ -z "$API_KEY" ]; then
    echo "Usage: $0 <tenant_id> <api_key> [domain]"
    exit 1
fi

echo "🔍 Debug deployment for tenant: $TENANT_ID"

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found"
    exit 1
fi
echo "✅ Docker found: $(docker --version)"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found"
    exit 1
fi
echo "✅ Docker Compose found: $(docker-compose --version)"

# Check network
echo "🌐 Checking Docker network..."
if ! docker network inspect memorybank_network &> /dev/null; then
    echo "⚠️ memorybank_network not found, creating..."
    docker network create memorybank_network
else
    echo "✅ memorybank_network exists"
fi

# Check if tenant already exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TENANT_DIR="$PROJECT_ROOT/deployments/$TENANT_ID"

if [ -d "$TENANT_DIR" ]; then
    echo "⚠️ Tenant directory already exists: $TENANT_DIR"
    echo "   Removing existing deployment..."
    cd "$TENANT_DIR"
    if [ -f "docker-compose.yml" ]; then
        docker-compose down -v || true
    fi
    cd "$PROJECT_ROOT"
    rm -rf "$TENANT_DIR"
fi

# Create tenant directories
echo "📁 Creating tenant directories..."
mkdir -p "$TENANT_DIR/data"
mkdir -p "$TENANT_DIR/logs"
echo "✅ Directories created"

# Generate docker-compose.yml
echo "📝 Generating docker-compose.yml..."
cat > "$TENANT_DIR/docker-compose.yml" << EOF
version: '3.8'

services:
  memorybank-$TENANT_ID:
    build:
      context: $PROJECT_ROOT
      dockerfile: Dockerfile
    container_name: memorybank-$TENANT_ID
    ports:
      - "0:8000"
    environment:
      - API_KEY=$API_KEY
      - TENANT_ID=$TENANT_ID
      - CHROMA_DB_PATH=/app/data
      - LLM_PROVIDER=claude
      - EMBEDDING_PROVIDER=openai
    volumes:
      - ./data:/app/data/$TENANT_ID
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - memorybank_network

networks:
  memorybank_network:
    external: true
EOF

echo "✅ docker-compose.yml generated"

# Start the container
echo "🚀 Starting container..."
cd "$TENANT_DIR"
docker-compose up -d

# Wait for health check
echo "⏳ Waiting for container to be healthy..."
timeout=120
counter=0

while [ $counter -lt $timeout ]; do
    if docker-compose ps | grep -q "healthy"; then
        echo "✅ Container is healthy!"
        break
    fi
    
    sleep 2
    counter=$((counter + 2))
    
    if [ $counter -ge $timeout ]; then
        echo "❌ Timeout waiting for container to be healthy"
        echo "📋 Container logs:"
        docker-compose logs --tail=20
        exit 1
    fi
done

# Get container port
CONTAINER_PORT=$(docker-compose port memorybank-$TENANT_ID 8000 | cut -d: -f2)

# Test health endpoint
echo "🏥 Testing health endpoint..."
if curl -f "http://localhost:$CONTAINER_PORT/health" > /dev/null 2>&1; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    docker-compose logs --tail=20
    exit 1
fi

# Save deployment info
cat > "deployment-info.json" << EOF
{
  "tenant_id": "$TENANT_ID",
  "domain": "$TENANT_ID.$DOMAIN",
  "api_key": "$API_KEY",
  "container_port": $CONTAINER_PORT,
  "deployed_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "deployment_directory": "$TENANT_DIR"
}
EOF

echo ""
echo "🎉 Debug deployment successful!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Tenant ID: $TENANT_ID"
echo "Container Port: $CONTAINER_PORT"
echo "Health Check: http://localhost:$CONTAINER_PORT/health"
echo "API Test: curl -H 'Authorization: Bearer $API_KEY' http://localhost:$CONTAINER_PORT/health"
echo ""