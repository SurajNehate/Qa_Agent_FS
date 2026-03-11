"""Document loading, chunking, and indexing into ChromaDB."""

import os
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredMarkdownLoader,
    Docx2txtLoader,
)

from src.rag.retriever import clear_collection

# Map file extensions to their LangChain loader classes
LOADER_MAP: dict[str, type] = {
    ".pdf": PyPDFLoader,
    ".txt": TextLoader,
    ".md": UnstructuredMarkdownLoader,
    ".docx": Docx2txtLoader,
}

SUPPORTED_EXTENSIONS = set(LOADER_MAP.keys())


def _get_loader(file_path: str):
    """Select the appropriate loader based on file extension.

    Args:
        file_path: Path to the file to load.

    Returns:
        An instantiated LangChain document loader.

    Raises:
        ValueError: If the file extension is not supported.
    """
    ext = Path(file_path).suffix.lower()
    if ext not in LOADER_MAP:
        raise ValueError(
            f"Unsupported file type '{ext}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    loader_cls = LOADER_MAP[ext]
    return loader_cls(file_path)


def _get_splitter() -> RecursiveCharacterTextSplitter:
    """Return a configured text splitter with sane defaults."""
    return RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        length_function=len,
    )


def load_and_chunk(file_path: str, original_name: str | None = None) -> list[Document]:
    """Load a single file and split it into chunks.

    Args:
        file_path: Path to the document file.
        original_name: Original filename (used when file_path is a temp path).

    Returns:
        List of chunked Document objects with metadata including 'source'.
    """
    loader = _get_loader(file_path)
    documents = loader.load()

    # Use original filename if provided, otherwise basename of file_path
    display_name = original_name or os.path.basename(file_path)

    # Ensure every document has a readable source in metadata
    for doc in documents:
        doc.metadata["source"] = display_name
        # Ensure page number is a string for display
        if "page" in doc.metadata:
            doc.metadata["page"] = str(int(doc.metadata["page"]) + 1)  # 0-indexed → 1-indexed

    splitter = _get_splitter()
    chunks = splitter.split_documents(documents)

    # Propagate source to all chunks
    for chunk in chunks:
        if "source" not in chunk.metadata:
            chunk.metadata["source"] = display_name

    return chunks


def ingest_files(
    file_paths: list[str],
    store: Chroma,
    original_names: list[str] | None = None,
) -> dict:
    """Load, chunk, and index multiple files into the vector store.

    Args:
        file_paths: List of file paths to ingest.
        store: A Chroma vector store instance.
        original_names: Optional list of original filenames (same order as file_paths).

    Returns:
        Dict with 'files' count and 'chunks' count.
    """
    all_chunks: list[Document] = []
    names = original_names or [None] * len(file_paths)

    for path, name in zip(file_paths, names):
        chunks = load_and_chunk(path, original_name=name)
        all_chunks.extend(chunks)

    if all_chunks:
        store.add_documents(all_chunks)

    return {"files": len(file_paths), "chunks": len(all_chunks)}


def reindex(
    file_paths: list[str],
    store: Chroma,
    original_names: list[str] | None = None,
) -> dict:
    """Clear the collection and re-ingest files from scratch.

    Args:
        file_paths: List of file paths to ingest.
        store: A Chroma vector store instance.
        original_names: Optional list of original filenames.

    Returns:
        Dict with 'files' count and 'chunks' count.
    """
    clear_collection(store)
    return ingest_files(file_paths, store, original_names=original_names)
