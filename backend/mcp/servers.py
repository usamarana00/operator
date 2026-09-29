import requests
from mcp.s3_fs import filesystem_write

# Re-export S3-backed filesystem MCP tool under the original name.
# Callers must now pass user_id as the first argument.

__all__ = [
    "filesystem_write",
    "github_mcp_list_issues",
    "github_mcp_list_prs",
]


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
