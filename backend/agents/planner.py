import json
import re
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage
from dotenv import load_dotenv

load_dotenv()

_llm = ChatOpenAI(model="gpt-4o", temperature=0)

_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a routing agent for a freelance project management assistant.

Classify the user's intent as exactly one of these four values:
- "deadline" — any question about project work, tasks, milestones, deliverables, due dates, deadlines, what the user is working on, project status, what's next, upcoming work
- "repo" — any question about GitHub repositories, commits, pull requests, issues, code changes, branches, repos
- "both" — questions that need BOTH project deadline info AND GitHub repo info
- "general" — ONLY for greetings, small talk, or questions completely unrelated to work, projects, or code

When in doubt, prefer "deadline" over "general". If the user asks about work, projects, or status in any way, use "deadline".

Examples:
- "what am I working on?" → deadline
- "what are my deadlines?" → deadline
- "tell me about my deadlines" → deadline
- "show me my tasks" → deadline
- "what repos are there?" → repo
- "show me open PRs" → repo
- "what's the status of Project Alpha?" → both
- "hello" → general
- "what is Python?" → general

Extract project/repo names if explicitly mentioned, otherwise use null.

Respond with raw JSON only — no markdown, no backticks:
{{"intent": "deadline|repo|both|general", "entities": {{"project": null, "repo": null}}}}
"""),
    ("human", "Chat history:\n{history}\n\nUser message: {message}"),
])


def classify_intent(message: str, history: list[BaseMessage]) -> dict:
    history_str = "\n".join(
        f"{'Human' if m.type == 'human' else 'AI'}: {m.content}" for m in history
    )
    response = (_PROMPT | _llm).invoke({"message": message, "history": history_str})
    content = response.content.strip()

    # Strip markdown code fences if present
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)
    content = content.strip()

    try:
        result = json.loads(content)
        if result.get("intent") not in ("deadline", "repo", "both", "general"):
            result["intent"] = "general"
        return result
    except json.JSONDecodeError:
        return {"intent": "general", "entities": {"project": None, "repo": None}}
