"""Modal.com deployment for QA RAG Agent FastAPI.

Deploys the FastAPI REST API as a serverless ASGI app on Modal.com.
ChromaDB data persists across deployments via Modal Volume.
API keys are managed via Modal Secrets.

Setup (one-time):
    pip install modal
    modal token new
    modal secret create qa-rag-agent-secrets \
        OPENAI_API_KEY=sk-... \
        TAVILY_API_KEY=tvly-... \
        LLM_PROVIDER=openai \
        LLM_MODEL=gpt-4o-mini \
        DATABASE_MEMORY_URL=sqlite:///data/memory.db

Deploy:
    modal deploy deploy_modal.py

Dev (hot-reload, temporary URL):
    modal serve deploy_modal.py
"""

import modal

# ---------------------------------------------------------------------------
# Modal resources
# ---------------------------------------------------------------------------

app = modal.App("qa-rag-agent")

# Persistent volume — survives redeployments, stores ChromaDB + SQLite memory
volume = modal.Volume.from_name("qa-rag-agent-data", create_if_missing=True)

# Container image with all Python dependencies
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("build-essential", "curl")
    .pip_install_from_requirements("requirements.txt")
    .env({"PYTHONPATH": "/root"})
    .add_local_dir("src", remote_path="/root/src", copy=True)
)


# ---------------------------------------------------------------------------
# FastAPI ASGI app
# ---------------------------------------------------------------------------

@app.function(
    image=image,
    volumes={"/root/data": volume},
    secrets=[modal.Secret.from_name("qa-rag-agent-secrets")],
    timeout=300,
    scaledown_window=120,
)
@modal.concurrent(max_inputs=10)
@modal.asgi_app()
def fastapi_app():
    """Mount the existing FastAPI app — zero code duplication."""
    import os

    os.chdir("/root")

    # Ensure data directories exist inside the volume
    os.makedirs("/root/data/chroma_db", exist_ok=True)

    from src.api.main import app as _app

    return _app
