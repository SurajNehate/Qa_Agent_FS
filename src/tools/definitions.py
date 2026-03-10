"""LangGraph tool definitions for the agent.

Tools are defined with the @tool decorator so they can be used with
LangGraph's ToolNode and bind_tools() for LLM-decided tool calling.
"""

from langchain_core.tools import tool

from src.tools.web_search import (
    web_search as _raw_web_search,
    format_web_context,
    is_tavily_configured,
)


@tool
def web_search_tool(query: str) -> str:
    """Search the web for current information about a topic.

    Use this tool when:
    - The user asks about recent events or news
    - The question requires up-to-date information
    - No relevant documents were found in the knowledge base

    Args:
        query: The search query string

    Returns:
        Formatted web search results with source URLs, or a message
        indicating no results were found.
    """
    if not is_tavily_configured():
        return "Web search is not configured (TAVILY_API_KEY not set)."

    results = _raw_web_search(query)
    if not results:
        return "No web search results found for this query."
    return format_web_context(results)


# All tools available to the agent — add new tools here
TOOLS = [web_search_tool]
