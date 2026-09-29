import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from agents.planner import classify_intent


def _fake_llm_response(content: str):
    msg = MagicMock()
    msg.content = content
    return msg


def test_classify_intent_handles_bad_json():
    with patch("agents.planner._PROMPT") as prompt:
        chain = MagicMock()
        chain.invoke.return_value = _fake_llm_response("not json at all")
        prompt.__or__.return_value = chain
        result = classify_intent("hello", [])
        assert result["intent"] == "general"


def test_classify_intent_extracts_valid_intent():
    with patch("agents.planner._PROMPT") as prompt:
        chain = MagicMock()
        chain.invoke.return_value = _fake_llm_response(
            '{"intent": "repo", "entities": {"project": "Alpha", "repo": null}}'
        )
        prompt.__or__.return_value = chain
        result = classify_intent("show PRs for Alpha", [])
        assert result["intent"] == "repo"
        assert result["entities"]["project"] == "Alpha"


def test_classify_intent_rejects_unknown_intent():
    with patch("agents.planner._PROMPT") as prompt:
        chain = MagicMock()
        chain.invoke.return_value = _fake_llm_response('{"intent": "banana", "entities": {}}')
        prompt.__or__.return_value = chain
        result = classify_intent("???", [])
        assert result["intent"] == "general"
