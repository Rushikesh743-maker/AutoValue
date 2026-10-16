# AutoValue Phase 12 — Vehicle Risk & Trust Intelligence Engine

## 1. Overview & Objective

The **Vehicle Risk & Trust Intelligence Engine** provides deterministic, empirical, and multi-dimensional evaluations of the observable data and marketplace evidence surrounding any used vehicle valuation.

The engine answers the core question:
> **"How much observable/data-derived risk is associated with this vehicle valuation, and how trustworthy is the available marketplace evidence?"**

### Critical Architectural Distinction
AutoValue strictly maintains the boundary between:
1. **Machine Learning Predictive Estimate** (statistical fair value from XGBoost v002 and conformal intervals)
2. **Observed Marketplace Evidence** (empirical comparables, source feeds, median asking prices, price spreads)
3. **Unknown Physical Vehicle Condition** (unverified physical attributes such as engine health, transmission condition, accident history, flood damage, structural repairs, battery health, and odometer tampering)

> [!IMPORTANT]
> The Risk Engine does **NOT** compute a "probability of fraud", "accident probability", or "mechanical failure probability". It evaluates **Observable Market & Evidence Risk**.

---

## 2. Design Hierarchy

```
Observed Evidence (Market listings, source diversity, completeness, conformal interval)
       │
       ▼
Derived Risk Signals (Price anomaly %, km/yr deviations, liquidity density, dispersion)
       │
       ▼
Risk Factors (9 deterministic dimensions evaluated into normalized 0–100 scores)
       │
       ▼
Composite Risk Score (Deterministic weighted sum: 0–100)
       │
       ▼
Risk Classification (VERY_LOW, LOW, MODERATE, HIGH, VERY_HIGH, INSUFFICIENT_EVIDENCE)
       │
       ▼
Evidence & Explanations (Mathematical factor breakdowns, positive & risk signals)
       │
       ▼
Physical Condition Unknowns (Explicit unverified mechanical and structural disclaimers)
```

---

## 3. The 9 Evaluated Risk Dimensions & Weights

The composite risk score is computed using deterministic weights totaling 100%:

| Dimension Key | Dimension Name | Weight | Purpose & Evaluation Methodology |
| :--- | :--- | :---: | :--- |
| `price_anomaly` | **Price Anomaly Risk** | **20%** | Measures divergence of asking price from ML estimated fair value and market median. Penalizes extreme undervaluation (-15% to -30%) and extreme overpricing (+25%+). |
| `mileage_usage` | **Mileage / Usage Risk** | **15%** | Evaluates absolute mileage, vehicle age, normalized annual usage (`km_per_year` vs Indian average 12,000–15,000 km/yr), and ratio against comparable median mileage. |
| `vehicle_age` | **Vehicle Age Risk** | **10%** | Evaluates age-related market risk, market segment depreciation curves, and model obsolescence. |
| `market_liquidity` | **Market Liquidity Risk** | **15%** | Evaluates comparable listing count, segment transaction density, and variant availability across markets. |
| `data_quality` | **Data Quality Risk** | **10%** | Assesses attribute completeness (variant, transmission, fuel, engine displacement, location, seller type) reusing the Data Confidence Engine. |
| `market_evidence` | **Market Evidence Risk** | **10%** | Analyzes reliability and depth of supporting market listings, source diversity, and empirical consistency. |
| `valuation_uncertainty` | **Valuation Uncertainty** | **10%** | Evaluates the relative width of the 80% conformal prediction interval $((High - Low) / EstimatedValue)$. |
| `price_dispersion` | **Price Dispersion Risk** | **5%** | Analyzes the observed price variance and interquartile spread $(P75 - P25) / Median$ across active listings. |
| `source_concentration` | **Source Concentration** | **5%** | Measures single-source dependency via Herfindahl-Hirschman concentration index across listing platforms (e.g. Spinny, Cars24, CarWale, Olx, Truebil). |

---

## 4. Score Interpretation & Severities

```
 0 – 19   : VERY_LOW
20 – 39   : LOW
40 – 59   : MODERATE
60 – 79   : HIGH
80 – 100  : VERY_HIGH
```

### Insufficient Evidence Handling
If critical marketplace evidence is missing (e.g., $N_{\text{comparables}} < 1$):
- **Risk Level**: `INSUFFICIENT_EVIDENCE`
- **Confidence**: `LOW`
- **Explanation**: Explicitly states that insufficient comparable listings exist to calculate an empirical risk assessment, preventing false certainty.

---

## 5. REST API Specifications

### 1. Direct Risk Analysis
`POST /api/risk`
- **Request**: Accepts vehicle specifications and optional `asking_price` (conforms to `ValuationRequestSchema`).
- **Response**: Returns `RiskAnalysisResponse` with composite score, level, confidence, 9 factor breakdowns, positive signals, risk signals, physical condition unknowns, and evidence summary.

### 2. Saved Valuation Risk Analysis
`GET /api/risk/{valuation_id}`
- **Request**: Path parameter `valuation_id`, with optional query param `share_token` for public reports.
- **Security**: Strict authentication and IDOR ownership verification. Non-owners cannot access private saved valuations.

### 3. Batch Candidate Risk Analysis
`POST /api/risk/batch`
- **Request**: `BatchRiskRequest` accepting up to 10 vehicle candidates.
- **Response**: `BatchRiskResponse` with vehicle-level risk scores, classifications, and top risk factors.

---

## 6. Physical Condition Unknowns Notice

Every risk report includes an unverified physical condition checklist:
- Engine condition not independently verified
- Transmission health not independently verified
- Accident and collision history not independently verified
- Structural chassis repairs not independently verified
- Flood or water damage not independently verified
- Odometer tampering / rollback not independently verified
- Tyre and brake pad condition not independently verified
- High-voltage battery health (EVs) not independently verified
