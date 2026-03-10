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


def load_and_chunk(file_path: str) -> list[Document]:
    """Load a single file and split it into chunks.

    Args:
        file_path: Path to the document file.

    Returns:
        List of chunked Document objects with metadata including 'source'.
    """
    loader = _get_loader(file_path)
    documents = loader.load()

    # Ensure every document has a source in metadata
    for doc in documents:
        if "source" not in doc.metadata:
            doc.metadata["source"] = os.path.basename(file_path)

    splitter = _get_splitter()
    chunks = splitter.split_documents(documents)

    # Propagate source to all chunks
    for chunk in chunks:
        if "source" not in chunk.metadata:
            chunk.metadata["source"] = os.path.basename(file_path)

    return chunks


def ingest_files(file_paths: list[str], store: Chroma) -> dict:
    """Load, chunk, and index multiple files into the vector store.

    Args:
        file_paths: List of file paths to ingest.
        store: A Chroma vector store instance.

    Returns:
        Dict with 'files' count and 'chunks' count.

    Raises:
        ValueError: If any file has an unsupported extension.
    """
    all_chunks: list[Document] = []

    for path in file_paths:
        chunks = load_and_chunk(path)
        all_chunks.extend(chunks)

    if all_chunks:
        store.add_documents(all_chunks)

    return {"files": len(file_paths), "chunks": len(all_chunks)}


def reindex(file_paths: list[str], store: Chroma) -> dict:
    """Clear the collection and re-ingest files from scratch.

    Args:
        file_paths: List of file paths to ingest.
        store: A Chroma vector store instance.

    Returns:
        Dict with 'files' count and 'chunks' count.
    """
    clear_collection(store)
    return ingest_files(file_paths, store)
