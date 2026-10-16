# Smart Deal Analysis Engine Documentation

## 1. Overview
The **Smart Deal Analysis Engine** (`DealAnalysisService`) provides deterministic, evidence-grounded price position evaluation for used vehicles. Rather than relying on a black-box heuristic, it evaluates the seller's asking price against both empirical market distributions (P25, median, P75) and active machine learning fair-value estimates.

---

## 2. Mathematical Foundations & Metrics

### 2.1 Price Gap Metrics
For a given valuation request with user asking price $P_{\text{ask}}$, ML estimated fair value $\hat{V}_{\text{ML}}$, and observed market quartiles $(P_{25}, M_{\text{obs}}, P_{75})$:

1. **Asking Price vs. ML Fair Value:**
   $$\Delta_{\text{ML}} = P_{\text{ask}} - \hat{V}_{\text{ML}}$$

2. **Percentage Difference from ML Fair Value:**
   $$\% \Delta_{\text{ML}} = \frac{P_{\text{ask}} - \hat{V}_{\text{ML}}}{\hat{V}_{\text{ML}}} \times 100$$

3. **Asking Price vs. Market Median:**
   $$\Delta_{\text{median}} = P_{\text{ask}} - M_{\text{obs}}$$

4. **Percentage Difference from Market Median:**
   $$\% \Delta_{\text{median}} = \frac{P_{\text{ask}} - M_{\text{obs}}}{M_{\text{obs}}} \times 100$$

5. **Interquartile Gaps:**
   $$\Delta_{P25} = P_{\text{ask}} - P_{25}$$
   $$\Delta_{P75} = P_{\text{ask}} - P_{75}$$

---

## 3. Evidence Strength & Support Scoring

The confidence of the deal classification depends strictly on the empirical density of comparable listings ($N_{\text{comp}}$):

| Comparable Count ($N_{\text{comp}}$) | Evidence Strength | Comparable Support Score ($S_{\text{comp}}$) |
|---|---|---|
| $0$ | `INSUFFICIENT` | $0.00$ |
| $1 \le N_{\text{comp}} < 3$ | `LOW` | $0.35 + 0.15 \times \left(\frac{N_{\text{comp}}}{3}\right)$ |
| $3 \le N_{\text{comp}} < 6$ | `MEDIUM` | $0.65 + 0.15 \times \left(\frac{N_{\text{comp}} - 3}{3}\right)$ |
| $N_{\text{comp}} \ge 6$ | `HIGH` | $\min\left(1.0, 0.85 + 0.15 \times \left(\frac{N_{\text{comp}} - 6}{4}\right)\right)$ |

---

## 4. Deterministic Classification Matrix

The asking price is classified into one of 6 transparent categories:

```
          Asking Price relative to ML Fair Value (%Δ_ML)
  < -10%               -10% to -3%       -3% to +3%       +3% to +10%         > +10%
[SIGNIFICANTLY_BELOW] [BELOW_MARKET]   [FAIRLY_PRICED]   [ABOVE_MARKET]  [SIGNIFICANTLY_ABOVE]
```

### Thresholds:
- **`SIGNIFICANTLY_BELOW_MARKET`**: $\% \Delta_{\text{ML}} \le -10.0\%$
- **`BELOW_MARKET`**: $-10.0\% < \% \Delta_{\text{ML}} \le -3.0\%$
- **`FAIRLY_PRICED`**: $-3.0\% < \% \Delta_{\text{ML}} < +3.0\%$
- **`ABOVE_MARKET`**: $+3.0\% \le \% \Delta_{\text{ML}} < +10.0\%$
- **`SIGNIFICANTLY_ABOVE_MARKET`**: $\% \Delta_{\text{ML}} \ge +10.0\%$
- **`INSUFFICIENT_EVIDENCE`**: Triggered when asking price is missing, non-positive, or when comparable support is below minimum statistical thresholds.

---

## 5. Market Position Mapping
When market quartiles are available from comparable listings:
- **`BELOW_P25`**: $P_{\text{ask}} < P_{25}$
- **`BETWEEN_P25_AND_MEDIAN`**: $P_{25} \le P_{\text{ask}} < M_{\text{obs}}$
- **`BETWEEN_MEDIAN_AND_P75`**: $M_{\text{obs}} \le P_{\text{ask}} \le P_{75}$
- **`ABOVE_P75`**: $P_{\text{ask}} > P_{75}$

---

## 6. Limitations & Integrity Policy
- Deal classifications are strictly comparative pricing calculations and **do NOT certify physical or mechanical vehicle condition**.
- If no asking price is supplied by the user, the engine returns `INSUFFICIENT_EVIDENCE` with an explicit advisory notice rather than fabricating a recommendation.
