"""Embedding model configuration.

Uses OpenAI text-embedding-3-small for high-accuracy, 1536-dimensional embeddings.
Requires OPENAI_API_KEY environment variable.
"""

import logging
from langchain_openai import OpenAIEmbeddings

logger = logging.getLogger(__name__)

MODEL_NAME = "text-embedding-3-small"


def get_embeddings() -> OpenAIEmbeddings:
    """Return a configured OpenAI embedding model."""
    try:
        return OpenAIEmbeddings(model=MODEL_NAME)
    except Exception as e:
        logger.error("Failed to initialize OpenAI Embeddings: %s", e)
        raise
