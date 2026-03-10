"""Tests for document ingestion: loading, chunking, and indexing."""

import os
import tempfile

import pytest

from src.rag.ingestion import ingest_files, load_and_chunk, reindex, SUPPORTED_EXTENSIONS


class TestLoadAndChunk:
    """Test loading and chunking individual files."""

    def test_load_txt(self, sample_txt_path):
        """TXT files should load and produce chunks with source metadata."""
        chunks = load_and_chunk(sample_txt_path)
        assert len(chunks) > 0
        for chunk in chunks:
            assert "source" in chunk.metadata
            assert chunk.page_content.strip() != ""

    def test_load_md(self, sample_md_path):
        """Markdown files should load and produce chunks with source metadata."""
        chunks = load_and_chunk(sample_md_path)
        assert len(chunks) > 0
        for chunk in chunks:
            assert "source" in chunk.metadata

    def test_unsupported_extension_raises(self, tmp_path):
        """Unsupported extensions should raise ValueError."""
        fake_file = tmp_path / "data.xyz"
        fake_file.write_text("some content")
        with pytest.raises(ValueError, match="Unsupported file type"):
            load_and_chunk(str(fake_file))

    def test_supported_extensions_constant(self):
        """SUPPORTED_EXTENSIONS should include all expected types."""
        assert ".pdf" in SUPPORTED_EXTENSIONS
        assert ".txt" in SUPPORTED_EXTENSIONS
        assert ".md" in SUPPORTED_EXTENSIONS
        assert ".docx" in SUPPORTED_EXTENSIONS


class TestIngestFiles:
    """Test multi-file ingestion into vector store."""

    def test_ingest_txt(self, sample_txt_path, tmp_chroma_store):
        """Ingesting a TXT file should index chunks and return counts."""
        result = ingest_files([sample_txt_path], tmp_chroma_store)
        assert result["files"] == 1
        assert result["chunks"] > 0

    def test_ingest_multiple_files(self, sample_txt_path, sample_md_path, tmp_chroma_store):
        """Ingesting multiple files should sum chunks correctly."""
        result = ingest_files([sample_txt_path, sample_md_path], tmp_chroma_store)
        assert result["files"] == 2
        assert result["chunks"] > 0


class TestReindex:
    """Test reindexing (clear + reingest)."""

    def test_reindex_clears_and_rebuilds(self, sample_txt_path, tmp_chroma_store):
        """Reindex should clear old data and index fresh."""
        # First ingest
        ingest_files([sample_txt_path], tmp_chroma_store)

        # Reindex with same file
        result = reindex([sample_txt_path], tmp_chroma_store)
        assert result["files"] == 1
        assert result["chunks"] > 0
