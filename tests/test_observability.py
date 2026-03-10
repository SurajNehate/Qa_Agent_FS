"""Tests for observability callback factory."""

import os

import pytest


class TestGetCallbacks:
    """Test the get_callbacks() factory."""

    def test_returns_empty_when_both_disabled(self, monkeypatch):
        """With both tracing disabled, should return empty list."""
        monkeypatch.setenv("LANGFUSE_ENABLED", "false")
        monkeypatch.setenv("LANGSMITH_ENABLED", "false")

        from src.observability.tracing import get_callbacks
        callbacks = get_callbacks()
        assert callbacks == []

    def test_langsmith_sets_env_vars(self, monkeypatch):
        """When LangSmith is enabled, should set LANGCHAIN_TRACING_V2."""
        monkeypatch.setenv("LANGSMITH_ENABLED", "true")
        monkeypatch.setenv("LANGCHAIN_API_KEY", "test-key")
        monkeypatch.setenv("LANGFUSE_ENABLED", "false")

        from src.observability.tracing import get_callbacks
        callbacks = get_callbacks()

        assert os.environ.get("LANGCHAIN_TRACING_V2") == "true"
        assert os.environ.get("LANGCHAIN_PROJECT") == "qa-rag-agent"

    def test_custom_project_name(self, monkeypatch):
        """Should use custom project name if set."""
        monkeypatch.setenv("LANGSMITH_ENABLED", "true")
        monkeypatch.setenv("LANGSMITH_PROJECT", "my-custom-project")
        monkeypatch.setenv("LANGFUSE_ENABLED", "false")

        from src.observability.tracing import get_callbacks
        get_callbacks()

        assert os.environ.get("LANGCHAIN_PROJECT") == "my-custom-project"


class TestDebugHelpers:
    """Test debug module helpers."""

    def test_is_debug_disabled_by_default(self, monkeypatch):
        monkeypatch.setenv("LANGGRAPH_DEBUG", "false")
        from src.observability.debug import is_debug_enabled
        assert is_debug_enabled() is False

    def test_is_debug_enabled_when_true(self, monkeypatch):
        monkeypatch.setenv("LANGGRAPH_DEBUG", "true")
        from src.observability.debug import is_debug_enabled
        assert is_debug_enabled() is True
