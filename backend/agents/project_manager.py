from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage
from langchain_core.vectorstores import VectorStoreRetriever
from db.sqlite import get_milestones
from dotenv import load_dotenv

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


def run_pm_agent(
    message: str,
    retriever: VectorStoreRetriever,
    history: list[BaseMessage],
    db_path: str = "backend/data/projects.db",
) -> str:
    docs = retriever.invoke(message)
    context = "\n\n".join(d.page_content for d in docs)

    milestones = get_milestones(db_path)
    milestones_str = "\n".join(
        f"- {m['title']} (due {m['due_date']}, {'done' if m['completed'] else 'pending'})"
        for m in milestones
    )

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
