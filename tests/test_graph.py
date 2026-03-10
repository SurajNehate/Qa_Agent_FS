"""Tests for the Q&A agent pipeline."""

from src.rag.ingestion import ingest_files
from src.core.graph import run_graph, _mode_route, _route_node
from src.core.nodes import stream_answer


class TestWithDocs:
    """Test pipeline when documents are indexed (RAG path)."""

    def test_generate_answer_with_docs(self, sample_txt_path, tmp_chroma_store, mock_llm):
        """With indexed docs, pipeline should produce an answer with citations."""
        ingest_files([sample_txt_path], tmp_chroma_store)
        result = run_graph(
            question="What is LangGraph?",
            chat_history=[],
            store=tmp_chroma_store,
            llm=mock_llm,
        )

        assert result["answer"] != ""
        assert result["used_fallback"] is False
        assert len(result["citations"]) > 0
        assert result["error"] is None

    def test_citations_have_source(self, sample_txt_path, tmp_chroma_store, mock_llm):
        """Citations should include source filename."""
        ingest_files([sample_txt_path], tmp_chroma_store)
        result = run_graph(
            question="What is LangGraph?",
            chat_history=[],
            store=tmp_chroma_store,
            llm=mock_llm,
        )

        for cite in result["citations"]:
            assert "source" in cite
            assert "snippet" in cite


class TestWithoutDocs:
    """Test pipeline when store is empty (fallback path)."""

    def test_fallback_on_empty_store(self, tmp_chroma_store, mock_llm):
        """With no indexed docs, pipeline should use fallback."""
        result = run_graph(
            question="Tell me about quantum computing",
            chat_history=[],
            store=tmp_chroma_store,
            llm=mock_llm,
        )

        assert result["answer"] != ""
        assert result["used_fallback"] is True
        assert result["citations"] == []
        assert result["error"] is None


class TestWithHistory:
    """Test that chat history is passed through."""

    def test_history_is_forwarded(self, sample_txt_path, tmp_chroma_store, mock_llm):
        """Chat history should be preserved in the result."""
        from langchain_core.messages import HumanMessage, AIMessage

        ingest_files([sample_txt_path], tmp_chroma_store)

        history = [
            HumanMessage(content="What is LangGraph?"),
            AIMessage(content="LangGraph is a library for building agentic applications."),
        ]

        result = run_graph(
            question="Tell me more",
            chat_history=history,
            store=tmp_chroma_store,
            llm=mock_llm,
        )
        assert result["answer"] != ""
        assert result["chat_history"] == history


class TestStreamAnswer:
    """Test the unified stream_answer() entry point directly."""

    def test_stream_returns_tokens(self, sample_txt_path, tmp_chroma_store, mock_llm):
        """stream_answer should return a generator that yields tokens."""
        ingest_files([sample_txt_path], tmp_chroma_store)
        token_stream, citations, used_fallback, source_type = stream_answer(
            question="What is LangGraph?",
            chat_history=[],
            store=tmp_chroma_store,
            llm=mock_llm,
            rag_enabled=True,
        )
        answer = "".join(token_stream)
        assert answer != ""
        assert len(citations) > 0
        assert used_fallback is False
        assert source_type == "rag"

    def test_stream_fallback(self, tmp_chroma_store, mock_llm):
        """stream_answer should fallback when store is empty."""
        token_stream, citations, used_fallback, source_type = stream_answer(
            question="Random question",
            chat_history=[],
            store=tmp_chroma_store,
            llm=mock_llm,
        )
        answer = "".join(token_stream)
        assert answer != ""
        assert citations == []
        assert used_fallback is True
        assert source_type == "direct"


class TestGraphRouting:
    """Unit tests for explicit graph routing decisions."""

    def test_mode_route_to_retrieve_when_rag_enabled(self):
        assert _mode_route({"question": "q", "rag_enabled": True}) == "retrieve"

    def test_mode_route_to_agent_when_rag_disabled_and_web_enabled(self):
        assert _mode_route(
            {"question": "q", "rag_enabled": False, "tools_enabled": True}
        ) == "agent"

    def test_mode_route_to_fallback_when_rag_and_web_disabled(self):
        assert _mode_route(
            {"question": "q", "rag_enabled": False, "tools_enabled": False}
        ) == "fallback"

    def test_retrieve_route_to_generate_when_documents_present(self):
        assert _route_node({"question": "q", "documents": ["doc"]}) == "generate"

    def test_retrieve_route_to_agent_when_no_docs_and_web_enabled(self):
        assert _route_node({"question": "q", "documents": [], "tools_enabled": True}) == "agent"

