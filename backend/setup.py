"""
Freelance Agent — First-time setup
Run: python backend/setup.py

Validates API keys, fetches your GitHub repos, lets you pick which ones
to track, seeds SQLite, generates project markdown docs, and builds the
ChromaDB vector index so the RAG pipeline is ready on first launch.
"""

import os
import sys
import json
import re
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Allow running as `python backend/setup.py` from repo root
sys.path.insert(0, os.path.dirname(__file__))

load_dotenv()

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
PROJECTS_DIR = DATA_DIR / "projects"
CLIENTS_DIR = DATA_DIR / "clients"
DB_PATH = str(DATA_DIR / "projects.db")
CHROMA_DIR = str(DATA_DIR / "chroma_db")

PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
CLIENTS_DIR.mkdir(parents=True, exist_ok=True)
(DATA_DIR / "notes").mkdir(parents=True, exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _hr(char="─", width=60):
    print(char * width)


def _header(text: str):
    _hr()
    print(f"  {text}")
    _hr()


def _ok(text: str):
    print(f"  [OK] {text}")


def _warn(text: str):
    print(f"  [!!] {text}")


def _fail(text: str):
    print(f"  [XX] {text}")
    sys.exit(1)


def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"  {prompt}{suffix}: ").strip()
    return val if val else default


def _ask_yn(prompt: str, default: bool = True) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    val = input(f"  {prompt} {suffix}: ").strip().lower()
    if not val:
        return default
    return val.startswith("y")


# ── Step 1: Validate environment ──────────────────────────────────────────────

def validate_env() -> tuple[str, str]:
    _header("Step 1/5 — Validating environment")

    openai_key = os.getenv("OPENAI_API_KEY", "")
    github_token = os.getenv("GITHUB_TOKEN", "")

    if not openai_key or openai_key.startswith("sk-..."):
        _fail("OPENAI_API_KEY missing or not set in .env")
    _ok(f"OPENAI_API_KEY found (…{openai_key[-6:]})")

    if not github_token or github_token.startswith("ghp_..."):
        _fail("GITHUB_TOKEN missing or not set in .env")
    _ok(f"GITHUB_TOKEN found (…{github_token[-6:]})")

    tavily = os.getenv("TAVILY_API_KEY", "")
    if tavily and not tavily.startswith("tvly-..."):
        _ok("TAVILY_API_KEY found (optional web search enabled)")
    else:
        print("  [--] TAVILY_API_KEY not set — web search disabled (optional)")

    return openai_key, github_token


# ── Step 2: Fetch GitHub repos ────────────────────────────────────────────────

def fetch_github_repos(token: str) -> tuple[dict, list[dict]]:
    _header("Step 2/5 — Fetching your GitHub repositories")
    headers = {"Authorization": f"token {token}", "User-Agent": "freelance-agent-setup"}

    # Get authenticated user info
    r = requests.get("https://api.github.com/user", headers=headers, timeout=10)
    if r.status_code != 200:
        _fail(f"GitHub API error: {r.status_code} — check your GITHUB_TOKEN")
    user = r.json()
    _ok(f"Authenticated as: {user['login']} ({user.get('name', 'no name')})")

    # Fetch repos (owned + collaborator, sorted by recent activity)
    repos = []
    page = 1
    while True:
        r = requests.get(
            f"https://api.github.com/user/repos?sort=updated&per_page=50&page={page}&affiliation=owner,collaborator",
            headers=headers,
            timeout=10,
        )
        if r.status_code != 200 or not r.json():
            break
        batch = r.json()
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 50:
            break
        page += 1

    _ok(f"Found {len(repos)} repositories")
    return user, repos


# ── Step 3: User selects repos ────────────────────────────────────────────────

def select_repos(repos: list[dict]) -> list[dict]:
    _header("Step 3/5 — Select repos to track")
    print("  Enter the numbers of repos you want to add (comma-separated).")
    print("  Example: 1,3,5\n")

    for i, r in enumerate(repos, 1):
        visibility = "private" if r["private"] else "public "
        updated = r.get("updated_at", "")[:10]
        print(f"  {i:>3}. [{visibility}] {r['full_name']:<50} updated {updated}")

    print()
    raw = input("  Your selection: ").strip()
    if not raw:
        _fail("No repos selected. Exiting.")

    selected = []
    for part in raw.split(","):
        part = part.strip()
        if not part.isdigit():
            continue
        idx = int(part) - 1
        if 0 <= idx < len(repos):
            selected.append(repos[idx])

    if not selected:
        _fail("No valid repos selected.")

    print(f"\n  Selected {len(selected)} repo(s):")
    for r in selected:
        print(f"    - {r['full_name']}")
    return selected


# ── Step 4: Collect project details + fetch GitHub data ───────────────────────

def _fetch_readme(owner: str, repo: str, headers: dict) -> str:
    r = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/readme",
        headers={**headers, "Accept": "application/vnd.github.raw"},
        timeout=10,
    )
    if r.status_code == 200:
        # Truncate to first 3000 chars to keep chunks manageable
        return r.text[:3000]
    return ""


def _fetch_recent_commits(owner: str, repo: str, headers: dict) -> list[str]:
    r = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=10",
        headers=headers,
        timeout=10,
    )
    if r.status_code != 200:
        return []
    commits = []
    for c in r.json():
        if isinstance(c, dict) and "commit" in c:
            msg = c["commit"]["message"].split("\n")[0]
            date = c["commit"]["author"]["date"][:10]
            commits.append(f"- {date}: {msg}")
    return commits


def _write_project_doc(
    repo_name: str,
    project_name: str,
    client_name: str,
    repo_url: str,
    milestones: list[dict],
    readme: str,
    commits: list[str],
) -> Path:
    lines = [
        f"# {project_name} — {client_name}",
        "",
        f"Repository: {repo_url}",
        "",
        "## Overview",
    ]

    if readme:
        # Use first paragraph of README as overview
        first_para = readme.strip().split("\n\n")[0]
        first_para = re.sub(r"^#+\s*", "", first_para, flags=re.MULTILINE).strip()
        lines.append(first_para[:500])
    else:
        lines.append("No README found.")

    if milestones:
        lines += ["", "## Milestones"]
        for m in milestones:
            lines.append(f"- **{m['title']}** — {m['due_date']}: {m.get('notes', '')}")

    if commits:
        lines += ["", "## Recent Commits"]
        lines.extend(commits[:10])

    lines += ["", f"## Client\n{client_name}", ""]

    doc_path = PROJECTS_DIR / f"{repo_name}.md"
    doc_path.write_text("\n".join(lines), encoding="utf-8")
    return doc_path


def collect_projects(selected_repos: list[dict], token: str) -> list[dict]:
    _header("Step 4/5 — Configure projects")
    headers = {"Authorization": f"token {token}", "User-Agent": "freelance-agent-setup"}
    projects = []

    for repo in selected_repos:
        owner, repo_name = repo["full_name"].split("/")
        print(f"\n  Repo: {repo['full_name']}")

        project_name = _ask("  Project name", default=repo_name.replace("-", " ").title())
        client_name = _ask("  Client / company name", default="Personal")

        # Milestones
        milestones = []
        if _ask_yn("  Add milestones?", default=True):
            print("  Enter milestones one at a time. Leave title blank to stop.")
            while True:
                title = _ask("    Milestone title", default="")
                if not title:
                    break
                due = _ask("    Due date (YYYY-MM-DD)", default=datetime.now().strftime("%Y-%m-%d"))
                milestones.append({"title": title, "due_date": due})

        # Fetch GitHub data
        print(f"  Fetching README and recent commits from GitHub...")
        readme = _fetch_readme(owner, repo_name, headers)
        commits = _fetch_recent_commits(owner, repo_name, headers)
        _ok(f"README: {'found' if readme else 'not found'} | Commits: {len(commits)}")

        # Write project doc
        doc_path = _write_project_doc(
            repo_name=repo_name,
            project_name=project_name,
            client_name=client_name,
            repo_url=repo["html_url"],
            milestones=milestones,
            readme=readme,
            commits=commits,
        )
        _ok(f"Wrote {doc_path.name}")

        projects.append({
            "name": project_name,
            "client": client_name,
            "repo_url": repo["html_url"],
            "milestones": milestones,
        })

    return projects


# ── Step 5: Seed DB + build ChromaDB ─────────────────────────────────────────

def seed_and_index(projects: list[dict]):
    _header("Step 5/5 — Seeding database and building vector index")

    from db.sqlite import init_db, _connect

    # Wipe and reinit DB
    if Path(DB_PATH).exists():
        Path(DB_PATH).unlink()
    init_db(DB_PATH)
    _ok("SQLite database initialized")

    conn = _connect(DB_PATH)
    for proj in projects:
        cur = conn.execute(
            "INSERT INTO projects (name, client, repo_url, status) VALUES (?, ?, ?, 'active')",
            (proj["name"], proj["client"], proj["repo_url"]),
        )
        project_id = cur.lastrowid
        for m in proj.get("milestones", []):
            conn.execute(
                "INSERT INTO milestones (project_id, title, due_date) VALUES (?, ?, ?)",
                (project_id, m["title"], m["due_date"]),
            )
    conn.commit()
    conn.close()
    _ok(f"Inserted {len(projects)} project(s) and their milestones")

    # Build ChromaDB index from written project docs
    import shutil
    if Path(CHROMA_DIR).exists():
        shutil.rmtree(CHROMA_DIR)

    from rag.loader import load_documents
    from rag.chunker import chunk_documents
    from rag.retriever import build_retriever

    docs = load_documents(str(DATA_DIR))
    if not docs:
        _warn("No documents found to index — add .md files to backend/data/projects/")
        return

    chunks = chunk_documents(docs)
    build_retriever(chunks, persist_dir=CHROMA_DIR)
    _ok(f"ChromaDB indexed {len(chunks)} chunks from {len(docs)} document(s)")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print()
    print("  Freelance Agent — Setup")
    print("  This will configure your projects and build the AI knowledge base.")
    print()

    _, token = validate_env()
    user, all_repos = fetch_github_repos(token)
    selected = select_repos(all_repos)
    projects = collect_projects(selected, token)
    seed_and_index(projects)

    _hr("═")
    print()
    print("  Setup complete! Start the app:")
    print()
    print("  Backend:  uvicorn backend.main:app --reload")
    print("  Frontend: cd frontend && npm run dev")
    print()
    _hr("═")


if __name__ == "__main__":
    main()
