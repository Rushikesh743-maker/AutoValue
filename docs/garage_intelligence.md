# AutoValue — Phase 16: Garage & Portfolio Intelligence Engine

## 1. Executive Summary

AutoValue Phase 16 introduces the **Garage & Portfolio Intelligence Engine**, extending the platform from single-vehicle valuations into a comprehensive multi-vehicle ownership intelligence system.

A user's **Garage** represents their personal fleet of vehicles (owned, considering, watching, or sold). The **Portfolio Intelligence Engine** aggregates their economic footprint, models total costs of ownership (TCO), analyzes cost per kilometer, evaluates sell-first vs keep-first priority rankings, identifies functional and segment redundancies, discovers market replacement opportunities, and provides interactive counterfactual what-if scenario simulations.

---

## 2. Terminology & Conceptual Model

- **Garage**: The authenticated user's private collection of vehicles.
- **Portfolio**: The aggregate economic and market analysis derived from all active vehicles in the user's garage.
- **Vehicle**: An individual automotive asset in the garage with known identity, odometer, annual usage, and purchase history.
- **Transportation Asset**: We explicitly treat vehicles as depreciating transportation assets rather than speculative financial assets.

---

## 3. Architecture & Engine Orchestration

The Garage Engine orchestrates existing production services without duplicating financial formulas:

```
+-----------------------------------------------------------------------------------+
|                            Individual Vehicle Models                              |
|   ValuationService | RiskService | TCOService | ForecastService | LifecycleService|
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
|                        GarageVehicleSnapshot Engine                               |
|   • Live Fair Value Estimation                                                    |
|   • 5Y Net TCO & Resale Forecast                                                  |
|   • Cost per Kilometer & Monthly Mileage                                          |
|   • Risk Score & Market Momentum                                                  |
|   • Lifecycle Action & Score (BUY / KEEP / SELL_NOW / WAIT / REPLACE)             |
|   • Provenance Tagging (OBSERVED / DERIVED / FORECAST / USER_DEFINED)             |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
|                      Garage Aggregation & Analytics Engine                        |
|   • Total Market Value (Sum)                                                      |
|   • Total Annual Ownership Cost & 5Y TCO (Sum)                                    |
|   • Average Cost per KM & Resale Recovery                                         |
|   • Value-Weighted Risk Score & Market Momentum                                   |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
|                       Portfolio Intelligence & Strategy                           |
|   • Garage Efficiency Score (0-100, 6 Transparent Pillars)                        |
|   • Sell-First Priority Ranking (0-100 Score with Factor Analysis)                |
|   • Keep-First Retention Ranking (0-100 Score with Operating Merits)              |
|   • Pairwise Vehicle Redundancy Detection (Segment / Powertrain / Usage Overlap)  |
|   • Alternative Vehicle Replacement Analysis (with Break-Even Months)             |
|   • What-If Scenario Simulator (Sell / Replace / Update Mileage / Add Vehicle)    |
|   • Portfolio Action Recommendation (KEEP / SELL / REPLACE / CONSOLIDATE)         |
+-----------------------------------------------------------------------------------+
```

---

## 4. Garage Efficiency Score Methodology

The **Garage Efficiency Score** is a transparent 0–100 index evaluated across 6 weighted dimensions:

| Component | Weight | Target / Optimal State | Description |
|---|---|---|---|
| **Ownership Economics** | 30% | Low cost per km, optimized operating expenditure | Measures how cost-effective the fleet is to operate relative to standard benchmarks. |
| **Fleet Utilization** | 20% | High mileage per vehicle, no idle capital | Evaluates whether vehicles are actively utilized (>=12,000 km/yr) vs under-utilized. |
| **Risk Mitigation** | 15% | Low mechanical, history, and dispersion risk | Weighted average fleet risk score and trust reliability. |
| **Market Position & Momentum** | 15% | Favorable market timing and rising/stable trends | Avoids holding vehicles experiencing severe cyclical market downturns. |
| **Resale Retention Strength** | 10% | High residual value preservation | Evaluates 5-year projected residual value percentages. |
| **Portfolio Redundancy** | 10% | Low functional overlap across garage assets | Penalizes duplicate daily-commuters or identical segment/fuel redundancies. |

---

## 5. Decision Algorithms

### 5.1 Sell-First Priority Ranking
Calculates a **Sell Priority Score (0–100)** to determine which vehicle in the portfolio creates the highest operating drag or has the most favorable immediate exit window:
- Favorable sell-timing signal (+25 pts)
- High projected annual depreciation decline >=12% (+20 pts)
- Annual ownership cost exceeding garage average (+15 pts)
- High vehicle risk score >=45 (+15 pts)
- Lifecycle `SELL_NOW` recommendation (+20 pts)
- Downward market trend (+10 pts)

### 5.2 Keep-First Retention Ranking
Calculates a **Keep Priority Score (0–100)** highlighting vehicles with the best long-term retention economics:
- Low cost per kilometer <= ₹8.0/km (+25 pts)
- Low risk score <= 30 (+20 pts)
- Stable or rising market trend (+15 pts)
- Lifecycle `KEEP` recommendation (+20 pts)
- Low annual operating cost below garage average (+15 pts)

### 5.3 Vehicle Redundancy Detection
Evaluates pairwise vehicles $V_A$ and $V_B$ on:
1. **Body Segment Overlap**: Same segment / body style.
2. **City Overlap**: Operating in the same metropolitan area.
3. **Usage Overlap**: Low individual utilization indicating shared utility.
4. **Powertrain Overlap**: Same fuel type and transmission.

Classified into `HIGH`, `MODERATE`, `LOW`, or `INSUFFICIENT_EVIDENCE`.

### 5.4 Replacement Opportunity & Break-Even
For owned vehicles, searches candidate replacement listings using `AlternativeVehicleService` and calculates:
- Purchase capital delta ($\Delta P = P_{\text{replacement}} - P_{\text{current}}$)
- 5-Year TCO savings ($\Delta \text{TCO}$)
- Annual operating cost difference ($\Delta \text{Annual}$)
- Resale advantage ($\Delta R_{5Y}$)
- **Break-Even Months**:
  $$\text{Break Even Months} = \frac{\Delta P}{\frac{|\Delta \text{Annual}|}{12}}$$
  *(Only computed when annual savings $\Delta \text{Annual} < 0$ and $\Delta P > 0$; otherwise returns `null` or `0.0`)*

---

## 6. Security & IDOR Protections

1. **Authentication Required**: All endpoints require a valid JWT bearer token.
2. **Strict User Isolation**: Every database query filters by `user_id == current_user.id`.
3. **IDOR Defense**:
   - Accessing another user's vehicle ID returns `HTTP 403 Forbidden` (`detail="Access forbidden: You do not own this garage vehicle."`).
   - Requesting non-existent vehicle IDs returns `HTTP 404 Not Found`.
   - Batch / Compare / Scenario requests validating multiple vehicle IDs verify all IDs belong to `current_user.id` or reject with `403`.
4. **Batch Limits**: Comparison and Scenario endpoints enforce maximum 10 vehicles per request.

---

## 7. API Reference

| Method | Path | Description | Access |
|---|---|---|---|
| `POST` | `/api/garage` | Create new garage vehicle | Authenticated |
| `GET` | `/api/garage` | List all garage vehicles for user | Authenticated |
| `GET` | `/api/garage/intelligence` | Full portfolio economic intelligence | Authenticated |
| `GET` | `/api/garage/{id}` | Get single vehicle details | Authenticated (Owner) |
| `GET` | `/api/garage/{id}/intelligence` | Single vehicle intelligence snapshot | Authenticated (Owner) |
| `PATCH` | `/api/garage/{id}` | Update garage vehicle | Authenticated (Owner) |
| `DELETE` | `/api/garage/{id}` | Remove vehicle from garage | Authenticated (Owner) |
| `POST` | `/api/garage/scenario` | What-if portfolio scenario simulator | Authenticated |
| `POST` | `/api/garage/compare` | Multi-vehicle comparison matrix | Authenticated |

---

## 8. Data Provenance & Integrity

Every portfolio metric includes an explicit provenance descriptor:
- `current_estimated_value`: `DERIVED` (XGBoost v002 valuation model)
- `five_year_tco`: `DERIVED` (deterministic TCO engine)
- `projected_5y_resale`: `FORECAST` (empirical depreciation curve)
- `annual_km`: `USER_DEFINED` (or default fallback 12,000 km/yr)
- `market_trend`: `DERIVED` (historical listing observations)
- `lifecycle_action`: `DERIVED` (multi-criteria lifecycle decision engine)
