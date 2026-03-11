#!/usr/bin/env python3
"""Generate tests/fixtures/sample.pdf for testing."""
from fpdf import FPDF
from pathlib import Path


def generate():
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

    out = Path(__file__).parent / "sample.pdf"
    pdf.output(str(out))
    print(f"Generated: {out}")


if __name__ == "__main__":
    generate()
