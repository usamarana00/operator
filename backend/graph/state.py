from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
import operator


class AgentState(TypedDict):
    message: str
    session_id: str
    history: Annotated[list[BaseMessage], operator.add]
    intent: str
    entities: dict
    pm_output: str
    github_output: str
    final_response: str
