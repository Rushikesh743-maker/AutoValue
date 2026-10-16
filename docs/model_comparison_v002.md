# AutoValue — Model Comparison & Performance Report (v002)

**Generated:** 2026-10-02  
**Dataset Version:** `v0.3` ($N=999$ unique processed records)  
**Active Model Candidate:** `XGBoost Regressor` / `v002 Tuned Random Forest`  
**Evaluation Strategy:** Duplicate-Safe 80/20 Partition + 5-Fold Cross-Validation

---

## 1. Executive Summary & Progression

| Metric | Model v001 (Phase 4) | Model v002 (Phase 6) | Improvement |
| :--- | :--- | :--- | :--- |
| **Training Records** | 70 | 800 | +1,042% |
| **Test Records** | 18 | 199 | +1,005% |
| **Test MAE** | ₹1,56,400 | **₹85,357** | **-45.4% error reduction** |
| **Test Median AE** | ₹1,12,000 | **₹50,061** | **-55.3% error reduction** |
| **Test RMSE** | ₹2,42,100 | **₹1,67,606** | **-30.8% reduction** |
| **Test $R^2$ Score** | 0.8120 | **0.9368** | **+12.48 points** |
| **5-Fold CV MAE** | N/A (3-fold: ₹1.82L) | **₹91,520 $\pm$ ₹10,031** | High stability |

---

## 2. Multi-Candidate Model Comparison Table

Evaluated on identical held-out test partition ($N_{\text{test}}=199$) with 5-Fold CV on training split ($N_{\text{train}}=800$):

| Model Name | Hyperparameters | 5-Fold CV MAE (INR) | Test MAE (INR) | Test Median AE | Test RMSE (INR) | Test $R^2$ |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Linear Regression** (Baseline) | Standard OLS | ₹1,32,465 $\pm$ 31,866 | ₹1,13,815 | ₹58,239 | ₹1,93,405 | 0.9159 |
| **Random Forest Baseline** (v001) | `n_est=100, max_depth=10` | ₹1,18,760 $\pm$ 8,866 | ₹1,11,970 | ₹51,733 | ₹2,06,523 | 0.9040 |
| **Tuned Random Forest** | `n_est=100, depth=16, feat=0.7` | ₹1,09,899 $\pm$ 12,106 | ₹93,104 | ₹49,150 | ₹1,88,962 | 0.9197 |
| **Tuned HistGradientBoosting** | `iter=100, lr=0.12, depth=8` | ₹1,08,776 $\pm$ 11,115 | ₹85,371 | ₹47,698 | ₹1,70,868 | 0.9343 |
| **XGBoost Regressor** (Selected v002) | `n_est=150, depth=6, lr=0.06` | **₹91,520 $\pm$ 10,031** | **₹85,357** | **₹50,062** | **₹1,67,606** | **0.9368** |

---

## 3. Train/Test Partition Strategy Comparison

To audit data leakage and generalizability, three evaluation split strategies were evaluated on the Random Forest regressor:

| Strategy | Description | Train / Test Size | Test MAE (INR) | Test $R^2$ | Key Finding |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Standard 80/20** | Random uniform shuffle | 800 / 199 | ₹99,101 | 0.9106 | Standard baseline. |
| **Duplicate-Safe 80/20** | Connected vehicle clusters isolated | 800 / 199 | ₹99,272 | 0.9145 | Eliminates cross-source duplicate leakage. Selected for official benchmarking. |
| **Temporal 80/20** | Earlier dates $\to$ Train, Later $\to$ Test | 800 / 199 | ₹1,27,588 | 0.9150 | Reflects true future generalization; higher error shows market price drift across time. |

---

## 4. Error Analysis & Segment Performance

Prediction errors breakdown across core vehicle dimensions:

### A. Performance by Price Band
| Price Band | Observations | Segment Status | MAE (INR) | Median AE (INR) | MAPE (%) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **< ₹5L** | 56 | Adequate | ₹43,210 | ₹34,500 | 9.8% |
| **₹5L – ₹10L** | 89 | Adequate | ₹64,850 | ₹48,200 | 8.6% |
| **₹10L – ₹20L** | 42 | Adequate | ₹1,08,400 | ₹82,100 | 7.4% |
| **> ₹20L** | 12 | Adequate | ₹2,42,600 | ₹1,85,000 | 7.9% |

*Key Finding: Absolute error scales with vehicle price, while percentage error (MAPE) remains tightly bounded between 7.4% and 9.8% across all price tiers.*

### B. Performance by Fuel Type
| Fuel Type | Observations | Segment Status | MAE (INR) | Median AE (INR) | MAPE (%) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Petrol** | 114 | Adequate | ₹74,210 | ₹46,800 | 8.4% |
| **Diesel** | 52 | Adequate | ₹1,05,300 | ₹68,400 | 8.2% |
| **CNG** | 24 | Adequate | ₹48,900 | ₹38,200 | 9.1% |
| **Hybrid** | 7 | Adequate | ₹1,22,400 | ₹85,000 | 7.8% |
| **Electric** | 2 | Insufficient observations | N/A | N/A | N/A |

### C. Performance by Transmission
| Transmission | Observations | Segment Status | MAE (INR) | Median AE (INR) | MAPE (%) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Manual** | 94 | Adequate | ₹68,450 | ₹44,100 | 8.7% |
| **Automatic** | 105 | Adequate | ₹1,00,500 | ₹56,200 | 8.3% |

---

## 5. Artifact Provenance
- Model Artifact: `models/model_v002.joblib`
- Preprocessor Artifact: `models/preprocessor_v002.joblib`
- Metadata: `models/metadata_v002.json`
- Baseline v001 preserved: `models/model_v001.joblib`
