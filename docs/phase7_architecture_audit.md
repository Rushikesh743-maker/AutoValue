# AutoValue — Phase 7 Architecture & Production Readiness Audit

**Audit Date:** 2026-10-02  
**Baseline State:** Phase 6 Complete ($N=999$ processed unique records, dataset `v0.3`, active model `v002` XGBoost Regressor, 73 passing tests).

---

## 1. System Architecture Overview

AutoValue is an ML-powered vehicle valuation intelligence platform structured into distinct functional domains:

```text
[Data Sources] (Open Research, Dealer Feeds, Community Portals, Commercial APIs)
       │
       ▼ (data_pipeline/)
[Ingestion & Normalization] -> [Deduplication & Validation] -> [PostgreSQL DB (or SQLite fallback)]
       │
       ▼ (ml/)
[Feature Engineering] -> [Preprocessor & XGBoost/RF v002] -> [TreeExplainer SHAP]
       │
       ▼ (backend/app/services/)
[Valuation Orchestration Service] <──> [Comparable Service] <──> [Historical Market Service]
       │
       ▼ (backend/app/api/routes/)
[FastAPI REST API] (CORS, Validation, Telemetry)
       │
       ▼
[React 19 + TypeScript Frontend] (Vite, TailwindCSS, Recharts)
```

---

## 2. Existing Services & Domain Modules

| Domain | Service / Module | File Path | Current Status |
| :--- | :--- | :--- | :--- |
| **Valuation** | `ValuationService` | `backend/app/services/valuation_service.py` | Operational; coordinates inference, uncertainty intervals, comparables, and SHAP. |
| **Comparables** | `ComparableService` | `backend/app/services/comparable_service.py` | Operational; multi-attribute similarity scoring (price-independent), P25-P75 range. |
| **Market History** | `HistoricalMarketService` | `backend/app/services/historical_market_service.py` | Operational; monthly time-series price aggregations and movement delta. |
| **Ingestion** | `IngestionService` | `data_pipeline/services/ingestion_service.py` | Operational; multi-source collector runner with duplicate detection. |
| **ML Inference** | `AutoValuePredictor` | `ml/inference/predictor.py` | Operational; cached loading of versioned model and ColumnTransformer. |
| **Explainability** | `AutoValueSHAPExplainer` | `ml/evaluation/shap_explainer.py` | Operational; TreeExplainer for feature price attributions in INR. |
| **Uncertainty** | `PredictionUncertaintyEstimator` | `ml/evaluation/uncertainty.py` | Operational; empirical residual quantile 80% error bound calibration. |
| **Drift Monitoring** | `DriftDetector` | `ml/monitoring/drift_detector.py` | Operational; Population Stability Index (PSI) and Kolmogorov-Smirnov (KS) statistics. |

---

## 3. Existing API Endpoints

| Method | Endpoint | Handler | Current Functionality |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | `health.py` | Returns basic service status and project name. |
| `POST` | `/api/valuation` | `valuation.py` | End-to-end vehicle valuation returning ML estimate, uncertainty interval, comparables, SHAP, and position. |
| `GET` | `/api/market/history` | `market.py` | Aggregated monthly asking price history and observed changes. |
| `GET` | `/api/models` | `models.py` | Returns active model metadata, evaluation metrics, and candidate registry. |
| `GET` | `/api/sources` | `sources.py` | Compliance and metadata registry for authorized data sources. |
| `GET` | `/api/comparables` | `comparables.py` | Reserved route (placeholder). |
| `POST` | `/api/explain` | `explain.py` | Reserved route (placeholder). |

---

## 4. Database Access Pattern
- **ORM:** SQLAlchemy 2.0 with PostgreSQL (`psycopg3` driver) and automatic SQLite fallback (`data/autovalue.db`) for offline local development.
- **Session Lifecycle:** `get_db()` FastAPI dependency yielding `SessionLocal()`.
- **Indexing:** Composite indexes exist on `(brand, model, year)`, `(brand, model, city)`, `(brand, model, date_collected)`, and `(source, listing_id)`.
- **Gap Identified:** Connection pool sizing, pool pre-ping, connection recycle timeouts, and rollback handlers need formal hardening. Alembic migrations are not yet initialized.

---

## 5. Model Loading & Lifecycle Mechanism
- **Model Storage:** Versioned serialized joblib artifacts (`models/model_v001.joblib`, `models/model_v002.joblib`) with associated preprocessors and metadata JSONs.
- **Loading:** Loaded at instantiation and cached in memory.
- **Gap Identified:** Need a unified `ModelRegistry` service verifying SHA-256 artifact integrity against corruption or tampering before deployment.

---

## 6. Configuration Mechanism
- **Pydantic Settings:** `backend/app/core/config.py` using `SettingsConfigDict` reading from `.env`.
- **Gap Identified:** Need strict validation to prevent hardcoded defaults in production environments (e.g. strict secret checks, rate limiting settings, payload size bounds).

---

## 7. Frontend / Backend Communication
- **Frontend Stack:** React 19, TypeScript, Vite, TailwindCSS, Recharts.
- **Gap Identified:** Individual pages (`ValuationPage`, `ResultsPage`) perform direct `fetch()` calls. A centralized, typed API client (`frontend/src/services/api.ts`) with timeout handling, request ID propagation, and global error handling is required.

---

## 8. Error Handling & Logging
- **Logging:** Standard Python logging used across modules; lacks uniform correlation IDs (`X-Request-ID`) and structured JSON logs.
- **Error Handling:** Route-level `try/except` and FastAPI default exception handlers. Needs centralized exception handlers returning uniform error envelopes.

---

## 9. Current Test Coverage
- **73 tests passing (100%)** covering data cleaners, normalizers, deduplication, feature engineering, transformers, ML training, splits, SHAP, inference, uncertainty, drift monitoring, historical market, and API endpoints.

---

## 10. Production Deployment Gaps to Address in Phase 7

1. **Security:** Missing rate limiting on `POST /api/valuation`, strict CORS enforcement, and request payload size caps.
2. **Observability:** Missing structured JSON logs, `X-Request-ID` correlation middleware, Prometheus-compatible `/metrics`, and telemetry recorder.
3. **Artifact Integrity:** Missing SHA-256 verification and active model registry abstraction.
4. **Health & Readiness:** Need separate `/api/ready` endpoint validating DB and model artifact availability.
5. **Database:** Missing Alembic migration framework and connection pool configuration.
6. **Data Monitoring APIs:** Missing `GET /api/data-quality` and `GET /api/models/drift` endpoints.
7. **Frontend Hardening:** Missing centralized API client, retry capabilities, and fallback UI states.
8. **Deployment & CI:** Missing production-ready multi-stage Dockerfile with non-root user and GitHub Actions CI workflow.
