# AutoValue — Prediction Uncertainty & Interval Methodology

**Generated:** 2026-10-02  
**Applicable Models:** `v001`, `v002`

---

## 1. Core Principle: Disentangling Uncertainty from Market Spread

AutoValue explicitly distinguishes between two separate statistical concepts:

1. **ML Model Uncertainty (`model_interval`)**:
   - Quantifies the statistical variance and potential error bounds of the regression estimator $\hat{f}(X)$ for a specific vehicle attribute vector $X$.
   - Derived directly from cross-validation / validation residual distributions and tree ensemble variance.
2. **Observed Comparable Range (`market_range`)**:
   - Represents the empirical price dispersion ($P_{25} \to P_{75}$) of actual comparable vehicle listings active across monitored sources.

---

## 2. Uncertainty Methodologies Evaluated

### Methodology A: Empirical Residual Quantile Calibration (Conformal Bound)
- On held-out validation / test folds, empirical absolute residuals $e_i = |y_i - \hat{y}_i|$ are recorded.
- The 80th percentile residual bound $q_{0.80}$ is determined:
  $$q_{0.80} = \text{Percentile}(\{|y_i - \hat{y}_i|\}_{i=1}^N, 80)$$
- For Model `v002`, the calibrated 80% error bound is **$\pm$ ₹97,713** (and 90% bound is $\pm$ ₹1,56,145).
- Point prediction intervals are calculated as:
  $$[\hat{y} - q_{0.80}, \hat{y} + q_{0.80}]$$

### Methodology B: Random Forest Ensemble Prediction Spread
- For tree ensemble estimators with $T$ trees:
  $$\hat{y}_t = f_t(X), \quad t = 1, \dots, T$$
- The ensemble standard deviation $\sigma_{\text{trees}} = \text{std}(\{\hat{y}_t\})$ is computed.
- Tree variance measures the disagreement among individual decision trees regarding unfamiliar attribute combinations.

---

## 3. Production Implementation
AutoValue exposes:
```json
"model_interval": {
  "interval_low": 1117287.0,
  "interval_high": 1312713.0,
  "confidence_level": 0.8,
  "method": "Empirical validation residual quantile (80% coverage)"
}
```
No static arbitrary percentages (e.g. "$\pm 10\%$") are used.
