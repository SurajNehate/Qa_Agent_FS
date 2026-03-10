"""LangGraph debug helpers — verbose logging + graph PNG export."""

import os


def enable_debug() -> None:
    """Enable verbose LangGraph debug logging to stdout."""
    try:
        import logging

        logging.getLogger("langgraph").setLevel(logging.DEBUG)
        print("[debug] LangGraph verbose logging enabled")
    except Exception as e:
        print(f"[debug] Could not enable LangGraph debug: {e}")


def is_debug_enabled() -> bool:
    """Check if LANGGRAPH_DEBUG=true in env."""
    return os.getenv("LANGGRAPH_DEBUG", "false").lower() == "true"


def export_graph_png(compiled_graph, path: str = "docs/graph.png") -> bool:
    """Export compiled graph topology as PNG.

    Returns True when export succeeds, otherwise False.
    """
    try:
        png_bytes = compiled_graph.get_graph().draw_mermaid_png()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(png_bytes)
        print(f"[debug] Graph PNG exported to {path}")
        return True
    except Exception as e:
        print(f"[debug] Graph PNG export skipped: {e}")
        return False
