# Repo & Dependency Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate the project onto a single dependency manager (uv), remove dead/unused/wrong dependencies, and fix a latent production bug in PDF export — with no changes to agent architecture, DB design, or features.

**Architecture:** `pyproject.toml` + `uv.lock` at repo root become the sole Python dependency manifest; `backend/requirements.txt` is deleted. `weasyprint` (undeclared dependency, needs native system libraries Render can't provide) is replaced with `fpdf2` (pure Python) in the proposal-PDF endpoint. CI, `render.yaml`, and README are updated to drive the backend via `uv run` / `uv sync` instead of `pip install -r requirements.txt`.

**Tech Stack:** uv (dependency manager), FastAPI, fpdf2, pytest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-25-repo-dep-cleanup-design.md`

## Global Constraints

- uv (`pyproject.toml` + `uv.lock`) is canonical; `backend/requirements.txt` is deleted, not kept in sync.
- `weasyprint` is replaced by `fpdf2`, not fixed in place — no native system libraries in the dependency set.
- `slowapi` is removed, not wired up — rate limiting is out of scope.
- `docs/superpowers/` planning docs and agent file naming (`project_manager.py` / `producer_agent.py`) are untouched — explicitly out of scope.
- Verified in this session (do not re-derive): uv performs upward directory discovery for `pyproject.toml` — running `uv sync` / `uv run` from `backend/` (Render's `rootDir`) correctly finds the root project without any `--project` flag or `cd`.

---

## File Structure

- `pyproject.toml` (modify) — drop `chromadb`, `langchain-chroma`, `jwt`, `pypdf`, `slowapi`; add `fpdf2`.
- `uv.lock` (regenerate).
- `backend/requirements.txt` (delete).
- `backend/routers/proposal.py` (modify) — extract a `_render_pdf(content: str) -> bytes` helper built on `fpdf2`; drop the unused `html` import.
- `tests/test_proposal_pdf.py` (create) — unit test for `_render_pdf`.
- `frontend/.env.local.example` (create).
- `.github/workflows/ci.yml` (modify) — backend job installs/runs via uv.
- `render.yaml` (modify) — buildCommand/startCommand via uv.
- `README.md` (modify) — backend quickstart (lines ~118-124) and "Running tests" (lines ~223-227) use uv commands.

---

## Task 1: Make pyproject.toml the clean, canonical dependency manifest

**Files:**
- Modify: `pyproject.toml`
- Regenerate: `uv.lock`
- Delete: `backend/requirements.txt`

- [ ] **Step 1: Remove the dead/wrong dependencies**

Run from the repo root:
```bash
uv remove chromadb langchain-chroma pypdf slowapi jwt
```
Expected: `pyproject.toml`'s `dependencies` list no longer contains `chromadb`, `langchain-chroma`, `pypdf`, `slowapi`, or `jwt` (the wrong non-PyJWT package); `pyjwt==2.9.0` remains. `uv.lock` is rewritten to match.

- [ ] **Step 2: Add fpdf2**

Run:
```bash
uv add fpdf2
```
Expected: a `fpdf2` entry with a pinned version is added to `pyproject.toml`'s `dependencies`, and `uv.lock` is updated.

- [ ] **Step 3: Verify the environment installs clean**

Run: `uv sync`
Expected: no errors; `uv pip list 2>/dev/null | grep -i chroma` and `uv pip list 2>/dev/null | grep -i weasyprint` both return nothing; `uv pip list 2>/dev/null | grep -i fpdf` shows `fpdf2`.

- [ ] **Step 4: Delete the now-redundant requirements.txt**

Run:
```bash
git rm backend/requirements.txt
```
Expected: file removed. (CI and `render.yaml` still reference it until Tasks 4-5 — that's fixed before this branch is pushed, not before this commit.)

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: consolidate on uv, drop chromadb/pypdf/slowapi/stray-jwt, add fpdf2"
```

---

## Task 2: Replace weasyprint with fpdf2 in the proposal-PDF endpoint

**Problem:** `backend/routers/proposal.py:91` calls `weasyprint.HTML(...).write_pdf()`, but `weasyprint` was never declared in either dependency file (a clean install breaks this endpoint), and it additionally needs native system libraries (Pango/cairo) that Render's plain `pip install`/`uv sync` build won't provide. `fpdf2` is pure Python — no native deps, no separate system-library problem.

**Files:**
- Modify: `backend/routers/proposal.py`
- Test: `tests/test_proposal_pdf.py` (create)

**Interfaces:**
- Produces: `_render_pdf(content: str) -> bytes` in `backend/routers/proposal.py` — takes the plain-text proposal content, returns PDF bytes. Used only inside the `proposal_pdf` route; no other task depends on it.

- [ ] **Step 1: Write the failing test**

Create `tests/test_proposal_pdf.py`:
```python
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from routers.proposal import _render_pdf


def test_render_pdf_returns_pdf_bytes():
    pdf_bytes = _render_pdf("Proposal for Acme Corp\n\nBudget: $5,000\nTimeline: 2 weeks")
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")


def test_render_pdf_handles_empty_content():
    pdf_bytes = _render_pdf("")
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_proposal_pdf.py -v`
Expected: FAIL — `ImportError: cannot import name '_render_pdf' from 'routers.proposal'`.

- [ ] **Step 3: Add `_render_pdf` and wire it into the route**

In `backend/routers/proposal.py`, remove the `import html` line (top of file — becomes unused), then replace the `try`/`except` block inside `proposal_pdf` (currently lines ~89-113, the block starting `try:` / `from weasyprint import HTML` through the `except Exception as exc:` fallback) so the `try` body reads:
```python
    try:
        pdf = _render_pdf(content)
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="proposal-{session_id[:8]}.pdf"'},
        )
    except Exception as exc:
        logger.warning("proposal pdf fallback for session=%s: %s", session_id, exc)
        return Response(
            content=content,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="proposal-{session_id[:8]}.md"'},
        )
```
And add the helper function above `proposal_pdf` (after the module-level `router = APIRouter(...)` line, before `class ProposalRequest`, alongside the other imports — add this import near the top with the other third-party imports):
```python
from fpdf import FPDF
```
```python
def _render_pdf(content: str) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 8, content)
    return bytes(pdf.output())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_proposal_pdf.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Run the full suite to confirm no regressions**

Run: `uv run pytest tests/ -v`
Expected: all PASS, same count as before plus the 2 new tests.

- [ ] **Step 6: Commit**

```bash
git add backend/routers/proposal.py tests/test_proposal_pdf.py
git commit -m "fix: replace weasyprint with fpdf2 for proposal PDF export"
```

---

## Task 3: Create the missing frontend env example

**Problem:** `.gitignore` (`!frontend/.env.local.example`) and `README.md`'s quickstart (`cp frontend/.env.local.example frontend/.env.local`) both reference this file, but it doesn't exist — onboarding breaks at that step.

**Files:**
- Create: `frontend/.env.local.example`

- [ ] **Step 1: Find the exact vars the frontend reads**

Run: `grep -rhoE "process\.env\.[A-Z_]+" frontend/app frontend/lib frontend/middleware.ts frontend/components 2>/dev/null | sort -u`
Expected: a list including at least `GITHUB_ID`, `GITHUB_SECRET`, `NEXTAUTH_SECRET`, `NEXTAUTH_URL`, and the backend URL variable (confirm its exact name in this output — the README quickstart calls it `BACKEND_URL`; use whatever this grep actually shows).

- [ ] **Step 2: Create the file**

Create `frontend/.env.local.example` using the exact variable names from Step 1's output, e.g.:
```bash
GITHUB_ID=
GITHUB_SECRET=
NEXTAUTH_SECRET=
NEXTAUTH_URL=http://localhost:3000
BACKEND_URL=http://localhost:8000
```
(Adjust names/values to match what Step 1 found — do not guess a name Step 1 didn't confirm.)

- [ ] **Step 3: Verify it's not accidentally ignored**

Run: `git check-ignore -v frontend/.env.local.example`
Expected: no output (not ignored) — confirms the `.gitignore` negation (`!frontend/.env.local.example`) is doing its job.

- [ ] **Step 4: Commit**

```bash
git add frontend/.env.local.example
git commit -m "docs: add missing frontend/.env.local.example referenced by README and .gitignore"
```

---

## Task 4: Move CI to uv

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Replace the backend-tests job's install/run steps**

In `.github/workflows/ci.yml`, replace the `backend-tests` job's steps (currently `actions/checkout@v4`, `actions/setup-python@v5`, `pip install -r backend/requirements.txt`, `pytest tests/ -v`) with:
```yaml
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      - name: Install deps
        run: uv sync
      - name: Run tests (offline, mocked)
        env:
          OPENAI_API_KEY: sk-test-dummy
        run: uv run pytest tests/ -v
```
Leave the `frontend-build` job unchanged (it's npm-based, not Python).

- [ ] **Step 2: Verify the exact commands pass locally**

Run: `OPENAI_API_KEY=sk-test-dummy uv sync && OPENAI_API_KEY=sk-test-dummy uv run pytest tests/ -v`
Expected: all PASS — same commands CI will run.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: install and run backend tests via uv instead of pip/requirements.txt"
```

---

## Task 5: Move Render deploy to uv

**Files:**
- Modify: `render.yaml`

- [ ] **Step 1: Update buildCommand and startCommand**

In `render.yaml`, change:
```yaml
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
```
to:
```yaml
    buildCommand: pip install uv && uv sync --frozen
    startCommand: uv run uvicorn main:app --host 0.0.0.0 --port $PORT
```
`rootDir: backend` stays as-is — verified in this session that `uv sync`/`uv run` invoked from `backend/` correctly discover the root `pyproject.toml`/`uv.lock` via upward directory search, with no `--project` flag needed.

- [ ] **Step 2: Reproduce Render's exact build+start locally**

Run:
```bash
cd backend && pip install uv && uv sync --frozen && uv run uvicorn main:app --host 0.0.0.0 --port 8000 &
sleep 2
curl -sS http://localhost:8000/health
kill %1
```
Expected: the `curl` returns a healthy response (the same `/health` path `render.yaml`'s `healthCheckPath` checks); no import errors in the startup log.

- [ ] **Step 3: Commit**

```bash
git add render.yaml
git commit -m "chore: deploy backend via uv on Render instead of pip/requirements.txt"
```

---

## Task 6: Update README to match the uv-based workflow

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update the backend quickstart (lines ~118-124)**

Replace:
```markdown
### 2. Backend env + run
```bash
cp backend/.env.example backend/.env   # fill NEON_DATABASE_URL (local), APP_ENCRYPTION_KEY, NEXTAUTH_SECRET, OPENAI_API_KEY, AWS_* (LocalStack)
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload     # http://localhost:8000
```
```
with:
```markdown
### 2. Backend env + run
```bash
cp backend/.env.example backend/.env   # fill NEON_DATABASE_URL (local), APP_ENCRYPTION_KEY, NEXTAUTH_SECRET, OPENAI_API_KEY, AWS_* (LocalStack)
uv sync
uv run uvicorn backend.main:app --reload     # http://localhost:8000
```
```

- [ ] **Step 2: Update "Running tests" (lines ~223-227)**

Replace:
```markdown
## Running tests

```bash
pytest tests/ -v
```
```
with:
```markdown
## Running tests

```bash
uv run pytest tests/ -v
```
```

- [ ] **Step 3: Verify no stale references remain**

Run: `grep -n "pip install -r\|requirements.txt\|python -m venv" README.md`
Expected: no matches.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: update README quickstart and test instructions to uv"
```

---

## Self-Review Notes

- **Spec coverage:** uv consolidation → Task 1 (+ 4, 5, 6 for the tools that referenced the old manifest). weasyprint→fpdf2 → Task 2. Missing frontend env example → Task 3. All items from the spec's File Structure section are covered; nothing deferred silently.
- **Placeholder scan:** none — every step has literal commands/code, not descriptions of what to do.
- **Type consistency:** `_render_pdf(content: str) -> bytes` is defined once in Task 2 and not referenced by any other task.
- **Ordering:** Task 1 runs before Task 2 so `fpdf2` is installed before Task 2's test needs it. Task 1 deletes `backend/requirements.txt` before Tasks 4-5 update the tools that reference it — acceptable since these commits land together on one branch before anything is pushed; if tasks are executed with pushes in between, push after Task 5 at the earliest.
- **Deferred (not in this plan):** OpenAI API key replacement (needs a real key from the user — the current one returns `401 invalid_api_key`), agent file renaming, wiring up rate limiting, any DB/architecture change.
