# modules/users

## Purpose
This module owns all user-management concerns for the OptiAgent platform. It provides a full CRUD API for user records, gated by RBAC so that only callers with the appropriate permissions can read or mutate user data. The module follows the full layered architecture: a domain layer defining the entity and repository interface, an application layer containing the service, and an infrastructure layer providing the Prisma-backed repository implementation.

Users are never hard-deleted. A `deactivate` operation sets `isActive = false`, preserving the record for audit purposes. Every mutating operation (create, update, deactivate) is written to the audit log via the injected `AuditLogService`. The `isActive` flag and role assignments are validated by the service layer before being persisted.

## Responsibilities
- Creating new user records with hashed passwords
- Retrieving a single user by ID
- Listing users with server-side pagination and optional filters: free-text search (case-insensitive ILIKE on name/email), role, and `isActive` status
- Updating user profile fields (name, email, role)
- Soft-deactivating users (setting `isActive = false`)
- Enforcing RBAC: routes require `users:read` or `users:write` permission as appropriate
- Writing an audit log entry on every create, update, and deactivate action

## Does NOT Contain
- Authentication logic (belongs in `modules/auth/`)
- Token issuance or password verification for login (belongs in `modules/auth/`)
- Role or permission catalog data (belongs in `modules/roles/` and `@optiagent/shared`)
- Direct Redis access (token concerns are handled in `infrastructure/security/`)

## Architecture Position
```
GET    /api/v1/users
POST   /api/v1/users
GET    /api/v1/users/:id
PATCH  /api/v1/users/:id
DELETE /api/v1/users/:id
           |
[authenticate.middleware]     ← verifies JWT, attaches req.auth
[authorize.middleware]        ← checks users:read / users:write
[validate.middleware]         ← Zod schemas for body and query params
           |
[UsersController]             ← HTTP layer, maps results to responses
           |
[UserService]                 ← application/user.service.ts
      /          \
[IUserRepository]  [AuditLogService]
      |
[UserPrismaRepository]        ← infrastructure/user.prisma.repository.ts
      |
[PrismaService]               ← src/infrastructure/database/
```

## Expected Contents
- `domain/user.entity.ts` — Pure TypeScript class representing a user record; no Prisma types exposed.
- `domain/i-user.repository.ts` — Repository interface (`IUserRepository`) defining the contract for all persistence operations; used by `UserService` and `AuthService`.
- `application/user.service.ts` — Business logic: pagination, filtering, password hashing on create, RBAC-aware deactivation, audit log calls.
- `infrastructure/user.prisma.repository.ts` — Implements `IUserRepository` using `PrismaService`; translates Prisma models to `UserEntity`.
- `users.controller.ts` — Handles HTTP request/response; extracts query params and body; delegates to `UserService`.
- `users.validators.ts` — Zod schemas for create body, update body, and list query params (page, limit, search, role, isActive).
- `routes.ts` — Express Router; applies middleware chain and binds controller methods.
- `users.container.ts` — Binds `IUserRepository`, `UserService`, and `UsersController` to their DI Symbol tokens.

## Design Principles
- Single Responsibility: this module exclusively handles user data management.
- Separation of Concerns: domain, application, and infrastructure sub-layers are strictly separated; the service never imports Prisma.
- No Database Access: `UserService` depends only on `IUserRepository`; Prisma is touched exclusively in `UserPrismaRepository`.
- No HTTP Logic: `UserService` returns domain entities or `Result` types; it has no knowledge of HTTP status codes or `Response` objects.

## Current Status
Implemented

## Future Work
Increment 2 may add bulk-import functionality for onboarding users via CSV. Increment 3 may extend the list endpoint with additional audit-trail filters. No structural changes to this module are anticipated.
