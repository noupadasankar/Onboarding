# AI Service Architecture

OptiAgent — Python FastAPI AI Service

---

## Table of Contents

1. [Service Responsibilities](#service-responsibilities)
2. [Application Structure](#application-structure)
3. [Internal Service Authentication](#internal-service-authentication)
4. [Data Ownership Boundary](#data-ownership-boundary)
5. [RAG Pipeline](#rag-pipeline)
6. [Hybrid Search (BM25 + Dense RRF)](#hybrid-search-bm25--dense-rrf)
7. [Document Versioning](#document-versioning)
8. [Secure Retrieval — Department Scoping](#secure-retrieval--department-scoping)
9. [LangGraph Supervisor Pattern](#langgraph-supervisor-pattern)
10. [ChromaDB Vector Store](#chromadb-vector-store)

---

## Service Responsibilities

The Python AI service is responsible for all machine-learning and LLM workloads within OptiAgent. It is intentionally isolated from the Node.js API gateway: user authentication, RBAC, business-logic routing, and relational data are handled in Node.js, while the AI service focuses exclusively on:

- Receiving validated, authenticated requests from the Node.js backend
- Running the full RAG pipeline: chunking, embedding, hybrid retrieval, reranking, prompt construction
- Calling the LLM via the configured provider (Anthropic, OpenAI, or Ollama)
- Managing document loaders and chunkers for ingested content
- Owning the ChromaDB vector store and its associated metadata
- Routing queries to the appropriate specialist agent via a LangGraph supervisor
- Deleting stale document vectors when a new document version supersedes an old one

The AI service is never called directly by the browser. All traffic reaches it through the Node.js backend, which validates the caller's identity before forwarding.

---

## Application Structure

```
ai-service/
├── app/
│   ├── __init__.py
│   ├── main.py            ← FastAPI app factory, lifespan, router mounting
│   │
│   ├── api/               ← HTTP routers and endpoint handlers
│   │   └── v1/
│   │       ├── router.py         ← mounts all sub-routers
│   │       ├── health.py         ← GET /health
│   │       ├── documents.py      ← POST /documents/upload, /documents/{id}/index
│   │       ├── vectorstore.py    ← GET /vectorstore/count, DELETE /documents/{id}/vectors
│   │       ├── search.py         ← POST /search  (retrieval without LLM)
│   │       └── chat.py           ← POST /chat    (full RAG + LLM response)
│   │
│   ├── core/              ← Config, logging, security (cross-cutting)
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── security.py    ← authenticated_request dependency (token + user headers)
│   │
│   ├── loaders/           ← Document ingestion: PDF, CSV, DOCX, TXT, XLSX
│   ├── chunking/          ← Text splitting: recursive character splitter
│   ├── embeddings/        ← Vector generation via provider (OpenAI / local)
│   ├── vectorstore/       ← ChromaDB client wrapper
│   ├── repositories/      ← VectorRepository (thin ChromaDB adapter)
│   ├── services/          ← VectorService (business logic over repository)
│   ├── retrieval/         ← RetrievalService, HybridRetriever, pipeline stages
│   │   ├── retrieval_service.py  ← orchestrates dense + hybrid + rerank + context
│   │   ├── hybrid_retriever.py   ← BM25 + dense RRF fusion (Increment 10)
│   │   └── retrieval_pipeline.py ← thin wrapper called by /chat and /search
│   ├── schemas/           ← Pydantic request/response models
│   ├── models/            ← Internal domain models (RetrievalResult, etc.)
│   ├── prompts/           ← Prompt templates for RAG and agents
│   ├── providers/         ← LLM provider wrappers: Anthropic, OpenAI, Ollama
│   ├── graph/             ← LangGraph StateGraph definition and workflow
│   └── agents/            ← Supervisor and domain agents: HR, Finance, IT
│
├── tests/
│   ├── conftest.py
│   ├── test_health.py
│   ├── versioning/
│   │   └── test_document_versioning.py   ← 17 tests: DELETE endpoint, idempotency
│   └── retrieval/
│       ├── test_hybrid_retriever.py      ← 20 tests: BM25, RRF, exact identifiers
│       └── test_secure_retrieval.py      ← 15 tests: department from header not body
│
├── scripts/
│   ├── e2e_versioning_test.py   ← end-to-end versioning validation (live stack)
│   └── performance_benchmark.py ← latency stats for all pipeline stages
│
├── Dockerfile
└── pyproject.toml
```

### Key Conventions

- All configuration is loaded through `core/config.py` using `pydantic-settings`. No configuration is hardcoded. Environment variables follow the prefix `AI_` (e.g., `AI_CHROMA_HOST`, `AI_ANTHROPIC_API_KEY`).
- Pydantic v2 models are used for all request/response schemas in `api/`. There are no untyped `dict` payloads.
- FastAPI's dependency injection (`Depends`) is used to provide the ChromaDB client, LLM provider, and compiled LangGraph workflow to route handlers.
- The `lifespan` context manager in `main.py` handles startup (initialise ChromaDB client, warm embedding model) and shutdown (flush connections) tasks.

---

## Internal Service Authentication

The AI service does not receive or validate user JWTs. It uses a separate internal service token mechanism to ensure that only the Node.js backend can call it.

### Why Not User JWTs

Passing user JWTs to the AI service would require the AI service to hold the RS256 public key and perform JWT validation on every request. This couples the AI service to the authentication infrastructure and creates a dependency that does not belong in an AI runtime.

### Service Token Pattern

At startup, the Node.js backend and the AI service share a symmetric secret (`INTERNAL_SERVICE_TOKEN`) injected via environment variable. The Node.js backend includes this token in every request to the AI service:

```
X-Internal-Token: <shared secret>
```

The FastAPI dependency `authenticated_request` validates this header and reads user identity forwarded by Node.js:

```
X-Internal-Token:   <shared secret>            (required — validated by HMAC compare_digest)
X-User-Id:          <userId from verified JWT>  (required)
X-User-Role:        <role from RBAC>            (required)
X-User-Department:  <department from JWT>       (optional — used for ChromaDB scoping)
```

For system-initiated calls (e.g., the Node backend deleting vectors on behalf of a supersede operation), the gateway passes a fixed service identity:

```
X-User-Id:    system
X-User-Role:  SYSTEM
```

---

## Data Ownership Boundary

A strict boundary separates what the Node.js backend owns from what the AI service owns:

| Concern | Owner | Storage |
|---|---|---|
| Users, roles, permissions | Node.js backend | PostgreSQL (Prisma) |
| Document metadata (filename, uploader, upload timestamp, version) | Node.js backend | PostgreSQL (Prisma) |
| Document version chain (parentDocumentId, SUPERSEDED status) | Node.js backend | PostgreSQL (Prisma) |
| Conversation metadata (session ID, timestamps) | Node.js backend | PostgreSQL (Prisma) |
| Document embeddings and chunk vectors | AI service | ChromaDB |
| Prompt templates | AI service | In-code (`prompts/`) |
| Conversation memory | AI service | In-memory (per session) |

The AI service trusts user identity forwarded by the Node.js backend and never stores or replicates user records. It does not maintain its own relational database.

---

## RAG Pipeline

The RAG pipeline transforms a user query into a grounded LLM response by retrieving relevant document chunks before calling the LLM. Each stage is orchestrated by `retrieval/retrieval_service.py`:

```
User Query
      │
      ▼
[1] QueryProcessor       ← normalise query text (strip whitespace, lowercase for BM25)
      │
      ▼
[2] EmbeddingService     ← embed the query (OpenAI text-embedding-3-small or local)
      │
      ▼
[3a] VectorRepository    ← ChromaDB .query(embedding, n=20, where={department})
      Dense rank list
      │
      │  (if use_hybrid=True, default)
      ▼
[3b] HybridRetriever     ← BM25 keyword search + RRF fusion (see section below)
      Fused rank list
      │
      ▼
[4] ScoreReranker        ← keep top_k by score, apply min_score filter
      │
      ▼
[5] ContextBuilder       ← assemble retrieved text within 6 000 token budget
      │
      ▼
[6] PromptBuilder        ← system prompt + department context + retrieved text + question
      │
      ▼
[7] LLM provider         ← Claude / GPT-4o / Ollama (chat completion)
      │
      ▼
Grounded response with citations
```

### Document Ingestion (Pre-RAG)

Before retrieval can occur, documents must be ingested:

1. Node.js backend stores the file and creates a Postgres `Document` record (status=`PENDING`).
2. `DocumentService._indexAsync()` fires asynchronously (non-blocking upload response).
3. `loaders/` selects the appropriate loader by MIME type and extracts raw text.
4. `chunking/` splits the text into overlapping segments (default: 400 tokens, 60 overlap).
5. `embeddings/` converts each chunk to a vector via the configured provider.
6. `vectorstore/` (via `VectorRepository`) upserts each embedding + metadata into ChromaDB.
7. Node.js updates the `Document` status to `INDEXED`.

---

## Hybrid Search (BM25 + Dense RRF)

**Problem:** Pure semantic (dense) vector search fails for exact identifiers. Querying `HR-204`, `TE-004`, `BUPA`, or `£150` produces semantically similar but keyword-mismatched results because these tokens have no embedding-space meaning.

**Solution:** BM25 keyword search is blended with dense search via Reciprocal Rank Fusion (RRF).

### Implementation

| Component | File |
|---|---|
| `HybridRetriever` class | `app/retrieval/hybrid_retriever.py` |
| Integration into pipeline | `app/retrieval/retrieval_service.py` — step 3b |
| Corpus fetch (text only) | `app/services/vector_service.py → get_all_text()` |
| `use_hybrid` request field | `app/schemas/search.py` |
| Dependency | `pyproject.toml` — `rank-bm25>=0.2.2` |

### RRF Formula

```
score[chunk_id] += 1 / (k + rank + 1)
```

where `k = 60` (standard smoothing constant). Applied independently to the dense rank list and the BM25 rank list; scores are summed and sorted descending.

### Graceful Degradation

If `rank_bm25` is not installed, or if the corpus is empty, `HybridRetriever` falls back to returning the original dense results unchanged. No exception is raised; a warning is logged.

### Performance Characteristics

At 1 000 chunks × ~100 words each:

- `get_all_text()` fetches ~100 KB of text (no embeddings fetched)
- BM25 index build: ~5–20 ms
- Total hybrid overhead vs dense-only: ~15–50 ms per query

---

## Document Versioning

When a user uploads a document with the same name to the same department, OptiAgent detects the duplicate and performs a version bump:

```
[1] DocumentService.upload() calls findLatestByNameAndDept(name, departmentId)
[2] Prior version found → increment version, set parentDocumentId = root of chain
[3] Fire-and-forget (does not block HTTP 201 response):
      repo.markSuperseded(existing.id)   → Postgres: status=SUPERSEDED, isLatest=false
      _deleteVectorsAsync(existing.id)   → DELETE /api/v1/documents/{id}/vectors
[4] Create new Document record (version=N, isLatest=true, status=PENDING)
[5] Return HTTP 201 immediately
[6] _indexAsync fires for new version (same pipeline as first upload)
```

### Vector Deletion Endpoint

```
DELETE /api/v1/documents/{document_id}/vectors
```

Called by the Node.js backend with system user context (`X-User-Id: system`, `X-User-Role: SYSTEM`). Removes all ChromaDB chunks whose `document_id` metadata matches. Returns `{"document_id": "...", "vectors_deleted": N}`. Safe to retry — returns `vectors_deleted: 0` if already deleted.

### Post-Versioning State

| id | originalName | version | isLatest | status | parentDocId |
|---|---|---|---|---|---|
| doc_v1 | Employee_Handbook.pdf | 1 | false | SUPERSEDED | null |
| doc_v2 | Employee_Handbook.pdf | 2 | true | INDEXED | doc_v1 |

ChromaDB retains only doc_v2 vectors. Searches cannot surface stale v1 content.

### Design Trade-offs

| Decision | Rationale |
|---|---|
| Fire-and-forget supersede | Upload response is immediate; deletion is asynchronous |
| `SUPERSEDED` ≠ `DELETED` | Keeps audit history; admin can query version chain |
| `parentDocumentId` chain | All versions in a chain point to v1 (the root) |
| Idempotent delete | Safe to retry if AI service was briefly unavailable |
| Known gap | Race condition on concurrent same-name uploads (production: distributed lock or unique constraint) |

---

## Secure Retrieval — Department Scoping

**Security contract:** The `department` filter applied to ChromaDB at query time **must** come from `ctx.department` — the `RequestContext` object populated from the `X-User-Department` header forwarded by Node.js from the verified JWT — **not** from `body.department` (client-controlled).

This prevents an HR user from querying Finance documents by sending `POST /search { "department": "Finance" }`.

### Implementation (`app/api/v1/search.py`)

```python
# SECURITY: department scope comes from the authenticated request context,
# not from the request body. Callers cannot override their own department scope.
config = RetrievalConfig(
    top_k_search=20,
    top_k_rerank=body.top_k,
    min_score=body.min_score,
    department=ctx.department,   # ← enforced from X-User-Department header
    document_id=body.document_id,
    section=body.section,
    use_hybrid=body.use_hybrid,
)
```

`body.department` field exists in the schema (it is forwarded from older clients) but is explicitly ignored for scoping. The `use_hybrid` flag is a feature flag (not a security concern) and is passed through from the body.

---

## LangGraph Supervisor Pattern

The LangGraph supervisor provides multi-agent routing. The architecture follows a supervisor/worker pattern: `graph/` owns the graph topology, `agents/` owns the node implementations.

```
User Query
    │
    ▼
┌──────────────────────┐
│   graph/workflow.py  │  Compiled LangGraph chain
└──────────────────────┘
    │
    ▼
┌──────────────────────┐
│  agents/supervisor   │  Classifies query intent, routes to specialist
└──────────────────────┘
    │           │           │
    ▼           ▼           ▼
┌────────┐ ┌─────────┐ ┌───────┐
│  HR    │ │ Finance │ │  IT   │
│ Agent  │ │  Agent  │ │ Agent │
└────────┘ └─────────┘ └───────┘
    │           │           │
    └───────────┴───────────┘
                │
          retrieval/retrieval_service.py (with hybrid search)
                │
           providers/ (LLM)
```

| Agent | Domain | Example Queries |
|---|---|---|
| HR Agent | HR policies, leave, onboarding | "What is policy HR-204?" |
| Finance Agent | Budget, expenses, procurement | "What is the approval limit for IT purchases?" |
| IT Agent | IT policies, access, software | "How do I request access to Salesforce?" |

---

## ChromaDB Vector Store

ChromaDB runs as a separate container (`chromadb:8200`) on the internal Docker network and is accessible only to the AI service. In development and tests, an in-memory client is used (`ChromaClient(mode="memory")`).

### Metadata Per Chunk

Each stored chunk carries the following metadata:

| Field | Type | Description |
|---|---|---|
| `document_id` | string | Identifier matching the Document record in Postgres |
| `chunk_index` | int | Position of this chunk within the document |
| `source_file` | string | Original filename |
| `department` | string | Owning department — used for access filtering at query time |
| `uploaded_by` | string | User ID forwarded from the Node.js backend |
| `uploaded_at` | ISO datetime | Ingestion timestamp |

Department filtering is applied at query time using ChromaDB's metadata `where` clause:

```python
where={"department": {"$eq": ctx.department}}
```

This ensures users only retrieve content they are authorised to see, even if they attempt to override their department via the request body.
