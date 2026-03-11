"""Embedding model configuration.

Uses sentence-transformers/all-MiniLM-L6-v2 — no API key needed.
384-dimensional vectors, fast on CPU.

The model is downloaded once from HuggingFace Hub and cached locally.
On subsequent runs it loads from cache. If the network check fails
(e.g. corporate proxy / SSL issues), it falls back to offline mode
automatically.
"""

import logging
import os

from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def get_embeddings() -> HuggingFaceEmbeddings:
    """Return a configured HuggingFace embedding model.

    Tries online first (checks for updates), then falls back to
    offline/cached mode if network is unavailable or SSL fails.
    """
    try:
        return HuggingFaceEmbeddings(
            model_name=MODEL_NAME,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    except Exception as e:
        logger.warning(
            "Online embedding load failed (%s). Retrying in offline mode...", e
        )
        # Force HuggingFace Hub to use only local cache
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        return HuggingFaceEmbeddings(
            model_name=MODEL_NAME,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
