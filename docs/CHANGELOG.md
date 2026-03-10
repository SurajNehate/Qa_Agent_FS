# 📝 Changelog

All notable changes to this project are documented here.

---

## V9 — Modal.com Cloud Deployment (2026-03-10)

### Added ✅

- `deploy_modal.py` — Modal.com serverless deployment script for FastAPI
  - `@modal.asgi_app()` mounts existing FastAPI app (zero code duplication)
  - `modal.Volume` for persistent ChromaDB across redeployments
  - `modal.Secret` for API key management
  - `allow_concurrent_inputs=10`, `container_idle_timeout=120`
- `QA_RAG_AGENT_V9_PROMPT.md` — Deployment prompt with setup, commands, and smoke tests
- `QA_RAG_AGENT_V10_PROMPT.md` — Angular frontend prompt (prompt ready, not yet implemented)

### Updated 🔧

- `Dockerfile` — Exposes both 8501 (Streamlit) and 8000 (FastAPI), dual healthcheck
- `docker-compose.yml` — Added `api` service with `uvicorn` CMD override, shared volumes
- `Makefile` — Already has `api` target for local FastAPI dev
- `README.md` — Added ☁️ Cloud Deployment section with Modal setup and smoke tests
- `VERSIONS.md` — Added V9 (Implemented) and V10 (Prompt Ready)
- `HLD.md` — Evolution timeline extended with Deployment section (V9, V10)

---

## Post-V7.1 - Tools Naming + Prompt/Docs Alignment (2026-03-10)

### Updated 🔧

- Unified naming to `tools_enabled` across tests and architecture docs.
- Updated routing diagrams to reflect current graph shape:
  - `mode_router -> retrieve|agent|fallback`
  - `retrieve -> generate|agent|fallback`
  - `agent <-> tools` ReAct loop
  - `generate -> human_review -> END`
- Added `QA_RAG_AGENT_V8_PROMPT.md` for FastAPI parity/hardening implementation tracking.
- Updated version roadmap docs to include implemented V8.

### Dependency Alignment ✅

- `requirements.txt` now explicitly includes:
  - `langgraph-checkpoint-sqlite`
  - `python-multipart`
  - `httpx`

---

## Post-V7 — REST API + Cleanup (2026-03-10)

### Added ✅

- `src/api/main.py` — FastAPI REST API with 6 endpoints (ask, ask/stream, ingest, sessions, health)
- `src/api/schemas.py` — Pydantic request/response models
- `tests/test_api.py` — 11 tests for endpoints, schemas, and OpenAPI docs
- `create_graph()` zero-argument wrapper for `langgraph dev` compatibility
- `python-multipart` dependency for file upload support

### Removed 🗑️

- `get_execution_history()` — dead code (LangGraph's built-in `get_state_history()` covers this)
- Orphaned `web_search` graph node registration + edge (unreachable after V5 tool-calling refactor)

### Fixed 🐛

- `langgraph.json` now points to `create_graph` (zero-arg factory) instead of `build_graph` (custom params rejected by dev server)

---

## V7 — Checkpointing (2026-03-09)

### Added ✅

- `src/core/checkpointer.py` — Factory for SqliteSaver (production) and MemorySaver (tests)
- `get_thread_config()` helper for thread-based execution
- `get_execution_history()` for time-travel debugging
- `CHECKPOINT_DB_PATH` and `CHECKPOINT_ENABLED` env vars
- `langgraph-checkpoint-sqlite` dependency in `pyproject.toml`
- `tests/test_checkpointing.py` — 7 tests for checkpointer factory and graph compilation

### Updated 🔧

- `build_graph()` now accepts `checkpointer` and `interrupt_before` parameters
- `.env.example` updated with V7 checkpoint variables

---

## V6 — Human-in-the-Loop (2026-03-09)

### Added ✅

- `_human_review_node()` in `graph.py` — Approve/reject flow for generated answers
- `AgentState` extended with review fields: `review_mode`, `requires_review`, `human_approved`, `human_feedback`
- Generate node now routes through `human_review` before `END`
- `tests/test_human_loop.py` — 5 tests for review logic

---

## V5 — LangGraph Tool-Calling (2026-03-09)

### Added ✅

- `src/tools/definitions.py` — `web_search_tool` with `@tool` decorator and schema
- `TOOLS` list for extensible multi-tool support
- `_agent_node()` in `graph.py` — LLM decides when to call tools via `bind_tools()`
- `_agent_should_continue()` — ReAct loop routing (tools vs end)
- `ToolNode(TOOLS)` added to graph for automatic tool execution
- `AgentState.messages` field for tool-calling conversation
- `tests/test_tools.py` — 10 tests for tool schemas and agent routing

### Updated 🔧

- Mode router now routes to `agent` instead of `web_search` when `tools_enabled=True`
- Post-retrieval routing also routes to `agent` when no docs found
- `run_graph()` now defaults `rag_enabled=True` and accepts routing params

---

## V4 — Evaluation + Docker (2026-03-09)

### Added ✅

- `src/eval/evaluator.py` — LLM-as-judge scoring (faithfulness, relevance, completeness)
- `src/eval/dataset.py` — Pydantic-validated dataset loader
- `src/eval/runner.py` — Batch evaluation runner with formatted tabular report
- `data/eval_dataset.json` — 5 sample evaluation questions
- `Dockerfile` — Production container with health check
- `docker-compose.yml` — Multi-service with optional Ollama profile
- `.dockerignore`
- `tests/test_eval.py` — 7 tests for evaluator and dataset loader
- Makefile targets: `eval`, `docker-build`, `docker-up`, `docker-down`, `docker-ollama`

---

## V3 — Architecture Alignment (2026-03-03)

### Updated 🔧

- Graph now explicitly implements `mode_router` as the entry node.
- Web search moved from `src/rag/web_search.py` to `src/tools/web_search.py`.
- Routing defaults: `state.get("rag_enabled", False)` and `state.get("tools_enabled", False)`.
- Documentation and README aligned to current graph topology.

### Added ✨

- Consistent Mermaid diagrams across all docs.
- HLD and Architecture descriptions updated to match runtime behavior.
- Debug PNG export (`LANGGRAPH_DEBUG=true` → `docs/graph.png`).

---

## V2 — Memory + Observability + Web Search (2026-02-22)

### Added ✨

- **SQLite conversation memory** (`src/memory/`)
  - `ConversationSession` and `ConversationMessage` ORM models.
  - `SQLiteChatHistory` implementing `BaseChatMessageHistory`.
  - Session management (create, load, delete) in Streamlit sidebar.
- **Observability** (`src/observability/`)
  - `get_callbacks()` factory for Langfuse + LangSmith dual tracing.
  - UI toggle for enabling/disabling tracing at runtime.
  - `enable_debug()` + `export_graph_png()` for LangGraph debug mode.
- **Web search** (`src/tools/web_search.py`)
  - Tavily integration with graceful degradation.
  - `format_web_context()` for LLM context building.
  - `WEB_SEARCH_PROMPT` template for web-grounded answers.
- **LangGraph StateGraph** (`build_graph()`)
  - Proper `StateGraph` with nodes and conditional edges.
  - Compatible with `langgraph dev --config langgraph.json`.
- **3-tier routing**: RAG → Web Search → Direct/Fallback.
- **AgentState extensions**: `source_type`, `rag_enabled`, `tools_enabled`, `session_id`.
- **New tests**: `test_memory_sqlite.py`, `test_observability.py`.
- **New dependencies**: SQLAlchemy, langfuse, langsmith, tavily-python.

### Changed 🔄

- `stream_answer()` signature extended with `rag_enabled`, `tools_enabled`, `callbacks` params.
- `run_graph()` preserved as thin wrapper for backward compatibility.
- `pyproject.toml` version bumped to `0.2.0`.

---

## V1 — Baseline RAG (2026-02-18)

### Added ✨

- **Core RAG pipeline** (`src/core/`)
  - `AgentState` TypedDict for typed state flow.
  - `stream_answer()` single code path for streaming and non-streaming use.
  - `prepare_retrieval()` for sync retrieval + routing.
  - `run_graph()` thin wrapper for test execution.
  - RAG and fallback prompt templates with `MessagesPlaceholder`.
- **Document ingestion** (`src/rag/`)
  - Support for PDF, TXT, Markdown, DOCX via LangChain loaders.
  - `RecursiveCharacterTextSplitter` (800 chars, 150 overlap).
  - `HuggingFaceEmbeddings` with `all-MiniLM-L6-v2`.
  - ChromaDB `PersistentClient` for durable vector storage.
- **Multi-LLM support** (`src/llm/provider.py`)
  - Factory pattern with OpenAI, Groq, Ollama providers.
  - `LLMConfig` Pydantic model with env var defaults.
  - Runtime model switching via UI dropdown.
- **Streamlit UI** (`src/ui/app.py`)
  - Chat interface with `st.chat_message` bubbles.
  - Token streaming via `st.write_stream()`.
  - Document upload + indexing sidebar.
  - Citation display with expandable source snippets.
  - Fallback notice when no relevant documents found.
- **Tests**: `test_ingestion.py`, `test_retrieval.py`, `test_graph.py`.
- **Documentation**: README.md with quickstart and architecture diagram.

