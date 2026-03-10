"""Tests for human-in-the-loop review (V6)."""

import pytest

from src.core.graph import _human_review_node


class TestHumanReview:
    """Test the human review node logic."""

    def test_approved_passes_through(self):
        """When human_approved=True, state should pass through unchanged."""
        state = {
            "question": "What is LangGraph?",
            "answer": "LangGraph is a framework.",
            "human_approved": True,
            "source_type": "rag",
        }
        result = _human_review_node(state)
        assert result["answer"] == "LangGraph is a framework."
        assert result["source_type"] == "rag"

    def test_pending_passes_through(self):
        """When human_approved is None (pending), state should pass through."""
        state = {
            "question": "What is LangGraph?",
            "answer": "LangGraph is a framework.",
            "human_approved": None,
        }
        result = _human_review_node(state)
        assert result["answer"] == "LangGraph is a framework."

    def test_rejected_overrides_answer(self):
        """When human_approved=False, answer should be replaced with rejection."""
        state = {
            "question": "What is LangGraph?",
            "answer": "Original answer.",
            "human_approved": False,
            "human_feedback": "This answer is incorrect.",
            "source_type": "rag",
        }
        result = _human_review_node(state)
        assert "rejected by reviewer" in result["answer"].lower()
        assert "This answer is incorrect" in result["answer"]
        assert result["source_type"] == "rejected"
        assert result["used_fallback"] is True

    def test_rejected_without_feedback(self):
        """Rejection without feedback should still work."""
        state = {
            "question": "Test?",
            "answer": "Original.",
            "human_approved": False,
        }
        result = _human_review_node(state)
        assert "rejected by reviewer" in result["answer"].lower()

    def test_no_review_fields_passes_through(self):
        """State without review fields should pass through unchanged."""
        state = {
            "question": "What is LangGraph?",
            "answer": "LangGraph is a framework.",
        }
        result = _human_review_node(state)
        assert result["answer"] == "LangGraph is a framework."
