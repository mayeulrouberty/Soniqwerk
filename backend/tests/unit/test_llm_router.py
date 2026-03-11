import pytest
from unittest.mock import AsyncMock, patch
from app.llm.router import classify_query, ModelChoice


def test_classify_creative_query_returns_claude():
    result = classify_query("Comment créer une ambiance mystérieuse avec du reverb ?")
    assert result == ModelChoice.CLAUDE


def test_classify_technical_query_returns_gpt4o():
    result = classify_query("Quel threshold pour le compressor sidechain sur la kick ?")
    assert result == ModelChoice.GPT4O


def test_classify_faq_short_query_returns_mini():
    result = classify_query("Qu'est-ce que le LUFS ?")
    assert result == ModelChoice.GPT4O_MINI


def test_classify_default_returns_gpt4o():
    result = classify_query("Comment faire un drop dans ma track ?")
    assert result == ModelChoice.GPT4O


def test_classify_wavetable_is_creative():
    result = classify_query("Explique-moi comment utiliser wavetable synthesis dans Serum")
    assert result == ModelChoice.CLAUDE


def test_classify_routing_is_technical():
    result = classify_query("Comment configurer le routing MIDI dans Ableton ?")
    assert result == ModelChoice.GPT4O


@pytest.mark.asyncio
async def test_stream_response_yields_chunks():
    async def _mock_stream(*args, **kwargs):
        yield "Hello"
        yield " world"

    with patch("app.llm.router.stream_gpt4o", side_effect=_mock_stream), \
         patch("app.llm.router.classify_query", return_value=ModelChoice.GPT4O):
        from app.llm.router import stream_response
        chunks = []
        async for chunk in stream_response("test", []):
            chunks.append(chunk)

    assert chunks == ["Hello", " world"]


@pytest.mark.asyncio
async def test_stream_response_with_rag_chunks():
    rag_chunks = [{"text": "Serum doc", "metadata": {"title": "Serum"}, "score": 0.9}]

    async def _mock_stream(*args, **kwargs):
        yield "response"

    with patch("app.llm.router.stream_claude", side_effect=_mock_stream), \
         patch("app.llm.router.classify_query", return_value=ModelChoice.CLAUDE):
        from app.llm.router import stream_response
        chunks = [c async for c in stream_response("test", [], rag_chunks=rag_chunks)]

    assert chunks == ["response"]


@pytest.mark.asyncio
async def test_stream_response_model_override():
    async def _mock_mini(*args, **kwargs):
        yield "mini"

    with patch("app.llm.router.stream_gpt4o", side_effect=_mock_mini):
        from app.llm.router import stream_response
        chunks = [c async for c in stream_response("test", [], model_override="gpt-4o-mini")]

    assert chunks == ["mini"]


@pytest.mark.asyncio
async def test_stream_response_timeout_falls_back():
    call_count = {"n": 0}

    async def _timeout_stream(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise TimeoutError("provider timeout")
        yield "fallback"

    with patch("app.llm.router.stream_gpt4o", side_effect=_timeout_stream), \
         patch("app.llm.router.classify_query", return_value=ModelChoice.GPT4O):
        from app.llm.router import stream_response
        chunks = [c async for c in stream_response("test", [])]

    assert chunks == ["fallback"]
