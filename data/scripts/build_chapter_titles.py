"""Add verified chapter titles to data/processed/ncert/chapters.csv.

Titles live in data/course_packs/chapter_titles.csv. Each was checked against the
chapter's running page header or the book's contents page. Chapters not listed there
are marked "needs_review" (reading titles automatically from page 1 was wrong for
about half the chapters, so we do not guess).
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "processed" / "ncert" / "chapters.csv"
VERIFIED = ROOT / "course_packs" / "chapter_titles.csv"


def main():
    with open(VERIFIED, encoding="utf8") as f:
        titles = {(r["subject"], r["class"], r["chapter"]): r["title"] for r in csv.DictReader(f)}
    with open(CSV, encoding="utf8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r.pop("title_guess", None)
        r.pop("title", None)
        r.pop("title_status", None)
        title = titles.get((r["subject"], r["class"], r["chapter"]), "")
        r["title"], r["title_status"] = title, "verified" if title else "needs_review"
    with open(CSV, "w", newline="", encoding="utf8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(sum(r["title_status"] == "verified" for r in rows), "of", len(rows), "titles verified")


if __name__ == "__main__":
    main()
