# AutoValue Total Cost of Ownership (TCO) Engine

## 1. Overview & Core Objective

The **Total Cost of Ownership (TCO) & Resale Intelligence Engine (Phase 13)** answers the critical buyer question:
> *"If I buy this vehicle today, what could it realistically cost me to own over time, and what might its resale position look like?"*

AutoValue strictly separates four epistemic categories to prevent fake financial precision:
```
OBSERVED MARKET EVIDENCE  →  USER ASSUMPTIONS  →  DERIVED EXPENDITURES  →  STATISTICAL PROJECTIONS
```

---

## 2. Mathematical Formulations

### Gross Cash Outflow ($C_{\text{gross}}$)
$$C_{\text{gross}} = P_{\text{purchase}} + C_{\text{fuel}} + C_{\text{ins}} + C_{\text{maint}} + C_{\text{tax}} + C_{\text{other}}$$

Where:
- $P_{\text{purchase}}$: Effective purchase price resolved via `FAIR_VALUE`, `ASKING_PRICE`, or `CUSTOM`.
- $C_{\text{fuel}}$: Cumulative fuel / energy consumption over $T$ years.
- $C_{\text{ins}}$: Cumulative insurance premiums over $T$ years.
- $C_{\text{maint}}$: Cumulative scheduled maintenance and routine wear budget.
- $C_{\text{tax}}$: Upfront registration/transfer fees.
- $C_{\text{other}}$: Recurring ancillary expenses (parking, tolls, extended warranty).

### Net Total Cost of Ownership ($TCO_{\text{net}}$)
$$TCO_{\text{net}} = C_{\text{gross}} - V_{\text{resale}}(T)$$

Where $V_{\text{resale}}(T)$ is the statistical projected resale recovery at the end of ownership horizon $T$.

### Annualized Cost ($\text{Cost}_{\text{annual}}$)
$$\text{Cost}_{\text{annual}} = \frac{TCO_{\text{net}}}{T}$$

### Cost Per Kilometer ($\text{Cost}_{\text{km}}$)
$$\text{Cost}_{\text{km}} = \frac{TCO_{\text{net}}}{\text{Total Projected Kilometers}} = \frac{TCO_{\text{net}}}{D_{\text{annual}} \times T}$$

---

## 3. Powertrain & Fuel Modeling

### Internal Combustion Engine (ICE - Petrol, Diesel, CNG)
$$\text{Annual Consumption (L or kg)} = \frac{D_{\text{annual}}}{\eta_{\text{fuel}}}$$
$$\text{Annual Fuel Cost} = \left(\frac{D_{\text{annual}}}{\eta_{\text{fuel}}}\right) \times P_{\text{fuel}}$$

### Electric Vehicles (EV)
$$\text{Annual Energy (kWh)} = D_{\text{annual}} \times \left(\frac{\eta_{\text{kWh/100km}}}{100}\right)$$
$$\text{Annual Electricity Cost} = \text{Annual Energy (kWh)} \times P_{\text{kWh}}$$

### Default Configuration Parameters (Indian Market Baseline)
| Fuel Type | Default Price | Default Efficiency | Default Annual Maintenance |
|---|---|---|---|
| **Petrol** | ₹104.50 / L | 16.0 km/L | ₹15,000 / yr |
| **Diesel** | ₹92.50 / L | 18.5 km/L | ₹18,000 / yr |
| **CNG** | ₹86.00 / kg | 22.0 km/kg | ₹16,000 / yr |
| **Electric (EV)** | ₹10.00 / kWh | 15.0 kWh / 100km | ₹10,000 / yr |
| **Hybrid** | ₹104.50 / L | 22.5 km/L | ₹16,000 / yr |

---

## 4. Scenario Engine

| Scenario | Fuel Multiplier | Maintenance Multiplier | Resale Multiplier | Purpose |
|---|---|---|---|---|
| **Conservative** | $+10\%$ | $+25\%$ | $-8\%$ | Stress-tests budget against rising fuel, unexpected repairs, and softer resale. |
| **Base** | $1.0\times$ | $1.0\times$ | $1.0\times$ | Central calibrated model aligned with observable market history. |
| **Optimistic** | $-8\%$ | $-15\%$ | $+6\%$ | Favorable driving conditions, high resale retention, and trouble-free maintenance. |

---

## 5. Deterministic Sensitivity Analysis

Evaluates first-order partial derivatives across 5 key input dimensions:
1. **Fuel Price ($\pm 10\%$)**: Direct linear impact on running expenditure.
2. **Annual Mileage ($\pm 20\%$)**: Proportional impact on fuel, tire wear, and vehicle depreciation penalty.
3. **Purchase Price ($-\text{₹}50,000$)**: Immediate capital savings from negotiation leverage.
4. **Maintenance ($\pm\text{₹}10,000/\text{yr}$)**: Sensitivity to major service items or premium component replacement.
5. **Resale ($\pm 10\%$)**: Resale valuation risk exposure.

---

## 6. Critical Limitations

1. **Estimates, Not Financial Quotes**: Insurance and financing figures are transparent model assumptions, not binding quotes.
2. **Asking Price Evidence**: Market evidence is calibrated primarily against advertised seller asking listings.
3. **Physical Condition Unknown**: Vehicle accident history, tire tread depth, battery health degradation, and mechanical condition are not physically inspected.
