import asyncio
import json
import logging
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("freelance_agent")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from auth import AuthMiddleware, get_user_id, get_github_token
from db.postgres import init_schema, close_pool, get_projects, get_milestones
from routers.setup import router as setup_router
from routers.files import router as files_router
from agents.planner import classify_intent
from agents.project_manager import run_pm_agent
from agents.github_agent import run_github_agent
from agents.response_agent import run_response_agent
from memory.buffer_memory import get_history, save_exchange
from mcp.servers import filesystem_write

_FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")

app = FastAPI(title="Freelance Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[_FRONTEND_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthMiddleware)

app.include_router(setup_router)
app.include_router(files_router)


@app.on_event("startup")
async def startup():
    await init_schema()
    logger.info("DB schema ready")


@app.on_event("shutdown")
async def shutdown():
    await close_pool()


class ChatRequest(BaseModel):
    message: str
    session_id: str = ""


def _sse(agent: str, event_type: str, content: str) -> str:
    return f"data: {json.dumps({'agent': agent, 'type': event_type, 'content': content})}\n\n"


async def _stream(message: str, session_id: str, user_id: str, github_token: str):
    history = await get_history(user_id, session_id)
    logger.info("── NEW REQUEST [user=%s session=%s] ──", user_id[:8], session_id[:8])

    # ── Planner ──────────────────────────────────────────
    yield _sse("planner", "thinking", "Analyzing your request...")
    await asyncio.sleep(0)
    routing = classify_intent(message, history)
    intent = routing.get("intent", "general")
    entities = routing.get("entities", {})
    intent_labels = {
        "deadline": "project deadlines & milestones",
        "repo":     "GitHub repository data",
        "both":     "deadlines + GitHub data",
        "general":  "general conversation",
    }
    logger.info("[Planner] intent=%s entities=%s", intent, entities)
    yield _sse("planner", "event", f"Intent classified → {intent_labels.get(intent, intent)}")
    if entities.get("project"):
        yield _sse("planner", "event", f"Entity detected → project: \"{entities['project']}\"")

    pm_output = ""
    github_output = ""

    # ── PM Agent ─────────────────────────────────────────
    if intent in ("deadline", "both"):
        yield _sse("pm", "thinking", "Engaging PM Agent...")
        await asyncio.sleep(0)

        milestones = await get_milestones(user_id)
        logger.info("[PM Agent] milestones=%d", len(milestones))
        yield _sse("pm", "event", f"DB › Queried milestones → {len(milestones)} records found")

        pm_output = await run_pm_agent(message, user_id, history)
        logger.info("[PM Agent] output=%d chars", len(pm_output))

        await filesystem_write(user_id, "pm_queries.txt", f"Query: {message}\nResult: {pm_output}\n---\n")
        yield _sse("mcp", "event", "S3 MCP › Wrote query log to notes/pm_queries.txt")
        yield _sse("pm", "data", pm_output)

    # ── GitHub Agent ──────────────────────────────────────
    if intent in ("repo", "both"):
        yield _sse("github", "thinking", "Engaging GitHub Agent...")
        await asyncio.sleep(0)

        projects = await get_projects(user_id)
        repo_url = None
        entity_project = (entities or {}).get("project") or (entities or {}).get("repo") or ""
        if entity_project:
            term = entity_project.lower()
            for p in projects:
                name_match = term in p["name"].lower()
                repo_slug = (p.get("repo_name") or "").replace("-", " ").lower()
                if name_match or term in repo_slug:
                    owner = p.get("repo_owner", "")
                    repo = p.get("repo_name", "")
                    repo_url = f"https://github.com/{owner}/{repo}" if owner and repo else None
                    break
        if not repo_url and projects:
            p = projects[0]
            owner = p.get("repo_owner", "")
            repo = p.get("repo_name", "")
            repo_url = f"https://github.com/{owner}/{repo}" if owner and repo else None

        logger.info("[GitHub Agent] repo_url=%s", repo_url)
        if repo_url:
            yield _sse("github", "event", f"GitHub API › Fetching data from {repo_url}")
        yield _sse("mcp", "event", "GitHub MCP › Structured repo access via MCP tool layer")

        github_output = run_github_agent(message, repo_url, history, github_token=github_token)
        logger.info("[GitHub Agent] output=%d chars", len(github_output))
        yield _sse("github", "event", "GitHub API › Data retrieved and parsed")
        yield _sse("github", "data", github_output)

    # ── Response Agent ────────────────────────────────────
    yield _sse("response", "thinking", "Synthesizing final answer...")
    await asyncio.sleep(0)

    if intent == "general":
        yield _sse("response", "event", "General query → answering from conversation context")

    final = run_response_agent(message, pm_output, github_output, history)
    logger.info("[Response Agent] final=%d chars", len(final))
    yield _sse("response", "event", "Memory › Saving exchange to chat history")
    yield _sse("response", "final", final)

    await save_exchange(user_id, session_id, message, final)
    yield _sse("system", "done", "")


@app.post("/chat")
async def chat(req: ChatRequest, request: Request):
    user_id = get_user_id(request)
    github_token = get_github_token(request)
    session_id = req.session_id or str(uuid.uuid4())
    return StreamingResponse(
        _stream(req.message, session_id, user_id, github_token),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Session-Id": session_id},
    )


@app.get("/projects")
async def projects(request: Request):
    user_id = get_user_id(request)
    return {
        "projects": await get_projects(user_id),
        "milestones": await get_milestones(user_id),
    }


@app.get("/health")
def health():
    return {"status": "ok"}
