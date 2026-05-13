import os
import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

_BUCKET = os.environ.get("AWS_S3_BUCKET", "freelance-agent-dev")
_ENDPOINT = os.environ.get("AWS_ENDPOINT_URL")  # set for LocalStack in dev


def _client():
    kwargs: dict[str, Any] = {}
    if _ENDPOINT:
        kwargs["endpoint_url"] = _ENDPOINT
    return boto3.client("s3", **kwargs)


def _note_key(user_id: str, filename: str) -> str:
    return f"users/{user_id}/notes/{filename}"


def _file_key(user_id: str, file_id: str, filename: str) -> str:
    return f"users/{user_id}/files/{file_id}/{filename}"


# --- MCP tool surface (mirrors old filesystem MCP) ---

async def filesystem_write(user_id: str, filename: str, content: str) -> str:
    key = _note_key(user_id, filename)
    try:
        _client().put_object(
            Bucket=_BUCKET,
            Key=key,
            Body=content.encode("utf-8"),
            ContentType="text/plain",
        )
        return f"Written to s3://{_BUCKET}/{key}"
    except ClientError as exc:
        logger.warning("S3 write failed: %s", exc)
        return f"S3 write failed: {exc}"


async def filesystem_read(user_id: str, filename: str) -> str:
    key = _note_key(user_id, filename)
    try:
        obj = _client().get_object(Bucket=_BUCKET, Key=key)
        return obj["Body"].read().decode("utf-8")
    except ClientError:
        return f"File not found: {filename}"


async def filesystem_list(user_id: str) -> list[str]:
    prefix = f"users/{user_id}/notes/"
    try:
        resp = _client().list_objects_v2(Bucket=_BUCKET, Prefix=prefix)
        return [
            obj["Key"].removeprefix(prefix)
            for obj in resp.get("Contents", [])
        ]
    except ClientError as exc:
        logger.warning("S3 list failed: %s", exc)
        return []


# --- Presigned URLs for direct browser uploads ---

def presign_put(user_id: str, file_id: str, filename: str, content_type: str) -> str:
    key = _file_key(user_id, file_id, filename)
    url = _client().generate_presigned_url(
        "put_object",
        Params={"Bucket": _BUCKET, "Key": key, "ContentType": content_type},
        ExpiresIn=900,  # 15 minutes
    )
    return url


def presign_get(user_id: str, file_id: str, filename: str) -> str:
    key = _file_key(user_id, file_id, filename)
    url = _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": _BUCKET, "Key": key},
        ExpiresIn=900,
    )
    return url


def delete_file(user_id: str, file_id: str, filename: str) -> None:
    key = _file_key(user_id, file_id, filename)
    try:
        _client().delete_object(Bucket=_BUCKET, Key=key)
    except ClientError as exc:
        logger.warning("S3 delete failed: %s", exc)
