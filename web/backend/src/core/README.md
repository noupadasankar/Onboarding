# core

## Purpose
This directory provides the framework-level building blocks that all other parts of the backend depend on. It contains no business logic, no database access, and no HTTP handlers — only the foundational abstractions that make the rest of the application consistent and testable. Code here is stable; it changes only when a cross-cutting architectural decision changes, not when a feature is added.

Every module and infrastructure adapter in this codebase relies on at least one export from `core/`: the DI container for wiring dependencies, the error classes for typed failure handling, the logger factory for structured output, or the `Result` type for explicit error propagation without exceptions.

## Responsibilities
- Assembling and exporting the InversifyJS DI container (`core/di/`)
- Defining Symbol tokens for every bound interface (`core/di/types.ts`)
- Providing typed application error classes with HTTP status semantics (`core/errors/`)
- Providing HTTP response helpers that serialize `Result` values into Express `Response` objects (`core/http/`)
- Providing a pino logger factory that attaches a correlation ID and service name to every log entry (`core/logging/`)
- Providing the `Result<T, E>` type for explicit, type-safe error propagation across service and repository boundaries (`core/result/`)

## Does NOT Contain
- Business logic of any kind
- Prisma imports or database queries
- Redis imports or cache logic
- Express route handlers or middleware
- JWT or password utilities (those belong in `infrastructure/security/`)
- Module-specific code (auth, users, roles concerns belong in `modules/`)

## Architecture Position
```
Everything depends on core/ — it sits at the base of the dependency graph.

[modules/*/application/]  →  core/result/, core/errors/
[modules/*/routes.ts]     →  (indirectly via middleware)
[middleware/*]            →  core/errors/, core/http/, core/logging/
[infrastructure/*]        →  core/di/, core/logging/, core/result/
[app.ts]                  →  core/di/container, core/logging/
```

## Expected Contents
- `di/types.ts` — Symbol token registry (`TYPES`) for every interface bound in the container (e.g., `TYPES.IUserRepository`, `TYPES.JwtService`).
- `di/container.ts` — InversifyJS `Container` instance; imports all module-level `container.ts` files and infrastructure bindings; exported as a singleton.
- `errors/app-error.ts` — Base `AppError` class extending `Error`; carries `statusCode` and optional `code` string.
- `errors/http-errors.ts` — Concrete error subclasses: `NotFoundError` (404), `UnauthorizedError` (401), `ForbiddenError` (403), `ConflictError` (409), `ValidationError` (422), `InternalServerError` (500).
- `http/response.helpers.ts` — Utility functions (`ok`, `created`, `noContent`, `fail`) that write a consistent JSON envelope (`{ success, data, error }`) to an Express `Response`.
- `logging/logger.factory.ts` — Returns a pino logger instance pre-configured with level, transport, and base fields (service name, environment). Consumed by `infrastructure/` adapters and `app.ts`.
- `result/result.ts` — Generic `Result<T, E>` discriminated union (`Ok<T>` | `Err<E>`) with helper constructors `ok()` and `err()`. Used as the return type of all service and repository methods.

## Design Principles
- Single Responsibility: each subfolder addresses exactly one framework concern.
- Separation of Concerns: no subfolder in `core/` imports from another subfolder in `core/`, except `di/container.ts` which imports `di/types.ts`.
- No Business Logic: all code here is structural or infrastructural — it provides primitives, never makes domain decisions.
- No Database Access: `core/` has no Prisma or Redis dependency.
- No HTTP Logic: `core/http/` contains response serialization helpers only; it does not define routes or middleware.
- Pure Functions: `Result` helpers and HTTP response helpers are pure functions with no side effects.

## Current Status
Implemented

## Future Work
No additional work planned at this layer. New modules and infrastructure adapters will register their Symbol tokens in `di/types.ts` and their bindings in `di/container.ts` as they are added in subsequent increments.
