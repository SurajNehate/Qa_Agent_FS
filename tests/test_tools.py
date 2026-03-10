"""Tests for LangGraph tool-calling (V5)."""

import pytest

from src.tools.definitions import web_search_tool, TOOLS
from src.core.graph import _agent_should_continue, _mode_route


class TestToolDefinitions:
    """Test that tool definitions are properly structured."""

    def test_web_search_tool_has_name(self):
        """Tool should have a descriptive name."""
        assert web_search_tool.name == "web_search_tool"

    def test_web_search_tool_has_description(self):
        """Tool should have a docstring for LLM guidance."""
        assert "Search the web" in web_search_tool.description

    def test_web_search_tool_has_args_schema(self):
        """Tool should define input schema."""
        schema = web_search_tool.args_schema
        assert schema is not None
        # Should have a 'query' field
        fields = schema.model_fields
        assert "query" in fields

    def test_tools_list_is_not_empty(self):
        """TOOLS list should contain at least web_search_tool."""
        assert len(TOOLS) >= 1
        assert web_search_tool in TOOLS


class TestAgentRouting:
    """Test the agent routing logic."""

    def test_mode_route_to_agent_when_web_enabled(self):
        """With tools_enabled=True and rag_enabled=False, should route to agent."""
        state = {"question": "q", "rag_enabled": False, "tools_enabled": True}
        assert _mode_route(state) == "agent"

    def test_mode_route_to_retrieve_when_rag_enabled(self):
        """With rag_enabled=True, should route to retrieve regardless of web setting."""
        state = {"question": "q", "rag_enabled": True, "tools_enabled": True}
        assert _mode_route(state) == "retrieve"

    def test_mode_route_to_fallback_when_both_disabled(self):
        """With both disabled, should route to fallback."""
        state = {"question": "q", "rag_enabled": False, "tools_enabled": False}
        assert _mode_route(state) == "fallback"

    def test_agent_should_continue_to_end_on_empty_messages(self):
        """With no messages, agent should end."""
        assert _agent_should_continue({"question": "q"}) == "end"

    def test_agent_should_continue_to_end_on_text_response(self):
        """When last message has no tool_calls, agent should end."""
        from langchain_core.messages import AIMessage
        state = {"question": "q", "messages": [AIMessage(content="answer")]}
        assert _agent_should_continue(state) == "end"

    def test_agent_should_continue_to_tools_on_tool_call(self):
        """When last message has tool_calls, agent should call tools."""
        from langchain_core.messages import AIMessage

        # Simulate a message with tool_calls
        msg = AIMessage(content="", tool_calls=[{
            "id": "call_1",
            "name": "web_search_tool",
            "args": {"query": "test"},
        }])
        state = {"question": "q", "messages": [msg]}
        assert _agent_should_continue(state) == "tools"

