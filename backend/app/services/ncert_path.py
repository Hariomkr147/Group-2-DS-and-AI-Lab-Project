"""Backtracking for NCERT lessons.

Course packs list their prerequisites by hand. The NCERT corpus has no such list, so the prerequisite of a topic is
found at run time (ncert.prerequisites: earlier topics closest in meaning). This module holds the rest of the
detour: when to step back, the stack of topics to return to, and how the learner asks for it.

Stack entries live in `session.stack` as {"passage_id", "heading", "chapter"}. Counters live in `session.pending`.
"""
import re

STUCK_LIMIT = 2        # help requests in a row (hint, "I still don't understand") before stepping back
MAX_DEPTH = 3          # detours inside detours

RESUME = re.compile(
    r"(?:(?:ok(?:ay)?|yes|now|so)[,.! ]*)*(?:(?:go|get|take me) back to (?:the |our )?(?:main|original|earlier|previous|first) "
    r"(?:topic|one|question|lesson)|back to (?:the |our )?(?:main|original) (?:topic|lesson)|"
    r"i(?:'m| am) ready(?: to (?:go back|continue|resume))?|resume|continue with (?:the )?(?:main|original) topic|"
    r"(?:i )?(?:get|understand|got) (?:it|this|that)(?: now)?|(?:i )?(?:understood|understand) now|"
    r"(?:ok(?:ay)?,? )?(?:that )?(?:makes sense|is clear|(?:is|it's) clear(?: now)?)|got it(?: now)?)[.! ]*", re.I)
WANTS_BASICS = re.compile(
    r"(?:(?:can we |could we |let me |let's |i (?:need|want) to )?(?:go back|step back|revise|review)(?: to)? "
    r"(?:the )?(?:basics|prerequisites?|earlier topics?|foundations?)|start (?:from|with) (?:the )?basics|"
    r"i (?:don't|do not) know the basics)[.! ]*", re.I)
ASKS_PREREQUISITES = re.compile(
    r"(?:what (?:are|is) (?:the )?prerequisites?(?: for (?:this|it)(?: topic)?)?|"
    r"what (?:should|do) i (?:know|learn|study|revise) (?:first|before(?: this)?)|"
    r"what (?:do i need to know|comes before)(?: (?:first|before)(?: this)?| this)?)[?.! ]*", re.I)


def entry(passage: dict, chapter: dict) -> dict:
    return {"passage_id": passage["passage_id"], "heading": passage["heading"], "chapter": chapter}


def can_step_back(stack: list) -> bool:
    return len(stack) < MAX_DEPTH


def new_ones(candidates: list[dict], current_id: str, stack: list) -> list[dict]:
    """Candidates not already on the way (the topic itself or one we came from)."""
    on_path = {current_id, *(e["passage_id"] for e in stack)}
    return [c for c in candidates if c["passage_id"] not in on_path]
