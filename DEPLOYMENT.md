# AI ARCHITECT — DEPLOYMENT & OPERATIONS GUIDE

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Production Deployment](#production-deployment)
4. [Environment Configuration](#environment-configuration)
5. [Database Management](#database-management)
6. [Monitoring & Logging](#monitoring--logging)
7. [Scaling & Performance](#scaling--performance)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Services (Free Tier)

- **Supabase** (PostgreSQL + pgvector) — https://supabase.com
- **OpenRouter** (AI Model API) — https://openrouter.ai
- **Cloudflare R2** (Object Storage) — https://dash.cloudflare.com
- **Upstash Redis** (Cache) — https://upstash.com
- **GitHub** (Source Control + CI/CD) — https://github.com

### Local Development Requirements

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git
- `curl` or Postman (for API testing)

---

## Local Development Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/ai-architect.git
cd ai-architect
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Fill in your API keys
# OPENROUTER_API_KEY=sk-or-v1-...
# SUPABASE_URL=https://your-project.supabase.co
# SUPABASE_ANON_KEY=...
# etc.
```

### 3. Start Services with Docker Compose

```bash
docker-compose up -d
```

This starts:
- FastAPI backend on `http://localhost:8000`
- Next.js frontend on `http://localhost:3000`
- Redis cache on `localhost:6379`

### 4. Initialize Database

```bash
# Apply schema to Supabase
# Option 1: Use Supabase UI
# - Go to SQL Editor in Supabase dashboard
# - Paste contents of backend/database/schema.sql

# Option 2: Use psql (if you have it)
psql postgresql://postgres:password@db.supabase.co:5432/postgres < backend/database/schema.sql
```

### 5. Verify Setup

```bash
# Check backend health
curl http://localhost:8000/health

# Check frontend
open http://localhost:3000

# View API docs
open http://localhost:8000/api/docs
```

---

## Production Deployment

### Option 1: Vercel + Railway (Recommended)

#### Frontend (Vercel)

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel --prod

# Configure environment variables in Vercel dashboard
```

#### Backend (Railway)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Link to existing project (if applicable)
railway link

# Deploy
railway up

# View logs
railway logs
```

#### Configure Domain

1. Point DNS to Vercel frontend
2. Configure API endpoint in Vercel environment: `NEXT_PUBLIC_API_URL=https://api.yourdomain.com`

### Option 2: Self-Hosted (AWS/GCP/Digital Ocean)

#### Build Docker Images

```bash
# Backend
docker build -f Dockerfile.backend -t ai-architect-backend:latest .

# Frontend
docker build -f frontend/Dockerfile -t ai-architect-frontend:latest .

# Push to registry
docker push your-registry/ai-architect-backend:latest
docker push your-registry/ai-architect-frontend:latest
```

#### Deploy with Docker Compose

```bash
# On your server
docker-compose -f docker-compose.yml up -d
```

#### Setup Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;
    
    location / {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://frontend:3000;
        proxy_set_header Host $host;
    }
}
```

---

## Environment Configuration

### Required Variables (.env)

```bash
# ---- OpenRouter (Free Models) ----
OPENROUTER_API_KEY=sk-or-v1-your-key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# ---- Supabase (PostgreSQL) ----
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key

# ---- Cloudflare R2 (Object Storage) ----
CLOUDFLARE_R2_ACCESS_KEY=your-access-key
CLOUDFLARE_R2_SECRET_KEY=your-secret-key
CLOUDFLARE_R2_BUCKET=ai-architect-scenes
CLOUDFLARE_R2_ENDPOINT=https://your-account.r2.cloudflarestorage.com

# ---- Upstash Redis ----
UPSTASH_REDIS_URL=redis://default:token@endpoint.upstash.io:6379
UPSTASH_REDIS_TOKEN=your-token

# ---- HuggingFace (Optional - for inference) ----
HUGGINGFACE_API_TOKEN=hf_your_token

# ---- Auth ----
JWT_SECRET=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# ---- Application ----
APP_NAME=AI Architect
APP_VERSION=0.1.0
DEBUG=False
ENVIRONMENT=production

# ---- CORS ----
CORS_ORIGINS=https://yourdomain.com,https://api.yourdomain.com

# ---- Frontend ----
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_WS_URL=wss://api.yourdomain.com
NODE_ENV=production
```

---

## Database Management

### Backup Database

```bash
# Using Supabase backup feature (built-in)
# Dashboard → Database → Backups → Manual backup

# Or export with pg_dump:
PGPASSWORD="your_password" pg_dump \
    -h db.supabase.co \
    -U postgres \
    -d postgres > backup.sql
```

### Restore Database

```bash
PGPASSWORD="your_password" psql \
    -h db.supabase.co \
    -U postgres \
    -d postgres < backup.sql
```

### Run Migrations

```bash
# Create migration
alembic revision --autogenerate -m "add_new_table"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## Monitoring & Logging

### View Backend Logs

```bash
# Docker
docker logs -f ai-architect-backend

# Railway
railway logs

# Supabase
# Dashboard → Logs → Postgres logs
```

### View Frontend Logs

```bash
# Docker
docker logs -f ai-architect-frontend

# Vercel
vercel logs

# Browser console
# Open Developer Tools → Console tab
```

### Setup Error Tracking

```bash
# Add Sentry integration
pip install sentry-sdk

# In backend/main.py
import sentry_sdk
sentry_sdk.init("your-sentry-dsn")
```

### Monitor API Performance

```bash
# View request latency
curl http://localhost:8000/api/docs

# Check database query performance
# Supabase Dashboard → Database → Query Performance

# View token usage
# OpenRouter Dashboard → Usage
```

---

## Scaling & Performance

### Database Optimization

```sql
-- Add indexes for common queries
CREATE INDEX CONCURRENTLY idx_scenes_status_created 
ON scenes(status, created_at DESC);

CREATE INDEX CONCURRENTLY idx_agent_executions_agent_name 
ON agent_executions(agent_name, created_at DESC);

-- Analyze table
ANALYZE scenes;
```

### Redis Caching

```python
# Cache scene data
from backend.database.client import redis_client

# Set cache
redis_client.set(f"scene:{scene_id}", json.dumps(scene_data), ex=3600)

# Get cache
cached = redis_client.get(f"scene:{scene_id}")
```

### CDN Configuration

```bash
# Configure Cloudflare CDN for R2 assets
# Cloudflare Dashboard → CDN → Cache Rules
# Pattern: /assets/* → Cache Level: Cache Everything
```

### Rate Limiting

```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/scenes")
@limiter.limit("100/minute")
async def list_scenes(...):
    ...
```

---

## Troubleshooting

### Issue: Database Connection Failed

```bash
# Check Supabase is online
curl https://your-project.supabase.co

# Verify credentials in .env
# Test connection
psql postgresql://user:pass@host:5432/db

# Check firewall rules
# Supabase Dashboard → Settings → Database → Connection String
```

### Issue: OpenRouter API Rate Limited

```python
# Check token budget in OpenRouter client
client.get_token_budget_status("agent_id")

# Free tier limits:
# - 20 requests/minute
# - 500 tokens total per day
# Solution: Use paid tier or implement caching
```

### Issue: WebSocket Connection Failing

```javascript
// In frontend console
const ws = new WebSocket("wss://api.yourdomain.com/ws/client123");
ws.onopen = () => console.log("Connected");
ws.onerror = (err) => console.error("Error:", err);
```

### Issue: Scene Generation Times Out

```bash
# Increase timeout in main.py
# FastAPI timeout is 60 seconds by default

# Check OpenRouter response times
# If models are slow, use simpler models:
FALLBACK_CHAIN = [
    "meta-llama/llama-3.3-70b-instruct:free",  # Faster
    "deepseek/deepseek-r1:free"  # Slower but smarter
]
```

### Issue: Memory Usage High

```bash
# Check what's consuming memory
# Docker stats
docker stats ai-architect-backend

# Restart service
docker-compose restart backend

# In Python, profile memory
import tracemalloc
tracemalloc.start()
# ... your code ...
tracemalloc.take_snapshot()
```

### Issue: Build Fails

```bash
# Clear Docker cache
docker-compose down -v
docker-compose build --no-cache

# Check Python version compatibility
python --version  # Should be 3.11+

# Install missing dependencies
pip install -r backend/requirements.txt --force-reinstall
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

```yaml
name: AI Architect CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt
          
      - name: Run tests
        run: pytest backend/tests
      
      - name: Lint
        run: flake8 backend

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to Railway
        run: |
          railway up
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

---

## Maintenance

### Regular Tasks

- **Daily**: Check logs for errors
- **Weekly**: Review API usage and costs
- **Monthly**: Update dependencies, run security scan
- **Quarterly**: Review architecture and plan optimization

### Update Dependencies

```bash
# Backend
pip list --outdated
pip install --upgrade package-name

# Frontend
npm outdated
npm update package-name
```

### Security

```bash
# Scan for vulnerabilities
pip install bandit
bandit -r backend

npm audit
npm audit fix
```

---

## Cost Estimation (Free Tier)

| Service | Free Tier | Est. Monthly Cost at Scale |
|---------|-----------|---------------------------|
| Supabase | 500 MB DB | $25-100 |
| OpenRouter | $5 credits | $100-500 |
| Cloudflare R2 | 10 GB/mo | $10-50 |
| Upstash Redis | 10K cmds/day | $20-100 |
| Vercel | Included | $0-50 |
| Railway | $5 free | $20-100 |
| **Total** | — | **$175-900/month** |

---

## Support & Resources

- **Documentation**: https://github.com/your-org/ai-architect/wiki
- **Issues**: https://github.com/your-org/ai-architect/issues
- **Discussions**: https://github.com/your-org/ai-architect/discussions
- **API Docs**: http://localhost:8000/api/docs
- **Supabase Docs**: https://supabase.com/docs
- **OpenRouter Docs**: https://openrouter.ai/docs
