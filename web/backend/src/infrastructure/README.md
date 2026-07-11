# infrastructure

## Purpose
This directory contains singleton adapters for every external system the backend depends on: the PostgreSQL database (via Prisma), the Redis cache, JWT signing and verification, password hashing, refresh token storage, and the audit log writer. Each adapter wraps a third-party library or protocol behind a stable TypeScript interface, so the rest of the application depends on abstractions rather than concrete library APIs.

All adapters are registered as singletons in the DI container. This means a single Prisma connection pool, a single Redis connection, and a single JWT key pair are shared across the entire request lifecycle — no per-request re-initialization.

## Responsibilities
- Providing a `PrismaService` singleton that initializes the Prisma client and manages connection lifecycle (`database/`)
- Providing a `RedisService` singleton that wraps the Redis client and exposes typed get/set/del/expire operations (`cache/`)
- Providing a `JwtService` that signs and verifies JWTs using RS256 asymmetric keys read from environment variables (`security/`)
- Providing a `PasswordService` that hashes passwords with bcrypt and verifies plaintext against a hash (`security/`)
- Providing a `TokenStore` that persists, retrieves, and invalidates refresh tokens in Redis with a configurable TTL (`security/`)
- Providing an `AuditLogService` that writes structured audit records to the Prisma `auditLog` table in a non-fatal, fire-and-forget manner (`audit/`)

## Does NOT Contain
- Business logic (no domain rules are applied here — adapters do only what is requested of them)
- HTTP logic (no Express types, no `Request` or `Response` imports)
- Module-specific code (auth or user domain concerns belong in `modules/`)
- Feature flags, routing, or application-level orchestration
- Migrations or schema definitions (belong in `prisma/`)

## Architecture Position
```
[modules/*/application/]
  uses interfaces: IUserRepository, AuditLogService, TokenStore
         |
         ↓ (resolved by DI container at runtime)
[infrastructure/database/PrismaService]    ← PostgreSQL via Prisma Client
[infrastructure/cache/RedisService]        ← Redis via ioredis
[infrastructure/security/JwtService]       ← RS256 sign/verify
[infrastructure/security/PasswordService]  ← bcrypt hash/compare
[infrastructure/security/TokenStore]       ← refresh token CRUD in Redis
[infrastructure/audit/AuditLogService]     ← fire-and-forget audit writes
         |
         ↓ (external systems)
      PostgreSQL          Redis
```

## Expected Contents
- `database/prisma.service.ts` — Initializes `PrismaClient` with logging configuration; exposes `connect()` and `disconnect()` methods called in `main.ts`; re-exports the client as `db` for use in repository implementations.
- `cache/redis.service.ts` — Wraps `ioredis`; exposes typed `get<T>`, `set`, `del`, `expire`, and `keys` methods; handles connection errors and reconnect logic.
- `security/jwt.service.ts` — Reads RS256 private and public keys from environment variables; exposes `sign(payload, expiresIn)` and `verify(token)` methods; throws `UnauthorizedError` on invalid or expired tokens.
- `security/password.service.ts` — Wraps `bcrypt`; exposes `hash(plaintext)` and `compare(plaintext, hash)` methods; salt rounds are read from config.
- `security/token-store.ts` — Wraps `RedisService`; stores refresh tokens keyed by `refreshToken:<token>`; exposes `save`, `get`, `delete`, and `deleteAllForUser` methods with configurable TTL.
- `audit/audit-log.service.ts` — Writes to the Prisma `auditLog` table; all writes are non-fatal — errors are logged but never propagated to the caller; called by `UserService` and `AuthService`.

## Design Principles
- Single Responsibility: each subfolder handles exactly one external integration.
- Separation of Concerns: infrastructure adapters implement well-defined interfaces; callers never import third-party library types directly.
- No Business Logic: adapters perform I/O operations only; they apply no domain rules and make no authorization decisions.
- No HTTP Logic: no Express types appear anywhere in this directory.
- Stateless: adapter methods are stateless functions over injected clients; all connection state is held in the underlying client library.

## Current Status
Implemented

## Future Work
Increment 2 will add an `http/ai-client.service.ts` adapter for proxying requests to the Python AI service over HTTP. Increment 3 may add a `storage/` adapter for document attachments if file persistence is required.
