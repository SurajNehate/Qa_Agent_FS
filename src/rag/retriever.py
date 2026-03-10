"""ChromaDB persistent vector store and search."""

import os
from typing import Optional

import chromadb
from langchain_chroma import Chroma
from langchain_core.documents import Document

from src.rag.embeddings import get_embeddings


def get_vector_store(
    persist_dir: Optional[str] = None,
    collection_name: Optional[str] = None,
) -> Chroma:
    """Initialize and return a persistent ChromaDB vector store.

    Args:
        persist_dir: Path to Chroma storage directory. Defaults to env CHROMA_PERSIST_DIR.
        collection_name: Name of the collection. Defaults to env CHROMA_COLLECTION.

    Returns:
        LangChain Chroma wrapper backed by a persistent client.
    """
    persist_dir = persist_dir or os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
    collection_name = collection_name or os.getenv("CHROMA_COLLECTION", "qa_docs")

    client = chromadb.PersistentClient(path=persist_dir)
    embeddings = get_embeddings()

    return Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=embeddings,
    )


def search(
    query: str,
    store: Chroma,
    k: Optional[int] = None,
) -> list[Document]:
    """Run similarity search and return full Document objects with metadata.

    Args:
        query: The search query string.
        store: A Chroma vector store instance.
        k: Number of top results to return. Defaults to env TOP_K.

    Returns:
        List of Document objects with page_content and metadata preserved.
    """
    k = k or int(os.getenv("TOP_K", "4"))
    return store.similarity_search(query, k=k)


def search_with_scores(
    query: str,
    store: Chroma,
    k: Optional[int] = None,
) -> list[tuple[Document, float]]:
    """Run similarity search and return Documents with relevance scores.

    Args:
        query: The search query string.
        store: A Chroma vector store instance.
        k: Number of top results. Defaults to env TOP_K.

    Returns:
        List of (Document, score) tuples. Lower score = more similar.
    """
    k = k or int(os.getenv("TOP_K", "4"))
    return store.similarity_search_with_score(query, k=k)


def clear_collection(store: Chroma) -> None:
    """Delete all documents from the collection."""
    collection = store._collection
    # Get all IDs and delete them
    result = collection.get()
    if result["ids"]:
        collection.delete(ids=result["ids"])
