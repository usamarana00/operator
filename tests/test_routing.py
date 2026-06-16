import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from graph.workflow import _route


def test_route_deadline_goes_to_pm():
    assert _route({"intent": "deadline"}) == "pm"


def test_route_repo_goes_to_github():
    assert _route({"intent": "repo"}) == "github"


def test_route_general_goes_to_response():
    assert _route({"intent": "general"}) == "response"


def test_route_both_runs_pm_then_github():
    # "both" must visit BOTH pm and github before response.
    # With pm as entry, the pm->github edge guarantees github runs.
    assert _route({"intent": "both"}) == "pm"


def test_pm_after_both_routes_to_github():
    from graph.workflow import _route_after_pm
    assert _route_after_pm({"intent": "both"}) == "github"
    assert _route_after_pm({"intent": "deadline"}) == "response"
