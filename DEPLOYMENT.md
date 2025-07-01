# MemoryBank Production Deployment Guide

This guide covers deploying MemoryBank as a scalable, multi-tenant SaaS platform.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │    │  Reverse Proxy  │    │   Tenant Apps   │
│   (Traefik)     │───▶│   (Nginx)       │───▶│  (Containers)   │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   DNS/CDN       │    │   SSL/TLS       │    │  Vector Storage │
│                 │    │  (Let's Encrypt)│    │   (Per Tenant)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### 1. Prerequisites

- Docker & Docker Compose
- Domain name with DNS control
- SSL certificates (or Let's Encrypt)
- API keys for LLM providers

### 2. Initial Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd MemMem

# Create network for containers
docker network create memorybank_network

# Start Traefik reverse proxy
docker-compose -f docker-compose.traefik.yml up -d traefik
```

### 3. Deploy Your First Tenant

```bash
# Make scripts executable
chmod +x scripts/*.sh scripts/*.py

# Create a new tenant
./scripts/manage-tenants.py create customer1 --domain yourdomain.com

# Or use the shell script directly
./scripts/deploy-tenant.sh customer1 your-api-key yourdomain.com
```

### 4. Verify Deployment

```bash
# Check tenant status
./scripts/manage-tenants.py info customer1

# Test the API
curl -H "Authorization: Bearer your-api-key" \
     https://customer1.yourdomain.com/health
```

## 🐳 Docker Deployment

### Single Tenant Deployment

```bash
# Set environment variables
export TENANT_ID=customer1
export API_KEY=your-secure-api-key
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-...

# Deploy
docker-compose up -d
```

### Multi-Tenant with Traefik

```bash
# Start Traefik first
docker-compose -f docker-compose.traefik.yml up -d

# Deploy tenants using management script
./scripts/manage-tenants.py create tenant1
./scripts/manage-tenants.py create tenant2
./scripts/manage-tenants.py create tenant3
```

## ☸️ Kubernetes Deployment

### 1. Install Helm Chart

```bash
# Add the repository (when published)
helm repo add memorybank https://charts.memorybank.dev
helm repo update

# Or install from local files
cd k8s/helm
```

### 2. Configure Values

Create `production-values.yaml`:

```yaml
image:
  repository: your-registry/memorybank
  tag: "v1.0.0"

multiTenant:
  enabled: true

secrets:
  OPENAI_API_KEY: "sk-..."
  ANTHROPIC_API_KEY: "sk-..."

tenants:
  - id: "customer1"
    apiKey: "secure-key-123"
    domain: "customer1.yourdomain.com"
    resources:
      limits:
        cpu: 1000m
        memory: 1Gi
    persistence:
      size: 20Gi

persistence:
  enabled: true
  storageClass: "fast-ssd"
  size: 100Gi

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
  hosts:
    - host: "*.yourdomain.com"
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: memorybank-tls
      hosts:
        - "*.yourdomain.com"

monitoring:
  enabled: true
```

### 3. Deploy

```bash
helm install memorybank ./memorybank -f production-values.yaml
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TENANT_ID` | `default` | Unique tenant identifier |
| `API_KEY` | - | API key for accessing the service |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `ANTHROPIC_API_KEY` | - | Anthropic API key |
| `GOOGLE_API_KEY` | - | Google API key |
| `LLM_PROVIDER` | `claude` | Default LLM provider |
| `EMBEDDING_PROVIDER` | `openai` | Embedding provider |
| `CHROMA_DB_PATH` | `./data` | Path for vector database |
| `FORGETTING_INTERVAL_HOURS` | `24` | Hours between forgetting curve runs |
| `MAINTENANCE_INTERVAL_HOURS` | `168` | Hours between maintenance |
| `FORGETTING_THRESHOLD` | `0.1` | Importance threshold for forgetting |

### Multi-Tenant Configuration

Each tenant gets:
- Isolated database in `/data/{tenant_id}/`
- Unique API key
- Subdomain: `{tenant_id}.yourdomain.com`
- Separate container with resource limits

## 🔄 Tenant Management

### Creating Tenants

```bash
# Interactive creation
./scripts/manage-tenants.py create new-customer

# With custom domain
./scripts/manage-tenants.py create new-customer --domain mydomain.com

# With custom API key
./scripts/manage-tenants.py create new-customer --api-key custom-key-123
```

### Managing Tenants

```bash
# List all tenants
./scripts/manage-tenants.py list

# Get tenant information
./scripts/manage-tenants.py info customer1

# Get usage statistics
./scripts/manage-tenants.py stats --tenant-id customer1

# Delete tenant (stops container, keeps data)
./scripts/manage-tenants.py delete customer1

# Force delete (removes all data)
./scripts/manage-tenants.py delete customer1 --force
```

### API Integration

Create tenants via your webapp:

```python
import subprocess
import json

def create_memorybank_tenant(tenant_id, domain="yourdomain.com"):
    try:
        result = subprocess.run([
            "./scripts/manage-tenants.py", "create", 
            tenant_id, "--domain", domain
        ], capture_output=True, text=True, check=True)
        
        tenant_info = json.loads(result.stdout)
        return {
            "success": True,
            "tenant_id": tenant_info["tenant_id"],
            "api_key": tenant_info["api_key"],
            "endpoint": f"https://{tenant_info['domain']}"
        }
    except subprocess.CalledProcessError as e:
        return {"success": False, "error": e.stderr}
```

## 📊 Monitoring & Logging

### Prometheus + Grafana

```bash
# Start monitoring stack
docker-compose -f docker-compose.traefik.yml up -d prometheus grafana

# Access dashboards
# Grafana: https://grafana.yourdomain.com (admin/admin123)
# Prometheus: https://prometheus.yourdomain.com
```

### Key Metrics

- **Request Rate**: Requests per second per tenant
- **Error Rate**: 4xx/5xx errors
- **Response Time**: API response latency
- **Memory Usage**: Vector database size
- **Container Health**: Up/down status

### Alerting

Alerts are configured for:
- High error rate (>10%)
- High memory usage (>90%)
- Container downtime
- High API latency (>2s)
- Low disk space (<10%)

## 🔒 Security

### API Keys

- Generated automatically with `mb_` prefix
- 32-byte URL-safe random strings
- Hashed in database (SHA-256)
- Per-tenant isolation

### Network Security

- Containers isolated in Docker network
- Rate limiting via Nginx/Traefik
- HTTPS enforced with Let's Encrypt
- Security headers configured

### Data Isolation

- Each tenant has separate database directory
- Container filesystem isolation
- No shared data between tenants

## 🚨 Troubleshooting

### Common Issues

1. **Container won't start**
   ```bash
   # Check logs
   docker-compose logs memorybank-{tenant_id}
   
   # Check environment variables
   docker-compose config
   ```

2. **DNS not resolving**
   ```bash
   # Verify DNS configuration
   nslookup tenant1.yourdomain.com
   
   # Check Traefik routing
   curl -H "Host: tenant1.yourdomain.com" http://localhost
   ```

3. **SSL certificate issues**
   ```bash
   # Check certificate status
   docker-compose logs traefik | grep -i cert
   
   # Force certificate renewal
   docker-compose restart traefik
   ```

4. **High memory usage**
   ```bash
   # Check vector database size
   du -sh data/*/memory_db/
   
   # Run forgetting curve manually
   curl -X POST -H "Authorization: Bearer {api_key}" \
        https://tenant1.yourdomain.com/run_forgetting_curve
   ```

### Health Checks

```bash
# System health
curl https://tenant1.yourdomain.com/health

# Memory statistics
curl -H "Authorization: Bearer {api_key}" \
     https://tenant1.yourdomain.com/memory_stats

# Scheduler status
curl -H "Authorization: Bearer {api_key}" \
     https://tenant1.yourdomain.com/scheduler_status
```

## 📈 Scaling

### Horizontal Scaling

1. **Load Balancer**: Use multiple Traefik instances
2. **Database**: Shard by tenant_id
3. **Storage**: Distributed storage for vector DBs
4. **Cache**: Redis for session management

### Vertical Scaling

```yaml
# docker-compose.yml
services:
  memorybank:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

### Auto-scaling (Kubernetes)

```yaml
# values.yaml
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80
```

## 🔄 Updates & Maintenance

### Rolling Updates

```bash
# Build new image
docker build -t memorybank:v1.1.0 .

# Update deployment
./scripts/update-tenant.sh customer1 v1.1.0

# Or update all tenants
./scripts/manage-tenants.py list | jq -r '.[].tenant_id' | \
  xargs -I {} ./scripts/update-tenant.sh {} v1.1.0
```

### Backup Strategy

```bash
# Backup tenant data
tar -czf backup-customer1-$(date +%Y%m%d).tar.gz \
    deployments/customer1/data/

# Automated backup script
./scripts/backup-tenants.sh
```

### Database Maintenance

```bash
# Run forgetting curve for all tenants
./scripts/manage-tenants.py list | jq -r '.[].tenant_id' | \
  xargs -I {} curl -X POST -H "Authorization: Bearer {api_key}" \
    https://{}.yourdomain.com/run_forgetting_curve
```

## 📞 Support

- **Documentation**: This file and inline code comments
- **Monitoring**: Grafana dashboards for real-time metrics
- **Logging**: Centralized logs via Docker logging drivers
- **Health Checks**: Automated container health monitoring