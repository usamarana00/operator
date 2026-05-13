from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage
from dotenv import load_dotenv

from db import postgres as db
from rag.retriever import retrieve

load_dotenv()

_llm = ChatOpenAI(model="gpt-4o", temperature=0)

_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a project management assistant for a freelance developer.

You have access to:
1. Retrieved project documents (specs, contracts, notes)
2. Structured deadline data from the database

Answer the user's question clearly and concisely. List deadlines with dates.
If nothing is relevant, say so honestly.
"""),
    ("human", """Chat history:
{history}

Retrieved documents:
{context}

Database milestones:
{milestones}

User question: {message}
"""),
])


async def run_pm_agent(
    message: str,
    user_id: str,
    history: list[BaseMessage],
) -> str:
    chunks = await retrieve(user_id=user_id, query=message, k=4)
    context = "\n\n".join(chunks) if chunks else "No project documents indexed yet."

    milestones = await db.get_milestones(user_id)
    milestones_str = "\n".join(
        f"- {m['title']} (due {m['due_date']}, {m['status']})"
        for m in milestones
    ) or "No milestones found."

    history_str = "\n".join(
        f"{'Human' if m.type == 'human' else 'AI'}: {m.content}" for m in history
    )

    response = (_PROMPT | _llm).invoke({
        "message": message,
        "context": context,
        "milestones": milestones_str,
        "history": history_str,
    })
    return response.content
