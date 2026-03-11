import os
import pytest
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("API_SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")


@pytest.fixture(scope="session", autouse=True)
def generate_sample_pdf():
    """Generate sample PDF for PDF loader tests."""
    from fpdf import FPDF

    fixtures_dir = Path(__file__).parent / "fixtures"
    fixtures_dir.mkdir(exist_ok=True)

    sample_pdf = fixtures_dir / "sample.pdf"
    if sample_pdf.exists():
        return

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(200, 10, txt="SONIQWERK Test Document", ln=True)
    pdf.ln(5)

    # Add enough text to create multiple chunks
    for i in range(30):
        pdf.multi_cell(
            0,
            10,
            txt=f"Paragraph {i+1}: This is sample audio documentation text about synthesizers, mixing, and music production. It covers topics like oscillators, filters, envelope generators, and effects processing in digital audio workstations.",
        )

    pdf.output(str(sample_pdf))
    print(f"Generated: {sample_pdf}")
