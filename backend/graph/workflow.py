def _resolve_repo_url(entity_project: str, projects: list[dict]) -> str | None:
    """Pick a repo URL from the user's projects, matching the named entity by
    project name or repo slug, falling back to the first project."""
    def url_for(p: dict) -> str | None:
        owner = p.get("repo_owner", "")
        repo = p.get("repo_name", "")
        return f"https://github.com/{owner}/{repo}" if owner and repo else None

    term = (entity_project or "").lower()
    if term:
        for p in projects:
            name_match = term in p["name"].lower()
            repo_slug = (p.get("repo_name") or "").replace("-", " ").lower()
            if name_match or term in repo_slug:
                return url_for(p)
    if projects:
        return url_for(projects[0])
    return None
