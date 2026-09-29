"""The DB layer is thin asyncpg SQL. We assert the schema text is coherent
rather than hitting a live Postgres, keeping the suite offline."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from db import postgres as db


def test_schema_defines_core_tables():
    sql = db.SCHEMA_SQL
    for table in ("users", "projects", "milestones", "doc_chunks", "chat_messages", "files", "notes"):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql


def test_schema_enables_pgvector():
    assert 'CREATE EXTENSION IF NOT EXISTS "vector"' in db.SCHEMA_SQL


def test_doc_chunks_embedding_dimension_is_1536():
    assert "VECTOR(1536)" in db.SCHEMA_SQL
