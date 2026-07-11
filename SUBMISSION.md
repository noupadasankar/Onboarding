# OptiAgent — Capstone Submission Runbook

Deloitte Capstone Program 2026

This document is the single reference for completing the four validation steps
required before submission. Follow them in order — Step 1 is a prerequisite for
all subsequent steps.

---

## Prerequisites

Before starting, ensure:

- Docker is running and `docker compose up` has started all services
- Node.js backend is reachable at `http://localhost:3000`
- AI service is reachable at `http://localhost:8100`
- PostgreSQL and ChromaDB containers are healthy

```bash
# Quick health check
curl http://localhost:8100/health
# Expected: {"status":"ok","version":"..."}

curl http://localhost:3000/api/health
# Expected: {"status":"ok"}
```

---

## Step 1 — Apply Prisma Migration (BLOCKER)

This adds the versioning columns to the `Document` table. **No other step works
without this migration.** Run it once; Prisma tracks it and will skip on re-runs.

```bash
cd web/backend
pnpm prisma:migrate dev --name add_document_versioning
```

### What this migration creates

| Change | SQL |
|---|---|
| `SUPERSEDED` added to `DocumentStatus` enum | `ALTER TYPE "DocumentStatus" ADD VALUE 'SUPERSEDED'` |
| `version INT NOT NULL DEFAULT 1` column | Added to `Document` table |
| `is_latest BOOLEAN NOT NULL DEFAULT TRUE` column | Added to `Document` table |
| `superseded_at TIMESTAMPTZ` column | Added to `Document` table (nullable) |
| `parent_document_id UUID` column | Self-referencing FK to `Document.id` (nullable) |
| Composite index | `CREATE INDEX ON "Document"("original_name", "department_id", "is_latest")` |

### Expected output

```
Environment variables loaded from .env
Prisma schema loaded from prisma/schema.prisma
Datasource "db": PostgreSQL database "optiagent" at "localhost:5432"

Applying migration `20260710000000_add_document_versioning`

The following migration(s) have been applied:

migrations/
  └─ 20260710000000_add_document_versioning/
       └─ migration.sql

Your database is now in sync with your schema.
```

---

## Step 2 — Install AI Service Dependency

The hybrid search feature requires `rank-bm25`. It is declared in `pyproject.toml`
so a full install picks it up automatically. Only do this once per environment.

```bash
cd web/ai-service

# Option A: full dev install (recommended — installs all deps including test tools)
pip install -e ".[dev]"

# Option B: runtime only
pip install "rank-bm25>=0.2.2"
```

### Verify

```bash
python -c "from rank_bm25 import BM25Okapi; print('rank_bm25 OK')"
# Expected: rank_bm25 OK
```

---

## Step 3 — Run the Automated Test Suite

All tests use in-memory ChromaDB and do not require a live stack. They run in
under 60 seconds on a development machine.

```bash
cd web/ai-service
pytest tests/ -v
```

### Expected result

```
tests/test_health.py::test_health_returns_ok                         PASSED
...
tests/versioning/test_document_versioning.py::TestDeleteVectors::...  (17 tests)
tests/retrieval/test_hybrid_retriever.py::TestHybridRetriever::...    (20 tests)
tests/retrieval/test_secure_retrieval.py::TestDepartmentFromContext::... (15 tests)

============= N passed in X.XXs =============
```

All three new test modules must pass. A summary of what each covers:

| Module | Tests | What it validates |
|---|---|---|
| `tests/versioning/test_document_versioning.py` | 17 | DELETE `/documents/{id}/vectors` — returns 200, correct count, idempotent, requires auth, does not affect other documents |
| `tests/retrieval/test_hybrid_retriever.py` | 20 | BM25 promotes exact identifiers (HR-204, TE-004, £150, Section 7.2, BUPA), RRF mechanics, graceful degradation on empty corpus or missing `rank_bm25` |
| `tests/retrieval/test_secure_retrieval.py` | 15 | `ctx.department` (from header) always wins over `body.department`, HR cannot escalate to Finance via body, cross-department isolation |

### Run individual modules

```bash
# Versioning only
pytest tests/versioning/test_document_versioning.py -v

# Hybrid search only
pytest tests/retrieval/test_hybrid_retriever.py -v

# Secure retrieval only
pytest tests/retrieval/test_secure_retrieval.py -v
```

---

## Step 4 — End-to-End Versioning Test (live stack)

This script exercises the full versioning flow against a running system. It
requires a valid JWT (HR Manager or Admin role).

### Get a token

Log in to the application normally and copy the `accessToken` from the response,
or use the dev admin credentials from your `.env` file:

```bash
curl -s -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@optiagent.dev","password":"your-dev-password"}' \
  | jq -r '.accessToken'
```

### Run the test

```bash
cd web/ai-service
python scripts/e2e_versioning_test.py \
  --node-url http://localhost:3000 \
  --ai-url  http://localhost:8100 \
  --token   eyJhbGc...   # paste your token here
```

### What each phase does

| Phase | Action | Pass condition |
|---|---|---|
| 1 | Upload v1 document ("20 days annual leave") | HTTP 201, `version=1` |
| 2 | Trigger indexing of v1 | `status=INDEXED`, chunk count > 0 |
| 3 | Chat: "How many days annual leave?" | Answer contains "20" |
| 4 | Upload v2 document ("25 days annual leave", same name) | HTTP 201, `version=2` |
| 5 | Verify v1 is SUPERSEDED in Postgres | `status=SUPERSEDED`, `isLatest=false` |
| 6 | Verify v1 vectors are deleted from ChromaDB | vector count decreased |
| 7 | Trigger indexing of v2 | `status=INDEXED` |
| 8 | Chat: "How many days annual leave?" | Answer contains "25", NOT "20" |
| 9 | Document list shows only v2 | v1 absent from default list |
| 10 | Cleanup | Vectors deleted, DB records removed |

### Expected output (summary)

```
Phase 1 PASS  Upload v1 document (version=1)
Phase 2 PASS  Index v1 (24 chunks indexed)
Phase 3 PASS  Chat proves v1 content ("20 days")
Phase 4 PASS  Upload v2 document (version=2)
Phase 5 PASS  v1 is SUPERSEDED in Postgres
Phase 6 PASS  v1 vectors deleted from ChromaDB
Phase 7 PASS  Index v2 (24 chunks indexed)
Phase 8 PASS  Chat proves v2 content ("25 days") — v1 content absent
Phase 9 PASS  Document list shows only v2
Phase 10 PASS Cleanup complete

All 10 phases passed. ✓
```

---

## Step 5 — Performance Benchmark (optional)

Measures latency for every stage of the ingestion and query pipelines. No token
required — the script uses the dev internal token.

```bash
cd web/ai-service
python scripts/performance_benchmark.py --runs 10
```

### Expected output shape

```
================================================================
  OptiAgent — AI Service Performance Benchmark
================================================================
  Target:      http://localhost:8100
  Search runs: 10

  ── INGESTION PIPELINE ──────────────────────────────────────
  Upload (network + disk write)         ~  45.0 ms
  Index pipeline (24 chunks)            ~ 280.0 ms  (openai/text-embedding-3-small)

  ChromaDB: 24 chunks, 1 document(s)
  Total ingestion latency: ~325.0 ms

  ── QUERY PIPELINE (RETRIEVAL ONLY) ─────────────────────────
  Query                             Hybrid    Dense-only    Delta
  Semantic — broad                 ~35ms       ~28ms       +7ms
  Keyword — HR-204                 ~38ms       ~29ms       +9ms
  Keyword — BUPA                   ~36ms       ~27ms       +9ms
  ...

  BM25+RRF overhead: +8ms average per query

  ── KEYWORD RECALL SPOT-CHECK ────────────────────────────────
  HR-204   → Hybrid top: "HR-204 entitles employees to..."  ✓
  TE-004   → Hybrid top: "TE-004: employees may take..."    ✓
  BUPA     → Hybrid top: "BUPA medical insurance: £150..."  ✓

  ── SUMMARY TABLE ─────────────────────────────────────────────
  Upload                           ~45ms   network + disk write
  Index pipeline                  ~280ms   24 chunks, embed + upsert
  Retrieval (dense-only)           ~28ms   embed + ChromaDB query + rerank
  Retrieval (hybrid)               ~37ms   + BM25 build + RRF fusion
  Hybrid overhead                   +9ms   BM25 + RRF added cost
```

Hybrid search overhead is negligible (~10ms at 24 chunks). At 1 000 chunks,
expect ~15–50ms overhead — acceptable for enterprise knowledge retrieval.

---

## Implemented Features Summary

| Feature | Increment | Status |
|---|---|---|
| Document upload + storage | 1–2 | ✅ Complete |
| Multi-format ingestion (PDF, DOCX, XLSX, CSV, TXT) | 3 | ✅ Complete |
| Text cleaning and chunking | 4 | ✅ Complete |
| Embedding generation (OpenAI / local) | 5 | ✅ Complete |
| ChromaDB vector store | 6 | ✅ Complete |
| RAG retrieval pipeline (retrieve, rerank, context, prompt) | 7 | ✅ Complete |
| LLM integration (Anthropic, OpenAI, Ollama) | 8 | ✅ Complete |
| LangGraph supervisor + domain agents | 9 | ✅ Complete |
| Document versioning (SUPERSEDED, vector deletion) | 10 | ✅ Complete |
| Hybrid search — BM25 + dense RRF | 10 | ✅ Complete |
| Secure retrieval — department from JWT, not body | 10 | ✅ Complete |

---

## Known Limitations (Acceptable for Capstone)

| Limitation | Production Fix |
|---|---|
| Race condition on concurrent same-name uploads | Distributed lock (Redis) or unique DB constraint |
| AI service downtime during vector deletion leaves stale vectors | Durable job queue (BullMQ) with retry |
| BM25 index rebuilt per query from ChromaDB corpus | Pre-build and cache per-department index on upload events |
| Conversation memory is in-process (lost on restart) | Redis-backed memory store |
| No structured observability | Prometheus counters on 4 key operations |
| No user feedback loop | `PUT /messages/{id}/feedback` + thumbs up/down DB columns |

These are operational enhancements, not architectural gaps. The core pipeline
(ingestion → retrieval → generation) is complete and production-quality.

---

## File Reference

| What you need | Where to find it |
|---|---|
| Architecture overview | `docs/architecture/ai-service-architecture.md` |
| Document versioning sequence diagram | `docs/diagrams/document-versioning-sequence.md` |
| Hybrid search sequence diagram | `docs/diagrams/hybrid-search-sequence.md` |
| Versioning tests | `web/ai-service/tests/versioning/test_document_versioning.py` |
| Hybrid retriever tests | `web/ai-service/tests/retrieval/test_hybrid_retriever.py` |
| Secure retrieval tests | `web/ai-service/tests/retrieval/test_secure_retrieval.py` |
| E2E versioning script | `web/ai-service/scripts/e2e_versioning_test.py` |
| Performance benchmark | `web/ai-service/scripts/performance_benchmark.py` |
| Prisma schema | `web/backend/prisma/schema.prisma` |
| AI gateway (Node→AI HTTP client) | `web/backend/src/infrastructure/ai/ai-gateway.ts` |
| HybridRetriever implementation | `web/ai-service/app/retrieval/hybrid_retriever.py` |
| Vector delete endpoint | `web/ai-service/app/api/v1/vectorstore.py` |
