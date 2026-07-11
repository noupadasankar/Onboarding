# Hybrid Search — BM25 + Dense RRF Sequence

OptiAgent — How exact identifiers and semantic queries are both handled correctly

---

## The Problem Hybrid Search Solves

Pure semantic (dense) vector search fails for exact identifiers:

| Query              | Pure Dense Result | Root Cause |
|--------------------|-------------------|------------|
| `HR-204`           | Generic HR chunks | "HR-204" tokenises into ["HR", "204"] — no semantic context |
| `TE-004`           | Mental health chunks (lucky) | Accidental semantic similarity |
| `BUPA`             | Medical/insurance chunks | "BUPA" is not in embedding training data |
| `£150`             | No result / wrong result | Currency symbols poorly embedded |
| `Section 7.2`      | Random policy sections | Section number has no semantic content |

BM25 (Best Match 25) solves this: it is a keyword relevance model that
scores chunks by exact term frequency and inverse document frequency.
It finds `HR-204` reliably because it looks for the literal string.

Reciprocal Rank Fusion (RRF) blends both signals: semantic similarity
for conceptual queries and BM25 for exact identifiers.

---

## Hybrid Search Pipeline

```
User Question
"What is policy HR-204?"
       │
       ▼
┌──────────────────────────────────────────┐
│  RetrievalService.retrieve()             │
│  config.use_hybrid = True (default)      │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│  QueryProcessor                          │
│  Normalise: strip excess whitespace,     │
│  lowercase for BM25, preserve for embed  │
└──────────────┬───────────────────────────┘
               │
       ┌───────┴───────┐
       │               │
       ▼               ▼
┌─────────────┐  ┌─────────────────────────┐
│ DENSE PATH  │  │ SPARSE PATH (BM25)       │
│             │  │                          │
│ Embed query │  │ VectorService            │
│ (OpenAI /   │  │ .get_all_text(dept=HR)   │
│  Local)     │  │                          │
│     │       │  │ ChromaDB.get(            │
│     ▼       │  │   include=["documents",  │
│ ChromaDB    │  │            "metadatas"]) │
│ .query(     │  │   (no embeddings fetch)  │
│   embed,    │  │       │                  │
│   n=20)     │  │       ▼                  │
│     │       │  │ BM25Okapi(               │
│     ▼       │  │   tokenised_corpus)      │
│ Dense rank  │  │       │                  │
│  list       │  │       ▼                  │
│ (by cosine  │  │ bm25.get_scores(         │
│  similarity)│  │   "what is policy hr-204"│
│             │  │ .lower().split())        │
│             │  │       │                  │
│             │  │       ▼                  │
│             │  │ BM25 rank list           │
│             │  │ (by keyword relevance)   │
└──────┬──────┘  └──────────┬──────────────┘
       │                    │
       └────────┬───────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────┐
│  Reciprocal Rank Fusion (RRF)                                 │
│                                                               │
│  Formula:   score[chunk_id] += 1 / (k + rank + 1)            │
│  k = 60     (standard smoothing constant)                     │
│                                                               │
│  Dense contributions:                                         │
│    chunk "HR-204 leave policy"   rank=4  → +1/(60+4+1) =0.015│
│    chunk "onboarding guide"      rank=0  → +1/(60+0+1) =0.016│
│                                                               │
│  BM25 contributions:                                          │
│    chunk "HR-204 leave policy"   rank=0  → +1/(60+0+1) =0.016│
│    chunk "onboarding guide"      rank=9  → +1/(60+9+1) =0.014│
│                                                               │
│  Combined RRF scores:                                         │
│    "HR-204 leave policy"  → 0.015 + 0.016 = 0.031  ← WINNER │
│    "onboarding guide"     → 0.016 + 0.014 = 0.030            │
│                                                               │
│  Sort by combined score (descending)                          │
│  Cap at n_results                                             │
└────────────────────────────────┬──────────────────────────────┘
                                 │
                                 ▼
                    Fused result list (20 chunks)
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │  ScoreReranker         │
                    │  Keep top 5 by score   │
                    │  Apply min_score filter│
                    └────────────┬───────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │  ContextBuilder        │
                    │  Assemble text within  │
                    │  6 000 token budget    │
                    └────────────┬───────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │  PromptBuilder         │
                    │  System prompt +       │
                    │  context + question    │
                    └────────────────────────┘
```

---

## RRF vs Dense-only: Rank Comparison

Query: **`HR-204`**

```
Rank  Dense-only                      Hybrid (RRF)
────  ──────────────────────────────  ────────────────────────────────
  1   "General leave entitlement..."   ★ "HR-204 leave policy: ..."  ← CORRECT
  2   "Onboarding process: ..."           "General leave entitlement..."
  3   "Sick leave allowance ..."          "Annual review process ..."
  4   "Annual review process ..."         "Onboarding process ..."
  5   ★ "HR-204 leave policy: ..."        "Sick leave allowance ..."

  HR-204 chunk at rank 5 in dense → rank 1 in hybrid (BM25 promoted it)
```

Query: **`How many days of annual leave?`** (semantic)

```
Rank  Dense-only                      Hybrid (RRF)
────  ──────────────────────────────  ────────────────────────────────
  1   "Employees receive 25 days..."   "Employees receive 25 days..."
  2   "Leave carryover policy..."      "Leave carryover policy..."
  3   "Public holidays: 10 per year"   "Public holidays: 10 per year"
  4   "HR-204 policy document..."      "HR-204 policy document..."
  5   "Sick leave: 10 days..."         "Sick leave: 10 days..."

  For semantic queries, RRF makes minimal difference — dense already wins
```

---

## Graceful Degradation Ladder

```
rank_bm25 installed?
    │
    ├── No  →  Log warning → Return dense results unchanged (no crash)
    │
    └── Yes
          │
          ▼
        Corpus empty (no indexed docs)?
          │
          ├── Yes →  Return dense results unchanged
          │
          └── No
                │
                ▼
              BM25 scores all zero for query?
                │
                ├── Yes →  Only dense RRF contributions apply
                │          (effectively dense-only with RRF scores)
                │
                └── No  →  Full BM25 + dense RRF fusion
```

---

## Corpus Fetching Strategy

```
ChromaDB collection
       │
       ▼
collection.get(
    include=["documents", "metadatas"]
    # ↑ NO "embeddings" — large vectors not needed for BM25
)
       │
       ▼
Filter by department (optional)
  where={"department": {"$eq": "HR"}}
       │
       ▼
[
  { chunk_id, text, document_id, metadata },
  { chunk_id, text, document_id, metadata },
  ...
]
       │
       ▼
BM25Okapi([ text.lower().split() for each chunk ])

Performance note:
  At 1 000 chunks × ~100 words each, get_all_text() fetches ~100 KB of text.
  BM25 index build ≈ 5–20 ms.
  Total hybrid overhead ≈ 15–50 ms (vs dense-only).
  At 10 000 chunks: consider pre-building the BM25 index per-department
  and refreshing on document upload/delete.
```

---

## Code Locations

| Component | File |
|-----------|------|
| HybridRetriever (BM25 + RRF) | `app/retrieval/hybrid_retriever.py` |
| RetrievalService (fusion step) | `app/retrieval/retrieval_service.py` — step 3b |
| VectorService.get_all_text() | `app/services/vector_service.py` |
| VectorRepository.get_all_text() | `app/repositories/vector_repository.py` |
| SearchRequest.use_hybrid | `app/schemas/search.py` |
| Search endpoint | `app/api/v1/search.py` |
| Dependency | `pyproject.toml` — `rank-bm25>=0.2.2` |
| Tests | `tests/retrieval/test_hybrid_retriever.py` |
