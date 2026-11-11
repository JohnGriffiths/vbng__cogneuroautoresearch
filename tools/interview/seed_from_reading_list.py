#!/usr/bin/env python3
"""Assemble the pre-interview prompt from a reading-list folder of PDFs.

Usage:
    python seed_from_reading_list.py <session_dir>

Expects PDFs in <session_dir>/reading_list/. Uses pypdf for text
extraction if it's installed; otherwise falls back to listing
filenames only (still useful -- the LLM can work from titles, and you
can describe each paper verbally when you paste the prompt in).
"""

import argparse
import sys
from pathlib import Path

from _common import PROMPTS_DIR, ensure_session_dirs

EXCERPT_CHARS = 4000

try:
    from pypdf import PdfReader
    HAVE_PYPDF = True
except ImportError:
    HAVE_PYPDF = False


def extract_excerpt(pdf_path: Path) -> str:
    if not HAVE_PYPDF:
        return "(pypdf not installed -- title only, describe this paper verbally)"
    try:
        reader = PdfReader(str(pdf_path))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        text = text.strip()
        if len(text) > EXCERPT_CHARS:
            text = text[:EXCERPT_CHARS] + "\n...(truncated)..."
        return text or "(no extractable text -- likely a scanned PDF; title only)"
    except Exception as e:
        return f"(extraction failed: {e} -- title only)"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session_dir")
    args = parser.parse_args()

    paths = ensure_session_dirs(args.session_dir)
    reading_list_dir = paths["reading_list"]
    reading_list_dir.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(reading_list_dir.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {reading_list_dir} -- drop some in and re-run.", file=sys.stderr)
        sys.exit(1)

    if not HAVE_PYPDF:
        print(
            "pypdf not installed -- proceeding with filenames only "
            "(pip install pypdf for real excerpts).",
            file=sys.stderr,
        )

    instructions = (PROMPTS_DIR / "reading_list_instructions.md").read_text()

    sections = []
    for pdf in pdfs:
        excerpt = extract_excerpt(pdf)
        sections.append(f"### {pdf.name}\n\n{excerpt}")

    prompt = f"{instructions}\n\n---\n\n## Reading list\n\n" + "\n\n".join(sections)

    out_path = paths["prompts"] / "reading_list_prompt.md"
    out_path.write_text(prompt)

    print(prompt)
    print(f"\n--- saved to {out_path} ---", file=sys.stderr)
    print(
        f"Paste the above into your LLM chat, then save the reply to "
        f"{paths['responses']}/reading_list_response.md and run:\n"
        f"  python ingest_response.py {args.session_dir} 0 "
        f"{paths['responses']}/reading_list_response.md --topic 'reading list seed'",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
