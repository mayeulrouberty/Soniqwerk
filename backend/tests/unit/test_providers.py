import pytest
from unittest.mock import AsyncMock, MagicMock, patch


async def _async_iter(items):
    for item in items:
        yield item


@pytest.mark.asyncio
async def test_stream_gpt4o_yields_chunks():
    chunk1 = MagicMock()
    chunk1.choices = [MagicMock(delta=MagicMock(content="Hello"))]
    chunk2 = MagicMock()
    chunk2.choices = [MagicMock(delta=MagicMock(content=" world"))]
    chunk3 = MagicMock()
    chunk3.choices = [MagicMock(delta=MagicMock(content=None))]

    mock_stream = MagicMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__aexit__ = AsyncMock(return_value=False)
    mock_stream.__aiter__ = lambda self: _async_iter([chunk1, chunk2, chunk3])

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_stream

    with patch("app.llm.providers._get_openai", return_value=mock_client):
        from app.llm.providers import stream_gpt4o
        chunks = []
        async for chunk in stream_gpt4o("gpt-4o", [{"role": "user", "content": "test"}], "system"):
            chunks.append(chunk)

    assert chunks == ["Hello", " world"]


@pytest.mark.asyncio
async def test_stream_claude_yields_chunks():
    mock_stream = AsyncMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__aexit__ = AsyncMock(return_value=False)

    async def _text_gen():
        yield "Bonjour"
        yield " Claude"

    mock_stream.text_stream = _text_gen()

    mock_client = MagicMock()
    mock_client.messages.stream.return_value = mock_stream

    with patch("app.llm.providers._get_anthropic", return_value=mock_client):
        from app.llm.providers import stream_claude
        chunks = []
        async for chunk in stream_claude([{"role": "user", "content": "test"}], "system"):
            chunks.append(chunk)

    assert chunks == ["Bonjour", " Claude"]


@pytest.mark.asyncio
async def test_stream_gpt4o_skips_none_content():
    chunk = MagicMock()
    chunk.choices = [MagicMock(delta=MagicMock(content=None))]

    mock_stream = MagicMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__aexit__ = AsyncMock(return_value=False)
    mock_stream.__aiter__ = lambda self: _async_iter([chunk])

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_stream

    with patch("app.llm.providers._get_openai", return_value=mock_client):
        from app.llm.providers import stream_gpt4o
        chunks = [c async for c in stream_gpt4o("gpt-4o-mini", [], "sys")]

    assert chunks == []
