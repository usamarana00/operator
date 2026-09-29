import os
import sys
import time

import jwt
import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from auth import _decode_nextauth_jwt

SECRET = "test-nextauth-secret"


@pytest.fixture(autouse=True)
def _nextauth_secret(monkeypatch):
    monkeypatch.setenv("NEXTAUTH_SECRET", SECRET)


def _make_token(payload, secret=SECRET):
    return jwt.encode(payload, secret, algorithm="HS256")


def test_decode_valid_token_returns_payload():
    token = _make_token(
        {
            "sub": "12345",
            "github_login": "octocat",
            "email": "octocat@example.com",
            "github_token": "gho_abc123",
            "exp": int(time.time()) + 300,
        }
    )

    payload = _decode_nextauth_jwt(token)

    assert payload["sub"] == "12345"
    assert payload["github_login"] == "octocat"
    assert payload["github_token"] == "gho_abc123"


def test_decode_expired_token_raises_401():
    token = _make_token(
        {"sub": "12345", "exp": int(time.time()) - 60}
    )

    with pytest.raises(HTTPException) as exc_info:
        _decode_nextauth_jwt(token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Token expired"


def test_decode_wrong_signature_raises_401():
    token = _make_token(
        {"sub": "12345", "exp": int(time.time()) + 300}, secret="wrong-secret"
    )

    with pytest.raises(HTTPException) as exc_info:
        _decode_nextauth_jwt(token)

    assert exc_info.value.status_code == 401


def test_decode_garbage_token_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        _decode_nextauth_jwt("not-a-jwt")

    assert exc_info.value.status_code == 401
