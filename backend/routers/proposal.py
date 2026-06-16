import html
import logging
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from agents.producer_agent import ProducerAgent
from auth import get_github_token, get_user_id
from db import postgres as db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["proposal"])


class ProposalRequest(BaseModel):
    client: str
    description: str
    budget: str = ""
    session_id: str = ""


def _parse_sse_content(chunk: str) -> tuple[str, str] | None:
    import json

    if not chunk.startswith("data: "):
        return None
    try:
        event = json.loads(chunk.removeprefix("data: ").strip())
    except json.JSONDecodeError:
        return None
    return str(event.get("type", "")), str(event.get("content", ""))


async def _proposal_stream(
    *,
    user_id: str,
    github_token: str,
    body: ProposalRequest,
) -> AsyncIterator[str]:
    final_content = ""
    agent = ProducerAgent(user_id=user_id, github_token=github_token)

    async for chunk in agent.proposal(
        description=body.description,
        client=body.client,
        budget=body.budget,
    ):
        parsed = _parse_sse_content(chunk)
        if parsed and parsed[0] == "final":
            final_content = parsed[1]
        yield chunk

    if final_content and body.session_id:
        await db.append_message(user_id, body.session_id, "assistant", final_content)


@router.post("/proposal")
async def proposal(body: ProposalRequest, request: Request):
    user_id = get_user_id(request)
    github_token = get_github_token(request)
    if not body.client.strip() or not body.description.strip():
        raise HTTPException(status_code=422, detail="Client and description are required")

    logger.info("proposal requested: user=%s client=%s", user_id, body.client)
    return StreamingResponse(
        _proposal_stream(user_id=user_id, github_token=github_token, body=body),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/proposal/{session_id}/pdf")
async def proposal_pdf(session_id: str, request: Request):
    user_id = get_user_id(request)

    messages = await db.get_messages(user_id, session_id, limit=20)
    content = next(
        (
            message["content"]
            for message in reversed(messages)
            if message.get("role") == "assistant"
        ),
        "",
    )
    if not content:
        raise HTTPException(status_code=404, detail="Proposal not found")

    try:
        from weasyprint import HTML

        document = f"""
        <!doctype html>
        <html>
          <head>
            <meta charset="utf-8">
            <style>
              body {{ font-family: sans-serif; line-height: 1.5; padding: 32px; }}
              pre {{ white-space: pre-wrap; font-family: inherit; }}
            </style>
          </head>
          <body><pre>{html.escape(content)}</pre></body>
        </html>
        """
        pdf = HTML(string=document).write_pdf()
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="proposal-{session_id[:8]}.pdf"'},
        )
    except Exception as exc:
        logger.warning("proposal pdf fallback for session=%s: %s", session_id, exc)
        return Response(
            content=content,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="proposal-{session_id[:8]}.md"'},
        )
