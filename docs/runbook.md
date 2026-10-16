# AutoValue — Operational Incident Runbook

This runbook provides diagnostic and remediation procedures for common operational failure modes in AutoValue.

---

## Scenario 1: API Is Down / Unresponsive

### Symptoms
- Liveness check `GET /api/health` times out or returns HTTP 502/504 from reverse proxy.
- Frontend displays network error banner.

### Diagnostic Steps
1. Check container process status:
   ```bash
   docker compose ps backend
   ```
2. Inspect recent backend error logs:
   ```bash
   docker compose logs backend --tail=100
   ```
3. Test direct container connectivity:
   ```bash
   curl -I http://127.0.0.1:8000/api/health
   ```

### Recovery Steps
1. If the process crashed due to an unhandled exception or OOM, restart the container:
   ```bash
   docker compose restart backend
   ```
2. Verify startup logs confirm model loading:
   ```bash
   docker compose logs backend | grep "Successfully loaded"
   ```

---

## Scenario 2: Database Unavailable / Connection Errors

### Symptoms
- Readiness check `GET /api/ready` returns HTTP 503 with `"checks": {"database": false}`.
- Telemetry logs display `DATABASE_UNAVAILABLE` or `DatabaseConnectionError`.

### Diagnostic Steps
1. Check PostgreSQL container health:
   ```bash
   docker compose ps postgres
   ```
2. Verify connection from host:
   ```bash
   pg_isready -h localhost -p 5432 -U postgres -d autovalue
   ```
3. Inspect PostgreSQL logs:
   ```bash
   docker compose logs postgres --tail=100
   ```

### Recovery Steps
1. If PostgreSQL container is stopped, restart it:
   ```bash
   docker compose up -d postgres
   ```
2. Verify connection pool parameters in `.env` (`DB_POOL_SIZE=5`, `DB_MAX_OVERFLOW=10`, `DB_POOL_TIMEOUT=30`).
3. Re-check readiness:
   ```bash
   curl http://127.0.0.1:8000/api/ready
   ```

---

## Scenario 3: Model Artifact Missing

### Symptoms
- Readiness check `GET /api/ready` returns HTTP 503 with `"active_model_artifacts": false`.
- Log entry: `ModelNotFoundError: Model artifact 'models/model_v002.joblib' not found.`

### Diagnostic Steps
1. Inspect files in the `models/` directory:
   ```bash
   ls -la models/
   ```
2. Check configured model version in `.env`:
   ```bash
   cat .env | grep ACTIVE_MODEL_VERSION
   ```

### Recovery Steps
1. If artifacts were deleted or not mounted into container, re-run training pipeline to generate v002:
   ```bash
   python ml/training/train_v002.py
   ```
2. Or roll back to baseline model v001 by updating `.env`:
   ```bash
   ACTIVE_MODEL_VERSION=v001
   ```
3. Restart API service.

---

## Scenario 4: Model Checksum Mismatch (Integrity Failure)

### Symptoms
- API startup failure or readiness probe returns HTTP 503.
- Log entry: `ModelIntegrityError: Model artifact v002 checksum verification failed.`

### Diagnostic Steps
1. Compute actual SHA-256 of artifact on disk:
   ```bash
   sha256sum models/model_v002.joblib
   ```
2. Compare with `artifact_integrity.model_sha256` in `models/metadata_v002.json`.

### Recovery Steps
1. If artifact was modified or corrupted in transit, restore from trusted Git tag or re-execute `python ml/training/train_v002.py`.
2. Do not manually bypass checksum verification in production.

---

## Scenario 5: Valuation Latency Increases

### Symptoms
- `POST /api/valuation` latency exceeds 500ms.
- High request latency recorded in Prometheus metrics (`/metrics`).

### Diagnostic Steps
1. Query `/metrics` to identify latency breakdown:
   - Check `autovalue_http_requests_total`
   - Check access log `latency_ms` field.
2. Verify CPU and Memory utilization:
   ```bash
   docker stats autovalue-backend
   ```
3. Test if comparable search or SHAP tree explainability is the bottleneck.

### Recovery Steps
1. If under high concurrent traffic, increase Uvicorn worker count in `docker/Dockerfile.backend` (`--workers 4`).
2. Verify PostgreSQL composite indexes are active:
   ```sql
   SELECT indexname FROM pg_indexes WHERE tablename = 'car_listings';
   ```

---

## Scenario 6: Model Drift Warning Appears

### Symptoms
- `GET /api/models/drift` returns `"status": "warning"` and `drifted_features_count > 0`.

### Diagnostic Steps
1. Inspect the drift report details:
   ```bash
   curl -s http://127.0.0.1:8000/api/models/drift | jq .feature_audits
   ```
2. Check which features exceeded the Population Stability Index (PSI) threshold (`PSI >= 0.25`).

### Recovery Steps
1. Collect latest market listings via ingestion pipeline:
   ```bash
   python data_pipeline/run_transformations.py
   ```
2. Retrain model candidate against updated dataset partition:
   ```bash
   python ml/training/train_v002.py
   ```
3. Evaluate test MAE and CV stability before promoting new candidate.

---

## Scenario 7: Data Quality Degradation

### Symptoms
- `GET /api/data-quality` reports `ml_readiness.is_ready: false` or high missingness.

### Diagnostic Steps
1. Query dataset quality endpoint:
   ```bash
   curl -s http://127.0.0.1:8000/api/data-quality | jq .missingness_summary
   ```
2. Inspect ingestion logs for collector rejections or source format alterations.

### Recovery Steps
1. Run dataset cleaner and transformer:
   ```bash
   python data_pipeline/run_transformations.py
   ```
2. Verify `data/processed/autovalue_processed.csv` reaches minimum volume ($N \ge 800$) and target feature completeness.

---

## Scenario 8: Frontend Cannot Reach Backend

### Symptoms
- Frontend shows "Valuation Unavailable: Network connection failed. Backend service may be unreachable."

### Diagnostic Steps
1. Check browser console network tab for CORS errors or connection refused.
2. Verify `VITE_API_URL` configuration in frontend environment.
3. Check `CORS_ORIGINS` in backend configuration.

### Recovery Steps
1. Ensure `CORS_ORIGINS` in `.env` includes the frontend origin:
   ```env
   CORS_ORIGINS=http://localhost:5173,http://localhost:80,http://127.0.0.1:5173,http://127.0.0.1:80
   ```
2. Restart backend to reload CORS settings.
