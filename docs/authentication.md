# AutoValue Authentication Architecture (Phase 8)

## 1. Overview
AutoValue provides secure user authentication allowing automotive buyers, sellers, and analysts to register, log in, maintain personalized valuation history, bookmark vehicle configurations, and manage public report sharing.

---

## 2. Authentication Mechanism & Design Principles
- **Password Security**:
  - Minimum length 8 characters, maximum 128 characters.
  - Hashed using **bcrypt** with 12 salt rounds (`bcrypt.gensalt(rounds=12)`).
  - Plaintext passwords are never stored in the database or logged in telemetry.
- **Email Normalization & Enumeration Protection**:
  - Email addresses are stripped of whitespace and converted to lowercase prior to database queries.
  - Login failures return generic 401 Unauthorized messages (`"Invalid email or password"`) preventing account enumeration attacks.
- **Session & Token Management**:
  - Tokens are signed JWTs using **HS256** with configurable expiration (`ACCESS_TOKEN_EXPIRE_MINUTES`, default 1440 min / 24 hours).
  - Dual-mode client authentication:
    1. **HTTP-only Cookies** (`autovalue_token`) with `SameSite=lax` and configurable `Secure` flag for web browser sessions.
    2. **Bearer Token Authorization Header** (`Authorization: Bearer <token>`) for programmatic API consumers and mobile/headless clients.
- **Environment-Driven Secrets**:
  - JWT signing key is derived strictly from `AUTH_SECRET` or `SECRET_KEY` environment variables.

---

## 3. API Endpoints

### Registration: `POST /api/auth/register`
- **Request Body**:
```json
{
  "email": "analyst@example.com",
  "password": "StrongPassword123!",
  "full_name": "Rohan Sharma"
}
```
- **Response** (HTTP 201 Created):
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "user": {
    "id": "2e38cab1-ab5a-4146-a998-f12cb4ad3301",
    "email": "analyst@example.com",
    "full_name": "Rohan Sharma",
    "is_active": true,
    "created_at": "2026-10-03T12:00:00Z",
    "last_login_at": "2026-10-03T12:00:00Z"
  }
}
```

### Login: `POST /api/auth/login`
- **Request Body**:
```json
{
  "email": "analyst@example.com",
  "password": "StrongPassword123!"
}
```
- **Response** (HTTP 200 OK): Returns JWT token, user profile, and sets `autovalue_token` session cookie.

### Logout: `POST /api/auth/logout`
- **Response** (HTTP 200 OK): Clears the session cookie.

### Current User Profile: `GET /api/auth/me`
- **Authentication**: Required (Bearer token or session cookie)
- **Response** (HTTP 200 OK): Returns `UserResponse` without password or hash fields.

### Account Deletion: `DELETE /api/auth/me`
- **Authentication**: Required
- **Cascade Behavior**: Permanently deletes user account and automatically cascades to remove saved valuations, bookmarks, and share tokens. Does not alter public models or dataset artifacts.
