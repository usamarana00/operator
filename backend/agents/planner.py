import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage
from dotenv import load_dotenv

load_dotenv()

_llm = ChatOpenAI(model="gpt-4o", temperature=0)

_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a routing agent for a freelance project management assistant.

Classify the user's intent as exactly one of:
- "deadline": questions about project deadlines, milestones, tasks, deliverables, due dates
- "repo": questions about GitHub repos, commits, pull requests, issues, code changes
- "both": questions that require both project deadline info AND repo info
- "general": greetings, meta questions, or anything not about projects or repos

Also extract named entities if present.

Respond ONLY with valid JSON in this exact format:
{{"intent": "<classification>", "entities": {{"project": "<name or null>", "repo": "<name or null>"}}}}
"""),
    ("human", "Chat history:\n{history}\n\nUser message: {message}"),
])


def classify_intent(message: str, history: list[BaseMessage]) -> dict:
    history_str = "\n".join(
        f"{'Human' if m.type == 'human' else 'AI'}: {m.content}" for m in history
    )
    response = (_PROMPT | _llm).invoke({"message": message, "history": history_str})
    try:
        return json.loads(response.content)
    except json.JSONDecodeError:
        return {"intent": "general", "entities": {"project": None, "repo": None}}
