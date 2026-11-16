"""Socratic question model.

Our fine-tuned Qwen (provider qwen_finetuned) writes the reply after a wrong answer (hint and probe turns).
Turns that hand out a new question keep the templates, so the question text is always exact. The template is
also used when the model is not configured, down, slow, cut off or gives away the answer.
SOCRATIC_PROVIDER picks another provider, or set it to templates to switch the model off.
"""
import logging
import os
import re

from ..schemas import Action, Concept, Question
from . import guardrails, llm

log = logging.getLogger(__name__)

# The prompt the model was fine-tuned on (docs/milestone-3/model_hosting/README.md). Keep the wording.
SYSTEM_TEMPLATE = (
    "You are a Socratic maths tutor. Guide the student one step at a time "
    "with questions and hints. Never state the final answer.\n\n"
    "Problem: {question}\n"
    "Correct final answer (for checking only, never reveal it): {answer}"
)
MODEL_ACTIONS = (Action.HINT, Action.PROBE)
DEFAULT_PROVIDER = "qwen_finetuned"
TEMPLATES_ONLY = ("", "templates", "none")   # SOCRATIC_PROVIDER values that switch the model off


def _template(action: Action, concept: Concept, question: Question | None) -> str:
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


def _from_model(provider: str, question: Question, learner_text: str) -> str | None:
    """The model's reply, or None when it cannot be used."""
    try:
        system = SYSTEM_TEMPLATE.format(question=question.text, answer=question.answer)
        text = llm.get_provider(provider).generate(learner_text, system, 256).strip()
    except Exception as e:  # not configured, unreachable, busy, bad reply
        log.warning("Socratic model unavailable (%s): %s", provider, type(e).__name__)
        return None
    if text and text[-1] not in ".?!":   # cut off at the token limit: keep the complete sentences
        ends = [m.end() for m in re.finditer(r"[.?!](?=\s)", text)]
        text = text[:ends[-1]] if ends else ""
    if not text or guardrails.leaks_answer(text, question.answer):
        log.warning("Socratic model reply rejected (%s)", "empty or cut off" if not text else "leaks the answer")
        return None
    return text


def write(action: Action, concept: Concept, question: Question | None, learner_text: str | None = None) -> str:
    provider = os.environ.get("SOCRATIC_PROVIDER", DEFAULT_PROVIDER).strip().lower()
    if provider not in TEMPLATES_ONLY and action in MODEL_ACTIONS and question and learner_text:
        reply = _from_model(provider, question, learner_text)
        if reply:
            return reply
    return _template(action, concept, question)


REDIRECT_OFF_TOPIC = "That's outside this course. Ask me about a topic from your course and we'll work on it together."
REDIRECT_ANSWER = "I won't give the final answer, but I'll guide you to it. Which step is unclear?"
