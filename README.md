# Freelance Project Assistant

A multi-agent AI system that helps freelance developers manage projects, track deadlines, and monitor GitHub repositories — all through a natural language chat interface.

Built as a capstone project for an AI engineering bootcamp, demonstrating LangChain, LangGraph, RAG, MCP, and SSE streaming in a production-style full-stack application.

---

## What it does

Ask questions like:
- *"What deadlines do I have this week?"*
- *"Show me open pull requests for Project Alpha"*
- *"What's the status of my paki-portal repo?"*
- *"What am I working on right now?"*

The system routes your question to the right agents, queries the right data sources, and streams the entire reasoning process to your screen in real time.

---

## Features
- **Chat** — natural-language Q&A routed across planner / PM / GitHub / response agents, streamed step-by-step over SSE.
- **Morning briefing** — one-click summary of upcoming deadlines + recent repo activity (`POST /briefing`).
- **Proposal generator** — wizard that drafts a client proposal and exports it as PDF (`POST /proposal`, `GET /proposal/{session_id}/pdf`).
- **File uploads** — per-project document uploads to S3 via presigned URLs.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser (Next.js)                     │
│  Setup Wizard ──► Chat UI (SSE streaming)  ◄── Sidebar      │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP / SSE
┌───────────────────────────▼─────────────────────────────────┐
│                    FastAPI Backend                           │
│                                                             │
│   ┌──────────┐    ┌──────────────────────────────────────┐  │
│   │  Setup   │    │         Chat Pipeline                │  │
│   │  Router  │    │                                      │  │
│   │          │    │  ┌─────────┐                         │  │
│   │ /keys    │    │  │ Planner │ classify_intent()       │  │
│   │ /status  │    │  └────┬────┘ → deadline/repo/both/   │  │
│   │ /repos   │    │       │        general               │  │
│   │ /complete│    │  ┌────▼──────────────┐               │  │
│   └──────────┘    │  │  Conditional      │               │  │
│                   │  │  Router           │               │  │
│                   │  └──┬────────────┬───┘               │  │
│                   │     │            │                   │  │
│              ┌────▼───┐ │      ┌─────▼──────┐            │  │
│              │PM Agent│ │      │GitHub Agent│            │  │
│              │        │ │      │            │            │  │
│              │RAG     │ │      │GitHub API  │            │  │
│              │pgvector│ │      │Tavily      │            │  │
│              │Postgres│ │      │            │            │  │
│              │MCP S3FS│ │      │MCP GitHub  │            │  │
│              └────┬───┘ │      └─────┬──────┘            │  │
│                   │     │            │                   │  │
│              ┌────▼─────▼────────────▼───┐               │  │
│              │      Response Agent       │               │  │
│              │  Synthesize → Markdown    │               │  │
│              │  Save to Postgres history │               │  │
│              └───────────────────────────┘               │  │
└─────────────────────────────────────────────────────────────┘
```

### Agent pipeline

| Agent | Trigger | Data sources |
|-------|---------|-------------|
| **Planner** | Every request | LLM (GPT-4o) — classifies intent + extracts entities |
| **PM Agent** | `deadline` or `both` intent | Postgres pgvector (RAG), Postgres (milestones), S3 filesystem MCP |
| **GitHub Agent** | `repo` or `both` intent | GitHub REST API, Tavily web search |
| **Response Agent** | Always | Synthesizes PM + GitHub outputs into final Markdown |

### SSE streaming

Every agent step emits a Server-Sent Event to the browser as it happens — intent classification, RAG retrieval counts, Postgres query results, GitHub API calls, MCP writes, and the final synthesized response all appear in real time.

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS v4 |
| Backend | FastAPI, Python 3.11, Uvicorn |
| Agent framework | LangChain, LangGraph |
| LLM | GPT-4o (OpenAI) |
| Vector store | Neon Postgres + pgvector + OpenAI text-embedding-3-small |
| Structured data | Neon Postgres (asyncpg) |
| Memory | Postgres-backed chat history per session |
| Auth | NextAuth (GitHub OAuth) → JWT verified by FastAPI middleware |
| File storage | AWS S3 (presigned uploads) + S3-backed notes MCP |
| External APIs | GitHub REST API, Tavily Search |
| MCP tools | S3-backed filesystem MCP, GitHub MCP |
| Streaming | Server-Sent Events (SSE) |

---

## Quickstart (local development)

The backend is multi-tenant and auth-gated, so local dev runs the full stack:
Postgres + pgvector (Docker), S3 (LocalStack), FastAPI, and Next.js with GitHub OAuth.

### Prerequisites
- [uv](https://docs.astral.sh/uv/) (installs Python for you), Node.js 18+, Docker
- A GitHub OAuth app (Settings → Developers → New OAuth App), callback `http://localhost:3000/api/auth/callback/github`
- An OpenAI API key

### 1. Start Postgres + LocalStack
```bash
docker compose up -d
```

### 2. Backend env + run
```bash
cp backend/.env.example backend/.env   # fill NEON_DATABASE_URL (local), APP_ENCRYPTION_KEY, NEXTAUTH_SECRET, OPENAI_API_KEY, AWS_* (LocalStack)
uv sync
uv run uvicorn backend.main:app --reload     # http://localhost:8000
```
Generate the two secrets:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"                 # NEXTAUTH_SECRET
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # APP_ENCRYPTION_KEY
```

### 3. Frontend env + run
```bash
cp frontend/.env.local.example frontend/.env.local   # GITHUB_ID, GITHUB_SECRET, NEXTAUTH_SECRET (same as backend), NEXTAUTH_URL, BACKEND_URL
cd frontend && npm install && npm run dev             # http://localhost:3000
```

### 4. Sign in + complete the wizard
Open http://localhost:3000, sign in with GitHub, then the 4-step wizard: confirm OpenAI key → pick repos → name projects + milestones → build (fetches READMEs/commits, seeds Postgres, indexes pgvector).

---

## Project structure

```
freelance-agent/
├── backend/
│   ├── main.py                  # FastAPI app, SSE chat endpoint
│   ├── auth.py                  # NextAuth JWT verification + GitHub OAuth + Fernet encryption
│   ├── .env.example             # Environment variable template
│   ├── agents/
│   │   ├── planner.py           # Intent classification + entity extraction
│   │   ├── project_manager.py   # RAG + Postgres deadline agent
│   │   ├── github_agent.py      # GitHub API + Tavily agent (via MCP tool layer)
│   │   ├── response_agent.py    # Final synthesis agent
│   │   └── producer_agent.py    # Morning briefing + proposal generation
│   ├── db/
│   │   └── postgres.py          # asyncpg pool + schema (users, projects, milestones,
│   │                             #   notes, files, doc_chunks/pgvector, chat_messages)
│   ├── graph/
│   │   ├── state.py             # LangGraph AgentState TypedDict
│   │   └── workflow.py          # LangGraph StateGraph workflow
│   ├── mcp/
│   │   ├── s3_fs.py             # S3-backed filesystem MCP + presigned upload/download
│   │   └── servers.py           # Re-exports S3 MCP tools + GitHub MCP tool wrappers
│   ├── memory/
│   │   ├── buffer_memory.py     # Per-session chat history backed by Postgres
│   │   └── vector_memory.py     # Long-term memory embedded into pgvector
│   ├── rag/
│   │   ├── loader.py            # Document loading for project docs
│   │   ├── chunker.py           # RecursiveCharacterTextSplitter
│   │   └── retriever.py         # pgvector index + similarity search
│   └── routers/
│       ├── setup.py             # Setup wizard API endpoints
│       ├── briefing.py          # POST /briefing
│       ├── proposal.py          # POST /proposal, GET /proposal/{session_id}/pdf
│       └── files.py             # Presigned S3 upload/download + file metadata
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # Root — setup wizard or main chat
│   │   ├── api/auth/[...nextauth]/route.ts  # NextAuth GitHub OAuth route
│   │   └── globals.css          # Tailwind v4 + typography plugin
│   ├── components/
│   │   ├── setup/               # 4-step onboarding wizard
│   │   │   ├── SetupWizard.tsx
│   │   │   ├── StepValidate.tsx
│   │   │   ├── StepRepos.tsx
│   │   │   ├── StepConfigure.tsx
│   │   │   └── StepBuilding.tsx
│   │   ├── ChatWindow.tsx       # Multi-turn chat UI with SSE
│   │   ├── AgentMessage.tsx     # Per-agent styled event renderer
│   │   ├── Sidebar.tsx          # Active projects + milestone urgency
│   │   ├── ProjectCard.tsx      # Individual project card
│   │   ├── BriefingButton.tsx   # Triggers the morning briefing
│   │   ├── ProposalWizard.tsx   # Proposal generator form
│   │   ├── ProposalDownload.tsx # PDF download for a generated proposal
│   │   ├── FileUpload.tsx       # Presigned S3 file upload
│   │   └── SignIn.tsx           # GitHub OAuth sign-in
│   └── lib/
│       └── useSSE.ts            # SSE streaming hook with turn history
└── tests/
    ├── test_db.py
    ├── test_rag.py
    ├── test_agents.py
    ├── test_workflow.py
    ├── test_routing.py
    ├── test_repo_resolution.py
    ├── test_github_mcp_usage.py
    └── test_productivity_routes.py
```

---

## Re-running setup

Setup state lives in Postgres per user, not in local files. To reconfigure, either:
- delete your projects/milestones rows for your user in the database, or
- (local dev) drop and recreate the schema: `docker compose down -v && docker compose up -d`, then reload http://localhost:3000.

> A "Manage projects / re-run setup" UI button is tracked as a future enhancement.

---

## Running tests

```bash
uv run pytest tests/ -v
```

---

## Capstone requirements coverage

| Requirement | Implementation |
|-------------|---------------|
| LangChain foundations | LCEL chains (`prompt \| llm`), ChatOpenAI, ChatPromptTemplate |
| Conversation memory | Postgres-backed chat history per session in `buffer_memory.py` |
| RAG pipeline | Postgres pgvector (`doc_chunks` table) + OpenAI embeddings, chunking |
| 3+ agents | Planner, PM Agent, GitHub Agent, Response Agent, Producer Agent |
| LangGraph workflow | `StateGraph` with conditional routing in `graph/workflow.py`, executed by the chat pipeline |
| 2+ MCP servers | S3-backed filesystem MCP (`mcp/s3_fs.py`) + GitHub MCP tool layer (`mcp/servers.py`, used by the GitHub agent) |
| 2+ external APIs | GitHub REST API + Tavily Search API |
| 2+ data sources | Postgres (structured) + pgvector (RAG) + GitHub REST API (live) |

---

## Deployment

The app runs as four services — all on free tiers.

| Service | What | Where |
|---------|------|-------|
| **Vercel** | Next.js frontend | `vercel.com` — connect repo, root = `/` |
| **Render** | FastAPI backend | `render.com` — auto-detected via `render.yaml` |
| **Neon** | Postgres + pgvector | `neon.tech` — free tier, permanent |
| **AWS S3** | File storage | your AWS account, free tier |

### One-time setup checklist

**1. GitHub OAuth app** — `github.com/settings/developers → New OAuth App`
- Homepage URL: `https://<your-app>.vercel.app`
- Callback URL: `https://<your-app>.vercel.app/api/auth/callback/github`
- Copy **Client ID** and **Client Secret**

**2. Neon database**
```sql
-- run once in the Neon SQL editor
CREATE EXTENSION IF NOT EXISTS vector;
```
Copy the **pooler connection string** (postgres://...).

**3. AWS S3 bucket**
- Create bucket `freelance-agent-prod`, block all public access
- Create IAM user, attach inline policy: `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject` on `arn:aws:s3:::freelance-agent-prod/*`
- Add CORS rule: allow `PUT` / `GET` from your Vercel domain
- Copy **Access Key ID** and **Secret Access Key**

**4. Generate secrets**
```bash
# NEXTAUTH_SECRET and APP_ENCRYPTION_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"
# APP_ENCRYPTION_KEY must be a valid Fernet key:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

**5. Render — set env vars** (Settings → Environment)
```
NEON_DATABASE_URL      = <pooler URL from Neon>
NEXTAUTH_SECRET        = <generated above>
APP_ENCRYPTION_KEY     = <Fernet key from above>
FRONTEND_ORIGIN        = https://<your-app>.vercel.app
AWS_ACCESS_KEY_ID      = <from IAM>
AWS_SECRET_ACCESS_KEY  = <from IAM>
AWS_REGION             = us-east-1
AWS_S3_BUCKET          = freelance-agent-prod
TAVILY_API_KEY         = <optional>
OPENAI_API_KEY         = <optional fallback>
```

**6. Vercel — set env vars** (Settings → Environment Variables)
```
BACKEND_URL      = https://<your-render-service>.onrender.com
NEXTAUTH_SECRET  = <same value as Render>
NEXTAUTH_URL     = https://<your-app>.vercel.app
GITHUB_ID        = <OAuth app client ID>
GITHUB_SECRET    = <OAuth app client secret>
```

**7. Deploy**
```bash
# Push to main — Vercel and Render auto-deploy on push
git push origin main
```

### Local development

See the [Quickstart](#quickstart-local-development) section above — it covers Docker, env setup, and running both services locally.
