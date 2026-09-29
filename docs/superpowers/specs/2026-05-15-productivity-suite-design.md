# Freelance Productivity Suite — Design Spec

**Date:** 2026-05-15  
**Status:** Approved  
**Author:** Claude (brainstorming session)

---

## Context

Freelance developers lose significant time to context switching between projects. The existing app has strong foundations (RAG, GitHub integration, milestones, multi-tenant auth) but lacks proactive output — it only responds when queried. This spec adds two features that push value to the user:

1. **Daily Briefing** — on-demand morning digest of project status
2. **Proposal Generator** — AI-drafted client proposals based on past project data, with PDF export

Both share a common `ProjectContextBuilder` utility to avoid duplicating data-fetching logic.

---

## Architecture

### New Components

```
backend/
  agents/
    producer_agent.py       # New: briefing + proposal modes
  utils/
    project_context.py      # New: shared ProjectContextBuilder
  routers/
    briefing.py             # New: POST /briefing
    proposal.py             # New: POST /proposal, GET /proposal/{session_id}/pdf

frontend/
  components/
    BriefingButton.tsx      # New: sidebar button → triggers briefing SSE
    ProposalWizard.tsx      # New: 3-field modal → triggers proposal SSE
    ProposalDownload.tsx    # New: "Download PDF" button shown after proposal
```

### Shared Utility: `ProjectContextBuilder`

Located at `backend/utils/project_context.py`. Fetches for a given `user_id`:

- All active projects + their milestones (from PostgreSQL via `backend/db/postgres.py`)
- Recent GitHub commits, open PRs, open issues (via `backend/agents/github_agent.py` logic)
- Top RAG chunks from `doc_chunks` table (via `backend/rag/retriever.py`)

Returns a structured `ProjectContext` dataclass. Both `ProducerAgent` modes call this once.

### ProducerAgent

Located at `backend/agents/producer_agent.py`. Two async methods:

- `async def briefing(user_id: str) -> AsyncIterator[str]` — yields SSE chunks
- `async def proposal(user_id: str, description: str, client: str, budget: str | None) -> AsyncIterator[str]` — yields SSE chunks

Both use GPT-4o with structured system prompts. Both stream output via the existing SSE pattern in `backend/main.py`.

---

## Feature 1: Daily Briefing

### Trigger

User clicks **"Morning Briefing"** button in the sidebar, OR types `/briefing` in the chat input.

### Backend

- Route: `POST /briefing` (new router at `backend/routers/briefing.py`)
- Auth: existing `get_current_user` dependency
- Response: `text/event-stream` (same SSE format as `/chat`)
- No new DB tables required

### Output Format

```markdown
## Daily Briefing — {date}

### Overdue
- [{Project}] Milestone "{title}" — was due {date}
- [{Project}] PR #{n} "{title}" — open {n} days, no review

### Due This Week
- [{Project}] Milestone "{title}" — due {date}

### Recent Activity (last 24h)
- [{Project}] {n} commits on `{branch}` — last: "{message}"
- [{Project}] Issue #{n} opened — "{title}"

### Suggested Focus
{One-sentence AI recommendation of where to start, based on deadlines and blockers}
```

### Edge Cases

| Situation | Behavior |
|-----------|----------|
| No projects set up | Returns message directing user to Setup Wizard |
| GitHub API rate limited | Skips GitHub section, notes gracefully in output |
| OpenAI key missing | Returns 401 with message "Configure your OpenAI key in Settings" |
| No milestones | Skips overdue/upcoming sections, shows only GitHub activity |

---

## Feature 2: Proposal Generator

### Trigger

User clicks **"New Proposal"** button in sidebar, OR types `/proposal` in chat input → 3-field modal opens:

1. **Client name** (text, required)
2. **Project description** (textarea, required)
3. **Budget range** (text, optional — e.g. "$3,000–$5,000")

On submit → modal closes → proposal streams into chat.

### Backend

- Route: `POST /proposal` (new router at `backend/routers/proposal.py`)
- Auth: existing `get_current_user` dependency
- Body: `{ client: str, description: str, budget: str | None }`
- Response: `text/event-stream`

### Proposal Prompt Strategy

1. `ProjectContextBuilder` fetches completed/archived projects as reference material
2. RAG retriever finds top-5 chunks semantically similar to the proposal description
3. GPT-4o system prompt instructs: use past projects as evidence of capability, infer tech stack from description, generate timeline phases

### Output Format

```markdown
## Proposal: {description} for {client}

### Overview
{What will be built, 2-3 sentences}

### Approach & Tech Stack
{Inferred from description + past project patterns}

### Timeline
| Phase | Deliverable | Duration |
|-------|-------------|----------|
| 1     | ...         | ...      |

### Pricing
{Budget breakdown if provided; else placeholder ranges}

### Why Choose Me
{Track record pulled from past project data — specific project names, outcomes}
```

### PDF Export

- After proposal streams to chat, a **"Download as PDF"** button renders below the message
- Route: `GET /proposal/{session_id}/pdf`
- Implementation: retrieves last assistant message for session from `chat_messages` table → renders via `WeasyPrint` → returns `application/pdf`
- Fallback: if WeasyPrint fails, offers Markdown download as `.md` file
- Dependency to add: `weasyprint` in `requirements.txt` / `pyproject.toml`

### Edge Cases

| Situation | Behavior |
|-----------|----------|
| No past projects | Agent notes lack of reference data, generates proposal from description alone |
| OpenAI key missing | Returns 401 with message "Configure your OpenAI key in Settings" |
| PDF generation failure | Falls back to `.md` file download |

---

## Frontend Changes

### Sidebar (`frontend/components/Sidebar.tsx`)

Add two buttons below the project list:
- **"Morning Briefing"** → calls `POST /api/backend/briefing` → streams result into a new chat turn
- **"New Proposal"** → opens `ProposalWizard` modal

### Chat Input (`frontend/components/ChatWindow.tsx`)

Detect `/briefing` and `/proposal` slash commands:
- `/briefing` → triggers briefing flow
- `/proposal` → opens `ProposalWizard` modal

### ProposalWizard (`frontend/components/ProposalWizard.tsx`)

Modal with 3 fields. On submit: calls `POST /api/backend/proposal` → streams response into chat via existing `useSSE` hook.

### ProposalDownload (`frontend/components/ProposalDownload.tsx`)

Appears below any chat message identified as a proposal (detect by session metadata or message tag). Button: "Download PDF" → fetches `/api/backend/proposal/{session_id}/pdf` → triggers browser download.

---

## Data Flow

```
User clicks "Morning Briefing"
  → Frontend: POST /api/backend/briefing (Next.js proxy)
  → Backend: POST /briefing
  → get_current_user (JWT auth)
  → ProducerAgent.briefing(user_id)
  → ProjectContextBuilder.fetch(user_id)
     → postgres.get_projects_with_milestones(user_id)
     → github_agent.get_repo_summary(projects)
     → rag.retriever.search(user_id, query="project status")
  → GPT-4o synthesis
  → SSE stream → ChatWindow → AgentMessage render

User submits proposal form
  → Frontend: POST /api/backend/proposal
  → Backend: POST /proposal
  → ProducerAgent.proposal(user_id, description, client, budget)
  → ProjectContextBuilder.fetch(user_id) [past projects focus]
  → RAG similarity search on description
  → GPT-4o proposal generation
  → SSE stream → ChatWindow
  → ProposalDownload button appears
  → User clicks "Download PDF"
  → GET /api/backend/proposal/{session_id}/pdf
  → WeasyPrint renders Markdown → PDF bytes → browser download
```

---

## Dependencies to Add

| Package | Use | Where |
|---------|-----|-------|
| `weasyprint` | Markdown→PDF render | `pyproject.toml`, `requirements.txt` |

---

## Testing

### Unit Tests

- `test_project_context_builder.py` — mock DB + GitHub, assert correct aggregation
- `test_producer_agent_briefing.py` — mock context builder, assert SSE output format
- `test_producer_agent_proposal.py` — mock context + RAG, assert proposal structure

### Integration Tests

- `POST /briefing` with valid auth → assert SSE response, non-empty output
- `POST /proposal` with client/description → assert SSE response contains timeline table
- `GET /proposal/{session_id}/pdf` → assert `Content-Type: application/pdf`

### Manual Verification

1. Log in with GitHub OAuth → complete setup wizard for 1+ project
2. Click "Morning Briefing" → verify structured digest appears in chat
3. Click "New Proposal" → fill form → verify proposal streams to chat
4. Click "Download PDF" → verify PDF opens with correct content
5. Test with no projects configured → verify friendly error messages
6. Test with GitHub API unavailable → verify briefing still produces output

---

## Out of Scope (This Phase)

- Email/push notification delivery for briefing (can be Phase 2 with a scheduler)
- Team collaboration / shared proposals
- Billing/invoice generation
- Toggl/Clockify time tracking integration
