from __future__ import annotations
import re
from enum import Enum
from typing import AsyncIterator, Optional, List, Dict, Any

from app.config import settings
from app.llm.prompts import build_system_prompt, build_rag_context
from app.llm.providers import stream_gpt4o, stream_claude, stream_ollama


class ModelChoice(str, Enum):
    CLAUDE = "claude-sonnet-4-6"
    GPT4O = "gpt-4o"
    GPT4O_MINI = "gpt-4o-mini"
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


def classify_query(query: str) -> ModelChoice:
    """
    Lightweight classifier: regex → ModelChoice.
    No LLM call — avoids extra latency and cost.

    Priority:
    1. Offline mode → OLLAMA
    2. Short FAQ (< 30 tokens, FAQ pattern) → GPT4O_MINI
    3. Creative (texture, timbre, vibe) → CLAUDE
    4. Technical (routing, LUFS, params) → GPT4O
    5. Default → GPT4O
    """
    if settings.llm_provider == "ollama":
        return ModelChoice.OLLAMA

    token_count = len(query.split())

    if token_count < 30 and _FAQ_PATTERNS.search(query):
        return ModelChoice.GPT4O_MINI

    if _CREATIVE_PATTERNS.search(query):
        return ModelChoice.CLAUDE

    if _TECHNICAL_PATTERNS.search(query):
        return ModelChoice.GPT4O

    # Default: GPT-4o for general production questions
    return ModelChoice.GPT4O


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
        # Timeout enforcement is handled at the HTTP client level (OpenAI/Anthropic SDKs).
        # TimeoutError can still be raised and caught in the outer try/except.
        if model == ModelChoice.CLAUDE:
            async for chunk in stream_claude(messages, system):
                yield chunk
        elif model in (ModelChoice.GPT4O, ModelChoice.GPT4O_MINI):
            async for chunk in stream_gpt4o(model.value, messages, system):
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
