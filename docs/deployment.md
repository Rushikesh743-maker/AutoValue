# AutoValue Production Deployment Guide (Phase 9)

This guide documents the architecture, configuration, deployment runbook, rollback procedures, and health verification for **AutoValue**.

---

## 1. System Architecture

```
                 [ Internet Users / API Clients ]
                                |
                                v
               +----------------------------------+
               |  Nginx Edge / Reverse Proxy      |
               |  - TLS / HTTPS Termination       |
               |  - Security Headers (CSP, HSTS)  |
               |  - Gzip Compression              |
               |  - Static Asset Caching (SPA)    |
               +----------------+-----------------+
                                |
             +------------------+------------------+
             |                                     |
             v                                     v
+--------------------------+          +--------------------------+
|  Frontend Static (SPA)   |          |  FastAPI Backend (ASGI)  |
|  - React 19 + TypeScript |          |  - Gunicorn / Uvicorn    |
|  - Vite production bundle|          |  - Rate Limiting         |
|                          |          |  - Request IDs & Logging |
+--------------------------+          |  - Model Registry (v002) |
                                      +-------------+------------+
                                                    |
                                                    v
                                      +--------------------------+
                                      |  PostgreSQL 16 Database  |
                                      |  - Connection Pooling    |
                                      |  - User & Valuation Data |
                                      |  - Alembic Migrations    |
                                      +--------------------------+
```

---

## 2. Environment Variables & Secret Configuration

Set the following environment variables in your production environment manager (e.g. AWS Secrets Manager, Render Env, Doppler, or systemd):

| Variable | Type | Required | Description | Example / Recommended |
|---|---|---|---|---|
| `ENVIRONMENT` | String | **Yes** | Execution mode. Enforces strict production checks. | `production` |
| `DEBUG` | Boolean | **Yes** | Debug mode. Automatically forced `false` in production. | `false` |
| `DOCS_ENABLED` | Boolean | No | Controls `/api/docs` and `/api/redoc`. | `false` (or `true` if public API) |
| `SECRET_KEY` | String | **Yes** | 256-bit cryptographic signing secret. | `openssl rand -hex 32` |
| `AUTH_SECRET` | String | **Yes** | 256-bit secret key for JWT session tokens. | `openssl rand -hex 32` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Integer | No | JWT access token lifetime (default: 1440 min / 24h). | `1440` |
| `COOKIE_SECURE` | Boolean | **Yes** | Enforces `Secure` flag on session cookies (HTTPS). | `true` |
| `COOKIE_SAMESITE` | String | No | Session cookie CSRF policy (`lax`, `strict`, `none`). | `lax` |
| `COOKIE_NAME` | String | No | Session cookie identifier. | `autovalue_token` |
| `DATABASE_URL` | String | **Yes** | PostgreSQL connection URI with `psycopg3` driver. | `postgresql+psycopg://user:pass@db-host:5432/autovalue` |
| `DB_POOL_SIZE` | Integer | No | Persistent database connection pool size. | `10` |
| `DB_MAX_OVERFLOW` | Integer | No | Maximum burst connections beyond pool size. | `20` |
| `DB_POOL_TIMEOUT` | Integer | No | Seconds before database checkout timeout. | `30` |
| `DB_POOL_RECYCLE` | Integer | No | Seconds before recycling idle database connections. | `1800` |
| `BACKEND_CORS_ORIGINS` | JSON / CSV | **Yes** | Explicit allowed origins (wildcard `*` rejected in prod). | `["https://autovalue.example.com"]` |
| `TRUSTED_HOSTS` | JSON / CSV | **Yes** | Permitted HTTP Host header domains. | `["autovalue.example.com", "api.autovalue.example.com"]` |
| `RATE_LIMIT_PER_MINUTE` | Integer | No | Max valuation requests per minute per IP. | `60` |
| `MAX_REQUEST_BODY_BYTES` | Integer | No | Max HTTP payload size (default 1MB). | `1048576` |
| `AUTOVALUE_MODEL_VERSION`| String | **Yes** | Active version in model registry. | `v002` |
| `LOG_LEVEL` | String | No | Application log level. | `INFO` |
| `LOG_FORMAT` | String | No | Log output format. | `json` |
| `ENABLE_PROMETHEUS_METRICS` | Boolean | No | Expose `/metrics` Prometheus endpoint. | `true` |

---

## 3. Database Migration Runbook

AutoValue uses Alembic for declarative, versioned database migrations.

### Apply Migrations
Execute from the application root directory with `DATABASE_URL` configured:
```bash
alembic upgrade head
```

### Validate Migration Status
```bash
alembic current
alembic check
```

### Rollback Previous Migration
```bash
alembic downgrade -1
```

---

## 4. Model Artifact Deployment Safety

The AutoValue valuation engine requires pre-trained, validated ML artifacts:
- `models/model_v002.joblib`
- `models/preprocessor_v002.joblib`
- `models/metadata_v002.json`

### Cryptographic Verification
During container startup and in the `/api/ready` probe, `ModelRegistry` calculates the SHA-256 checksum of on-disk model artifacts and compares them against `artifact_integrity` in `metadata_v002.json`.

If any artifact is missing or corrupted, the service **fails closed** and returns HTTP 503 rather than serving corrupt or synthetic estimates.

---

## 5. Health & Observability Endpoints

| Endpoint | Method | Purpose | Expected Response |
|---|---|---|---|
| `/api/health` | `GET` | Liveness probe (process is running) | `{"status": "ok", "service": "autovalue-api", "version": "0.9.0"}` |
| `/api/ready` | `GET` | Readiness probe (DB, Model SHA-256, Dataset) | HTTP 200 `{"status": "ready", "checks": {...}}` or HTTP 503 |
| `/metrics` | `GET` | Prometheus telemetry scraping | Plaintext Prometheus metrics |

---

## 6. Deployment Target Runbooks

### 6.1 Docker Compose (Self-Hosted / VPS)
```bash
# 1. Clone repository and create production .env
git clone <repo-url> /opt/autovalue
cd /opt/autovalue
cp .env.example .env
# Edit .env with production credentials

# 2. Build and launch services
docker compose -f docker-compose.yml up -d --build

# 3. Run database migrations inside backend container
docker compose exec backend alembic upgrade head

# 4. Verify system health
curl -f http://localhost:8000/api/health
curl -f http://localhost:8000/api/ready
```

### 6.2 Render / Railway / Fly.io (PaaS)
1. **Managed PostgreSQL**: Provision a managed PostgreSQL instance and copy the connection URI into `DATABASE_URL`.
2. **Backend Web Service**:
   - Environment: Docker or Python 3.11
   - Build command: `pip install -r requirements.txt`
   - Release command: `alembic upgrade head`
   - Start command: `gunicorn backend.app.main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 60`
   - Health check path: `/api/health`
3. **Frontend Static Site**:
   - Build command: `npm install && npm run build`
   - Publish directory: `frontend/dist`
   - Environment variable: `VITE_API_BASE_URL=https://your-backend-url.com`

---

## 7. Rollback & Disaster Recovery

If an issue occurs post-deployment:
1. **Application Rollback**: Re-deploy the previous tagged Docker image or commit SHA.
2. **Database Rollback**: If a database schema change needs reverting, run `alembic downgrade -1`.
3. **Cache & Cookies**: Session cookies expire automatically according to `ACCESS_TOKEN_EXPIRE_MINUTES`. Rotating `AUTH_SECRET` immediately invalidates all active sessions if a security incident occurs.

---

## 8. Post-Deployment Verification Checklist

- [ ] Liveness probe returns HTTP 200: `curl -I https://api.yourdomain.com/api/health`
- [ ] Readiness probe returns HTTP 200: `curl -I https://api.yourdomain.com/api/ready`
- [ ] Model SHA-256 checksum verified in `/api/ready` response
- [ ] Alembic schema is at `head`
- [ ] Rate limiting is operational (HTTP 429 after threshold)
- [ ] HTTPS redirect and `Secure` cookie flag enabled
- [ ] Automated smoke test passes: `python scripts/smoke_test.py --url https://api.yourdomain.com`
- [ ] Observability scraper is collecting `/metrics`
