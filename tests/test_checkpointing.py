"""Tests for graph checkpointing (V7)."""

import os
import pytest

from src.core.checkpointer import get_checkpointer, get_thread_config


class TestCheckpointerFactory:
    """Test the checkpointer factory."""

    def test_memory_saver_for_tests(self):
        """MemorySaver should be returned when use_sqlite=False."""
        from langgraph.checkpoint.memory import MemorySaver

        cp = get_checkpointer(use_sqlite=False)
        assert isinstance(cp, MemorySaver)

    def test_memory_saver_is_different_instances(self):
        """Each call should return a fresh MemorySaver."""
        cp1 = get_checkpointer(use_sqlite=False)
        cp2 = get_checkpointer(use_sqlite=False)
        assert cp1 is not cp2

    def test_thread_config_structure(self):
        """get_thread_config should return proper config dict."""
        config = get_thread_config("test-thread-123")
        assert config == {"configurable": {"thread_id": "test-thread-123"}}

    def test_thread_config_with_different_ids(self):
        """Different thread IDs should produce different configs."""
        c1 = get_thread_config("thread-a")
        c2 = get_thread_config("thread-b")
        assert c1["configurable"]["thread_id"] != c2["configurable"]["thread_id"]


class TestGraphWithCheckpointer:
    """Test graph compilation with checkpointer."""

    def test_graph_compiles_with_memory_saver(self):
        """Graph should compile successfully with MemorySaver."""
        from src.core.graph import build_graph

        cp = get_checkpointer(use_sqlite=False)
        graph = build_graph(checkpointer=cp)
        assert graph is not None

    def test_graph_compiles_without_checkpointer(self):
        """Graph should compile without any checkpointer."""
        from src.core.graph import build_graph

        graph = build_graph(checkpointer=None)
        assert graph is not None

    def test_graph_compiles_with_interrupt_before(self):
        """Graph should compile with interrupt_before nodes."""
        from src.core.graph import build_graph

        cp = get_checkpointer(use_sqlite=False)
        graph = build_graph(
            checkpointer=cp,
            interrupt_before=["tools"],
        )
        assert graph is not None
