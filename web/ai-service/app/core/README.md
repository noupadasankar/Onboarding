# core

## Purpose
This package provides the cross-cutting concerns that the entire AI Service depends on: application configuration, structured logging, and internal authentication. These utilities are intentionally kept separate from business logic so that every other layer of the application can import them without creating circular dependencies or pulling in domain knowledge.

`core/` is the only package that is allowed to be imported by every other package in `app/`. All other packages should be treated as unidirectional dependencies flowing from `api/` down through `rag/` and `agents/`.

## Responsibilities
- Loading and validating environment variables and application settings (`config.py`)
- Providing a pre-configured structured JSON logger (`logging.py`)
- Validating internal service-to-service authentication tokens (`security.py`)
- Exposing reusable FastAPI dependencies (e.g., `require_internal_token`) for use in router definitions

## Does NOT Contain
- Business logic of any kind
- Database models or query logic
- HTTP route definitions
- Domain-specific data transformation
- Any import from `api/`, `rag/`, `agents/`, `loaders/`, or `vectorstore/`

## Architecture Position

```
                  ┌────────────────────────────────┐
                  │           app/core/             │
                  │                                 │
                  │  config.py   ◄── .env / env vars│
                  │  logging.py  ◄── stdlib logging  │
                  │  security.py ◄── token header    │
                  └────────────┬───────────────────┘
                               │  imported by
              ┌────────────────┼──────────────┐
              ▼                ▼              ▼
           api/             rag/          agents/
```

## Expected Contents

| File | Description | Status |
|---|---|---|
| `__init__.py` | Marks `core` as a Python package | Implemented |
| `config.py` | Pydantic `BaseSettings` class; reads `SERVICE_TOKEN`, `LOG_LEVEL`, `ENVIRONMENT`, and other service-wide settings from environment variables | Implemented |
| `logging.py` | Configures the Python `logging` module to emit structured JSON, compatible with pino-style log aggregation in the wider platform | Implemented |
| `security.py` | FastAPI dependency that validates the `X-Internal-Token` header against the configured `SERVICE_TOKEN`; raises `HTTP 401` on mismatch | Implemented |

## Design Principles
- **No Business Logic** — `core/` is infrastructure only; it knows nothing about documents, RAG, or agents.
- **No Database Access** — Configuration and logging utilities must not depend on database state.
- **No HTTP Logic** — `security.py` exposes a FastAPI dependency function, but the HTTP mechanics (routing, response formatting) are owned by `api/`.
- **Single Responsibility** — Each module owns exactly one concern: settings, logging, or authentication.
- **Stateless** — All functions and dependencies in `core/` are stateless; they read from environment or from the incoming request, and they do not mutate application state.

## Current Status
Implemented — all three modules (`config.py`, `logging.py`, `security.py`) are complete and active in the running service.

## Future Work
No additional modules are planned for `core/`. As new capabilities are added in later increments, they will consume the existing `core/` utilities rather than extending this package.
