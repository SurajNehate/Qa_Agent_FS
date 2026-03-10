"""Tavily web search integration."""

import os


def is_tavily_configured() -> bool:
    """Check if Tavily API key is set."""
    return bool(os.getenv("TAVILY_API_KEY"))


def web_search(query: str, max_results: int = 3) -> list[dict]:
    """Search the web using Tavily API.

    Returns empty list if Tavily is not configured or the call fails.
    """
    if not is_tavily_configured():
        return []

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
        response = client.search(query=query, max_results=max_results)

        results = []
        for item in response.get("results", []):
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                }
            )
        return results
    except Exception as e:
        print(f"[web_search] Tavily search failed: {e}")
        return []


def format_web_context(results: list[dict]) -> str:
    """Format web search results into a context string for the LLM."""
    if not results:
        return "No web search results found."

    parts = []
    for i, r in enumerate(results):
        parts.append(
            f"[Web Source {i + 1}: {r['title']}]\n"
            f"URL: {r['url']}\n"
            f"{r['content']}"
        )
    return "\n\n---\n\n".join(parts)

