import os
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv

from graph.state import AgentState
from agents.planner import classify_intent
from agents.project_manager import run_pm_agent
from agents.github_agent import run_github_agent
from agents.response_agent import run_response_agent
from memory.buffer_memory import get_history, save_exchange
from db.postgres import get_projects

load_dotenv()


async def _planner_node(state: AgentState) -> AgentState:
    result = classify_intent(state["message"], state["history"])
    return {**state, "intent": result["intent"], "entities": result.get("entities", {})}


async def _pm_node(state: AgentState) -> AgentState:
    output = await run_pm_agent(state["message"], state["user_id"], state["history"])
    return {**state, "pm_output": output}


async def _github_node(state: AgentState) -> AgentState:
    projects = await get_projects(state["user_id"])
    repo_url = None
    entity_project = (state.get("entities") or {}).get("project") or ""
    for p in projects:
        if entity_project and entity_project.lower() in p["name"].lower():
            owner = p.get("repo_owner", "")
            repo = p.get("repo_name", "")
            repo_url = f"https://github.com/{owner}/{repo}" if owner and repo else None
            break
    if not repo_url and projects:
        p = projects[0]
        owner = p.get("repo_owner", "")
        repo = p.get("repo_name", "")
        repo_url = f"https://github.com/{owner}/{repo}" if owner and repo else None

    output = run_github_agent(
        state["message"], repo_url, state["history"],
        github_token=state.get("github_token", ""),
    )
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


def _route_after_pm(state: AgentState) -> str:
    """After the PM node, 'both' intents continue to GitHub; everyone else synthesizes."""
    return "github" if state.get("intent") == "both" else "response"


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
    graph.add_conditional_edges("pm", _route_after_pm, {
        "github": "github",
        "response": "response",
    })
    graph.add_edge("github", "response")
    graph.add_edge("response", END)

    return graph.compile()


_compiled_graph = _build_graph()


async def run_workflow(
    message: str,
    session_id: str,
    user_id: str,
    github_token: str,
) -> str:
    history = await get_history(user_id, session_id)
    initial_state: AgentState = {
        "message": message,
        "session_id": session_id,
        "user_id": user_id,
        "github_token": github_token,
        "history": history,
        "intent": "",
        "entities": {},
        "pm_output": "",
        "github_output": "",
        "final_response": "",
    }
    result = await _compiled_graph.ainvoke(initial_state)
    final = result["final_response"]
    await save_exchange(user_id, session_id, message, final)
    return final
