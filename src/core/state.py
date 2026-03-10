"""Agent state definition for the Q&A RAG graph.

This state flows through all graph nodes. Each version extends it:
- V1: Core fields (question, answer, citations)
- V2: Session and routing fields (session_id, rag_enabled, tools_enabled)
- V5: Tool-calling fields (messages for ReAct loop)
- V6: Human-in-the-loop fields (review_mode, human_approved, human_feedback)
"""

from typing import Optional, TypedDict, Required, NotRequired

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage


class AgentState(TypedDict, total=False):
    """Typed state that flows through all graph nodes.

    Attributes:
        question: The user's current question.
        session_id: Active conversation session UUID (for persistent memory).
        chat_history: Prior HumanMessage/AIMessage pairs for conversation context.
        documents: Retrieved Document objects from the vector store.
        answer: The generated answer string.
        citations: List of source citation dicts [{source, page, snippet}].
        used_fallback: True if the answer was generated without RAG context.
        error: Error message if something went wrong, else None.
        source_type: One of "rag", "web", "direct", "fallback", "rejected".
        rag_enabled: Whether RAG retrieval is enabled.
        tools_enabled: Whether the agent can use tools (web search, etc).
        messages: Message list for tool-calling agent (ReAct loop).
        review_mode: "tool_approval" | "answer_review" | "none".
        requires_review: Whether this response needs human review.
        human_approved: None=pending, True=approved, False=rejected.
        human_feedback: Optional text feedback from human reviewer.
    """

    # V1: Core fields
    question: Required[str]
    session_id: NotRequired[Optional[str]]
    chat_history: NotRequired[list[BaseMessage]]
    documents: NotRequired[list[Document]]
    answer: NotRequired[str]
    citations: NotRequired[list[dict]]
    used_fallback: NotRequired[bool]
    error: NotRequired[Optional[str]]

    # V2: Routing fields
    source_type: NotRequired[str]
    rag_enabled: NotRequired[bool]
    tools_enabled: NotRequired[bool]

    # V5: Tool-calling fields
    messages: NotRequired[list[BaseMessage]]

    # V6: Human-in-the-loop fields
    review_mode: NotRequired[str]
    requires_review: NotRequired[bool]
    human_approved: NotRequired[Optional[bool]]
    human_feedback: NotRequired[Optional[str]]
