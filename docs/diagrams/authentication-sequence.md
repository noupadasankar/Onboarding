# Authentication Sequence Diagrams

OptiAgent — Auth Flows

---

## 1. Login Flow

A user submits their credentials. The backend validates them, issues a JWT access token (RS256) and a refresh token, stores the refresh token in Redis, and returns both to the client.

```
Browser / Client        Node.js Backend          PostgreSQL              Redis
       │                       │                       │                    │
       │  POST /api/v1/auth/login                      │                    │
       │  { email, password }  │                       │                    │
       │──────────────────────►│                       │                    │
       │                       │                       │                    │
       │                       │  SELECT user          │                    │
       │                       │  WHERE email = ?      │                    │
       │                       │──────────────────────►│                    │
       │                       │                       │                    │
       │                       │  [user row + roles    │                    │
       │                       │   + role permissions] │                    │
       │                       │◄──────────────────────│                    │
       │                       │                       │                    │
       │                       │ ┌─────────────────────────────────────┐   │
       │                       │ │ Validate password against bcrypt    │   │
       │                       │ │ hash. Throw INVALID_CREDENTIALS if  │   │
       │                       │ │ mismatch.                           │   │
       │                       │ └─────────────────────────────────────┘   │
       │                       │                       │                    │
       │                       │ ┌─────────────────────────────────────┐   │
       │                       │ │ Resolve permissions:                │   │
       │                       │ │ Flatten and deduplicate permissions │   │
       │                       │ │ from all user roles.               │   │
       │                       │ └─────────────────────────────────────┘   │
       │                       │                       │                    │
       │                       │ ┌─────────────────────────────────────┐   │
       │                       │ │ Issue accessToken (RS256):          │   │
       │                       │ │ payload: { sub, email,              │   │
       │                       │ │           permissions[], iat, exp } │   │
       │                       │ │ Signed with private key.            │   │
       │                       │ │ Expiry: 15 minutes.                 │   │
       │                       │ └─────────────────────────────────────┘   │
       │                       │                       │                    │
       │                       │ ┌─────────────────────────────────────┐   │
       │                       │ │ Generate refreshToken:              │   │
       │                       │ │ Cryptographically random UUID v4.  │   │
       │                       │ └─────────────────────────────────────┘   │
       │                       │                       │                    │
       │                       │  SET refreshToken →   │                    │
       │                       │  userId (TTL 7d)       │                    │
       │                       │───────────────────────────────────────────►│
       │                       │                       │                    │
       │                       │ ┌─────────────────────────────────────┐   │
       │                       │ │ Write audit log:                    │   │
       │                       │ │ action: "USER_LOGIN"                │   │
       │                       │ │ (non-fatal, fire-and-forget)        │   │
       │                       │ └─────────────────────────────────────┘   │
       │                       │                       │                    │
       │  HTTP 200             │                       │                    │
       │  { accessToken,       │                       │                    │
       │    refreshToken,      │                       │                    │
       │    user: { id, email, │                       │                    │
       │    roles, permissions }│                      │                    │
       │◄──────────────────────│                       │                    │
       │                       │                       │                    │
       │ [Client stores:       │                       │                    │
       │  accessToken → Redux  │                       │                    │
       │  refreshToken → sessionStorage]               │                    │
```

---

## 2. Authenticated Request Flow

After login, every protected API call carries the access token. The `authenticate` middleware validates it locally (no database or Redis lookup required).

```
Browser / Client        NGINX               Node.js Backend
       │                   │                       │
       │  GET /api/v1/...  │                       │
       │  Authorization:   │                       │
       │  Bearer <token>   │                       │
       │──────────────────►│                       │
       │                   │  Forward + requestId  │
       │                   │──────────────────────►│
       │                   │                       │
       │                   │      ┌────────────────▼────────────────────┐
       │                   │      │  authenticate middleware             │
       │                   │      │                                     │
       │                   │      │  1. Extract "Bearer <token>"        │
       │                   │      │     from Authorization header.      │
       │                   │      │                                     │
       │                   │      │  2. Verify RS256 signature using    │
       │                   │      │     the public key (in-memory).     │
       │                   │      │     No network call required.       │
       │                   │      │                                     │
       │                   │      │  3. Check exp claim:                │
       │                   │      │     If expired → 401.              │
       │                   │      │                                     │
       │                   │      │  4. Populate req.auth:             │
       │                   │      │     {                              │
       │                   │      │       userId:      jwt.sub,        │
       │                   │      │       email:       jwt.email,      │
       │                   │      │       permissions: jwt.permissions │
       │                   │      │     }                              │
       │                   │      │                                     │
       │                   │      │  5. Call next() — request proceeds. │
       │                   │      └────────────────┬────────────────────┘
       │                   │                       │
       │                   │      ┌────────────────▼────────────────────┐
       │                   │      │  authorize middleware                │
       │                   │      │  Check req.auth.permissions         │
       │                   │      │  contains required permission.      │
       │                   │      └────────────────┬────────────────────┘
       │                   │                       │
       │                   │      [controller → service → repo → DB]
       │                   │                       │
       │  HTTP 200         │                       │
       │◄──────────────────│◄──────────────────────│
```

---

## 3. Token Refresh Flow

Access tokens expire after 15 minutes. The client uses the stored refresh token to obtain a new token pair without requiring the user to log in again. Refresh token rotation ensures each token can only be used once.

```
Browser / Client        Node.js Backend                         Redis
       │                       │                                   │
       │  [accessToken expires │                                   │
       │   — RTK Query         │                                   │
       │   intercepts 401]     │                                   │
       │                       │                                   │
       │  POST /api/v1/auth/refresh                                │
       │  { refreshToken:      │                                   │
       │    "<current>" }      │                                   │
       │──────────────────────►│                                   │
       │                       │                                   │
       │                       │  GET refreshToken key             │
       │                       │──────────────────────────────────►│
       │                       │                                   │
       │                       │  ┌── FOUND: userId ──┐            │
       │                       │  │  (token is valid) │            │
       │                       │◄──────────────────────────────────│
       │                       │                                   │
       │                       │ ┌─────────────────────────────────────┐
       │                       │ │ ATOMIC ROTATION:                    │
       │                       │ │                                     │
       │                       │ │ Step 1: DEL current refreshToken    │
       │                       │ │  — prevents replay attacks          │
       │                       │ └─────────────────────────────────────┘
       │                       │  DEL <current refreshToken>       │
       │                       │──────────────────────────────────►│
       │                       │                                   │
       │                       │ ┌─────────────────────────────────────┐
       │                       │ │ Step 2: Issue new accessToken       │
       │                       │ │  RS256, 15-min expiry.              │
       │                       │ │ Step 3: Generate new refreshToken   │
       │                       │ │  UUID v4, opaque, random.           │
       │                       │ └─────────────────────────────────────┘
       │                       │                                   │
       │                       │  SET newRefreshToken → userId     │
       │                       │  (TTL 7 days)                     │
       │                       │──────────────────────────────────►│
       │                       │                                   │
       │  HTTP 200             │                                   │
       │  { accessToken:  "<new>",                                 │
       │    refreshToken: "<new>" }                                │
       │◄──────────────────────│                                   │
       │                       │                                   │
       │ [Client stores new    │                                   │
       │  token pair, retries  │                                   │
       │  original request]    │                                   │
       │                       │                                   │
       │                       │                                   │
  ── Replay Attack Path ────────────────────────────────────────────
       │                       │                                   │
       │  [Attacker replays    │                                   │
       │   old refreshToken    │                                   │
       │   after legitimate    │                                   │
       │   client used it]     │                                   │
       │                       │                                   │
       │  POST /auth/refresh   │                                   │
       │  { refreshToken: "<old>" }                                │
       │──────────────────────►│                                   │
       │                       │  GET <old refreshToken>           │
       │                       │──────────────────────────────────►│
       │                       │                                   │
       │                       │  ── NOT FOUND (was deleted) ───── │
       │                       │◄──────────────────────────────────│
       │                       │                                   │
       │  HTTP 401             │                                   │
       │  INVALID_REFRESH_TOKEN│                                   │
       │◄──────────────────────│                                   │
```

---

## 4. Logout Flow

The client sends the current refresh token. The backend deletes it from Redis, preventing any further silent refreshes. The access token expires naturally.

```
Browser / Client        Node.js Backend                         Redis
       │                       │                                   │
       │  POST /api/v1/auth/logout                                 │
       │  { refreshToken:      │                                   │
       │    "<current>" }      │                                   │
       │──────────────────────►│                                   │
       │                       │                                   │
       │                       │ ┌─────────────────────────────────────┐
       │                       │ │ Validate request body:              │
       │                       │ │ refreshToken field must be present. │
       │                       │ └─────────────────────────────────────┘
       │                       │                                   │
       │                       │  DEL <refreshToken>               │
       │                       │──────────────────────────────────►│
       │                       │                                   │
       │                       │  OK (or key not found — both OK)  │
       │                       │◄──────────────────────────────────│
       │                       │                                   │
       │                       │ ┌─────────────────────────────────────┐
       │                       │ │ Write audit log:                    │
       │                       │ │ action: "USER_LOGOUT"               │
       │                       │ │ (non-fatal, fire-and-forget)        │
       │                       │ └─────────────────────────────────────┘
       │                       │                                   │
       │  HTTP 200             │                                   │
       │  { loggedOut: true }  │                                   │
       │◄──────────────────────│                                   │
       │                       │                                   │
       │ [Client clears Redux  │                                   │
       │  auth state, clears   │                                   │
       │  sessionStorage,      │                                   │
       │  resets RTK Query     │                                   │
       │  cache, redirects     │                                   │
       │  to /login]           │                                   │
       │                       │                                   │
  ── After Logout ─────────────────────────────────────────────────
       │                       │                                   │
       │  POST /auth/refresh   │                                   │
       │  (any attempt with    │                                   │
       │   revoked token)      │                                   │
       │──────────────────────►│                                   │
       │                       │  GET <refreshToken> → NOT FOUND   │
       │                       │──────────────────────────────────►│
       │                       │◄──────────────────────────────────│
       │  HTTP 401             │                                   │
       │◄──────────────────────│                                   │
```
