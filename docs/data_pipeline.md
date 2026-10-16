# AutoValue — Data Pipeline & Ingestion Architecture

This document describes the design and operation of the AutoValue real-world data collection, processing, deduplication, and persistence pipeline.

---

## 1. Architectural Pipeline Flow

```text
       ┌─────────────────────────────────────────────────────────────┐
       │             Legitimate Data Sources (Permissible)           │
       │  (Open Research / Dealership DMS Feeds / Verified Ingest)   │
       └──────────────────────────────┬──────────────────────────────┘
                                      │
                                      ▼
                        [ RateLimitedHttpClient ]
             Polite inter-request delay, exponential backoff,
                 custom User-Agent & timeout controls
                                      │
                                      ▼
                         [ BaseCollector Implementations ]
            SourceFieldAdapter maps heterogeneous raw fields
                                      │
                                      ▼
                         [ Raw Data Preservation ]
            Saves unmodified JSON snapshot to data/raw/
                                      │
                                      ▼
                           [ CarDataCleaner ]
           Parses INR Lakhs/Crores, odometers, fuel, gearbox
                                      │
                                      ▼
                          [ VehicleNormalizer ]
          Disambiguates brands, splits model & variant with
             canonical dictionaries and RapidFuzz fallback
                                      │
                                      ▼
                          [ ListingValidator ]
         Enforces CanonicalCarListing contract & realistic bounds
                                      │
                                      ▼
                         [ DuplicateDetector ]
       Calculates multi-attribute similarity confidence (0.0 to 1.0)
         and flags cross-posted duplicate candidates
                                      │
                                      ▼
                      [ PostgreSQL / SQLite Database ]
      Persists car_listings, sources, and collection_runs
                                      │
                                      ▼
                        [ DataQualityReporter ]
      Computes real empirical completeness & error distributions
```

---

## 2. Key Components

### A. Rate-Limited & Polite HTTP Client (`data_pipeline/collectors/http_client.py`)
- **Configurable Inter-request Delay**: Defaults to 2.0s per request to prevent server overload.
- **Exponential Backoff**: Automatic retry with backoff on HTTP status codes 429 and 5xx.
- **Identifiable User-Agent**: Identifies the project transparently (`AutoValue/0.1 (+https://github.com/autovalue)`).
- **Timeouts**: Strict 10s request timeout to prevent hanging worker threads.

### B. Heterogeneous Source Adapters (`data_pipeline/cleaners/source_adapters.py`)
- Standardizes diverse upstream nomenclatures into canonical `RawCarListing` structures:
  - Price fields: `["asking_price", "selling_price", "cost", "listed_price", "price"]`
  - Odometer fields: `["odometer", "kms_run", "distance_driven", "km_driven", "kms"]`
  - Vehicle make: `["make", "manufacturer", "company", "brand"]`
  - Vehicle model: `["car_model", "model_name", "model"]`

### C. Raw Data Preservation (`data/raw/`)
- Every collection run generates an immutable, timestamped JSON snapshot before transformation.
- In addition, the original raw dictionary is stored inside the `raw_payload` database column on each `CarListing` record, answering: *"Where did this listing originate, and what was its exact raw form?"*

### D. Duplicate Detection & Similarity Scoring (`data_pipeline/deduplication/detector.py`)
- Multi-factor weighted similarity scoring:
  - **Brand Match**: 25% weight (strict equality required)
  - **Model Match**: 25% weight
  - **Registration Year**: 15% weight
  - **Odometer Tolerance**: 15% weight (relative threshold within 5-15%)
  - **Price Ratio**: 10% weight
  - **Location/City**: 10% weight
- Listings matching above the confidence threshold (e.g. 0.82) are flagged as `is_duplicate_candidate = True` with cross-reference `duplicate_of_id` and explanatory notes, preserving both records for downstream empirical analysis without destructive deletion.

### E. Data Quality Reporting (`data_pipeline/validators/quality_report.py`)
- Computes real-time empirical completeness percentages across all valid records for every collection run:
  - `brand`, `model`, `variant`, `year`, `listed_price`, `km_driven`, `fuel_type`, `transmission`, `city`, `state`, `owner_count`, `listing_url`.
- Tracks exact validation rejection reasons.

---

## 3. Running the Ingestion Pipeline

```bash
# Ingest from all configured sources
python data_pipeline/run_collection.py --source all --limit 50

# Ingest specifically from open research datasets
python data_pipeline/run_collection.py --source open_research --limit 50

# Ingest specifically from dealership DMS feeds
python data_pipeline/run_collection.py --source dealer_feed --limit 50
```
