from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from db import postgres as db


async def get_history(user_id: str, session_id: str, limit: int = 20) -> list[BaseMessage]:
    rows = await db.get_messages(user_id, session_id, limit=limit)
    messages: list[BaseMessage] = []
    for row in rows:
        if row["role"] == "user":
            messages.append(HumanMessage(content=row["content"]))
        else:
            messages.append(AIMessage(content=row["content"]))
    return messages


async def save_exchange(user_id: str, session_id: str, human: str, ai: str) -> None:
    await db.append_message(user_id, session_id, "user", human)
    await db.append_message(user_id, session_id, "assistant", ai)
