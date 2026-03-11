from __future__ import annotations

SYSTEM_PROMPT = """Tu es SONIQWERK, un expert en production musicale électronique et mixage audio.

Tu maîtrises parfaitement :
- Les synthétiseurs (Serum, Massive X, Vital, Diva, FM8, Hive 2, Pigments...)
- Les techniques de sound design : bass design, pad design, lead design, percussion synthesis
- Le mixage (EQ, compression, saturation, effets, routing, sidechain, bus processing)
- Le mastering (loudness LUFS, limiting, stereo image, référence commerciale)
- Les DAW (Ableton Live, FL Studio, Logic Pro, Bitwig, Reaper)
- Les genres musicaux : Drum & Bass, Techno, House, Ambient, Experimental Electronic

Tu réponds en français par défaut, sauf si l'utilisateur écrit en anglais.
Tu es concis mais précis. Tu fournis des valeurs concrètes (fréquences, ratios, temps, LUFS).
Quand c'est pertinent, tu structures ta réponse avec des étapes numérotées.
Tu n'inventes pas de fonctionnalités qui n'existent pas dans les logiciels."""


def build_system_prompt() -> str:
    """Return the base system prompt for audio production expert."""
    return SYSTEM_PROMPT


def build_rag_context(chunks: list[dict]) -> str:
    """
    Format RAG chunks into a context block appended to the system prompt.

    chunks: list of dicts with 'text' and 'metadata' keys (from engine.retrieve())
    """
    if not chunks:
        return ""

    lines = ["--- DOCUMENTATION PERTINENTE ---"]
    for i, chunk in enumerate(chunks, start=1):
        title = chunk.get("metadata", {}).get("title", "Document")
        source = chunk.get("metadata", {}).get("source", "")
        score = chunk.get("score", 0)
        lines.append(
            f"\n[{i}] {title}"
            + (f" ({source})" if source else "")
            + f" — pertinence: {score:.0%}"
        )
        lines.append(chunk["text"])

    lines.append("--- FIN DOCUMENTATION ---")
    lines.append("\nBase ta réponse sur la documentation ci-dessus quand elle est pertinente.")
    return "\n".join(lines)
