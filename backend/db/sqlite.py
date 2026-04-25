import sqlite3
from typing import Any

DB_PATH = "backend/data/projects.db"


def _connect(path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path: str = DB_PATH) -> None:
    conn = _connect(path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            client TEXT NOT NULL,
            repo_url TEXT,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT (date('now'))
        );
        CREATE TABLE IF NOT EXISTS milestones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            due_date TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES projects(id)
        );
    """)
    _seed(conn)
    conn.commit()
    conn.close()


def _seed(conn: sqlite3.Connection) -> None:
    existing = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    if existing > 0:
        return
    conn.execute("""
        INSERT INTO projects (name, client, repo_url, status)
        VALUES ('Project Alpha', 'Acme Corp', 'https://github.com/usamarana00/Hello-World', 'active')
    """)
    conn.execute("""
        INSERT INTO projects (name, client, repo_url, status)
        VALUES ('Project Beta', 'Globex Inc', 'https://github.com/usamarana00/Hello-World', 'active')
    """)
    conn.execute("""
        INSERT INTO milestones (project_id, title, due_date, completed)
        VALUES (1, 'MVP Launch', '2026-05-01', 0)
    """)
    conn.execute("""
        INSERT INTO milestones (project_id, title, due_date, completed)
        VALUES (1, 'Design Review', '2026-04-28', 0)
    """)
    conn.execute("""
        INSERT INTO milestones (project_id, title, due_date, completed)
        VALUES (2, 'API Integration', '2026-05-10', 0)
    """)


def get_projects(path: str = DB_PATH) -> list[dict[str, Any]]:
    conn = _connect(path)
    rows = conn.execute("SELECT * FROM projects WHERE status = 'active'").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_milestones(path: str = DB_PATH, project_id: int | None = None) -> list[dict[str, Any]]:
    conn = _connect(path)
    if project_id:
        rows = conn.execute(
            "SELECT * FROM milestones WHERE project_id = ? ORDER BY due_date", (project_id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM milestones ORDER BY due_date").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_note(path: str = DB_PATH, project_id: int = 1, content: str = "") -> None:
    conn = _connect(path)
    conn.execute(
        "INSERT INTO notes (project_id, content) VALUES (?, ?)", (project_id, content)
    )
    conn.commit()
    conn.close()


def get_notes(path: str = DB_PATH, project_id: int | None = None) -> list[dict[str, Any]]:
    conn = _connect(path)
    if project_id:
        rows = conn.execute(
            "SELECT * FROM notes WHERE project_id = ? ORDER BY created_at DESC", (project_id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM notes ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]
