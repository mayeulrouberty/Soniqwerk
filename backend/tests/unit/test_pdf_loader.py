import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def test_load_pdf_returns_chunks():
    from app.ingestion.pdf_loader import load_pdf

    sample = FIXTURES_DIR / "sample.pdf"
    chunks = load_pdf(str(sample), "manuals")
    assert len(chunks) > 0
    assert all("text" in c for c in chunks)
    assert all("metadata" in c for c in chunks)


def test_load_pdf_metadata_has_required_fields():
    from app.ingestion.pdf_loader import load_pdf

    sample = FIXTURES_DIR / "sample.pdf"
    chunks = load_pdf(str(sample), "manuals")
    meta = chunks[0]["metadata"]
    assert "source" in meta
    assert "category" in meta
    assert meta["category"] == "manuals"
    assert "title" in meta
    assert "chunk_index" in meta


def test_load_pdf_with_custom_title():
    from app.ingestion.pdf_loader import load_pdf

    sample = FIXTURES_DIR / "sample.pdf"
    chunks = load_pdf(str(sample), "plugins", title="Serum Manual")
    assert chunks[0]["metadata"]["title"] == "Serum Manual"


def test_load_pdf_chunk_size_respected():
    from app.ingestion.pdf_loader import load_pdf, CHUNK_SIZE

    sample = FIXTURES_DIR / "sample.pdf"
    chunks = load_pdf(str(sample), "books")
    # All chunks should be roughly within size limits (some overlap allowed)
    for chunk in chunks:
        assert len(chunk["text"]) <= CHUNK_SIZE * 1.5  # allow some slack


def test_load_pdf_empty_returns_empty_list(tmp_path):
    """PDF with no extractable text returns empty list."""
    from fpdf import FPDF

    from app.ingestion.pdf_loader import load_pdf

    pdf = FPDF()
    pdf.add_page()
    # No text added — empty page
    empty_pdf = tmp_path / "empty.pdf"
    pdf.output(str(empty_pdf))

    result = load_pdf(str(empty_pdf), "articles")
    assert result == []
