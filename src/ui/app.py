"""Streamlit Q&A RAG Agent — main UI with persistent memory & observability."""

import os
import sys
import uuid
import tempfile

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage

# Ensure project root is on sys.path for relative imports
_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

load_dotenv()

from src.llm.provider import LLMConfig, get_llm, PROVIDER_MODELS
from src.rag.retriever import get_vector_store, clear_collection
from src.rag.ingestion import ingest_files, reindex, SUPPORTED_EXTENSIONS
from src.tools.web_search import is_tavily_configured
from src.core.nodes import stream_answer
from src.memory.store import SQLiteChatHistory
from src.memory.models import init_db, get_engine
from src.memory import repository
from src.observability.tracing import get_callbacks
from src.observability.debug import is_debug_enabled, enable_debug, export_graph_png
from sqlalchemy.orm import sessionmaker

# ─── Page config ─────────────────────────────────────────────
st.set_page_config(
    page_title="Q&A RAG Agent",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 Q&A RAG Agent")
st.caption("Ask questions about your uploaded documents")

# ─── Enable debug if env says so ─────────────────────────────
if is_debug_enabled():
    enable_debug()
    if not st.session_state.get("debug_graph_exported", False):
        try:
            from src.core.graph import build_graph

            compiled_graph = build_graph()
            st.session_state.debug_graph_exported = export_graph_png(compiled_graph)
        except Exception as e:
            print(f"[debug] Could not build/export graph PNG: {e}")

# ─── Database setup ──────────────────────────────────────────
DB_URL = os.getenv("DATABASE_MEMORY_URL", "sqlite:///./data/memory.db")
os.makedirs("data", exist_ok=True)
_engine = init_db(DB_URL)
_DBSession = sessionmaker(bind=_engine)


# ─── Session state defaults ──────────────────────────────────
def _init_state():
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "store" not in st.session_state:
        st.session_state.store = get_vector_store()
    if "indexed_files" not in st.session_state:
        st.session_state.indexed_files = []
    if "llm_provider" not in st.session_state:
        st.session_state.llm_provider = os.getenv("LLM_PROVIDER", "groq")
    if "llm_model" not in st.session_state:
        st.session_state.llm_model = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
    if "llm" not in st.session_state:
        st.session_state.llm = None
    if "last_citations" not in st.session_state:
        st.session_state.last_citations = []
    if "last_fallback" not in st.session_state:
        st.session_state.last_fallback = False
    if "last_source_type" not in st.session_state:
        st.session_state.last_source_type = ""
    if "rag_enabled" not in st.session_state:
        st.session_state.rag_enabled = True
    if "tools_enabled" not in st.session_state:
        st.session_state.tools_enabled = False
    if "langfuse_enabled" not in st.session_state:
        st.session_state.langfuse_enabled = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
    if "langsmith_enabled" not in st.session_state:
        st.session_state.langsmith_enabled = os.getenv("LANGSMITH_ENABLED", "false").lower() == "true"

_init_state()


def _build_llm():
    """Build/rebuild the LLM with current settings."""
    config = LLMConfig(
        provider=st.session_state.llm_provider,
        model=st.session_state.llm_model,
    )
    st.session_state.llm = get_llm(config)


def _get_callbacks():
    """Get observability callbacks based on UI toggle state."""
    # Override env vars from UI toggles
    os.environ["LANGFUSE_ENABLED"] = str(st.session_state.langfuse_enabled).lower()
    os.environ["LANGSMITH_ENABLED"] = str(st.session_state.langsmith_enabled).lower()
    return get_callbacks(trace_name=f"session-{st.session_state.session_id[:8]}")


def _load_session(session_id: str):
    """Load a session's messages from SQLite into chat_history."""
    history = SQLiteChatHistory(session_id=session_id, db_url=DB_URL)
    st.session_state.session_id = session_id
    st.session_state.chat_history = history.messages
    st.session_state.last_citations = []
    st.session_state.last_fallback = False


# ─── Sidebar ─────────────────────────────────────────────────
with st.sidebar:
    # ── Session management ──
    st.header("💾 Sessions")

    with _DBSession() as db:
        sessions = repository.list_sessions(db, limit=20)

    session_options = {s.id: f"{s.title} ({s.created_at.strftime('%m/%d %H:%M') if s.created_at else ''})" for s in sessions}

    if session_options:
        selected = st.selectbox(
            "Load past session",
            options=["(current)"] + list(session_options.keys()),
            format_func=lambda x: "(current session)" if x == "(current)" else session_options.get(x, x[:8]),
        )
        if selected != "(current)" and selected != st.session_state.session_id:
            _load_session(selected)
            st.rerun()

    col_new, col_del = st.columns(2)
    with col_new:
        if st.button("➕ New", use_container_width=True):
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.chat_history = []
            st.session_state.last_citations = []
            st.session_state.last_fallback = False
            st.rerun()
    with col_del:
        if st.button("🗑️ Delete", use_container_width=True):
            with _DBSession() as db:
                repository.delete_session(db, st.session_state.session_id)
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.chat_history = []
            st.rerun()

    st.divider()

    # ── Document upload ──
    st.header("📁 Upload Documents")

    supported = [ext.lstrip(".") for ext in SUPPORTED_EXTENSIONS]
    uploaded_files = st.file_uploader(
        "Choose files",
        type=supported,
        accept_multiple_files=True,
        help=f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
    )

    col1, col2 = st.columns(2)
    with col1:
        index_btn = st.button("📥 Add to Index", use_container_width=True,
                              help="Adds new docs alongside existing ones")
    with col2:
        reindex_btn = st.button("🔄 Replace All", use_container_width=True,
                                help="Clears ALL existing docs, then indexes new ones")

    if uploaded_files and (index_btn or reindex_btn):
        with st.spinner("Indexing documents..."):
            tmp_paths = []
            for uf in uploaded_files:
                suffix = os.path.splitext(uf.name)[1]
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                tmp.write(uf.read())
                tmp.close()
                tmp_paths.append(tmp.name)

            try:
                if reindex_btn:
                    result = reindex(tmp_paths, st.session_state.store)
                    st.session_state.indexed_files = [uf.name for uf in uploaded_files]
                    st.success(f"✅ Replaced! Indexed {result['chunks']} chunks from {result['files']} file(s)")
                else:
                    result = ingest_files(tmp_paths, st.session_state.store)
                    st.session_state.indexed_files += [uf.name for uf in uploaded_files]
                    st.success(f"✅ Added {result['chunks']} chunks from {result['files']} file(s)")
            except Exception as e:
                st.error(f"❌ Indexing failed: {e}")
            finally:
                for p in tmp_paths:
                    os.unlink(p)

    if st.session_state.indexed_files:
        st.caption(f"📄 Indexed: {', '.join(st.session_state.indexed_files)}")

    if st.button("🗑️ Clear Index", use_container_width=True,
                 help="Removes ALL documents from the vector store"):
        clear_collection(st.session_state.store)
        st.session_state.indexed_files = []
        st.success("✅ Index cleared — all documents removed.")

    st.divider()

    # ── Answer Mode ──
    st.header("🔀 Answer Mode")

    st.session_state.rag_enabled = st.checkbox(
        "📚 RAG (use indexed documents)",
        value=st.session_state.rag_enabled,
        help="When enabled, searches your uploaded documents for answers",
    )

    _tavily_ok = is_tavily_configured()
    st.session_state.tools_enabled = st.checkbox(
        "🛠️ Use Tools",
        value=st.session_state.tools_enabled,
        disabled=not _tavily_ok,
        help="Requires TAVILY_API_KEY in .env" if not _tavily_ok
             else "When enabled, agent can use tools (web search, etc.)",
    )
    if not _tavily_ok:
        st.caption("⚠️ Set `TAVILY_API_KEY` in .env to enable web search")

    if not st.session_state.rag_enabled and not st.session_state.tools_enabled:
        st.info("💡 Direct mode — answers from LLM's own knowledge")

    st.divider()

    # ── Model settings ──
    st.header("🤖 Model Settings")

    provider = st.selectbox(
        "Provider",
        options=list(PROVIDER_MODELS.keys()),
        index=list(PROVIDER_MODELS.keys()).index(st.session_state.llm_provider)
        if st.session_state.llm_provider in PROVIDER_MODELS
        else 0,
        key="provider_select",
    )

    models = PROVIDER_MODELS.get(provider, ["default"])
    current_model = st.session_state.llm_model
    model_index = models.index(current_model) if current_model in models else 0

    model = st.selectbox(
        "Model",
        options=models,
        index=model_index,
        key="model_select",
    )

    if st.button("⚡ Apply Model", use_container_width=True):
        st.session_state.llm_provider = provider
        st.session_state.llm_model = model
        st.session_state.llm = None
        st.success(f"Switched to {provider} / {model}")

    st.divider()

    # ── Observability ──
    st.header("📡 Observability")

    st.session_state.langfuse_enabled = st.checkbox(
        "Enable Langfuse tracing",
        value=st.session_state.langfuse_enabled,
    )
    st.session_state.langsmith_enabled = st.checkbox(
        "Enable LangSmith tracing",
        value=st.session_state.langsmith_enabled,
    )
    st.caption(f"Session: `{st.session_state.session_id[:8]}...`")

    st.divider()

    # ── Memory ──
    st.header("💬 Memory")
    if st.button("🗑️ Clear Chat", use_container_width=True):
        history = SQLiteChatHistory(session_id=st.session_state.session_id, db_url=DB_URL)
        history.clear()
        st.session_state.chat_history = []
        st.session_state.last_citations = []
        st.session_state.last_fallback = False
        st.rerun()

    st.caption(f"Messages in history: {len(st.session_state.chat_history)}")


# ─── Ensure LLM is built ────────────────────────────────────
if st.session_state.llm is None:
    try:
        _build_llm()
    except Exception as e:
        st.error(f"❌ Failed to initialize LLM: {e}")
        st.info("Please check your API key in .env and try again.")
        st.stop()


# ─── Chat history display ───────────────────────────────────
for msg in st.session_state.chat_history:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user"):
            st.write(msg.content)
    elif isinstance(msg, AIMessage):
        with st.chat_message("assistant"):
            st.write(msg.content)


# ─── Chat input ─────────────────────────────────────────────
user_input = st.chat_input("Ask a question about your documents...")

if user_input:
    with st.chat_message("user"):
        st.write(user_input)

    # Persist to SQLite + session state
    st.session_state.chat_history.append(HumanMessage(content=user_input))
    sqlite_history = SQLiteChatHistory(session_id=st.session_state.session_id, db_url=DB_URL)
    sqlite_history.add_message(HumanMessage(content=user_input))

    # Get observability callbacks
    callbacks = _get_callbacks()

    # Stream the answer
    with st.chat_message("assistant"):
        try:
            token_stream, citations, used_fallback, source_type = stream_answer(
                question=user_input,
                chat_history=st.session_state.chat_history,
                store=st.session_state.store,
                llm=st.session_state.llm,
                callbacks=callbacks or None,
                rag_enabled=st.session_state.rag_enabled,
                tools_enabled=st.session_state.tools_enabled,
            )

            answer = st.write_stream(token_stream)

            st.session_state.last_citations = citations
            st.session_state.last_fallback = used_fallback
            st.session_state.last_source_type = source_type

            if answer:
                ai_msg = AIMessage(content=answer)
                st.session_state.chat_history.append(ai_msg)
                sqlite_history.add_message(ai_msg)
            else:
                st.warning("No answer was generated. Please try rephrasing your question.")

        except Exception as e:
            st.error(f"❌ Error: {e}")

    # ── Source indicator ──
    source = st.session_state.last_source_type
    if source == "rag":
        st.success("📚 Source: Indexed Documents (RAG)")
    elif source == "web":
        st.info("🌐 Source: Web Search (Tavily)")
    elif source == "direct":
        st.warning("💡 Source: LLM General Knowledge (no documents/web)")

    # ── Citations ──
    if st.session_state.last_citations:
        st.subheader("📎 Sources")
        for i, cite in enumerate(st.session_state.last_citations):
            source_label = cite.get('source', 'Unknown')
            page_label = cite.get('page', 'N/A')
            if page_label == "web":
                header = f"🌐 Source {i + 1}: {source_label}"
            else:
                header = f"Source {i + 1}: {source_label} (Page: {page_label})"
            with st.expander(header):
                st.text(cite.get("snippet", "No preview available."))
