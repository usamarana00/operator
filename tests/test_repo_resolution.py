import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from graph.workflow import _resolve_repo_url

PROJECTS = [
    {"name": "Paki Portal", "repo_owner": "acme", "repo_name": "paki-portal"},
    {"name": "Alpha", "repo_owner": "acme", "repo_name": "project-alpha"},
]


def test_resolves_by_project_name():
    assert _resolve_repo_url("Alpha", PROJECTS) == "https://github.com/acme/project-alpha"


def test_resolves_by_repo_slug():
    # "project alpha" does NOT match the name "Alpha", only the slug "project-alpha"
    # (dashes converted to spaces) — isolates the slug-matching branch.
    assert _resolve_repo_url("project alpha", PROJECTS) == "https://github.com/acme/project-alpha"


def test_falls_back_to_first_project():
    assert _resolve_repo_url("", PROJECTS) == "https://github.com/acme/paki-portal"


def test_returns_none_when_no_projects():
    assert _resolve_repo_url("anything", []) is None
