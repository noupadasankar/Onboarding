# Architecture Documentation

OptiAgent — Deloitte Capstone 2026

This folder contains detailed technical documentation for each architectural layer of the OptiAgent platform. Start with the system overview for a high-level picture, then drill into the service-specific documents for implementation detail.

---

## Documents

### [system-overview.md](./system-overview.md)

The starting point for understanding the platform. Covers:
- High-level ASCII architecture diagram showing all services and their relationships
- Rationale for the three-service split (React / Node.js / Python)
- End-to-end data flow from a browser request to an LLM response
- Technology choices at each layer
- Cross-cutting concerns: authentication, audit logging, correlation IDs
- Deployment topology overview

### [backend-architecture.md](./backend-architecture.md)

Deep-dive into the Node.js/Express API gateway. Covers:
- Request pipeline layering: route → middleware → validator → controller → service → repository → Prisma
- InversifyJS dependency injection: symbol tokens, container setup, module binding pattern
- Domain module structure following a domain / application / infrastructure layout
- Permission-based RBAC enforcement (not role-based)
- Audit logging as a non-fatal, injected cross-cutting concern
- JWT RS256 issuance and refresh token rotation via Redis

### [frontend-architecture.md](./frontend-architecture.md)

Deep-dive into the React 19 frontend. Covers:
- Feature-first folder structure
- RTK Query with a shared `baseApi` and tag-based cache invalidation
- Auth state in Redux: `accessToken`, `refreshToken`, `permissions[]`
- Permission-based UI gating via `useAuth().hasPermission()`
- URL-synced filter state pattern for list views
- `AppLayout` shell with a permission-aware sidebar

### [ai-service-architecture.md](./ai-service-architecture.md)

Deep-dive into the Python FastAPI AI service. Covers:
- FastAPI application folder structure: `api/`, `core/`, `agents/`, `rag/`, `loaders/`, `vectorstore/`
- Internal service token authentication (separate from user JWTs)
- Planned LangGraph supervisor/worker agent pattern
- Planned RAG pipeline (document loader → chunker → embedder → retriever → prompt builder)
- Planned ChromaDB vector store integration
- Alembic migration ownership for the AI service's own schema

### [deployment-architecture.md](./deployment-architecture.md)

Infrastructure and deployment documentation. Covers:
- Docker Compose service topology
- Service port assignments
- NGINX as reverse proxy routing `/api` to the backend and `/` to the frontend
- Environment variable strategy and `.env.example` files
- Production hardening considerations: TLS termination, secret management

---

## Architecture Decision Records

ADRs are stored in the [adr/](./adr/) subfolder. See the [ADR index](./adr/README.md) for a full list.
