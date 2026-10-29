"""Turn the NCERT chapter PDFs into searchable text chunks for the course pack.

For every chapter PDF: extract text page by page, clean it, drop near-empty pages,
and split long pages into chunks of at most ~250 words. Each chunk keeps where it
came from (subject, class, chapter, page) so the tutor can link a mistake back to
the exact page.

Needs fontTools (see requirements.txt); without it the minus and multiplication
signs are lost.

Output (data/processed/ncert/): chunks.jsonl (not committed), chapters.csv, stats.json
"""
import csv
import json
import logging
import re
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "ncert"
OUT = ROOT / "processed" / "ncert"
MIN_CHARS, MAX_WORDS = 200, 250
logging.getLogger("pypdf").setLevel(logging.ERROR)

# "Reprint 2025-26", bare page numbers, and print-layout footers like "Chapter-5.indd 61 ..."
NOISE = re.compile(r"^\s*(Reprint.*|\d{1,3})\s*$|^.*\.indd.*$", re.M)


def clean(text: str) -> str:
    text = NOISE.sub("", text)
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)      # re-join words hyphenated at line end
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n\n", text)
    return text.strip()


def split(text: str) -> list[str]:
    """Split on paragraph breaks into chunks of at most MAX_WORDS words."""
    chunks, current = [], []
    for para in re.split(r"\n\s*\n", text):
        words = para.split()
        if current and len(current) + len(words) > MAX_WORDS:
            chunks.append(" ".join(current))
            current = []
        current += words
    if current:
        chunks.append(" ".join(current))
    return chunks


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    chapters, stats = [], {"chunks": 0, "pages": 0, "pages_kept": 0, "pages_failed": 0, "books": {}}
    with open(OUT / "chunks.jsonl", "w", encoding="utf8") as f:
        for book in sorted(RAW.iterdir()):
            subject, cls = book.name.split("_class")
            cls = int(cls)
            n_chunks = 0
            for pdf in sorted(book.glob("*.pdf")):
                chapter = int(pdf.stem[-2:])
                pages = PdfReader(pdf).pages
                title = ""
                for i, page in enumerate(pages, start=1):
                    try:
                        text = clean(page.extract_text() or "")
                    except Exception:  # e.g. pypdf token limit on a page full of drawings
                        stats["pages_failed"] += 1
                        continue
                    stats["pages"] += 1
                    if len(text) < MIN_CHARS:
                        continue
                    stats["pages_kept"] += 1
                    if not title:  # first line is usually the running title, e.g. "ALGEBRAIC EXPRESSIONS  93"
                        title = re.sub(r"\s*\d+\s*$", "", text.splitlines()[0]).strip()[:80]
                    for j, chunk in enumerate(split(text)):
                        row = {"id": f"ncert-{subject}-{cls}-{chapter:02d}-p{i:03d}-{j}",
                               "course": f"ncert-{subject}", "subject": subject, "class": cls,
                               "level": cls, "chapter": chapter, "page": i,
                               "source": f"NCERT {subject.title()} Class {cls}, chapter {chapter}",
                               "text": chunk}
                        f.write(json.dumps(row, ensure_ascii=False) + "\n")
                        n_chunks += 1
                chapters.append({"subject": subject, "class": cls, "chapter": chapter,
                                 "title_guess": title, "pages": len(pages), "file": pdf.name})
            stats["books"][book.name] = {"chapters": len(list(book.glob('*.pdf'))), "chunks": n_chunks}
            stats["chunks"] += n_chunks

    with open(OUT / "chapters.csv", "w", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=chapters[0])
        w.writeheader()
        w.writerows(chapters)
    (OUT / "stats.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
