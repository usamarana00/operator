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
│              │ChromaDB│ │      │Tavily      │            │  │
│              │SQLite  │ │      │            │            │  │
│              │MCP FS  │ │      │MCP GitHub  │            │  │
│              └────┬───┘ │      └─────┬──────┘            │  │
│                   │     │            │                   │  │
│              ┌────▼─────▼────────────▼───┐               │  │
│              │      Response Agent       │               │  │
│              │  Synthesize → Markdown    │               │  │
│              │  Save to ConvBufferMemory │               │  │
│              └───────────────────────────┘               │  │
└─────────────────────────────────────────────────────────────┘
```

### Agent pipeline

| Agent | Trigger | Data sources |
|-------|---------|-------------|
| **Planner** | Every request | LLM (GPT-4o) — classifies intent + extracts entities |
| **PM Agent** | `deadline` or `both` intent | ChromaDB (RAG), SQLite (milestones), MCP filesystem |
| **GitHub Agent** | `repo` or `both` intent | GitHub REST API, Tavily web search |
| **Response Agent** | Always | Synthesizes PM + GitHub outputs into final Markdown |

### SSE streaming

Every agent step emits a Server-Sent Event to the browser as it happens — intent classification, RAG retrieval counts, SQLite query results, GitHub API calls, MCP writes, and the final synthesized response all appear in real time.

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS v4 |
| Backend | FastAPI, Python 3.11, Uvicorn |
| Agent framework | LangChain, LangGraph |
| LLM | GPT-4o (OpenAI) |
| Vector store | ChromaDB + OpenAI text-embedding-3-small |
| Structured data | SQLite |
| Memory | LangChain ConversationBufferMemory |
| External APIs | GitHub REST API, Tavily Search |
| MCP tools | Filesystem MCP, GitHub MCP |
| Streaming | Server-Sent Events (SSE) |

---

## Quickstart

### Prerequisites
- Python 3.11
- Node.js 18+
- An OpenAI API key
- A GitHub personal access token (classic, with `repo` scope)

### 1. Clone and configure

```bash
git clone <repo-url>
cd freelance-agent

cp backend/.env.example backend/.env
```

Open `backend/.env` and fill in your keys:

```env
OPENAI_API_KEY=sk-...
GITHUB_TOKEN=ghp_...
TAVILY_API_KEY=tvly-...   # optional
```

### 2. Install backend dependencies

```bash
cd freelance-agent

# Create a Python 3.11 virtual environment
python3.11 -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 3. Start the backend

```bash
uvicorn backend.main:app --reload
```

Backend runs at `http://localhost:8000`.

### 4. Install and start the frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`.

### 5. Complete the setup wizard

Open `http://localhost:3000` in your browser. On first run, a setup wizard appears:

1. **Keys** — confirms your API keys are detected (nothing is sent to the browser)
2. **Repos** — lists your GitHub repositories; pick the ones you want to track
3. **Configure** — name each project, set the client name, add milestones
4. **Build** — fetches READMEs and recent commits, seeds SQLite, builds ChromaDB index

Once complete, the wizard redirects to the chat interface automatically.

---

## Project structure

```
freelance-agent/
├── backend/
│   ├── main.py                  # FastAPI app, SSE chat endpoint
│   ├── setup.py                 # (optional) CLI alternative to the web wizard
│   ├── .env.example             # Environment variable template
│   ├── agents/
│   │   ├── planner.py           # Intent classification + entity extraction
│   │   ├── project_manager.py   # RAG + SQLite deadline agent
│   │   ├── github_agent.py      # GitHub API + Tavily agent
│   │   └── response_agent.py    # Final synthesis agent
│   ├── db/
│   │   └── sqlite.py            # Project, milestone, and notes schema
│   ├── graph/
│   │   ├── state.py             # LangGraph AgentState TypedDict
│   │   └── workflow.py          # LangGraph StateGraph workflow
│   ├── mcp/
│   │   └── servers.py           # Filesystem MCP + GitHub MCP tool wrappers
│   ├── memory/
│   │   ├── buffer_memory.py     # Per-session ConversationBufferMemory
│   │   └── vector_memory.py     # Long-term Chroma vector memory
│   ├── rag/
│   │   ├── loader.py            # DirectoryLoader for project docs
│   │   ├── chunker.py           # RecursiveCharacterTextSplitter
│   │   └── retriever.py         # ChromaDB build + load
│   ├── routers/
│   │   └── setup.py             # Setup wizard API endpoints
│   └── data/
│       ├── projects/            # Auto-generated project docs (gitignored)
│       ├── clients/             # Client docs (gitignored)
│       ├── notes/               # MCP filesystem write target (gitignored)
│       ├── chroma_db/           # Vector index (gitignored)
│       └── projects.db          # SQLite database (gitignored)
├── frontend/
│   ├── app/
│   │   ├── page.tsx             # Root — setup wizard or main chat
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
│   │   └── ProjectCard.tsx      # Individual project card
│   └── lib/
│       └── useSSE.ts            # SSE streaming hook with turn history
└── tests/
    ├── test_db.py
    ├── test_rag.py
    ├── test_agents.py
    └── test_workflow.py
```

---

## Re-running setup

To reconfigure your projects (add new repos, change milestones):

```bash
# Delete the database — wizard will appear on next browser load
rm backend/data/projects.db
rm -rf backend/data/chroma_db
rm backend/data/projects/*.md
```

Then refresh `http://localhost:3000`.

---

## Running tests

```bash
pytest tests/ -v
```

---

## Capstone requirements coverage

| Requirement | Implementation |
|-------------|---------------|
| LangChain foundations | LCEL chains (`prompt \| llm`), ChatOpenAI, ChatPromptTemplate |
| Conversation memory | `ConversationBufferMemory` per session in `buffer_memory.py` |
| RAG pipeline | ChromaDB + OpenAI embeddings, DirectoryLoader, chunking |
| 3+ agents | Planner, PM Agent, GitHub Agent, Response Agent |
| LangGraph workflow | `StateGraph` with conditional routing in `graph/workflow.py` |
| 2+ MCP servers | Filesystem MCP + GitHub MCP in `mcp/servers.py` |
| 2+ external APIs | GitHub REST API + Tavily Search API |
| 2+ data sources | SQLite (structured) + ChromaDB (vector) + GitHub API (live) |
