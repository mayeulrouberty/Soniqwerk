from __future__ import annotations
import re
from enum import Enum
from typing import AsyncIterator, Optional, List, Dict, Any

from app.config import settings
from app.llm.prompts import build_system_prompt, build_rag_context
from app.llm.providers import stream_gpt4o, stream_claude, stream_gemini, stream_ollama


class ModelChoice(str, Enum):
    CLAUDE = "claude-sonnet-4-6"
    GPT4O = "gpt-4o"
    GPT4O_MINI = "gpt-4o-mini"
    GEMINI = "gemini-2.0-flash"
    OLLAMA = "ollama"


# Regex patterns — order matters (most specific first)
_CREATIVE_PATTERNS = re.compile(
    r"\b(ambiance|texture|timbre|feel|vibe|couleur|atmosphère|caractère|"
    r"sound design|wavetable|harmonic|resonan|warmth|chaud|froid|agressif|"
    r"doux|spatial|width|depth|creative|créati|inspire|inspir)\b",
    re.IGNORECASE,
)

_TECHNICAL_PATTERNS = re.compile(
    r"\b(routing|paramètre|parameter|config|LUFS|dBFS|db|hz|kHz|ratio|"
    r"threshold|attack|release|knee|sidechain|bpm|tempo|latence|latency|"
    r"plugin|VST|AU|MIDI|CC|automation|quantiz|sample rate|bit depth|"
    r"EQ|compresseur|compressor|limiter|saturati|distortion|reverb|delay|"
    r"chorus|flanger|phaser|envelope|LFO|oscillator|filter|cutoff)\b",
    re.IGNORECASE,
)

_FAQ_PATTERNS = re.compile(
    r"^(qu'est[- ]ce|what is|c'est quoi|define|définit|difference between|"
    r"différence entre|how many|combien|when was|quand|who made|qui a fait)\b",
    re.IGNORECASE,
)


def available_providers() -> set:
    """Returns the set of ModelChoice values that have API keys configured."""
    providers = {ModelChoice.OLLAMA}  # always available (local, no key needed)
    if settings.openai_api_key:
        providers.add(ModelChoice.GPT4O)
        providers.add(ModelChoice.GPT4O_MINI)
    if settings.anthropic_api_key:
        providers.add(ModelChoice.CLAUDE)
    if settings.google_api_key:
        providers.add(ModelChoice.GEMINI)
    return providers


def _pick(preferences: list, available: set) -> ModelChoice:
    """Return the first available choice from a preference list."""
    for choice in preferences:
        if choice in available:
            return choice
    return ModelChoice.OLLAMA


def classify_query(query: str) -> ModelChoice:
    """
    Lightweight classifier: regex → ModelChoice.
    Only considers providers that have API keys configured.

    Priority per query type:
    - FAQ (short)  : GPT-4o-mini > Gemini > Claude > GPT-4o
    - Creative     : Claude > Gemini > GPT-4o > GPT-4o-mini
    - Technical    : GPT-4o > Gemini > Claude > GPT-4o-mini
    - Default      : GPT-4o > Gemini > Claude > GPT-4o-mini
    """
    if settings.llm_provider == "ollama":
        return ModelChoice.OLLAMA

    available = available_providers()
    token_count = len(query.split())

    if token_count < 30 and _FAQ_PATTERNS.search(query):
        return _pick(
            [ModelChoice.GPT4O_MINI, ModelChoice.GEMINI, ModelChoice.CLAUDE, ModelChoice.GPT4O],
            available,
        )

    if _CREATIVE_PATTERNS.search(query):
        return _pick(
            [ModelChoice.CLAUDE, ModelChoice.GEMINI, ModelChoice.GPT4O, ModelChoice.GPT4O_MINI],
            available,
        )

    if _TECHNICAL_PATTERNS.search(query):
        return _pick(
            [ModelChoice.GPT4O, ModelChoice.GEMINI, ModelChoice.CLAUDE, ModelChoice.GPT4O_MINI],
            available,
        )

    return _pick(
        [ModelChoice.GPT4O, ModelChoice.GEMINI, ModelChoice.CLAUDE, ModelChoice.GPT4O_MINI],
        available,
    )


async def stream_response(
    query: str,
    history: List[Dict[str, Any]],
    rag_chunks: Optional[List[Dict]] = None,
    model_override: Optional[str] = None,
) -> AsyncIterator[str]:
    """
    Main streaming entry point.
    1. Classify query → select model
    2. Build system prompt (+ RAG context if chunks provided)
    3. Stream from provider with fallback on error/timeout
    """
    model = ModelChoice(model_override) if model_override else classify_query(query)
    system = build_system_prompt()

    if rag_chunks:
        system = system + "\n\n" + build_rag_context(rag_chunks)

    messages = history + [{"role": "user", "content": query}]

    async def _stream_provider() -> AsyncIterator[str]:
        if model == ModelChoice.CLAUDE:
            async for chunk in stream_claude(messages, system):
                yield chunk
        elif model in (ModelChoice.GPT4O, ModelChoice.GPT4O_MINI):
            async for chunk in stream_gpt4o(model.value, messages, system):
                yield chunk
        elif model == ModelChoice.GEMINI:
            async for chunk in stream_gemini(messages, system):
                yield chunk
        elif model == ModelChoice.OLLAMA:
            async for chunk in stream_ollama(messages, system):
                yield chunk

    try:
        async for chunk in _stream_provider():
            yield chunk
    except TimeoutError:
        # Explicit timeout fallback → GPT-4o-mini
        if model != ModelChoice.GPT4O_MINI:
            async for chunk in stream_gpt4o("gpt-4o-mini", messages, system):
                yield chunk
        else:
            yield "Désolé, le service est momentanément indisponible. Réessaie dans un instant."
    except Exception:
        # Generic provider error → fallback
        if model != ModelChoice.GPT4O_MINI:
            async for chunk in stream_gpt4o("gpt-4o-mini", messages, system):
                yield chunk
        else:
            yield "Désolé, je rencontre un problème technique. Réessaie dans un instant."
