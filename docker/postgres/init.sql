-- Runs once on first Postgres init. Enables extensions the schema relies on.
-- pgcrypto provides gen_random_uuid() used by the AI service's Alembic tables and
-- is the basis for the capstone's AES-256-at-rest (pgcrypto) requirement.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Separate logical database for AI-service-owned tables (prompt templates, memory).
-- Prisma (Node) uses the primary database; Alembic (Python) uses this one.
SELECT 'CREATE DATABASE optiagent_ai'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'optiagent_ai')\gexec
