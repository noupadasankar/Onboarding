# Document Versioning — Full Sequence

OptiAgent — How v2 supersedes v1 across Postgres + ChromaDB

---

## Overview

When the same document name is re-uploaded to the same department, OptiAgent
detects the duplicate, increments the version number, marks the previous
version as SUPERSEDED (invisible to all document lists and searches), and
deletes its stale vectors from ChromaDB — ensuring users always retrieve
answers grounded only in the latest version.

---

## 1. Happy Path — First Upload (v1, no prior version)

```
Browser (React)       Node Backend          PostgreSQL            AI Service        ChromaDB
      │                    │                    │                     │                │
      │  POST              │                    │                     │                │
      │  /api/v1/          │                    │                     │                │
      │  documents/upload  │                    │                     │                │
      │  file:             │                    │                     │                │
      │  Employee_          │                   │                     │                │
      │  Handbook.pdf      │                    │                     │                │
      │───────────────────►│                    │                     │                │
      │                    │                    │                     │                │
      │                    │  ┌─────────────────▼───────────────────────────────────┐ │
      │                    │  │  [1] authenticate + authorize                        │ │
      │                    │  └─────────────────┬───────────────────────────────────┘ │
      │                    │                    │                     │                │
      │                    │  ┌─────────────────▼───────────────────────────────────┐ │
      │                    │  │  [2] DocumentService.upload()                        │ │
      │                    │  │  findLatestByNameAndDept(                            │ │
      │                    │  │    originalName = "Employee_Handbook.pdf",           │ │
      │                    │  │    departmentId = null                               │ │
      │                    │  │  )                                                   │ │
      │                    │  └─────────────────┬───────────────────────────────────┘ │
      │                    │                    │                     │                │
      │                    │  SELECT Document   │                     │                │
      │                    │  WHERE originalName│                     │                │
      │                    │  = 'handbook.pdf'  │                     │                │
      │                    │  AND isLatest=true │                     │                │
      │                    │───────────────────►│                     │                │
      │                    │                    │                     │                │
      │                    │  { null }          │                     │                │
      │                    │  (no prior version)│                     │                │
      │                    │◄───────────────────│                     │                │
      │                    │                    │                     │                │
      │                    │  ┌─────────────────▼───────────────────────────────────┐ │
      │                    │  │  [3] version = 1, parentDocumentId = null           │ │
      │                    │  │  repo.create({                                      │ │
      │                    │  │    originalName: "Employee_Handbook.pdf",            │ │
      │                    │  │    version: 1,                                       │ │
      │                    │  │    isLatest: true,                                   │ │
      │                    │  │    parentDocumentId: null,                           │ │
      │                    │  │    status: "PENDING"                                 │ │
      │                    │  │  })                                                  │ │
      │                    │  └─────────────────┬───────────────────────────────────┘ │
      │                    │                    │                     │                │
      │                    │  INSERT Document   │                     │                │
      │                    │  (v1, PENDING)     │                     │                │
      │                    │───────────────────►│                     │                │
      │                    │  { id: doc_v1 }    │                     │                │
      │                    │◄───────────────────│                     │                │
      │                    │                    │                     │                │
      │  HTTP 201          │                    │                     │                │
      │  { id: doc_v1,     │                    │                     │                │
      │    version: 1,     │                    │                     │                │
      │    status: PENDING }                    │                     │                │
      │◄───────────────────│                    │                     │                │
      │                    │                    │                     │                │
      │                    │  ┌─────────────────▼──────────────────────────────────┐  │
      │                    │  │  [4] _indexAsync() fires (setImmediate, async)      │  │
      │                    │  │  UPDATE doc_v1 SET status = "INDEXING"              │  │
      │                    │  │  POST /api/v1/documents/index → AI Service          │  │
      │                    │  └─────────────────┬──────────────────────────────────┘  │
      │                    │                    │                     │                │
      │                    │                    │  POST /documents/   │                │
      │                    │                    │  doc_v1/index       │                │
      │                    │                    │  (chunk+embed)      │                │
      │                    │────────────────────────────────────────►│                │
      │                    │                    │                     │                │
      │                    │                    │                     │  upsert(       │
      │                    │                    │                     │   doc_v1       │
      │                    │                    │                     │   vectors)     │
      │                    │                    │                     │──────────────►│
      │                    │                    │                     │  OK            │
      │                    │                    │                     │◄──────────────│
      │                    │                    │                     │                │
      │                    │                    │  { chunk_count: 24 }│                │
      │                    │◄───────────────────────────────────────│                │
      │                    │                    │                     │                │
      │                    │  UPDATE doc_v1     │                     │                │
      │                    │  SET status=INDEXED│                     │                │
      │                    │───────────────────►│                     │                │
```

---

## 2. Version Re-upload — v2 supersedes v1

```
Browser (React)       Node Backend          PostgreSQL            AI Service        ChromaDB
      │                    │                    │                     │                │
      │  POST /upload      │                    │                     │                │
      │  Employee_Handbook │                    │                     │                │
      │  .pdf (v2 content) │                    │                     │                │
      │───────────────────►│                    │                     │                │
      │                    │                    │                     │                │
      │                    │  ┌─────────────────▼───────────────────────────────────┐ │
      │                    │  │  [1] findLatestByNameAndDept(                        │ │
      │                    │  │    "Employee_Handbook.pdf", null)                    │ │
      │                    │  └─────────────────┬───────────────────────────────────┘ │
      │                    │                    │                     │                │
      │                    │  SELECT Document   │                     │                │
      │                    │  WHERE originalName│                     │                │
      │                    │  = 'handbook.pdf'  │                     │                │
      │                    │  AND isLatest=true │                     │                │
      │                    │───────────────────►│                     │                │
      │                    │                    │                     │                │
      │                    │  { id: doc_v1,     │                     │                │
      │                    │    version: 1,     │                     │                │
      │                    │    status: INDEXED }                    │                │
      │                    │◄───────────────────│                     │                │
      │                    │                    │                     │                │
      │                    │  ┌─────────────────▼───────────────────────────────────┐ │
      │                    │  │  [2] Prior version found → version bump              │ │
      │                    │  │    new_version         = 2                           │ │
      │                    │  │    parentDocumentId    = doc_v1 (root of chain)      │ │
      │                    │  │                                                      │ │
      │                    │  │  [3] Fire-and-forget (do NOT await):                 │ │
      │                    │  │    repo.markSuperseded(doc_v1.id)  ──── (3a)         │ │
      │                    │  │    _deleteVectorsAsync(doc_v1.id)  ──── (3b)         │ │
      │                    │  │                                                      │ │
      │                    │  │  [4] Create v2 record (blocks HTTP response)         │ │
      │                    │  │    repo.create({ version: 2, isLatest: true,         │ │
      │                    │  │                 parentDocumentId: doc_v1 })          │ │
      │                    │  └─────────────────┬───────────────────────────────────┘ │
      │                    │                    │                     │                │
      │                    │  ┌ ─ ─ ─ ─ ─ ─ ─ ─▼─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐   │
      │                    │     (3a) markSuperseded — fire-and-forget             │   │
      │                    │  └ ─ ─ ─ ─ ─ ─ ─ ─┬─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘   │
      │                    │                    │                     │                │
      │                    │  UPDATE doc_v1     │                     │                │
      │                    │  SET status        │                     │                │
      │                    │  = SUPERSEDED,     │                     │                │
      │                    │  isLatest = false, │                     │                │
      │                    │  supersededAt = NOW│                     │                │
      │                    │───────────────────►│                     │                │
      │                    │                    │                     │                │
      │                    │  ┌ ─ ─ ─ ─ ─ ─ ─ ─▼─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐   │
      │                    │     (3b) _deleteVectorsAsync — fire-and-forget        │   │
      │                    │  └ ─ ─ ─ ─ ─ ─ ─ ─┬─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘   │
      │                    │                    │                     │                │
      │                    │                    │  DELETE /documents/ │                │
      │                    │                    │  doc_v1/vectors     │                │
      │                    │────────────────────────────────────────►│                │
      │                    │                    │                     │                │
      │                    │                    │                     │  collection.   │
      │                    │                    │                     │  delete(       │
      │                    │                    │                     │   where: {     │
      │                    │                    │                     │    doc_id:     │
      │                    │                    │                     │    doc_v1})    │
      │                    │                    │                     │──────────────►│
      │                    │                    │                     │               │
      │                    │                    │                     │  24 deleted   │
      │                    │                    │                     │◄──────────────│
      │                    │                    │                     │                │
      │                    │                    │  { vectors_deleted: 24 }            │
      │                    │◄───────────────────────────────────────│                │
      │                    │                    │                     │                │
      │                    │  INSERT doc_v2     │                     │                │
      │                    │  (version: 2,      │                     │                │
      │                    │   isLatest: true,  │                     │                │
      │                    │   parent: doc_v1)  │                     │                │
      │                    │───────────────────►│                     │                │
      │                    │  { id: doc_v2 }    │                     │                │
      │                    │◄───────────────────│                     │                │
      │                    │                    │                     │                │
      │  HTTP 201          │                    │                     │                │
      │  { id: doc_v2,     │                    │                     │                │
      │    version: 2,     │                    │                     │                │
      │    status: PENDING }                    │                     │                │
      │◄───────────────────│                    │                     │                │
      │                    │                    │                     │                │
      │                    │  [4] _indexAsync() fires for doc_v2                      │
      │                    │  (same flow as Phase 1 indexing above)                   │
      │                    │                    │                     │                │
      │                    │                    │  POST /documents/   │                │
      │                    │                    │  doc_v2/index       │                │
      │                    │────────────────────────────────────────►│                │
      │                    │                    │                     │  upsert(       │
      │                    │                    │                     │   doc_v2       │
      │                    │                    │                     │   vectors)     │
      │                    │                    │                     │──────────────►│
      │                    │                    │                     │  OK            │
      │                    │                    │                     │◄──────────────│
      │                    │  UPDATE doc_v2     │                     │                │
      │                    │  SET status=INDEXED│                     │                │
      │                    │───────────────────►│                     │                │
```

---

## 3. Post-versioning State

```
PostgreSQL — Document table
┌──────────┬───────────────────────┬─────────┬─────────┬────────────────────┬───────────────┐
│ id       │ originalName          │ version │isLatest │ status             │parentDocId    │
├──────────┼───────────────────────┼─────────┼─────────┼────────────────────┼───────────────┤
│ doc_v1   │ Employee_Handbook.pdf │    1    │  false  │ SUPERSEDED         │ null          │
│ doc_v2   │ Employee_Handbook.pdf │    2    │  true   │ INDEXED            │ doc_v1        │
└──────────┴───────────────────────┴─────────┴─────────┴────────────────────┴───────────────┘

ChromaDB — Vector collection
┌──────────────────┬───────────────┐
│ document_id      │ chunk count   │
├──────────────────┼───────────────┤
│ doc_v2           │ 24 vectors    │  ← v2 content only
│ (doc_v1 deleted) │               │  ← no stale v1 chunks
└──────────────────┴───────────────┘

Document List API (default view — isLatest=true, status NOT IN [SUPERSEDED, DELETED])
  → Shows only doc_v2 (version 2, INDEXED)
  → doc_v1 is invisible without explicit status filter

Search / RAG
  → All retrieved chunks belong to doc_v2
  → "25 days annual leave" (v2) is the answer
  → "20 days" (v1) cannot appear — its vectors are deleted
```

---

## 4. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Fire-and-forget supersede + vector delete | Upload response is immediate (201 in ~50ms); deletion happens asynchronously |
| SUPERSEDED != DELETED | SUPERSEDED keeps audit history; DELETED is for explicit removals |
| `isLatest: false` on supersede | Document list filter (`isLatest: true`) hides old versions automatically |
| `parentDocumentId` chain | Enables version history view (Admin Dashboard roadmap item) |
| Vector deletion before v2 indexing | Brief window where old chunks may appear; acceptable because governance layer still grounds answers in documents |
| Idempotent DELETE endpoint | Safe to retry; returns `{vectors_deleted: 0}` if already deleted |
