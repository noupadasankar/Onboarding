# Request Flow Diagrams

OptiAgent — Authenticated Request Lifecycle

---

## 1. Standard Authenticated Request

The following diagram shows the complete lifecycle of an authenticated API request — in this example, `GET /api/v1/users` — from the browser through the full middleware chain to the database and back.

```
Browser                NGINX               Node.js Backend                PostgreSQL
  │                      │                        │                            │
  │  GET /api/v1/users   │                        │                            │
  │  Authorization:      │                        │                            │
  │  Bearer <token>      │                        │                            │
  │─────────────────────►│                        │                            │
  │                      │  Proxy to :8000        │                            │
  │                      │  (forward headers +    │                            │
  │                      │   X-Request-ID)        │                            │
  │                      │───────────────────────►│                            │
  │                      │                        │                            │
  │                      │          ┌─────────────▼──────────────────────┐    │
  │                      │          │  [1] requestId middleware           │    │
  │                      │          │  Assign UUID correlation ID.       │    │
  │                      │          │  Set req.requestId + X-Request-ID  │    │
  │                      │          │  response header.                  │    │
  │                      │          └─────────────┬──────────────────────┘    │
  │                      │                        │                            │
  │                      │          ┌─────────────▼──────────────────────┐    │
  │                      │          │  [2] requestLogger middleware       │    │
  │                      │          │  Log: method, URL, requestId,      │    │
  │                      │          │  timestamp. (start timer)          │    │
  │                      │          └─────────────┬──────────────────────┘    │
  │                      │                        │                            │
  │                      │          ┌─────────────▼──────────────────────┐    │
  │                      │          │  [3] authenticate middleware        │    │
  │                      │          │  - Extract Bearer token            │    │
  │                      │          │  - Verify RS256 signature          │    │
  │                      │          │  - Check exp claim                 │    │
  │                      │          │  - Populate req.auth:              │    │
  │                      │          │    { userId, email, permissions }  │    │
  │                      │          └─────────────┬──────────────────────┘    │
  │                      │                        │                            │
  │                      │          ┌─────────────▼──────────────────────┐    │
  │                      │          │  [4] authorize middleware           │    │
  │                      │          │  Check req.auth.permissions        │    │
  │                      │          │  includes "users:read".            │    │
  │                      │          │  Throw ForbiddenError if not.      │    │
  │                      │          └─────────────┬──────────────────────┘    │
  │                      │                        │                            │
  │                      │          ┌─────────────▼──────────────────────┐    │
  │                      │          │  [5] validate middleware            │    │
  │                      │          │  Run Zod schema against            │    │
  │                      │          │  req.query (page, pageSize,        │    │
  │                      │          │  search, role, isActive).          │    │
  │                      │          │  Throw ValidationError if invalid. │    │
  │                      │          └─────────────┬──────────────────────┘    │
  │                      │                        │                            │
  │                      │          ┌─────────────▼──────────────────────┐    │
  │                      │          │  [6] UserController.listUsers()     │    │
  │                      │          │  Extract validated query params.   │    │
  │                      │          │  Call UserService.listUsers().     │    │
  │                      │          └─────────────┬──────────────────────┘    │
  │                      │                        │                            │
  │                      │          ┌─────────────▼──────────────────────┐    │
  │                      │          │  [7] UserService.listUsers()        │    │
  │                      │          │  Apply business logic.             │    │
  │                      │          │  Call UserRepository.findMany().   │    │
  │                      │          └─────────────┬──────────────────────┘    │
  │                      │                        │                            │
  │                      │          ┌─────────────▼──────────────────────┐    │
  │                      │          │  [8] PrismaUserRepository           │    │
  │                      │          │  .findMany()                       │    │
  │                      │          │  Build Prisma query with filters.  │    │
  │                      │          └─────────────┬──────────────────────┘    │
  │                      │                        │                            │
  │                      │                        │  SELECT users ...          │
  │                      │                        │───────────────────────────►│
  │                      │                        │                            │
  │                      │                        │  [rows]                    │
  │                      │                        │◄───────────────────────────│
  │                      │                        │                            │
  │                      │          ┌─────────────▼──────────────────────┐    │
  │                      │          │  [9] Controller wraps result        │    │
  │                      │          │  in ApiResponse envelope.          │    │
  │                      │          │  res.json({ success: true,         │    │
  │                      │          │             data: paginatedResult })│    │
  │                      │          │  requestLogger logs response time. │    │
  │                      │          └─────────────┬──────────────────────┘    │
  │                      │                        │                            │
  │                      │  HTTP 200 + body        │                            │
  │                      │◄───────────────────────│                            │
  │                      │                        │                            │
  │  HTTP 200 + body     │                        │                            │
  │◄─────────────────────│                        │                            │
  │                      │                        │                            │
```

---

## 2. Error Path: Insufficient Permissions

When a user without the required permission makes the same request, the chain short-circuits at step [4]:

```
Browser                NGINX               Node.js Backend
  │                      │                        │
  │  GET /api/v1/users   │                        │
  │  (user lacks         │                        │
  │   users:read)        │                        │
  │─────────────────────►│───────────────────────►│
  │                      │                        │
  │                      │          [1] requestId  │
  │                      │          [2] requestLogger
  │                      │          [3] authenticate → OK
  │                      │                        │
  │                      │          ┌─────────────▼──────────────────────┐
  │                      │          │  [4] authorize                     │
  │                      │          │  req.auth.permissions does NOT     │
  │                      │          │  include "users:read".             │
  │                      │          │  throw new ForbiddenError()        │
  │                      │          └─────────────┬──────────────────────┘
  │                      │                        │
  │                      │          ┌─────────────▼──────────────────────┐
  │                      │          │  Global error handler               │
  │                      │          │  Map ForbiddenError → HTTP 403.    │
  │                      │          │  Return ApiResponse error envelope.│
  │                      │          └─────────────┬──────────────────────┘
  │                      │                        │
  │                      │  HTTP 403              │
  │                      │  { success: false,     │
  │                      │    error: {            │
  │                      │     code: "PERMISSION_DENIED",
  │                      │     message: "..." } } │
  │                      │◄───────────────────────│
  │                      │                        │
  │  HTTP 403            │                        │
  │◄─────────────────────│                        │
```

---

## 3. Refresh Token Flow

When the browser's access token expires, RTK Query's `baseQueryWithReAuth` wrapper intercepts the 401 and performs a silent token refresh before retrying the original request.

```
Browser (RTK Query)     NGINX               Node.js Backend           Redis
  │                      │                        │                      │
  │  GET /api/v1/users   │                        │                      │
  │  (expired token)     │                        │                      │
  │─────────────────────►│───────────────────────►│                      │
  │                      │                        │                      │
  │                      │          ┌─────────────▼──────────────────┐   │
  │                      │          │  authenticate                   │   │
  │                      │          │  JWT exp claim has passed.      │   │
  │                      │          │  throw UnauthorizedError        │   │
  │                      │          └─────────────┬───────────────────┘   │
  │                      │                        │                      │
  │  HTTP 401            │                        │                      │
  │◄────────────────────────────────────────────── │                      │
  │                      │                        │                      │
  │  [RTK Query          │                        │                      │
  │   baseQueryWithReAuth│                        │                      │
  │   intercepts 401]    │                        │                      │
  │                      │                        │                      │
  │  POST /auth/refresh  │                        │                      │
  │  { refreshToken }    │                        │                      │
  │─────────────────────►│───────────────────────►│                      │
  │                      │                        │                      │
  │                      │          ┌─────────────▼──────────────────┐   │
  │                      │          │  AuthService.refresh()          │   │
  │                      │          │  Look up refreshToken in Redis  │───►│
  │                      │          │                                │   │
  │                      │          │◄── userId (found) ─────────────│───│
  │                      │          │                                │   │
  │                      │          │  DEL old refreshToken in Redis │───►│
  │                      │          │  Issue new accessToken (RS256)  │   │
  │                      │          │  Generate new refreshToken      │   │
  │                      │          │  SET new refreshToken in Redis  │───►│
  │                      │          └─────────────┬───────────────────┘   │
  │                      │                        │                      │
  │  HTTP 200            │                        │                      │
  │  { accessToken,      │                        │                      │
  │    refreshToken }    │                        │                      │
  │◄─────────────────────│◄───────────────────────│                      │
  │                      │                        │                      │
  │  [RTK Query stores   │                        │                      │
  │   new credentials,   │                        │                      │
  │   retries original   │                        │                      │
  │   request]           │                        │                      │
  │                      │                        │                      │
  │  GET /api/v1/users   │                        │                      │
  │  (new token)         │                        │                      │
  │─────────────────────►│───────────────────────►│                      │
  │                      │                        │                      │
  │  HTTP 200 + data     │                        │                      │
  │◄─────────────────────│◄───────────────────────│                      │
```
