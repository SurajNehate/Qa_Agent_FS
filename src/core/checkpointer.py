"""Checkpointer factory for LangGraph graph state persistence.

V7 feature: Provides durable checkpointing for time-travel debugging,
crash recovery, and human-in-the-loop interrupt/resume.

Usage:
    checkpointer = get_checkpointer()          # SqliteSaver (production)
    checkpointer = get_checkpointer(False)     # MemorySaver (tests)
"""

import os


def get_checkpointer(use_sqlite: bool = True):
    """Create a checkpointer for the graph.

    Args:
        use_sqlite: If True, use durable SqliteSaver (persists across restarts).
                    If False, use in-memory MemorySaver (for tests).

    Returns:
        A LangGraph-compatible checkpointer instance.
    """
    if use_sqlite:
        from langgraph.checkpoint.sqlite import SqliteSaver

        db_path = os.getenv("CHECKPOINT_DB_PATH", "./data/checkpoints.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        return SqliteSaver.from_conn_string(db_path)

    from langgraph.checkpoint.memory import MemorySaver
    return MemorySaver()


def get_thread_config(thread_id: str) -> dict:
    """Create a LangGraph config dict for thread-based execution.

    Args:
        thread_id: Unique identifier for this conversation thread.

    Returns:
        Config dict suitable for graph.invoke(state, config).
    """
    return {"configurable": {"thread_id": thread_id}}
