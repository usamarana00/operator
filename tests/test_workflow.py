import os
import sys
import asyncio
from unittest.mock import patch, AsyncMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from graph import workflow


def test_general_query_skips_pm_and_github():
    async def run():
        with patch("graph.workflow.classify_intent", return_value={"intent": "general", "entities": {}}), \
             patch("graph.workflow.run_response_agent", return_value="hello there"), \
             patch("graph.workflow.get_projects", new=AsyncMock(return_value=[])), \
             patch("graph.workflow.run_pm_agent", new=AsyncMock(return_value="PM")) as pm, \
             patch("graph.workflow.run_github_agent", return_value="GH") as gh:
            state = {
                "message": "hi", "session_id": "s", "user_id": "u", "github_token": "",
                "history": [], "intent": "", "entities": {},
                "pm_output": "", "github_output": "", "final_response": "",
            }
            result = await workflow._compiled_graph.ainvoke(state)
            return result, pm, gh

    result, pm, gh = asyncio.run(run())
    assert result["final_response"] == "hello there"
    pm.assert_not_called()
    gh.assert_not_called()


def test_both_intent_runs_pm_then_github():
    async def run():
        with patch("graph.workflow.classify_intent", return_value={"intent": "both", "entities": {"project": "Alpha"}}), \
             patch("graph.workflow.run_response_agent", return_value="final"), \
             patch("graph.workflow.get_projects", new=AsyncMock(return_value=[
                 {"name": "Alpha", "repo_owner": "acme", "repo_name": "alpha"}])), \
             patch("graph.workflow.run_pm_agent", new=AsyncMock(return_value="PM")) as pm, \
             patch("graph.workflow.run_github_agent", return_value="GH") as gh:
            state = {
                "message": "status of Alpha", "session_id": "s", "user_id": "u", "github_token": "",
                "history": [], "intent": "", "entities": {},
                "pm_output": "", "github_output": "", "final_response": "",
            }
            await workflow._compiled_graph.ainvoke(state)
            return pm, gh

    pm, gh = asyncio.run(run())
    pm.assert_called_once()
    gh.assert_called_once()
