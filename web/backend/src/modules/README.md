# modules

## Purpose
This directory contains all feature modules for the OptiAgent backend. Each module is a self-contained vertical slice that owns every layer of its own concern — from the domain model and repository interface, through the application service, down to the Prisma repository implementation, HTTP controller, route definitions, Zod validators, and DI container bindings.

This structure ensures that adding or modifying a feature requires touching only its own module folder, not scattered files across the project. Modules do not import from one another; any cross-cutting concerns (JWT, audit logging, Redis, RBAC) are injected through the DI container using shared interfaces.

## Responsibilities
- Encapsulating one cohesive business capability per subfolder (auth, users, roles)
- Defining the domain model (entity class and repository interface) inside each module's `domain/` subfolder
- Implementing application logic (services) inside each module's `application/` subfolder
- Implementing persistence (Prisma repository) inside each module's `infrastructure/` subfolder
- Exposing HTTP endpoints through a controller and an Express Router
- Validating incoming requests with Zod schemas before they reach the controller
- Binding all module-local classes to the DI container via a per-module `container.ts`

## Does NOT Contain
- Cross-module business logic (no module imports another module's service or repository)
- Global middleware (belongs in `src/middleware/`)
- External adapter singletons such as PrismaService or RedisService (belongs in `src/infrastructure/`)
- Environment configuration or constants (belongs in `src/config/`)
- Shared type augmentations (belongs in `src/types/`)

## Architecture Position
```
Request
  |
[src/routes/index.ts]         ← composes all module routers
  |
[modules/<name>/routes.ts]    ← module-specific Express Router
  |
[modules/<name>/controller.ts]← handles HTTP req/res, delegates to service
  |
[modules/<name>/application/] ← service: business rules, orchestration
  |
[modules/<name>/domain/]      ← entity + repository interface (no DB)
  |
[modules/<name>/infrastructure/] ← Prisma repository implementation
  |
[src/infrastructure/database/PrismaService]
```

## Expected Contents
- `auth/` — Authentication module: login, logout, token refresh, and current-user (`/me`) endpoints. See `auth/README.md`.
- `users/` — Users module: full CRUD with RBAC-gated routes, search/filter, and audit logging. See `users/README.md`.
- `roles/` — Roles module: static catalog endpoints for roles and permissions. No database interaction. See `roles/README.md`.
- Additional domain modules (e.g., `hr-queries/`, `finance-queries/`, `it-queries/`, `governance/`) are planned for Increment 2 and beyond.

## Design Principles
- Single Responsibility: each module owns exactly one business capability.
- Separation of Concerns: domain, application, and infrastructure sub-layers are kept distinct within every module.
- No Business Logic: controllers and routes contain no business logic; they delegate immediately to services.
- No Database Access: domain and application sub-layers never import Prisma directly; they depend on repository interfaces.

## Current Status
Partially Implemented

## Future Work
Increment 2 will add domain-specific query modules (hr-queries, finance-queries, it-queries) that proxy to the Python AI service. Increment 3 will add a governance module for audit trail queries and override logging.
