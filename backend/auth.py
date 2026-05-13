import os
import logging
from typing import Any

import jwt
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
    secret = os.environ["NEXTAUTH_SECRET"]
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


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        # NextAuth sends the token via Authorization: Bearer <jwt>
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Missing token"})

        token = auth_header.removeprefix("Bearer ").strip()

        try:
            payload = _decode_nextauth_jwt(token)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

        github_id = str(payload.get("sub", ""))
        github_login = payload.get("github_login", "")
        email = payload.get("email")
        github_token_raw = payload.get("github_token")

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

        return await call_next(request)


def get_github_token(request: Request) -> str:
    enc = getattr(request.state, "github_token_enc", None)
    if not enc:
        raise HTTPException(status_code=400, detail="GitHub token not found for user")
    return decrypt(bytes(enc))


def get_user_id(request: Request) -> str:
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_id
