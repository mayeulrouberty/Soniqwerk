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
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)

    # Add enough text to create multiple chunks (>1000 chars each)
    for i in range(40):
        # Use write() which handles line wrapping safely
        pdf.write(
            8,
            f"Paragraph {i+1}: This is sample audio documentation about synthesizers "
            f"mixing and music production. It covers oscillators filters envelope "
            f"generators and effects processing in digital audio workstations. "
            f"The Serum synthesizer has two main oscillators with wavetable synthesis. "
            f"Compression is used to control dynamics in the mix. "
        )
        pdf.ln(6)

    pdf.output(str(sample_pdf))
    print(f"Generated: {sample_pdf}")
