# src

## Purpose
This is the root source directory for the OptiAgent backend service. All application code lives here, organized into focused subfolders by architectural concern. The entry point is `main.ts`, which bootstraps the application and starts the HTTP server. Application setup — middleware registration, route mounting, and error handling — is handled in `app.ts`. Nothing outside this directory is compiled or executed as application code.

This directory establishes the top-level shape of the backend: configuration is read once at startup, the DI container is assembled, Express is configured, and the server begins accepting connections on port 8000.

## Responsibilities
- Providing `main.ts` as the single process entry point (server listen, graceful shutdown)
- Providing `app.ts` as the Express application factory (middleware stack, route mounting, global error handler)
- Grouping all backend source code under a single compilable root
- Organizing subfolders so each architectural concern is isolated from the others

## Does NOT Contain
- Business logic of any kind (belongs in `modules/*/application/`)
- Database access code (belongs in `infrastructure/database/` or `modules/*/infrastructure/`)
- Raw SQL or Prisma calls (belongs in repository implementations)
- Frontend assets or React code
- Shared package source (lives in the monorepo `packages/shared` directory)

## Architecture Position
```
[main.ts]  ← process entry, starts server
     |
[app.ts]   ← Express factory, middleware + route registration
     |
+----+--------------------------------------------+
|         |          |           |                 |
[config/] [core/]  [middleware/] [modules/]  [routes/]
           DI        auth/authz   features    /api/v1
           errors    validate     auth
           logging   rate-limit   users
           result                 roles
```

## Expected Contents
- `main.ts` — process entry point; creates the Express app, binds the DI container, and starts listening on the configured port. Registers SIGTERM/SIGINT handlers for graceful shutdown.
- `app.ts` — Express application factory; registers global middleware (request ID, logger, body parser), mounts the root router, and attaches the global error handler.
- `config/` — Zod-validated environment variables and compile-time constants. See `config/README.md`.
- `core/` — Framework-level building blocks: DI container, error classes, HTTP helpers, logger factory, Result type. See `core/README.md`.
- `infrastructure/` — Singleton adapters for external systems: Prisma, Redis, JWT, bcrypt, audit log. See `infrastructure/README.md`.
- `middleware/` — Reusable Express middleware: authentication, authorization, validation, request ID, logging, rate limiting. See `middleware/README.md`.
- `modules/` — Feature modules (auth, users, roles), each self-contained. See `modules/README.md`.
- `routes/` — Root Express router that composes all module routers under `/api/v1`. See `routes/README.md`.
- `types/` — Ambient TypeScript type augmentations (e.g., `express/index.d.ts` extending `Request` with `auth` and `id` fields).
- `docs/` — OpenAPI/Swagger specification files (planned for Increment 3).

## Design Principles
- Separation of Concerns: each subfolder has a single architectural role; `app.ts` wires them together but does not implement any of them.
- Single Responsibility: `main.ts` owns only process lifecycle; `app.ts` owns only Express configuration.

## Current Status
Implemented

## Future Work
Increment 3 will add the `docs/` OpenAPI specification and auto-generated Swagger UI. No structural changes to this directory are anticipated.
