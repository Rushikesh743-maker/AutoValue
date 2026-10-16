# AutoValue — Data Transformation, Feature Engineering & Quality Specification

This document details the transformation, feature engineering, duplicate policy, outlier auditing, and ML readiness gate implemented in Phase 3.

---

## 1. End-to-End Transformation Pipeline

```text
       ┌─────────────────────────────────────────────────────────────┐
       │                Raw Collected Listings (data/raw/)           │
       └──────────────────────────────┬──────────────────────────────┘
                                      │
                                      ▼
                        [ Duplicate Classification ]
        Classifies records into Confirmed, Probable, and Possible
            duplicates using multi-attribute similarity scoring
                                      │
                                      ▼
                        [ Missing Value Analyzer ]
       Retains categorical 'Unspecified' & learns training medians
                                      │
                                      ▼
                         [ Outlier & Domain Audit ]
        Audits price bounds, year validity, and KM intensity fences
                                      │
                                      ▼
                        [ Feature Engineering Engine ]
          Generates car_age, km_per_year, and categorical sets
                                      │
                                      ▼
                        [ Data Leakage Verification ]
        Verifies zero target-derived features in feature matrix X
                                      │
                                      ▼
                         [ ML Readiness Quality Gate ]
       Evaluates sample size, diversity, and feature completeness
                                      │
                                      ▼
                 [ Processed Dataset & Versioned Metadata ]
           data/processed/autovalue_processed.csv + metadata.json
```

---

## 2. Duplicate Classification Strategy

Cross-source duplicate listings (where the same physical vehicle is posted across multiple platforms or dealerships) are evaluated using a multi-factor similarity score (0.0 to 1.0) and partitioned into four tiers:

| Tier | Similarity Threshold | Classification | Strategy |
|---|---|---|---|
| **Tier 1** | Score $\ge 0.95$ | **Confirmed Duplicate** | Primary record retained; duplicate flagged with `duplicate_of_id` and filtered from ML training set. |
| **Tier 2** | $0.85 \le \text{Score} < 0.95$ | **Probable Duplicate** | Flagged as duplicate candidate; preserved in historical archive. |
| **Tier 3** | $0.70 \le \text{Score} < 0.85$ | **Possible Duplicate** | Preserved with similarity notes for human audit. |
| **Tier 4** | $\text{Score} < 0.70$ | **Independent Listing** | Treated as distinct, unique physical vehicle. |

---

## 3. Missing Value Strategy

Missing values are never replaced with arbitrary constants. Strategies are chosen based on feature properties:

| Feature | Strategy | Rationale |
|---|---|---|
| `brand`, `model`, `year`, `listed_price` | **Error if Missing** | Mandatory baseline coordinates for car valuation. |
| `variant`, `fuel_type`, `transmission`, `city`, `state`, `seller_type` | **Retain Category (`Unspecified`)** | Preserves signal that specific sub-variant or location was not disclosed by seller. |
| `km_driven`, `owner_count`, `engine_cc`, `mileage` | **Median Imputation (Training Split Only)** | Robust against skewness; medians are calculated strictly on training folds to prevent test leakage. |

---

## 4. Outlier & Domain Constraint Auditing

Outlier detection combines automotive domain rules with statistical IQR fences (multiplier 2.5):

- **Price Bounds**: Flagged if $\text{Price} < ₹25,000$ or $\text{Price} > ₹25,000,000$ (₹2.5 Crore).
- **Year Bounds**: Flagged if $\text{Year} < 1995$ or $\text{Year} > 2026$.
- **Odometer Bounds**: Flagged if $\text{KM} < 0$ or $\text{KM} > 500,000\text{ km}$.
- **KM Intensity Anomaly**: Flagged if $\frac{\text{KM}}{\text{Age}} > 75,000\text{ km/year}$.
- **Preservation Principle**: Outliers are **not** blindly dropped; they receive boolean flags `is_outlier = True` and detailed `outlier_reasons` for transparent modeling decisions.

---

## 5. Engineered Features

### A. Vehicle Age (`car_age`)
$$\text{car\_age} = \max(0, \text{reference\_year} - \text{year})$$
- Reference Year defaults to **2024** (configurable).

### B. Annual Kilometer Intensity (`km_per_year`)
$$\text{km\_per\_year} = \frac{\text{km\_driven}}{\max(\text{car\_age}, 1)}$$
- Measures usage intensity while preventing division-by-zero for brand-new/same-year vehicles.

### C. Standardized Categoricals
- Clean string representations for `brand`, `model`, `variant`, `fuel_type`, `transmission`, `city`, `state`, `seller_type`.

---

## 6. Data Leakage Protection

- Target variable is explicitly defined as `listed_price` (observed asking price in INR).
- **Audit Rule**: Automated `check_target_leakage()` guarantees that no price-derived metrics (e.g. `price_per_km`, `log_price`, `predicted_price`) or target statistics enter the independent feature matrix $X$.
- Any future target encoding or cluster pricing must be fitted strictly on training partitions during cross-validation.

---

## 7. Machine Learning Readiness Gate

Before any training script executes, the `MLReadinessGate` performs automated validation:
1. **Sample Volume Check**: Requires minimum $N \ge 50$ records for 5-fold cross-validation.
2. **Target Validity Check**: Verifies 100% positive non-null target values.
3. **Core Feature Completeness**: Checks existence of `brand`, `model`, `year`, `km_driven`, `car_age`, `km_per_year`.
4. **Brand Diversity**: Requires $\ge 3$ distinct OEM brands.
5. **Leakage Audit**: Confirms zero target leakage.
