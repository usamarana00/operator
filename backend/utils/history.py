from langchain_core.messages import BaseMessage


def format_history(history: list[BaseMessage]) -> str:
    return "\n".join(
        f"{'Human' if m.type == 'human' else 'AI'}: {m.content}" for m in history
    )
