"""Tutor controller: picks the next step.

Stub: fixed rules, which the report keeps as the baseline. Replace `decide` with
the trained controller model; it receives the same inputs and returns a Decision.
"""
from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..db import SessionRow
from ..schemas import Action
from . import course_store, learner_model

WEAK = 0.6          # readiness below this counts as a gap
MAX_TRIES = 2       # wrong answers on one concept before moving on to a probe


@dataclass
class Decision:
    action: Action
    concept_id: str


def decide(db: Session, session: SessionRow, correct: bool) -> Decision:
    """Decide after the learner answered a question on session.current_concept."""
    cur = session.current_concept
    if correct:
        session.tries = 0
        if cur == session.target_concept:
            return Decision(Action.DONE, cur)
        stack = list(session.stack)
        nxt = stack.pop() if stack else session.target_concept
        session.stack = stack
        return Decision(Action.ADVANCE, nxt)

    session.tries += 1
    concept = course_store.get_concept(db, session.course_id, cur)
    weak = [p for p in concept.prerequisites
            if learner_model.readiness(db, session.learner_id, session.course_id, p) < WEAK]
    if weak:
        session.stack = [*session.stack, cur]
        session.tries = 0
        return Decision(Action.BACKTRACK, weak[0])
    action = Action.HINT if session.tries <= MAX_TRIES else Action.PROBE
    return Decision(action, cur)
