# src

## Purpose

This directory is the sole source tree for `@optiagent/shared`, the cross-cutting contract
library consumed by both the Node.js backend and the React frontend. It defines the
canonical shapes of API payloads, authentication primitives, role and permission constants,
and error codes in one place so that neither the backend nor the frontend ever has to
duplicate or guess at these definitions.

Because `@optiagent/shared` is consumed by two runtimes with different environments (Node
and the browser), every file in this tree must compile to plain TypeScript with no
platform-specific imports. Zod is the only runtime dependency permitted.

## Responsibilities

- Define all Data Transfer Objects (DTOs) that cross the HTTP boundary between backend and
  frontend.
- Provide Zod schemas for every request body that requires validation, so both sides can
  derive types from the same ground truth.
- Export the canonical `Role` and `Permission` enums and the `ROLE_PERMISSIONS` map that
  drives RBAC on both the backend (enforcement) and the frontend (UI visibility).
- Export the `ApiResponse` discriminated union (`ApiSuccess<T> | ApiFailure`) and the
  `Paginated<T>` interface so API consumers never hard-code envelope shapes.
- Export the `ErrorCode` enum so error handling is consistent across the monorepo.

## Does NOT Contain

- Any import from `@optiagent/backend` or `@optiagent/frontend`.
- Any Node.js built-in (fs, path, http, crypto, etc.).
- Any browser-only API (window, document, localStorage, etc.).
- Database models, Prisma types, or ORM-specific code.
- Business logic, service classes, or stateful code.
- Environment variable reads or configuration loading.

## Architecture Position

```
@optiagent/frontend  ──┐
                       ├──► @optiagent/shared/src  (compile-time only)
@optiagent/backend   ──┘

shared/src is a pure TypeScript library.
It is never deployed on its own — it is bundled into the frontend
and compiled into the backend at build time.
```

## Expected Contents

```
src/
├── auth/
│   ├── dto.ts          — UserDTO, CreateUserRequest, UpdateUserRequest,
│   │                     RoleDTO, AuthResponse, AuthUser, LoginRequest
│   ├── schemas.ts      — loginSchema, registerSchema, createUserSchema,
│   │                     updateUserSchema, userListQuerySchema (Zod)
│   └── roles.ts        — Role enum, Permission enum, ALL_ROLES,
│                         ALL_PERMISSIONS, ROLE_PERMISSIONS map,
│                         permissionsForRole(), roleHasPermission()
├── common/
│   ├── api.ts          — ApiResponse (ApiSuccess<T> | ApiFailure),
│   │                     isApiFailure() type guard, Paginated<T>
│   └── schemas.ts      — paginationQuerySchema (Zod)
├── errors/
│   └── codes.ts        — ErrorCode enum (VALIDATION_ERROR, UNAUTHORIZED,
│                         FORBIDDEN, NOT_FOUND, CONFLICT, INTERNAL_ERROR)
└── index.ts            — barrel re-export for the entire package
```

## Design Principles

- **Single source of truth.** Any type that appears on both sides of the HTTP boundary
  lives here and nowhere else.
- **Zod-first.** Schemas are the source; TypeScript types are derived via `z.infer<>` so
  runtime validation and static types are always in sync.
- **Zero runtime dependencies beyond Zod.** Keeps the package safe to bundle in any
  environment.
- **No side effects at import time.** All exports are pure values or pure types; importing
  this package never triggers I/O, network calls, or global mutations.

## Current Status

Implemented

## Future Work

Add DTOs and Zod schemas for each new domain increment as it lands (documents, embeddings,
agent runs, audit events). Keep additions scoped to shapes that genuinely cross the
frontend-backend boundary.
