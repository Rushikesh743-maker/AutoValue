# AutoValue — Production Readiness & Architecture Specification

## 1. Overview & Architecture

AutoValue is an AI-powered used-car valuation, uncertainty estimation, comparable matching, and market intelligence platform for the Indian automotive market.

```
┌─────────────────────────────────────────────────────────────┐
│                 React + TypeScript Frontend                 │
│         (Vite + TailwindCSS + Recharts SPA @ :80/:5173)     │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP / JSON API
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                     │
│  ├── Correlation Middleware (X-Request-ID Tracing)          │
│  ├── Sliding-Window Rate Limiter (Valuation Endpoints)       │
│  ├── Request Body Size Limiter (Max 1MB Payload)            │
│  ├── Centralized Global Error Handlers                      │
│  └── Prometheus Telemetry & Structured Logging              │
├──────────────────────────────┬──────────────────────────────┤
│  Model Registry Service      │  PostgreSQL Database Layer   │
│  ├── SHA-256 Checksum Verify │  ├── SQLAlchemy 2.0 ORM      │
│  ├── In-Memory Bundle Cache  │  ├── Connection Pool (5-10)  │
│  └── Active Model: v002      │  ├── Alembic Migrations      │
│      (XGBoost Regressor)     │  └── Composite B-Tree Indexes│
└──────────────────────────────┴──────────────────────────────┘
```

---

## 2. Environment Configuration Matrix

All configuration is parsed and validated at startup via `backend/app/core/config.py` using `pydantic-settings`:

| Variable | Type | Default | Description |
|---|---|---|---|
| `ENVIRONMENT` | string | `development` | Deployment environment (`development`, `testing`, `production`) |
| `DEBUG` | boolean | `false` | Debug mode (disables docs in production if false) |
| `DATABASE_URL` | string | `postgresql+psycopg://...` | Relational database connection URI |
| `DB_POOL_SIZE` | integer | `5` | SQLAlchemy pool size |
| `DB_MAX_OVERFLOW` | integer | `10` | SQLAlchemy pool overflow headroom |
| `DB_POOL_TIMEOUT` | integer | `30` | Connection checkout timeout in seconds |
| `DB_POOL_RECYCLE` | integer | `1800` | Connection recycling period (30 min) |
| `ACTIVE_MODEL_VERSION` | string | `v002` | Active version of the ML valuation model |
| `CORS_ORIGINS` | comma-separated list | `http://localhost:5173,...` | Allowed CORS origins for browser security |
| `RATE_LIMIT_PER_MINUTE` | integer | `60` | In-memory rate limit per IP for `/api/valuation` |
| `MAX_REQUEST_BODY_BYTES`| integer | `1048576` (1MB) | Maximum allowed incoming request body size |
| `LOG_LEVEL` | string | `INFO` | Application log verbosity |
| `LOG_JSON_FORMAT` | boolean | `true` | Structured JSON log formatting |

---

## 3. Startup & Deployment Procedure

### Local Development Startup
```bash
# 1. Start relational database
docker compose up -d postgres

# 2. Run pending schema migrations
alembic upgrade head

# 3. Start FastAPI backend
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

# 4. Start React Frontend
cd frontend && npm run dev
```

### Production Docker Startup
```bash
# Verify configuration syntax
docker compose config

# Build and start all production services
docker compose up -d --build
```

---

## 4. Health, Readiness & Telemetry Endpoints

- `GET /api/health`: Liveness probe (validates API event loop responsiveness).
- `GET /api/ready`: Readiness probe (checks database connection, active model artifacts + SHA-256 integrity, and processed dataset presence).
- `GET /metrics`: Prometheus formatted metrics counter (HTTP requests, status codes, valuation counts, latency).
- `GET /api/models`: Model registry metadata and candidate catalog.
- `GET /api/models/drift`: Population Stability Index (PSI) and Kolmogorov-Smirnov (KS) drift telemetry.
- `GET /api/data-quality`: Dataset volume, missingness profile, and ML readiness gate report.

---

## 5. Model & Dataset Rollback Strategy

### Model Rollback
1. To roll back from `v002` to `v001`:
   - Set environment variable `ACTIVE_MODEL_VERSION=v001`.
   - Restart backend container: `docker compose restart backend`.
   - Model registry automatically loads and verifies `models/model_v001.joblib` with SHA-256 checksum.

### Dataset Rollback
1. Processed snapshots are versioned under `data/processed/`.
2. Database listings can be reverted by running Alembic migrations or restoring from point-in-time PostgreSQL backups.

---

## 6. Security Assumptions & Trade-offs

1. **Authentication:** Intentionally deferred. AutoValue valuation endpoints are designed as public pricing calculators. Abuse protection is handled via rate limiting and payload size restrictions.
2. **Rate Limiting:** Built-in in-memory sliding-window limiter is suitable for single-instance deployments. For horizontally scaled multi-pod deployments, configure an upstream reverse proxy (Nginx / Cloudflare) or Redis-backed limiter.
3. **Data Provenance:** Observed listing prices represent seller asking prices and do not constitute guaranteed buy/sell transaction values.
