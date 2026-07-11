# api

## Purpose
This package contains all FastAPI router definitions and HTTP endpoint handlers for the AI Service. It is the outermost layer of the application: it receives validated HTTP requests, delegates work to the appropriate service or pipeline layer, and returns structured HTTP responses.

The `api/` package is versioned from the outset. All current endpoints live under `v1/`, giving the service a clear path for introducing breaking changes in future versions without disrupting existing consumers.

## Responsibilities
- Defining FastAPI `APIRouter` instances and registering them on the application
- Declaring route paths, HTTP methods, request models, and response models
- Performing request-level validation via Pydantic schemas
- Delegating business logic to the `core/`, `rag/`, or `agents/` layers
- Returning well-formed HTTP responses with appropriate status codes

## Does NOT Contain
- Business logic or data transformation beyond what is needed to shape a response
- Direct database access
- Authentication implementation (that lives in `core/security.py`; authentication is applied as a dependency)
- Service-level orchestration logic (that belongs in `rag/` or `agents/`)

## Architecture Position

```
Node.js Backend / External Client
             │
             │  HTTP (internal token in header)
             ▼
       app/api/v1/
             │
      ┌──────┴──────┐
      │             │
 health.py     (future routers)
      │             │
  Returns 200   delegates to
   + metadata    rag/ / agents/
```

## Expected Contents

| File / Folder | Description | Status |
|---|---|---|
| `__init__.py` | Marks `api` as a Python package | Implemented |
| `v1/__init__.py` | Marks `v1` as a sub-package | Implemented |
| `v1/router.py` | Top-level v1 `APIRouter`; aggregates all v1 sub-routers | Implemented |
| `v1/health.py` | `GET /api/v1/health` — returns service status and version | Implemented |
| `v1/documents.py` | Document upload and ingestion endpoints | Planned for Increment 3 |
| `v1/query.py` | AI query endpoint; accepts user questions, returns RAG-grounded answers | Planned for Increment 7 |

## Design Principles
- **No Business Logic** — Routers coordinate between HTTP and service layers; they do not make domain decisions.
- **No Database Access** — The API layer never queries the database directly; it calls service functions that abstract persistence.
- **Separation of Concerns** — Each router file handles exactly one resource domain (health, documents, queries).

## Current Status
Partially Implemented — the `v1/` sub-package and health endpoint are complete. Document and query endpoints are reserved for future increments.

## Future Work
- Increment 3: `v1/documents.py` — upload and ingestion endpoints for PDF, CSV, DOCX, and TXT files
- Increment 7: `v1/query.py` — RAG-backed question-answering endpoint consumed by the Node.js backend
