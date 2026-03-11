"""FastAPI REST API for the QA RAG Agent.

This is a thin adapter layer — it translates HTTP requests into calls
to the same ``run_graph()`` and ``stream_answer()`` functions that the
Streamlit UI uses.  Zero business logic lives here.

Run:
    uvicorn src.api.main:app --reload --port 8000
"""

import os
import tempfile

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

from src.api.schemas import (
    AskRequest,
    AskResponse,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    SessionResponse,
)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

load_dotenv()

app = FastAPI(
    title="QA RAG Agent API",
    description="REST API for the Q&A RAG Agent with LangGraph",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Lazy-loaded shared resources (avoid import-time heavy lifting)
# ---------------------------------------------------------------------------

_store = None
_llm_cache: dict[str, object] = {}


def _get_store():
    global _store
    if _store is None:
        from src.rag.retriever import get_vector_store
        _store = get_vector_store()
    return _store


def _get_llm_for_model(model_name: str | None = None):
    """Get or create an LLM instance, optionally for a specific model."""
    from src.llm.provider import LLMConfig, get_llm, PROVIDER_MODELS

    if not model_name:
        # Use default from env
        config = LLMConfig()
        model_name = config.model
    else:
        config = None

    # Return cached LLM if exists
    if model_name in _llm_cache:
        return _llm_cache[model_name]

    # Determine provider from PROVIDER_MODELS
    if config is None:
        provider = None
        for prov, models in PROVIDER_MODELS.items():
            if model_name in models:
                provider = prov
                break
        if provider is None:
            provider = "openai"  # default fallback
        config = LLMConfig(provider=provider, model=model_name)

    try:
        llm = get_llm(config)
        _llm_cache[model_name] = llm
        return llm
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"LLM initialization failed for {model_name}: {e}",
        ) from e


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health", response_model=HealthResponse, tags=["System"])
async def health():
    """Health check — returns service status and feature availability."""
    from src.tools.web_search import is_tavily_configured

    store = _get_store()
    collection_count = 0
    try:
        collection_count = store._collection.count()
    except Exception:
        pass

    return HealthResponse(
        status="ok",
        version="0.2.0",
        rag_ready=collection_count > 0,
        web_search_ready=is_tavily_configured(),
    )


@app.get("/api/models", tags=["System"])
async def list_models():
    """List available LLM models grouped by provider."""
    import os
    from src.llm.provider import PROVIDER_MODELS, LLMConfig

    default_model = LLMConfig().model
    ollama_available = bool(os.getenv("OLLAMA_BASE_URL"))
    groq_available = bool(os.getenv("GROQ_API_KEY"))

    result = []
    for provider, models in PROVIDER_MODELS.items():
        available = True
        warning = None
        if provider == "ollama" and not ollama_available:
            available = False
            warning = "Ollama requires local setup — not available in cloud deployment"
        elif provider == "groq" and not groq_available:
            available = False
            warning = "GROQ_API_KEY not configured"

        for model in models:
            result.append({
                "model": model,
                "provider": provider,
                "available": available,
                "warning": warning,
                "is_default": model == default_model,
            })
    return result


@app.post("/api/ask", response_model=AskResponse, tags=["Agent"])
async def ask(req: AskRequest):
    """Ask the agent a question. Returns a complete answer with citations."""
    import uuid
    from src.core.graph import run_graph
    from src.memory.store import SQLiteChatHistory
    from langchain_core.messages import HumanMessage, AIMessage
    from src.observability.tracing import get_callbacks

    store = _get_store()
    llm = _get_llm_for_model(req.model)

    # Auto-create session if not provided
    session_id = req.session_id or str(uuid.uuid4())

    # Load chat history from session
    chat_history = []
    try:
        history = SQLiteChatHistory(session_id=session_id)
        chat_history = history.messages
    except Exception:
        pass

    callbacks = get_callbacks(trace_name=f"api-ask-{session_id[:8]}")

    result = run_graph(
        question=req.question,
        chat_history=chat_history,
        store=store,
        llm=llm,
        rag_enabled=req.rag_enabled,
        tools_enabled=req.tools_enabled,
        callbacks=callbacks,
    )

    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    answer = result.get("answer", "")

    # Persist messages to session
    try:
        history = SQLiteChatHistory(session_id=session_id)
        history.add_message(HumanMessage(content=req.question))
        history.add_message(AIMessage(content=answer))
        # Update session title from first question
        if not req.session_id:
            from sqlalchemy.orm import Session as DBSession
            from src.memory.models import get_engine, ConversationSession
            engine = get_engine()
            with DBSession(engine) as db:
                s = db.query(ConversationSession).filter_by(id=session_id).first()
                if s and (not s.title or s.title == "New conversation"):
                    s.title = req.question[:80]
                    db.commit()
    except Exception:
        pass

    return AskResponse(
        answer=answer,
        citations=result.get("citations", []),
        source_type=result.get("source_type", "direct"),
        used_fallback=result.get("used_fallback", False),
        session_id=session_id,
        error=result.get("error"),
    )


@app.post("/api/ask/stream", tags=["Agent"])
async def ask_stream(req: AskRequest):
    """Ask the agent a question with streaming response (SSE)."""
    import uuid
    import json
    from src.core.nodes import stream_answer
    from src.memory.store import SQLiteChatHistory
    from langchain_core.messages import HumanMessage, AIMessage
    from src.observability.tracing import get_callbacks

    store = _get_store()
    llm = _get_llm_for_model(req.model)

    # Auto-create session if not provided
    session_id = req.session_id or str(uuid.uuid4())

    chat_history = []
    try:
        history = SQLiteChatHistory(session_id=session_id)
        chat_history = history.messages
    except Exception:
        pass

    callbacks = get_callbacks(trace_name=f"api-stream-{session_id[:8]}")

    token_stream, citations, used_fallback, source_type = stream_answer(
        question=req.question,
        chat_history=chat_history,
        store=store,
        llm=llm,
        callbacks=callbacks,
        rag_enabled=req.rag_enabled,
        tools_enabled=req.tools_enabled,
    )

    def generate():
        full_answer = []
        for token in token_stream:
            full_answer.append(token)
            yield f"data: {token}\n\n"

        # Persist messages to session
        try:
            h = SQLiteChatHistory(session_id=session_id)
            h.add_message(HumanMessage(content=req.question))
            h.add_message(AIMessage(content="".join(full_answer)))
            # Update session title from first question
            if not req.session_id:
                from sqlalchemy.orm import Session as DBSession
                from src.memory.models import get_engine, ConversationSession
                engine = get_engine()
                with DBSession(engine) as db:
                    s = db.query(ConversationSession).filter_by(id=session_id).first()
                    if s and (not s.title or s.title == "New conversation"):
                        s.title = req.question[:80]
                        db.commit()
        except Exception:
            pass

        # Send metadata as JSON before DONE
        meta = json.dumps({
            "citations": citations,
            "source_type": source_type,
            "used_fallback": used_fallback,
            "session_id": session_id,
        })
        yield f"data: [META]{meta}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/ingest", response_model=IngestResponse, tags=["Documents"])
async def ingest(files: list[UploadFile], replace_existing: bool = False):
    """Upload and ingest documents into the vector store.

    Supports: .txt, .md, .pdf, .docx
    """
    from src.rag.ingestion import ingest_files, reindex, SUPPORTED_EXTENSIONS

    store = _get_store()
    tmp_paths = []
    original_names = []

    try:
        for f in files:
            ext = os.path.splitext(f.filename or "")[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {ext}. Supported: {SUPPORTED_EXTENSIONS}",
                )
            # Save to temp file, track original name
            suffix = ext
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                content = await f.read()
                tmp.write(content)
                tmp_paths.append(tmp.name)
                original_names.append(f.filename or os.path.basename(tmp.name))

        if replace_existing:
            result = reindex(tmp_paths, store, original_names=original_names)
        else:
            result = ingest_files(tmp_paths, store, original_names=original_names)

        return IngestResponse(
            files_processed=result.get("files", 0),
            chunks_created=result.get("chunks", 0),
        )
    finally:
        for p in tmp_paths:
            try:
                os.unlink(p)
            except OSError:
                pass


@app.delete("/api/index", tags=["Documents"])
async def clear_index():
    """Clear all documents from the vector store."""
    try:
        import os
        import chromadb
        collection_name = os.getenv("CHROMA_COLLECTION", "qa_docs")
        client = chromadb.PersistentClient(path="data/chroma_db")
        # Delete and recreate the collection
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass  # collection doesn't exist yet
        client.get_or_create_collection(collection_name)
        # Reset cached store so next request creates a fresh one
        global _store
        _store = None
        return {"status": "cleared", "message": "All documents removed from index"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear index: {e}")


@app.get("/api/sessions", response_model=list[SessionResponse], tags=["Memory"])
async def list_sessions():
    """List recent conversation sessions."""
    from src.memory.models import get_engine
    from src.memory.repository import list_sessions as _list_sessions
    from sqlalchemy.orm import Session as DBSession

    engine = get_engine()
    with DBSession(engine) as db:
        sessions = _list_sessions(db, limit=20)
        return [
            SessionResponse(
                id=str(s.id),
                title=s.title,
                created_at=s.created_at.isoformat() if s.created_at else "",
            )
            for s in sessions
        ]

@app.get("/api/sessions/{session_id}/messages", tags=["Memory"])
async def get_session_messages(session_id: str):
    """Load all messages from a conversation session."""
    try:
        from src.memory.store import SQLiteChatHistory
        from langchain_core.messages import HumanMessage

        history = SQLiteChatHistory(session_id=session_id)
        messages = history.messages
        return [
            {
                "role": "human" if isinstance(m, HumanMessage) else "ai",
                "content": m.content,
            }
            for m in messages
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load messages: {e}")


@app.delete("/api/sessions/{session_id}", tags=["Memory"])
async def delete_session(session_id: str):
    """Delete a conversation session and its messages."""
    from src.memory.models import get_engine
    from src.memory.repository import delete_session as _delete_session
    from sqlalchemy.orm import Session as DBSession

    engine = get_engine()
    with DBSession(engine) as db:
        _delete_session(db, session_id)
        return {"status": "deleted", "session_id": session_id}
