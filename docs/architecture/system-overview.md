# System Overview

OptiAgent — Deloitte Capstone 2026

---

## Table of Contents

1. [High-Level Architecture](#high-level-architecture)
2. [Three-Service Split Rationale](#three-service-split-rationale)
3. [End-to-End Data Flow](#end-to-end-data-flow)
4. [Technology Choices](#technology-choices)
5. [Cross-Cutting Concerns](#cross-cutting-concerns)
6. [Deployment Topology](#deployment-topology)

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Client Browser                             │
│                    React 19 + Redux + RTK Query                     │
│                         localhost:3000                              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTPS
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         NGINX Reverse Proxy                         │
│              /api  → backend:8000                                   │
│              /     → frontend:3000                                  │
└──────────────┬──────────────────────────────────────────────────────┘
               │
       ┌───────┴──────────────────────────────────┐
       │                                          │
       ▼                                          ▼
┌──────────────────────┐               ┌──────────────────────┐
│   Node.js Backend    │               │   React Frontend     │
│   Express + Prisma   │               │   (served by NGINX)  │
│   InversifyJS DI     │               │   :3000              │
│   JWT RS256 / Redis  │               └──────────────────────┘
│   :8000              │
└──────────┬───────────┘
           │
    ┌──────┴───────────────────────────────────┐
    │                                          │
    ▼                                          ▼
┌──────────────────────┐          ┌────────────────────────────┐
│   PostgreSQL 16      │          │   Python AI Service        │
│   Primary datastore  │          │   FastAPI + LangGraph      │
│   :5432              │          │   ChromaDB + RAG           │
└──────────────────────┘          │   :8100                    │
                                  └──────────────┬─────────────┘
┌──────────────────────┐                         │
│   Redis 7            │          ┌──────────────▼─────────────┐
│   Refresh token      │          │   ChromaDB                 │
│   store / cache      │          │   Vector store             │
│   :6379              │          │   :8200                    │
└──────────────────────┘          └──────────────┬─────────────┘
                                                 │
                                  ┌──────────────▼─────────────┐
                                  │   Claude (LLM)             │
                                  │   Anthropic API            │
                                  └────────────────────────────┘
```

---

## Three-Service Split Rationale

OptiAgent is divided into three runtime services: a React frontend, a Node.js API gateway, and a Python AI service. This split reflects three fundamentally different concerns with different scaling, language, and dependency requirements.

### React Frontend

The frontend is a single-page application that runs entirely in the browser after the initial load. It is responsible for user interaction, state management, and presenting data returned by the backend API. It has no direct access to the database, the AI service, or any LLM.

Serving the frontend separately from the API allows the two to scale independently, be deployed to a CDN in production, and be developed by frontend engineers without requiring a running backend.

### Node.js API Gateway

The Node.js backend is the system's trust boundary. Every request from the browser passes through it. It is responsible for:

- Authentication and session management (JWT RS256, refresh token rotation)
- Authorization (permission-based RBAC enforcement)
- Business logic orchestration (user management, role assignment, audit logging)
- Proxying AI requests to the Python service after validating the caller's identity

Node.js was chosen here because its JWT ecosystem, HTTP middleware libraries, and TypeScript type system are well-suited to an API gateway role. Non-AI workloads should not depend on the Python runtime.

### Python AI Service

The AI service is isolated because the relevant libraries — LangGraph, LangChain, ChromaDB, sentence-transformers, and the Anthropic SDK — are Python-native. Running them from Node.js would require fragile subprocess bridging.

Isolation also means the AI service can be scaled independently (more replicas during heavy inference load), restarted without affecting authentication or user management, and developed by data engineers without touching the API gateway.

---

## End-to-End Data Flow

The following describes a complete AI query once all increments are implemented.

```
1. Browser sends POST /api/ai/query with Bearer token in Authorization header.

2. NGINX forwards the request to the Node.js backend on :8000.

3. Backend middleware chain runs:
   a. requestId middleware assigns a correlation ID (X-Request-ID header).
   b. requestLogger logs the incoming request with the correlation ID.
   c. authenticate middleware validates the JWT RS256 signature and expiry,
      populates req.auth with { userId, email, permissions[] }.
   d. authorize middleware checks that req.auth.permissions includes 'ai:query'.
   e. validate middleware runs the Zod schema for the request body.
   f. Controller receives a clean, authenticated, validated request object.

4. Controller calls AIService.query(userId, queryText).

5. AIService calls the Python AI service at :8100 via HTTP, passing:
   - The user query
   - An internal service token (not the user JWT)
   - The correlation ID for distributed tracing

6. Python AI service:
   a. Validates the internal service token.
   b. LangGraph supervisor routes the query to the appropriate agent (HR, Finance, IT).
   c. The agent invokes the RAG pipeline:
      i.  Embed the query using the embedding model.
      ii. Query ChromaDB for the top-k relevant document chunks.
      iii. Build a prompt from the retrieved context.
      iv. Call Claude via the Anthropic API.
   d. Returns the LLM response as JSON.

7. Node.js backend:
   a. Receives the AI service response.
   b. Writes an audit log entry (non-fatal, fire-and-forget).
   c. Wraps the response in the standard ApiResponse envelope.
   d. Returns HTTP 200 to the browser.

8. Browser RTK Query cache receives the response and the UI updates.
```

---

## Technology Choices

### Frontend Layer

| Concern | Technology | Reason |
|---|---|---|
| UI framework | React 19 | Industry standard, concurrent rendering, large ecosystem |
| State management | Redux Toolkit | Structured global state, DevTools, predictable updates |
| API layer | RTK Query | Co-located data fetching, automatic caching, tag invalidation |
| Styling | TailwindCSS | Utility-first, consistent design tokens, no CSS-in-JS overhead |
| Language | TypeScript | Shared types with backend via shared package |

### Backend Layer

| Concern | Technology | Reason |
|---|---|---|
| Runtime | Node.js 20 | Event-loop concurrency, mature JWT/HTTP ecosystem |
| Framework | Express | Minimal, well-understood, large middleware library |
| DI container | InversifyJS | Decorator-based IoC, testable services, TypeScript-native |
| ORM | Prisma | Type-safe query builder, schema-first migrations |
| Database | PostgreSQL 16 | ACID compliance, JSONB for flexible fields, well-supported |
| Session store | Redis 7 | Fast key-value store for refresh token whitelist |
| Auth | JWT RS256 | Asymmetric signing; public key can be shared with AI service |
| Validation | Zod | Schema-first, type inference, composable |

### AI Service Layer

| Concern | Technology | Reason |
|---|---|---|
| Framework | FastAPI | Async, OpenAPI generation, Python-native |
| Orchestration | LangGraph | Stateful multi-agent graphs, supervisor pattern support |
| Vector store | ChromaDB | Embedded-friendly, local-first, Python-native |
| LLM | Claude (Anthropic) | Instruction-following, long context, tool use |
| Migrations | Alembic | SQL migration management for the AI service's own schema |

---

## Cross-Cutting Concerns

### Authentication

Every request to the Node.js backend (except `/auth/login` and `/auth/refresh`) must carry a valid RS256-signed JWT in the `Authorization: Bearer <token>` header. The middleware validates the signature, checks expiry, and populates `req.auth`. The AI service uses a separate internal service token issued at startup; it never receives user JWTs.

### Correlation IDs

The `requestId` middleware assigns a UUID to every incoming request and attaches it as `X-Request-ID` on both the incoming `req` object and the outgoing response header. When the backend calls the AI service, it forwards this header. This allows a single user-visible request to be traced across all service logs.

### Audit Logging

A cross-cutting `AuditService` is injected into any service that performs state-changing operations. It writes structured audit records (actor, action, target entity, timestamp, IP address) to the database. Audit write failures are caught and logged to the application logger but never propagated to the caller — audit failures must never block business operations.

### Error Handling

All error responses use the shared `ApiResponse` envelope:

```json
{
  "success": false,
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "You do not have permission to perform this action."
  }
}
```

A global Express error handler catches unhandled errors, logs them with the correlation ID, and returns a sanitized 500 response that does not expose internal stack traces.

---

## Deployment Topology

See [deployment-architecture.md](./deployment-architecture.md) for full detail.

In summary:

- All services run as Docker containers orchestrated by Docker Compose.
- NGINX acts as the single public entry point, terminating TLS in production.
- The Node.js backend, Python AI service, PostgreSQL, Redis, and ChromaDB are on an internal Docker network not exposed to the host.
- Secrets are injected via environment variables from `.env` files; no secrets are baked into container images.
