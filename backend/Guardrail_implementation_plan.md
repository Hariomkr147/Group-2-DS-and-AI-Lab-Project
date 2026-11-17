# Guardrail implementation plan

The backend already runs rule-based guardrails. Add the benchmarked TF-IDF and logistic-regression router to the existing chat flow. It will predict student intent and curriculum scope separately, while the tutor validates grading and topic changes.

## What the backend does today

| Guardrail | Current behavior |
|---|---|
| Direct-answer requests | Both chat paths check common phrases through `guardrails.requests_answer()` and return a guidance prompt when matched. |
| Course-pack relevance and grading | `guardrails.classify_input()` uses answer patterns, numeric input and concept keyword search. During a pending exercise, short messages can still reach grading even when classified off-topic. |
| NCERT relevance and follow-ups | `tutor._handle_ncert()` uses phrase patterns for follow-ups and ranks approved textbook passages within the session's grade and subject. It asks for clarification when some chapter matches are ambiguous. |
| Answer disclosure | Course-pack replies and wrong-step feedback check for the known answer string. NCERT retrieval filters answer-risk flags and answer headings. Grounded NCERT chat has no trusted answer key for equivalent-answer checks. |

See [guardrails.py](app/services/guardrails.py), [tutor.py](app/services/tutor.py), [socratic.py](app/services/socratic.py) and [NCERT retrieval](app/services/ncert.py).

TF-IDF is currently an evaluation candidate. On 104 synthetic test cases, it reached **78.8% intent accuracy**, **93.3% scope accuracy** and **74.0% joint accuracy**, and mislabeled **six non-answer messages** as answer attempts. The development cutoff accepted 24 test messages, of which 22 had both labels correct. That cutoff is a benchmark result. Choose runtime thresholds from reviewed development examples. [Benchmark report](eval/message_router/REPORT.md)

## 1. Export the existing classifier for runtime use

- Reuse the benchmark's word and character TF-IDF features with two logistic-regression classifiers, one for intent and one for scope. Move context formatting to one shared function used by training and inference.
- Start with the [existing cases](eval/message_router/cases.json). Review the labels and add new conversations with unseen lesson contexts, short student replies, mixed intents and topics outside the selected subject. Keep conversations and related paraphrases together within each split. Use development cases to select per-decision thresholds and reserve an independent test set.
- Add a small training/export entry point under `eval/message_router/` that writes one versioned artifact containing the fitted vectorizer, both classifiers, and the label and threshold metadata. Bundle the trusted artifact with the backend and load it once per process. For a scikit-learn artifact serialized with pickle or joblib, load only the packaged artifact built by the project.
- Pin the tested scikit-learn version in the backend's local dependency setup and Render's `requirements.txt`. Benchmark the packaged loader on Render's Python version with at least one real chat request before rollout.

## 2. Route before either tutoring path changes state

Add one classifier entry point in `app/services/guardrails.py` and call it from `tutor.handle_message()`, before dispatching to the course-pack or NCERT flow. Build context from the selected course, allowed subjects and grades, current concept or chapter, pending assessment question, expected answer type when known, and the last few turns from the same session. The classifier sees the question and answer type. Keep the answer key in the grader.

Keep intent and scope as separate decisions. Reuse the current chat endpoint and response shape. Course settings constrain where a student can switch, and a supported switch needs a destination resolved by course-pack search or scoped NCERT retrieval. Treat weak evidence as uncertain. Propagate retrieval failures as service errors so callers can retry with their session state intact.

## 3. Apply deterministic checks before grading or switching

| Situation | Handling and session behavior |
|---|---|
| Direct-answer request or clear attempt to obtain an answer key | Run the existing direct-answer rule and a focused answer-key check before dispatch. Redirect to guidance. Preserve the pending exercise and mastery totals. Keep existing output checks for replies and wrong-step feedback. |
| Answer attempt | Grade only when an actual assessment question is pending and a compatible answer or worked solution can be identified independently of the classifier. Reuse numeric equivalence and worked-step checks. For ambiguous short text, ask whether it is the student's answer. NCERT open-ended guidance offers feedback without recording correctness. |
| Doubt, hint or explanation | Use the active question or chapter and recent tutor turns. Preserve the pending question, attempts and prerequisite stack. |
| Topic switch | Respect the existing explicit `new_topic` control. Resolve the requested topic within the selected curriculum. Initialize the new topic only after resolution succeeds. An unsuccessful switch leaves the active topic and any pending exercise intact. |
| Unsupported topic | Redirect within the selected course. A topic outside the current lesson can still be supported by the course. |
| Uncertain prediction or ambiguous topic | Ask one targeted question. Preserve the active exercise or chapter while clarification is pending. Reuse NCERT's clarification flow and keep the unresolved request alongside active context in the existing session JSON. |
| Clarification reply or acknowledgement | Apply a clarification reply only when there is a pending clarification. Acknowledge ordinary conversation without scoring it. |

Remove the course-pack shortcut that lets short off-topic messages reach grading. Replace NCERT's broad follow-up phrase guessing with the shared decision while keeping its scoped passage retrieval. If the artifact is unavailable or invalid, retain direct-answer handling and clearly identifiable attempts for pending questions. Ask for clarification before grading or changing topics on uncertain input.

## 4. Verify through the existing chat endpoint

- Extend [course-pack tests](tests/test_api.py) and [NCERT tests](tests/test_ncert.py). Check that `10` grades once for a pending numeric question, that the same message without a question leaves attempt counts alone, and that a hint or doubt preserves the pending question. Keep existing numeric equivalence and worked-step behavior covered.
- Exercise a fractions-to-photosynthesis switch with science enabled and with a maths-only selection. Also check a cricket prediction, a context-free “What is a cell?”, a clarification reply, and an answer-key request. Assert the intended reply, topic, pending question, prerequisite state and attempt count where applicable.
- On the independent evaluation set, report recall for answer attempts and topic switches, false grades, false unsupported redirects and clarification frequency. The regression set must pass without grading help requests, disclosing exercise answers or changing topic on failed resolution. Measure peak memory, cold load and chat latency on Render before enabling the classifier there.
