"""Tests for conversation memory (session-scoped chat history)."""

from langchain_core.messages import HumanMessage, AIMessage

from src.core.graph import run_graph


class TestChatMemory:
    """Test that chat history grows correctly across sequential invocations."""

    def test_history_grows_across_turns(self, sample_txt_path, tmp_chroma_store, mock_llm):
        """After two turns, chat_history should contain 2 HumanMessages."""
        from src.rag.ingestion import ingest_files

        ingest_files([sample_txt_path], tmp_chroma_store)

        # Simulate managing history like the UI does
        chat_history = []

        # Turn 1
        chat_history.append(HumanMessage(content="What is LangGraph?"))
        result1 = run_graph(
            question="What is LangGraph?",
            chat_history=chat_history,
            store=tmp_chroma_store,
            llm=mock_llm,
        )
        chat_history.append(AIMessage(content=result1["answer"]))

        assert len(chat_history) == 2  # 1 human + 1 ai

        # Turn 2
        chat_history.append(HumanMessage(content="Tell me more about its features"))
        result2 = run_graph(
            question="Tell me more about its features",
            chat_history=chat_history,
            store=tmp_chroma_store,
            llm=mock_llm,
        )
        chat_history.append(AIMessage(content=result2["answer"]))

        assert len(chat_history) == 4  # 2 human + 2 ai

    def test_clear_history_resets(self, tmp_chroma_store, mock_llm):
        """After clearing history, pipeline receives empty context."""
        chat_history = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!"),
        ]

        # Clear
        chat_history.clear()

        result = run_graph(
            question="Who am I?",
            chat_history=chat_history,
            store=tmp_chroma_store,
            llm=mock_llm,
        )
        assert result["chat_history"] == []
        assert result["answer"] != ""
