import json
import os
import re
import shutil
from pathlib import Path

import requests
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/setup", tags=["setup"])

_BASE = Path(__file__).parent.parent
DATA_DIR = _BASE / "data"
PROJECTS_DIR = DATA_DIR / "projects"
CLIENTS_DIR = DATA_DIR / "clients"
DB_PATH = str(DATA_DIR / "projects.db")
CHROMA_DIR = str(DATA_DIR / "chroma_db")


# ── Models ────────────────────────────────────────────────────────────────────

class MilestoneInput(BaseModel):
    title: str
    due_date: str


class ProjectInput(BaseModel):
    name: str
    client: str
    repo_url: str
    milestones: list[MilestoneInput] = []


class SetupRequest(BaseModel):
    projects: list[ProjectInput]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sse(event_type: str, content: str) -> str:
    return f"data: {json.dumps({'type': event_type, 'content': content})}\n\n"


def _github_headers() -> dict:
    token = os.getenv("GITHUB_TOKEN", "")
    h = {"User-Agent": "freelance-agent"}
    if token:
        h["Authorization"] = f"token {token}"
    return h


def _fetch_readme(owner: str, repo: str) -> str:
    r = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/readme",
        headers={**_github_headers(), "Accept": "application/vnd.github.raw"},
        timeout=10,
    )
    return r.text[:3000] if r.status_code == 200 else ""


def _fetch_commits(owner: str, repo: str) -> list[str]:
    r = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=10",
        headers=_github_headers(),
        timeout=10,
    )
    if r.status_code != 200:
        return []
    lines = []
    for c in r.json():
        if isinstance(c, dict) and "commit" in c:
            msg = c["commit"]["message"].split("\n")[0]
            date = c["commit"]["author"]["date"][:10]
            lines.append(f"- {date}: {msg}")
    return lines


def _write_project_doc(proj: ProjectInput, readme: str, commits: list[str]) -> None:
    repo_name = proj.repo_url.rstrip("/").split("/")[-1]
    lines = [
        f"# {proj.name} — {proj.client}",
        "",
        f"Repository: {proj.repo_url}",
        "",
        "## Overview",
    ]
    if readme:
        first_para = readme.strip().split("\n\n")[0]
        first_para = re.sub(r"^#+\s*", "", first_para, flags=re.MULTILINE).strip()
        lines.append(first_para[:500])
    else:
        lines.append("No README available.")

    if proj.milestones:
        lines += ["", "## Milestones"]
        for m in proj.milestones:
            lines.append(f"- **{m.title}** — {m.due_date}")

    if commits:
        lines += ["", "## Recent Commits"]
        lines.extend(commits[:10])

    lines += ["", f"## Client\n{proj.client}", ""]

    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    (PROJECTS_DIR / f"{repo_name}.md").write_text("\n".join(lines), encoding="utf-8")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/keys")
def key_status():
    """Returns which API keys are present in .env (values never exposed)."""
    return {
        "openai": bool(os.getenv("OPENAI_API_KEY", "").strip()),
        "github": bool(os.getenv("GITHUB_TOKEN", "").strip()),
        "tavily": bool(os.getenv("TAVILY_API_KEY", "").strip()),
    }


@router.get("/status")
def setup_status():
    """Returns whether the app has been configured (has at least one project)."""
    db = Path(DB_PATH)
    if not db.exists():
        return {"configured": False}
    try:
        import sys
        sys.path.insert(0, str(_BASE))
        from db.sqlite import init_db, get_projects
        init_db(DB_PATH)
        projects = get_projects(DB_PATH)
        return {"configured": len(projects) > 0}
    except Exception:
        return {"configured": False}


@router.get("/repos")
def list_repos():
    """Fetch the authenticated user's GitHub repos using GITHUB_TOKEN from .env."""
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        return {"error": "GITHUB_TOKEN not set in .env", "repos": []}

    headers = _github_headers()

    # Get user info
    user_r = requests.get("https://api.github.com/user", headers=headers, timeout=10)
    if user_r.status_code != 200:
        return {"error": f"GitHub auth failed ({user_r.status_code})", "repos": []}
    user = user_r.json()

    # Paginate repos
    repos = []
    page = 1
    while True:
        r = requests.get(
            f"https://api.github.com/user/repos?sort=updated&per_page=50&page={page}&affiliation=owner,collaborator",
            headers=headers,
            timeout=10,
        )
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 50:
            break
        page += 1

    return {
        "user": {"login": user["login"], "name": user.get("name", "")},
        "repos": [
            {
                "full_name": rp["full_name"],
                "html_url": rp["html_url"],
                "private": rp["private"],
                "description": rp.get("description") or "",
                "updated_at": rp.get("updated_at", "")[:10],
            }
            for rp in repos
        ],
    }


@router.post("/complete")
async def complete_setup(req: SetupRequest):
    """SSE stream: fetch READMEs, write docs, seed SQLite, build ChromaDB."""

    async def _stream():
        import sys
        sys.path.insert(0, str(_BASE))

        yield _sse("progress", f"Starting setup for {len(req.projects)} project(s)...")

        # Fetch GitHub data and write project docs
        for proj in req.projects:
            parts = proj.repo_url.rstrip("/").split("/")
            owner, repo_name = parts[-2], parts[-1]

            yield _sse("progress", f"Fetching README for {owner}/{repo_name}...")
            readme = _fetch_readme(owner, repo_name)

            yield _sse("progress", f"Fetching recent commits for {owner}/{repo_name}...")
            commits = _fetch_commits(owner, repo_name)

            yield _sse("progress", f"Writing project document for {proj.name}...")
            _write_project_doc(proj, readme, commits)

        # Seed SQLite
        yield _sse("progress", "Seeding SQLite database...")
        from db.sqlite import init_db, _connect

        if Path(DB_PATH).exists():
            Path(DB_PATH).unlink()
        init_db(DB_PATH)

        conn = _connect(DB_PATH)
        for proj in req.projects:
            cur = conn.execute(
                "INSERT INTO projects (name, client, repo_url, status) VALUES (?, ?, ?, 'active')",
                (proj.name, proj.client, proj.repo_url),
            )
            project_id = cur.lastrowid
            for m in proj.milestones:
                conn.execute(
                    "INSERT INTO milestones (project_id, title, due_date) VALUES (?, ?, ?)",
                    (project_id, m.title, m.due_date),
                )
        conn.commit()
        conn.close()
        yield _sse("progress", f"SQLite seeded — {len(req.projects)} project(s) saved")

        # Build ChromaDB
        yield _sse("progress", "Building vector index (ChromaDB)...")
        if Path(CHROMA_DIR).exists():
            shutil.rmtree(CHROMA_DIR)

        from rag.loader import load_documents
        from rag.chunker import chunk_documents
        from rag.retriever import build_retriever

        docs = load_documents(str(DATA_DIR))
        chunks = chunk_documents(docs)
        build_retriever(chunks, persist_dir=CHROMA_DIR)
        yield _sse("progress", f"ChromaDB ready — {len(chunks)} chunks indexed from {len(docs)} document(s)")

        yield _sse("done", "Setup complete")

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )
