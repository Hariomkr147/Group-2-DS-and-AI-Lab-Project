"""Socratic question model.

Stub: templates. Replace `write` with the fine-tuned Qwen3-4B + LoRA model; it
must never state the answer (the output guardrail checks this).
"""
from ..schemas import Action, Concept, Question


def write(action: Action, concept: Concept, question: Question | None) -> str:
    q = question.text if question else ""
    if action == Action.ASK:
        return f"Let's work it out together. First, a question on {concept.name}: {q}"
    if action == Action.BACKTRACK:
        return f"Let's revisit {concept.name} (Level {concept.level}) first. {q}"
    if action == Action.ADVANCE:
        return f"Good. Now back to {concept.name}: {q}"
    if action == Action.HINT:
        return f"Not quite. Hint: {question.hint if question else ''} Try again: {q}"
    if action == Action.PROBE:
        return f"Let's slow down. What does the question on {concept.name} ask you to find? {q}"
    if action == Action.DONE:
        return f"You reached it yourself. Ready for a harder {concept.name} question?"
    return ""


REDIRECT_OFF_TOPIC = "That's outside this course. Ask me about a topic from your course and we'll work on it together."
REDIRECT_ANSWER = "I won't give the final answer, but I'll guide you to it. Which step is unclear?"
