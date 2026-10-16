# AutoValue Resale Intelligence Engine

## 1. Overview & Methodology

The **Resale Intelligence Engine (Phase 13)** calculates market-anchored, multi-year vehicle depreciation and projected residual value corridors across 1 to 10-year horizons.

Unlike simplistic linear depreciation tables, AutoValue uses a **market-anchored geometric curve calibrated to vehicle age lifecycle brackets, annual mileage intensity, and observed historical price trajectories**.

---

## 2. Depreciation Model Formulation

### Base Depreciation by Age Tier
For year $t$ of future ownership (where initial age is $A_0$ and projected age is $A(t) = A_0 + t$):

$$\delta_{\text{base}}(A) = \begin{cases} 
13.5\% & \text{if } A \le 3 \text{ years (rapid early lifecycle)} \\
9.5\% & \text{if } 4 \le A \le 7 \text{ years (linear maturation phase)} \\
7.0\% & \text{if } A \ge 8 \text{ years (asymptotic residual phase)}
\end{cases}$$

### Mileage Intensity Adjustment ($\Delta_{\text{km}}$)
High annual usage accelerates wear and market depreciation:
$$\Delta_{\text{km}} = \text{clamp}\left(-0.02, +0.03, \frac{D_{\text{annual}} - 12000}{100000} \times 0.05\right)$$

### Market Timing / Historical Trend Anchoring ($\Delta_{\text{trend}}$)
Incorporate observable 6-month historical market price movement:
$$\Delta_{\text{trend}} = \text{clamp}\left(-0.02, +0.02, -\frac{\Delta_{\text{market\%}}}{100} \times 0.2\right)$$

### Effective Annual Depreciation Rate
$$\delta_{\text{eff}}(t) = \text{clamp}\left(0.04, 0.25, \delta_{\text{base}}(A_0 + t) + \Delta_{\text{km}} + \Delta_{\text{trend}}\right)$$

### Residual Floor Protection
To prevent indefinite extrapolation to zero:
$$V_{\text{floor}} = \max(\text{₹}40,000, P_{\text{purchase}} \times 12\%)$$
$$V_{\text{resale}}(t) = \max\left(V_{\text{floor}}, V_{\text{resale}}(t-1) \times (1 - \delta_{\text{eff}}(t))\right)$$

---

## 3. Resale Uncertainty Corridor

Uncertainty widens as the projection horizon extends into the future and reflects underlying marketplace price dispersion:

$$\text{Half-Width \%}(t) = \min\left(0.28, 0.06 + (t \times 0.025) + \sigma_{\text{market}}\right)$$
$$V_{\text{lower}}(t) = \max\left(\text{₹}35,000, V_{\text{resale}}(t) \times (1 - \text{Half-Width \%}(t))\right)$$
$$V_{\text{upper}}(t) = V_{\text{resale}}(t) \times (1 + \text{Half-Width \%}(t))$$

---

## 4. Evidence Confidence Categorization

Confidence reflects empirical data density, not subjective probability:
- **`HIGH`**: $\ge 8$ active comparable listings in dataset.
- **`MODERATE`**: $3 - 7$ comparable listings.
- **`LOW`**: $1 - 2$ comparable listings.
- **`INSUFFICIENT_EVIDENCE`**: $0$ comparable listings.

---

## 5. Critical Boundaries & Limitations

- **Projections $\neq$ Guarantees**: Projections reflect historical market patterns; future regulatory shifts (e.g. diesel bans, EV incentives) or economic shocks may alter actual realizations.
- **Condition Variance**: Exceptional care or neglect will place a vehicle near the upper or lower bounds respectively.
