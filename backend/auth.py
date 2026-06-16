import os
import logging
from typing import Any

import jwt
import requests
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from cryptography.fernet import Fernet

from backend.db import postgres as db

logger = logging.getLogger(__name__)

# Routes that don't require authentication
_PUBLIC_PATHS = {"/", "/health", "/docs", "/openapi.json", "/redoc"}


def _fernet() -> Fernet:
    key = os.environ["APP_ENCRYPTION_KEY"]
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(plaintext: str) -> bytes:
    return _fernet().encrypt(plaintext.encode())


def decrypt(ciphertext: bytes) -> str:
    return _fernet().decrypt(ciphertext).decode()


def _decode_nextauth_jwt(token: str) -> dict[str, Any]:
    secret = os.environ.get("NEXTAUTH_SECRET")
    if not secret:
        raise HTTPException(status_code=401, detail="NEXTAUTH_SECRET is not configured")
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")


def _token_kind(token: str) -> str:
    if token.startswith("gho_"):
        return "github_oauth"
    if token.count(".") == 2:
        return "jwt"
    return "unknown"


def _get_github_user(token: str) -> dict[str, Any]:
    response = requests.get(
        "https://api.github.com/user",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "freelance-agent",
        },
        timeout=10,
    )
    if response.status_code != 200:
        logger.warning(
            "GitHub token validation failed: status=%s token_kind=%s",
            response.status_code,
            _token_kind(token),
        )
        raise HTTPException(status_code=401, detail="Invalid GitHub token")
    return response.json()


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        # NextAuth sends the token via Authorization: Bearer <jwt>
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Missing token"})

        token = auth_header.removeprefix("Bearer ").strip()
        token_kind = _token_kind(token)
        logger.info("Auth start: path=%s token_kind=%s", request.url.path, token_kind)

        github_token_raw = None
        auth_source = "nextauth_jwt"
        try:
            payload = _decode_nextauth_jwt(token)
            github_id = str(payload.get("sub", ""))
            github_login = payload.get("github_login", "")
            email = payload.get("email")
            github_token_raw = payload.get("github_token")
        except HTTPException:
            try:
                github_user = _get_github_user(token)
            except HTTPException as exc:
                return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
            github_id = str(github_user.get("id", ""))
            github_login = github_user.get("login", "")
            email = github_user.get("email")
            github_token_raw = token
            auth_source = "github_oauth"

        if not github_id:
            return JSONResponse(status_code=401, content={"detail": "Token missing sub"})

        # Encrypt and upsert user on every request (no-op if unchanged)
        github_token_enc = encrypt(github_token_raw) if github_token_raw else None
        try:
            user = await db.upsert_user(
                github_id=github_id,
                github_login=github_login,
                email=email,
                github_token_enc=github_token_enc,
            )
        except Exception:
            logger.exception("DB upsert_user failed for github_id=%s", github_id)
            return JSONResponse(status_code=503, content={"detail": "Database unavailable"})

        request.state.user_id = str(user["id"])
        request.state.github_login = github_login
        request.state.github_token_enc = user.get("github_token_enc")
        logger.info(
            "Auth ok: path=%s source=%s github_id=%s login=%s has_raw_github_token=%s has_stored_github_token=%s user_id=%s",
            request.url.path,
            auth_source,
            github_id,
            github_login,
            bool(github_token_raw),
            bool(request.state.github_token_enc),
            request.state.user_id,
        )

        return await call_next(request)


def get_github_token(request: Request) -> str:
    enc = getattr(request.state, "github_token_enc", None)
    if not enc:
        logger.warning(
            "GitHub token missing on request state: path=%s user_id=%s login=%s",
            request.url.path,
            getattr(request.state, "user_id", ""),
            getattr(request.state, "github_login", ""),
        )
        raise HTTPException(status_code=400, detail="GitHub token not found for user")
    return decrypt(bytes(enc))


def get_user_id(request: Request) -> str:
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_id
