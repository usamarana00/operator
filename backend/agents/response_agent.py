from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage
from dotenv import load_dotenv

load_dotenv()

_llm = ChatOpenAI(model="gpt-4o", temperature=0.3)

_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful assistant for a freelance software developer.

You synthesize information from specialist agents into clear, well-formatted Markdown responses.

Rules:
- Use headers and bullet points for readability
- Highlight urgent deadlines (within 7 days) in **bold**
- Be concise — the user is a busy developer
- If project and repo data are both available, integrate them naturally
- For general questions (no project/repo data), just answer helpfully and conversationally
- End with 1-2 actionable next steps when relevant
- Never say "No project data retrieved" or "No repository data retrieved" — just answer from what you have
"""),
    ("human", """Chat history:
{history}

Project Manager Agent output:
{pm_output}

GitHub Agent output:
{github_output}

User question: {message}

Write the final response:
"""),
])


def run_response_agent(
    original_message: str,
    pm_output: str,
    github_output: str,
    history: list[BaseMessage],
) -> str:
    history_str = "\n".join(
        f"{'Human' if m.type == 'human' else 'AI'}: {m.content}" for m in history
    )
    response = (_PROMPT | _llm).invoke({
        "message": original_message,
        "pm_output": pm_output or "No project data retrieved.",
        "github_output": github_output or "No repository data retrieved.",
        "history": history_str,
    })
    return response.content
