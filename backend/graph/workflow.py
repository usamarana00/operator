import os
from langgraph.graph import StateGraph, END

from graph.state import AgentState
from agents.planner import classify_intent
from agents.project_manager import run_pm_agent
from agents.github_agent import run_github_agent
from agents.response_agent import run_response_agent
from memory.buffer_memory import get_history, save_exchange
from rag.loader import load_documents
from rag.chunker import chunk_documents
from rag.retriever import build_retriever, load_retriever
from db.sqlite import get_projects, init_db
from dotenv import load_dotenv

load_dotenv()

_BASE = os.path.dirname(__file__)
DATA_DIR = os.path.join(_BASE, '..', 'data')
DB_PATH = os.path.join(_BASE, '..', 'data', 'projects.db')
CHROMA_DIR = os.path.join(_BASE, '..', 'data', 'chroma_db')


def _get_retriever():
    if os.path.exists(CHROMA_DIR) and os.listdir(CHROMA_DIR):
        return load_retriever(CHROMA_DIR)
    docs = load_documents(DATA_DIR)
    chunks = chunk_documents(docs)
    return build_retriever(chunks, persist_dir=CHROMA_DIR)


def _planner_node(state: AgentState) -> AgentState:
    result = classify_intent(state["message"], state["history"])
    return {**state, "intent": result["intent"], "entities": result.get("entities", {})}


def _pm_node(state: AgentState) -> AgentState:
    retriever = _get_retriever()
    output = run_pm_agent(state["message"], retriever, state["history"], db_path=DB_PATH)
    return {**state, "pm_output": output}


def _github_node(state: AgentState) -> AgentState:
    projects = get_projects(DB_PATH)
    repo_url = None
    entity_project = (state.get("entities") or {}).get("project") or ""
    for p in projects:
        if entity_project and entity_project.lower() in p["name"].lower():
            repo_url = p["repo_url"]
            break
    if not repo_url and projects:
        repo_url = projects[0]["repo_url"]
    output = run_github_agent(state["message"], repo_url, state["history"])
    return {**state, "github_output": output}


def _response_node(state: AgentState) -> AgentState:
    final = run_response_agent(
        original_message=state["message"],
        pm_output=state.get("pm_output", ""),
        github_output=state.get("github_output", ""),
        history=state["history"],
    )
    return {**state, "final_response": final}


def _route(state: AgentState) -> str:
    intent = state.get("intent", "general")
    if intent == "deadline":
        return "pm"
    if intent == "repo":
        return "github"
    if intent == "both":
        return "pm"
    return "response"


def _build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("planner", _planner_node)
    graph.add_node("pm", _pm_node)
    graph.add_node("github", _github_node)
    graph.add_node("response", _response_node)

    graph.set_entry_point("planner")
    graph.add_conditional_edges("planner", _route, {
        "pm": "pm",
        "github": "github",
        "response": "response",
    })
    graph.add_edge("pm", "response")
    graph.add_edge("github", "response")
    graph.add_edge("response", END)

    return graph.compile()


_compiled_graph = _build_graph()


def run_workflow(message: str, session_id: str) -> str:
    init_db(DB_PATH)
    history = get_history(session_id)
    initial_state: AgentState = {
        "message": message,
        "session_id": session_id,
        "history": history,
        "intent": "",
        "entities": {},
        "pm_output": "",
        "github_output": "",
        "final_response": "",
    }
    result = _compiled_graph.invoke(initial_state)
    final = result["final_response"]
    save_exchange(session_id, message, final)
    return final
