# AutoValue System Architecture & Design Specification

## 1. System Vision

AutoValue is built as a transparent, data-driven used car market valuation and intelligence engine designed specifically for the Indian pre-owned automotive market.

The primary product requirement is **authenticity and explainability**:
- Every valuation estimate is rooted in empirical listing observations from verifiable sources.
- No fabricated figures or black-box single numbers.
- Explicit distinction between **asking price** (observed in listings) and transaction settlement value.

---

## 2. End-to-End Pipeline Stages

```
1. Ingestion / Collectors
   └── Scheduled tasks fetch listings from vetted platforms with rate limiting and robot compliance.
   
2. Schema Ingestion (RawCarListing)
   └── Captures unstructured text, URLs, pricing strings, and source identifiers.

3. Cleaning & Standardization (CarDataCleaner)
   └── Normalizes price numbers (Lakhs, Crores, INR symbols), odometer readings, fuel & transmission strings.

4. Vehicle Entity Normalization (VehicleNormalizer)
   └── Disambiguates brand names, splits model and variant/trim with fuzzy matching and ontology dictionaries.

5. Deduplication Engine (DuplicateDetector)
   └── Pairwise multi-attribute similarity scoring across make, model, year, odometer, price tolerance, and location.

6. Relational Storage (PostgreSQL)
   └── Indexed storage for listings, collection run logs, and sources.

7. Feature Engineering
   └── Vehicle age, annual km intensity, fuel efficiency interaction, brand segment tiers, regional liquidity indices.

8. Machine Learning Model (XGBoost / LightGBM)
   └── Regression modeling to generate market median and quantile prediction bands (P10 - P90 confidence interval).

9. Explainability (SHAP)
   └── Local explanation decomposition showing impact of mileage, age, variant features, and city demand.

10. Comparable Vehicle Matcher
    └── Finds top-K active comparable vehicles currently in the market.
```

---

## 3. Data Integrity Principles

1. **Provenance Preservation**: Every record tracks `source`, `listing_id`, `listing_url` (where available), and `date_collected`.
2. **Deterministic Validation**: No corrupted data enters the database; records failing canonical validation are logged into rejected collection metrics.
3. **No Fabricated Data**: No fake scraping endpoints, demo hardcoding, or artificial test datasets masquerading as market reality.
