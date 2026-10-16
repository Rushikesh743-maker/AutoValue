# AutoValue Decision Intelligence Architecture (Phase 11)

## 1. System Architecture Overview

Phase 11 transforms AutoValue into a comprehensive **Automotive Decision Intelligence Platform**. It layers deterministic analytical services, multi-attribute scoring engines, non-destructive counterfactual simulators, alternative discovery algorithms, and temporal tracking onto the established XGBoost v002 valuation foundation.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Client Layer (React / Vite)                           │
│  - /intelligence (12-Section Decision Dashboard)                                │
│  - ResultsPage.tsx (Decision Intelligence CTA Card)                             │
│  - Watchlist Management UI (Live Track & Refresh)                               │
└──────────────────────────────────────┬──────────────────────────────────────────┘
                                       │ HTTP / JSON
┌──────────────────────────────────────▼──────────────────────────────────────────┐
│                            FastAPI Application Router                            │
│  - POST /api/intelligence (Unified Decision Intelligence Suite)                  │
│  - POST /api/scenario (XGBoost What-If Simulator)                               │
│  - POST /api/alternatives (Closest Evidence-Supported Alternatives)             │
│  - GET  /api/market/timing (Historical Movement & Trajectory)                    │
│  - POST /api/compare (Multi-Factor Vehicle Deltas)                              │
│  - GET/POST/PATCH /api/watchlist (Authenticated User Bookmarks)                 │
└──────┬──────────────┬──────────────┬──────────────┬──────────────┬──────────────┘
       │              │              │              │              │
┌──────▼──────┐┌──────▼──────┐┌──────▼──────┐┌──────▼──────┐┌──────▼──────┐
│ DealAnalysis││ Negotiation ││  ValueScore ││DataConfidence││ScenarioEngine│
│   Service   ││   Service   ││   Service   ││   Service    ││   Service    │
└──────┬──────┘└──────┬──────┘└──────┬──────┘└──────┬──────┘└──────┬──────┘
       │              │              │              │              │
       └──────────────┴──────────────┼──────────────┴──────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────────────────┐
│                             Core Engine Services                                │
│  - ValuationService (XGBoost v002 Inference, SHAP Attributions, Uncertainty)    │
│  - ComparableService (Distance-Weighted Empirical Listings)                     │
│  - HistoricalMarketService (Temporal Price Distributions)                       │
│  - Telemetry & Observability (Prometheus Metrics & Structured Logging)          │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Modules Summary

1. **`DealAnalysisService` (`backend/app/services/deal_analysis_service.py`)**:
   Deterministic pricing classification (`SIGNIFICANTLY_BELOW_MARKET`, `BELOW_MARKET`, `FAIRLY_PRICED`, `ABOVE_MARKET`, `SIGNIFICANTLY_ABOVE_MARKET`, `INSUFFICIENT_EVIDENCE`) based on strict interquartile and model-gap thresholds.

2. **`NegotiationService` (`backend/app/services/negotiation_service.py`)**:
   Produces aggressive, evidence-supported, and conservative target corridors alongside structured talking points and leverage assessment.

3. **`ValueScoreService` (`backend/app/services/value_score_service.py`)**:
   Transparent, composite 0–100 index combining price advantage (40%), mileage intensity (25%), vehicle age (15%), and market evidence density (20%).

4. **`DataConfidenceService` (`backend/app/services/data_confidence_service.py`)**:
   Data quality scoring and explicit enumeration of physical condition factors that AutoValue does not inspect (engine health, accident history, flood damage, tyre wear).

5. **`ScenarioService` (`backend/app/services/scenario_service.py`)**:
   Active XGBoost counterfactual simulation allowing instant "What-If" parameter modifications without database mutation.

6. **`AlternativeVehicleService` (`backend/app/services/alternative_vehicle_service.py`)**:
   Multi-criteria search engine ranking real dataset candidates by budget proximity, mileage, age, and attribute completeness.

7. **`MarketTimingService` (`backend/app/services/market_timing_service.py`)**:
   Historical asking-price momentum analysis with direction indicators (`RISING`, `STABLE`, `DECLINING`, `INSUFFICIENT_DATA`).

8. **Watchlist & Tracking (`backend/app/api/routes/watchlist.py`, Alembic Migration `003`)**:
   Authenticated bookmarking with status tracking (`watching`, `interested_in_selling`, `interested_in_buying`) and live valuation re-calculation.

---

## 3. Telemetry & Observability Integration

Prometheus counters and histograms registered in `backend/app/services/telemetry.py`:
- `autovalue_deal_analysis_total`: Classification counts labeled by outcome.
- `autovalue_scenario_requests_total`: Counter for scenario simulations.
- `autovalue_alternative_search_total`: Counter for alternative vehicle discovery queries.
- `autovalue_watchlist_refresh_total`: Counter for user watchlist valuation refreshes.
- `autovalue_intelligence_latency_seconds`: Latency distribution histogram for composite decision intelligence calculations.

---

## 4. Security & Access Controls
- **Zero Regressions**: Preserves all Phase 7–10 JWT auth, password hashing, CORS, rate limits, and payload size bounds.
- **IDOR Protection**: Strict user-ownership validation on all watchlist endpoints (`/api/watchlist`, `/api/watchlist/{id}/refresh`, `/api/watchlist/{id}/status`).
- **Data Privacy**: Decision intelligence queries remain stateless unless explicitly saved to user account.
