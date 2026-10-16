# AutoValue Phase 8 Security & Privacy Architecture

## 1. Security Architecture Summary

AutoValue Phase 8 extends all prior Phase 1–7 security, observability, and resilience controls with user-facing authentication and authorization protections.

| Security Domain | Implementation | Threat Mitigated |
|---|---|---|
| **Password Storage** | Bcrypt with 12 salt rounds | Credential dumping / Rainbow tables |
| **Authentication Flow** | Dual-mode: HTTP-only cookies (`SameSite=lax`) + Bearer JWT | Cross-Site Scripting (XSS) token theft |
| **Account Enumeration** | Normalized email + generic 401 error message | User enumeration / Account harvesting |
| **Authorization & IDOR** | Database-level user ownership verification on all endpoints | Insecure Direct Object Reference (IDOR) |
| **Share Link Security** | `secrets.token_urlsafe(32)` (256-bit entropy) | Token prediction / URL enumeration |
| **Data Minimization** | Dedicated Pydantic response models excluding sensitive fields | Data leakage / Unintentional exposure |
| **Input Validation** | Pydantic v2 strict typing, string length & range bounds | Injection / Malformed payloads |
| **Rate Limiting** | Sliding window IP rate limiting middleware | DoS / Brute-force requests |
| **Body Size Limit** | 1MB request payload enforcement | Memory exhaustion DoS |
| **Telemetry Privacy** | Sensitive headers & passwords filtered from structured logs | Log credential leakage |
| **Data Rights** | Cascade account deletion (`DELETE /api/auth/me`) | Privacy compliance / User data sovereignty |

---

## 2. IDOR Prevention Pattern
All user-owned resource queries (saved valuations, bookmarks, share tokens) apply direct user filter constraints:

```python
valuation = db.query(SavedValuation).filter(SavedValuation.id == valuation_id).first()
if not valuation:
    raise HTTPException(status_code=404, detail="Valuation record not found.")

if valuation.user_id != current_user.id:
    raise HTTPException(status_code=403, detail="Access forbidden.")
```

---

## 3. Account Deletion & Cascading Clean-up
When a user exercises their data deletion right:
1. `DELETE /api/auth/me` deletes the `User` record in PostgreSQL.
2. SQLAlchemy and PostgreSQL foreign key cascade rules (`ondelete="CASCADE"`) automatically delete all dependent records:
   - `saved_valuations`
   - `saved_vehicles`
   - `share_tokens`
3. The session cookie is cleared on the response.
4. Core shared datasets, preprocessors, and ML model artifacts remain untouched.
