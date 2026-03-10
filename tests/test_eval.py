"""Tests for the RAG evaluation module."""

import json
import pytest

from langchain_core.messages import AIMessage

from src.eval.evaluator import EvalResult, evaluate_answer
from src.eval.dataset import EvalCase, load_dataset


class MockEvalLLM:
    """Mock LLM that returns valid JSON evaluation scores."""

    def __init__(self, scores=None):
        self.scores = scores or {
            "faithfulness": 4,
            "relevance": 5,
            "completeness": 3,
            "reasoning": "Mock evaluation: answer is relevant and mostly faithful.",
        }

    def invoke(self, messages, **kwargs):
        return AIMessage(content=json.dumps(self.scores))

    def stream(self, messages, **kwargs):
        content = json.dumps(self.scores)
        yield AIMessage(content=content)


class MockBadEvalLLM:
    """Mock LLM that returns invalid (non-JSON) evaluation response."""

    def invoke(self, messages, **kwargs):
        return AIMessage(content="I cannot evaluate this answer properly.")

    def stream(self, messages, **kwargs):
        yield AIMessage(content="I cannot evaluate this answer properly.")


class TestEvaluator:
    """Tests for evaluate_answer()."""

    def test_evaluate_returns_valid_result(self):
        """evaluate_answer should return an EvalResult with all fields."""
        llm = MockEvalLLM()
        result = evaluate_answer(
            question="What is LangGraph?",
            answer="LangGraph is a framework for building agentic applications.",
            context="LangGraph is a library by LangChain for building stateful agents.",
            llm=llm,
        )

        assert isinstance(result, EvalResult)
        assert result.faithfulness == 4
        assert result.relevance == 5
        assert result.completeness == 3
        assert result.overall == pytest.approx(4.0, abs=0.01)
        assert "Mock evaluation" in result.reasoning

    def test_evaluate_handles_bad_json(self):
        """evaluate_answer should gracefully handle non-JSON responses."""
        llm = MockBadEvalLLM()
        result = evaluate_answer(
            question="What is RAG?",
            answer="RAG is retrieval-augmented generation.",
            context="Some context here.",
            llm=llm,
        )

        assert isinstance(result, EvalResult)
        assert result.faithfulness == 1
        assert result.relevance == 1
        assert result.completeness == 1
        assert "Failed to parse" in result.reasoning

    def test_evaluate_clamps_scores(self):
        """Scores outside 1-5 should be clamped."""
        llm = MockEvalLLM(scores={
            "faithfulness": 10,
            "relevance": 0,
            "completeness": 3,
            "reasoning": "Extreme scores test.",
        })
        result = evaluate_answer(
            question="Test?",
            answer="Test answer.",
            context="Test context.",
            llm=llm,
        )

        assert result.faithfulness == 5  # Clamped from 10
        assert result.relevance == 1     # Clamped from 0
        assert result.completeness == 3

    def test_evaluate_handles_markdown_wrapped_json(self):
        """evaluate_answer should handle ```json ... ``` wrapped responses."""
        class MarkdownLLM:
            def invoke(self, messages, **kwargs):
                return AIMessage(
                    content='```json\n{"faithfulness": 4, "relevance": 4, '
                            '"completeness": 4, "reasoning": "good"}\n```'
                )
        result = evaluate_answer(
            question="Test?", answer="Answer.", context="Context.", llm=MarkdownLLM()
        )
        assert result.faithfulness == 4
        assert result.relevance == 4


class TestDataset:
    """Tests for eval dataset loading."""

    def test_load_valid_dataset(self, tmp_path):
        """Should load and validate a well-formed dataset."""
        dataset = [
            {"question": "What is X?", "expected_keywords": ["X"], "category": "factual"},
            {"question": "How does Y work?"},
        ]
        path = tmp_path / "test_eval.json"
        path.write_text(json.dumps(dataset))

        cases = load_dataset(str(path))
        assert len(cases) == 2
        assert cases[0].question == "What is X?"
        assert cases[0].expected_keywords == ["X"]
        assert cases[1].category == "general"  # Default

    def test_load_missing_file_raises(self):
        """Should raise FileNotFoundError for missing dataset."""
        with pytest.raises(FileNotFoundError):
            load_dataset("nonexistent.json")

    def test_load_invalid_json_structure(self, tmp_path):
        """Should raise ValueError if JSON is not a list."""
        path = tmp_path / "bad.json"
        path.write_text('{"not": "a list"}')

        with pytest.raises(ValueError, match="JSON array"):
            load_dataset(str(path))
