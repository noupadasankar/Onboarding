# modules/roles

## Purpose
This module exposes the OptiAgent RBAC catalog — the four roles and seven permissions that govern access across the platform — as HTTP endpoints. Because the role and permission definitions are static constants defined in the `@optiagent/shared` package, this module performs no database queries and maintains no persistent state. Its sole purpose is to make the catalog discoverable by the React frontend and any other consumers without requiring them to import the shared package directly.

Serving this data through an API endpoint ensures the frontend always reflects the authoritative source of truth, and allows the role catalog to be consumed by teams who do not have access to the monorepo source.

## Responsibilities
- Serving a `GET /api/v1/roles` response listing all four roles with their display names and assigned permissions
- Serving a `GET /api/v1/permissions` response listing all seven permissions with their descriptions
- Reading role and permission data exclusively from `@optiagent/shared` constants — never from the database
- Requiring a valid access token (authenticate middleware) to prevent unauthenticated enumeration of the RBAC model

## Does NOT Contain
- Database access of any kind (no Prisma calls, no repository interface or implementation)
- Role assignment or mutation logic (assigning a role to a user belongs in `modules/users/`)
- Permission enforcement logic (belongs in `middleware/authorize.middleware.ts`)
- A `domain/` subfolder — the domain model lives in `@optiagent/shared`
- An `infrastructure/` subfolder — there is no persistence layer for static constants

## Architecture Position
```
GET /api/v1/roles
GET /api/v1/permissions
         |
[authenticate.middleware]     ← requires valid JWT
         |
[RolesController]             ← reads from RoleCatalogService, returns JSON
         |
[RoleCatalogService]          ← application/role-catalog.service.ts
         |
[@optiagent/shared constants] ← ROLES, PERMISSIONS definitions
         (no database)
```

## Expected Contents
- `application/role-catalog.service.ts` — Thin service that reads from `@optiagent/shared` constants and formats the response payload; no I/O.
- `roles.controller.ts` — Handles HTTP request/response for both endpoints; delegates to `RoleCatalogService`.
- `routes.ts` — Express Router; applies `authenticate` middleware; binds controller methods to paths.
- `roles.container.ts` — Binds `RoleCatalogService` and `RolesController` to their DI Symbol tokens.

## Design Principles
- Single Responsibility: this module exclusively serves the static RBAC catalog.
- No Database Access: constants are imported from the shared package; no repository or Prisma dependency exists.
- No Business Logic: the service performs data formatting only; it enforces no rules and makes no decisions.
- Pure Functions: `RoleCatalogService` methods are effectively pure — given the same shared constants, they always return the same output with no side effects.
- Stateless: no state is held between requests; every call reads directly from the imported constants.

## Current Status
Implemented

## Future Work
No additional work planned at this layer. If roles become dynamic and database-driven in a future increment, a `domain/` and `infrastructure/` subfolder would be introduced at that time.
