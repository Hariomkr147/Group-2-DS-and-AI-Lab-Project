"""Build the NCERT course packs (the format the backend loads) from data/course_packs/specs.py.

For every concept: check the spec, compute question answers, and attach up to 3 text
chunks from the NCERT chapter that teaches it (the chunks that mention the concept's
keywords most). Output goes to data/processed/course_packs/<pack id>.json. It holds
NCERT text, so it is not committed.

Checks: prerequisite ids exist, no prerequisite is at a higher level, no cycles,
every concept has questions and at least one material.
"""
import json
import math
import re
import sys
from fractions import Fraction as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "course_packs"))
from specs import PACKS  # noqa: E402

CHUNKS = ROOT / "processed" / "ncert" / "chunks.jsonl"
OUT = ROOT / "processed" / "course_packs"
MATERIALS_PER_CONCEPT, MIN_WORDS = 3, 60
EXERCISE = re.compile(r"exercise|\bQ\.\s*\d|figure it out|try these", re.I)  # question pages


def density(text: str, keywords: list[str]) -> float:
    """Keyword hits per word, so short focused passages beat long ones that mention a word once."""
    return sum(text.lower().count(k) for k in keywords) / max(len(text.split()), 1)


def fmt(value: F, decimal: bool) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    if decimal:
        text = f"{float(value):.6f}".rstrip("0")
        return text
    return f"{value.numerator}/{value.denominator}"


def answer(q) -> str:
    if q.expr is None:
        return q.ans
    value = eval(q.expr, {"F": F, "math": math, "__builtins__": {}})
    return fmt(F(value), q.dec)


def check_graph(concepts):
    ids = {c["id"]: c for c in concepts}
    assert len(ids) == len(concepts), "duplicate concept id"
    for c in concepts:
        assert c["questions"], f"{c['id']}: no questions"
        for p in c["prerequisites"]:
            assert p in ids, f"{c['id']}: unknown prerequisite {p}"
            assert ids[p]["level"] <= c["level"], f"{c['id']}: prerequisite {p} is at a higher level"
    seen, done = set(), set()

    def visit(cid):
        assert cid not in seen or cid in done, f"prerequisite cycle through {cid}"
        if cid in done:
            return
        seen.add(cid)
        for p in ids[cid]["prerequisites"]:
            visit(p)
        done.add(cid)

    for cid in ids:
        visit(cid)


def main():
    chunks = [json.loads(line) for line in open(CHUNKS, encoding="utf8")]
    OUT.mkdir(parents=True, exist_ok=True)
    for spec in PACKS:
        subject = "maths" if spec["id"].endswith("maths") else "science"
        check_graph(spec["concepts"])
        concepts = []
        for c in spec["concepts"]:
            pool = [r for r in chunks if r["subject"] == subject and r["class"] == c["cls"] and r["chapter"] == c["chapter"]]
            pool = [r for r in pool if not EXERCISE.search(r["text"]) and len(r["text"].split()) >= MIN_WORDS]
            scored = sorted(pool, key=lambda r: -density(r["text"], c["keywords"]))
            top = [r for r in scored[:MATERIALS_PER_CONCEPT] if density(r["text"], c["keywords"]) > 0]
            assert top, f"{c['id']}: no NCERT text found in class {c['cls']} chapter {c['chapter']}"
            concepts.append({
                "id": c["id"], "name": c["name"], "level": c["level"], "prerequisites": c["prerequisites"],
                "materials": [{"source": r["source"], "page": f"PDF page {r['page']}", "text": r["text"]} for r in top],
                "questions": [{"id": f"{c['id']}-{i}", "text": q.text, "answer": answer(q), "hint": q.hint,
                               "difficulty": q.difficulty} for i, q in enumerate(c["questions"], start=1)],
            })
        pack = {"id": spec["id"], "title": spec["title"], "subject": spec["subject"], "concepts": concepts}
        (OUT / f"{spec['id']}.json").write_text(json.dumps(pack, indent=2, ensure_ascii=False), encoding="utf8")
        n_q = sum(len(c["questions"]) for c in concepts)
        print(f"{spec['id']}: {len(concepts)} concepts, {n_q} questions, "
              f"{sum(len(c['prerequisites']) for c in concepts)} prerequisite links")


if __name__ == "__main__":
    main()
