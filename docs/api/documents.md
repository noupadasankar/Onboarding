# Documents API

OptiAgent REST API — `/api/v1/documents`

---

> **Status: Not yet implemented.**
> This API is planned for **Increment 3** (Document Upload). The endpoints, schemas, and behaviors described below represent the intended design and are subject to change during implementation.

---

## Overview

The documents endpoints will allow authenticated users to upload, list, and delete documents for AI-powered retrieval. Uploaded documents are ingested by the Python AI service (chunked, embedded, and stored in ChromaDB) to enable RAG-based queries.

Supported file types: PDF, CSV, DOCX, TXT.

---

## Planned Schemas

### DocumentDTO

```typescript
{
  id:           string;
  fileName:     string;
  fileType:     'pdf' | 'csv' | 'docx' | 'txt';
  sizeBytes:    number;
  uploadedBy:   string;   // User ID
  department:   string;   // Owning department (for access filtering)
  status:       'pending' | 'processing' | 'ready' | 'error';
  errorMessage: string | null;
  createdAt:    string;   // ISO 8601
  updatedAt:    string;   // ISO 8601
}
```

### UploadDocumentRequest

Submitted as `multipart/form-data`:

| Field | Type | Description |
|---|---|---|
| `file` | File | The document file (PDF, CSV, DOCX, or TXT) |
| `department` | string | Department this document belongs to (HR, Finance, IT) |
| `displayName` | string (optional) | Human-readable name; defaults to filename |

---

## Planned Endpoints

---

### POST /api/v1/documents

Uploads a new document and initiates background ingestion.

**Authentication required:** Yes
**Permission required:** `documents:write` (planned)
**Content-Type:** `multipart/form-data`

**Request:** multipart form with `file` and `department` fields.

**Response:** `ApiResponse<DocumentDTO>` — HTTP 202 Accepted

The document record is created immediately with `status: "pending"`. Ingestion (chunking, embedding, ChromaDB storage) occurs asynchronously. Callers should poll `GET /documents/:id` or use a websocket notification to detect when `status` becomes `"ready"`.

**Planned error responses:**

| HTTP | Code | Condition |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Missing required fields or unsupported file type |
| 400 | `FILE_TOO_LARGE` | File exceeds the size limit (planned: 50 MB) |
| 401 | `INVALID_TOKEN` | Missing or expired token |
| 403 | `PERMISSION_DENIED` | Caller does not hold `documents:write` |

---

### GET /api/v1/documents

Returns a paginated list of documents accessible to the caller.

**Authentication required:** Yes
**Permission required:** `documents:read` (planned)

**Planned query parameters:**

| Parameter | Type | Description |
|---|---|---|
| `page` | number | Page number (1-indexed) |
| `pageSize` | number | Items per page |
| `department` | string | Filter by department |
| `status` | string | Filter by ingestion status |
| `search` | string | Partial match on `fileName` or `displayName` |

**Response:** `ApiResponse<PaginatedResponse<DocumentDTO>>` — HTTP 200

---

### GET /api/v1/documents/:id

Returns a single document record by ID.

**Authentication required:** Yes
**Permission required:** `documents:read` (planned)

**Response:** `ApiResponse<DocumentDTO>` — HTTP 200

**Planned error responses:**

| HTTP | Code | Condition |
|---|---|---|
| 404 | `DOCUMENT_NOT_FOUND` | No document with the given ID |

---

### DELETE /api/v1/documents/:id

Deletes a document and removes its chunks from ChromaDB.

**Authentication required:** Yes
**Permission required:** `documents:delete` (planned)

**Response:** `ApiResponse<{ deleted: true }>` — HTTP 200

Deletion is permanent. The document record and all associated vector embeddings are removed.

**Planned error responses:**

| HTTP | Code | Condition |
|---|---|---|
| 404 | `DOCUMENT_NOT_FOUND` | No document with the given ID |

---

## Implementation Notes

When Increment 3 begins, the following design decisions will need to be confirmed:

- **File size limit:** 50 MB is the current proposal. Will be validated by the team.
- **Ingestion async strategy:** Background processing will likely use a Redis-backed job queue (Bull/BullMQ for Node.js). The Node.js backend enqueues the job after receiving the upload; the Python AI service is the worker.
- **Access control:** Whether document visibility is based on the uploading user's department or an explicit `department` field on the document. The current schema assumes an explicit field.
- **Status polling vs. push notifications:** The initial implementation will use status polling. WebSocket push may be added in a later increment.
