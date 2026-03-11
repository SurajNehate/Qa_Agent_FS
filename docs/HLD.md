# 🧱 HLD — High-Level Design

## 🎯 Objective

Build a maintainable, learning-friendly QA system that demonstrates core agentic AI patterns through a real working application.

The system routes questions to the best available answer source:
1. **RAG generation** from locally indexed documents (highest trust)
2. **Web-grounded generation** using Tavily search (medium trust)
3. **Fallback answer** from LLM's general knowledge (lowest trust, clearly labeled)

---

## 🌍 System Context

```mermaid
C4Context
    title System Context Diagram

    Person(user, "User", "Asks questions about documents")

    System(ui, "Angular 17 Browser Client", "Rich UI with session management and markdown streaming")
    System(agent, "QA RAG Agent FastAPI", "LangGraph-based Q&A REST backend with RAG, web search, and persistent memory")

    System_Ext(chroma, "ChromaDB", "Persistent vector store for document embeddings")
    System_Ext(tavily, "Tavily API", "Web search for real-time information")
    System_Ext(llm, "LLM Provider", "OpenAI / Groq / Ollama")
    System_Ext(langfuse, "Langfuse", "Production tracing and cost monitoring")
    System_Ext(langsmith, "LangSmith", "Development tracing and evaluation")

    Rel(user, ui, "Interacts with chat interface")
    Rel(ui, agent, "HTTP/SSE requests (Ask, Upload, Sessions)")
    Rel(agent, chroma, "Stores and retrieves document embeddings")
    Rel(agent, tavily, "Searches web when RAG has no results")
    Rel(agent, llm, "Generates answers via streaming API")
    Rel(agent, langfuse, "Sends traces (optional)")
    Rel(agent, langsmith, "Sends traces (optional)")
```

---

## 🧠 Routing Design

The routing system has two decision stages:

### Stage 1: Mode Router (entry point)

```mermaid
flowchart TD
    Q[Incoming question] --> M{mode_router}
    M -->|"rag_enabled = true"| R[retrieve]
    M -->|"rag_enabled = false\ntools_enabled = true"| A[agent]
    M -->|"rag_enabled = false\ntools_enabled = false"| F[fallback]
```

**Design rationale:** The mode router is placed BEFORE retrieval to avoid wasted compute. If the user has disabled RAG, there's no point running embeddings and vector search.

### Stage 2: Post-Retrieve Router

```mermaid
flowchart TD
    R[retrieve] --> K{documents found?}
    K -->|"yes"| G[generate with RAG context]
    K -->|"no + tools enabled"| A[agent -> tools -> agent]
    K -->|"no + tools disabled"| F[fallback]
```

**Design rationale:** Even when RAG is enabled, retrieval might return no relevant documents. The post-retrieve router provides a graceful cascade to web search or fallback.

---

## 🧩 Logical Layers

```mermaid
flowchart TB
    subgraph "Layer 1 — Presentation"
        direction LR
        UI[Streamlit UI]
    end

    subgraph "Layer 2 — Application"
        direction LR
        GRAPH[Graph Orchestration]
        NODES[Node Logic]
        STATE[State Definition]
    end

    subgraph "Layer 3 — Domain"
        direction LR
        RAG[RAG Services]
        TOOLS[Tool Services]
    end

    subgraph "Layer 4 — Infrastructure"
        direction LR
        LLM[LLM Provider]
        MEM[Persistent Memory]
        OBS[Observability]
    end

    UI --> GRAPH
    GRAPH --> NODES
    NODES --> RAG
    NODES --> TOOLS
    NODES --> LLM
    UI --> MEM
    UI --> OBS
```

**Dependency rule:** Higher layers depend on lower layers. Lower layers never import from higher layers.

---

## ✅ Quality Attributes

| Attribute | Design Choice | How It's Achieved |
|---|---|---|
| **Maintainability** | Explicit node boundaries and typed state | `AgentState(TypedDict)` with `Required`/`NotRequired` annotations |
| **Extensibility** | New nodes/tools can be added with local impact | Add node to `build_graph()` + add edge — no existing code changes |
| **Reliability** | Deterministic fallback route | Every routing combination has a valid terminal path |
| **Testability** | Single code path for streaming and collection | `stream_answer()` returns generator — UI streams it, tests collect it |
| **Observability** | Trace-ready callback hooks | `get_callbacks()` injects tracing without modifying core logic |
| **Learning** | Visual routing and layered docs | Mermaid diagrams in every doc, guided learning path |
| **Performance** | Lazy imports and conditional execution | LLM providers loaded only when selected, tracing has zero overhead when disabled |

---

## 🔮 Evolution Path

```mermaid
timeline
    title QA RAG Agent Evolution
    section Foundation
        V1 : Baseline RAG : Streaming : Multi-LLM
        V2 : SQLite Memory : Langfuse/LangSmith : Web Search
        V3 : mode_router : Tools restructure : Debug PNG
    section Agentic Patterns
        V4 : LLM-as-judge Eval : Docker Compose : Ollama
        V5 : ToolNode : bind_tools : ReAct pattern
        V6 : interrupt_before : Human review : Approval flows
    section Production
        V7 : SqliteSaver : Time-travel debug : Crash recovery
        V8 : FastAPI REST API : tools_enabled parity : API hardening
    section Deployment
        V9 : Modal.com : Serverless API : Persistent volumes
        V10 : Angular Frontend : Netlify : SSE streaming UI
```

V1–V8 are **fully implemented**. V9–V10 have **prompts ready**. See [VERSIONS.md](VERSIONS.md) for details.

