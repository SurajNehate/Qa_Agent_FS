"""Shared test fixtures for Q&A RAG Agent tests."""

import os
import shutil
import tempfile

import pytest
import chromadb
from langchain_chroma import Chroma
from langchain_core.messages import AIMessage

from src.rag.embeddings import get_embeddings


@pytest.fixture
def tmp_chroma_store(tmp_path):
    """Create an isolated ChromaDB store for testing.

    Uses tmp_path (pytest-managed) and manual cleanup that handles
    Windows file locking gracefully.
    """
    chroma_dir = str(tmp_path / "chroma_test")
    os.makedirs(chroma_dir, exist_ok=True)

    client = chromadb.PersistentClient(path=chroma_dir)
    embeddings = get_embeddings()
    store = Chroma(
        client=client,
        collection_name="test_collection",
        embedding_function=embeddings,
    )
    yield store

    # Cleanup: ChromaDB keeps files open on Windows, so we
    # need to delete the client reference first and ignore errors
    del store
    del client
    try:
        shutil.rmtree(chroma_dir, ignore_errors=True)
    except Exception:
        pass


@pytest.fixture
def fixtures_dir():
    """Return the path to the test fixtures directory."""
    return os.path.join(os.path.dirname(__file__), "fixtures")


@pytest.fixture
def sample_txt_path(fixtures_dir):
    """Return path to the sample.txt fixture."""
    return os.path.join(fixtures_dir, "sample.txt")


@pytest.fixture
def sample_md_path(fixtures_dir):
    """Return path to the sample.md fixture."""
    return os.path.join(fixtures_dir, "sample.md")


class MockLLM:
    """A minimal mock LLM that returns a fixed response.

    Implements invoke() and stream() for the single code path.
    """

    def __init__(self, response: str = "This is a mock answer about LangGraph."):
        self.response = response

    def invoke(self, messages, **kwargs):
        return AIMessage(content=self.response)

    def stream(self, messages, **kwargs):
        """Yield word-by-word AIMessage chunks, like a real streaming LLM."""
        words = self.response.split(" ")
        for i, word in enumerate(words):
            token = word if i == 0 else " " + word
            yield AIMessage(content=token)


@pytest.fixture
def mock_llm():
    """Return a MockLLM instance."""
    return MockLLM()
