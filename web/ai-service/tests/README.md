# tests

## Purpose
This directory contains the automated test suite for the AI Service. Tests are written with pytest and use `httpx`'s `AsyncClient` to exercise the FastAPI application without starting a live server process. The suite is structured to mirror the `app/` package layout, making it straightforward to locate the tests for any given module.

All tests run in CI on every pull request. The test suite is the primary safety net for the service: it must remain green before any change is merged.

## Responsibilities
- Providing end-to-end HTTP-level tests for every API endpoint
- Providing unit tests for core utilities (config, logging, security)
- Providing integration tests for service-layer modules (loaders, RAG pipeline, agents) as they are implemented
- Supplying shared fixtures via `conftest.py` (application instance, authenticated client, test database, etc.)
- Asserting correct behaviour for both success paths and error paths (4xx, 5xx responses)

## Does NOT Contain
- Application source code
- Migration scripts
- Test data files larger than a few kilobytes (larger fixtures should be stored in a dedicated `tests/fixtures/` directory)
- Tests that make real network calls to external services without mocking

## Architecture Position

```
pytest
  │
  ├── conftest.py          ◄── shared fixtures (app, async client, auth token)
  │
  ├── test_health.py       ◄── tests for GET /api/v1/health
  │
  ├── api/                 ◄── mirrors app/api/  (future endpoint tests)
  ├── core/                ◄── mirrors app/core/ (unit tests for config, security)
  ├── loaders/             ◄── mirrors app/loaders/ (Increment 3)
  ├── rag/                 ◄── mirrors app/rag/    (Increment 7)
  └── agents/              ◄── mirrors app/agents/ (Increment 9)
```

## Expected Contents

| File / Folder | Description | Status |
|---|---|---|
| `conftest.py` | pytest fixtures: FastAPI `TestClient` / `AsyncClient`, `internal_token` header injection, any shared test state | Implemented |
| `test_health.py` | Tests for `GET /api/v1/health`: asserts 200 response, correct JSON shape, and 401 when token is absent or invalid | Implemented |
| `api/` | Sub-directory for HTTP-level tests mirroring `app/api/`; populated as new endpoints are added | Planned for Increment 3+ |
| `core/` | Unit tests for `config.py`, `logging.py`, and `security.py` | Planned |
| `loaders/` | Unit tests for each document loader, using small sample files | Planned for Increment 3 |
| `rag/` | Unit and integration tests for the RAG pipeline stages | Planned for Increment 7 |
| `agents/` | Integration tests for LangGraph supervisor and domain agent routing | Planned for Increment 9 |

## Running the Tests

```bash
# From the ai-service root
pytest tests/

# With verbose output
pytest tests/ -v

# Run a specific test file
pytest tests/test_health.py
```

The internal service token is injected automatically by the `conftest.py` fixture and does not need to be set manually when running tests locally, provided the `.env` file is present.

## Design Principles
- **Separation of Concerns** — Tests mirror the `app/` structure; each test file covers one corresponding module.
- **Stateless** — Tests do not share mutable state across test functions; each test is fully independent.

## Current Status
Partially Implemented — `conftest.py` and `test_health.py` are complete. Sub-directories for loaders, RAG, and agents will be added as those packages are implemented.

## Future Work
- Increment 3: `tests/loaders/` — unit tests for PDF, CSV, DOCX, and TXT loaders
- Increment 7: `tests/rag/` — pipeline integration tests with a mocked vector store
- Increment 9: `tests/agents/` — supervisor routing tests and domain agent response tests
