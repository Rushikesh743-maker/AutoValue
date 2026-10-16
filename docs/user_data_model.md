# AutoValue User Data Model & Schema (Phase 8)

## 1. Entity Relationship Overview

```mermaid
erDiagram
    USERS ||--o{ SAVED_VALUATIONS : owns
    USERS ||--o{ SAVED_VEHICLES : bookmarks
    SAVED_VALUATIONS ||--o| SHARE_TOKENS : generates

    USERS {
        string id PK "UUID (CHAR 36)"
        string email UK "Unique index, normalized lowercase"
        string password_hash "Bcrypt 12 rounds"
        string full_name "Nullable"
        boolean is_active "Default true"
        datetime created_at "Indexed"
        datetime updated_at "On update timestamp"
        datetime last_login_at "Nullable"
    }

    SAVED_VALUATIONS {
        string id PK "UUID (CHAR 36)"
        string user_id FK "References users.id ON DELETE CASCADE"
        string request_id "Traceability ID"
        datetime created_at "Indexed"
        string brand "Make name"
        string model "Model name"
        string variant "Trim"
        int year "Manufacturing year"
        string fuel_type "Petrol / Diesel / CNG / EV"
        string transmission "Manual / Automatic"
        int km_driven "Odometer"
        string city "Location"
        float estimated_value "Calculated estimate in INR"
        float range_low "Empirical lower bound"
        float range_high "Empirical upper bound"
        float model_interval_low "Uncertainty bound"
        float model_interval_high "Uncertainty bound"
        float market_median "Comparable median"
        int comparable_count "Count of comparables"
        string model_version "Engine version (e.g. v002)"
        string dataset_version "Data version (e.g. v0.3)"
        text payload_json "Full serialized immutable snapshot"
        string notes "User notes"
    }

    SAVED_VEHICLES {
        string id PK "UUID (CHAR 36)"
        string user_id FK "References users.id ON DELETE CASCADE"
        string brand "Make"
        string model "Model"
        string variant "Trim"
        int year "Year"
        string fuel_type "Fuel"
        string transmission "Transmission"
        int km_driven "KM"
        string city "City"
        string notes "Notes"
        datetime created_at "Indexed"
    }

    SHARE_TOKENS {
        string id PK "UUID (CHAR 36)"
        string valuation_id FK "References saved_valuations.id ON DELETE CASCADE (Unique)"
        string token UK "Cryptographic URL-safe token (256-bit entropy)"
        boolean is_active "Revocable status"
        datetime created_at "Creation timestamp"
        datetime expires_at "Nullable expiration"
        int view_count "Access counter"
    }
```

---

## 2. Database Constraints & Indexing Strategy
1. **Uniqueness Constraints**:
   - `users.email`: Unique index preventing duplicate registrations.
   - `saved_vehicles`: Unique fingerprint constraint `uq_user_saved_vehicle_fingerprint` across `(user_id, brand, model, variant, year, fuel_type, transmission, km_driven, city)`.
   - `share_tokens.token`: Unique index for public access.
   - `share_tokens.valuation_id`: 1:1 relationship with saved valuations.
2. **Deterministic Query Indexes**:
   - `ix_saved_valuations_user_created` (`user_id`, `created_at` DESC) to optimize history pagination and avoid N+1 scans.
   - `ix_saved_vehicles_user_created` (`user_id`, `created_at` DESC) for rapid bookmark retrieval.
   - `ix_share_tokens_token_active` (`token`, `is_active`) for fast lookup on public report pages.
