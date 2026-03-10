"""Q&A RAG agent — single code path for streaming and non-streaming use.

Architecture:
    prepare_retrieval()  →  sync: retrieval + routing + citations
    stream_answer()      →  unified entry: returns (generator, citations, used_fallback, source_type)

Modes (controlled by flags):
    RAG enabled       →  retrieve from ChromaDB, answer with context
    Web Search enabled →  search with Tavily, answer with web results
    Both disabled      →  answer from LLM's general knowledge (direct mode)

UI streams from the generator; tests collect it with "".join().
"""

from typing import Any, Generator

from langchain_chroma import Chroma
from langchain_core.language_models.chat_models import BaseChatModel

from src.core.prompts import (
    RAG_SYSTEM_PROMPT,
    FALLBACK_SYSTEM_PROMPT,
    WEB_SEARCH_PROMPT,
    DIRECT_PROMPT,
)
from src.rag.retriever import search_with_scores
from src.tools.web_search import web_search, format_web_context


def build_context_and_citations(documents: list) -> tuple[str, list[dict[str, str]]]:
    """Build prompt context and citation metadata from retrieved documents."""
    context_parts = []
    citations: list[dict[str, str]] = []
    for i, doc in enumerate(documents):
        source = doc.metadata.get("source", "Unknown")
        page = doc.metadata.get("page", "N/A")
        snippet = doc.page_content[:200]
        context_parts.append(
            f"[Source {i + 1}: {source}, Page: {page}]\n{doc.page_content}"
        )
        citations.append({"source": source, "page": page, "snippet": snippet})

    context = "\n\n---\n\n".join(context_parts) if context_parts else "No context available."
    return context, citations


def prepare_retrieval(
    question: str,
    chat_history: list,
    store: Chroma,
) -> dict[str, Any]:
    """Run retrieval + context check and return prepared data.

    This is the fast, synchronous phase — no LLM calls.

    Returns:
        Dict with: route ("generate" | "fallback"), documents, citations,
        context string, recent_history (last 6 messages).
    """
    # Retrieve
    try:
        results = search_with_scores(question, store)
        documents = [doc for doc, _score in results]
    except Exception:
        documents = []

    # Route
    route = "generate" if documents else "fallback"

    # Build citations + context string
    context, citations = build_context_and_citations(documents)
    recent_history = (chat_history or [])[-6:]

    return {
        "route": route,
        "documents": documents,
        "citations": citations,
        "context": context,
        "recent_history": recent_history,
    }


def _stream_rag(
    question: str,
    context: str,
    recent_history: list,
    llm: BaseChatModel,
    callbacks: list | None = None,
) -> Generator[str, None, None]:
    """Yield answer tokens grounded in retrieved context."""
    messages = RAG_SYSTEM_PROMPT.format_messages(
        context=context,
        chat_history=recent_history,
        question=question,
    )
    kwargs = {"config": {"callbacks": callbacks}} if callbacks else {}
    for chunk in llm.stream(messages, **kwargs):
        if chunk.content:
            yield chunk.content


def _stream_fallback(
    question: str,
    recent_history: list,
    llm: BaseChatModel,
    callbacks: list | None = None,
) -> Generator[str, None, None]:
    """Yield answer tokens from general LLM knowledge (no docs found)."""
    messages = FALLBACK_SYSTEM_PROMPT.format_messages(
        chat_history=recent_history,
        question=question,
    )
    kwargs = {"config": {"callbacks": callbacks}} if callbacks else {}
    for chunk in llm.stream(messages, **kwargs):
        if chunk.content:
            yield chunk.content


def _stream_web_search(
    question: str,
    context: str,
    recent_history: list,
    llm: BaseChatModel,
    callbacks: list | None = None,
) -> Generator[str, None, None]:
    """Yield answer tokens grounded in web search results."""
    messages = WEB_SEARCH_PROMPT.format_messages(
        context=context,
        chat_history=recent_history,
        question=question,
    )
    kwargs = {"config": {"callbacks": callbacks}} if callbacks else {}
    for chunk in llm.stream(messages, **kwargs):
        if chunk.content:
            yield chunk.content


def _stream_direct(
    question: str,
    recent_history: list,
    llm: BaseChatModel,
    callbacks: list | None = None,
) -> Generator[str, None, None]:
    """Yield answer tokens from LLM's own knowledge (direct mode)."""
    messages = DIRECT_PROMPT.format_messages(
        chat_history=recent_history,
        question=question,
    )
    kwargs = {"config": {"callbacks": callbacks}} if callbacks else {}
    for chunk in llm.stream(messages, **kwargs):
        if chunk.content:
            yield chunk.content


def stream_rag_from_documents(
    question: str,
    chat_history: list,
    documents: list,
    llm: BaseChatModel,
    callbacks: list | None = None,
) -> tuple[Generator[str, None, None], list[dict]]:
    """Create a RAG token stream directly from already-retrieved documents."""
    recent_history = (chat_history or [])[-6:]
    context, citations = build_context_and_citations(documents)
    gen = _stream_rag(question, context, recent_history, llm, callbacks)
    return gen, citations


def stream_fallback_answer(
    question: str,
    chat_history: list,
    llm: BaseChatModel,
    callbacks: list | None = None,
) -> Generator[str, None, None]:
    """Create a fallback token stream using the fallback prompt."""
    recent_history = (chat_history or [])[-6:]
    return _stream_fallback(question, recent_history, llm, callbacks)


def stream_answer(
    question: str,
    chat_history: list,
    store: Chroma,
    llm: BaseChatModel,
    callbacks: list | None = None,
    rag_enabled: bool = False,
    tools_enabled: bool = False,
) -> tuple[Generator[str, None, None], list[dict], bool, str]:
    """Unified entry point — retrieves, routes, and returns a token stream.

    Routing logic:
        1. If rag_enabled → try RAG retrieval first
           - docs found → RAG answer
           - no docs → fall through to step 2
        2. If tools_enabled → search web with Tavily
           - results found → web-grounded answer
           - no results → fall through to step 3
        3. Direct LLM answer (general knowledge)

    Usage (UI — streaming):
        stream, citations, used_fallback, source = stream_answer(q, hist, store, llm)
        answer = st.write_stream(stream)

    Usage (tests — non-streaming):
        stream, citations, used_fallback, source = stream_answer(q, hist, store, llm)
        answer = "".join(stream)

    Args:
        callbacks: Optional list of LangChain callbacks for observability.
        rag_enabled: If True, attempt ChromaDB retrieval first.
        tools_enabled: If True and RAG has no results, use tools (web search).

    Returns:
        Tuple of (token_generator, citations_list, used_fallback_flag, source_type).
        source_type is one of: "rag", "web", "direct", "fallback".
    """
    recent_history = (chat_history or [])[-6:]

    # ── Step 1: RAG retrieval ──
    if rag_enabled:
        prep = prepare_retrieval(question, chat_history, store)
        if prep["route"] == "generate":
            gen = _stream_rag(
                question, prep["context"], prep["recent_history"], llm, callbacks
            )
            return gen, prep["citations"], False, "rag"

    # ── Step 2: Web search ──
    if tools_enabled:
        results = web_search(question)
        if results:
            context = format_web_context(results)
            citations = [
                {"source": r["url"], "page": "web", "snippet": r["content"][:200]}
                for r in results
            ]
            gen = _stream_web_search(
                question, context, recent_history, llm, callbacks
            )
            return gen, citations, False, "web"

    # ── Step 3: Direct LLM answer ──
    gen = _stream_direct(question, recent_history, llm, callbacks)
    return gen, [], True, "direct"
