import json
import logging
import os
import re
from typing import Any

import requests
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from auth import get_user_id, get_github_token, encrypt
from db import postgres as db
from rag.loader import load_documents
from rag.chunker import chunk_documents
from rag.retriever import index_documents

router = APIRouter(prefix="/setup", tags=["setup"])
logger = logging.getLogger(__name__)


# ── Models ────────────────────────────────────────────────────────────────────

class KeysRequest(BaseModel):
    openai_key: str


class MilestoneInput(BaseModel):
    title: str
    due_date: str


class ProjectInput(BaseModel):
    name: str
    client: str
    repo_owner: str
    repo_name: str
    milestones: list[MilestoneInput] = []


class SetupRequest(BaseModel):
    projects: list[ProjectInput]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sse(event_type: str, content: str) -> str:
    return f"data: {json.dumps({'type': event_type, 'content': content})}\n\n"


def _github_headers(token: str) -> dict:
    h: dict[str, str] = {"User-Agent": "freelance-agent"}
    if token:
        h["Authorization"] = f"token {token}"
    return h


def _fetch_readme(owner: str, repo: str, token: str) -> str:
    r = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/readme",
        headers={**_github_headers(token), "Accept": "application/vnd.github.raw"},
        timeout=10,
    )
    return r.text[:3000] if r.status_code == 200 else ""


def _fetch_commits(owner: str, repo: str, token: str) -> list[str]:
    r = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=10",
        headers=_github_headers(token),
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


def _build_doc_text(proj: ProjectInput, readme: str, commits: list[str]) -> str:
    lines = [
        f"# {proj.name} — {proj.client}",
        "",
        f"Repository: https://github.com/{proj.repo_owner}/{proj.repo_name}",
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
    return "\n".join(lines)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/keys")
async def save_keys(body: KeysRequest, request: Request) -> dict[str, str]:
    """Store the user's OpenAI key encrypted in the DB."""
    user_id = get_user_id(request)
    logger.info(
        "Setup keys save requested: user_id=%s has_key=%s key_prefix_valid=%s",
        user_id,
        bool(body.openai_key.strip()),
        body.openai_key.strip().startswith("sk-"),
    )
    if not body.openai_key.strip().startswith("sk-"):
        logger.warning("Setup keys rejected: user_id=%s reason=invalid_format", user_id)
        raise HTTPException(status_code=422, detail="Invalid OpenAI API key format")
    encrypted = encrypt(body.openai_key.strip())
    await db.set_openai_key(user_id, encrypted)
    logger.info("Setup keys saved: user_id=%s", user_id)
    return {"status": "saved"}


@router.get("/status")
async def setup_status(request: Request) -> dict[str, Any]:
    """Returns whether this user has completed setup."""
    user_id = get_user_id(request)
    server_has_key = bool(os.environ.get("OPENAI_API_KEY", "").strip())
    user = await db.get_user_by_id(user_id)
    has_key = server_has_key or bool(user and user.get("openai_key_enc"))
    configured = has_key and await db.has_projects(user_id)
    logger.info(
        "Setup status: user_id=%s server_has_openai_key=%s user_has_openai_key=%s configured=%s",
        user_id,
        server_has_key,
        bool(user and user.get("openai_key_enc")),
        configured,
    )
    return {
        "configured": configured,
        "has_openai_key": has_key,
        "server_has_openai_key": server_has_key,
    }


@router.get("/repos")
async def list_repos(request: Request) -> dict[str, Any]:
    """Fetch the authenticated user's GitHub repos using their OAuth token."""
    user_id = get_user_id(request)
    logger.info("Setup repos requested: user_id=%s", user_id)
    token = get_github_token(request)
    headers = _github_headers(token)

    user_r = requests.get("https://api.github.com/user", headers=headers, timeout=10)
    if user_r.status_code != 200:
        logger.warning(
            "Setup repos GitHub user fetch failed: user_id=%s status=%s body=%s",
            user_id,
            user_r.status_code,
            user_r.text[:200],
        )
        return {"error": f"GitHub auth failed ({user_r.status_code})", "repos": []}
    user = user_r.json()

    repos = []
    page = 1
    while True:
        r = requests.get(
            f"https://api.github.com/user/repos?sort=updated&per_page=50&page={page}&affiliation=owner,collaborator",
            headers=headers,
            timeout=10,
        )
        if r.status_code != 200:
            logger.warning(
                "Setup repos page fetch failed: user_id=%s page=%s status=%s body=%s",
                user_id,
                page,
                r.status_code,
                r.text[:200],
            )
            break
        batch = r.json()
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 50:
            break
        page += 1

    logger.info(
        "Setup repos fetched: user_id=%s github_login=%s repo_count=%s",
        user_id,
        user.get("login", ""),
        len(repos),
    )
    return {
        "user": {"login": user["login"], "name": user.get("name", "")},
        "repos": [
            {
                "full_name": rp["full_name"],
                "owner": rp["owner"]["login"],
                "repo_name": rp["name"],
                "html_url": rp["html_url"],
                "private": rp["private"],
                "description": rp.get("description") or "",
                "updated_at": rp.get("updated_at", "")[:10],
            }
            for rp in repos
        ],
    }


@router.post("/complete")
async def complete_setup(req: SetupRequest, request: Request):
    """SSE: fetch READMEs, seed Postgres, build pgvector index — per user."""
    user_id = get_user_id(request)
    token = get_github_token(request)

    async def _stream():
        yield _sse("progress", f"Starting setup for {len(req.projects)} project(s)...")

        for proj in req.projects:
            yield _sse("progress", f"Fetching README for {proj.repo_owner}/{proj.repo_name}...")
            readme = _fetch_readme(proj.repo_owner, proj.repo_name, token)

            yield _sse("progress", f"Fetching recent commits for {proj.repo_owner}/{proj.repo_name}...")
            commits = _fetch_commits(proj.repo_owner, proj.repo_name, token)

            yield _sse("progress", f"Saving project {proj.name} to database...")
            project = await db.create_project(
                user_id=user_id,
                name=proj.name,
                client=proj.client or None,
                repo_owner=proj.repo_owner,
                repo_name=proj.repo_name,
            )
            project_id = str(project["id"])

            for m in proj.milestones:
                await db.create_milestone(
                    user_id=user_id,
                    project_id=project_id,
                    title=m.title,
                    due_date=m.due_date,
                )

            yield _sse("progress", f"Indexing documents for {proj.name}...")
            doc_text = _build_doc_text(proj, readme, commits)

            # Use rag chunker so large docs are split sensibly
            from langchain_core.documents import Document
            raw_doc = Document(page_content=doc_text, metadata={"project": proj.name})
            chunks = chunk_documents([raw_doc])
            await index_documents(
                user_id=user_id,
                project_id=project_id,
                chunks=chunks,
                source="readme",
            )
            yield _sse("progress", f"Indexed {len(chunks)} chunks for {proj.name}")

        yield _sse("progress", f"Setup complete — {len(req.projects)} project(s) ready")
        yield _sse("done", "Setup complete")

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )
