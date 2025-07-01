#!/bin/bash

# Automated tenant deployment script
# Usage: ./deploy-tenant.sh <tenant_id> <api_key> [domain]

set -e

TENANT_ID="$1"
API_KEY="$2"
DOMAIN="${3:-yourdomain.com}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Validate inputs
if [ -z "$TENANT_ID" ] || [ -z "$API_KEY" ]; then
    echo "Usage: $0 <tenant_id> <api_key> [domain]"
    echo "Example: $0 user123 secret_key_123 mydomain.com"
    exit 1
fi

# Validate tenant ID format (alphanumeric and dashes only)
if [[ ! "$TENANT_ID" =~ ^[a-zA-Z0-9-]+$ ]]; then
    echo "Error: Tenant ID must contain only alphanumeric characters and dashes"
    exit 1
fi

echo "🚀 Deploying MemoryBank instance for tenant: $TENANT_ID"

# Create tenant-specific directories
TENANT_DIR="$PROJECT_ROOT/deployments/$TENANT_ID"
mkdir -p "$TENANT_DIR"
mkdir -p "$TENANT_DIR/data"
mkdir -p "$TENANT_DIR/logs"

# Generate tenant-specific docker-compose file
cat > "$TENANT_DIR/docker-compose.yml" << EOF
version: '3.8'

services:
  memorybank-$TENANT_ID:
    build:
      context: $PROJECT_ROOT
      dockerfile: Dockerfile
    container_name: memorybank-$TENANT_ID
    ports:
      - "0:8000"  # Let Docker assign a random port
    environment:
      - API_KEY=$API_KEY
      - TENANT_ID=$TENANT_ID
      - OPENAI_API_KEY=\${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=\${ANTHROPIC_API_KEY}
      - GOOGLE_API_KEY=\${GOOGLE_API_KEY}
      - LLM_PROVIDER=\${LLM_PROVIDER:-claude}
      - EMBEDDING_PROVIDER=\${EMBEDDING_PROVIDER:-openai}
      - CHROMA_DB_PATH=/app/data
      - FORGETTING_INTERVAL_HOURS=\${FORGETTING_INTERVAL_HOURS:-24}
      - MAINTENANCE_INTERVAL_HOURS=\${MAINTENANCE_INTERVAL_HOURS:-168}
      - FORGETTING_THRESHOLD=\${FORGETTING_THRESHOLD:-0.1}
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
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.$TENANT_ID.rule=Host(\`$TENANT_ID.$DOMAIN\`)"
      - "traefik.http.routers.$TENANT_ID.tls=true"
      - "traefik.http.routers.$TENANT_ID.tls.certresolver=letsencrypt"
      - "traefik.http.services.$TENANT_ID.loadbalancer.server.port=8000"
      - "traefik.docker.network=memorybank_network"
    networks:
      - memorybank_network

networks:
  memorybank_network:
    external: true
EOF

# Create tenant-specific environment file
cat > "$TENANT_DIR/.env" << EOF
TENANT_ID=$TENANT_ID
API_KEY=$API_KEY
DOMAIN=$DOMAIN

# Copy these from your main .env file
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
LLM_PROVIDER=claude
EMBEDDING_PROVIDER=openai
FORGETTING_INTERVAL_HOURS=24
MAINTENANCE_INTERVAL_HOURS=168
FORGETTING_THRESHOLD=0.1
EOF

# Deploy the container
echo "📦 Building and starting container for $TENANT_ID..."

cd "$TENANT_DIR"

# Copy environment variables from main .env if it exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "📋 Copying environment variables from main .env file..."
    # Extract API keys from main .env and update tenant .env
    grep -E "^(OPENAI_API_KEY|ANTHROPIC_API_KEY|GOOGLE_API_KEY)" "$PROJECT_ROOT/.env" >> .env
fi

# Start the container
docker-compose up -d

# Wait for container to be healthy
echo "⏳ Waiting for container to be healthy..."
timeout=60
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
        docker-compose logs
        exit 1
    fi
done

# Get the assigned port
CONTAINER_PORT=$(docker-compose port memorybank-$TENANT_ID 8000 | cut -d: -f2)

# Display deployment information
echo ""
echo "🎉 Deployment successful!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Tenant ID: $TENANT_ID"
echo "Domain: $TENANT_ID.$DOMAIN"
echo "Container Port: $CONTAINER_PORT"
echo "Health Check: http://localhost:$CONTAINER_PORT/health"
echo "API Endpoint: http://localhost:$CONTAINER_PORT"
echo "Deployment Directory: $TENANT_DIR"
echo ""
echo "📝 Next steps:"
echo "1. Configure DNS: $TENANT_ID.$DOMAIN -> your server IP"
echo "2. Test the API: curl -H 'Authorization: Bearer $API_KEY' http://localhost:$CONTAINER_PORT/health"
echo "3. Update your reverse proxy configuration if not using Traefik"
echo ""

# Save deployment info
cat > "$TENANT_DIR/deployment-info.json" << EOF
{
  "tenant_id": "$TENANT_ID",
  "domain": "$TENANT_ID.$DOMAIN",
  "api_key": "$API_KEY",
  "container_port": $CONTAINER_PORT,
  "deployed_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "deployment_directory": "$TENANT_DIR"
}
EOF

echo "💾 Deployment info saved to: $TENANT_DIR/deployment-info.json"