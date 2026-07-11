# AI Query API

OptiAgent REST API — `/api/v1/ai`

---

> **Status: Not yet implemented.**
> This API is planned for **Increment 7** (RAG Pipeline). The endpoint, schemas, and behaviors described below represent the intended design and are subject to change during implementation. The LangGraph supervisor and specialist agents are planned for **Increment 8 and 9**.

---

## Overview

The AI query endpoint allows authenticated users to submit natural-language questions. The Node.js backend forwards the request to the Python AI service, which runs the RAG pipeline, routes the query to the appropriate specialist agent (HR, Finance, or IT), and calls Claude to generate a grounded response.

All AI responses are grounded in documents that have been ingested and indexed in ChromaDB. The system does not answer questions from general LLM knowledge — if no relevant documents are found, the response will indicate that no matching content is available.

---

## Planned Schemas

### QueryRequest

```typescript
{
  query:      string;   // The user's natural-language question (max 2000 chars)
  department?: string;  // Optional: explicitly route to HR | Finance | IT
                        // If omitted, the supervisor classifies automatically
}
```

### QueryResponse

```typescript
{
  answer:     string;           // The LLM-generated response
  sources:    SourceChunk[];    // Document chunks used as context
  agent:      string;           // Which specialist agent handled the query
  tokenUsage: {
    inputTokens:  number;
    outputTokens: number;
  };
  latencyMs:  number;           // Total time from query to response
}
```

### SourceChunk

```typescript
{
  documentId:   string;   // Source document ID
  fileName:     string;   // Original filename
  chunkIndex:   number;   // Position within the document
  excerpt:      string;   // The text of the retrieved chunk
  score:        number;   // Cosine similarity score (0.0 – 1.0)
}
```

---

## Planned Endpoints

---

### POST /api/v1/ai/query

Submits a natural-language query and returns a RAG-grounded LLM response.

**Authentication required:** Yes
**Permission required:** `ai:query` (planned)

**Request body:** `QueryRequest`

```json
{
  "query":      "What is the company's policy on remote work?",
  "department": "HR"
}
```

**Response:** `ApiResponse<QueryResponse>` — HTTP 200

```json
{
  "success": true,
  "data": {
    "answer": "According to the Employee Handbook (updated January 2026), employees may work remotely up to 3 days per week with manager approval. Full remote arrangements require VP-level sign-off...",
    "sources": [
      {
        "documentId": "doc_01HZ...",
        "fileName":   "employee-handbook-2026.pdf",
        "chunkIndex": 42,
        "excerpt":    "Remote work is permitted up to 3 days per week...",
        "score":      0.91
      }
    ],
    "agent":      "HR",
    "tokenUsage": {
      "inputTokens":  1240,
      "outputTokens":  318
    },
    "latencyMs": 2340
  }
}
```

**Planned error responses:**

| HTTP | Code | Condition |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Query too long or request body invalid |
| 401 | `INVALID_TOKEN` | Missing or expired token |
| 403 | `PERMISSION_DENIED` | Caller does not hold `ai:query` |
| 503 | `AI_SERVICE_UNAVAILABLE` | Python AI service did not respond |
| 504 | `AI_SERVICE_TIMEOUT` | Python AI service exceeded the timeout threshold |

---

## Implementation Notes

When Increment 7 begins, the following design decisions will need to be confirmed:

- **Streaming vs. blocking response:** The initial implementation will use a blocking request/response pattern. Streaming (SSE or WebSocket) may be added if LLM latency is unacceptable for the user experience.
- **Timeout:** A 30-second timeout is proposed for the Node.js → AI service call. This will be tuned based on observed LLM latency.
- **No-document fallback:** If ChromaDB returns no chunks above the similarity threshold, the system should return a clear "no relevant documents found" response rather than hallucinating an answer from LLM training data.
- **Audit logging:** Each AI query will be audit-logged with `action: "AI_QUERY"`, the query text, and the responding agent. This allows administrators to review AI usage.
- **Rate limiting:** Per-user rate limiting on this endpoint is anticipated. The limit (e.g., 60 requests/hour) will be enforced at the Node.js layer using a Redis counter.
- **Department routing:** If `department` is omitted, the LangGraph supervisor classifies the query intent using the query text and the user's department context from their JWT. Explicit department selection will be available in the UI for cases where the user knows the routing target.
