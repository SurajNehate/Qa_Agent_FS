"""Tests for vector store retrieval."""

from src.rag.ingestion import ingest_files
from src.rag.retriever import search, search_with_scores


class TestSearch:
    """Test similarity search against indexed documents."""

    def test_search_returns_results(self, sample_txt_path, tmp_chroma_store):
        """After indexing, search should return relevant documents."""
        ingest_files([sample_txt_path], tmp_chroma_store)
        results = search("What is LangGraph?", tmp_chroma_store, k=2)
        assert len(results) > 0
        # The sample text is about LangGraph, so results should contain relevant content
        combined = " ".join(doc.page_content for doc in results)
        assert "LangGraph" in combined

    def test_search_with_scores(self, sample_txt_path, tmp_chroma_store):
        """search_with_scores should return (Document, score) tuples."""
        ingest_files([sample_txt_path], tmp_chroma_store)
        results = search_with_scores("LangGraph features", tmp_chroma_store, k=2)
        assert len(results) > 0
        for doc, score in results:
            assert doc.page_content
            assert isinstance(score, float)

    def test_search_empty_store(self, tmp_chroma_store):
        """Search on an empty store should return empty list."""
        results = search("anything", tmp_chroma_store, k=2)
        assert results == []

    def test_search_preserves_metadata(self, sample_txt_path, tmp_chroma_store):
        """Search results should preserve document source metadata."""
        ingest_files([sample_txt_path], tmp_chroma_store)
        results = search("LangGraph", tmp_chroma_store, k=1)
        assert len(results) > 0
        assert "source" in results[0].metadata
