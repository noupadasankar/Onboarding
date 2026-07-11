# memory

## Purpose

This package manages conversation memory for the agent layer: storing, retrieving, and summarising conversation history so that agents can maintain context across multiple turns within a session. Memory is passed into the LangGraph state at request time; it is not stored as module-level mutable state.

Memory storage may be in-process (for short sessions) or backed by a lightweight store (Redis or a dedicated table) when conversation history needs to survive across service restarts or scale across multiple instances.

## Responsibilities

- Storing and retrieving per-session conversation turns (user messages and agent responses)
- Summarising long conversation histories when they would exceed the LLM context window
- Providing a clean interface for agent nodes to read prior context and append new turns
- Deciding which turns to retain versus summarise based on configurable window size

## Does NOT Contain

- Document storage or retrieval (that belongs in `vectorstore/`)
- User profile or authentication data (that belongs in the Node backend)
- LLM provider API calls directly (those go through `providers/`)
- HTTP endpoint definitions (those live in `api/`)

## Architecture Position

```
api/v1/query.py  (receives session_id + new message)
       │
       ▼
memory/  ◄── loads prior conversation turns for this session
       │
       │  conversation history
       ▼
graph/workflow.py  (injected into LangGraph state)
       │
       ▼
memory/  ◄── appends new turn after graph execution completes
```

## Expected Contents

| File | Description | Status |
|---|---|---|
| `__init__.py` | Marks `memory` as a Python package | Not yet assigned to an increment |
| `store.py` | Reads and writes conversation turns keyed by session ID | Not yet assigned to an increment |
| `summariser.py` | Compresses long conversation histories into a summary when the window exceeds a configurable token budget | Not yet assigned to an increment |

## Design Principles

- **Single Responsibility** — Memory handles conversation history only; it does not influence routing or retrieval decisions.
- **Separation of Concerns** — Memory is a service consumed by the graph layer; it has no knowledge of agent logic or domain specifics.
- **Stateless** — The memory module does not hold conversation state in Python process memory between requests; state is externalised to a store.

## Current Status

Reserved for future implementation — the directory exists as a placeholder. No functional code has been written.

## Future Work

Increment not yet assigned. Memory becomes necessary when multi-turn conversation support is added to the agent layer (Increment 10+). The implementation approach (Redis-backed vs. lightweight DB table) will be decided at that point based on deployment requirements.
