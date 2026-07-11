# OptiAgent — System Architecture Overview

OptiAgent is a three-service platform. Each service has a single responsibility and a
well-defined boundary; they communicate over HTTP(S)/WSS with explicit contracts.

## Service topology

```mermaid
flowchart TD
  subgraph Browser
    FE["frontend<br/>React 19 · Redux Toolkit · RTK Query"]
  end

  subgraph Gateway["backend — Node/Express (Clean Architecture + DI)"]
    MW["Middleware: JWT · RBAC · rate-limit · request-id · logging"]
    APP["Application services"]
    REPO["Repositories (interfaces)"]
    PRISMA["Prisma"]
  end

  subgraph AI["ai-service — Python/FastAPI"]
    GUARD["Internal-token guard"]
    AGENTS["LangGraph agents · RAG (future increments)"]
  end

  PG[("PostgreSQL<br/>Users · Roles · Audit")]
  RD[("Redis<br/>refresh tokens · rate limits")]
  CH[("ChromaDB<br/>vectors")]
  LLM["OpenAI / Anthropic"]

  FE -- "HTTPS (Bearer JWT)" --> MW
  MW --> APP --> REPO --> PRISMA --> PG
  APP -- "sessions / limits" --> RD
  APP -- "internal token + X-User-Id/Role" --> GUARD
  GUARD --> AGENTS --> CH
  AGENTS --> LLM
```

## Responsibilities & boundaries

| Concern | Owner | Notes |
|---|---|---|
| Authentication, refresh, logout | **backend** | RS256 JWT; Python never authenticates users |
| Authorization (RBAC / permissions) | **backend** | Enforced in middleware before controllers |
| CRUD & business logic | **backend** | Route→MW→Validator→Controller→Service→Repo→Prisma |
| Relational data | **backend** (PostgreSQL) | Users, Roles, Permissions, Audit |
| Agents, RAG, embeddings, memory | **ai-service** | Trusts the gateway via internal token |
| Vector store, prompt templates | **ai-service** (ChromaDB + Alembic) | No CRUD business logic here |
| UI, routing, state | **frontend** | Feature-first; RBAC-aware routing |
| Shared DTOs / RBAC / Zod | **shared** | Imported by frontend + backend |

## Cross-service trust model

The browser holds a short-lived RS256 access token. The Node gateway verifies it, resolves
the principal + permissions, and — only for AI requests — calls the Python service with an
**internal service token** plus `X-User-Id` / `X-User-Role` headers. The Python service
verifies the internal token and trusts those headers; it has no notion of end-user login.

See [ADR 0001](adr/0001-three-service-split.md) and [ADR 0002](adr/0002-node-gateway-python-ai.md).
