import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


def test_workflow_returns_final_response():
    from graph.workflow import run_workflow
    result = run_workflow(
        message="What deadlines do I have this week?",
        session_id="test-session-1",
    )
    assert isinstance(result, str)
    assert len(result) > 10


def test_workflow_handles_general_query():
    from graph.workflow import run_workflow
    result = run_workflow(
        message="Hello, what can you help me with?",
        session_id="test-session-2",
    )
    assert isinstance(result, str)
    assert len(result) > 10
