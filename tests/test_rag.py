import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'backend', 'data')


def test_load_markdown_files():
    from rag.loader import load_documents
    docs = load_documents(DATA_DIR)
    assert len(docs) >= 2
    assert all(hasattr(d, 'page_content') for d in docs)
    assert all(len(d.page_content) > 0 for d in docs)


def test_loaded_docs_have_source_metadata():
    from rag.loader import load_documents
    docs = load_documents(DATA_DIR)
    assert all('source' in d.metadata for d in docs)


def test_chunk_documents():
    from rag.loader import load_documents
    from rag.chunker import chunk_documents
    docs = load_documents(DATA_DIR)
    chunks = chunk_documents(docs)
    assert len(chunks) >= len(docs)
    assert all(len(c.page_content) <= 600 for c in chunks)


def test_retriever_returns_relevant_chunks(tmp_path):
    from rag.loader import load_documents
    from rag.chunker import chunk_documents
    from rag.retriever import build_retriever
    docs = load_documents(DATA_DIR)
    chunks = chunk_documents(docs)
    retriever = build_retriever(chunks, persist_dir=str(tmp_path))
    results = retriever.invoke("What are the deadlines for Project Alpha?")
    assert len(results) >= 1
    assert any("Alpha" in r.page_content or "milestone" in r.page_content.lower() or "deadline" in r.page_content.lower() for r in results)
