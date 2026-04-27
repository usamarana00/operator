import asyncio
import json
import logging
import os
import sys
import uuid

# Ensure backend/ is on the path when run via `uvicorn backend.main:app`
sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("freelance_agent")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from db.sqlite import get_projects, get_milestones, init_db
from routers.setup import router as setup_router
from agents.planner import classify_intent
from agents.project_manager import run_pm_agent
from agents.github_agent import run_github_agent
from agents.response_agent import run_response_agent
from memory.buffer_memory import get_history, save_exchange
from rag.loader import load_documents
from rag.chunker import chunk_documents
from rag.retriever import build_retriever, load_retriever
from mcp.servers import filesystem_list, filesystem_write

_BASE = os.path.dirname(__file__)
DB_PATH = os.path.join(_BASE, "data", "projects.db")
CHROMA_DIR = os.path.join(_BASE, "data", "chroma_db")
DATA_DIR = os.path.join(_BASE, "data")

app = FastAPI(title="Freelance Agent API")
app.include_router(setup_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    session_id: str = ""


def _get_retriever():
    if os.path.exists(CHROMA_DIR) and os.listdir(CHROMA_DIR):
        return load_retriever(CHROMA_DIR)
    docs = load_documents(DATA_DIR)
    chunks = chunk_documents(docs)
    return build_retriever(chunks, persist_dir=CHROMA_DIR)


def _sse(agent: str, event_type: str, content: str) -> str:
    return f"data: {json.dumps({'agent': agent, 'type': event_type, 'content': content})}\n\n"


async def _stream(message: str, session_id: str):
    init_db(DB_PATH)
    history = get_history(session_id)
    logger.info("── NEW REQUEST [session=%s] ──────────────────────", session_id[:8])
    logger.info("User: %s", message)
    logger.info("History length: %d messages", len(history))

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

        yield _sse("pm", "event", "RAG › Searching project documents (Chroma vector DB)...")
        retriever = _get_retriever()
        docs = retriever.invoke(message)
        logger.info("[PM Agent] RAG retrieved %d chunks", len(docs))
        yield _sse("pm", "event", f"RAG › Retrieved {len(docs)} relevant document chunks")

        milestones = get_milestones(DB_PATH)
        logger.info("[PM Agent] SQLite milestones=%d", len(milestones))
        yield _sse("pm", "event", f"SQLite › Queried milestones table → {len(milestones)} records found")

        pm_output = run_pm_agent(message, retriever, history, db_path=DB_PATH)
        logger.info("[PM Agent] output length=%d chars", len(pm_output))

        filesystem_write("pm_queries.txt", f"Query: {message}\nResult: {pm_output}\n---\n")
        logger.info("[MCP Filesystem] wrote pm_queries.txt")
        yield _sse("mcp", "event", "Filesystem MCP › Wrote query log to data/notes/pm_queries.txt")

        yield _sse("pm", "data", pm_output)

    # ── GitHub Agent ──────────────────────────────────────
    if intent in ("repo", "both"):
        yield _sse("github", "thinking", "Engaging GitHub Agent...")
        await asyncio.sleep(0)

        projects = get_projects(DB_PATH)
        repo_url = None
        # Combine project + repo entity into one search term
        entity_project = (entities or {}).get("project") or (entities or {}).get("repo") or ""
        if entity_project:
            term = entity_project.lower()
            for p in projects:
                name_match = term in p["name"].lower()
                # also match against repo URL slug ("paki-portal" -> "paki portal")
                url_slug = p["repo_url"].rstrip("/").split("/")[-1].replace("-", " ").lower()
                slug_match = term in url_slug or any(w in url_slug for w in term.split())
                if name_match or slug_match:
                    repo_url = p["repo_url"]
                    break
        if not repo_url and projects:
            repo_url = projects[0]["repo_url"]

        logger.info("[GitHub Agent] repo_url=%s", repo_url)
        if repo_url:
            yield _sse("github", "event", f"GitHub API › Fetching commits, PRs, issues from {repo_url}")
        yield _sse("mcp", "event", "GitHub MCP › Structured repo access via MCP tool layer")

        github_output = run_github_agent(message, repo_url, history)
        logger.info("[GitHub Agent] output length=%d chars", len(github_output))
        yield _sse("github", "event", "GitHub API › Data retrieved and parsed")
        yield _sse("github", "data", github_output)

    # ── Response Agent ────────────────────────────────────
    yield _sse("response", "thinking", "Synthesizing final answer...")
    await asyncio.sleep(0)

    if intent == "general":
        yield _sse("response", "event", "General query → answering directly from conversation context")

    final = run_response_agent(message, pm_output, github_output, history)
    logger.info("[Response Agent] final response length=%d chars", len(final))
    yield _sse("response", "event", "Memory › Saving exchange to ConversationBufferMemory")
    yield _sse("response", "final", final)

    save_exchange(session_id, message, final)
    logger.info("── REQUEST COMPLETE ──────────────────────────────")
    yield _sse("system", "done", "")


@app.post("/chat")
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    return StreamingResponse(
        _stream(req.message, session_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Session-Id": session_id},
    )


@app.get("/projects")
def projects():
    init_db(DB_PATH)
    return {
        "projects": get_projects(DB_PATH),
        "milestones": get_milestones(DB_PATH),
    }


@app.get("/health")
def health():
    return {"status": "ok"}
