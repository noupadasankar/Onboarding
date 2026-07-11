# OptiAgent Documentation

Enterprise AI Platform — Deloitte Capstone 2026

This folder contains all technical documentation for the OptiAgent platform. It is organized into four sections covering architecture, API references, visual diagrams, and a top-level decision log.

---

## Contents

### [architecture/](./architecture/)

Detailed technical documentation for each layer of the system.

| Document | Description |
|---|---|
| [system-overview.md](./architecture/system-overview.md) | High-level architecture, three-service split rationale, end-to-end data flow, cross-cutting concerns |
| [backend-architecture.md](./architecture/backend-architecture.md) | Node.js/Express layering, InversifyJS DI, RBAC enforcement, audit logging, JWT RS256 |
| [frontend-architecture.md](./architecture/frontend-architecture.md) | React feature structure, RTK Query, Redux auth state, permission-gated UI, URL-synced filters |
| [ai-service-architecture.md](./architecture/ai-service-architecture.md) | FastAPI structure, LangGraph supervisor pattern, RAG pipeline, ChromaDB vector store |
| [deployment-architecture.md](./architecture/deployment-architecture.md) | Docker Compose topology, service ports, NGINX reverse proxy, environment variables |

### [architecture/adr/](./architecture/adr/)

Architecture Decision Records (ADRs) documenting significant design choices and their rationale.

| Document | Description |
|---|---|
| [ADR-0001](./architecture/adr/0001-three-service-split.md) | Decision to split the system into React frontend, Node.js backend, and Python AI service |
| [ADR-0002](./architecture/adr/0002-node-gateway-python-ai.md) | Decision to use Node.js as the API gateway rather than exposing the Python AI service directly |

### [api/](./api/)

REST API reference documentation for each resource domain.

| Document | Description |
|---|---|
| [authentication.md](./api/authentication.md) | Auth endpoints: login, logout, token refresh, current user |
| [users.md](./api/users.md) | User and role management endpoints with permission requirements |
| [documents.md](./api/documents.md) | Document upload API — planned for Increment 3 |
| [ai.md](./api/ai.md) | AI query API — planned for Increment 7 |

### [diagrams/](./diagrams/)

ASCII sequence and flow diagrams for key system behaviors.

| Document | Description |
|---|---|
| [request-flow.md](./diagrams/request-flow.md) | Full authenticated request lifecycle through the middleware chain |
| [authentication-sequence.md](./diagrams/authentication-sequence.md) | Login, token refresh, and logout sequence diagrams |

---

## Top-Level Documents

| Document | Description |
|---|---|
| [decisions.md](./decisions.md) | Consolidated log of key architectural decisions and their rationale |

---

## Increment Status

| # | Increment | Status |
|---|---|---|
| 1 | Auth (JWT RS256, refresh rotation, RBAC) | Complete |
| 2 | Users, Roles, Permissions (CRUD, audit log, admin UI) | Complete |
| 3 | Document Upload (PDF, CSV, DOCX, TXT ingestion) | Planned |
| 4 | Chunking (recursive, semantic) | Planned |
| 5 | Embeddings | Planned |
| 6 | Vector Database (ChromaDB) | Planned |
| 7 | RAG Pipeline (retriever, prompt builder) | Planned |
| 8 | LangGraph (graph/workflow) | Planned |
| 9 | Agents (supervisor, HR, Finance, IT) | Planned |
