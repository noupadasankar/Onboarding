# ADR 0001 — Three-service split (frontend / backend / ai-service)

- **Status:** Accepted
- **Date:** 2026-07-09

## Context

OptiAgent combines a conventional enterprise CRUD/RBAC application with an AI workload
(LangGraph multi-agent orchestration, RAG, embeddings). These have very different runtimes
(Node vs Python), scaling profiles, dependency sets, and failure modes.

## Decision

Split the system into three independently deployable services plus a shared contracts
package and container/docs directories:

- `frontend/` — React 19 SPA.
- `backend/` — Node/Express gateway (auth, RBAC, CRUD, audit, WS gateway).
- `ai-service/` — Python/FastAPI (agents, RAG, embeddings only).
- `shared/` — TypeScript DTOs, RBAC enums, Zod schemas consumed by frontend + backend.

## Consequences

- **+** Each service scales and deploys on its own; Python's heavy ML deps never bloat the
  gateway; the AI service can be replaced or run on GPU nodes independently.
- **+** Clear ownership boundaries reduce accidental coupling (no LangChain in Node, no CRUD
  in Python).
- **−** More moving parts to orchestrate locally — mitigated by Docker Compose.
- **−** Cross-language contracts must be kept in sync — mitigated by explicit headers/DTOs.
