import os
import requests
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
NOTES_DIR = DATA_DIR / "notes"
NOTES_DIR.mkdir(exist_ok=True)


# --- Filesystem MCP ---

def filesystem_read(file_path: str) -> str:
    target = DATA_DIR / file_path
    if not target.exists():
        return f"File not found: {file_path}"
    return target.read_text(encoding="utf-8")


def filesystem_write(file_path: str, content: str) -> str:
    target = NOTES_DIR / file_path
    target.write_text(content, encoding="utf-8")
    return f"Written to {target}"


def filesystem_list(directory: str = "projects") -> list[str]:
    target = DATA_DIR / directory
    if not target.exists():
        return []
    return [f.name for f in target.iterdir() if f.is_file()]


# --- GitHub MCP ---

def github_mcp_list_issues(owner: str, repo: str, token: str = "") -> list[dict]:
    headers = {"Authorization": f"token {token}"} if token else {}
    url = f"https://api.github.com/repos/{owner}/{repo}/issues?state=open&per_page=10"
    r = requests.get(url, headers=headers, timeout=10)
    if r.status_code != 200:
        return []
    return [
        {"number": i["number"], "title": i["title"], "state": i["state"]}
        for i in r.json()
        if "pull_request" not in i
    ]


def github_mcp_list_prs(owner: str, repo: str, token: str = "") -> list[dict]:
    headers = {"Authorization": f"token {token}"} if token else {}
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state=open&per_page=10"
    r = requests.get(url, headers=headers, timeout=10)
    if r.status_code != 200:
        return []
    return [
        {"number": p["number"], "title": p["title"], "user": p["user"]["login"]}
        for p in r.json()
    ]


MCP_TOOLS = {
    "filesystem_read": filesystem_read,
    "filesystem_write": filesystem_write,
    "filesystem_list": filesystem_list,
    "github_list_issues": github_mcp_list_issues,
    "github_list_prs": github_mcp_list_prs,
}
