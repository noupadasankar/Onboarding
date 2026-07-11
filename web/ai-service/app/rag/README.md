# rag

## Purpose
This package implements the Retrieval-Augmented Generation pipeline that grounds the AI Service's answers in documents that have been ingested and indexed by the platform. When an agent needs to answer a question, it calls into this pipeline to retrieve relevant document chunks, optionally rerank them for relevance, and assemble a structured prompt that is then sent to the LLM.

Separating the RAG pipeline into its own package ensures that the retrieval logic remains testable and reusable independently of the agent layer that calls it.

## Responsibilities
- Querying the vector store for chunks semantically similar to a given input
- Optionally reranking retrieved chunks to improve answer quality
- Assembling retrieved context into a structured prompt suitable for the LLM
- Orchestrating the end-to-end retrieval → rerank → prompt → LLM call sequence
- Returning a structured result (answer text + source references) to the calling agent

## Does NOT Contain
- Vector store client or collection management code (that lives in `vectorstore/`)
- Document loading or parsing logic (that lives in `loaders/`)
- HTTP route definitions (those live in `api/`)
- Agent routing or workflow state management (that lives in `agents/`)
- Raw LLM client configuration (that is handled in `core/` or a dedicated LLM client module)

## Architecture Position

```
agents/ (or api/ for direct query)
       │
       │  query string + retrieval config
       ▼
 rag/pipeline.py          ◄── orchestrates the full flow
       │
       ├──► rag/retriever.py     ──► vectorstore/  (semantic search)
       │                                   │
       │                               returns ranked chunks
       │
       ├──► rag/reranker.py      ◄── applies cross-encoder reranking (optional)
       │
       └──► rag/prompt_builder.py ◄── formats chunks + query into LLM prompt
                    │
                    ▼
                 LLM (Claude)  ──► answer text
```

## Expected Contents

| File | Description | Status |
|---|---|---|
| `__init__.py` | Marks `rag` as a Python package | Reserved |
| `pipeline.py` | Top-level orchestrator; calls retriever, reranker, and prompt builder in sequence | Planned for Increment 7 |
| `retriever.py` | Queries `vectorstore/` for the top-K chunks most similar to the input query | Planned for Increment 7 |
| `reranker.py` | Applies a cross-encoder or LLM-based reranking pass to improve chunk ordering | Planned for Increment 7 |
| `prompt_builder.py` | Formats retrieved chunks and the original query into a structured prompt string | Planned for Increment 7 |

## Design Principles
- **Single Responsibility** — Each module handles one stage of the pipeline; no single file spans retrieval, reranking, and prompt construction.
- **Separation of Concerns** — The RAG pipeline does not know about HTTP, agents, or document ingestion; it consumes chunks from the vector store and produces a prompt.
- **No Database Access** — The `rag/` package accesses the vector store only through the `vectorstore/` abstraction layer; it does not issue raw database queries.
- **Pure Functions** — Where possible, pipeline stages are implemented as pure functions to simplify unit testing and composition.

## Current Status
Reserved for future implementation — the directory exists as a placeholder. No functional code has been written.

## Future Work
Increment 7 implements the full RAG pipeline: `retriever.py`, `reranker.py`, `prompt_builder.py`, and `pipeline.py`. The pipeline will be consumed by the agent layer (Increment 9) and exposed via a query endpoint in `api/v1/query.py`.
