# Repo & Dependency Cleanup Design

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development or superpowers:executing-plans to implement the plan generated from this spec.

**Goal:** Consolidate the project onto one dependency manager (uv), remove dead/unused dependencies and files, and fix a latent production bug in PDF export — without changing agent architecture, DB design, or adding features.

**Context:** The `fix/authenticity-docs-honesty` branch already made the project's docs and agent behavior match reality (LangGraph actually runs, GitHub "MCP" calls are real, README matches the Postgres/auth/S3 stack, tests are offline/mocked, CI runs on push). This spec covers a second pass: the repo currently carries two disagreeing Python dependency manifests, several dependencies nothing imports, one dependency that's used but never declared, and a docs/onboarding gap.

**Confirmed during investigation (not assumptions):**
- Single DB stack in actual use: Neon Postgres (`asyncpg`) for structured data + `pgvector` for embeddings, one embedding model (`text-embedding-3-small`). No ChromaDB or any other vector engine is imported anywhere in `backend/`. Live-tested: Postgres connection works, `vector` extension installed, all 7 expected tables present.
- `chromadb` / `langchain-chroma` exist only as dead entries in the unused root `pyproject.toml`/`uv.lock`, plus historical mentions in `.gitignore` (now removed) and two old planning docs (left as-is, they're history).
- `backend/routers/proposal.py:91` imports `weasyprint` for PDF export, but `weasyprint` is declared in **neither** dependency file — a clean install breaks that endpoint. `weasyprint` also needs native system libraries (Pango/cairo) that Render's plain `pip install` build wouldn't provide anyway.
- `pyproject.toml` declares both `jwt>=1.4.0` (wrong PyPI package — not PyJWT) and `pyjwt==2.9.0`; `backend/auth.py` does `import jwt` expecting PyJWT. If `pyproject.toml` becomes canonical without fixing this, `uv sync` risks installing the wrong `jwt` package.
- `pypdf` and `slowapi` are declared in both dependency files with zero usages anywhere in `backend/`.
- `frontend/.env.local.example` is referenced by `.gitignore` (`!frontend/.env.local.example`) and by the README quickstart (`cp frontend/.env.local.example frontend/.env.local`) but does not exist — onboarding breaks at that step.
- Live-tested: `OPENAI_API_KEY` in the pasted `.env` returns `401 invalid_api_key` from `/v1/models`. This is an environment/credentials issue, not something a repo cleanup can fix — noted here so it isn't mistaken for a code bug during verification, not in scope to "fix" (no valid key to swap in).

**Decisions locked in with the user:**
- uv (`pyproject.toml` + `uv.lock`) becomes the single canonical dependency manager. `backend/requirements.txt` is deleted. CI, `render.yaml`, and README are updated to use `uv sync` / `uv run`.
- `weasyprint` is replaced with `fpdf2` (pure-Python, no native system libraries) rather than fixing weasyprint's system-dependency requirement on Render.
- `slowapi` is removed as dead weight (not wired up into rate limiting — out of scope to build that now).
- `docs/superpowers/` planning docs stay in the repo (kept for portfolio/process visibility).
- Agent naming (`project_manager.py` vs `producer_agent.py`) is explicitly out of scope for this pass.

---

## File Structure

- `pyproject.toml` (modify) — canonical dependency list: drop `chromadb`, `langchain-chroma`, `jwt`, `pypdf`, `slowapi`, `weasyprint`(never was there); add `fpdf2`.
- `uv.lock` (regenerate via `uv lock`).
- `backend/requirements.txt` (delete).
- `backend/routers/proposal.py` (modify) — swap the `weasyprint.HTML(...).write_pdf()` call for `fpdf2`.
- `frontend/.env.local.example` (create).
- `.github/workflows/ci.yml` (modify) — `uv sync` + `uv run pytest` / `uv run` for the frontend step stays npm-based (Node, not uv).
- `render.yaml` (modify) — buildCommand/startCommand to uv.
- `README.md` (modify) — quickstart backend section to uv commands.
- `.gitignore` (done) — dead `backend/data/chroma_db/` line already removed.
- `tests/test_proposal_pdf.py` (create) — asserts the PDF endpoint returns `application/pdf` via the fpdf2 path.

---

## Verification plan

- `uv sync` installs cleanly with no `chromadb`/native-build steps.
- `uv run pytest tests/ -v` — full existing suite stays green, plus the new PDF test.
- `uv run uvicorn main:app` boots locally (manual smoke check — DB confirmed reachable; OpenAI-dependent paths will still fail until the key is replaced, which is expected and out of scope).
- CI workflow passes on push (or the equivalent commands are run locally to confirm before pushing, since triggering CI itself is a separate action).
- `grep -rn "weasyprint\|chromadb\|langchain-chroma" pyproject.toml uv.lock backend/` returns nothing.

---

## Self-Review Notes

- **Scope check:** every item traces back either to something confirmed by grep/live investigation in this session, or to an explicit user decision from the clarifying questions. Nothing here is speculative "might as well" cleanup.
- **Placeholder scan:** no TBDs — the OpenAI key issue is documented as explicitly out of scope rather than left ambiguous.
- **Consistency:** `weasyprint`'s system-library problem is the stated reason for the `fpdf2` swap, not an unrelated aside; matches the user's chosen option.
- **Deferred (not in this plan):** OpenAI key replacement (needs a real key from the user), agent renaming, wiring up rate limiting, any DB/architecture change (none was needed — stack is already a single Postgres+pgvector setup).
