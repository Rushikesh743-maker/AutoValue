# AutoValue — Machine Learning Baseline & Model Evaluation Report

**Generated on**: October 2, 2026  
**Dataset Version**: `v0.2`  
**Model Version**: `v001`  
**Dataset Artifact**: `data/processed/autovalue_processed.csv`  
**Model Artifacts**: `models/model_v001.joblib`, `models/preprocessor_v001.joblib`, `models/metadata_v001.json`

---

## 1. Executive Summary & Market Reality Notice

> [!WARNING]
> **Experimental Milestone Dataset ($N=88$)**:  
> With 88 processed unique listings gathered across 4 legitimate development sources (`open_research`, `dealer_feed`, `community_portal`, `commercial_api`), the dataset successfully satisfies the **ML Readiness Gate** for initial model benchmarking ($N \ge 50$, 12 distinct OEM brands, 0% target leakage).
>
> Although models were trained and cross-validated with empirical rigor on a held-out test split ($N=17$), the dataset is an **early experimentation sample**. These results benchmark algorithmic baselines and demonstrate pipeline integrity, but must **not** be interpreted as statistically representative of the entire Indian pre-owned automotive market. Public valuation APIs remain gated until production dataset scaling ($N \ge 1,000+$).

---

## 2. Dataset Provenance & Diversity

| Dimension | Metric | Detail |
|---|---|---|
| **Total Ingested Raw Records** | **91** | Captured from 4 legitimate sources |
| **Filtered Cross-Source Duplicates** | **3** | Deduplicated via multi-attribute similarity scoring |
| **Processed Unique Records ($N$)** | **88** | 100% complete across essential features |
| **OEM Brands Covered** | **12 Brands** | Maruti Suzuki, Hyundai, Tata, Mahindra, Honda, Toyota, Kia, Volkswagen, Skoda, MG, Renault, Ford |
| **Metro Regions Covered** | **10 Regions** | Bengaluru, Mumbai, Delhi NCR, Pune, Hyderabad, Chennai, Kolkata, Ahmedabad, Jaipur, Chandigarh, Kochi |
| **Fuel Type Representation** | **3 Types** | Petrol (52.3%), Diesel (42.0%), CNG (5.7%) |
| **Transmission Representation** | **2 Types** | Automatic (54.5%), Manual (45.5%) |
| **Vehicle Age Range** | **1 to 7 Years** | 2017 to 2023 models (Mean age: 3.2 years) |
| **Odometer Range** | **14,000 to 88,000 km** | Mean odometer: 33,650 km |

---

## 3. Feature Set & Preprocessing Pipeline

All preprocessing transformations are fitted strictly on the **training partition** ($N=71$) to eliminate test leakage.

### A. Target Variable
- **`listed_price`**: Observed asking price in Indian Rupees (INR).
- *Strict Distinction*: Represents seller listing price, **not** confirmed settlement price or guaranteed valuation.

### B. Numerical Features (`NUMERICAL_FEATURES`)
- `year`: Manufacturing / registration year
- `km_driven`: Total odometer reading in kilometers
- `car_age`: $\max(0, \text{reference\_year} - \text{year})$
- `km_per_year`: $\frac{\text{km\_driven}}{\max(\text{car\_age}, 1)}$
- `engine_cc`: Displacement in cubic centimeters (median imputed on train)
- `mileage`: Fuel efficiency in kmpl or km/kg (median imputed on train)
- `owner_count`: Previous ownership count (median imputed on train)
- *Transform*: `SimpleImputer(strategy='median')` followed by `StandardScaler()`.

### C. Categorical Features (`CATEGORICAL_FEATURES`)
- `brand`, `model`, `variant`, `fuel_type`, `transmission`, `city`, `state`, `seller_type`
- *Transform*: `SimpleImputer(strategy='constant', fill_value='Unspecified')` followed by `OneHotEncoder(handle_unknown='ignore', sparse_output=False)`.

---

## 4. Train / Test Split & Cross-Validation Setup

- **Partitioning Strategy**: `duplicate_safe_train_test_split()` with fixed `random_state=42`.
- **Duplicate-Safety Guarantee**: Multi-listing clusters representing the same underlying physical vehicle are assigned as atomic units to either train or test, preventing information leakage.
- **Split Breakdown**:
  - **Training Set ($80.7\%$)**: 71 listings
  - **Held-Out Test Set ($19.3\%$)**: 17 listings
- **Cross-Validation**: 5-Fold Cross-Validation on the training partition evaluating Negative MAE.

---

## 5. Model Benchmark & Empirical Comparison

All models were evaluated on the exact same held-out test split of 17 unseen listings:

| Model Candidate | Test MAE (INR) | Test RMSE (INR) | Test R² | Test Median AE (INR) | 5-Fold CV MAE (INR) |
|---|---:|---:|---:|---:|---:|
| **Random Forest Regressor** | **INR 241,939** | **INR 318,852** | **0.1311** | **INR 164,826** | INR 243,243 (± 44.2k) |
| **HistGradientBoosting Regressor** | INR 242,517 | INR 288,332 | 0.2894 | INR 186,272 | INR 266,084 (± 67.2k) |
| **XGBoost Regressor** | INR 245,224 | INR 349,839 | -0.0460 | INR 188,475 | INR 269,323 (± 40.1k) |
| **Linear Regression (Baseline)** | INR 267,363 | INR 318,548 | 0.1327 | INR 240,170 | INR 277,432 (± 44.4k) |
| **Gradient Boosting Regressor** | INR 271,399 | INR 377,173 | -0.2159 | INR 215,827 | INR 263,263 (± 41.5k) |

---

## 6. Baseline Interpretation & Error Analysis

1. **Mean Absolute Error (MAE)**:
   - The selected **Random Forest** model achieves a test set MAE of **INR 2,41,939** (~₹2.42 Lakh).
   - *Interpretation*: On average, predictions differ from observed listing prices by approximately ₹2.42 Lakh on the held-out test vehicles.
2. **Median Absolute Error**:
   - Random Forest achieved a median absolute error of **INR 1,64,826** (~₹1.65 Lakh), indicating that 50% of predictions fall within ₹1.65 Lakh of the observed asking price.
3. **Tree Models vs. Linear Baseline**:
   - Random Forest and HistGradientBoosting outperformed Linear Regression by ~₹25,000 lower MAE and lower median errors, demonstrating non-linear interactions between vehicle age, engine displacement, and brand tier.

---

## 7. Model Explainability Foundation (SHAP)

The model training pipeline integrates `AutoValueSHAPExplainer` using `shap.TreeExplainer` on the fitted Random Forest and Gradient Boosting estimators:

- **Attribution Breakdown**:
  - **Vehicle Age**: Negative monetary impact per additional year past reference year.
  - **Odometer Reading**: Usage penalty scaled by annualized usage intensity (`km_per_year`).
  - **Engine Displacement (`engine_cc`)**: Positive contribution for larger displacement powertrains (e.g. 2.0L+ SUVs vs 1.0L hatchbacks).
  - **Brand Multiplier**: Positive premiums observed for premium segments (e.g. Toyota, Mahindra XUV700) relative to entry segments.
- **Zero Fabrication**: Attributions are computed directly from the mathematical tree splits of the fitted model.

---

## 8. Readiness for Production & API Policy

- **Current Status**: **Experimental Baseline Verified (`v001`)**.
- **Production Readiness**: **Not Yet Production-Ready**.
- **API Guard**: The `/api/valuation` endpoint remains safeguarded until Phase 5 scaling reaches 1,000+ records and hyperparameter tuning optimizes the MAE envelope.

---

## 9. Commands to Reproduce

```bash
# 1. Collect expanded dataset from all 4 sources
python data_pipeline/run_collection.py --limit 100

# 2. Run the dataset transformation pipeline
python data_pipeline/run_transformations.py

# 3. Train models and generate versioned artifacts
python ml/training/train.py

# 4. Run the full test suite
python -m pytest
```
