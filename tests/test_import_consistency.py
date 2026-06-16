import importlib
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


def test_auth_uses_same_postgres_module_as_db():
    """auth.py must import the same postgres module object as the rest of the app,
    otherwise there are two asyncpg pools with split state."""
    import auth
    from db import postgres as canonical
    assert auth.db is canonical, (
        "auth.db is a different module object than db.postgres — duplicate pool bug"
    )
