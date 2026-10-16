# AutoValue — Model Drift & Continuous Monitoring Architecture

**Generated:** 2026-10-02  
**Applicable Module:** `ml/monitoring/drift_detector.py`

---

## 1. Overview
The AutoValue Monitoring Module tracks data distribution shifts, feature drift, target drift, and model prediction drift between baseline training benchmarks (e.g. `v0.3`) and incoming live production batches or runtime requests.

---

## 2. Statistical Metrics Used

### A. Population Stability Index (PSI)
$$PSI = \sum_{i=1}^B (Actual\%_i - Expected\%_i) \times \ln\left(\frac{Actual\%_i}{Expected\%_i}\right)$$

**Interpretation Standard:**
- **$PSI < 0.10$**: **STABLE** (Negligible distribution change; no action needed).
- **$0.10 \le PSI < 0.25$**: **MODERATE DRIFT** (Slight shift; trigger telemetry warning).
- **$PSI \ge 0.25$**: **SIGNIFICANT DRIFT** (Substantial shift; recommend model review & retrain gate).

### B. Kolmogorov-Smirnov (KS) Test
- Evaluates maximum distance between empirical CDFs of baseline vs runtime continuous features (`km_driven`, `car_age`, `listed_price`).
- Flags drift if $p$-value $< 0.05$ and $KS > 0.15$.

---

## 3. Monitored Features
1. `km_driven` (Odometer distribution)
2. `car_age` / `year` (Vehicle age profile)
3. `km_per_year` (Usage intensity)
4. `listed_price` (Market price level)
5. `source` distribution (Source balance stability)

---

## 4. Retraining Protocol
AutoValue avoids arbitrary automatic retraining triggers. When `DRIFT_DETECTED` is flagged:
1. Ingestion Quality Report is generated.
2. Cross-source duplicate rate is audited.
3. ML Readiness Gate is evaluated on the newly collected batch.
4. If gate passes, model candidate training and 5-fold CV comparison are executed and logged to `experiments_registry.json`.
