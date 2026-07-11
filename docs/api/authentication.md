# Authentication API

OptiAgent REST API — `/api/v1/auth`

---

## Overview

The authentication endpoints handle user login, logout, token refresh, and current-user retrieval. All responses use the shared `ApiResponse` envelope:

**Success:**
```json
{
  "success": true,
  "data": <T>
}
```

**Error:**
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message."
  }
}
```

All auth endpoints are public (no `Authorization` header required) except `GET /auth/me`.

---

## Schemas

### LoginRequest

```typescript
{
  email:    string;   // Valid email address
  password: string;   // Minimum 8 characters
}
```

### AuthResponse

```typescript
{
  accessToken:  string;   // RS256-signed JWT, 15-minute expiry
  refreshToken: string;   // Opaque random string, 7-day expiry
  user: AuthUser;
}
```

### AuthUser

```typescript
{
  id:          string;
  email:       string;
  displayName: string;
  roles:       string[];       // e.g. ["HR_MANAGER"]
  permissions: string[];       // Resolved permission strings, e.g. ["users:read", "ai:query"]
  isActive:    boolean;
}
```

---

## Endpoints

---

### POST /api/v1/auth/login

Authenticates a user with email and password. Returns a token pair and the authenticated user's profile.

**Authentication required:** No

**Request body:** `LoginRequest`

```json
{
  "email":    "jane.doe@optiagent.com",
  "password": "SecurePass123!"
}
```

**Response:** `ApiResponse<AuthResponse>` — HTTP 200

```json
{
  "success": true,
  "data": {
    "accessToken":  "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refreshToken": "d4e8f3a1-9b2c-4f5d-a6e7-8c1b0f3d2e4a",
    "user": {
      "id":          "usr_01HZXK9...",
      "email":       "jane.doe@optiagent.com",
      "displayName": "Jane Doe",
      "roles":       ["HR_MANAGER"],
      "permissions": ["users:read", "ai:query"],
      "isActive":    true
    }
  }
}
```

**Error responses:**

| HTTP | Code | Condition |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Request body fails schema validation |
| 401 | `INVALID_CREDENTIALS` | Email not found or password incorrect |
| 403 | `ACCOUNT_INACTIVE` | User account has been deactivated |

**Notes:**
- The `accessToken` JWT payload contains `{ sub, email, permissions[], iat, exp }`.
- The `refreshToken` is stored in Redis with the user ID. It is single-use: consuming it during a refresh call immediately invalidates it.
- Callers should store the `refreshToken` in `sessionStorage` and the `accessToken` in memory only.

---

### POST /api/v1/auth/logout

Revokes the caller's refresh token. The access token cannot be revoked (it expires naturally after 15 minutes), but the refresh token is deleted from Redis immediately, preventing further silent refreshes.

**Authentication required:** No (but a valid refresh token must be supplied)

**Request body:**

```json
{
  "refreshToken": "d4e8f3a1-9b2c-4f5d-a6e7-8c1b0f3d2e4a"
}
```

**Response:** `ApiResponse<{ loggedOut: true }>` — HTTP 200

```json
{
  "success": true,
  "data": {
    "loggedOut": true
  }
}
```

**Error responses:**

| HTTP | Code | Condition |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Request body missing `refreshToken` field |

**Notes:**
- If the provided refresh token does not exist in Redis (already expired or already used), the endpoint still returns `{ loggedOut: true }`. Logout is idempotent from the caller's perspective.
- After calling this endpoint, the client must clear all stored tokens and reset Redux state.

---

### POST /api/v1/auth/refresh

Issues a new token pair in exchange for a valid refresh token. The provided refresh token is immediately invalidated and replaced with a new one (rotation).

**Authentication required:** No (but a valid refresh token must be supplied)

**Request body:**

```json
{
  "refreshToken": "d4e8f3a1-9b2c-4f5d-a6e7-8c1b0f3d2e4a"
}
```

**Response:** `ApiResponse<{ accessToken: string; refreshToken: string }>` — HTTP 200

```json
{
  "success": true,
  "data": {
    "accessToken":  "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refreshToken": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }
}
```

**Error responses:**

| HTTP | Code | Condition |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Request body missing `refreshToken` field |
| 401 | `INVALID_REFRESH_TOKEN` | Token not found in Redis (expired, used, or revoked) |

**Notes:**
- Refresh token rotation: each token can only be used once. The old token is deleted from Redis before the new one is stored. If an attacker attempts to replay a stolen refresh token after the legitimate client has already used it, the Redis lookup fails and a 401 is returned.
- The response does not include the user object. Callers should decode the new `accessToken` JWT to re-read the user's permissions if needed, or call `GET /auth/me`.

---

### GET /api/v1/auth/me

Returns the currently authenticated user's profile.

**Authentication required:** Yes — `Authorization: Bearer <accessToken>`

**Request body:** None

**Response:** `ApiResponse<AuthUser>` — HTTP 200

```json
{
  "success": true,
  "data": {
    "id":          "usr_01HZXK9...",
    "email":       "jane.doe@optiagent.com",
    "displayName": "Jane Doe",
    "roles":       ["HR_MANAGER"],
    "permissions": ["users:read", "ai:query"],
    "isActive":    true
  }
}
```

**Error responses:**

| HTTP | Code | Condition |
|---|---|---|
| 401 | `MISSING_TOKEN` | No `Authorization` header present |
| 401 | `INVALID_TOKEN` | JWT signature invalid or token expired |
| 403 | `ACCOUNT_INACTIVE` | User account was deactivated after token was issued |

**Notes:**
- This endpoint re-reads the user record from the database to reflect any permission or role changes that occurred after the JWT was issued.
- Useful after a token refresh to synchronize the client-side user state without requiring a full re-login.
