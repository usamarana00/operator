import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from agents.producer_agent import ProducerAgent
from auth import get_github_token, get_user_id
from utils.sse import guard_stream

logger = logging.getLogger(__name__)
router = APIRouter(tags=["briefing"])


@router.post("/briefing")
async def briefing(request: Request):
    user_id = get_user_id(request)
    github_token = get_github_token(request)
    logger.info("briefing requested: user=%s", user_id)
    return StreamingResponse(
        guard_stream(ProducerAgent(user_id=user_id, github_token=github_token).briefing(), "Briefing"),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
