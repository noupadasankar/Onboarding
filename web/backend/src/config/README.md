# config

## Purpose
This directory is the single source of truth for all environment-driven configuration and compile-time constants in the OptiAgent backend. Environment variables are validated once at process startup using Zod; if any required variable is missing or malformed, the process exits immediately with a descriptive error rather than failing silently at runtime. Compile-time constants that are not environment-dependent (header names, token prefixes, timeout values) are defined here as typed exports so they are never spelled differently across the codebase.

Centralizing configuration here ensures that no other file ever calls `process.env` directly, making the configuration surface explicit, validated, and easy to audit.

## Responsibilities
- Parsing and validating all environment variables with Zod at startup (`env.ts`)
- Exporting a fully-typed, validated `env` object that the rest of the application imports
- Failing fast with a clear error message if the environment is incomplete or invalid
- Defining compile-time string and numeric constants that are used across multiple files (`constants.ts`)

## Does NOT Contain
- Business logic of any kind
- Database access or Redis connection setup (belongs in `infrastructure/`)
- DI container bindings (belongs in `core/di/`)
- Feature flags or runtime toggle logic
- Secrets themselves — only the schema that validates and types them

## Architecture Position
```
Process startup (main.ts)
        |
  [config/env.ts]          ← Zod validates process.env; exits on failure
        |
  exported `env` object
        |
  consumed by:
    infrastructure/database/  (DATABASE_URL)
    infrastructure/cache/      (REDIS_URL)
    infrastructure/security/   (JWT_PRIVATE_KEY, JWT_PUBLIC_KEY, BCRYPT_ROUNDS)
    middleware/rate-limit       (RATE_LIMIT_WINDOW_MS, RATE_LIMIT_MAX)
    app.ts                     (PORT, NODE_ENV, CORS_ORIGIN)

  [config/constants.ts]     ← compile-time literals, no env dependency
        |
  consumed by:
    middleware/authenticate  (BEARER_PREFIX)
    middleware/request-id    (REQUEST_ID_HEADER)
    infrastructure/security/ (TOKEN_TTL_SECONDS)
```

## Expected Contents
- `env.ts` — Defines a Zod schema covering all required and optional environment variables; calls `schema.parse(process.env)` on module load; exports the resulting typed `env` object. Required variables include: `DATABASE_URL`, `REDIS_URL`, `JWT_PRIVATE_KEY`, `JWT_PUBLIC_KEY`, `PORT`, `NODE_ENV`, `CORS_ORIGIN`, `BCRYPT_ROUNDS`, and token TTL settings.
- `constants.ts` — Named exports for values that are referenced in more than one file and must never diverge: `BEARER_PREFIX`, `REQUEST_ID_HEADER`, `REFRESH_TOKEN_COOKIE_NAME`, `DEFAULT_PAGE_SIZE`, `MAX_PAGE_SIZE`, and similar.

## Design Principles
- Single Responsibility: this directory exclusively handles configuration parsing and constant definition.
- No Business Logic: no conditions, transformations, or domain decisions are made here beyond type coercion (e.g., `z.coerce.number()` for numeric variables).
- Pure Functions: `env.ts` is effectively a pure parse-and-validate operation run once; `constants.ts` exports are immutable literals.
- Stateless: both files export static values; no state is held or mutated after startup.

## Current Status
Implemented

## Future Work
No additional work planned at this layer. New environment variables required by future increments (e.g., AI service URL, storage bucket name) will be added to the Zod schema in `env.ts`.
