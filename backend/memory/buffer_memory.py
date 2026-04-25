from langchain.memory import ConversationBufferMemory
from langchain_core.messages import BaseMessage

_sessions: dict[str, ConversationBufferMemory] = {}


def get_buffer_memory(session_id: str) -> ConversationBufferMemory:
    if session_id not in _sessions:
        _sessions[session_id] = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            max_token_limit=2000,
        )
    return _sessions[session_id]


def get_history(session_id: str) -> list[BaseMessage]:
    memory = get_buffer_memory(session_id)
    return memory.chat_memory.messages


def save_exchange(session_id: str, human: str, ai: str) -> None:
    memory = get_buffer_memory(session_id)
    memory.chat_memory.add_user_message(human)
    memory.chat_memory.add_ai_message(ai)
