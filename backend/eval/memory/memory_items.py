"""Evaluate the long-term memory notes (TUTOR_MEMORY=full, see app/services/memory.py).

1. Chat with the tutor using TUTOR_MEMORY=full (about 20 conversations).
2. Export what the model proposed, with the turn each item quotes:
       python eval/memory/memory_items.py export memory_items.csv
3. Open the CSV and fill the `correct` column for every kept item (rejected is empty): y if the note is true
   to the chat and worth remembering, n if not. Rejected items can be labelled too, to see what the checks
   threw away (were they really wrong?).
4. Score it:
       python eval/memory/memory_items.py score memory_items.csv

Reported: precision of kept items (overall and per kind), and how many items each check rejected.
Run from backend/ so the app's DATABASE_URL (.env) is used.
"""
import csv
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select  # noqa: E402

from app.db import MemoryItemRow, SessionLocal, TurnRow  # noqa: E402

FIELDS = ["id", "session_id", "kind", "quote", "note", "source_turn", "rejected", "active", "correct"]


def export(path: str) -> None:
    with SessionLocal() as db:
        rows = db.execute(select(MemoryItemRow, TurnRow.text).outerjoin(TurnRow, TurnRow.id == MemoryItemRow.turn_id)
                          .order_by(MemoryItemRow.id)).all()
    with open(path, "w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, FIELDS)
        writer.writeheader()
        for item, source in rows:
            writer.writerow({"id": item.id, "session_id": item.session_id, "kind": item.kind, "quote": item.quote,
                             "note": item.note, "source_turn": source or "", "rejected": item.rejected or "",
                             "active": item.active, "correct": ""})
    print(f"{len(rows)} items written to {path}")


def score(path: str) -> None:
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    kept = [r for r in rows if not r["rejected"]]
    labelled = [r for r in kept if r["correct"].strip().lower() in ("y", "n")]
    right = [r for r in labelled if r["correct"].strip().lower() == "y"]
    print(f"items proposed: {len(rows)}, kept: {len(kept)}, rejected: {len(rows) - len(kept)}")
    if labelled:
        print(f"precision of kept items: {len(right)}/{len(labelled)} = {len(right) / len(labelled):.2f}")
    for kind in sorted({r["kind"] for r in labelled}):
        mine = [r for r in labelled if r["kind"] == kind]
        good = sum(r["correct"].strip().lower() == "y" for r in mine)
        print(f"  {kind}: {good}/{len(mine)} = {good / len(mine):.2f}")
    print("rejected by check:")
    for reason, n in Counter(r["rejected"] for r in rows if r["rejected"]).most_common():
        wrongly = sum(r["correct"].strip().lower() == "y" for r in rows if r["rejected"] == reason)
        print(f"  {reason}: {n}" + (f" ({wrongly} of them labelled correct)" if wrongly else ""))


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("export", "score"):
        sys.exit("usage: python eval/memory/memory_items.py export|score memory_items.csv")
    {"export": export, "score": score}[sys.argv[1]](sys.argv[2])
