"""Backtracking for NCERT lessons.

Course packs list their prerequisites by hand. For NCERT, ncert.prerequisites reads the learning graph (approved
concept-to-concept edges whose evidence cites corpus passages) and falls back to earlier topics closest in meaning
when a topic has no graph concept. This module holds the rest of the detour: when to step back and the stack of
topics to return to. How the learner asks to move (back to the main topic, "got it", "go back to the basics",
"what should I know first?") is read by the model in socratic.classify_path; no regex rules.

Stack entries live in `session.stack` as {"passage_id", "heading", "chapter"}. Counters live in `session.pending`.
"""
STUCK_LIMIT = 2        # help requests in a row (hint, "I still don't understand") before stepping back
# No depth limit: a detour can go as deep as the prerequisites go. It cannot loop (new_ones skips topics already
# on the way) and it ends, because each prerequisite is an earlier topic in a finite corpus.


def entry(passage: dict, chapter: dict) -> dict:
    return {"passage_id": passage["passage_id"], "heading": passage["heading"], "chapter": chapter}


def new_ones(candidates: list[dict], current: dict, stack: list) -> list[dict]:
    """Candidates not already on the way (the topic itself or one we came from), by passage and by topic heading,
    so another chunk of a topic on the stack cannot start a loop."""
    on_path = {current["passage_id"], *(e["passage_id"] for e in stack)}
    topics = {_topic(current), *(_topic({**e["chapter"], "heading": e["heading"]}) for e in stack)}
    return [c for c in candidates if c["passage_id"] not in on_path and _topic(c) not in topics]


def _topic(row: dict) -> tuple:
    return row.get("book_code"), row.get("chapter"), row["heading"]
