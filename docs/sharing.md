# AutoValue Shareable Reports & Token Architecture (Phase 8)

## 1. Overview
AutoValue enables users to generate unguessable, read-only public share links for their saved valuation reports. This allows buyers, sellers, or dealership partners to review valuation methodology, SHAP attributions, and comparable listings without requiring an account.

---

## 2. Security & Sanitization Model
1. **Cryptographic Unpredictability**:
   - Share tokens are generated using Python's `secrets.token_urlsafe(32)`, providing 256 bits of entropy.
   - Tokens cannot be brute-forced or guessed.
2. **Strict Sanitization**:
   - The public share endpoint (`GET /api/shared/{token}`) excludes:
     - User IDs (`user_id`, `User.id`)
     - Email addresses
     - Passwords and password hashes
     - Internal database IDs of other records
     - Telemetry request metadata
3. **Revocation & Expiration**:
   - The report owner can revoke sharing at any time via `DELETE /api/valuations/{id}/share`.
   - Once revoked, subsequent requests to `/shared/{token}` immediately return HTTP 404 Not Found.
4. **View Tracking**:
   - Each access increments the `view_count` on the `ShareToken` record.

---

## 3. Endpoints

### Enable / Retrieve Share Token: `POST /api/valuations/{id}/share`
- **Authentication**: Required (Owner only)
- **Response**:
```json
{
  "share_token": "jL3x_K9qZ8b4mN2vP6tW1rY5uI7oE0aD9sF4gH1jK2l",
  "share_url": "/shared/jL3x_K9qZ8b4mN2vP6tW1rY5uI7oE0aD9sF4gH1jK2l",
  "is_active": true,
  "created_at": "2026-10-03T12:00:00Z",
  "view_count": 0
}
```

### Revoke Share Token: `DELETE /api/valuations/{id}/share`
- **Authentication**: Required (Owner only)
- **Response**: `{"message": "Public sharing link has been revoked."}`

### Public Report View: `GET /api/shared/{token}`
- **Authentication**: Public / None required
- **Response**: Sanitized `SharedValuationResponse` with full valuation snapshots and disclaimers.
