# RAG Chat Flow — Full AI Pipeline Sequence

OptiAgent — End-to-End RAG Chat Request Lifecycle

---

## Scenario

User asks: **"How many annual leave days do employees receive?"**

Participants: Browser (React) | Node Backend | FastAPI AI Service | ChromaDB | OpenAI

---

## 1. Happy Path — Full RAG Pipeline

```
Browser (React)       Node Backend          FastAPI AI Service        ChromaDB          OpenAI
      │                    │                        │                     │                │
      │  POST              │                        │                     │                │
      │  /api/v1/          │                        │                     │                │
      │  conversations/    │                        │                     │                │
      │  chat              │                        │                     │                │
      │  {                 │                        │                     │                │
      │   question:        │                        │                     │                │
      │   "How many        │                        │                     │                │
      │   annual leave     │                        │                     │                │
      │   days...",        │                        │                     │                │
      │   conversationId?  │                        │                     │                │
      │  }                 │                        │                     │                │
      │───────────────────►│                        │                     │                │
      │                    │                        │                     │                │
      │                    │  ┌─────────────────────▼──────────────────────────────────┐  │
      │                    │  │  [1] authenticate middleware                            │  │
      │                    │  │  Extract Bearer token, verify RS256 signature.         │  │
      │                    │  │  Check exp claim. Populate req.auth:                   │  │
      │                    │  │    { userId, email, permissions }                      │  │
      │                    │  └─────────────────────┬──────────────────────────────────┘  │
      │                    │                        │                     │                │
      │                    │  ┌─────────────────────▼──────────────────────────────────┐  │
      │                    │  │  [2] authorize middleware                               │  │
      │                    │  │  Check req.auth.permissions includes "HR_QUERY".       │  │
      │                    │  │  Throw ForbiddenError if not.                          │  │
      │                    │  └─────────────────────┬──────────────────────────────────┘  │
      │                    │                        │                     │                │
      │                    │  ┌─────────────────────▼──────────────────────────────────┐  │
      │                    │  │  [3] ConversationService.chat()                         │  │
      │                    │  │  - If conversationId provided: load existing            │  │
      │                    │  │    Conversation from DB, retrieve message history.      │  │
      │                    │  │  - If no conversationId: create new Conversation        │  │
      │                    │  │    record (status: ACTIVE).                             │  │
      │                    │  │  - Persist user Message to DB:                         │  │
      │                    │  │      { role: "user", content: question,                │  │
      │                    │  │        conversationId, createdAt }                     │  │
      │                    │  └─────────────────────┬──────────────────────────────────┘  │
      │                    │                        │                     │                │
      │                    │  ┌─────────────────────▼──────────────────────────────────┐  │
      │                    │  │  [4] AiGateway.chat()                                   │  │
      │                    │  │  Build outbound request:                               │  │
      │                    │  │    POST http://ai-service:8100/api/v1/chat             │  │
      │                    │  │  Headers:                                              │  │
      │                    │  │    X-Internal-Token: <shared-secret>                   │  │
      │                    │  │    X-User-Id: req.auth.userId                          │  │
      │                    │  │    X-User-Email: req.auth.email                        │  │
      │                    │  │    X-User-Permissions: HR_QUERY,...                    │  │
      │                    │  │  Body: { question, conversationId,                     │  │
      │                    │  │          history: [{ role, content }] }               │  │
      │                    │  └─────────────────────┬──────────────────────────────────┘  │
      │                    │                        │                     │                │
      │                    │  POST                  │                     │                │
      │                    │  http://ai-service:8100│                     │                │
      │                    │  /api/v1/chat          │                     │                │
      │                    │  (X-Internal-Token,    │                     │                │
      │                    │   X-User-* headers)    │                     │                │
      │                    │───────────────────────►│                     │                │
      │                    │                        │                     │                │
      │                    │          ┌─────────────▼──────────────────────────────────┐  │
      │                    │          │  [5] AI service: validate internal token        │  │
      │                    │          │  Compare X-Internal-Token against              │  │
      │                    │          │  INTERNAL_API_SECRET env var (constant-time).  │  │
      │                    │          │  Extract user context from X-User-* headers:   │  │
      │                    │          │    userId, email, permissions list.            │  │
      │                    │          │  Abort with 401 if token mismatch.            │  │
      │                    │          └─────────────┬──────────────────────────────────┘  │
      │                    │                        │                     │                │
      │                    │          ┌─────────────▼──────────────────────────────────┐  │
      │                    │          │  [6] LangGraph Supervisor                       │  │
      │                    │          │  Inspect question + user permissions.          │  │
      │                    │          │  Route decision:                               │  │
      │                    │          │    "annual leave days" → HR domain             │  │
      │                    │          │    → select HR Agent node.                     │  │
      │                    │          └─────────────┬──────────────────────────────────┘  │
      │                    │                        │                     │                │
      │                    │          ┌─────────────▼──────────────────────────────────┐  │
      │                    │          │  [7] HR Agent: embed question                   │  │
      │                    │          │  Call OpenAI embeddings API:                   │  │
      │                    │          │    model: text-embedding-3-small               │  │
      │                    │          │    input: "How many annual leave days..."       │  │
      │                    │          └─────────────┬──────────────────────────────────┘  │
      │                    │                        │                     │                │
      │                    │                        │  POST               │                │
      │                    │                        │  /v1/embeddings     │                │
      │                    │                        │  (text-embedding-   │                │
      │                    │                        │   3-small)          │                │
      │                    │                        │────────────────────────────────────► │
      │                    │                        │                     │                │
      │                    │                        │  { embedding:       │                │
      │                    │                        │    [1536-dim vec] } │                │
      │                    │                        │◄────────────────────────────────────│
      │                    │                        │                     │                │
      │                    │          ┌─────────────▼──────────────────────────────────┐  │
      │                    │          │  [8] HR Agent: query ChromaDB                   │  │
      │                    │          │  collection: "hr_documents"                    │  │
      │                    │          │  query_embeddings: [1536-dim vector]           │  │
      │                    │          │  n_results: 5  (top_k=5)                       │  │
      │                    │          │  include: ["documents","metadatas","distances"] │  │
      │                    │          └─────────────┬──────────────────────────────────┘  │
      │                    │                        │                     │                │
      │                    │                        │  query(             │                │
      │                    │                        │   embeddings,       │                │
      │                    │                        │   n_results=5)      │                │
      │                    │                        │────────────────────►│                │
      │                    │                        │                     │                │
      │                    │                        │  ┌──────────────────▼─────────────┐ │
      │                    │                        │  │  [9] ChromaDB semantic search   │ │
      │                    │                        │  │  Cosine similarity against      │ │
      │                    │                        │  │  indexed HR document vectors.   │ │
      │                    │                        │  │  Return top 5 chunks:           │ │
      │                    │                        │  │  [                              │ │
      │                    │                        │  │   { document: "Employees        │ │
      │                    │                        │  │     receive 20 days annual...", │ │
      │                    │                        │  │     metadata: { source:         │ │
      │                    │                        │  │      "hr-policy-2024.pdf",      │ │
      │                    │                        │  │      page: 4, chunk: 12 },      │ │
      │                    │                        │  │     distance: 0.08 },           │ │
      │                    │                        │  │   { document: "...", ... },     │ │
      │                    │                        │  │   ...                           │ │
      │                    │                        │  │  ]                              │ │
      │                    │                        │  └──────────────────┬─────────────┘ │
      │                    │                        │                     │                │
      │                    │                        │  { documents,       │                │
      │                    │                        │    metadatas,       │                │
      │                    │                        │    distances }      │                │
      │                    │                        │◄────────────────────│                │
      │                    │                        │                     │                │
      │                    │          ┌─────────────▼──────────────────────────────────┐  │
      │                    │          │  [10] HR Agent: build prompt                    │  │
      │                    │          │                                                │  │
      │                    │          │  System message:                               │  │
      │                    │          │    "You are an HR assistant. Answer only       │  │
      │                    │          │     from the provided context. If the          │  │
      │                    │          │     answer is not in the context, say so."     │  │
      │                    │          │                                                │  │
      │                    │          │  Context block (top 5 chunks injected):        │  │
      │                    │          │    [CHUNK 1] hr-policy-2024.pdf p.4            │  │
      │                    │          │    "Employees receive 20 days annual leave..." │  │
      │                    │          │    [CHUNK 2] ...                               │  │
      │                    │          │                                                │  │
      │                    │          │  Conversation history (prior turns):           │  │
      │                    │          │    [{ role: "user", content: "..." },          │  │
      │                    │          │     { role: "assistant", content: "..." }]     │  │
      │                    │          │                                                │  │
      │                    │          │  User message:                                 │  │
      │                    │          │    "How many annual leave days do              │  │
      │                    │          │     employees receive?"                        │  │
      │                    │          └─────────────┬──────────────────────────────────┘  │
      │                    │                        │                     │                │
      │                    │          ┌─────────────▼──────────────────────────────────┐  │
      │                    │          │  [11] HR Agent: call OpenAI chat completions    │  │
      │                    │          │  model: gpt-4.1                                │  │
      │                    │          │  temperature: 0.2                              │  │
      │                    │          │  messages: [system, context, history...,       │  │
      │                    │          │             user_question]                     │  │
      │                    │          └─────────────┬──────────────────────────────────┘  │
      │                    │                        │                     │                │
      │                    │                        │  POST               │                │
      │                    │                        │  /v1/chat/          │                │
      │                    │                        │  completions        │                │
      │                    │                        │  (gpt-4.1)          │                │
      │                    │                        │────────────────────────────────────► │
      │                    │                        │                     │                │
      │                    │                        │  ┌──────────────────────────────────▼┐
      │                    │                        │  │  [12] OpenAI generates answer      │
      │                    │                        │  │  Returns:                          │
      │                    │                        │  │  {                                 │
      │                    │                        │  │   choices: [{                      │
      │                    │                        │  │    message: {                      │
      │                    │                        │  │     role: "assistant",             │
      │                    │                        │  │     content: "Employees receive    │
      │                    │                        │  │      20 days of annual leave per   │
      │                    │                        │  │      year, as stated in the HR     │
      │                    │                        │  │      Policy 2024..."               │
      │                    │                        │  │    }                               │
      │                    │                        │  │   }],                              │
      │                    │                        │  │   usage: {                         │
      │                    │                        │  │    prompt_tokens: 842,             │
      │                    │                        │  │    completion_tokens: 97,          │
      │                    │                        │  │    total_tokens: 939               │
      │                    │                        │  │   }                                │
      │                    │                        │  │  }                                 │
      │                    │                        │  └──────────────────────────────────┬┘
      │                    │                        │                     │                │
      │                    │                        │  { answer,          │                │
      │                    │                        │    usage }          │                │
      │                    │                        │◄────────────────────────────────────│
      │                    │                        │                     │                │
      │                    │          ┌─────────────▼──────────────────────────────────┐  │
      │                    │          │  [13] HR Agent: build citations                 │  │
      │                    │          │  Map retrieved chunks → CitationDTO[]:         │  │
      │                    │          │  [                                             │  │
      │                    │          │   {                                            │  │
      │                    │          │    documentId: "doc_abc123",                   │  │
      │                    │          │    filename: "hr-policy-2024.pdf",             │  │
      │                    │          │    page: 4,                                    │  │
      │                    │          │    chunk: 12,                                  │  │
      │                    │          │    excerpt: "Employees receive 20 days...",    │  │
      │                    │          │    similarityScore: 0.92                       │  │
      │                    │          │   },                                           │  │
      │                    │          │   ...                                          │  │
      │                    │          │  ]                                             │  │
      │                    │          └─────────────┬──────────────────────────────────┘  │
      │                    │                        │                     │                │
      │                    │          ┌─────────────▼──────────────────────────────────┐  │
      │                    │          │  [14] AI service: build ChatResponse            │  │
      │                    │          │  {                                             │  │
      │                    │          │   answer: "Employees receive 20 days...",      │  │
      │                    │          │   citations: [ CitationDTO[] ],               │  │
      │                    │          │   model: "gpt-4.1",                            │  │
      │                    │          │   latency_ms: 1843,                            │  │
      │                    │          │   usage: {                                     │  │
      │                    │          │    prompt_tokens: 842,                         │  │
      │                    │          │    completion_tokens: 97,                      │  │
      │                    │          │    total_tokens: 939                           │  │
      │                    │          │   }                                            │  │
      │                    │          │  }                                             │  │
      │                    │          └─────────────┬──────────────────────────────────┘  │
      │                    │                        │                     │                │
      │                    │  HTTP 200              │                     │                │
      │                    │  ChatResponse          │                     │                │
      │                    │◄───────────────────────│                     │                │
      │                    │                        │                     │                │
      │                    │  ┌─────────────────────▼──────────────────────────────────┐  │
      │                    │  │  [15] Node backend: persist assistant Message           │  │
      │                    │  │  INSERT Message {                                      │  │
      │                    │  │    role: "assistant",                                  │  │
      │                    │  │    content: answer,                                    │  │
      │                    │  │    conversationId,                                     │  │
      │                    │  │    tokenCount: usage.total_tokens,                     │  │
      │                    │  │    latencyMs: latency_ms,                              │  │
      │                    │  │    citations: JSON.stringify(citations)                │  │
      │                    │  │  }                                                     │  │
      │                    │  └─────────────────────┬──────────────────────────────────┘  │
      │                    │                        │                     │                │
      │                    │  ┌─────────────────────▼──────────────────────────────────┐  │
      │                    │  │  [16] Node backend: return ChatResponse                 │  │
      │                    │  │  Wrap in ApiResponse envelope:                         │  │
      │                    │  │  {                                                     │  │
      │                    │  │   success: true,                                       │  │
      │                    │  │   data: {                                              │  │
      │                    │  │    answer: "Employees receive 20 days...",             │  │
      │                    │  │    citations: [ ... ],                                 │  │
      │                    │  │    conversationId: "conv_xyz789",                      │  │
      │                    │  │    messageId: "msg_def456",                            │  │
      │                    │  │    model: "gpt-4.1",                                   │  │
      │                    │  │    latency_ms: 1843,                                   │  │
      │                    │  │    usage: { prompt_tokens, completion_tokens,          │  │
      │                    │  │             total_tokens }                             │  │
      │                    │  │   }                                                    │  │
      │                    │  │  }                                                     │  │
      │                    │  └─────────────────────┬──────────────────────────────────┘  │
      │                    │                        │                     │                │
      │  HTTP 200          │                        │                     │                │
      │  { success: true,  │                        │                     │                │
      │    data: {         │                        │                     │                │
      │     answer, ...    │                        │                     │                │
      │    } }             │                        │                     │                │
      │◄───────────────────│                        │                     │                │
      │                    │                        │                     │                │
```

---

## 2. Error Path — Internal Token Verification Fails

When the AI service rejects the request because the shared secret is missing or wrong:

```
Browser (React)       Node Backend          FastAPI AI Service
      │                    │                        │
      │  POST              │                        │
      │  /api/v1/          │                        │
      │  conversations/    │                        │
      │  chat              │                        │
      │───────────────────►│                        │
      │                    │                        │
      │                    │  [1] authenticate → OK │
      │                    │  [2] authorize  → OK   │
      │                    │  [3] ConversationService.chat()
      │                    │                        │
      │                    │  POST /api/v1/chat     │
      │                    │  (malformed or missing │
      │                    │   X-Internal-Token)    │
      │                    │───────────────────────►│
      │                    │                        │
      │                    │          ┌─────────────▼──────────────────────┐
      │                    │          │  [5] validate internal token        │
      │                    │          │  X-Internal-Token does NOT match   │
      │                    │          │  INTERNAL_API_SECRET.              │
      │                    │          │  Return HTTP 401 Unauthorized.     │
      │                    │          └─────────────┬──────────────────────┘
      │                    │                        │
      │                    │  HTTP 401              │
      │                    │◄───────────────────────│
      │                    │                        │
      │                    │  ┌─────────────────────▼──────────────────────┐
      │                    │  │  AiGateway catches upstream 401.            │
      │                    │  │  Throw AiServiceError("Internal auth       │
      │                    │  │  failure — AI service rejected token").    │
      │                    │  │  Global error handler maps → HTTP 502.     │
      │                    │  └─────────────────────┬──────────────────────┘
      │                    │                        │
      │  HTTP 502          │                        │
      │  { success: false, │                        │
      │    error: {        │                        │
      │     code: "AI_SERVICE_UNAVAILABLE",
      │     message: "..." } }
      │◄───────────────────│                        │
```

---

## 3. Error Path — No Relevant Chunks Found

When ChromaDB returns chunks whose similarity scores are all below the acceptance threshold:

```
Browser (React)       Node Backend          FastAPI AI Service        ChromaDB
      │                    │                        │                     │
      │  POST /chat        │                        │                     │
      │───────────────────►│───────────────────────►│                     │
      │                    │                        │                     │
      │                    │          [5] token OK  │                     │
      │                    │          [6] Supervisor → HR Agent           │
      │                    │          [7] embed question                  │
      │                    │                        │                     │
      │                    │                        │  query(embeddings,  │
      │                    │                        │   n_results=5)      │
      │                    │                        │────────────────────►│
      │                    │                        │                     │
      │                    │                        │  { documents: [],   │
      │                    │                        │    distances:       │
      │                    │                        │    [0.78, 0.82,     │
      │                    │                        │     0.91, ...] }    │
      │                    │                        │◄────────────────────│
      │                    │                        │                     │
      │                    │          ┌─────────────▼──────────────────────────────────┐
      │                    │          │  HR Agent: check similarity threshold           │
      │                    │          │  All distances > 0.70 (low relevance).         │
      │                    │          │  Skip OpenAI call.                             │
      │                    │          │  Return fallback answer:                       │
      │                    │          │  "I couldn't find relevant information in      │
      │                    │          │   the uploaded documents. Please ensure        │
      │                    │          │   the relevant HR policy has been uploaded."   │
      │                    │          │  citations: []                                 │
      │                    │          └─────────────┬──────────────────────────────────┘
      │                    │                        │                     │
      │                    │  HTTP 200              │                     │
      │                    │  { answer: "I couldn't │                     │
      │                    │    find relevant...",  │                     │
      │                    │    citations: [] }     │                     │
      │                    │◄───────────────────────│                     │
      │                    │                        │                     │
      │  HTTP 200          │                        │                     │
      │  (fallback answer) │                        │                     │
      │◄───────────────────│                        │                     │
```

---

## 4. Error Path — OpenAI Timeout

When the OpenAI API call exceeds the configured timeout:

```
Browser (React)       Node Backend          FastAPI AI Service                    OpenAI
      │                    │                        │                                │
      │  POST /chat        │                        │                                │
      │───────────────────►│───────────────────────►│                                │
      │                    │                        │                                │
      │                    │          [5–10] token, route, embed, ChromaDB OK        │
      │                    │                        │                                │
      │                    │                        │  POST /v1/chat/completions     │
      │                    │                        │───────────────────────────────►│
      │                    │                        │                                │
      │                    │                        │  ... 30s timeout exceeded ...  │
      │                    │                        │                                │
      │                    │          ┌─────────────▼──────────────────────────────┐ │
      │                    │          │  HR Agent: httpx.TimeoutException           │ │
      │                    │          │  Catch timeout, raise AiTimeoutError.      │ │
      │                    │          │  AI service returns HTTP 502.              │ │
      │                    │          └─────────────┬──────────────────────────────┘ │
      │                    │                        │                                │
      │                    │  HTTP 502              │                                │
      │                    │◄───────────────────────│                                │
      │                    │                        │                                │
      │                    │  ┌─────────────────────▼──────────────────────────────┐ │
      │                    │  │  AiGateway catches 502, throws AiServiceError.      │ │
      │                    │  │  Global error handler → HTTP 502 to browser.       │ │
      │                    │  └─────────────────────┬──────────────────────────────┘ │
      │                    │                        │                                │
      │  HTTP 502          │                        │                                │
      │  { success: false, │                        │                                │
      │    error: {        │                        │                                │
      │     code: "AI_TIMEOUT",                     │                                │
      │     message: "The AI service timed out.     │                                │
      │      Please try again." } }                 │                                │
      │◄───────────────────│                        │                                │
```
