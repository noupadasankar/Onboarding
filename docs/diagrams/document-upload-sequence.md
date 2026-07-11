# Document Upload & Indexing Flow

OptiAgent — Document Upload, Storage, and Async Vector Indexing Sequence

---

## Overview

Document upload is a two-phase operation. Phase 1 is synchronous: the file is received, written to disk, and a DB record is created. The browser receives a 201 immediately. Phase 2 is asynchronous: the Node backend fires off an indexing job in the background — the AI service extracts text, chunks it, embeds each chunk, and upserts the vectors into ChromaDB. The frontend polls (or the user refreshes) to observe the status transition from PENDING → INDEXING → INDEXED.

---

## 1. Upload Phase — Synchronous (Client waits for this)

```
Browser (React)       Node Backend          PostgreSQL            Disk (uploads/)
      │                    │                    │                       │
      │  POST              │                    │                       │
      │  /api/v1/          │                    │                       │
      │  documents/upload  │                    │                       │
      │  Content-Type:     │                    │                       │
      │  multipart/form-   │                    │                       │
      │  data              │                    │                       │
      │  file: hr-policy-  │                    │                       │
      │   2024.pdf (5 MB)  │                    │                       │
      │  Authorization:    │                    │                       │
      │  Bearer <token>    │                    │                       │
      │───────────────────►│                    │                       │
      │                    │                    │                       │
      │                    │  ┌─────────────────▼──────────────────────────────────┐
      │                    │  │  [1] authenticate middleware                         │
      │                    │  │  Verify RS256 Bearer token.                         │
      │                    │  │  Populate req.auth { userId, email, permissions }.  │
      │                    │  └─────────────────┬──────────────────────────────────┘
      │                    │                    │                       │
      │                    │  ┌─────────────────▼──────────────────────────────────┐
      │                    │  │  [2] Multer middleware (memoryStorage)               │
      │                    │  │  Parse multipart/form-data in memory.               │
      │                    │  │  Validate:                                          │
      │                    │  │    - mimetype: application/pdf                      │
      │                    │  │    - size: ≤ 5 MB (fileSize limit enforced)         │
      │                    │  │  Reject with 400 if invalid type or oversized.      │
      │                    │  │  Set req.file = {                                   │
      │                    │  │    originalname, mimetype, size, buffer             │
      │                    │  │  }                                                  │
      │                    │  └─────────────────┬──────────────────────────────────┘
      │                    │                    │                       │
      │                    │  ┌─────────────────▼──────────────────────────────────┐
      │                    │  │  [3] DocumentService.upload()                        │
      │                    │  │                                                     │
      │                    │  │  a) Generate document ID and safe filename:         │
      │                    │  │       documentId = uuid()                           │
      │                    │  │       storedName = `${documentId}.pdf`              │
      │                    │  │       storedPath = uploads/${storedName}            │
      │                    │  │                                                     │
      │                    │  │  b) Write buffer to disk:                           │
      │                    │  │       fs.writeFileSync(storedPath, req.file.buffer) │
      │                    │  └─────────────────┬──────────────────────────────────┘
      │                    │                    │                       │
      │                    │                    │                       │  writeFileSync(
      │                    │                    │                       │  storedPath,
      │                    │                    │                       │  buffer)
      │                    │─────────────────────────────────────────── ────────────►│
      │                    │                    │                       │
      │                    │                    │                       │  OK (5 MB written)
      │                    │◄──────────────────────────────────────────────────────│
      │                    │                    │                       │
      │                    │  ┌─────────────────▼──────────────────────────────────┐
      │                    │  │  [3c] DocumentService.upload() — create DB record   │
      │                    │  │  INSERT Document {                                  │
      │                    │  │    id:           documentId,                        │
      │                    │  │    filename:     "hr-policy-2024.pdf",              │
      │                    │  │    storedPath:   "uploads/<id>.pdf",                │
      │                    │  │    mimeType:     "application/pdf",                 │
      │                    │  │    sizeBytes:    5242880,                           │
      │                    │  │    uploadedBy:   req.auth.userId,                   │
      │                    │  │    status:       "PENDING",                         │
      │                    │  │    chunkCount:   null,                              │
      │                    │  │    vectorCount:  null,                              │
      │                    │  │    createdAt:    NOW()                              │
      │                    │  │  }                                                  │
      │                    │  └─────────────────┬──────────────────────────────────┘
      │                    │                    │                       │
      │                    │  INSERT Document   │                       │
      │                    │  (status: PENDING) │                       │
      │                    │───────────────────►│                       │
      │                    │                    │                       │
      │                    │  { id, status,     │                       │
      │                    │    createdAt }     │                       │
      │                    │◄───────────────────│                       │
      │                    │                    │                       │
      │                    │  ┌─────────────────▼──────────────────────────────────┐
      │                    │  │  [4] Controller: return 201 immediately             │
      │                    │  │  DocumentService._indexAsync() is called with       │
      │                    │  │  setImmediate() — does NOT await.                  │
      │                    │  │                                                     │
      │                    │  │  res.status(201).json({                             │
      │                    │  │    success: true,                                   │
      │                    │  │    data: {                                          │
      │                    │  │      id:        documentId,                         │
      │                    │  │      filename:  "hr-policy-2024.pdf",               │
      │                    │  │      sizeBytes: 5242880,                            │
      │                    │  │      status:    "PENDING",                          │
      │                    │  │      createdAt: "2026-07-10T09:14:03.000Z"         │
      │                    │  │    }                                                │
      │                    │  │  })                                                 │
      │                    │  └─────────────────┬──────────────────────────────────┘
      │                    │                    │                       │
      │  HTTP 201          │                    │                       │
      │  { success: true,  │                    │                       │
      │    data: {         │                    │                       │
      │     id, filename,  │                    │                       │
      │     status:        │                    │                       │
      │     "PENDING",     │                    │                       │
      │     ...            │                    │                       │
      │    } }             │                    │                       │
      │◄───────────────────│                    │                       │
      │                    │                    │                       │
```

---

## 2. Indexing Phase — Asynchronous (Background, client does not wait)

```
Node Backend          PostgreSQL            FastAPI AI Service        ChromaDB
      │                    │                        │                     │
      │  [5] _indexAsync() │                        │                     │
      │  (setImmediate,    │                        │                     │
      │   fires after      │                        │                     │
      │   201 is sent)     │                        │                     │
      │                    │                        │                     │
      │  ┌─────────────────▼──────────────────────────────────────────┐  │
      │  │  [5] DocumentService._indexAsync()                          │  │
      │  │  UPDATE Document SET status = "INDEXING"                   │  │
      │  │  WHERE id = documentId                                      │  │
      │  └─────────────────┬──────────────────────────────────────────┘  │
      │                    │                        │                     │
      │  UPDATE status =   │                        │                     │
      │  "INDEXING"        │                        │                     │
      │───────────────────►│                        │                     │
      │                    │                        │                     │
      │  OK                │                        │                     │
      │◄───────────────────│                        │                     │
      │                    │                        │                     │
      │  ┌─────────────────▼──────────────────────────────────────────┐  │
      │  │  [6] AiGateway.indexDocument()                              │  │
      │  │  Build outbound request:                                   │  │
      │  │    POST http://ai-service:8100/api/v1/documents/index      │  │
      │  │  Headers:                                                  │  │
      │  │    X-Internal-Token: <shared-secret>                       │  │
      │  │    Content-Type: multipart/form-data                       │  │
      │  │  Body:                                                     │  │
      │  │    file:        <PDF binary re-read from storedPath>       │  │
      │  │    document_id: documentId                                 │  │
      │  │    filename:    "hr-policy-2024.pdf"                       │  │
      │  └─────────────────┬──────────────────────────────────────────┘  │
      │                    │                        │                     │
      │  POST              │                        │                     │
      │  /api/v1/documents │                        │                     │
      │  /index            │                        │                     │
      │  (X-Internal-Token │                        │                     │
      │   + PDF binary)    │                        │                     │
      │───────────────────────────────────────────►│                     │
      │                    │                        │                     │
      │                    │          ┌─────────────▼──────────────────────────────────┐
      │                    │          │  [7a] AI service: validate internal token       │
      │                    │          │  Compare X-Internal-Token against              │
      │                    │          │  INTERNAL_API_SECRET. Abort if mismatch.       │
      │                    │          └─────────────┬──────────────────────────────────┘
      │                    │                        │                     │
      │                    │          ┌─────────────▼──────────────────────────────────┐
      │                    │          │  [7b] AI service: extract text                  │
      │                    │          │  Use PyMuPDF (fitz) to open PDF buffer.        │
      │                    │          │  Iterate pages, extract plain text.            │
      │                    │          │  Result: raw_text (string, ~18 000 chars)      │
      │                    │          └─────────────┬──────────────────────────────────┘
      │                    │                        │                     │
      │                    │          ┌─────────────▼──────────────────────────────────┐
      │                    │          │  [7c] AI service: chunk text                    │
      │                    │          │  RecursiveCharacterTextSplitter:               │
      │                    │          │    chunk_size:    1 000 chars                  │
      │                    │          │    chunk_overlap: 200 chars                    │
      │                    │          │  Result: 24 chunks                             │
      │                    │          │  Each chunk tagged with metadata:              │
      │                    │          │    { document_id, filename, page, chunk_index }│
      │                    │          └─────────────┬──────────────────────────────────┘
      │                    │                        │                     │
      │                    │          ┌─────────────▼──────────────────────────────────┐
      │                    │          │  [7d] AI service: embed all chunks              │
      │                    │          │  Batch call OpenAI embeddings API:             │
      │                    │          │    POST /v1/embeddings                         │
      │                    │          │    model: text-embedding-3-small               │
      │                    │          │    input: [ chunk_0, chunk_1, ..., chunk_23 ]  │
      │                    │          │  Returns 24 × 1 536-dimension vectors.         │
      │                    │          └─────────────┬──────────────────────────────────┘
      │                    │                        │                     │
      │                    │          ┌─────────────▼──────────────────────────────────┐
      │                    │          │  [7e] AI service: upsert to ChromaDB            │
      │                    │          │  collection.upsert(                            │
      │                    │          │    ids:         [ "doc_id__chunk_0", ... ],    │
      │                    │          │    embeddings:  [ vec_0, ..., vec_23 ],        │
      │                    │          │    documents:   [ chunk_0, ..., chunk_23 ],    │
      │                    │          │    metadatas:   [ meta_0, ..., meta_23 ]       │
      │                    │          │  )                                             │
      │                    │          └─────────────┬──────────────────────────────────┘
      │                    │                        │                     │
      │                    │                        │  collection.upsert( │
      │                    │                        │   ids, embeddings,  │
      │                    │                        │   documents,        │
      │                    │                        │   metadatas)        │
      │                    │                        │────────────────────►│
      │                    │                        │                     │
      │                    │                        │  OK (24 vectors     │
      │                    │                        │   persisted)        │
      │                    │                        │◄────────────────────│
      │                    │                        │                     │
      │                    │          ┌─────────────▼──────────────────────────────────┐
      │                    │          │  [8] AI service: build IndexResponse            │
      │                    │          │  {                                             │
      │                    │          │    document_id:  "doc_abc123",                 │
      │                    │          │    chunk_count:  24,                           │
      │                    │          │    vector_count: 24                            │
      │                    │          │  }                                             │
      │                    │          └─────────────┬──────────────────────────────────┘
      │                    │                        │                     │
      │  HTTP 200          │                        │                     │
      │  { document_id,    │                        │                     │
      │    chunk_count: 24,│                        │                     │
      │    vector_count:24}│                        │                     │
      │◄───────────────────────────────────────────│                     │
      │                    │                        │                     │
      │  ┌─────────────────▼──────────────────────────────────────────┐  │
      │  │  [9] DocumentService: set status to INDEXED                 │  │
      │  │  UPDATE Document SET                                        │  │
      │  │    status =      "INDEXED",                                 │  │
      │  │    chunkCount =  24,                                        │  │
      │  │    vectorCount = 24,                                        │  │
      │  │    indexedAt =   NOW()                                      │  │
      │  │  WHERE id = documentId                                      │  │
      │  └─────────────────┬──────────────────────────────────────────┘  │
      │                    │                        │                     │
      │  UPDATE status =   │                        │                     │
      │  "INDEXED",        │                        │                     │
      │  chunkCount = 24   │                        │                     │
      │───────────────────►│                        │                     │
      │                    │                        │                     │
      │  OK                │                        │                     │
      │◄───────────────────│                        │                     │
      │                    │                        │                     │
```

---

## 3. Frontend Status Polling

After receiving the initial 201, the browser polls the document status endpoint until the document reaches INDEXED (or FAILED):

```
Browser (React)       Node Backend          PostgreSQL
      │                    │                    │
      │  [10] Poll loop:   │                    │
      │  every 3 seconds   │                    │
      │                    │                    │
      │  GET               │                    │
      │  /api/v1/documents │                    │
      │  /:id              │                    │
      │  Authorization:    │                    │
      │  Bearer <token>    │                    │
      │───────────────────►│                    │
      │                    │  SELECT * FROM     │
      │                    │  Document          │
      │                    │  WHERE id = :id    │
      │                    │───────────────────►│
      │                    │                    │
      │                    │  { id, status:     │
      │                    │    "INDEXING",     │
      │                    │    ... }           │
      │                    │◄───────────────────│
      │                    │                    │
      │  HTTP 200          │                    │
      │  { data: { id,     │                    │
      │    status:         │                    │
      │    "INDEXING" } }  │                    │
      │◄───────────────────│                    │
      │                    │                    │
      │  (still INDEXING — │                    │
      │   wait 3s, poll    │                    │
      │   again)           │                    │
      │                    │                    │
      │  GET               │                    │
      │  /api/v1/documents │                    │
      │  /:id              │                    │
      │───────────────────►│───────────────────►│
      │                    │                    │
      │                    │  { id, status:     │
      │                    │    "INDEXED",      │
      │                    │    chunkCount: 24, │
      │                    │    vectorCount: 24,│
      │                    │    indexedAt: ...} │
      │                    │◄───────────────────│
      │                    │                    │
      │  HTTP 200          │                    │
      │  { data: { id,     │                    │
      │    status:         │                    │
      │    "INDEXED",      │                    │
      │    chunkCount: 24, │                    │
      │    ... } }         │                    │
      │◄───────────────────│                    │
      │                    │                    │
      │  [UI updates badge │                    │
      │   from "Indexing"  │                    │
      │   to "Ready".      │                    │
      │   Polling stops.]  │                    │
      │                    │                    │
```

---

## 4. Error Path — Indexing Failure

If the AI service fails during indexing (e.g., PDF is corrupt or OpenAI embeddings call fails), the document is marked FAILED:

```
Node Backend          FastAPI AI Service        PostgreSQL
      │                        │                    │
      │  [6] POST              │                    │
      │  /api/v1/documents     │                    │
      │  /index (PDF binary)   │                    │
      │───────────────────────►│                    │
      │                        │                    │
      │                    ┌───▼────────────────────────────────────────┐
      │                    │  [7b] PyMuPDF raises exception:             │
      │                    │  "cannot open broken document"             │
      │                    │  (or OpenAI embeddings returns 429/500)    │
      │                    │  AI service returns HTTP 422 or 502.       │
      │                    └───┬────────────────────────────────────────┘
      │                        │                    │
      │  HTTP 422 / 502        │                    │
      │◄───────────────────────│                    │
      │                        │                    │
      │  ┌─────────────────────▼──────────────────────────────────────┐
      │  │  DocumentService._indexAsync() catches error.               │
      │  │  UPDATE Document SET                                        │
      │  │    status =   "FAILED",                                     │
      │  │    errorMsg = "PDF extraction failed: broken document"      │
      │  │  WHERE id = documentId                                      │
      │  └─────────────────────┬──────────────────────────────────────┘
      │                        │                    │
      │  UPDATE status =       │                    │
      │  "FAILED"              │                    │
      │──────────────────────────────────────────── ►│
      │                        │                    │
      │  OK                    │                    │
      │◄────────────────────────────────────────────│
      │                        │                    │
      │  (Browser polls next   │                    │
      │   interval, sees       │                    │
      │   status: "FAILED".    │                    │
      │   UI shows error       │                    │
      │   badge + message.)    │                    │
```
