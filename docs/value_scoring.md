# Value-For-Money Scoring System Documentation

## 1. Overview
The **Value-For-Money Score** (`ValueScoreService`) provides an interpretable, composite evaluation score (0 to 100) assessing a vehicle's pricing attractiveness relative to its lifecycle stage, mileage usage intensity, and marketplace evidence density.

---

## 2. Transparent Multi-Component Formula

The Overall Value Score ($S_{\text{overall}}$) is computed via a weighted linear combination of four sub-scores:

$$S_{\text{overall}} = w_{\text{price}} S_{\text{price}} + w_{\text{mileage}} S_{\text{mileage}} + w_{\text{age}} S_{\text{age}} + w_{\text{market}} S_{\text{market}}$$

### 2.1 Default Weights:
- **Price Value Weight ($w_{\text{price}}$)**: $0.40$ (40%)
- **Mileage Value Weight ($w_{\text{mileage}}$)**: $0.25$ (25%)
- **Vehicle Age Weight ($w_{\text{age}}$)**: $0.15$ (15%)
- **Market Support Weight ($w_{\text{market}}$)**: $0.20$ (20%)

*Note: If asking price is missing, $w_{\text{price}}$ is redistributed proportionally across mileage, age, and market support.*

---

## 3. Sub-Score Derivations

### 3.1 Price Value Score ($S_{\text{price}}$)
Measures the discount or premium of asking price ($P_{\text{ask}}$) relative to estimated fair value ($\hat{V}_{\text{ML}}$):
$$\% \Delta = \frac{P_{\text{ask}} - \hat{V}_{\text{ML}}}{\hat{V}_{\text{ML}}} \times 100$$
$$S_{\text{price}} = \text{clamp}\left(70.0 - (\% \Delta \times 2.0), 10.0, 100.0\right)$$

- At $0\%$ difference (fair value): $S_{\text{price}} = 70.0$
- At $-15\%$ discount: $S_{\text{price}} = 100.0$
- At $+30\%$ premium: $S_{\text{price}} = 10.0$

### 3.2 Mileage Value Score ($S_{\text{mileage}}$)
Evaluates annual usage intensity ($I_{\text{annual}} = \frac{\text{km\_driven}}{\max(1, \text{age})}$):
- $I_{\text{annual}} \le 8,000 \text{ km/yr}$ (Low usage): $S_{\text{mileage}} \in [85, 100]$
- $8,000 < I_{\text{annual}} \le 15,000 \text{ km/yr}$ (Typical usage): $S_{\text{mileage}} \in [70, 85]$
- $15,000 < I_{\text{annual}} \le 25,000 \text{ km/yr}$ (High usage): $S_{\text{mileage}} \in [45, 70]$
- $I_{\text{annual}} > 25,000 \text{ km/yr}$ (Extreme usage): $S_{\text{mileage}} \in [10, 45]$

### 3.3 Vehicle Age Score ($S_{\text{age}}$)
Evaluates position within standard lifecycle (assuming 15-year horizon):
$$S_{\text{age}} = \text{clamp}\left(100.0 - (\text{age} \times 6.0), 15.0, 100.0\right)$$

### 3.4 Market Support Score ($S_{\text{market}}$)
Evaluates sample size confidence from active comparables ($N_{\text{comp}}$):
$$S_{\text{market}} = \min\left(100.0, 30.0 + (N_{\text{comp}} \times 7.0)\right)$$

---

## 4. Rating Labels & Classification

| Score Range | Rating Label | Description |
|---|---|---|
| $85 \le S_{\text{overall}} \le 100$ | `EXCEPTIONAL_VALUE` | Substantial price discount, low usage, strong market evidence |
| $70 \le S_{\text{overall}} < 85$ | `STRONG_VALUE` | Attractive pricing with solid lifecycle metrics |
| $50 \le S_{\text{overall}} < 70$ | `AVERAGE_VALUE` | Fair alignment with typical market depreciation |
| $35 \le S_{\text{overall}} < 50$ | `BELOW_AVERAGE_VALUE` | Premium pricing or elevated mileage intensity |
| $0 \le S_{\text{overall}} < 35$ | `POOR_VALUE` | High premium over fair value with high age/mileage |

---

## 5. Distinction from Vehicle Mechanical Condition
> **Important**: The Value-For-Money score is strictly a financial and economic competitiveness metric. It **does NOT assess physical vehicle condition, mechanical soundness, flood history, or cosmetic flaws**.
