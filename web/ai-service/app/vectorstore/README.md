# vectorstore

## Purpose
This package encapsulates all interaction with ChromaDB, the vector database used to store and retrieve document embeddings. It provides a clean abstraction over the ChromaDB client so that the rest of the application — specifically the RAG pipeline and the ingestion flow — can perform semantic search and embedding storage without depending directly on ChromaDB's API surface.

Isolating ChromaDB integration here means the database client, collection configuration, and query logic are all maintained in one place. If the vector store technology changes in the future, only this package needs to be updated.

## Responsibilities
- Initialising and managing the ChromaDB client and its connection lifecycle
- Creating and retrieving named collections that correspond to document domains
- Storing document chunk embeddings alongside their metadata and source text
- Executing approximate nearest-neighbour queries and returning ranked results
- Deleting or updating stored embeddings when source documents are removed or re-ingested

## Does NOT Contain
- Embedding computation (embeddings are computed upstream and passed in as vectors)
- Chunking or text splitting logic (that belongs to a dedicated chunking module, Increment 4)
- HTTP endpoint definitions (those live in `api/`)
- RAG pipeline orchestration (that belongs in `rag/`)
- Business logic about which results are "good enough" to use in a prompt

## Architecture Position

```
Ingestion flow:
  loaders/ → chunking → embeddings → vectorstore/store.py  ──► ChromaDB

Query flow:
  rag/retriever.py ──► vectorstore/search.py ──► ChromaDB
                                │
                        returns List[ChunkResult]
                        { text, metadata, distance }
```

## Expected Contents

| File | Description | Status |
|---|---|---|
| `__init__.py` | Marks `vectorstore` as a Python package; exports the primary client accessor | Planned for Increment 6 |
| `client.py` | Initialises the ChromaDB `PersistentClient` or `HttpClient`; manages connection lifecycle and is injected as a FastAPI dependency | Planned for Increment 6 |
| `collections.py` | Defines named collection identifiers and handles collection creation/retrieval logic | Planned for Increment 6 |
| `store.py` | Accepts pre-computed embeddings and metadata; writes them to the appropriate ChromaDB collection | Planned for Increment 6 |
| `search.py` | Accepts a query embedding and returns the top-K most similar chunks from a given collection | Planned for Increment 6 |

## Design Principles
- **Single Responsibility** — Each module owns one concern: client lifecycle, collection management, writes, or reads.
- **Separation of Concerns** — The vector store layer does not know about loaders, chunking, or how results will be used in a prompt; it is a pure storage and retrieval interface.
- **No Business Logic** — Relevance thresholds, result filtering, and prompt assembly are the responsibility of the `rag/` layer.
- **No HTTP Logic** — This package is a service-layer abstraction; it is consumed by other Python modules, not by HTTP handlers directly.

## Current Status
Reserved for future implementation — the directory exists as a placeholder. No functional code has been written.

## Future Work
Increment 6 implements all modules in this package: ChromaDB client setup, collection management, embedding storage, and semantic search. This unblocks the RAG pipeline in Increment 7 and the agent layer in Increment 9.
