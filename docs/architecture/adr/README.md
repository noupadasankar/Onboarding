# Architecture Decision Records

OptiAgent — Deloitte Capstone 2026

Architecture Decision Records (ADRs) document significant design choices: what was decided, why, and what alternatives were considered. They provide a durable record that explains the system to future contributors and prevents the same debates from recurring.

ADRs are numbered sequentially and are never deleted. A superseded decision is marked as such and a new ADR is written to document the change.

---

## ADR Index

### Completed

| ADR | Title | Status | Increment |
|---|---|---|---|
| [0001](./0001-three-service-split.md) | Three-Service Split: React, Node.js, Python | Accepted | 1 |
| [0002](./0002-node-gateway-python-ai.md) | Node.js as API Gateway, Python for AI Workloads | Accepted | 1 |

### Planned

The following ADRs have been identified as necessary and will be written when the relevant increment begins. Decisions recorded here in advance are preliminary and subject to change.

| ADR | Title | Status | Planned Increment |
|---|---|---|---|
| 0003 | RAG Pipeline Design: Retrieval Strategy and Prompt Construction | Proposed | 7 |
| 0004 | Vector Database Selection: ChromaDB vs. Alternatives | Proposed | 6 |
| 0005 | LangGraph Supervisor Pattern: Routing Strategy for Specialist Agents | Proposed | 8 |
| 0006 | Document Chunking Strategy: Recursive vs. Semantic Splitting | Proposed | 4 |
| 0007 | Embedding Model Selection | Proposed | 5 |

---

## ADR Format

Each ADR follows this structure:

```
# ADR-NNNN: Title

Date: YYYY-MM-DD
Status: Proposed | Accepted | Deprecated | Superseded by ADR-XXXX

## Context

What situation or problem prompted this decision?

## Decision

What was decided?

## Rationale

Why was this option chosen over the alternatives?

## Alternatives Considered

What other options were evaluated and why were they rejected?

## Consequences

What are the trade-offs or implications of this decision?
```

---

## Notes on Planned ADRs

### ADR-0003: RAG Pipeline Design

Key questions to address:
- Whether to use a single retrieval step or a multi-hop retrieval strategy
- How to handle queries that span multiple documents or departments
- Whether to include a re-ranking step after initial retrieval
- How retrieved context is formatted in the LLM prompt

### ADR-0004: Vector Database Selection

ChromaDB has been selected as the provisional choice because it is embedded-friendly, Python-native, and has minimal operational overhead for a capstone project. This ADR will formally evaluate it against alternatives (pgvector, Pinecone, Weaviate) and justify the final selection.

### ADR-0005: LangGraph Supervisor Pattern

Key questions to address:
- Whether the supervisor uses keyword routing, LLM-based routing, or a hybrid
- How to handle queries that fall outside any agent's domain
- Whether agents communicate via shared state or message passing
- How to handle multi-turn conversations across agent boundaries

### ADR-0006: Document Chunking Strategy

Key questions to address:
- Recursive character splitting vs. semantic (sentence-boundary) splitting
- Optimal chunk size and overlap for the target document types
- Whether chunk size should vary by document type (PDFs vs. CSVs)

### ADR-0007: Embedding Model Selection

Key questions to address:
- Hosted embedding API (Anthropic, OpenAI) vs. local model (sentence-transformers)
- Dimension count and its effect on ChromaDB query performance
- Licensing and cost implications of the selected model
