import pytest
from unittest.mock import AsyncMock, patch
from app.llm.router import classify_query, available_providers, ModelChoice

# All providers available by default in tests
_ALL = {ModelChoice.CLAUDE, ModelChoice.GPT4O, ModelChoice.GPT4O_MINI, ModelChoice.GEMINI, ModelChoice.OLLAMA}


def test_classify_creative_query_returns_claude():
    with patch("app.llm.router.available_providers", return_value=_ALL):
        assert classify_query("Comment créer une ambiance mystérieuse avec du reverb ?") == ModelChoice.CLAUDE


def test_classify_technical_query_returns_gpt4o():
    with patch("app.llm.router.available_providers", return_value=_ALL):
        assert classify_query("Quel threshold pour le compressor sidechain sur la kick ?") == ModelChoice.GPT4O


def test_classify_faq_short_query_returns_mini():
    with patch("app.llm.router.available_providers", return_value=_ALL):
        assert classify_query("Qu'est-ce que le LUFS ?") == ModelChoice.GPT4O_MINI


def test_classify_default_returns_gpt4o():
    with patch("app.llm.router.available_providers", return_value=_ALL):
        assert classify_query("Comment faire un drop dans ma track ?") == ModelChoice.GPT4O


def test_classify_wavetable_is_creative():
    with patch("app.llm.router.available_providers", return_value=_ALL):
        assert classify_query("Explique-moi comment utiliser wavetable synthesis dans Serum") == ModelChoice.CLAUDE


def test_classify_routing_is_technical():
    with patch("app.llm.router.available_providers", return_value=_ALL):
        assert classify_query("Comment configurer le routing MIDI dans Ableton ?") == ModelChoice.GPT4O


def test_classify_falls_back_to_gemini_when_no_openai():
    only_gemini = {ModelChoice.GEMINI, ModelChoice.OLLAMA}
    with patch("app.llm.router.available_providers", return_value=only_gemini):
        assert classify_query("Quel threshold pour le compressor ?") == ModelChoice.GEMINI


def test_classify_falls_back_to_gemini_when_no_claude():
    no_claude = {ModelChoice.GPT4O, ModelChoice.GPT4O_MINI, ModelChoice.GEMINI, ModelChoice.OLLAMA}
    with patch("app.llm.router.available_providers", return_value=no_claude):
        assert classify_query("Comment créer une ambiance mystérieuse ?") == ModelChoice.GEMINI


def test_classify_falls_back_to_ollama_when_no_keys():
    with patch("app.llm.router.available_providers", return_value={ModelChoice.OLLAMA}):
        assert classify_query("Anything") == ModelChoice.OLLAMA


def test_available_providers_only_ollama_when_no_keys():
    with patch("app.llm.router.settings") as mock_settings:
        mock_settings.llm_provider = "multi"
        mock_settings.openai_api_key = ""
        mock_settings.anthropic_api_key = ""
        mock_settings.google_api_key = ""
        result = available_providers()
    assert result == {ModelChoice.OLLAMA}


def test_available_providers_all_keys_set():
    with patch("app.llm.router.settings") as mock_settings:
        mock_settings.openai_api_key = "sk-test"
        mock_settings.anthropic_api_key = "sk-ant-test"
        mock_settings.google_api_key = "AIza-test"
        result = available_providers()
    assert ModelChoice.GPT4O in result
    assert ModelChoice.CLAUDE in result
    assert ModelChoice.GEMINI in result
    assert ModelChoice.OLLAMA in result


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
