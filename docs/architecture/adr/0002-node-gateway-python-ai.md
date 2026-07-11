# ADR 0002 — Node is the auth gateway; Python never authenticates users

- **Status:** Accepted
- **Date:** 2026-07-09
- **Supersedes:** capstone document §2.1 (which placed JWT/RBAC inside FastAPI)

## Context

The capstone submission (`OptiAgent_Deloitte_Capstone_2026.md`, §2.1) originally described
FastAPI as the API gateway performing its own JWT auth and RBAC. During implementation we
adopted a stronger separation of concerns: a Node/Express gateway in front of the Python AI
service.

## Decision

- The **Node backend** owns all authentication (RS256 JWT issue/refresh/logout), authorization
  (RBAC/permissions), CRUD, rate limiting, and audit logging.
- The **Python ai-service never authenticates end users.** The gateway calls it with an
  **internal service token** (shared secret) plus forwarded `X-User-Id` and `X-User-Role`
  headers. The AI service verifies the internal token and trusts those headers.

## Rationale

- Keeps security-critical logic in one hardened surface (the gateway) rather than duplicated
  across two languages.
- The AI service stays focused on agents/RAG and has a minimal, auditable trust boundary.
- Matches the session engineering directive and the "Node handles authentication before
  forwarding AI requests" requirement.

## Consequences

- The capstone doc's §2 diagrams are now out of date and should be reconciled in a later
  documentation pass (tracked as future work). This ADR is the source of truth until then.
- The internal service token must be provisioned as a secret in every environment and rotated
  like any other credential.
