# AutoValue Privacy & Data Governance Policy (Phase 9)

**Effective Date**: October 2026  
**Applicability**: All AutoValue users, valuation API clients, and shared report viewers.

---

## 1. Introduction & Core Principles

AutoValue is committed to transparent, privacy-by-design data handling. We collect only the minimum data necessary to compute empirical vehicle valuations, manage user accounts, and provide valuation history tracking.

---

## 2. Information We Collect

### 2.1 Account Credentials
- **Email Address**: Used solely as the unique account identifier for authentication and account recovery.
- **Password**: Hashed using **bcrypt** (12 work factor rounds) before storage. Plaintext passwords are **never** stored, logged, or transmitted in plaintext.
- **Full Name** *(Optional)*: Stored only if explicitly provided in profile settings.

### 2.2 Vehicle Valuation Inputs & Saved History
- **Vehicle Attributes**: Brand, model, variant, registration year, fuel type, transmission, odometer reading (km), city, asking price, engine displacement (cc), mileage, owner count, and seller type.
- **Valuation Snapshots**: When an authenticated user saves a valuation, an immutable snapshot of the valuation calculation (model interval bounds, market median, comparable count, model version `v002`, dataset version `v0.3`) is preserved.

### 2.3 Bookmarked Vehicles
- Saved vehicle configurations saved by the user for ongoing market tracking.

### 2.4 Share Tokens
- When a user chooses to generate a shareable report, a cryptographically secure, 256-bit URL-safe token is created (`/shared/{share_token}`).

---

## 3. Information We DO NOT Collect

- We do not collect credit card, bank account, or payment credentials.
- We do not track user geolocation or mobile device identifiers.
- We do not use third-party behavioral advertising trackers or analytics pixels.
- We do not sell user data or valuation queries to third-party data brokers.

---

## 4. Public Shareable Report Privacy Boundaries

When a valuation report is viewed via its public share token (`GET /api/shared/{token}`), AutoValue enforces strict privacy boundaries:

| Data Field | Included in Public Shared View? |
|---|---|
| Vehicle Specifications & Valuations | **Yes** (Model Estimate, Uncertainty Bounds, Market Median) |
| Comparable Market Listings | **Yes** (Anonymized Market Data) |
| User Email Address | **NO** (Strictly excluded) |
| User Account ID | **NO** (Strictly excluded) |
| Internal Database IDs | **NO** (Strictly excluded) |
| Internal User Profile Notes | **NO** (Strictly excluded) |

Users can revoke sharing at any time via `DELETE /api/valuations/{id}/share`, which immediately terminates public access.

---

## 5. Session Management & Cookies

AutoValue uses secure session management:
- **HTTP-Only Cookies**: Authentication session tokens are stored in `autovalue_token` cookies with the `HttpOnly` flag enabled, preventing cross-site scripting (XSS) access.
- **Secure Flag**: In production, cookies require HTTPS transmission (`COOKIE_SECURE=True`).
- **SameSite Protection**: Configured with `SameSite=Lax` to prevent Cross-Site Request Forgery (CSRF).

---

## 6. Self-Service Account Deletion (Right to Erasure)

Users have the right to permanently erase all personal data at any time:
- **Endpoint**: `DELETE /api/auth/me`
- **Cascade Behavior**: Deletes the user account, all saved valuation records, bookmarked vehicles, and active share tokens.
- **Public Datasets**: System-level benchmark datasets and ML model artifacts remain intact as they contain no user-specific identifiers.

---

## 7. Valuation & Market Data Disclaimers

- **Asking Prices vs. Final Transactions**: The market comparables and historical trends displayed in AutoValue reflect observed market asking prices from verified listings. Actual private or dealer transaction prices may vary based on negotiation and physical vehicle condition.
- **Model Estimates**: Model valuations are statistical predictions derived from machine learning algorithms (XGBoost `v002`) and do not constitute legal guarantees of resale value.
