from app.llm.prompts import build_system_prompt, build_rag_context


def test_build_system_prompt_returns_string():
    prompt = build_system_prompt()
    assert isinstance(prompt, str)
    assert len(prompt) > 100
    assert "SONIQWERK" in prompt


def test_build_system_prompt_contains_key_domains():
    prompt = build_system_prompt()
    assert "mixage" in prompt.lower() or "mixing" in prompt.lower()
    assert "synthé" in prompt.lower() or "synth" in prompt.lower()


def test_build_rag_context_empty_returns_empty():
    result = build_rag_context([])
    assert result == ""


def test_build_rag_context_formats_chunks():
    chunks = [
        {
            "text": "Un Reese bass se crée avec deux oscillateurs désaccordés.",
            "metadata": {"title": "Serum Manual", "source": "serum.pdf"},
            "score": 0.94,
        }
    ]
    result = build_rag_context(chunks)
    assert "Serum Manual" in result
    assert "Reese bass" in result
    assert "94%" in result


def test_build_rag_context_multiple_chunks():
    chunks = [
        {"text": "text A", "metadata": {"title": "Doc A"}, "score": 0.9},
        {"text": "text B", "metadata": {"title": "Doc B"}, "score": 0.8},
    ]
    result = build_rag_context(chunks)
    assert "[1]" in result
    assert "[2]" in result
    assert "Doc A" in result
    assert "Doc B" in result
