import uuid
from typing import Any

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from auth import get_user_id
from db import postgres as db
from mcp.s3_fs import presign_put, presign_get, delete_file

router = APIRouter(prefix="/files", tags=["files"])


class PresignRequest(BaseModel):
    project_id: str
    filename: str
    content_type: str


class PresignResponse(BaseModel):
    file_id: str
    upload_url: str
    s3_key: str


class FileMetadataRequest(BaseModel):
    file_id: str
    project_id: str
    filename: str
    content_type: str
    size_bytes: int


@router.post("/presign", response_model=PresignResponse)
async def presign_upload(body: PresignRequest, request: Request) -> Any:
    user_id = get_user_id(request)

    # Verify project belongs to this user
    projects = await db.get_projects(user_id)
    if not any(str(p["id"]) == body.project_id for p in projects):
        raise HTTPException(status_code=404, detail="Project not found")

    file_id = str(uuid.uuid4())
    upload_url = presign_put(
        user_id=user_id,
        file_id=file_id,
        filename=body.filename,
        content_type=body.content_type,
    )
    s3_key = f"users/{user_id}/files/{file_id}/{body.filename}"

    return PresignResponse(file_id=file_id, upload_url=upload_url, s3_key=s3_key)


@router.post("/", status_code=201)
async def confirm_upload(body: FileMetadataRequest, request: Request) -> dict[str, Any]:
    user_id = get_user_id(request)

    async with db.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO files (id, project_id, user_id, s3_key, filename, mime, size_bytes)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id, filename, mime, size_bytes, uploaded_at
            """,
            body.file_id,
            body.project_id,
            user_id,
            f"users/{user_id}/files/{body.file_id}/{body.filename}",
            body.filename,
            body.content_type,
            body.size_bytes,
        )
    return dict(row)


@router.get("/")
async def list_files(request: Request, project_id: str | None = None) -> list[dict[str, Any]]:
    user_id = get_user_id(request)

    async with db.acquire() as conn:
        if project_id:
            rows = await conn.fetch(
                """
                SELECT id, project_id, filename, mime, size_bytes, uploaded_at
                FROM files WHERE user_id = $1 AND project_id = $2
                ORDER BY uploaded_at DESC
                """,
                user_id, project_id,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT id, project_id, filename, mime, size_bytes, uploaded_at
                FROM files WHERE user_id = $1
                ORDER BY uploaded_at DESC
                """,
                user_id,
            )
    return [dict(r) for r in rows]


@router.get("/{file_id}/download")
async def download_url(file_id: str, request: Request) -> dict[str, str]:
    user_id = get_user_id(request)

    async with db.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT filename FROM files WHERE id = $1 AND user_id = $2",
            file_id, user_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="File not found")

    url = presign_get(user_id=user_id, file_id=file_id, filename=row["filename"])
    return {"url": url}


@router.delete("/{file_id}", status_code=204)
async def delete(file_id: str, request: Request) -> None:
    user_id = get_user_id(request)

    async with db.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT filename FROM files WHERE id = $1 AND user_id = $2",
            file_id, user_id,
        )
    if not row:
        raise HTTPException(status_code=404, detail="File not found")

    delete_file(user_id=user_id, file_id=file_id, filename=row["filename"])

    async with db.acquire() as conn:
        await conn.execute(
            "DELETE FROM files WHERE id = $1 AND user_id = $2",
            file_id, user_id,
        )
