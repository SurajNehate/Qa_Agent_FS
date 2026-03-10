"""Q&A RAG pipeline with tool-calling, human-in-the-loop, and checkpointing.

This module provides:
1. build_graph()  - creates a LangGraph StateGraph (V1-V7 features)
2. run_graph()    - thin wrapper for programmatic/test execution

Version history:
- V1: Basic RAG pipeline (retrieve → generate | fallback)
- V3: mode_router entry point with conditional routing
- V5: ToolNode + bind_tools for LLM-decided tool calling
- V6: interrupt_before for human-in-the-loop review
- V7: SqliteSaver checkpointing for time-travel debugging
"""

from langchain_chroma import Chroma
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import END, StateGraph

from src.core.nodes import (
    prepare_retrieval,
    stream_answer,
    stream_fallback_answer,
    stream_rag_from_documents,
)
from src.core.prompts import WEB_SEARCH_PROMPT
from src.core.state import AgentState
from src.tools.web_search import format_web_context, web_search


# ---------------------------------------------------------------------------
# Graph node functions
# ---------------------------------------------------------------------------

def _mode_router_node(state: AgentState) -> AgentState:
    """Graph node: pass-through node used for explicit mode routing."""
    return state


def _mode_route(state: AgentState) -> str:
    """Route by high-level mode before retrieval."""
    if state.get("rag_enabled", False):
        return "retrieve"
    if state.get("tools_enabled", False):
        return "agent"
    return "fallback"


def _retrieve_node(state: AgentState) -> AgentState:
    """Graph node: retrieve documents from ChromaDB."""
    from src.rag.retriever import get_vector_store

    store = get_vector_store()
    prep = prepare_retrieval(
        question=state["question"],
        chat_history=state.get("chat_history", []),
        store=store,
    )
    return {
        **state,
        "documents": prep["documents"],
        "citations": prep["citations"],
    }


def _route_node(state: AgentState) -> str:
    """Graph node: decide whether to generate, use agent, or fallback."""
    if state.get("documents"):
        return "generate"
    if state.get("tools_enabled", False):
        return "agent"
    return "fallback"


def _generate_node(state: AgentState) -> AgentState:
    """Graph node: generate answer grounded in retrieved documents."""
    from src.llm.provider import LLMConfig, get_llm

    llm = get_llm(LLMConfig())
    token_stream, citations = stream_rag_from_documents(
        question=state["question"],
        chat_history=state.get("chat_history", []),
        documents=state.get("documents", []),
        llm=llm,
    )
    answer = "".join(token_stream)
    return {
        **state,
        "answer": answer,
        "citations": citations,
        "used_fallback": False,
        "source_type": "rag",
        "error": None,
    }


def _web_search_node(state: AgentState) -> AgentState:
    """Graph node: generate answer grounded in web search results."""
    from src.llm.provider import LLMConfig, get_llm

    llm = get_llm(LLMConfig())
    results = web_search(state["question"])
    recent_history = (state.get("chat_history", []) or [])[-6:]

    if not results:
        token_stream = stream_fallback_answer(
            question=state["question"],
            chat_history=recent_history,
            llm=llm,
        )
        return {
            **state,
            "answer": "".join(token_stream),
            "citations": [],
            "used_fallback": True,
            "source_type": "fallback",
            "error": None,
        }

    context = format_web_context(results)
    messages = WEB_SEARCH_PROMPT.format_messages(
        context=context,
        chat_history=recent_history,
        question=state["question"],
    )
    tokens = []
    for chunk in llm.stream(messages):
        if chunk.content:
            tokens.append(chunk.content)

    citations = [
        {"source": r["url"], "page": "web", "snippet": r["content"][:200]}
        for r in results
    ]
    return {
        **state,
        "answer": "".join(tokens),
        "citations": citations,
        "used_fallback": False,
        "source_type": "web",
        "error": None,
    }


def _fallback_node(state: AgentState) -> AgentState:
    """Graph node: answer using fallback prompt (no retrieval context)."""
    from src.llm.provider import LLMConfig, get_llm

    llm = get_llm(LLMConfig())
    token_stream = stream_fallback_answer(
        question=state["question"],
        chat_history=state.get("chat_history", []),
        llm=llm,
    )
    return {
        **state,
        "answer": "".join(token_stream),
        "citations": [],
        "used_fallback": True,
        "source_type": "fallback",
        "error": None,
    }


# ---------------------------------------------------------------------------
# V5: Tool-calling agent node
# ---------------------------------------------------------------------------

def _agent_node(state: AgentState) -> AgentState:
    """Graph node: LLM decides whether to call tools or respond directly.

    Uses bind_tools() so the LLM can choose to invoke web_search_tool
    (or any other tool in TOOLS) based on the question.
    """
    from src.llm.provider import LLMConfig, get_llm
    from src.tools.definitions import TOOLS

    llm = get_llm(LLMConfig())

    try:
        llm_with_tools = llm.bind_tools(TOOLS)
    except (AttributeError, NotImplementedError):
        # Fallback for LLMs that don't support tool binding (e.g., some Ollama models)
        return _web_search_node(state)

    msgs = state.get("messages", [])
    if not msgs:
        msgs = [HumanMessage(content=state["question"])]

    response = llm_with_tools.invoke(msgs)
    updated_messages = msgs + [response]

    # If the LLM responded with text (no tool call), extract the answer
    if not getattr(response, "tool_calls", None):
        return {
            **state,
            "messages": updated_messages,
            "answer": response.content,
            "citations": [],
            "used_fallback": False,
            "source_type": "web",
            "error": None,
        }

    return {**state, "messages": updated_messages}


def _agent_should_continue(state: AgentState) -> str:
    """Decide if agent should call tools or finish."""
    msgs = state.get("messages", [])
    if not msgs:
        return "end"

    last_message = msgs[-1]
    if getattr(last_message, "tool_calls", None):
        return "tools"
    return "end"


# ---------------------------------------------------------------------------
# V6: Human-in-the-loop review node
# ---------------------------------------------------------------------------

def _human_review_node(state: AgentState) -> AgentState:
    """Graph node: process human review decision.

    If approved or no review needed: pass through.
    If rejected: override answer with rejection message.
    """
    if state.get("human_approved") is False:
        feedback = state.get("human_feedback", "")
        return {
            **state,
            "answer": f"Answer rejected by reviewer. {feedback}".strip(),
            "used_fallback": True,
            "source_type": "rejected",
        }
    return state


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_graph(
    checkpointer=None,
    interrupt_before: list[str] | None = None,
) -> StateGraph:
    """Build the LangGraph StateGraph for the Q&A RAG agent.

    Graph structure (V7):
        mode_router → retrieve|agent|fallback
        retrieve → generate|agent|fallback
        agent → tools|end (ReAct loop)
        generate → human_review → END
        answer nodes → END

    Args:
        checkpointer: LangGraph checkpointer for state persistence.
                      None = no checkpointing. Use get_checkpointer() for production.
        interrupt_before: List of node names to pause before (for human-in-the-loop).
                         Example: ["tools"] to review tool calls before execution.

    Returns:
        Compiled StateGraph.
    """
    from langgraph.prebuilt import ToolNode
    from src.tools.definitions import TOOLS

    graph = StateGraph(AgentState)

    # Core nodes
    graph.add_node("mode_router", _mode_router_node)
    graph.add_node("retrieve", _retrieve_node)
    graph.add_node("generate", _generate_node)
    graph.add_node("fallback", _fallback_node)

    # V5: Tool-calling nodes
    graph.add_node("agent", _agent_node)
    graph.add_node("tools", ToolNode(TOOLS))

    # V6: Human review node
    graph.add_node("human_review", _human_review_node)

    # Entry routing
    graph.set_entry_point("mode_router")

    graph.add_conditional_edges(
        "mode_router",
        _mode_route,
        {
            "retrieve": "retrieve",
            "agent": "agent",
            "fallback": "fallback",
        },
    )

    # Post-retrieval routing
    graph.add_conditional_edges(
        "retrieve",
        _route_node,
        {
            "generate": "generate",
            "agent": "agent",
            "fallback": "fallback",
        },
    )

    # V5: ReAct loop — agent decides to call tools or finish
    graph.add_conditional_edges(
        "agent",
        _agent_should_continue,
        {
            "tools": "tools",
            "end": END,
        },
    )
    graph.add_edge("tools", "agent")  # After tool execution, back to agent

    # V6: Generate goes through human review before ending
    graph.add_edge("generate", "human_review")
    graph.add_edge("human_review", END)

    # Terminal edges for other paths
    graph.add_edge("fallback", END)

    # Compile with optional checkpointer and interrupt points
    compile_kwargs = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer
    if interrupt_before:
        compile_kwargs["interrupt_before"] = interrupt_before

    return graph.compile(**compile_kwargs)


def create_graph():
    """Zero-argument graph factory for ``langgraph dev`` server.

    The LangGraph dev server inspects the factory signature and only
    allows ``ServerRuntime`` or ``RunnableConfig`` parameters.
    This wrapper calls ``build_graph()`` with defaults so the dev
    server can load the graph without issues.
    """
    return build_graph()



# ---------------------------------------------------------------------------
# Simple wrapper for programmatic/test use
# ---------------------------------------------------------------------------

def run_graph(
    question: str,
    chat_history: list[BaseMessage] | None,
    store: Chroma,
    llm: BaseChatModel,
    rag_enabled: bool = True,
    tools_enabled: bool = False,
    callbacks: list | None = None,
) -> AgentState:
    """Run the Q&A pipeline and return a collected non-streaming result.

    Args:
        rag_enabled: If True, attempt RAG retrieval. Default True for
                     programmatic use (tests, eval, CLI).
        tools_enabled: If True, agent can use tools (web search, etc.).
        callbacks: Optional list of LangChain callbacks for observability.
    """
    chat_history = chat_history or []

    try:
        token_stream, citations, used_fallback, source_type = stream_answer(
            question=question,
            chat_history=chat_history,
            store=store,
            llm=llm,
            callbacks=callbacks,
            rag_enabled=rag_enabled,
            tools_enabled=tools_enabled,
        )
        answer = "".join(token_stream)

        return {
            "question": question,
            "chat_history": chat_history,
            "documents": [],
            "answer": answer,
            "citations": citations,
            "used_fallback": used_fallback,
            "source_type": source_type,
            "error": None,
        }
    except Exception as e:
        return {
            "question": question,
            "chat_history": chat_history,
            "documents": [],
            "answer": "",
            "citations": [],
            "used_fallback": False,
            "error": str(e),
        }
