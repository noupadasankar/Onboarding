# docker

## Purpose

This directory contains all container definitions and orchestration configuration for the
OptiAgent platform. It is the single authoritative place for infrastructure topology: which
services exist, which ports they expose, how they communicate on the internal Docker network,
and how the environment differs between local development and production deployment.

The compose file drives both developer workstations (via the `dev` profile) and the
production environment (via the `prod` profile), ensuring the two are as structurally
identical as possible while still allowing profile-specific differences such as TLS
termination and resource constraints.

## Responsibilities

- Define the `docker-compose.yml` that declares all infrastructure services (Postgres,
  Redis, ChromaDB, NGINX).
- Provide NGINX configuration files for reverse-proxying the frontend and backend.
- Provide Postgres initialization scripts for first-boot database setup.
- Own the separation between `dev` and `prod` compose profiles.
- Document port assignments and inter-service network topology.

## Does NOT Contain

- Application source code for any service (frontend, backend, ai-service, shared).
- Prisma migration files (those live in `backend/prisma/`).
- Alembic migration files (those live in `ai-service/alembic/`).
- Secrets or production credentials (use environment variable injection or a secrets
  manager at deploy time).
- CI/CD pipeline definitions (those live in `.github/`).

## Architecture Position

```
Developer workstation / Production host
│
├─ docker-compose.yml (this directory)
│     │
│     ├─ postgres   :5432  — primary relational store
│     ├─ redis      :6379  — session cache, rate-limit counters, job queues
│     ├─ chromadb   :8200  — vector store for RAG embeddings
│     └─ nginx      :80 / :443 (prod only)
│           ├─ /api  → backend  :8000
│           └─ /     → frontend :3000 (dev) or static build (prod)
│
Application services (backend :8000, ai-service :8100, frontend :3000)
run outside Docker in development, or as additional compose services in production.
```

## Expected Contents

```
docker/
├── docker-compose.yml      — orchestrates postgres, redis, chromadb, nginx
├── nginx/
│   ├── nginx.conf          — main NGINX config with upstream blocks
│   └── frontend.conf       — server block proxying / to the React app
└── postgres/
    └── init.sql            — creates database, enables uuid-ossp + pgcrypto
```

## Design Principles

- **Profile separation.** The `dev` profile omits TLS and uses relaxed resource limits.
  The `prod` profile adds TLS termination at NGINX and enforces memory/CPU caps.
- **Infrastructure only.** This directory does not build or run application code; it only
  manages the services application code depends on.
- **Idempotent initialization.** Postgres init scripts use `IF NOT EXISTS` guards so they
  are safe to run on an already-initialized volume.

## Current Status

Implemented

## Future Work

Add a production compose override (`docker-compose.prod.yml`) with CPU/memory limits,
restart policies, and a secrets-provider integration. Add a healthcheck for ChromaDB once
the RAG increment (Increment 6) is active.
