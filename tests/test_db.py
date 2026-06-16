import pytest
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from db.sqlite import init_db, get_projects, get_milestones, add_note, get_notes


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


def test_init_db_creates_tables(db_path):
    projects = get_projects(db_path)
    assert isinstance(projects, list)


def test_get_projects_returns_seeded_data(db_path):
    projects = get_projects(db_path)
    assert len(projects) >= 1
    assert "name" in projects[0]
    assert "client" in projects[0]


def test_get_milestones_for_project(db_path):
    projects = get_projects(db_path)
    project_id = projects[0]["id"]
    milestones = get_milestones(db_path, project_id)
    assert isinstance(milestones, list)


def test_add_and_get_note(db_path):
    projects = get_projects(db_path)
    project_id = projects[0]["id"]
    add_note(db_path, project_id, "Test note content")
    notes = get_notes(db_path, project_id)
    assert any(n["content"] == "Test note content" for n in notes)
