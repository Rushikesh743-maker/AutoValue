# AutoValue — Historical Market Intelligence & Database Indexing

**Generated:** 2026-10-02  
**Dataset Version:** `v0.3`  
**Applicable Service:** `backend/app/services/historical_market_service.py`  
**Endpoint:** `GET /api/market/history`

---

## 1. Objective & Methodology

The Historical Market Intelligence module aggregates historical asking prices across time periods (3 months, 6 months, 12 months, all-time) for specific makes, models, and locations.

### Aggregation Rules:
1. **Time Binning:** Listings are grouped by year-month (`YYYY-MM`).
2. **Robust Metrics:** Monthly median ($P_{50}$) is the primary indicator, accompanied by mean, $P_{25}$, $P_{75}$, min, and max.
3. **Observed Price Movement:** Absolute difference and percentage difference between the earliest and latest observed periods are computed mathematically.
4. **Data Sufficiency Gate:** A minimum of 3 observations is required. If fewer than 3 observations exist, the API explicitly returns `"Historical trend unavailable — insufficient observations."`

---

## 2. Database Indexing Strategy

To support high-throughput comparable filtering and historical time-series aggregations without table scans, the following composite indexes are configured on PostgreSQL:

| Index Name | Indexed Columns | Justification |
| :--- | :--- | :--- |
| `ix_listings_brand_model_year` | `(brand, model, year)` | Primary comparable candidate retrieval and segment price lookups. |
| `ix_listings_brand_model_city` | `(brand, model, city)` | Location-specific comparable search queries. |
| `ix_listings_brand_model_date` | `(brand, model, date_collected)` | Historical market trend aggregation over time ranges. |
| `ix_listings_source_listing_id` | `(source, listing_id)` | Unique source listing ingestion and duplicate provenance lookups. |

---

## 3. Disclaimers & Terminology
- Historical movements reflect **observed listing asking prices over time**.
- They do **not** represent completed transaction prices, dealer cost basis, or guaranteed future asset appreciation.
