from __future__ import annotations
from typing import AsyncIterator, Optional
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from app.config import settings

_openai_client: Optional[AsyncOpenAI] = None
_anthropic_client: Optional[AsyncAnthropic] = None


def _get_openai() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


def _get_anthropic() -> AsyncAnthropic:
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _anthropic_client


async def stream_gpt4o(
    model: str,
    messages: list[dict],
    system: str,
) -> AsyncIterator[str]:
    """Stream from OpenAI GPT-4o or GPT-4o-mini. Yields text chunks."""
    client = _get_openai()
    full_messages = [{"role": "system", "content": system}] + messages
    async with client.chat.completions.create(
        model=model,
        messages=full_messages,
        stream=True,
        temperature=0.7,
        max_tokens=2048,
    ) as stream:
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content


async def stream_claude(
    messages: list[dict],
    system: str,
) -> AsyncIterator[str]:
    """Stream from Anthropic Claude Sonnet 4.6. Yields text chunks."""
    client = _get_anthropic()
    async with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=system,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            yield text


async def stream_ollama(
    messages: list[dict],
    system: str,
) -> AsyncIterator[str]:
    """Stream from local Ollama instance. Yields text chunks."""
    import httpx
    full_messages = [{"role": "system", "content": system}] + messages
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            "http://localhost:11434/api/chat",
            json={
                "model": settings.ollama_model,
                "messages": full_messages,
                "stream": True,
            },
        ) as response:
            import json as json_lib
            async for line in response.aiter_lines():
                if line:
                    try:
                        data = json_lib.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
                    except json_lib.JSONDecodeError:
                        continue
