# modules/auth

## Purpose
This module owns all authentication concerns for the OptiAgent backend. It provides the four core auth endpoints — login, logout, token refresh, and current-user — and manages the full lifecycle of JWT access tokens and refresh tokens. No other module issues or validates tokens; all token logic is centralized here and in the `infrastructure/security/` adapters that this module depends on.

Access tokens are short-lived JWTs signed with RS256 (asymmetric key pair). Refresh tokens are opaque random strings stored in Redis with a TTL. On each successful refresh, the old refresh token is invalidated and a new one is issued (rotation), preventing replay attacks. Login endpoints are rate-limited to mitigate brute-force attempts.

## Responsibilities
- Accepting credentials (email + password) and returning a signed access token and a refresh token
- Verifying refresh tokens against Redis and issuing rotated token pairs
- Invalidating the refresh token in Redis on logout
- Returning the authenticated user's profile on `GET /auth/me` (requires a valid access token)
- Enforcing per-IP and per-user rate limits on the login endpoint
- Hashing and verifying passwords via the injected `PasswordService`
- Delegating all JWT signing/verification to the injected `JwtService`
- Delegating all token storage/invalidation to the injected `TokenStore`

## Does NOT Contain
- User management CRUD (belongs in `modules/users/`)
- Role or permission definitions (belongs in `modules/roles/` and `@optiagent/shared`)
- Raw Prisma calls — the module uses `IUserRepository` injected from `modules/users/infrastructure/`
- Any Redis calls directly — token persistence is handled by `infrastructure/security/TokenStore`

## Architecture Position
```
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
GET  /api/v1/auth/me
         |
[rate-limit.middleware]     ← applied to /login
[validate.middleware]       ← Zod schemas for login/refresh bodies
         |
[AuthController]            ← HTTP layer, delegates to service
         |
[AuthService]               ← application/auth.service.ts
      /    \      \
[JwtService] [PasswordService] [TokenStore]   ← infrastructure/security/
         |
[IUserRepository]           ← resolved to UserPrismaRepository at runtime
```

## Expected Contents
- `routes.ts` — Express Router; mounts controller methods on their paths; applies rate-limit and validate middleware.
- `auth.controller.ts` — Handles HTTP request/response for all four endpoints; calls `AuthService`; sets/clears the refresh token cookie.
- `auth.validators.ts` — Zod schemas for the login request body (`email`, `password`) and the refresh request body (`refreshToken`).
- `auth.container.ts` — Binds `AuthService` and `AuthController` to their DI Symbol tokens.
- `application/auth.service.ts` — Business logic: credential validation, token issuance, rotation, logout, and `me` resolution.

## Design Principles
- Single Responsibility: this module exclusively handles authentication; authorization (permission checks) is handled by `middleware/authorize.middleware.ts`.
- No Business Logic: the controller contains no business logic; it calls `AuthService` and maps the result to an HTTP response.
- No Database Access: `AuthService` depends on `IUserRepository`, never on `PrismaService` directly.
- Stateless: access tokens are self-contained JWTs; the only server-side state is the refresh token entry in Redis.

## Current Status
Implemented

## Future Work
Increment 2 may add MFA (TOTP) support as an extension to the login flow. No structural changes to this module are anticipated.
