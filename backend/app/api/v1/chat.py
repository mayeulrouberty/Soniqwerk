from __future__ import annotations
import json
import uuid
from typing import Optional
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.api.deps import verify_api_key
from app.rag.engine import retrieve
from app.llm.router import stream_response, classify_query

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    model_override: Optional[str] = None


def _sse(event_type: str, payload: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/chat")
async def chat(
    request: ChatRequest,
    _: str = Depends(verify_api_key),
):
    conversation_id = request.conversation_id or str(uuid.uuid4())
    model_choice = classify_query(request.message)

    async def generate():
        try:
            # 1. RAG retrieval
            rag_chunks = await retrieve(request.message)

            # 2. Stream LLM response
            async for chunk in stream_response(
                query=request.message,
                history=[],
                rag_chunks=rag_chunks,
                model_override=request.model_override,
            ):
                yield _sse("chunk", {"text": chunk, "conversation_id": conversation_id})

            # 3. Sources event — always emitted (empty list if no RAG results)
            sources = [
                {
                    "title": c["metadata"].get("title", c["metadata"].get("source", "Source")),
                    "source": c["metadata"].get("source", ""),
                    "score": round(c.get("score", 0), 3),
                }
                for c in rag_chunks
            ]
            yield _sse("sources", {"sources": sources})

            # 4. Done event
            yield _sse("done", {
                "model_used": model_choice.value,
                "conversation_id": conversation_id,
            })

        except TimeoutError:
            yield _sse("error", {
                "code": "LLM_TIMEOUT",
                "message": "Provider unavailable, retrying with fallback...",
            })
        except Exception as exc:
            yield _sse("error", {
                "code": "INTERNAL_ERROR",
                "message": str(exc),
            })

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
