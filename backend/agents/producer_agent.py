import json
import logging
from datetime import date
from typing import Any, AsyncIterator

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from utils.project_context import ProjectContext, ProjectContextBuilder

logger = logging.getLogger(__name__)

_llm = ChatOpenAI(model="gpt-4o", temperature=0.3)

_BRIEFING_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a daily briefing assistant for a freelance software developer.
Produce a concise morning briefing in Markdown.

Use this structure:
## Daily Briefing - {today}

### Overdue
### Due This Week
### Recent GitHub Activity
### Suggested Focus

Skip empty sections. Be specific with dates and project names. Keep it under 400 words.""",
        ),
        (
            "human",
            """Projects:
{projects}

Milestones:
{milestones}

GitHub Activity:
{github_summary}

Project Docs:
{rag_chunks}""",
        ),
    ]
)

_PROPOSAL_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a proposal-writing assistant for a freelance software developer.
Write a professional client proposal in Markdown.

Use this structure:
## Proposal: {description} for {client}

### Overview
### Approach & Tech Stack
### Timeline
### Pricing
### Why Choose Me

Cite relevant past projects when available. Keep it under 600 words.""",
        ),
        (
            "human",
            """Past projects:
{projects}

Past milestones:
{milestones}

Project docs/context:
{rag_chunks}

New project description: {description}
Client: {client}
Budget: {budget}""",
        ),
    ]
)


def _sse(event_type: str, content: str) -> str:
    payload = {"agent": "producer", "type": event_type, "content": content}
    return f"data: {json.dumps(payload)}\n\n"


def _fmt_projects(projects: list[dict[str, Any]]) -> str:
    if not projects:
        return "No projects configured."
    return "\n".join(
        "- {name} (client: {client}, repo: {owner}/{repo}, status: {status})".format(
            name=project.get("name", "Untitled"),
            client=project.get("client") or "N/A",
            owner=project.get("repo_owner") or "",
            repo=project.get("repo_name") or "",
            status=project.get("status") or "",
        )
        for project in projects
    )


def _fmt_milestones(milestones: list[dict[str, Any]]) -> str:
    if not milestones:
        return "No milestones."
    return "\n".join(
        "- [{project_id}] {title} - due {due_date} ({status})".format(
            project_id=milestone.get("project_id", ""),
            title=milestone.get("title", "Untitled"),
            due_date=milestone.get("due_date", ""),
            status=milestone.get("status", "open"),
        )
        for milestone in milestones
    )


class ProducerAgent:
    def __init__(self, user_id: str, github_token: str = "") -> None:
        self._user_id = user_id
        self._github_token = github_token

    async def briefing(self) -> AsyncIterator[str]:
        logger.info("producer briefing start: user=%s", self._user_id)
        yield _sse("thinking", "Gathering your project context...")

        ctx = await ProjectContextBuilder(
            user_id=self._user_id,
            github_token=self._github_token,
        ).build()

        if not ctx.projects:
            yield _sse("final", "No projects found. Please complete the Setup Wizard first.")
            yield _sse("done", "")
            return

        if ctx.github_error:
            yield _sse("event", "GitHub data unavailable; using local project data.")

        yield _sse(
            "event",
            f"Analysing {len(ctx.projects)} projects and {len(ctx.milestones)} milestones...",
        )
        response = await _llm.ainvoke(
            _BRIEFING_PROMPT.format_messages(
                today=date.today().isoformat(),
                projects=_fmt_projects(ctx.projects),
                milestones=_fmt_milestones(ctx.milestones),
                github_summary=ctx.github_summary or "No GitHub data available.",
                rag_chunks="\n---\n".join(ctx.rag_chunks) or "No documentation indexed.",
            )
        )
        content = str(response.content)
        logger.info("producer briefing complete: user=%s chars=%d", self._user_id, len(content))
        yield _sse("final", content)
        yield _sse("done", "")

    async def proposal(
        self,
        description: str,
        client: str,
        budget: str = "",
    ) -> AsyncIterator[str]:
        logger.info("producer proposal start: user=%s client=%s", self._user_id, client)
        yield _sse("thinking", f"Researching past projects for {client}...")

        ctx: ProjectContext = await ProjectContextBuilder(
            user_id=self._user_id,
            github_token=self._github_token,
        ).build(rag_query=description)

        if not ctx.projects:
            yield _sse("event", "No past project data found; drafting from the description.")
        else:
            yield _sse("event", f"Using {len(ctx.projects)} projects as proposal context...")

        response = await _llm.ainvoke(
            _PROPOSAL_PROMPT.format_messages(
                projects=_fmt_projects(ctx.projects),
                milestones=_fmt_milestones(ctx.milestones),
                rag_chunks="\n---\n".join(ctx.rag_chunks) or "No documentation indexed.",
                description=description,
                client=client,
                budget=budget or "Not specified",
            )
        )
        content = str(response.content)
        logger.info("producer proposal complete: user=%s chars=%d", self._user_id, len(content))
        yield _sse("final", content)
        yield _sse("done", "")
