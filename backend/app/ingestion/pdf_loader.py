from __future__ import annotations

from pathlib import Path
from typing import Optional

from pypdf import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def load_pdf(
    path: str, category: str, title: Optional[str] = None
) -> list[dict]:
    """
    Load a PDF and split into chunks with metadata.

    Args:
        path: Path to PDF file
        category: Document category (manuals | plugins | books | articles)
        title: Optional custom document title (defaults to filename)

    Returns:
        A list of dicts with structure:
        {
            "text": str,
            "metadata": {
                "source": str,     # original filename
                "category": str,   # manuals | plugins | books | articles
                "title": str,      # document title
                "page": int,       # 1-indexed page number
                "chunk_index": int # 0-indexed chunk within document
            }
        }
    """
    p = Path(path)
    source = p.name
    doc_title = title or p.stem.replace("_", " ").replace("-", " ").title()

    reader = PdfReader(path)
    full_text_by_page: list[tuple[int, str]] = []

    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            full_text_by_page.append((page_num, text))

    if not full_text_by_page:
        return []

    # Chunk the full document (join all pages)
    full_text = "\n\n".join(text for _, text in full_text_by_page)
    raw_chunks = _splitter.split_text(full_text)

    chunks = []
    for i, chunk_text in enumerate(raw_chunks):
        chunks.append(
            {
                "text": chunk_text,
                "metadata": {
                    "source": source,
                    "category": category,
                    "title": doc_title,
                    "page": 1,  # simplified — full doc chunking
                    "chunk_index": i,
                },
            }
        )

    return chunks
