import os
import requests
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage
from dotenv import load_dotenv

load_dotenv()

_llm = ChatOpenAI(model="gpt-4o", temperature=0)
_GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
_TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a GitHub assistant for a freelance developer.
Summarize the repository data clearly. Highlight open PRs, unresolved issues,
and recent commit activity. Be concise and actionable.
If no repo data is available, say so and suggest what info is needed."""),
    ("human", """Chat history:
{history}

GitHub data:
{github_data}

Tavily search results:
{search_results}

User question: {message}
"""),
])


def _parse_repo(repo_url: str | None) -> tuple[str, str] | None:
    if not repo_url:
        return None
    parts = repo_url.rstrip("/").split("/")
    if len(parts) < 2:
        return None
    return parts[-2], parts[-1]


def _fetch_github_data(owner: str, repo: str) -> str:
    headers = {"Authorization": f"token {_GITHUB_TOKEN}"} if _GITHUB_TOKEN else {}
    base = f"https://api.github.com/repos/{owner}/{repo}"

    def get(url: str) -> list:
        r = requests.get(url, headers=headers, timeout=10)
        return r.json() if r.status_code == 200 else []

    commits = get(f"{base}/commits?per_page=5")
    prs = get(f"{base}/pulls?state=open&per_page=5")
    issues = get(f"{base}/issues?state=open&per_page=5")

    lines = [f"Repository: {owner}/{repo}"]

    lines.append("\nRecent Commits:")
    for c in commits[:5]:
        if isinstance(c, dict) and "commit" in c:
            msg = c["commit"]["message"].split("\n")[0]
            author = c["commit"]["author"]["name"]
            lines.append(f"  - {msg} ({author})")

    lines.append("\nOpen Pull Requests:")
    for pr in prs[:5]:
        if isinstance(pr, dict):
            lines.append(f"  - #{pr.get('number')} {pr.get('title')}")

    lines.append("\nOpen Issues:")
    for issue in issues[:5]:
        if isinstance(issue, dict) and "pull_request" not in issue:
            lines.append(f"  - #{issue.get('number')} {issue.get('title')}")

    return "\n".join(lines)


def _tavily_search(query: str) -> str:
    if not _TAVILY_API_KEY:
        return "Tavily search unavailable (no API key)."
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=_TAVILY_API_KEY)
        results = client.search(query, max_results=3)
        return "\n".join(r["content"][:200] for r in results.get("results", []))
    except Exception:
        return "Tavily search failed."


def run_github_agent(
    message: str,
    repo_url: str | None,
    history: list[BaseMessage],
) -> str:
    parsed = _parse_repo(repo_url)
    github_data = _fetch_github_data(*parsed) if parsed else "No repository URL provided."
    search_results = (
        _tavily_search(message)
        if any(w in message.lower() for w in ("how", "fix", "best", "what is"))
        else "N/A"
    )

    history_str = "\n".join(
        f"{'Human' if m.type == 'human' else 'AI'}: {m.content}" for m in history
    )

    response = (_PROMPT | _llm).invoke({
        "message": message,
        "github_data": github_data,
        "search_results": search_results,
        "history": history_str,
    })
    return response.content
