# postgres

## Purpose

This directory contains the one-time initialization script that runs when the Postgres
container is started for the first time against an empty data volume. Its sole job is to
put the database into a state where the application migration tools (Prisma and Alembic)
can take over and own all subsequent schema changes.

After first-boot initialization, this directory plays no further role in schema evolution.
All structural changes to the database are applied exclusively through the migration
frameworks owned by each service.

## Responsibilities

- Create the application database if it does not already exist.
- Enable the PostgreSQL extensions required by the platform (`uuid-ossp` for
  `gen_random_uuid()` and `pgcrypto` for server-side hashing utilities).
- Provide a safe, idempotent script that can be re-run without side effects on an
  already-initialized volume.

## Does NOT Contain

- Schema creation DDL (tables, indexes, foreign keys). That belongs to Prisma migrations
  in `backend/prisma/migrations/` and Alembic migrations in `ai-service/alembic/`.
- Seed data. Application seed data lives in `backend/prisma/seed.ts`.
- Backup or restore scripts.
- Postgres configuration tuning (`postgresql.conf` overrides) — those are set via
  environment variables in `docker-compose.yml`.

## Architecture Position

```
docker-compose up (first run)
        │
        ▼
  Postgres 16 container
        │  mounts docker/postgres/init.sql as an initdb script
        ▼
  init.sql runs once:
    - CREATE DATABASE IF NOT EXISTS optiagent
    - CREATE EXTENSION IF NOT EXISTS "uuid-ossp"
    - CREATE EXTENSION IF NOT EXISTS "pgcrypto"
        │
        ▼
  Subsequent starts: init.sql is skipped (volume already initialized)
        │
        ├─ Node backend (Prisma)  → owns users, roles, permissions, audit tables
        └─ Python AI service (Alembic) → owns prompt templates, conversation memory tables
           (both schemas live in the same Postgres instance but are independently managed)
```

## Expected Contents

```
postgres/
├── init.sql      — idempotent first-boot script: database creation + extension setup
└── README.md     — this file
```

## Design Principles

- **Minimal surface area.** The init script does the least possible work so that each
  service's migration framework retains full ownership of its schema.
- **Schema isolation.** The Node backend (Prisma) and the Python AI service (Alembic)
  manage independent schema namespaces within the same Postgres instance. Neither
  migration framework touches the other's tables.
- **Idempotency.** All statements use `IF NOT EXISTS` guards so the script is safe to
  re-run without dropping data.

## Current Status

Implemented

## Future Work

If the platform expands to multiple environments with separate Postgres instances, add
environment-specific init variants. If the AI service schema grows to require its own
database user with restricted privileges, add the `CREATE ROLE` and `GRANT` statements
here rather than in application code.
