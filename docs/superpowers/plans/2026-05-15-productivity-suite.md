# Freelance Productivity Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Daily Briefing and Proposal Generator features to the freelance-agent backend and frontend, sharing a common ProjectContextBuilder utility.

**Architecture:** A new `ProducerAgent` with two async streaming modes (briefing, proposal) calls a shared `ProjectContextBuilder` that aggregates projects, milestones, GitHub data, and RAG context. Two new FastAPI routers expose SSE endpoints. The frontend adds a sidebar button (briefing), a modal wizard (proposal), and a PDF download button. WeasyPrint converts proposal Markdown to PDF.

**Tech Stack:** FastAPI (SSE), asyncpg (Postgres), LangChain ChatOpenAI gpt-4o, pgvector RAG, WeasyPrint (PDF), Next.js 16 + Tailwind CSS, next-auth JWT, existing `_sse()` pattern.

---

## File Map

### Backend — New Files
| File | Responsibility |
|------|---------------|
| `backend/utils/project_context.py` | `ProjectContextBuilder` — fetches projects, milestones, GitHub summary, RAG chunks |
| `backend/agents/producer_agent.py` | `ProducerAgent` — briefing + proposal async generators, GPT-4o prompts |
| `backend/routers/briefing.py` | `POST /briefing` — SSE route, auth, calls producer |
| `backend/routers/proposal.py` | `POST /proposal`, `GET /proposal/{session_id}/pdf` — SSE + PDF download |
| `tests/test_project_context.py` | Unit tests for ProjectContextBuilder |
| `tests/test_producer_agent.py` | Unit tests for ProducerAgent briefing + proposal |
| `tests/test_briefing_router.py` | Integration tests for /briefing endpoint |
| `tests/test_proposal_router.py` | Integration tests for /proposal endpoint |

### Backend — Modified Files
| File | Change |
|------|--------|
| `backend/main.py` | Register briefing + proposal routers; add `weasyprint` guard import |
| `pyproject.toml` | Add `weasyprint` dependency |

### Frontend — New Files
| File | Responsibility |
|------|---------------|
| `frontend/components/BriefingButton.tsx` | Sidebar button → triggers briefing SSE stream |
| `frontend/components/ProposalWizard.tsx` | 3-field modal (client, description, budget) |
| `frontend/components/ProposalDownload.tsx` | "Download PDF" button shown after proposal streams |

### Frontend — Modified Files
| File | Change |
|------|--------|
| `frontend/components/Sidebar.tsx` | Add `<BriefingButton>` and "New Proposal" button that opens `<ProposalWizard>` |
| `frontend/components/ChatWindow.tsx` | Detect `/briefing` and `/proposal` slash commands; render `<ProposalDownload>` after proposal turns |

---

## Task 1: ProjectContextBuilder utility

**Files:**
- Create: `backend/utils/__init__.py`
- Create: `backend/utils/project_context.py`
- Create: `tests/test_project_context.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_project_context.py
import pytest
from unittest.mock import AsyncMock, patch
from utils.project_context import ProjectContextBuilder, ProjectContext

@pytest.mark.asyncio
async def test_build_returns_project_context():
    mock_projects = [
        {"id": "p1", "name": "Alpha", "client": "Acme", "repo_owner": "usr", "repo_name": "alpha", "status": "active"}
    ]
    mock_milestones = [
        {"id": "m1", "project_id": "p1", "title": "Launch", "due_date": "2026-05-20", "status": "open"}
    ]
    mock_rag_chunks = ["Readme content about Alpha project"]
    mock_github_summary = "3 commits on main. 1 open PR: fix auth."

    with patch("utils.project_context.db.get_projects", new=AsyncMock(return_value=mock_projects)), \
         patch("utils.project_context.db.get_milestones", new=AsyncMock(return_value=mock_milestones)), \
         patch("utils.project_context.retrieve", new=AsyncMock(return_value=mock_rag_chunks)), \
         patch("utils.project_context._fetch_github_summary", new=AsyncMock(return_value=mock_github_summary)):

        builder = ProjectContextBuilder(user_id="u1", github_token="tok")
        ctx = await builder.build()

    assert isinstance(ctx, ProjectContext)
    assert ctx.projects == mock_projects
    assert ctx.milestones == mock_milestones
    assert ctx.rag_chunks == mock_rag_chunks
    assert ctx.github_summary == mock_github_summary

@pytest.mark.asyncio
async def test_build_handles_github_error_gracefully():
    with patch("utils.project_context.db.get_projects", new=AsyncMock(return_value=[])), \
         patch("utils.project_context.db.get_milestones", new=AsyncMock(return_value=[])), \
         patch("utils.project_context.retrieve", new=AsyncMock(return_value=[])), \
         patch("utils.project_context._fetch_github_summary", new=AsyncMock(side_effect=Exception("rate limit"))):

        builder = ProjectContextBuilder(user_id="u1", github_token="tok")
        ctx = await builder.build()

    assert ctx.github_summary == ""
    assert ctx.github_error is not None
```

- [ ] **Step 2: Run test to verify it fails**

```
cd e:\atomcamp\freelance-agent\backend
python -m pytest ../tests/test_project_context.py -v
```

Expected: `ModuleNotFoundError: No module named 'utils.project_context'`

- [ ] **Step 3: Create `backend/utils/__init__.py`**

```python
# backend/utils/__init__.py
```

- [ ] **Step 4: Create `backend/utils/project_context.py`**

```python
# backend/utils/project_context.py
import asyncio
import logging
from dataclasses import dataclass, field

import requests

from db import postgres as db
from rag.retriever import retrieve

logger = logging.getLogger(__name__)


@dataclass
class ProjectContext:
    projects: list[dict]
    milestones: list[dict]
    rag_chunks: list[str]
    github_summary: str
    github_error: str | None = None


async def _fetch_github_summary(projects: list[dict], github_token: str) -> str:
    """Fetch recent commits, open PRs, open issues for all active projects."""
    if not github_token:
        logger.warning("project_context: no github_token, skipping GitHub fetch")
        return ""

    headers = {"User-Agent": "freelance-agent"}
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    parts: list[str] = []
    for proj in projects:
        owner = proj.get("repo_owner")
        repo = proj.get("repo_name")
        if not owner or not repo:
            continue

        base = f"https://api.github.com/repos/{owner}/{repo}"
        try:
            commits = requests.get(f"{base}/commits?per_page=3", headers=headers, timeout=10).json()
            prs = requests.get(f"{base}/pulls?state=open&per_page=3", headers=headers, timeout=10).json()
            issues = requests.get(f"{base}/issues?state=open&per_page=3", headers=headers, timeout=10).json()

            commit_msgs = [c["commit"]["message"].splitlines()[0] for c in commits if isinstance(c, dict)]
            pr_titles = [p["title"] for p in prs if isinstance(p, dict)]
            issue_titles = [i["title"] for i in issues if isinstance(i, dict) and "pull_request" not in i]

            summary = f"[{proj['name']}] Commits: {commit_msgs}. Open PRs: {pr_titles}. Open Issues: {issue_titles}."
            parts.append(summary)
            logger.debug("project_context: fetched github data for %s/%s", owner, repo)
        except Exception as exc:
            logger.warning("project_context: github fetch failed for %s/%s: %s", owner, repo, exc)
            parts.append(f"[{proj['name']}] GitHub data unavailable.")

    return "\n".join(parts)


class ProjectContextBuilder:
    """Aggregate project data for ProducerAgent modes."""

    def __init__(self, user_id: str, github_token: str = "") -> None:
        self._user_id = user_id
        self._github_token = github_token

    async def build(self) -> ProjectContext:
        logger.info("project_context: building context for user=%s", self._user_id)

        projects, milestones = await asyncio.gather(
            db.get_projects(self._user_id),
            db.get_milestones(self._user_id),
        )
        logger.debug("project_context: %d projects, %d milestones", len(projects), len(milestones))

        rag_chunks = await retrieve(self._user_id, "project status milestones deadlines", k=6)
        logger.debug("project_context: %d rag chunks", len(rag_chunks))

        github_summary = ""
        github_error = None
        try:
            github_summary = await _fetch_github_summary(projects, self._github_token)
        except Exception as exc:
            github_error = str(exc)
            logger.warning("project_context: github summary failed: %s", exc)

        return ProjectContext(
            projects=projects,
            milestones=milestones,
            rag_chunks=rag_chunks,
            github_summary=github_summary,
            github_error=github_error,
        )
```

- [ ] **Step 5: Run test to verify it passes**

```
cd e:\atomcamp\freelance-agent\backend
python -m pytest ../tests/test_project_context.py -v
```

Expected: `2 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/utils/__init__.py backend/utils/project_context.py tests/test_project_context.py
git commit -m "feat: add ProjectContextBuilder utility"
```

---

## Task 2: ProducerAgent — briefing mode

**Files:**
- Create: `backend/agents/producer_agent.py`
- Create: `tests/test_producer_agent.py`

- [ ] **Step 1: Write the failing test for briefing**

```python
# tests/test_producer_agent.py
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from utils.project_context import ProjectContext
from agents.producer_agent import ProducerAgent

MOCK_CTX = ProjectContext(
    projects=[{"id": "p1", "name": "Alpha", "client": "Acme", "status": "active"}],
    milestones=[
        {"project_id": "p1", "title": "Launch", "due_date": "2026-05-18", "status": "open"},
        {"project_id": "p1", "title": "Design", "due_date": "2026-05-12", "status": "open"},
    ],
    rag_chunks=["Alpha project uses React + FastAPI"],
    github_summary="[Alpha] Commits: ['fix: auth bug']. Open PRs: ['Add tests']. Open Issues: [].",
)

@pytest.mark.asyncio
async def test_briefing_yields_sse_events():
    mock_llm_response = MagicMock()
    mock_llm_response.content = "## Daily Briefing\n\n### Overdue\n- Alpha: Design was due May 12\n\n### Suggested Focus\nFinish Launch milestone."

    with patch("agents.producer_agent.ProjectContextBuilder") as MockBuilder, \
         patch("agents.producer_agent._llm") as mock_llm:
        MockBuilder.return_value.build = AsyncMock(return_value=MOCK_CTX)
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)

        agent = ProducerAgent(user_id="u1", github_token="tok")
        chunks = []
        async for chunk in agent.briefing():
            chunks.append(chunk)

    assert len(chunks) >= 2
    # First chunk is a "thinking" event
    first = json.loads(chunks[0].removeprefix("data: ").strip())
    assert first["agent"] == "producer"
    assert first["type"] == "thinking"
    # Last chunk is "final"
    last = json.loads(chunks[-1].removeprefix("data: ").strip())
    assert last["type"] == "final"
    assert "Briefing" in last["content"]
```

- [ ] **Step 2: Run test to verify it fails**

```
cd e:\atomcamp\freelance-agent\backend
python -m pytest ../tests/test_producer_agent.py::test_briefing_yields_sse_events -v
```

Expected: `ModuleNotFoundError: No module named 'agents.producer_agent'`

- [ ] **Step 3: Create `backend/agents/producer_agent.py`**

```python
# backend/agents/producer_agent.py
import json
import logging
from datetime import date
from typing import AsyncIterator

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from utils.project_context import ProjectContextBuilder, ProjectContext

logger = logging.getLogger(__name__)

_llm = ChatOpenAI(model="gpt-4o", temperature=0.3)

_BRIEFING_SYSTEM = """You are a daily briefing assistant for a freelance software developer.
Given their project context, produce a concise morning briefing in Markdown.

Structure:
## Daily Briefing — {today}

### Overdue
(milestones past due_date that are still open; skip section if none)

### Due This Week
(milestones due within 7 days; skip section if none)

### Recent GitHub Activity
(summarize commits, PRs, issues per project; skip section if no data)

### Suggested Focus
(one sentence: which project to tackle first and why)

Be specific with dates and project names. Keep the total under 400 words."""

_BRIEFING_HUMAN = """Projects: {projects}
Milestones: {milestones}
GitHub Activity: {github_summary}
Project Docs: {rag_chunks}
Today: {today}"""

_BRIEFING_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _BRIEFING_SYSTEM),
    ("human", _BRIEFING_HUMAN),
])

_PROPOSAL_SYSTEM = """You are a proposal-writing assistant for a freelance software developer.
Given the developer's past project data and a new project description, write a professional client proposal in Markdown.

Structure:
## Proposal: {description} for {client}

### Overview
(2-3 sentences: what will be built)

### Approach & Tech Stack
(inferred from description and developer's past projects; be specific)

### Timeline
| Phase | Deliverable | Duration |
|-------|-------------|----------|
| 1     | ...         | ...      |
(3-5 phases)

### Pricing
(if budget provided: break it down by phase; otherwise give typical ranges for this type of work)

### Why Choose Me
(cite 1-2 specific past projects from the developer's history as evidence of relevant experience)

Keep it professional and under 600 words."""

_PROPOSAL_HUMAN = """Past projects: {projects}
Past milestones delivered: {milestones}
Project docs/context: {rag_chunks}
New project description: {description}
Client: {client}
Budget: {budget}"""

_PROPOSAL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", _PROPOSAL_SYSTEM),
    ("human", _PROPOSAL_HUMAN),
])


def _sse(event_type: str, content: str) -> str:
    return f"data: {json.dumps({'agent': 'producer', 'type': event_type, 'content': content})}\n\n"


def _fmt_projects(projects: list[dict]) -> str:
    return "\n".join(
        f"- {p['name']} (client: {p.get('client', 'N/A')}, repo: {p.get('repo_owner', '')}/{p.get('repo_name', '')}, status: {p.get('status', '')})"
        for p in projects
    ) or "No projects configured."


def _fmt_milestones(milestones: list[dict]) -> str:
    return "\n".join(
        f"- [{m.get('project_id', '')}] {m['title']} — due {m['due_date']} ({m.get('status', 'open')})"
        for m in milestones
    ) or "No milestones."


class ProducerAgent:
    def __init__(self, user_id: str, github_token: str = "") -> None:
        self._user_id = user_id
        self._github_token = github_token

    async def briefing(self) -> AsyncIterator[str]:
        """Yield SSE chunks for a daily project briefing."""
        logger.info("producer_agent: starting briefing for user=%s", self._user_id)
        yield _sse("thinking", "Gathering your project context...")

        ctx: ProjectContext = await ProjectContextBuilder(
            user_id=self._user_id, github_token=self._github_token
        ).build()

        if not ctx.projects:
            logger.info("producer_agent: no projects for user=%s", self._user_id)
            yield _sse("final", "No projects found. Please complete the Setup Wizard first.")
            return

        if ctx.github_error:
            logger.warning("producer_agent: github error in briefing: %s", ctx.github_error)
            yield _sse("event", "GitHub data unavailable — briefing will use local data only.")

        today = date.today().isoformat()
        yield _sse("event", f"Analysing {len(ctx.projects)} projects and {len(ctx.milestones)} milestones...")

        messages = _BRIEFING_PROMPT.format_messages(
            projects=_fmt_projects(ctx.projects),
            milestones=_fmt_milestones(ctx.milestones),
            github_summary=ctx.github_summary or "No GitHub data available.",
            rag_chunks="\n---\n".join(ctx.rag_chunks) or "No documentation indexed.",
            today=today,
        )

        logger.debug("producer_agent: invoking LLM for briefing")
        response = await _llm.ainvoke(messages)
        content = response.content

        logger.info("producer_agent: briefing complete for user=%s (%d chars)", self._user_id, len(content))
        yield _sse("final", content)

    async def proposal(
        self,
        description: str,
        client: str,
        budget: str = "",
    ) -> AsyncIterator[str]:
        """Yield SSE chunks for a client proposal."""
        logger.info("producer_agent: starting proposal for user=%s client=%s", self._user_id, client)
        yield _sse("thinking", f"Researching past projects to build a proposal for {client}...")

        ctx: ProjectContext = await ProjectContextBuilder(
            user_id=self._user_id, github_token=self._github_token
        ).build()

        if not ctx.projects:
            logger.info("producer_agent: no past projects — generating proposal from description only")
            yield _sse("event", "No past project data found — generating proposal from description alone.")

        yield _sse("event", "Drafting proposal with GPT-4o...")

        messages = _PROPOSAL_PROMPT.format_messages(
            projects=_fmt_projects(ctx.projects),
            milestones=_fmt_milestones(ctx.milestones),
            rag_chunks="\n---\n".join(ctx.rag_chunks) or "No documentation indexed.",
            description=description,
            client=client,
            budget=budget or "Not specified",
        )

        logger.debug("producer_agent: invoking LLM for proposal")
        response = await _llm.ainvoke(messages)
        content = response.content

        logger.info("producer_agent: proposal complete for user=%s (%d chars)", self._user_id, len(content))
        yield _sse("final", content)
```

- [ ] **Step 4: Run test to verify it passes**

```
cd e:\atomcamp\freelance-agent\backend
python -m pytest ../tests/test_producer_agent.py::test_briefing_yields_sse_events -v
```

Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/agents/producer_agent.py tests/test_producer_agent.py
git commit -m "feat: add ProducerAgent briefing mode"
```

---

## Task 3: ProducerAgent — proposal mode tests

**Files:**
- Modify: `tests/test_producer_agent.py`

- [ ] **Step 1: Write the failing test for proposal**

Add to `tests/test_producer_agent.py`:

```python
@pytest.mark.asyncio
async def test_proposal_yields_sse_events():
    mock_llm_response = MagicMock()
    mock_llm_response.content = "## Proposal: E-commerce site for RetailCo\n\n### Overview\nBuild a React + FastAPI store.\n\n### Timeline\n| Phase | Deliverable | Duration |\n|-------|-------------|----------|\n| 1 | Backend APIs | 2 weeks |"

    with patch("agents.producer_agent.ProjectContextBuilder") as MockBuilder, \
         patch("agents.producer_agent._llm") as mock_llm:
        MockBuilder.return_value.build = AsyncMock(return_value=MOCK_CTX)
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)

        agent = ProducerAgent(user_id="u1", github_token="tok")
        chunks = []
        async for chunk in agent.proposal(description="E-commerce site", client="RetailCo", budget="$5000"):
            chunks.append(chunk)

    assert len(chunks) >= 2
    last = json.loads(chunks[-1].removeprefix("data: ").strip())
    assert last["type"] == "final"
    assert "Proposal" in last["content"]

@pytest.mark.asyncio
async def test_proposal_no_past_projects_still_generates():
    empty_ctx = ProjectContext(projects=[], milestones=[], rag_chunks=[], github_summary="")
    mock_llm_response = MagicMock()
    mock_llm_response.content = "## Proposal: MVP for StartupX\n\n### Overview\nBuild from scratch."

    with patch("agents.producer_agent.ProjectContextBuilder") as MockBuilder, \
         patch("agents.producer_agent._llm") as mock_llm:
        MockBuilder.return_value.build = AsyncMock(return_value=empty_ctx)
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)

        agent = ProducerAgent(user_id="u1")
        chunks = []
        async for chunk in agent.proposal(description="MVP", client="StartupX"):
            chunks.append(chunk)

    events = [json.loads(c.removeprefix("data: ").strip()) for c in chunks]
    event_types = [e["type"] for e in events]
    assert "event" in event_types  # "No past project data" warning event
    assert "final" in event_types
```

- [ ] **Step 2: Run test to verify it fails**

```
cd e:\atomcamp\freelance-agent\backend
python -m pytest ../tests/test_producer_agent.py -v
```

Expected: `1 passed, 2 failed` (new tests fail — proposal not yet wired)

Actually the implementation is already in `producer_agent.py`. Run:

```
cd e:\atomcamp\freelance-agent\backend
python -m pytest ../tests/test_producer_agent.py -v
```

Expected: `3 passed`

- [ ] **Step 3: Commit**

```bash
git add tests/test_producer_agent.py
git commit -m "test: add proposal mode tests for ProducerAgent"
```

---

## Task 4: Briefing router

**Files:**
- Create: `backend/routers/briefing.py`
- Create: `tests/test_briefing_router.py`

- [ ] **Step 1: Write the failing integration test**

```python
# tests/test_briefing_router.py
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

# We test the router directly by mounting a minimal app
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from routers.briefing import router

app = FastAPI()
app.include_router(router)

# Stub auth middleware state
from fastapi import Request

@app.middleware("http")
async def stub_auth(request: Request, call_next):
    request.state.user_id = "test-user"
    request.state.github_token_enc = b""
    return await call_next(request)

client = TestClient(app, raise_server_exceptions=True)

def test_briefing_returns_event_stream():
    async def fake_briefing(self):
        yield 'data: {"agent": "producer", "type": "thinking", "content": "Loading..."}\n\n'
        yield 'data: {"agent": "producer", "type": "final", "content": "## Daily Briefing"}\n\n'

    with patch("routers.briefing.ProducerAgent.briefing", fake_briefing):
        response = client.post("/briefing")

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
```

- [ ] **Step 2: Run test to verify it fails**

```
cd e:\atomcamp\freelance-agent\backend
python -m pytest ../tests/test_briefing_router.py -v
```

Expected: `ModuleNotFoundError: No module named 'routers.briefing'`

- [ ] **Step 3: Create `backend/routers/briefing.py`**

```python
# backend/routers/briefing.py
import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from auth import get_user_id, get_github_token
from agents.producer_agent import ProducerAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/briefing", tags=["briefing"])


@router.post("")
async def briefing(request: Request):
    user_id = get_user_id(request)
    try:
        github_token = get_github_token(request)
    except Exception:
        github_token = ""
        logger.debug("briefing: no github token for user=%s", user_id)

    logger.info("briefing: request from user=%s", user_id)

    async def generate():
        agent = ProducerAgent(user_id=user_id, github_token=github_token)
        async for chunk in agent.briefing():
            yield chunk

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

- [ ] **Step 4: Run test to verify it passes**

```
cd e:\atomcamp\freelance-agent\backend
python -m pytest ../tests/test_briefing_router.py -v
```

Expected: `1 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/routers/briefing.py tests/test_briefing_router.py
git commit -m "feat: add /briefing SSE endpoint"
```

---

## Task 5: Proposal router (SSE + PDF)

**Files:**
- Create: `backend/routers/proposal.py`
- Create: `tests/test_proposal_router.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Add weasyprint dependency**

In `pyproject.toml`, under `dependencies = [`, add:

```toml
"weasyprint>=62.0",
```

Then install:

```
cd e:\atomcamp\freelance-agent
pip install weasyprint
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_proposal_router.py
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from routers.proposal import router

app = FastAPI()
app.include_router(router)

@app.middleware("http")
async def stub_auth(request: Request, call_next):
    request.state.user_id = "test-user"
    request.state.github_token_enc = b""
    return await call_next(request)

client = TestClient(app, raise_server_exceptions=True)

def test_proposal_returns_event_stream():
    async def fake_proposal(self, description, client, budget):
        yield 'data: {"agent": "producer", "type": "thinking", "content": "Drafting..."}\n\n'
        yield 'data: {"agent": "producer", "type": "final", "content": "## Proposal: MVP for Acme"}\n\n'

    with patch("routers.proposal.ProducerAgent.proposal", fake_proposal):
        response = client.post(
            "/proposal",
            json={"client": "Acme", "description": "MVP app", "budget": "$5000"},
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

def test_proposal_missing_required_fields_returns_422():
    response = client.post("/proposal", json={"client": "Acme"})
    assert response.status_code == 422

def test_proposal_pdf_returns_pdf_bytes():
    mock_messages = [
        {"role": "user", "content": "proposal request"},
        {"role": "assistant", "content": "## Proposal: MVP for Acme\n\n### Overview\nBuild it."},
    ]
    with patch("routers.proposal.db.get_messages", new=AsyncMock(return_value=mock_messages)), \
         patch("routers.proposal._markdown_to_pdf", return_value=b"%PDF-1.4 mock"):
        response = client.get("/proposal/test-session/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
```

- [ ] **Step 3: Run test to verify it fails**

```
cd e:\atomcamp\freelance-agent\backend
python -m pytest ../tests/test_proposal_router.py -v
```

Expected: `ModuleNotFoundError: No module named 'routers.proposal'`

- [ ] **Step 4: Create `backend/routers/proposal.py`**

```python
# backend/routers/proposal.py
import logging
import markdown

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel

from auth import get_user_id, get_github_token
from agents.producer_agent import ProducerAgent
from db import postgres as db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/proposal", tags=["proposal"])


class ProposalRequest(BaseModel):
    client: str
    description: str
    budget: str = ""


def _markdown_to_pdf(md_content: str) -> bytes:
    """Convert Markdown string to PDF bytes via WeasyPrint."""
    try:
        from weasyprint import HTML
        html_body = markdown.markdown(md_content, extensions=["tables"])
        full_html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<style>
  body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; color: #222; }}
  h1, h2, h3 {{ color: #1a1a2e; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
  th, td {{ border: 1px solid #ccc; padding: 8px 12px; text-align: left; }}
  th {{ background: #f0f0f0; }}
  code {{ background: #f5f5f5; padding: 2px 4px; border-radius: 3px; }}
</style>
</head><body>{html_body}</body></html>"""
        return HTML(string=full_html).write_pdf()
    except ImportError:
        logger.error("proposal: weasyprint not installed — cannot generate PDF")
        raise


@router.post("")
async def create_proposal(req: ProposalRequest, request: Request):
    user_id = get_user_id(request)
    try:
        github_token = get_github_token(request)
    except Exception:
        github_token = ""

    logger.info("proposal: request from user=%s client=%s", user_id, req.client)

    async def generate():
        agent = ProducerAgent(user_id=user_id, github_token=github_token)
        async for chunk in agent.proposal(
            description=req.description,
            client=req.client,
            budget=req.budget,
        ):
            yield chunk

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{session_id}/pdf")
async def download_proposal_pdf(session_id: str, request: Request):
    user_id = get_user_id(request)
    logger.info("proposal: PDF download requested for user=%s session=%s", user_id, session_id)

    messages = await db.get_messages(user_id, session_id, limit=50)
    proposal_content = None
    for msg in reversed(messages):
        if msg["role"] == "assistant" and "## Proposal" in msg.get("content", ""):
            proposal_content = msg["content"]
            break

    if not proposal_content:
        logger.warning("proposal: no proposal found in session=%s for user=%s", session_id, user_id)
        raise HTTPException(status_code=404, detail="No proposal found in this session")

    try:
        pdf_bytes = _markdown_to_pdf(proposal_content)
        logger.info("proposal: PDF generated (%d bytes) for user=%s", len(pdf_bytes), user_id)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="proposal-{session_id[:8]}.pdf"'},
        )
    except ImportError:
        logger.warning("proposal: PDF unavailable, returning markdown fallback for user=%s", user_id)
        return Response(
            content=proposal_content.encode("utf-8"),
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="proposal-{session_id[:8]}.md"'},
        )
```

- [ ] **Step 5: Install `markdown` package (used for HTML conversion)**

```
pip install markdown
```

Add to `pyproject.toml` dependencies:
```toml
"markdown>=3.7",
```

- [ ] **Step 6: Run tests to verify they pass**

```
cd e:\atomcamp\freelance-agent\backend
python -m pytest ../tests/test_proposal_router.py -v
```

Expected: `3 passed`

- [ ] **Step 7: Commit**

```bash
git add backend/routers/proposal.py tests/test_proposal_router.py pyproject.toml
git commit -m "feat: add /proposal SSE endpoint and PDF download"
```

---

## Task 6: Register routers in main.py

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Add router imports and registration**

In `backend/main.py`, find the existing router imports:

```python
from routers.setup import router as setup_router
from routers.files import router as files_router
```

Add below them:

```python
from routers.briefing import router as briefing_router
from routers.proposal import router as proposal_router
```

Find:

```python
app.include_router(setup_router)
app.include_router(files_router)
```

Add below them:

```python
app.include_router(briefing_router)
app.include_router(proposal_router)
```

- [ ] **Step 2: Verify the app starts without errors**

```
cd e:\atomcamp\freelance-agent\backend
python -c "from main import app; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Run all backend tests**

```
cd e:\atomcamp\freelance-agent\backend
python -m pytest ../tests/ -v
```

Expected: all tests pass

- [ ] **Step 4: Commit**

```bash
git add backend/main.py
git commit -m "feat: register briefing and proposal routers in main app"
```

---

## Task 7: Next.js proxy routes

**Files:**
- Create: `frontend/app/api/backend/briefing/route.ts`
- Create: `frontend/app/api/backend/proposal/route.ts`
- Create: `frontend/app/api/backend/proposal/[session_id]/pdf/route.ts`

- [ ] **Step 1: Read the existing proxy pattern**

Open `frontend/app/api/backend/chat/route.ts` (or equivalent) to confirm the proxy pattern. The pattern is:

```typescript
// Forwards request to BACKEND_URL with Authorization: Bearer {token}
```

- [ ] **Step 2: Create briefing proxy**

```typescript
// frontend/app/api/backend/briefing/route.ts
import { getToken } from "next-auth/jwt";
import { NextRequest } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  const token = await getToken({ req, secret: process.env.NEXTAUTH_SECRET });
  const githubToken = (token as any)?.github_token ?? "";

  const response = await fetch(`${BACKEND_URL}/briefing`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${githubToken}`,
    },
  });

  return new Response(response.body, {
    status: response.status,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
}
```

- [ ] **Step 3: Create proposal proxy**

```typescript
// frontend/app/api/backend/proposal/route.ts
import { getToken } from "next-auth/jwt";
import { NextRequest } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  const token = await getToken({ req, secret: process.env.NEXTAUTH_SECRET });
  const githubToken = (token as any)?.github_token ?? "";
  const body = await req.json();

  const response = await fetch(`${BACKEND_URL}/proposal`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${githubToken}`,
    },
    body: JSON.stringify(body),
  });

  return new Response(response.body, {
    status: response.status,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
}
```

- [ ] **Step 4: Create PDF proxy**

```typescript
// frontend/app/api/backend/proposal/[session_id]/pdf/route.ts
import { getToken } from "next-auth/jwt";
import { NextRequest } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function GET(
  req: NextRequest,
  { params }: { params: { session_id: string } }
) {
  const token = await getToken({ req, secret: process.env.NEXTAUTH_SECRET });
  const githubToken = (token as any)?.github_token ?? "";

  const response = await fetch(
    `${BACKEND_URL}/proposal/${params.session_id}/pdf`,
    {
      headers: { Authorization: `Bearer ${githubToken}` },
    }
  );

  const contentType = response.headers.get("content-type") ?? "application/pdf";
  const contentDisposition = response.headers.get("content-disposition") ?? "";

  return new Response(response.body, {
    status: response.status,
    headers: {
      "Content-Type": contentType,
      "Content-Disposition": contentDisposition,
    },
  });
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/app/api/backend/briefing/route.ts frontend/app/api/backend/proposal/route.ts "frontend/app/api/backend/proposal/[session_id]/pdf/route.ts"
git commit -m "feat: add Next.js proxy routes for briefing and proposal"
```

---

## Task 8: BriefingButton component

**Files:**
- Create: `frontend/components/BriefingButton.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/components/BriefingButton.tsx
"use client";

import { useState } from "react";

interface BriefingButtonProps {
  onStream: (chunks: string) => void;
}

export default function BriefingButton({ onStream }: BriefingButtonProps) {
  const [loading, setLoading] = useState(false);

  const handleClick = async () => {
    if (loading) return;
    setLoading(true);
    try {
      const res = await fetch("/api/backend/briefing", { method: "POST" });
      if (!res.ok || !res.body) throw new Error("Briefing request failed");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let accumulated = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        accumulated += decoder.decode(value, { stream: true });
        onStream(accumulated);
      }
    } catch (err) {
      console.error("BriefingButton: stream error", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleClick}
      disabled={loading}
      className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors text-gray-300 hover:text-white hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      <span>{loading ? "⏳" : "☀️"}</span>
      <span>{loading ? "Generating briefing..." : "Morning Briefing"}</span>
    </button>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/BriefingButton.tsx
git commit -m "feat: add BriefingButton component"
```

---

## Task 9: ProposalWizard component

**Files:**
- Create: `frontend/components/ProposalWizard.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/components/ProposalWizard.tsx
"use client";

import { useState } from "react";

interface ProposalWizardProps {
  open: boolean;
  onClose: () => void;
  onStream: (chunks: string) => void;
  onSessionId: (id: string) => void;
}

export default function ProposalWizard({
  open,
  onClose,
  onStream,
  onSessionId,
}: ProposalWizardProps) {
  const [client, setClient] = useState("");
  const [description, setDescription] = useState("");
  const [budget, setBudget] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!client.trim() || !description.trim()) {
      setError("Client and description are required.");
      return;
    }
    setError("");
    setLoading(true);
    onClose();

    try {
      const sessionId = crypto.randomUUID();
      onSessionId(sessionId);

      const res = await fetch("/api/backend/proposal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client, description, budget }),
      });

      if (!res.ok || !res.body) throw new Error("Proposal request failed");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let accumulated = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        accumulated += decoder.decode(value, { stream: true });
        onStream(accumulated);
      }
    } catch (err) {
      console.error("ProposalWizard: stream error", err);
    } finally {
      setLoading(false);
      setClient("");
      setDescription("");
      setBudget("");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-gray-800 rounded-xl shadow-2xl w-full max-w-md p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Generate Proposal</h2>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Client name *</label>
            <input
              type="text"
              value={client}
              onChange={(e) => setClient(e.target.value)}
              placeholder="e.g. Acme Corp"
              className="w-full bg-gray-700 text-white rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Project description *</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what needs to be built..."
              rows={4}
              className="w-full bg-gray-700 text-white rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Budget range (optional)</label>
            <input
              type="text"
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              placeholder="e.g. $3,000–$5,000"
              className="w-full bg-gray-700 text-white rounded-lg px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-sm text-gray-300 hover:text-white hover:bg-gray-700 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 hover:bg-blue-500 text-white transition-colors disabled:opacity-50"
            >
              {loading ? "Generating..." : "Generate Proposal"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/ProposalWizard.tsx
git commit -m "feat: add ProposalWizard modal component"
```

---

## Task 10: ProposalDownload component

**Files:**
- Create: `frontend/components/ProposalDownload.tsx`

- [ ] **Step 1: Create the component**

```tsx
// frontend/components/ProposalDownload.tsx
"use client";

import { useState } from "react";

interface ProposalDownloadProps {
  sessionId: string;
}

export default function ProposalDownload({ sessionId }: ProposalDownloadProps) {
  const [loading, setLoading] = useState(false);

  const handleDownload = async () => {
    if (loading) return;
    setLoading(true);
    try {
      const res = await fetch(`/api/backend/proposal/${sessionId}/pdf`);
      if (!res.ok) throw new Error("PDF generation failed");

      const blob = await res.blob();
      const contentDisposition = res.headers.get("content-disposition") ?? "";
      const filenameMatch = contentDisposition.match(/filename="(.+?)"/);
      const filename = filenameMatch?.[1] ?? `proposal-${sessionId.slice(0, 8)}.pdf`;

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("ProposalDownload: error", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleDownload}
      disabled={loading}
      className="mt-2 flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-700 hover:bg-gray-600 text-gray-200 transition-colors disabled:opacity-50"
    >
      <span>{loading ? "⏳" : "📄"}</span>
      <span>{loading ? "Generating PDF..." : "Download as PDF"}</span>
    </button>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/ProposalDownload.tsx
git commit -m "feat: add ProposalDownload button component"
```

---

## Task 11: Wire components into Sidebar

**Files:**
- Modify: `frontend/components/Sidebar.tsx`

- [ ] **Step 1: Read current Sidebar.tsx to find insertion points**

Open [frontend/components/Sidebar.tsx](frontend/components/Sidebar.tsx) and locate:
- The bottom section of the sidebar (below project list)
- The component's state and props

- [ ] **Step 2: Add imports and state to Sidebar**

At the top of `Sidebar.tsx`, add imports:

```typescript
import BriefingButton from "./BriefingButton";
import ProposalWizard from "./ProposalWizard";
```

Inside the Sidebar component, add state:

```typescript
const [proposalOpen, setProposalOpen] = useState(false);
const [proposalSessionId, setProposalSessionId] = useState("");
```

- [ ] **Step 3: Add `onBriefingStream` and `onProposalStream` props to Sidebar**

Update the Sidebar props interface to accept stream callbacks:

```typescript
interface SidebarProps {
  // ... existing props ...
  onBriefingStream?: (raw: string) => void;
  onProposalStream?: (raw: string) => void;
  onProposalSessionId?: (id: string) => void;
}
```

- [ ] **Step 4: Add buttons at bottom of sidebar JSX**

Find the closing `</div>` of the sidebar container and add above it:

```tsx
{/* Productivity tools */}
<div className="border-t border-gray-700 pt-3 mt-3 flex flex-col gap-1">
  <BriefingButton onStream={onBriefingStream ?? (() => {})} />
  <button
    onClick={() => setProposalOpen(true)}
    className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors text-gray-300 hover:text-white hover:bg-gray-700"
  >
    <span>📝</span>
    <span>New Proposal</span>
  </button>
</div>

<ProposalWizard
  open={proposalOpen}
  onClose={() => setProposalOpen(false)}
  onStream={onProposalStream ?? (() => {})}
  onSessionId={(id) => {
    setProposalSessionId(id);
    onProposalSessionId?.(id);
  }}
/>
```

- [ ] **Step 5: Build to check TypeScript**

```
cd e:\atomcamp\freelance-agent\frontend
npm run build 2>&1 | tail -30
```

Expected: no TypeScript errors related to Sidebar

- [ ] **Step 6: Commit**

```bash
git add frontend/components/Sidebar.tsx
git commit -m "feat: wire BriefingButton and ProposalWizard into Sidebar"
```

---

## Task 12: Wire callbacks in ChatWindow / page.tsx

**Files:**
- Modify: `frontend/app/page.tsx` (or wherever Sidebar is rendered)
- Modify: `frontend/components/ChatWindow.tsx`

- [ ] **Step 1: Read page.tsx to understand how Sidebar and ChatWindow are connected**

Open [frontend/app/page.tsx](frontend/app/page.tsx) and identify:
- How messages are added to the chat
- Where `<Sidebar>` is rendered
- How SSE events are currently injected into chat history

- [ ] **Step 2: Add proposal session state and handlers to page.tsx**

In `page.tsx`, add state:

```typescript
const [proposalSessionId, setProposalSessionId] = useState("");
```

Pass to Sidebar:

```tsx
<Sidebar
  {/* existing props */}
  onBriefingStream={(raw) => {
    // Parse raw SSE into chat messages using same logic as useSSE
    // Add as a new chat turn from "producer" agent
    injectSSEStream("briefing", raw);
  }}
  onProposalStream={(raw) => {
    injectSSEStream("proposal", raw);
  }}
  onProposalSessionId={setProposalSessionId}
/>
```

- [ ] **Step 3: Show ProposalDownload after proposal turns**

In `ChatWindow.tsx`, after rendering each agent message, check if it's a final proposal event:

```tsx
{msg.agent === "producer" && msg.type === "final" && proposalSessionId && (
  <ProposalDownload sessionId={proposalSessionId} />
)}
```

Import at top:

```typescript
import ProposalDownload from "./ProposalDownload";
```

- [ ] **Step 4: Build frontend to verify no TypeScript errors**

```
cd e:\atomcamp\freelance-agent\frontend
npm run build 2>&1 | tail -40
```

Expected: build succeeds, 0 TypeScript errors

- [ ] **Step 5: Commit**

```bash
git add frontend/app/page.tsx frontend/components/ChatWindow.tsx
git commit -m "feat: wire briefing and proposal streams into chat, show PDF download button"
```

---

## Task 13: Add structured logging to main.py

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Ensure logging is configured at startup**

In `backend/main.py`, find the logging setup (currently `import logging`). Replace or ensure:

```python
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)
```

- [ ] **Step 2: Add request logging for new endpoints**

The new routers already log via their own `logger = logging.getLogger(__name__)`. Verify `main.py` startup logs the routers:

```python
@app.on_event("startup")
async def startup():
    await init_schema()
    logger.info("startup: schema initialized")
    logger.info("startup: routers registered: chat, setup, files, briefing, proposal")
```

- [ ] **Step 3: Commit**

```bash
git add backend/main.py
git commit -m "chore: configure structured logging for all routes"
```

---

## Task 14: End-to-end verification

- [ ] **Step 1: Start backend**

```
cd e:\atomcamp\freelance-agent\backend
uvicorn main:app --reload --port 8000
```

Expected logs:
```
INFO     startup: schema initialized
INFO     startup: routers registered: chat, setup, files, briefing, proposal
INFO     uvicorn.error: Application startup complete.
```

- [ ] **Step 2: Start frontend**

```
cd e:\atomcamp\freelance-agent\frontend
npm run dev
```

- [ ] **Step 3: Test briefing**

1. Log in with GitHub OAuth
2. Complete setup wizard (if not done)
3. Click "Morning Briefing" in sidebar
4. Expected: SSE stream appears in chat with daily digest

- [ ] **Step 4: Test proposal**

1. Click "New Proposal" in sidebar
2. Fill: Client = "Test Co", Description = "Build a REST API for inventory management", Budget = "$4,000"
3. Click "Generate Proposal"
4. Expected: proposal streams to chat, "Download as PDF" button appears below

- [ ] **Step 5: Test PDF download**

1. Click "Download as PDF"
2. Expected: browser downloads `proposal-XXXXXXXX.pdf`
3. Open PDF — verify it contains the proposal content with correct formatting

- [ ] **Step 6: Test edge cases**

- No projects → briefing returns setup wizard message
- GitHub rate limited → briefing skips GitHub section gracefully
- Missing fields in proposal form → validation error shown in modal

- [ ] **Step 7: Run full test suite**

```
cd e:\atomcamp\freelance-agent\backend
python -m pytest ../tests/ -v --tb=short
```

Expected: all tests pass

- [ ] **Step 8: Final commit**

```bash
git add -A
git commit -m "feat: productivity suite — daily briefing, proposal generator, PDF export"
```
