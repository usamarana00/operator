import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import requests

from db import postgres as db
from rag.retriever import retrieve

logger = logging.getLogger(__name__)


@dataclass
class ProjectContext:
    projects: list[dict[str, Any]]
    milestones: list[dict[str, Any]]
    rag_chunks: list[str]
    github_summary: str
    github_error: str | None = None


async def _fetch_github_summary(projects: list[dict[str, Any]], github_token: str) -> str:
    if not github_token:
        return ""

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "freelance-agent",
    }
    parts: list[str] = []

    for project in projects:
        owner = project.get("repo_owner")
        repo = project.get("repo_name")
        if not owner or not repo:
            continue

        base = f"https://api.github.com/repos/{owner}/{repo}"
        try:
            commits_res, prs_res, issues_res = await asyncio.gather(
                asyncio.to_thread(
                    requests.get,
                    f"{base}/commits?per_page=3",
                    headers=headers,
                    timeout=10,
                ),
                asyncio.to_thread(
                    requests.get,
                    f"{base}/pulls?state=open&per_page=3",
                    headers=headers,
                    timeout=10,
                ),
                asyncio.to_thread(
                    requests.get,
                    f"{base}/issues?state=open&per_page=3",
                    headers=headers,
                    timeout=10,
                ),
            )
            commits = commits_res.json() if commits_res.status_code == 200 else []
            prs = prs_res.json() if prs_res.status_code == 200 else []
            issues = issues_res.json() if issues_res.status_code == 200 else []

            commit_msgs = [
                c["commit"]["message"].splitlines()[0]
                for c in commits
                if isinstance(c, dict) and isinstance(c.get("commit"), dict)
            ]
            pr_titles = [p.get("title", "") for p in prs if isinstance(p, dict)]
            issue_titles = [
                i.get("title", "")
                for i in issues
                if isinstance(i, dict) and "pull_request" not in i
            ]
            parts.append(
                f"[{project.get('name', repo)}] Commits: {commit_msgs}. "
                f"Open PRs: {pr_titles}. Open Issues: {issue_titles}."
            )
        except Exception as exc:
            logger.warning("github summary failed for %s/%s: %s", owner, repo, exc)
            parts.append(f"[{project.get('name', repo)}] GitHub data unavailable.")

    return "\n".join(parts)


class ProjectContextBuilder:
    def __init__(self, user_id: str, github_token: str = "") -> None:
        self._user_id = user_id
        self._github_token = github_token

    async def build(self, rag_query: str = "project status milestones deadlines") -> ProjectContext:
        projects, milestones = await asyncio.gather(
            db.get_projects(self._user_id),
            db.get_milestones(self._user_id),
        )

        try:
            rag_chunks = await retrieve(self._user_id, rag_query, k=6)
        except Exception as exc:
            logger.warning("rag retrieve failed for user=%s: %s", self._user_id, exc)
            rag_chunks = []

        github_summary = ""
        github_error = None
        try:
            github_summary = await _fetch_github_summary(projects, self._github_token)
        except Exception as exc:
            github_error = str(exc)
            logger.warning("github context failed for user=%s: %s", self._user_id, exc)

        return ProjectContext(
            projects=projects,
            milestones=milestones,
            rag_chunks=rag_chunks,
            github_summary=github_summary,
            github_error=github_error,
        )
