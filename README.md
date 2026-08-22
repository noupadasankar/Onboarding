# OptiAgent

> Deloitte Technology Consulting Capstone 2026

## Overview

OptiAgent is an enterprise AI platform that embeds trustworthy, governance-aware AI agents
into core business operations across HR, Finance, and IT. It is designed for large
organizations that need to augment knowledge-worker workflows with LLM-powered automation
while maintaining strict access control, full audit trails, and explainable decision paths.

The platform is built as a production-grade monorepo with three independently deployable
services: a React frontend, a Node.js API gateway, and a Python AI service. Role-based
access control is enforced at the gateway layer before any AI call is made, and every
agent action is attributable to an authenticated user.

## Architecture

```
Browser (React SPA)
        │
        ▼
   Nginx Gateway (:80)
   ├── /           → React static files
   └── /api/       → Node.js Backend (:8000)
                           │
                ┌──────────┴──────────┐
                │                     │
          PostgreSQL              Redis
          (Prisma ORM)        (token store + cache)
                │
                └──── FastAPI AI Service (:8100)    ← internal only, never browser-accessible
                              │
                    ┌─────────┴──────────┐
                    │                    │
                ChromaDB            OpenAI / Anthropic
              (vector store)          (LLM provider)
```

The Node backend authenticates every request before forwarding it to the AI service. The
Python service never authenticates end users; it trusts the gateway via an internal shared
secret. This keeps AI-specific code entirely separate from auth logic.

Database ownership is split by service:

- **Node backend** owns `users`, `roles`, `permissions`, `audit_logs`, and all relational
  business data — managed via **Prisma** migrations in `backend/prisma/`.
- **Python AI service** owns vector embeddings, prompt templates, and conversation memory
  — stored in **ChromaDB** and Postgres tables managed via **Alembic** in
  `ai-service/alembic/`.

Both Postgres schemas live in the same Postgres 16 instance but are independently
versioned.

## Services

| Directory | Package / Image | Role |
|---|---|---|
| `frontend/` | `@optiagent/frontend` | React 19 + Vite + Redux Toolkit + RTK Query + Tailwind + shadcn/ui. Renders the agent dashboard and all CRUD surfaces. |
| `backend/` | `@optiagent/backend` | Node 20 + Express + TypeScript + InversifyJS + Prisma. Auth, RBAC, REST/WebSocket gateway. Swagger docs at `/docs`. |
| `ai-service/` | `optiagent-ai` | Python 3.11 + FastAPI + LangGraph + LangChain. Agent orchestration, RAG, embeddings. Receives forwarded user context from the gateway. |
| `shared/` | `@optiagent/shared` | Pure TypeScript library. DTOs, Zod schemas, Role/Permission enums, API envelope types. Consumed by both frontend and backend at compile time. |

## Quick Start

### Prerequisites

- Node.js 20+ · pnpm 8+
- Python 3.11
- Docker Desktop

### 1. Start infrastructure

```bash
cp .env.example .env
# Fill in OPENAI_API_KEY and set a strong INTERNAL_SERVICE_TOKEN

docker compose -f docker/docker-compose.yml up -d postgres redis chromadb
```

### 2. Node backend

```bash
cd web/backend
cp .env.example .env   # already configured for local Docker infra

# First run only: generate RS256 keypair
node scripts/generate-keys.mjs

pnpm install
pnpm prisma:migrate dev   # create schema + run migrations
pnpm prisma:seed
pnpm prisma:migrate dev
          # insert demo users, roles, departments
pnpm dev                  # http://localhost:8000  ·  Swagger: /api/docs
```

### 3. AI service

```bash
cd web/ai-service
cp .env.example .env   # add your OPENAI_API_KEY here
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8100
```

### 4. Frontend

```bash
cd web/frontend
pnpm install
pnpm dev   # http://localhost:5173
```

### Demo accounts (password: `Password123!`)

| Email | Role |
|---|---|
| `employee@optiagent.dev` | EMPLOYEE |
| `hr.manager@optiagent.dev` | HR_MANAGER |
| `finance.admin@optiagent.dev` | FINANCE_ADMIN |
| `it.admin@optiagent.dev` | IT_ADMIN |

### Full Docker stack (production-like)

```bash
docker compose -f docker/docker-compose.yml --profile full up --build
# Open http://localhost
```

## Project Structure

```
.
├── frontend/           React 19 SPA — agent dashboard and admin UI
├── backend/            Node.js API gateway — auth, RBAC, CRUD, WebSocket
│   └── prisma/         Prisma schema + migrations + seed script
├── ai-service/         Python AI service — LangGraph agents, RAG, embeddings
│   └── alembic/        Alembic migrations for AI-service-owned tables
├── shared/             @optiagent/shared — cross-service contracts
│   └── src/
│       ├── auth/       DTOs, Zod schemas, Role/Permission constants
│       ├── common/     ApiResponse envelope, Paginated<T>, pagination schema
│       └── errors/     ErrorCode enum
├── docker/             docker-compose.yml, NGINX config, Postgres init
│   ├── nginx/          nginx.conf + frontend.conf
│   └── postgres/       init.sql (extensions + database creation)
└── docs/               Architecture writeups, ADRs, sequence diagrams
    └── architecture/
```

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`) runs on every push to `main` / `develop`:

1. **Shared** — typecheck + build the shared package artifact
2. **Backend** — typecheck, tests against real Postgres + Redis services
3. **Frontend** — typecheck, Vitest component tests, Vite build
4. **AI Service** — ruff lint, mypy type-check, pytest
5. **Docker build** — build all three images (on `main` only, with layer caching)

## Testing

```bash
# Backend (Vitest + supertest)
pnpm --filter @optiagent/backend test

# Frontend (Vitest + React Testing Library)
pnpm --filter @optiagent/frontend test

# AI service (pytest)
cd web/ai-service && pytest
```

## Documentation

Architecture writeups, Architecture Decision Records (ADRs), and sequence diagrams live in
[`docs/`](docs/). Start with:

- [`docs/architecture/00-overview.md`](docs/architecture/00-overview.md) — system-wide
  architecture narrative
- [`docs/architecture/01-auth-vertical-slice.md`](docs/architecture/01-auth-vertical-slice.md) —
  the authentication increment as the canonical pattern for all future increments

## Build Status

| Phase | Status | Description |
|---|---|---|
| Phase 1 — AI Service | ✅ Complete | FastAPI · LangGraph supervisor · HR/Finance/IT agents · RAG · ChromaDB |
| Phase 2 — Node Backend | ✅ Complete | Auth · RBAC · Users · Departments · Documents · Chat · Dashboard · Analytics · Notifications · Admin |
| Phase 3 — React Frontend | ✅ Complete | Login · Layout · Dashboard · Chat · Documents · Departments · Analytics · Notifications · Profile · Admin |
| Phase 4 — Integration | ✅ Complete | Docker Compose · Nginx gateway · Environment wiring |
| Phase 5 — Production | ✅ Complete | GitHub Actions CI/CD · Health checks · Structured logging · Prisma migrations |
| Phase 6 — Demo Prep | ✅ Complete | 7 sample documents (HR/Finance/IT) · 4 sequence diagrams · Demo guide · Presentation outline |

## AI Service Increments

| # | Name | Description |
|---|---|---|
| 1 | FastAPI Foundation | Project scaffold, internal auth, health endpoint |
| 2 | Internal Auth | HMAC token guard on all AI endpoints |
| 3 | Document Ingestion | File upload, text extraction, document model |
| 4 | Chunking | Semantic chunking pipeline with metadata |
| 5 | Embeddings | OpenAI/Voyage provider abstraction, batch embedding |
| 6 | ChromaDB | Vector store integration, collection manager |
| 7 | Retrieval | Semantic search, reranker, context builder, prompt builder |
| 8 | RAG Chat | LLM provider abstraction, citation builder, conversation store |
| 9 | LangGraph Supervisor | Stateful multi-agent graph, routing logic |
| 10 | Multi-Agent Platform | Finance/IT/Governance agents, parallel workflows, eval framework |

## License

UNLICENSED — Deloitte Capstone 2026 internal project.
