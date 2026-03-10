# 🏗️ Architecture

This document explains runtime flow, module boundaries, and design rationale.

---

## 1. Runtime Graph

```mermaid
flowchart TD
    A[__start__] --> B[mode_router]
    B -->|"rag_enabled=true"| C[retrieve]
    B -->|"rag_enabled=false\ntools_enabled=true"| D[agent]
    B -->|"rag_enabled=false\ntools_enabled=false"| E[fallback]
    C -->|"documents found"| F[generate]
    C -->|"no docs + tools enabled"| D
    C -->|"no docs + tools disabled"| E
    F --> G[human_review]
    G --> Z[__end__]
    D -->|"tool call"| H[tools]
    H --> D
    D -->|"final response"| Z
    E --> Z
```

### Why This Shape?

The graph has **two routing stages**:

1. **Mode Router** — Decides whether to attempt retrieval at all. This avoids wasted embedding computation when RAG is disabled.
2. **Post-Retrieve Router** — Decides what to do with retrieval results. This enables graceful fallback when indexed documents don't match the query.

This two-stage design means **every combination** of settings produces a valid path — there are no dead ends.

---

## 2. End-to-End Data Flow

```mermaid
sequenceDiagram
    participant User
    participant UI as Streamlit UI
    participant Graph as Core Graph
    participant RAG as RAG Layer
    participant LLM as LLM Provider
    participant DB as SQLite Memory

    User->>UI: Ask question
    UI->>DB: Load chat history
    UI->>Graph: stream_answer(question, history, store, llm)
    
    alt RAG enabled
        Graph->>RAG: prepare_retrieval(question, history, store)
        RAG-->>Graph: {documents, citations, context}
        alt Documents found
            Graph->>LLM: llm.stream(RAG prompt + context)
            LLM-->>Graph: token stream
        else No documents
            alt Tools enabled
                Graph->>LLM: bind_tools() agent loop
            else
                Graph->>LLM: llm.stream(fallback prompt)
            end
        end
    else RAG disabled
        alt Tools enabled
            Graph->>LLM: bind_tools() agent loop
        else
            Graph->>LLM: llm.stream(direct prompt)
        end
    end

    Graph-->>UI: (generator, citations, used_fallback, source_type)
    UI->>UI: st.write_stream(generator)
    UI->>DB: Save HumanMessage + AIMessage
    UI->>User: Display answer + citations
```

---

## 3. Component Architecture

```mermaid
flowchart TB
    subgraph "Presentation Layer"
        UI[src/ui/app.py\nStreamlit UI\n315 lines]
        API[src/api/main.py\nFastAPI REST\n210 lines]
        SCH[src/api/schemas.py\nPydantic models\n49 lines]
    end

    subgraph "Application Layer"
        GRAPH[src/core/graph.py\nStateGraph + routing\n329 lines]
        NODES[src/core/nodes.py\nstream_answer + helpers\n206 lines]
        STATE[src/core/state.py\nAgentState TypedDict\n50 lines]
        PROMPTS[src/core/prompts.py\nPrompt templates\n47 lines]
        CHECK[src/core/checkpointer.py\nSqlite/Memory factory\n31 lines]
    end

    subgraph "Domain Layer"
        ING[src/rag/ingestion.py\nDocument loading + chunking\n92 lines]
        RET[src/rag/retriever.py\nVector search\n64 lines]
        EMB[src/rag/embeddings.py\nEmbedding model\n12 lines]
        WEB[src/tools/web_search.py\nTavily integration\n40 lines]
        DEF[src/tools/definitions.py\nToolNode definitions\n31 lines]
        EVAL_R[src/eval/runner.py\nBatch eval runner\n109 lines]
        EVAL_E[src/eval/evaluator.py\nLLM-as-judge scorer\n106 lines]
    end

    subgraph "Infrastructure Layer"
        LLM[src/llm/provider.py\nMulti-provider factory\n63 lines]
        MOD[src/memory/models.py\nSQLAlchemy ORM\n43 lines]
        REP[src/memory/repository.py\nCRUD operations\n53 lines]
        STO[src/memory/store.py\nLangChain adapter\n54 lines]
        TRC[src/observability/tracing.py\nCallback factory\n35 lines]
        DBG[src/observability/debug.py\nDebug helpers\n27 lines]
    end

    UI --> GRAPH
    UI --> STO
    API --> GRAPH
    API --> NODES
    API --> STO
    SCH --> API
    GRAPH --> NODES
    NODES --> STATE
    NODES --> PROMPTS
    NODES --> RET
    NODES --> WEB
    GRAPH --> RET
    GRAPH --> DEF
    GRAPH --> CHECK
    ING --> RET
    RET --> EMB
    NODES --> LLM
    GRAPH --> LLM
    STO --> REP
    REP --> MOD
    UI --> TRC
    UI --> DBG
    EVAL_R --> EVAL_E
    EVAL_E --> LLM
```

---

## 4. Module Responsibilities

| Layer | Module | Files | Responsibility | Key Pattern |
|-------|--------|-------|----------------|-------------|
| **Presentation** | UI | `src/ui/app.py` | User interaction, streaming display, session management | Streamlit session state |
| **Presentation** | API | `src/api/main.py`, `schemas.py` | REST endpoints, thin adapter over core | FastAPI + Pydantic models |
| **Application** | Core | `graph.py`, `nodes.py`, `state.py`, `prompts.py`, `checkpointer.py` | Graph routing, state orchestration, prompt templates, checkpoint factory | StateGraph + conditional edges |
| **Domain** | RAG | `ingestion.py`, `retriever.py`, `embeddings.py` | Document indexing and vector retrieval | Loader dispatch + PersistentClient |
| **Domain** | Tools | `web_search.py`, `definitions.py` | External capability integration, ToolNode definitions | Graceful degradation + @tool |
| **Domain** | Eval | `evaluator.py`, `runner.py`, `dataset.py` | LLM-as-judge scoring, batch evaluation | Pydantic output parsing |
| **Infrastructure** | LLM | `provider.py` | LLM provider abstraction | Factory pattern + Pydantic config |
| **Infrastructure** | Memory | `models.py`, `repository.py`, `store.py` | Session and message persistence | ORM → Repository → LangChain adapter |
| **Infrastructure** | Observability | `tracing.py`, `debug.py` | Tracing callbacks, debug logging | Callback injection (decorator pattern) |

---

## 5. Dependency Direction

```mermaid
flowchart TB
    P[Presentation: UI] --> A[Application: Core]
    A --> D[Domain: RAG + Tools]
    A --> I[Infrastructure: Memory + LLM + Observability]
    D --> I

    P -.->|"direct for session mgmt"| I
```

Dependencies flow **downward only**. The domain and infrastructure layers never import from the presentation or application layers.

**Exception:** The UI directly accesses `SQLiteChatHistory` for session management. This is a pragmatic shortcut — in a larger system, this would go through an application-layer service.

---

## 6. File Size Budget

The project follows a **300-line max** per file. Current sizes:

| File | Lines | Status |
|------|-------|--------|
| `graph.py` | 329 | ⚠️ Over budget — heavily wired graph |
| `app.py` | 315 | ⚠️ Over budget — candidate for splitting |
| `main.py` (API) | 210 | ✅ |
| `nodes.py` | 206 | ✅ |
| `runner.py` (eval) | 109 | ✅ |
| `evaluator.py` | 106 | ✅ |
| `ingestion.py` | 92 | ✅ |
| `retriever.py` | 64 | ✅ |
| `provider.py` | 63 | ✅ |
| `repository.py` | 53 | ✅ |
| `store.py` | 54 | ✅ |
| `state.py` | 50 | ✅ |
| `schemas.py` | 49 | ✅ |
| `prompts.py` | 47 | ✅ |
| `models.py` | 43 | ✅ |
| `web_search.py` | 40 | ✅ |
| `tracing.py` | 35 | ✅ |
| `dataset.py` | 33 | ✅ |
| `checkpointer.py` | 31 | ✅ |
| `definitions.py` | 31 | ✅ |
| `debug.py` | 27 | ✅ |
| `embeddings.py` | 12 | ✅ |

