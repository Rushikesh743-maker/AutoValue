# Market Timing Intelligence Engine Documentation

## 1. Overview
The **Market Timing Intelligence Engine** (`MarketTimingService`) examines historical observed asking-price distributions across temporal intervals to provide factual momentum signals without claiming predictive certainty about future price changes.

---

## 2. Methodology & Movement Direction

The service segments observations into recent and baseline periods (or utilizes historical market trends) to compute observed trajectory:

$$\% \Delta_{\text{trend}} = \frac{M_{\text{recent}} - M_{\text{previous}}}{M_{\text{previous}}} \times 100$$

### 2.1 Direction Classifications:
- **`RISING`**: $\% \Delta_{\text{trend}} > +2.5\%$ (Median observed prices have trended upward).
- **`STABLE`**: $-2.5\% \le \% \Delta_{\text{trend}} \le +2.5\%$ (Observed prices remain within a tight corridor).
- **`DECLINING`**: $\% \Delta_{\text{trend}} < -2.5\%$ (Median observed prices have trended downward).
- **`INSUFFICIENT_DATA`**: Observation count $< 3$ or missing temporal history.

---

## 3. Evidence Strength & Confidence
- **`HIGH`**: Observation count $\ge 15$ with consistent geographical alignment.
- **`MEDIUM`**: $6 \le \text{Observation count} < 15$.
- **`LOW`**: $3 \le \text{Observation count} < 6$.
- **`INSUFFICIENT`**: Observation count $< 3$.

---

## 4. Mandatory Predictive Disclaimer
All market timing outputs include the explicit advisory:
> *"Observed market movement reflects past listed asking-price trends in available datasets. It does not constitute financial advice, investment counsel, or a guarantee of future vehicle resale value."*

---

## 5. API Specification
- **Endpoint**: `GET /api/market/timing?brand=Hyundai&model=Creta&city=Mumbai`
- **Response**:
```json
{
  "brand": "Hyundai",
  "model": "Creta",
  "city": "Mumbai",
  "recent_median": 1225000.0,
  "previous_median": 1200000.0,
  "percentage_movement": 2.08,
  "direction": "STABLE",
  "observation_count": 28,
  "evidence_strength": "HIGH",
  "summary": "Observed asking prices for Hyundai Creta in Mumbai have remained stable (+2.1% movement over recent periods).",
  "disclaimer": "Observed market movement reflects historical listing trends and is not a forecast of future vehicle values."
}
```
