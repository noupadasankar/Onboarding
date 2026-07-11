# routes

## Purpose
This directory contains the root Express router that composes all module-level routers into the application's public API. It is the single place where every route in the backend is registered under a common prefix, and the only place where module routes are assembled together. Nothing else in the application needs to know which modules exist or what paths they expose — `app.ts` mounts this router once, and this file does the rest.

Keeping all route composition here, rather than in `app.ts` or scattered across module files, makes it straightforward to see the full API surface in one place and to apply versioning consistently.

## Responsibilities
- Creating a top-level Express `Router` and exporting it for use in `app.ts`
- Mounting each module's router under its canonical sub-path beneath `/api/v1`
- Providing a `GET /api/v1/health` endpoint for infrastructure health checks (returns 200 with `{ status: "ok" }`)
- Enforcing the `/api/v1` version prefix across all module routes uniformly

## Does NOT Contain
- Route handler implementations (each handler lives in the corresponding `modules/*/controller.ts`)
- Middleware logic (middleware is applied in module-level route files or in `app.ts`)
- Business logic of any kind
- Direct Prisma or Redis access
- Module-specific validators or schemas

## Architecture Position
```
[app.ts]
    |
    app.use('/api/v1', rootRouter)   ← this directory
                |
     +----------+----------+---------+
     |          |          |         |
/auth        /users     /roles   /health
[modules/    [modules/  [modules/  (inline
 auth/        users/     roles/    handler)
 routes.ts]   routes.ts] routes.ts]
```

## Expected Contents
- `index.ts` — Creates and exports the root `Router`; imports each module's router and mounts it; defines the health check endpoint.

Additional sub-routers for future modules (e.g., `/hr-queries`, `/finance-queries`, `/it-queries`, `/governance`) will be mounted here as they are implemented in Increment 2 and Increment 3.

## Design Principles
- Single Responsibility: this directory exclusively handles route composition; it does not implement any handler behavior.
- Separation of Concerns: route composition is distinct from route handling; each module owns its own handler logic.
- No Business Logic: the health check response is the only logic permitted here, and it contains no domain rules.
- No HTTP Logic: beyond mounting routers and the health check response, no `req`/`res` manipulation occurs in this file.

## Current Status
Implemented

## Future Work
Increment 2 will add mounts for the domain query module routers (`/hr-queries`, `/finance-queries`, `/it-queries`). Increment 3 will add the `/governance` mount. No structural changes to `index.ts` are anticipated beyond adding new `router.use()` calls.
