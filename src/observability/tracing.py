"""Observability — Langfuse + LangSmith callback factory.

Returns a list of LangChain callbacks based on env vars.
Both can be active simultaneously. Returns [] if both disabled (zero overhead).
"""

import os


def get_callbacks(trace_name: str = "qa-rag-agent") -> list:
    """Build and return active tracing callbacks.

    Reads LANGFUSE_ENABLED and LANGSMITH_ENABLED from env.
    Both can run simultaneously for dual-platform tracing.

    Args:
        trace_name: Label for the trace (shown in dashboards).

    Returns:
        List of LangChain callback handlers. Empty if both disabled.
    """
    callbacks = []

    # Langfuse (v3.x reads keys from env vars automatically:
    #   LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST)
    if os.getenv("LANGFUSE_ENABLED", "false").lower() == "true":
        try:
            from langfuse.langchain import CallbackHandler as LangfuseCallback

            # Langfuse v3 reads config from env vars automatically:
            #   LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
            handler = LangfuseCallback()
            callbacks.append(handler)
            print(f"[observability] Langfuse tracing enabled (trace: {trace_name})")
        except ImportError:
            print("[observability] Langfuse package not installed. Run: pip install langfuse")
        except Exception as e:
            print(f"[observability] Langfuse init failed: {e}")

    # LangSmith (activated via env vars, no explicit callback object needed)
    if os.getenv("LANGSMITH_ENABLED", "false").lower() == "true":
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "qa-rag-agent")
        print(f"[observability] LangSmith tracing enabled (project: {os.environ['LANGCHAIN_PROJECT']})")

    return callbacks
