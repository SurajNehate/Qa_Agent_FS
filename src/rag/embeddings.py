"""Embedding model configuration."""

from langchain_huggingface import HuggingFaceEmbeddings


def get_embeddings() -> HuggingFaceEmbeddings:
    """Return a configured HuggingFace embedding model.

    Uses sentence-transformers/all-MiniLM-L6-v2 — no API key needed.
    384-dimensional vectors, fast on CPU.
    """
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
