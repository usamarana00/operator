from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage
from dotenv import load_dotenv

load_dotenv()

_llm = ChatOpenAI(model="gpt-4o", temperature=0.3)

_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are the final response agent for a freelance project assistant.

Your job is to synthesize information from other agents into a clear, helpful, well-formatted Markdown response.
- Use headers and bullet points for readability
- Highlight urgent deadlines (within 7 days)
- Be concise — the user is a busy developer
- If both project and repo data are available, integrate them naturally
- End with 1-2 actionable next steps
"""),
    ("human", """Original question: {message}

Project Manager Agent output:
{pm_output}

GitHub Agent output:
{github_output}

Chat history:
{history}

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
