# embeddings

## Purpose

This package converts text chunks — produced by `chunking/` — into fixed-dimensional vector representations using a configured embedding model. These vectors are then stored in the vector database by `vectorstore/` and used at query time to find semantically similar content.

The embedding layer is provider-agnostic: the underlying model (OpenAI, Anthropic, a locally-hosted sentence transformer, etc.) is injected through `providers/`, so the embedding interface remains stable across model changes.

## Responsibilities

- Accepting a list of text strings and returning a corresponding list of embedding vectors
- Delegating to the configured embedding provider from `providers/`
- Batching requests to the embedding API to stay within rate and token limits
- Normalising vector dimensions and types for compatibility with the vector store

## Does NOT Contain

- LLM provider client initialisation (that belongs in `providers/`)
- Chunking or text splitting logic (that belongs in `chunking/`)
- Vector store writes (that belongs in `vectorstore/`)
- HTTP endpoint definitions (those live in `api/`)
- Database access of any kind

## Architecture Position

```
chunking/
    │
    │  List[Chunk] { text, metadata }
    ▼
embeddings/service.py   ◄── calls provider, returns vectors
    │
    │  List[EmbeddingVector] (float[])
    ▼
vectorstore/store.py
```

## Expected Contents

| File | Description | Status |
|---|---|---|
| `__init__.py` | Marks `embeddings` as a Python package | Planned for Increment 5 |
| `service.py` | Core embedding logic: batching, error handling, vector normalisation | Planned for Increment 5 |
| `providers.py` | Thin wrappers over embedding API clients (OpenAI embeddings, local sentence-transformers, etc.) | Planned for Increment 5 |

## Design Principles

- **Single Responsibility** — `service.py` owns batching and orchestration; `providers.py` owns API client details.
- **Separation of Concerns** — The embedding service does not know about chunking strategy, vector storage, or retrieval logic.
- **No Database Access** — Embeddings are computed in memory; persistence is the responsibility of `vectorstore/`.
- **Stateless** — The embedding service is stateless between calls; the provider client is injected as a dependency.

## Current Status

Reserved for future implementation — the directory exists as a placeholder. No functional code has been written.

## Future Work

Increment 5 implements `service.py` and `providers.py`. The initial provider will target the embedding model available through the chosen LLM provider. Local sentence-transformer support may be added as an offline fallback.
