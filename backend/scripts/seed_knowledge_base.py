#!/usr/bin/env python3
"""
Seed the SONIQWERK RAG knowledge base from data/documents/.

Usage:
    python scripts/seed_knowledge_base.py            # ingest all PDFs
    python scripts/seed_knowledge_base.py --dry-run  # list files only
"""
from __future__ import annotations
import argparse
import asyncio
import glob
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ingestion.pdf_loader import load_pdf
from app.rag.embeddings import embed_texts
from app.rag.collections import get_collection

DOC_DIRS: dict[str, str] = {
    "data/documents/manuals/":          "manuals",
    "data/documents/plugins_effects/":  "plugins",
    "data/documents/plugins_synths/":   "plugins",
    "data/documents/books/":            "books",
    "data/documents/articles/":         "articles",
}


async def seed(dry_run: bool = False) -> None:
    total_docs = 0
    total_chunks = 0

    for dir_path, category in DOC_DIRS.items():
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        pdfs = glob.glob(os.path.join(dir_path, "**/*.pdf"), recursive=True)

        for pdf_path in sorted(pdfs):
            title = Path(pdf_path).stem.replace("_", " ").replace("-", " ").title()
            print(f"  PDF: {title}  [{category}]  ...", end=" ", flush=True)

            if dry_run:
                print("(dry-run)")
                total_docs += 1
                continue

            try:
                chunks = load_pdf(pdf_path, category, title)
                if not chunks:
                    print("WARNING: no text extracted")
                    continue

                texts = [c["text"] for c in chunks]
                embeddings = await embed_texts(texts)

                collection = get_collection(category)
                doc_slug = Path(pdf_path).stem.lower().replace(" ", "_")[:40]
                ids = [f"{doc_slug}_{i}" for i in range(len(chunks))]
                collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=[c["metadata"] for c in chunks],
                )
                total_docs += 1
                total_chunks += len(chunks)
                print(f"OK  {len(chunks)} chunks")

            except Exception as exc:
                print(f"ERROR: {exc}")

    print(f"\n{'DRY-RUN -- ' if dry_run else ''}Done: {total_docs} documents, {total_chunks} chunks indexed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed SONIQWERK knowledge base")
    parser.add_argument("--dry-run", action="store_true", help="List PDFs without ingesting")
    args = parser.parse_args()
    asyncio.run(seed(dry_run=args.dry_run))
