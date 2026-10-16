# AutoValue Valuation History & Immutable Snapshots (Phase 8)

## 1. Immutability Architecture
A core requirement of AutoValue is that saved valuation records are **immutable snapshots**.

When a user saves a valuation:
1. The vehicle inputs (brand, model, variant, year, fuel, transmission, odometer, city, asking price) are captured.
2. The exact model output metrics (point estimate, conformal prediction intervals, comparable market range, comparable count, model version `v002`, dataset version `v0.3`) are stored in tabular columns.
3. The full response envelope (including SHAP feature attributions, individual comparable listings, and market positions) is serialized into `payload_json`.

### Historical Integrity Guarantee:
- If AutoValue retrains or upgrades models (e.g. from `v002` to `v003`), previous valuation snapshots are **never recomputed**.
- Users viewing a report from months earlier see the authentic estimate that existed when the analysis was performed.

---

## 2. Valuation History API Endpoints

### List History: `GET /api/valuations`
- **Query Parameters**:
  - `page` (default `1`, integer >= 1)
  - `page_size` (default `10`, integer 1-50)
  - `brand` (optional string filter)
  - `model` (optional string filter)
- **Ordering**: Deterministic sorting by `created_at DESC`.
- **Response**:
```json
{
  "items": [
    {
      "id": "7bf3b6ca-ffaa-419b-a3da-f703565b53e8",
      "brand": "Hyundai",
      "model": "Creta",
      "variant": "1.5 CRDi SX",
      "year": 2021,
      "km_driven": 38000,
      "city": "Pune",
      "estimated_value": 1320000.0,
      "range_low": 1240000.0,
      "range_high": 1400000.0,
      "model_interval_low": 1250000.0,
      "model_interval_high": 1390000.0,
      "market_median": 1340000.0,
      "comparable_count": 5,
      "model_version": "v002",
      "dataset_version": "v0.3",
      "is_shared": false,
      "created_at": "2026-10-03T12:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 10,
  "total_pages": 1
}
```

### Get Single Valuation: `GET /api/valuations/{valuation_id}`
- **Security Check**: Enforces ownership (`valuation.user_id == current_user.id`).
- Returns full details and deserialized `payload` for complete interactive report rendering.

### Save Valuation: `POST /api/valuations`
- **Payload**: `SaveValuationRequest` containing `vehicle` specifications and `valuation_result`.

### Delete Valuation: `DELETE /api/valuations/{valuation_id}`
- Deletes record and cascades deletion of any associated public share tokens.
