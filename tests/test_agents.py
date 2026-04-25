import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


def test_classify_deadline_intent():
    from agents.planner import classify_intent
    result = classify_intent("What deadlines do I have this week?", [])
    assert result["intent"] in ("deadline", "both")


def test_classify_repo_intent():
    from agents.planner import classify_intent
    result = classify_intent("Show me open PRs for Project Alpha", [])
    assert result["intent"] in ("repo", "both")


def test_classify_both_intent():
    from agents.planner import classify_intent
    result = classify_intent("What's the status of Project Beta repo and its deadline?", [])
    assert result["intent"] in ("both", "deadline", "repo")


def test_classify_general_intent():
    from agents.planner import classify_intent
    result = classify_intent("Hello, what can you do?", [])
    assert result["intent"] == "general"


def test_result_has_entities_key():
    from agents.planner import classify_intent
    result = classify_intent("Check the alpha project deadlines", [])
    assert "entities" in result


def test_pm_agent_returns_deadline_info(tmp_path):
    from rag.loader import load_documents
    from rag.chunker import chunk_documents
    from rag.retriever import build_retriever
    from agents.project_manager import run_pm_agent

    data_dir = os.path.join(os.path.dirname(__file__), '..', 'backend', 'data')
    chroma_dir = str(tmp_path / "chroma")
    docs = load_documents(data_dir)
    chunks = chunk_documents(docs)
    retriever = build_retriever(chunks, persist_dir=chroma_dir)
    result = run_pm_agent("What deadlines are coming up?", retriever, [])
    assert isinstance(result, str)
    assert len(result) > 10


def test_pm_agent_mentions_milestones(tmp_path):
    from rag.loader import load_documents
    from rag.chunker import chunk_documents
    from rag.retriever import build_retriever
    from agents.project_manager import run_pm_agent

    data_dir = os.path.join(os.path.dirname(__file__), '..', 'backend', 'data')
    chroma_dir = str(tmp_path / "chroma")
    docs = load_documents(data_dir)
    chunks = chunk_documents(docs)
    retriever = build_retriever(chunks, persist_dir=chroma_dir)
    result = run_pm_agent("What milestones are due for Project Alpha?", retriever, [])
    assert any(word in result.lower() for word in ("milestone", "deadline", "due", "alpha", "launch"))


def test_github_agent_returns_string():
    from agents.github_agent import run_github_agent
    result = run_github_agent("Show open issues", repo_url=None, history=[])
    assert isinstance(result, str)
    assert len(result) > 0


def test_response_agent_synthesizes():
    from agents.response_agent import run_response_agent
    result = run_response_agent(
        original_message="What's the status of my projects?",
        pm_output="Design Review due 2026-04-28 for Project Alpha.",
        github_output="3 open PRs in alpha repo.",
        history=[],
    )
    assert isinstance(result, str)
    assert len(result) > 20
