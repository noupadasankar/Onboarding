# tests

## Purpose
This directory contains the complete test suite for the OptiAgent backend, organized into two distinct layers: unit tests that exercise service logic in isolation, and integration tests that exercise the full HTTP stack end-to-end. The separation ensures that unit tests remain fast and deterministic (no network, no database), while integration tests verify that the DI container, middleware, routing, and database interactions all work together correctly.

All tests are written with Vitest. Type safety is maintained throughout: fake implementations satisfy the same TypeScript interfaces as their real counterparts, preventing tests from diverging from production contracts.

## Responsibilities
- Testing service-layer business logic in isolation using in-memory fakes (`tests/unit/`)
- Testing HTTP endpoints from request to response using supertest against the real DI container (`tests/integration/`)
- Providing shared test utilities, fake implementations, and a test harness builder (`tests/helpers/`)
- Ensuring that fake implementations satisfy the same interfaces as their production counterparts
- Covering happy paths, validation failures, authentication errors, authorization errors, and edge cases

## Does NOT Contain
- Application source code (belongs in `src/`)
- Prisma schema or migration files (belong in `prisma/`)
- End-to-end browser tests (outside scope of this backend test suite)
- Performance or load tests
- Mock library auto-mocking — fakes are hand-written implementations of real interfaces

## Architecture Position
```
[tests/unit/]
    ← no HTTP, no database
    ← services receive InMemoryUserRepository, FakeAuditLogService
    ← verify business logic, error paths, pagination, filtering

[tests/integration/]
    ← TestHarness builds a real Express app with real DI container
    ← supertest sends HTTP requests; responses are asserted
    ← database interaction uses a dedicated test PostgreSQL database
    ← Redis interaction uses a dedicated test Redis instance (or fakeredis)

[tests/helpers/]
    ← fakes.ts: InMemoryUserRepository, FakeAuditLogService, FakeTokenStore
    ← test-harness.ts: TestHarness builder (creates app, seeds data, teardown)
    ← fixtures.ts: reusable test data factories (createUser, createAuthTokens)
```

## Expected Contents
- `unit/auth/auth.service.test.ts` — Unit tests for `AuthService`: valid login, wrong password, unknown user, refresh rotation, logout invalidation.
- `unit/users/user.service.test.ts` — Unit tests for `UserService`: create, read, update, deactivate, list with pagination, search filter, role filter, isActive filter.
- `unit/roles/role-catalog.service.test.ts` — Unit tests for `RoleCatalogService`: verifies correct role and permission payloads are returned from shared constants.
- `integration/auth/auth.routes.test.ts` — Integration tests for all four auth endpoints: login success/failure, refresh rotation, logout, `/me` with valid and invalid tokens.
- `integration/users/users.routes.test.ts` — Integration tests for user CRUD endpoints: RBAC enforcement (403 for insufficient permissions), create/read/update/deactivate flows, pagination and filter query params.
- `integration/roles/roles.routes.test.ts` — Integration tests for `/roles` and `/permissions` endpoints: unauthenticated returns 401, authenticated returns correct catalog.
- `helpers/fakes.ts` — `InMemoryUserRepository` (implements `IUserRepository` with an in-memory Map), `FakeAuditLogService` (no-op with call recording), `FakeTokenStore` (in-memory Map with TTL simulation).
- `helpers/test-harness.ts` — `TestHarness` class that constructs the Express application with a configured DI container suitable for integration testing; provides `request` (supertest), `seed`, and `teardown` methods.
- `helpers/fixtures.ts` — Factory functions for generating consistent test data: user objects, JWT payloads, valid request bodies.

## Design Principles
- Separation of Concerns: unit tests cover logic; integration tests cover HTTP contract; helpers cover shared infrastructure for tests only.
- No Business Logic: test helpers set up data and assert outcomes; they do not implement application logic.
- Single Responsibility: each test file covers exactly one module or service.

## Current Status
Partially Implemented

## Future Work
Integration test coverage will be expanded in each subsequent increment as new modules are added. Increment 2 will add unit and integration tests for the domain query modules. A CI pipeline configuration running the full test suite on pull requests is planned for Increment 2.
