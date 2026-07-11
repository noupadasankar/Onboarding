# Architectural Decision Log

OptiAgent — Deloitte Capstone 2026

This document records significant architectural decisions made during the design and implementation of OptiAgent, along with the reasoning behind each choice. For decisions with their own dedicated ADR, a reference is included.

---

## Decision Table

| # | Decision | Rationale |
|---|---|---|
| 1 | Node.js as API gateway | See below |
| 2 | Python AI service isolated | See below |
| 3 | Static roles from shared package | See below |
| 4 | Repository pattern with interfaces | See below |
| 5 | Permission-based RBAC | See below |
| 6 | Non-fatal audit logging | See below |
| 7 | URL-synced filter state | See below |
| 8 | RTK Query tag-based cache | See below |

---

## 1. Node.js as API Gateway (not Python)

**Decision:** The backend API layer is implemented in Node.js/TypeScript with Express, not in the Python AI service.

**Rationale:**
- Node.js has a mature ecosystem for HTTP middleware, JWT handling (RS256), and request validation that is well-suited to an API gateway role.
- TypeScript provides strong typing across the request/response surface, reducing integration errors with the React frontend.
- The team has established familiarity with the Node.js/TypeScript toolchain, reducing onboarding cost.
- Separating authentication and business-logic routing from AI processing keeps each service focused on a single concern.
- Non-AI workloads (user management, RBAC, audit logging) do not belong in an AI-specific runtime.

**See also:** [ADR-0002](./architecture/adr/0002-node-gateway-python-ai.md)

---

## 2. Python AI Service Isolated

**Decision:** All AI workloads (LangGraph, RAG pipeline, ChromaDB, LLM calls) are handled by a dedicated Python FastAPI service, not inside the Node.js backend.

**Rationale:**
- The LangGraph, LangChain, and ChromaDB libraries are Python-native. Using them from Node.js would require subprocess bridging or a thin HTTP proxy, both of which add fragility.
- The AI service can be scaled independently from the API gateway. During heavy inference load, only the Python service needs additional replicas.
- Python data-science tooling (numpy, sentence-transformers, etc.) integrates naturally in this service without polluting the Node.js runtime.
- Failure isolation: a crash in the AI service does not take down authentication, user management, or the API gateway.

**See also:** [ADR-0001](./architecture/adr/0001-three-service-split.md), [ADR-0002](./architecture/adr/0002-node-gateway-python-ai.md)

---

## 3. Static Roles from Shared Package (not Database)

**Decision:** The set of valid role names (ADMIN, HR_MANAGER, FINANCE_MANAGER, IT_MANAGER, EMPLOYEE) is defined in a shared TypeScript package and compiled into the backend, rather than stored in a roles database table with free-form names.

**Rationale:**
- Role names are referenced in code (guards, permission mappings, frontend routing). Allowing arbitrary database-defined role names would require runtime lookups on every request and make compile-time safety impossible.
- The set of roles is small and changes only with a deliberate code release, not at runtime. There is no operational need for administrators to create new role types dynamically.
- Eliminating the role repository removes a round-trip on every authenticated request. The roles a user holds are embedded in the JWT and loaded from the database once at login.
- Permissions remain in the database and are fully configurable, so the enforcement model is flexible even though role names are static.

---

## 4. Repository Pattern with Interfaces

**Decision:** Every data-access concern is implemented behind a TypeScript interface (e.g., `IUserRepository`), with a Prisma-backed concrete implementation. Services depend only on the interface.

**Rationale:**
- Services can be unit-tested using in-memory fake repositories without standing up a database. This dramatically reduces the cost of writing and maintaining service-layer tests.
- The concrete Prisma implementation can be swapped (e.g., to a different ORM or a test double) without modifying service code.
- InversifyJS binds the interface symbol to the concrete class, keeping the wiring declarative and centralized in the DI module.

---

## 5. Permission-Based RBAC (not Role-Based)

**Decision:** Authorization guards check for specific permission strings (e.g., `users:read`, `users:write`) rather than checking role membership directly.

**Rationale:**
- Roles change over time (new roles are added, role boundaries shift). If guards check roles by name, every role change requires touching guard code.
- Permissions represent stable capabilities. A guard that checks `users:write` remains correct regardless of which roles are later granted that permission.
- The mapping of permissions to roles is managed in the database and can be updated by an administrator without a code release.
- The user's resolved permission set is embedded in the JWT at login, so authorization checks are local (no database lookup per request).

---

## 6. Non-Fatal Audit Logging

**Decision:** The audit logging service is injected as a cross-cutting concern and its failures are silently caught. An audit log write failure never causes a business operation to fail or return an error to the caller.

**Rationale:**
- Audit logging is an observability concern, not a transactional one. The primary operation (create user, update role, etc.) has already succeeded if the audit write fails.
- Blocking a user-facing operation because of a logging side-effect would be disproportionate and unexpected from a caller perspective.
- Audit log failures are emitted to the application logger so they can be monitored and alerted on separately without disrupting users.

---

## 7. URL-Synced Filter State

**Decision:** List views (users table, etc.) synchronize their filter and pagination state to the URL query string rather than storing it only in component or Redux state.

**Rationale:**
- Filters survive a page refresh. A user who applies filters, copies the URL, and shares it with a colleague sees the same filtered view.
- Browser back/forward navigation moves through filter states naturally, matching user expectations for a web application.
- Deep-linked filter states reduce support friction: a manager can send a filtered view directly to a team member.
- RTK Query derives its cache key from the serialized URL parameters, so the cache is automatically keyed by filter combination.

---

## 8. RTK Query Tag-Based Cache Invalidation

**Decision:** RTK Query endpoint definitions use entity tags (e.g., `{ type: 'User', id }`, `{ type: 'User', id: 'LIST' }`) to control cache invalidation on mutations.

**Rationale:**
- Tag-based invalidation is surgical: a `PATCH /users/:id` invalidates only the specific user entry and the list, not the entire cache.
- Avoiding broad invalidation reduces unnecessary re-fetches and keeps the UI responsive after mutations.
- The pattern is declarative and co-located with the endpoint definition, making the invalidation logic easy to audit and maintain.
- RTK Query handles the timing and coordination of re-fetches automatically once tags are declared, eliminating manual `dispatch(invalidateTags(...))` calls scattered through components.
