import os
from typing import Any
from contextlib import asynccontextmanager

import asyncpg

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=os.environ["NEON_DATABASE_URL"],
            min_size=1,
            max_size=10,
        )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def acquire():
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    github_id     TEXT UNIQUE NOT NULL,
    github_login  TEXT NOT NULL,
    email         TEXT,
    github_token_enc BYTEA,
    openai_key_enc   BYTEA,
    created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS projects (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    client      TEXT,
    repo_owner  TEXT,
    repo_name   TEXT,
    status      TEXT DEFAULT 'active',
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS milestones (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id    UUID NOT NULL,
    title      TEXT NOT NULL,
    due_date   DATE NOT NULL,
    status     TEXT DEFAULT 'open',
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notes (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id    UUID NOT NULL,
    s3_key     TEXT,
    body       TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS files (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL,
    s3_key      TEXT NOT NULL,
    filename    TEXT NOT NULL,
    mime        TEXT,
    size_bytes  BIGINT,
    uploaded_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS doc_chunks (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    source     TEXT,
    content    TEXT NOT NULL,
    embedding  VECTOR(1536) NOT NULL
);

CREATE INDEX IF NOT EXISTS doc_chunks_embedding_idx
    ON doc_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS doc_chunks_user_project_idx
    ON doc_chunks (user_id, project_id);

CREATE TABLE IF NOT EXISTS chat_messages (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL,
    session_id TEXT NOT NULL,
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS chat_messages_session_idx
    ON chat_messages (user_id, session_id, created_at);
"""


async def init_schema() -> None:
    async with acquire() as conn:
        await conn.execute(SCHEMA_SQL)


# --- users ---

async def upsert_user(
    github_id: str,
    github_login: str,
    email: str | None,
    github_token_enc: bytes | None,
) -> dict[str, Any]:
    async with acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO users (github_id, github_login, email, github_token_enc)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (github_id) DO UPDATE
              SET github_login = EXCLUDED.github_login,
                  email = EXCLUDED.email,
                  github_token_enc = COALESCE(EXCLUDED.github_token_enc, users.github_token_enc)
            RETURNING id, github_id, github_login, email, openai_key_enc, created_at
            """,
            github_id, github_login, email, github_token_enc,
        )
        return dict(row)


async def get_user_by_github_id(github_id: str) -> dict[str, Any] | None:
    async with acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM users WHERE github_id = $1", github_id
        )
        return dict(row) if row else None


async def set_openai_key(user_id: str, openai_key_enc: bytes) -> None:
    async with acquire() as conn:
        await conn.execute(
            "UPDATE users SET openai_key_enc = $1 WHERE id = $2",
            openai_key_enc, user_id,
        )


# --- projects ---

async def create_project(
    user_id: str,
    name: str,
    client: str | None,
    repo_owner: str | None,
    repo_name: str | None,
) -> dict[str, Any]:
    async with acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO projects (user_id, name, client, repo_owner, repo_name)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
            """,
            user_id, name, client, repo_owner, repo_name,
        )
        return dict(row)


async def get_projects(user_id: str) -> list[dict[str, Any]]:
    async with acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM projects WHERE user_id = $1 AND status = 'active' ORDER BY created_at",
            user_id,
        )
        return [dict(r) for r in rows]


async def has_projects(user_id: str) -> bool:
    async with acquire() as conn:
        row = await conn.fetchrow(
            "SELECT 1 FROM projects WHERE user_id = $1 LIMIT 1", user_id
        )
        return row is not None


# --- milestones ---

async def create_milestone(
    user_id: str,
    project_id: str,
    title: str,
    due_date: str,
) -> dict[str, Any]:
    async with acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO milestones (user_id, project_id, title, due_date)
            VALUES ($1, $2, $3, $4)
            RETURNING *
            """,
            user_id, project_id, title, due_date,
        )
        return dict(row)


async def get_milestones(
    user_id: str,
    project_id: str | None = None,
) -> list[dict[str, Any]]:
    async with acquire() as conn:
        if project_id:
            rows = await conn.fetch(
                """
                SELECT * FROM milestones
                WHERE user_id = $1 AND project_id = $2
                ORDER BY due_date
                """,
                user_id, project_id,
            )
        else:
            rows = await conn.fetch(
                "SELECT * FROM milestones WHERE user_id = $1 ORDER BY due_date",
                user_id,
            )
        return [dict(r) for r in rows]


async def update_milestone_status(
    user_id: str, milestone_id: str, status: str
) -> None:
    async with acquire() as conn:
        await conn.execute(
            """
            UPDATE milestones SET status = $1, updated_at = now()
            WHERE id = $2 AND user_id = $3
            """,
            status, milestone_id, user_id,
        )


# --- doc_chunks (RAG) ---

async def insert_doc_chunk(
    user_id: str,
    project_id: str,
    source: str,
    content: str,
    embedding: list[float],
) -> None:
    async with acquire() as conn:
        await conn.execute(
            """
            INSERT INTO doc_chunks (user_id, project_id, source, content, embedding)
            VALUES ($1, $2, $3, $4, $5::vector)
            """,
            user_id, project_id, source, content, str(embedding),
        )


async def similarity_search(
    user_id: str,
    query_embedding: list[float],
    k: int = 5,
    project_id: str | None = None,
) -> list[dict[str, Any]]:
    async with acquire() as conn:
        if project_id:
            rows = await conn.fetch(
                """
                SELECT content, source, project_id,
                       1 - (embedding <=> $1::vector) AS score
                FROM doc_chunks
                WHERE user_id = $2 AND project_id = $3
                ORDER BY embedding <=> $1::vector
                LIMIT $4
                """,
                str(query_embedding), user_id, project_id, k,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT content, source, project_id,
                       1 - (embedding <=> $1::vector) AS score
                FROM doc_chunks
                WHERE user_id = $2
                ORDER BY embedding <=> $1::vector
                LIMIT $3
                """,
                str(query_embedding), user_id, k,
            )
        return [dict(r) for r in rows]


async def delete_doc_chunks(user_id: str, project_id: str) -> None:
    async with acquire() as conn:
        await conn.execute(
            "DELETE FROM doc_chunks WHERE user_id = $1 AND project_id = $2",
            user_id, project_id,
        )


# --- chat_messages ---

async def append_message(
    user_id: str,
    session_id: str,
    role: str,
    content: str,
) -> None:
    async with acquire() as conn:
        await conn.execute(
            """
            INSERT INTO chat_messages (user_id, session_id, role, content)
            VALUES ($1, $2, $3, $4)
            """,
            user_id, session_id, role, content,
        )


async def get_messages(
    user_id: str,
    session_id: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    async with acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT role, content, created_at FROM chat_messages
            WHERE user_id = $1 AND session_id = $2
            ORDER BY created_at DESC
            LIMIT $3
            """,
            user_id, session_id, limit,
        )
        return [dict(r) for r in reversed(rows)]
