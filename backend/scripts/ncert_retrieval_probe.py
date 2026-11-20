"""Print the top NCERT passages and scores for a set of test queries, to tune MIN_SCORE / CHAPTER_MARGIN.

Run from backend/ with the app's environment (DATABASE_URL, NCERT_ENABLED=1, and either a local encoder
or NCERT_EMBEDDING_URL / NCERT_EMBEDDING_API_KEY):

    python scripts/ncert_retrieval_probe.py                    # built-in queries
    python scripts/ncert_retrieval_probe.py "what is 4 * 6"    # your own queries

Read-only. Nothing is written to the database.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import ncert  # noqa: E402

QUERIES = [
    "what is 4 * 6",
    "explain 4 x 0.005 step by step",
    "the price of one pencil is 10 rupees, what is the price of 100 pencils",
    "multiplication of decimals",
    "how do I multiply a decimal by a whole number",
    "what is a force",
    "what is photosynthesis",
    "solve 2x + 3 = 11",
    "area of a triangle",
    "what is 20% of 50",
]


def main(queries: list[str]) -> None:
    for query in queries:
        print(f"\n=== {query}")
        for label, chapters in (("best passages", False), ("best per chapter", True)):
            rows = ncert.rank(query, {}, limit=5, chapters=chapters)
            print(f"  [{label}]")
            for row in rows:
                flag = "" if row["score"] >= ncert.MIN_SCORE else "  (below MIN_SCORE)"
                print(f"    {row['score']:.3f}  Class {row['grade']} {row['subject']} ch{row['chapter']}  "
                      f"{ncert.topic_title(row['heading'])[:60]}{flag}")
            if chapters and len(rows) > 1:
                gap = rows[0]["score"] - rows[1]["score"]
                print(f"    top-2 gap {gap:.3f} -> {'asks to clarify' if gap < ncert.CHAPTER_MARGIN else 'clear winner'}")


if __name__ == "__main__":
    main(sys.argv[1:] or QUERIES)
