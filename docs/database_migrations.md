# AutoValue — Database Migrations Guide

## 1. Overview

AutoValue uses [Alembic](https://alembic.sqlalchemy.org/) alongside SQLAlchemy 2.0 to manage relational schema versioning and deterministic schema evolution.

All schema definitions live in `backend/app/models/` and are mirrored in versioned migration scripts in `alembic/versions/`.

---

## 2. Migration Environment & Configuration

- **Config File:** `alembic.ini`
- **Environment Script:** `alembic/env.py` (reads `DATABASE_URL` dynamically from `backend.app.core.config.settings`)
- **Versions Directory:** `alembic/versions/`

---

## 3. Standard Migration Commands

### Run Pending Migrations (Upgrade to Head)
```bash
alembic upgrade head
```

### Roll Back Last Migration
```bash
alembic downgrade -1
```

### Roll Back to Specific Revision
```bash
alembic downgrade <revision_id>
```

### Check Current Migration Revision
```bash
alembic current
```

### View Migration History
```bash
alembic history --verbose
```

---

## 4. Development Workflow: Creating New Migrations

1. **Update ORM Models:**
   Modify or add models in `backend/app/models/`.

2. **Generate New Migration Revision:**
   ```bash
   alembic revision -m "add_column_name_to_table"
   ```
   Or generate autodetected diff:
   ```bash
   alembic revision --autogenerate -m "describe_changes"
   ```

3. **Inspect and Verify Migration Script:**
   Review the generated file in `alembic/versions/` to verify `upgrade()` and `downgrade()` logic.

4. **Apply and Test Locally:**
   ```bash
   alembic upgrade head
   python -m pytest -v
   ```

---

## 5. Schema & Indexing Strategy

### Tables
1. `sources`: Data source providers (e.g. `open_research`, `dealer_network`).
2. `collection_runs`: Audit history of data ingestion batches.
3. `car_listings`: Processed and raw canonical car listings.

### Indexing Rationale
- **Single-Column Indexes:**
  - `brand`, `model`, `year`, `city`, `date_collected`, `source`, `is_duplicate_candidate`
  - Facilitates fast filtering during comparable search and data-quality analysis.
- **Composite Indexes:**
  - `ix_listings_brand_model_year`: Optimized for comparable search queries with model & year bounds.
  - `ix_listings_brand_model_city`: Optimized for location-based market comparisons.
  - `ix_listings_brand_model_date`: Optimized for historical price trend analysis and time-series aggregation.
  - `ix_listings_source_listing_id`: Optimized for duplicate prevention and upsert checks during collection.
