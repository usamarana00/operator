import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import agents.github_agent as ga


def test_fetch_github_data_uses_mcp_layer():
    """_fetch_github_data must obtain PRs/issues via the MCP tool functions,
    so the 'GitHub MCP' SSE event reflects a real call."""
    with patch("agents.github_agent.github_mcp_list_prs", return_value=[{"number": 7, "title": "Fix bug", "user": "me"}]) as m_prs, \
         patch("agents.github_agent.github_mcp_list_issues", return_value=[{"number": 3, "title": "Slow load", "state": "open"}]) as m_iss, \
         patch("agents.github_agent.requests.get") as m_get:
        # commits still come from the direct endpoint
        m_get.return_value.status_code = 200
        m_get.return_value.json.return_value = []
        out = ga._fetch_github_data("acme", "paki-portal", "tok")

    m_prs.assert_called_once_with("acme", "paki-portal", token="tok")
    m_iss.assert_called_once_with("acme", "paki-portal", token="tok")
    assert "#7 Fix bug" in out
    assert "#3 Slow load" in out
