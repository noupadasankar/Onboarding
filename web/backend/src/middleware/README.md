# middleware

## Purpose
This directory contains all reusable Express middleware for the OptiAgent backend. Every file here exports a standard Express `RequestHandler` (or a factory function that returns one). Middleware in this directory operates on the HTTP layer only — it reads from the request, optionally mutates `req`, and either calls `next()` to continue the chain or calls `next(error)` to hand off to the global error handler. No middleware here contains business logic or database access.

This separation ensures that cross-cutting HTTP concerns (identity, authorization, validation, observability, rate limiting) are implemented once and composed declaratively in route definitions, rather than duplicated inside controllers.

## Responsibilities
- Verifying JWT access tokens and attaching the decoded payload to `req.auth` (`authenticate.middleware.ts`)
- Enforcing RBAC permission requirements on protected routes (`authorize.middleware.ts`)
- Validating Zod schemas against request body, query parameters, and route parameters (`validate.middleware.ts`)
- Generating and attaching a UUID correlation ID to every request as `req.id` and as the `X-Request-Id` response header (`request-id.middleware.ts`)
- Logging structured HTTP request/response records via pino-http (`request-logger.middleware.ts`)
- Applying configurable rate limiting on sensitive endpoints such as login (`rate-limit.middleware.ts`)

## Does NOT Contain
- Business logic (belongs in `modules/*/application/`)
- Database queries (belongs in `modules/*/infrastructure/` or `infrastructure/`)
- Token issuance (belongs in `modules/auth/application/auth.service.ts`)
- Route handler implementations (belongs in `modules/*/controller.ts`)
- Global error handler (registered in `app.ts`, not stored here)

## Architecture Position
```
Incoming Request
      |
[request-id.middleware]       ← attaches UUID to req.id + response header
[request-logger.middleware]   ← logs method, path, status, duration via pino-http
      |
      ↓ (route match)
[rate-limit.middleware]       ← applied per-route (e.g., POST /auth/login)
[authenticate.middleware]     ← verifies Bearer JWT, populates req.auth
[authorize.middleware('perm')]← checks req.auth.permissions includes required perm
[validate.middleware(schema)] ← runs Zod parse on body/query/params
      |
[Controller method]
```

## Expected Contents
- `authenticate.middleware.ts` — Extracts the `Authorization: Bearer <token>` header, calls `JwtService.verify()`, and attaches the decoded payload to `req.auth`. Passes `UnauthorizedError` to `next` on failure.
- `authorize.middleware.ts` — Factory `authorize(permission: string)` that returns a `RequestHandler`. Checks that `req.auth.permissions` includes the required permission; passes `ForbiddenError` to `next` on failure.
- `validate.middleware.ts` — Factory `validate(schema: ZodSchema)` that runs `schema.safeParse()` against the appropriate part of the request (body, query, or params). Passes `ValidationError` with structured field errors to `next` on failure.
- `request-id.middleware.ts` — Generates a UUID v4, assigns it to `req.id`, and sets the `X-Request-Id` response header. Respects an incoming `X-Request-Id` header from trusted upstream proxies.
- `request-logger.middleware.ts` — Wraps `pino-http` and configures it to log the correlation ID, route, HTTP method, status code, and response time. Redacts sensitive headers.
- `rate-limit.middleware.ts` — Thin wrapper around `express-rate-limit`. Exports pre-configured instances for specific use cases (e.g., `loginRateLimiter` with a sliding window of 10 requests per 15 minutes per IP).

## Design Principles
- Single Responsibility: each file handles exactly one cross-cutting concern.
- Separation of Concerns: middleware is entirely HTTP-layer code; it delegates all decisions to injected services and never calls the database directly.
- No Business Logic: middleware enforces structural and security invariants (token presence, schema shape, permission membership) but applies no domain rules.
- No Database Access: `authenticate.middleware.ts` calls `JwtService.verify()` (stateless RS256 verification); it does not query the database to validate the token.
- Stateless: all middleware functions are stateless; any state (rate limit counters) is held in an injected store, not in the middleware closure.

## Current Status
Implemented

## Future Work
Increment 3 may add an `idempotency.middleware.ts` for write endpoints that require exactly-once semantics. No changes to existing middleware files are anticipated.
