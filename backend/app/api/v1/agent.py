from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agent.react_agent import stream_agent
from app.api.deps import verify_api_key

router = APIRouter()


class AgentRequest(BaseModel):
    query: str


async def _event_stream(query: str) -> AsyncIterator[str]:
    async for event in stream_agent(query):
        yield f"data: {json.dumps(event)}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/agent")
async def agent_endpoint(
    request: AgentRequest,
    _: str = Depends(verify_api_key),
) -> StreamingResponse:
    return StreamingResponse(
        _event_stream(request.query),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
