# Deploy Freelance Agent as Multi-Tenant Portfolio App

## Context

Current state: single-tenant FastAPI + Next.js capstone. `backend/data/projects.db`, `chroma_db/`, and `data/notes/` are global — any visitor would own all data. Secrets live in server-wide `.env`. No deploy story.

Goal: ship a publicly accessible URL where any new visitor signs in, gets a clean isolated workspace, and their projects/milestones/notes/files are stored safely and never leak across users. Suitable for a portfolio link.

Open GitHub issues integrated:
- #1 File handling/upload per project → solved by S3 layer
- #2 Deadline-update workflow → deferred to follow-up feature pack

## Chosen Stack (confirmed)

| Layer | Choice |
|---|---|
| Auth | NextAuth.js + GitHub OAuth provider (JWT strategy) |
| Database | Neon Postgres + `pgvector` extension (free tier, permanent) |
| File storage | AWS S3 (user's free tier), per-user key prefix |
| MCP servers | GitHub MCP (kept) + new S3-backed filesystem MCP |
| Frontend host | Vercel |
| Backend host | Render (FastAPI + uvicorn) |
| Secrets | OpenAI API key per-user, Fernet-encrypted in `users` row; GitHub token from OAuth; AWS creds server-side env |

## Architecture

```
Browser (Vercel)                Backend (Render)               External
Next.js
 ├── NextAuth (GitHub OAuth) ──► /auth/callback                GitHub OAuth
 ├── Setup wizard
 ├── Chat UI (SSE)        Authorization: Bearer <JWT>
 └── Sidebar  ──► /api/* ──► JWT middleware ──► inject user_id
                                  │
                       ┌──────────┼──────────┐
                       ▼          ▼          ▼
                   Planner   PM Agent   GitHub Agent
                                │           │
                                ▼           ▼
                          Neon Postgres  GitHub API (user's token)
                          (pgvector)
                                ▲
                          S3 MCP ─────────────► S3 bucket
                          GitHub MCP            users/<id>/...
```

Invariant: every DB query, every S3 op, every agent state carries `user_id`. New user = zero rows = fresh start by construction.

## Data Model (Neon Postgres)

```sql
users (
  id            uuid primary key,
  github_id     text unique not null,
  github_login  text not null,
  email         text,
  github_token_enc bytea,        -- encrypted with app KEY
  openai_key_enc   bytea,        -- encrypted with app KEY
  created_at    timestamptz default now()
);

projects (
  id          uuid primary key,
  user_id     uuid references users(id) on delete cascade,
  name        text not null,
  client      text,
  repo_owner  text,
  repo_name   text,
  created_at  timestamptz default now()
);

milestones (
  id         uuid primary key,
  project_id uuid references projects(id) on delete cascade,
  user_id    uuid not null,             -- denormalized for fast filter
  title      text not null,
  due_date   date not null,
  status     text default 'open',
  updated_at timestamptz default now()
);

notes (
  id         uuid primary key,
  project_id uuid references projects(id) on delete cascade,
  user_id    uuid not null,
  s3_key     text,                       -- nullable: text-only notes still OK
  body       text,
  created_at timestamptz default now()
);

files (                                  -- issue #1
  id         uuid primary key,
  project_id uuid references projects(id) on delete cascade,
  user_id    uuid not null,
  s3_key     text not null,
  filename   text not null,
  mime       text,
  size_bytes bigint,
  uploaded_at timestamptz default now()
);

doc_chunks (                             -- replaces ChromaDB
  id         uuid primary key,
  user_id    uuid not null,
  project_id uuid references projects(id) on delete cascade,
  source     text,                       -- 'readme'|'commit'|'note'|'file'
  content    text not null,
  embedding  vector(1536) not null
);
create index on doc_chunks using ivfflat (embedding vector_cosine_ops);
create index on doc_chunks (user_id, project_id);

chat_messages (                          -- replaces ConversationBufferMemory
  id         uuid primary key,
  user_id    uuid not null,
  session_id text not null,
  role       text not null,               -- 'user'|'assistant'
  content    text not null,
  created_at timestamptz default now()
);
```

Every non-`users` table has `user_id`. Every read filters by `user_id` from JWT. No exceptions.

## Auth Flow

1. User clicks **Sign in with GitHub** on landing page
2. NextAuth redirects to GitHub OAuth (scopes: `repo`, `read:user`, `user:email`)
3. Callback → NextAuth creates JWT containing `{ sub: user_id, github_login, github_token }`
4. JWT stored in httpOnly cookie + accessible to API route handlers
5. Frontend calls FastAPI with `Authorization: Bearer <JWT>`
6. FastAPI middleware `auth.py`:
   - Verify JWT signature using `NEXTAUTH_SECRET` (shared via env)
   - On first sight of `github_id`, upsert into `users` and store encrypted `github_token`
   - Inject `request.state.user_id`
7. Every route + agent reads `user_id` from `request.state`

OpenAI key: collected in setup wizard step 1, POSTed to `/setup/keys` (auth-required), encrypted server-side with Fernet (`APP_ENCRYPTION_KEY` env var), stored in `users.openai_key_enc`. Per-request decryption only.

## S3-Backed Filesystem MCP

Replaces `backend/data/notes/` local writes.

- Bucket: single `freelance-agent-prod`
- Key layout: `users/<user_id>/notes/<note_id>.md`, `users/<user_id>/files/<file_id>/<filename>`
- MCP tool surface (same as filesystem MCP): `write_note(path, content)`, `read_note(path)`, `list_notes()`
- Implementation: thin wrapper over boto3 in `backend/mcp/s3_fs.py`. Path scoped automatically with user_id prefix — agent cannot escape its own user's prefix
- File uploads (issue #1): frontend requests presigned PUT URL from `/files/presign`, uploads directly to S3, then POSTs metadata to `/files`. Backend never sees the bytes.

## Setup Wizard Changes

Per-user, gated by auth. Triggered when `users.openai_key_enc IS NULL` or no projects.

| Step | Before | After |
|---|---|---|
| Validate keys | Reads `.env` | User pastes OpenAI key → stored encrypted per-user. GitHub token already in `users` from OAuth. |
| Pick repos | List from GitHub via server token | List using user's OAuth token |
| Configure | Writes to global SQLite | Inserts to `projects` + `milestones` with `user_id` |
| Build index | Writes ChromaDB on disk | Inserts `doc_chunks` into Postgres with `user_id` |

## Backend Refactor Surface

Files that change:

| File | Change |
|---|---|
| `backend/main.py` | Add auth middleware, CORS for Vercel domain |
| `backend/auth.py` | NEW — JWT verify + user_id injection |
| `backend/db/sqlite.py` | DELETE — replaced by `backend/db/postgres.py` using `asyncpg` or SQLAlchemy |
| `backend/db/postgres.py` | NEW — connection pool, all queries scoped by user_id |
| `backend/rag/retriever.py` | Swap ChromaDB → pgvector similarity query |
| `backend/mcp/servers.py` | Replace local filesystem MCP with `s3_fs.py` wrapper |
| `backend/mcp/s3_fs.py` | NEW — boto3 wrapper, user_id-prefixed |
| `backend/memory/buffer_memory.py` | Persist messages to `chat_messages` table instead of in-memory |
| `backend/memory/vector_memory.py` | Use `doc_chunks` (pgvector) |
| `backend/agents/*.py` | Accept `user_id` in state; pass to all DB/MCP calls |
| `backend/routers/setup.py` | All endpoints require auth; write per-user rows |
| `backend/graph/state.py` | Add `user_id: str` to `AgentState` |
| `backend/routers/files.py` | NEW — presign + metadata endpoints (issue #1) |
| `backend/requirements.txt` | Add `asyncpg`, `pgvector`, `boto3`, `cryptography`, `PyJWT` |

## Frontend Changes

| File | Change |
|---|---|
| `frontend/app/api/auth/[...nextauth]/route.ts` | NEW — NextAuth GitHub provider config |
| `frontend/middleware.ts` | NEW — gate `/` behind session |
| `frontend/app/page.tsx` | Branch on session: signed out → landing/sign-in CTA; signed in + no setup → wizard; ready → chat |
| `frontend/components/setup/StepValidate.tsx` | Replace `.env` check with OpenAI key input form |
| `frontend/lib/useSSE.ts` | Attach `Authorization: Bearer <session.accessToken>` |
| `frontend/components/SignIn.tsx` | NEW — landing page with GitHub sign-in button |
| `frontend/components/FileUpload.tsx` | NEW — presign + direct S3 upload (issue #1) |

## Deployment Topology

**Vercel (frontend)**
- Connect GitHub repo, root = `frontend/`
- Env vars: `NEXTAUTH_SECRET`, `NEXTAUTH_URL`, `GITHUB_ID`, `GITHUB_SECRET`, `BACKEND_URL`
- Free tier

**Render (backend)**
- Web Service, root = `backend/`, runtime Python 3.11
- Build: `pip install -r requirements.txt`
- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Env vars: `NEON_DATABASE_URL`, `NEXTAUTH_SECRET`, `APP_ENCRYPTION_KEY`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_BUCKET`, `AWS_REGION`, `OPENAI_API_KEY_FALLBACK` (optional for demo), `TAVILY_API_KEY`
- Free tier sleeps after 15 min idle — acceptable for portfolio demo

**Neon**
- Single project, single branch, install `pgvector` extension via SQL
- Connection pooler URL used by backend
- Free tier

**S3**
- Single bucket `freelance-agent-prod` in user's AWS account
- CORS: allow `PUT` from Vercel domain
- IAM user with `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject` on bucket only
- Block public access — all reads via presigned GET URLs

## Migration Path

No data migration — current `projects.db` / `chroma_db/` are dev-only on the user's machine. Drop them. Production starts empty. Local dev gets a `docker-compose.yml` running Postgres+pgvector + LocalStack for S3 so devs don't need cloud creds.

## Security Checklist

- JWT signature verified on every backend call
- All DB queries parameterized; `user_id` from JWT, never from request body
- Row-level isolation enforced in every query (`WHERE user_id = $1`)
- OpenAI key encrypted at rest (Fernet) with `APP_ENCRYPTION_KEY` (rotatable)
- GitHub token encrypted at rest, decrypted only when calling GitHub API
- S3 bucket: block public access, presigned URLs only, short TTL (15 min)
- CORS: allow only the Vercel frontend origin
- Rate limit on `/setup/*` and `/chat` (e.g., slowapi)
- No secrets in logs; structured logger redacts known fields
- `NEXTAUTH_SECRET` and `APP_ENCRYPTION_KEY` generated via `secrets.token_urlsafe(32)`

## Testing

| Layer | Test |
|---|---|
| Unit | `auth.py` JWT verify, Fernet round-trip, S3 key prefix scoping |
| Integration | Per-user isolation: create two users, ensure user A cannot read user B's projects/notes/files/embeddings |
| RAG | pgvector similarity returns correct chunks for `user_id` filter |
| E2E | Playwright: sign in → setup wizard → ask question → SSE renders agent steps → upload file |
| Security | Hit every endpoint without JWT → 401. With user A JWT requesting user B's resource → 403/404. |

Target 80% coverage on backend, smoke E2E on critical flows.

## Out of Scope (Future Iterations)

- Issue #2 deadline-update workflow (next feature pack)
- Email notifications, password auth, team accounts
- Custom domain, paid hosting tier
- Multi-region, CDN for S3, observability stack

## Verification Plan

1. Local: `docker-compose up` → Postgres + LocalStack + backend + frontend → run E2E
2. Staging: deploy to Vercel preview + Render preview, smoke test
3. Production:
   - Sign in with two different GitHub accounts in two browsers
   - Both run setup wizard independently → confirm zero cross-contamination
   - Upload file as user A → query as user B → must not appear
   - Inspect Neon: every row has correct `user_id`
   - Inspect S3: every object under correct `users/<id>/` prefix
4. Run `pytest tests/ -v` (coverage ≥80%)
5. Manual security pass: tamper JWT, missing JWT, wrong user_id in body

## Critical Files Reference (existing, to be modified)

- [backend/main.py](../../backend/main.py) — wire middleware, CORS
- [backend/agents/planner.py](../../backend/agents/planner.py), [project_manager.py](../../backend/agents/project_manager.py), [github_agent.py](../../backend/agents/github_agent.py), [response_agent.py](../../backend/agents/response_agent.py) — thread user_id through state
- [backend/graph/state.py](../../backend/graph/state.py), [workflow.py](../../backend/graph/workflow.py) — add user_id to AgentState
- [backend/db/sqlite.py](../../backend/db/sqlite.py) — delete and replace with `postgres.py`
- [backend/rag/retriever.py](../../backend/rag/retriever.py) — Chroma → pgvector
- [backend/mcp/servers.py](../../backend/mcp/servers.py) — local fs → S3 fs
- [backend/memory/buffer_memory.py](../../backend/memory/buffer_memory.py), [vector_memory.py](../../backend/memory/vector_memory.py) — persist to Postgres
- [backend/routers/setup.py](../../backend/routers/setup.py) — auth + per-user writes
- [frontend/app/page.tsx](../../frontend/app/page.tsx) — session gating
- [frontend/components/setup/StepValidate.tsx](../../frontend/components/setup/StepValidate.tsx) — OpenAI key entry form
- [frontend/lib/useSSE.ts](../../frontend/lib/useSSE.ts) — attach JWT

## Sequenced Implementation Phases

1. **Phase A — Schema + auth foundation:** Neon setup, `users` + `projects` + `milestones` tables, NextAuth GitHub, JWT middleware, encrypted key storage. Local dev with docker-compose.
2. **Phase B — Data layer migration:** Replace SQLite with Postgres, ChromaDB with pgvector, thread `user_id` through all agents + state.
3. **Phase C — S3 + file uploads:** Bucket setup, S3 MCP wrapper, presigned upload endpoints, FileUpload component (closes issue #1).
4. **Phase D — Setup wizard rework:** Per-user gating, OpenAI key collection, per-user repo selection.
5. **Phase E — Deploy:** Vercel + Render + Neon + S3 wiring, env vars, CORS, smoke test.
6. **Phase F — Tests + polish:** Isolation tests, E2E, README update with live demo link.

Each phase = its own PR, runnable locally before merge.
