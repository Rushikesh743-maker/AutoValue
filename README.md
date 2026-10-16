# AutoValue

### AI-Powered Used-Car Valuation and Market Intelligence Platform

AutoValue is an ML-powered pre-owned automotive valuation and market intelligence product. It collects real-world used-car listings from legitimate sources, standardizes and deduplicates records, finds comparable vehicles, predicts fair market values, and provides explainable valuation reports with prediction uncertainty bounds, historical market movements, SHAP feature attributions, personal valuation history snapshots, vehicle bookmarks, side-by-side comparison matrices, and secure public sharing.

---

## Important Market Principle & Limitations

> **Crucial Market Reality & Limitations:**
> 1. **Asking Prices vs. Completed Transactions**: AutoValue estimates market values from **observed listing asking prices** rather than closed transaction prices. Actual private sale or dealer exchange values may differ based on negotiation and physical vehicle condition.
> 2. **Rare Vehicle Segments**: Segments with limited market observations may carry wider uncertainty bounds.
> 3. **Dataset Distribution**: Model accuracy is bounded by the empirical distribution of verified training records.
> 4. **Estimates vs. Guarantees**: Market estimates reflect statistical model predictions and comparable benchmarks, not legally binding resale guarantees.

---

## Core Features

- **ML-Based Valuation Engine**: Tuned XGBoost regressor predicting fair market values from vehicle attributes (brand, model, variant, year, fuel, transmission, odometer km, city, engine cc, etc.).
- **Comparable Vehicle Analysis**: Fast similarity matching against 999 processed listings with percentage similarity scoring and source transparency.
- **Market Statistics**: Aggregated median, mean, min, max, 25th/75th percentiles, and asking price variance.
- **Prediction Uncertainty Bounds**: Conformal empirical residual prediction intervals (80% confidence level).
- **SHAP Explanations**: Feature attribution explaining individual feature contributions (positive/negative price impact in INR).
- **Historical Market Trends**: Longitudinal price trends and depreciation tracking across market quarters.
- **Model Drift & Data Quality Monitoring**: Population Stability Index (PSI), Kolmogorov-Smirnov (KS) feature drift checks, and ingestion data health metrics.
- **User Authentication & Profiles**: Secure registration, login, profile management, and account deletion with bcrypt password hashing and dual JWT / HTTP-only cookie sessions.
- **Saved Valuations & History**: Immutable valuation result snapshots with paginated history and IDOR protection.
- **Vehicle Bookmarking**: Bookmark favorite vehicle configurations for instant re-valuation.
- **Side-by-Side Comparison**: Multi-vehicle comparison matrix calculating factual empirical deltas without subjective bias.
- **Cryptographic Shareable Reports**: Unguessable 256-bit URL-safe share tokens with sanitized, zero-PII public report views and real-time revocation.
- **Market Forecasting & Buy/Sell Timing (Phase 14)**: Multi-horizon (30D, 90D, 180D, 365D) temporal price trend extrapolation, volatility classification, empirical depreciation trajectories, deterministic conservative/base/optimistic forecast corridors, and explainable buy/sell timing scores (0-100) with strict refusal on insufficient evidence.
- **Vehicle Lifecycle & Ownership Decision Intelligence (Phase 15)**: Six-pillar lifecycle recommendation engine (`BUY`, `KEEP`, `SELL_NOW`, `WAIT`, `REPLACE`, `INSUFFICIENT_EVIDENCE`), decision margin analysis, horizon outlooks, counterfactual scenario simulation, and candidate replacement discovery.
- **Garage & Portfolio Intelligence Engine (Phase 16)**: Multi-vehicle personal ownership intelligence, aggregate market value and 5Y TCO modeling, 6-component Garage Efficiency Scoring (0-100), Sell-First vs Keep-First priority rankings, pairwise functional redundancy detection, candidate replacement analysis with deterministic break-even calculations, and interactive what-if consolidation/replacement scenarios.
- **Privacy & Self-Service Erasure**: Right-to-erasure account deletion cascading across all personal data.

---

## API Summary

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/auth/register` | `POST` | Public | Register new user with bcrypt-hashed password |
| `/api/auth/login` | `POST` | Public | Authenticate user, receive JWT & HTTP-only cookie |
| `/api/auth/logout` | `POST` | Public | Clear active authentication session |
| `/api/auth/me` | `GET` | User | Retrieve current user profile |
| `/api/auth/me` | `PUT` | User | Update user profile |
| `/api/auth/me` | `DELETE` | User | Self-service account & data deletion |
| `/api/valuation` | `POST` | Public | Run live ML valuation for vehicle specifications |
| `/api/market/forecast` | `GET` | Public | Retrieve temporal market forecast & buy/sell timing |
| `/api/market/forecast` | `POST` | Public | Body-based market forecast & timing evaluation |
| `/api/market/forecast/{id}` | `GET` | User / Token | Forecast anchored to saved valuation (IDOR-protected) |
| `/api/market/forecast/batch` | `POST` | Public | Bounded batch market forecast (up to 10 vehicles) |
| `/api/lifecycle/decision` | `POST` | Public | Comprehensive 6-pillar vehicle lifecycle decision |
| `/api/lifecycle/{id}` | `GET` | User / Token | Lifecycle decision anchored to saved valuation |
| `/api/lifecycle/scenario` | `POST` | Public | Counterfactual what-if lifecycle scenario simulation |
| `/api/lifecycle/compare` | `POST` | Public | Vehicle replacement comparison matrix |
| `/api/lifecycle/batch` | `POST` | Public | Bounded batch lifecycle decision evaluation |
| `/api/garage` | `GET` | User | List all vehicles in user's personal garage |
| `/api/garage` | `POST` | User | Add vehicle to personal garage |
| `/api/garage/intelligence` | `GET` | User | Complete multi-vehicle portfolio economic intelligence |
| `/api/garage/{id}` | `GET` | User | Retrieve single garage vehicle (IDOR-protected) |
| `/api/garage/{id}/intelligence` | `GET` | User | Single garage vehicle intelligence snapshot |
| `/api/garage/{id}` | `PATCH` | User | Update garage vehicle specifications & usage |
| `/api/garage/{id}` | `DELETE` | User | Remove vehicle from garage |
| `/api/garage/scenario` | `POST` | User | Interactive what-if garage scenario simulation |
| `/api/garage/compare` | `POST` | User | Multi-vehicle garage comparison matrix (up to 10) |
| `/api/valuations` | `GET` | User | List user's valuation history with pagination |
| `/api/valuations` | `POST` | User | Save immutable valuation result snapshot |
| `/api/valuations/{id}` | `GET` | User | Retrieve single saved valuation detail (IDOR-protected) |
| `/api/valuations/{id}` | `DELETE` | User | Delete saved valuation snapshot |
| `/api/valuations/{id}/share` | `POST` | User | Generate/activate public share token |
| `/api/valuations/{id}/share` | `DELETE` | User | Revoke public report sharing |
| `/api/shared/{token}` | `GET` | Public | Retrieve sanitized public valuation report |
| `/api/saved-vehicles` | `GET` | User | List user's bookmarked vehicles |
| `/api/saved-vehicles` | `POST` | User | Bookmark vehicle configuration |
| `/api/saved-vehicles/{id}` | `DELETE` | User | Delete vehicle bookmark |
| `/api/compare` | `POST` | User | Compare 2-3 saved vehicles/valuations with empirical deltas |
| `/api/tco` | `POST` | Public | 5-year total cost of ownership & resale analysis |
| `/api/tco/{id}` | `GET` | User / Token | TCO anchored to saved valuation |
| `/api/risk` | `POST` | Public | Observable vehicle risk score & anomaly detection |
| `/api/health` | `GET` | Public | Liveness health check |
| `/api/ready` | `GET` | Public | Deep readiness probe (DB, Model SHA-256, dataset) |
| `/api/models` | `GET` | Public | Model registry & deployed versions |
| `/api/models/drift` | `GET` | Public | PSI & KS feature drift monitoring report |
| `/api/data-quality` | `GET` | Public | Ingestion data quality metrics |
| `/metrics` | `GET` | Public | Prometheus observability metrics |

---

## Running Locally

### 1. Backend Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run database migrations
alembic upgrade head

# 3. Run complete test suite
python -m pytest -v

# 4. Start backend server
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

- Backend API: `http://127.0.0.1:8000`
- Interactive Swagger Docs: `http://127.0.0.1:8000/api/docs`

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run TypeScript & Vite production build
npm run build

# Start development server
npm run dev
```

- Frontend Web App: `http://localhost:5173`

### 3. Docker Compose (Full Production-Like Stack)

```bash
# Validate Docker Compose configuration
docker compose config

# Build and start PostgreSQL, Backend, and Frontend containers
docker compose up -d --build

# Verify services
curl -f http://localhost:8000/api/health
curl -f http://localhost:8000/api/ready
```

---

## Production Deployment & Governance

- **Deployment Runbook**: See [`docs/deployment.md`](docs/deployment.md) for complete step-by-step guides across PaaS (Render, Railway, Fly.io) and IaaS/VPS (Docker Compose, AWS, Azure, GCP).
- **Privacy & Retention Policy**: See [`docs/privacy.md`](docs/privacy.md) for data governance, right-to-erasure, and anonymization protocols.
- **Production Audit Report**: See [`docs/production_readiness_audit.md`](docs/production_readiness_audit.md) for the complete 15-point readiness audit.
