# graph

## Purpose

This package defines the LangGraph `StateGraph` that wires together the supervisor and domain agent nodes into an executable workflow. It owns the graph topology — which nodes exist, which edges connect them, and what the entry and exit conditions are — but it does not implement the node logic itself. Node implementations live in `agents/`.

Separating graph construction from agent logic means the routing topology can be changed (e.g., adding a new domain specialist, changing routing conditions) without touching agent implementation files.

## Responsibilities

- Defining the shared graph state schema (`TypedDict`) passed between nodes
- Constructing the `StateGraph` and registering all agent nodes
- Defining conditional and unconditional edges that determine execution flow
- Compiling the graph into a runnable LangGraph chain
- Exposing the compiled graph for consumption by `api/v1/query.py`

## Does NOT Contain

- Agent node logic (supervisor routing, domain answers) — that belongs in `agents/`
- RAG pipeline calls — those are made by individual agent nodes, not the graph builder
- HTTP endpoint definitions — those live in `api/`
- Vector store or embedding code — those belong in `vectorstore/` and `embeddings/`

## Architecture Position

```
api/v1/query.py
       │
       │  user query + auth context
       ▼
graph/workflow.py  ◄── compiled LangGraph chain
       │
       │  StateGraph execution
       ▼
agents/supervisor.py  →  agents/hr_agent.py
                      →  agents/finance_agent.py
                      →  agents/it_agent.py
```

## Expected Contents

| File | Description | Status |
|---|---|---|
| `__init__.py` | Marks `graph` as a Python package | Planned for Increment 9 |
| `state.py` | `TypedDict` defining the shared state passed between all graph nodes (query, history, routing decision, retrieved chunks, final answer) | Planned for Increment 9 |
| `builder.py` | Constructs and compiles the `StateGraph`: registers nodes, defines edges, sets entry point | Planned for Increment 9 |
| `workflow.py` | Exposes the compiled, runnable graph as a FastAPI dependency or module-level singleton | Planned for Increment 9 |

## Design Principles

- **Single Responsibility** — This package only builds and exposes the graph; it does not implement what nodes do.
- **Separation of Concerns** — Graph topology is separate from agent logic and from HTTP handling.
- **Stateless** — The compiled graph object is stateless between invocations; per-request state is passed in via the `StateGraph` input at call time.

## Current Status

Reserved for future implementation — the directory exists as a placeholder. No functional code has been written.

## Future Work

Increment 9 implements the full graph definition: `state.py` typed schema, `builder.py` graph construction, and `workflow.py` runnable export. This depends on `agents/` (Increment 10) being available; the graph shell may be scaffolded first and populated as agent nodes land.
