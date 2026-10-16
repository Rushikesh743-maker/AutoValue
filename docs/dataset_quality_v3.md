# AutoValue — Dataset Quality & Characteristics Report (v0.3)

**Generated:** 2026-10-02  
**Dataset Version:** `v0.3`  
**Processed Dataset Path:** `data/processed/autovalue_processed.csv`  
**Metadata Path:** `data/processed/dataset_metadata.json`

---

## 1. Executive Summary

In Phase 6, the AutoValue dataset was scaled from $N=88$ baseline records to **$N=999$ processed unique listings** across four permissible Indian used car data sources. The ingestion pipeline rejected cross-source duplicates and unverified entries while strictly adhering to compliance protocols.

| Metric | Phase 4 (v0.2) | Phase 6 (v0.3) | Change |
| :--- | :--- | :--- | :--- |
| **Cumulative Raw Records** | 91 | 1,227 | +1,136 |
| **Processed Unique Records** | 88 | **999** | **+911 (+1,035%)** |
| **Duplicates Filtered** | 3 | 228 | +225 |
| **Distinct Brands (OEMs)** | 12 | 14 | +2 |
| **Distinct Models** | 22 | 44 | +22 |
| **Approved Sources** | 4 | 4 | Stable |
| **ML Readiness Gate** | READY | **READY** | Verified |

---

## 2. Source Distribution & Imbalance Analysis

| Source Name | Category | Record Count | Proportion (%) |
| :--- | :--- | :--- | :--- |
| `open_research` | Open Academic / Commons Archive | 416 | 41.6% |
| `dealer_feed` | Certified Dealer Inventory Feed | 295 | 29.5% |
| `community_portal` | User Classifieds Portal | 191 | 19.1% |
| `commercial_api` | Licensed Partner Marketplace API | 97 | 9.7% |
| **Total** | | **999** | **100.0%** |

### Imbalance Assessment
- The highest representation comes from open research archives ($41.6\%$) and dealer networks ($29.5\%$), with community classifieds at $19.1\%$ and commercial APIs at $9.7\%$.
- No single source holds a catastrophic monopoly ($>70\%$). 
- In accordance with Phase 6 guidelines, no artificial resampling was applied to the production dataset; source indicators are tracked to evaluate cross-source variance.

---

## 3. Brand & Model Diversity

The dataset covers major OEM brands in the Indian automotive market:

| OEM Brand | Count | Share (%) | Key Models Represented |
| :--- | :--- | :--- | :--- |
| **Maruti Suzuki** | 180 | 18.0% | Swift, Baleno, Wagon R, Dzire, Brezza, Ertiga, Grand Vitara |
| **Tata** | 129 | 12.9% | Nexon, Punch, Harrier, Safari, Tiago, Altroz |
| **Mahindra** | 122 | 12.2% | XUV700, Scorpio-N, Thar, XUV300, Bolero |
| **Hyundai** | 109 | 10.9% | Creta, i20, Grand i10 Nios, Venue, Verna |
| **Toyota** | 89 | 8.9% | Innova Crysta, Fortuner, Glanza, Urban Cruiser Hyryder |
| **Kia** | 76 | 7.6% | Seltos, Sonet, Carens |
| **Skoda** | 72 | 7.2% | Kushaq, Slavia, Octavia, Rapid |
| **Honda** | 68 | 6.8% | City, Amaze, Elevate |
| **Volkswagen** | 66 | 6.6% | Virtus, Taigun, Polo, Vento |
| **Mercedes-Benz** | 25 | 2.5% | C-Class, E-Class, GLC |
| **MG** | 24 | 2.4% | Hector, ZS EV |
| **BMW** | 19 | 1.9% | 3 Series, 5 Series, X1 |
| **Renault** | 18 | 1.8% | Kwid, Triber, Kiger |
| **Ford** | 2 | 0.2% | EcoSport, Endeavour (Legacy) |

---

## 4. Powertrain & Transmission Distribution

### Fuel Types
- **Petrol:** $55.6\%$ ($555$ listings)
- **Diesel:** $27.0\%$ ($270$ listings)
- **CNG:** $11.8\%$ ($118$ listings)
- **Hybrid:** $4.3\%$ ($43$ listings)
- **Electric:** $1.3\%$ ($13$ listings)

### Transmissions
- **Automatic:** $54.9\%$ ($548$ listings)
- **Manual:** $45.1\%$ ($451$ listings)

---

## 5. Geographical Distribution

Top geographic metro clusters:
- **Jaipur:** 86 listings (8.6%)
- **Pune:** 85 listings (8.5%)
- **Bangalore:** 85 listings (8.5%)
- **Noida:** 74 listings (7.4%)
- **Chandigarh:** 73 listings (7.3%)
- **Hyderabad:** 71 listings (7.1%)
- **Ahmedabad:** 70 listings (7.0%)
- **Gurgaon:** 68 listings (6.8%)
- **Kolkata:** 67 listings (6.7%)
- **Kochi:** 66 listings (6.6%)
- **Delhi / Mumbai / Chennai / Lucknow:** Remainder (20.5%)

---

## 6. Numerical Feature Distributions

| Metric | Year | KM Driven | Engine CC | Mileage (kmpl) | Listed Price (INR) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Mean** | 2019.5 | 56,120 | 1485.4 | 18.9 | ₹8,86,862 |
| **Std** | 3.12 | 26,450 | 412.8 | 3.6 | ₹6,65,508 |
| **Min** | 2014 | 4,200 | 799 | 12.0 | ₹1,50,000 |
| **25% (Q1)** | 2017 | 36,000 | 1197 | 16.5 | ₹4,90,000 |
| **50% (Median)** | 2020 | 52,000 | 1462 | 18.5 | ₹7,05,000 |
| **75% (Q3)** | 2022 | 72,000 | 1498 | 21.7 | ₹10,47,500 |
| **Max** | 2024 | 168,000 | 2755 | 27.9 | ₹47,25,000 |

---

## 7. Missing Value & Imputation Summary

| Field | Missing Count | Missing (%) | Strategy |
| :--- | :--- | :--- | :--- |
| `brand`, `model`, `year`, `price`, `km`, `fuel`, `transmission`, `city` | 0 | 0.0% | Complete |
| `variant` | 4 | 0.4% | Imputed as "Standard" |
| `owner_count` | 10 | 1.0% | Median imputed |
| `state` | 10 | 1.0% | City-to-state lookup |
| `engine_cc` | 184 | 18.4% | Group median by (brand, model) |
| `mileage` | 184 | 18.4% | Group median by (brand, model) |
| `seller_type` | 386 | 38.6% | Imputed as "Individual" |

---

## 8. Data Leakage Audit

A comprehensive data leakage audit was re-evaluated:
1. **Target Feature Leakage:** No features derived from `listed_price` exist in the feature matrix $X$.
2. **Preprocessing Transformations:** Preprocessor fits only on training splits during modeling.
3. **Engineered Features:**
   - `car_age` = `reference_year - year` (Strictly independent of target).
   - `km_per_year` = `km_driven / max(1.0, car_age)` (Strictly independent of target).

**Audit Result:** 100% PASSED.
