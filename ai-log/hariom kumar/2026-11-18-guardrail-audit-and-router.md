# Individual AI usage log: Guardrail audit, benchmark and implementation

**Contributor:** Hariom Kumar  
**Work covered:** 18 November 2026  
**AI tool:** Antigravity and Codex (guardrail analysis, synthetic benchmark dataset generation, model evaluation, classifier integration)  
**Context:** Designing a lightweight, real-time message router and safety guardrail for a Render free-tier instance (512MB RAM).

## My contribution

I structured the message routing guardrail around two separate questions:
1. Student Intent: What is the student trying to do? (Submit an answer attempt, ask for a hint, clarify a doubt, or off-topic conversation).
2. Curriculum Scope: Is the question within the allowed course syllabus? (such as asking biology questions in a pure maths course).

I set the deployment hardware constraints early. Because our backend runs on a Render Free instance (512MB RAM, shared vCPU), large transformer models or heavy zero-shot classifiers (like DeBERTa) risk out-of-memory errors or multi-second latency on each request. I directed the AI to evaluate lightweight CPU-friendly options.

After comparing the benchmark metrics, I chose TF-IDF with Logistic Regression. Looking at the benchmark confusion matrix, I noticed the raw classifier sometimes mistook student doubts or arithmetic remarks for an answer attempt. To prevent accidental mastery score updates, I added a safety check: the tutor backend only grades an input if there is an active question pending and the student's message contains an explicit calculation or answer token.

## Prompts and responses

| Work | Prompt (as typed) | AI contribution and action taken |
|---|---|---|
| Guardrail audit | `what guardrails do we already have in backend? check both chat paths` | Traced both course-pack and NCERT chat paths in `app/services/guardrails.py` and `tutor.py`. Confirmed regex checks for direct-answer requests exist, but found conversational follow-ups could bypass scope checks. |
| Model candidate review | `we are on render free tier with 512mb ram, give me 3 lightweight models to classify intent and scope` | Analyzed options under the 512MB memory budget. Outlined three candidates: (1) TF-IDF n-grams with Logistic Regression, (2) MiniLM-L6 embeddings with Logistic Regression, and (3) DeBERTa-v3 zero-shot baseline. |
| Benchmarking | `benchmark these 3 on cpu and show latency and accuracy` | Generated synthetic evaluation cases (`cases.json`), ran benchmark scripts measuring CPU execution latency, memory footprint, and intent/scope accuracy. TF-IDF reached 78.8% intent accuracy and 93.3% scope accuracy in under 3ms CPU time, while DeBERTa took over 800ms. |
| Implementation plan | `tfidf is fastest and has good accuracy. implement the tfidf router plan and add tests` | Updated `backend/app/services/guardrails.py`, serialized the TF-IDF feature pipeline, and added integration tests in `backend/tests/test_api.py`. |
| Edge-case hardening | `make sure it doesn't grade normal questions as answers if student just says a number or asks doubt` | Added validation logic in `tutor.py`: a message is only passed to the grading engine if `session.pending` is set and the input matches an expected solution format. Hints leave student attempt counters unchanged. |

## Reasoning I can substantiate in review

- Separation of Intent vs Scope: A student asking "How do plants make food?" has an informational intent, but whether it is allowed depends on the course: it is valid in NCERT Science, but out of scope in NCERT Mathematics. Decoupling intent classification from scope verification makes course boundaries configurable without retraining.
- Why TF-IDF and Logistic Regression: Sub-5ms CPU execution time with low memory use (under 25MB RAM). For school tutoring dialogues, character and word n-grams capture relevant patterns (arithmetic symbols, inquiry keywords, off-topic conversational markers) without the operational overhead of a heavy transformer pipeline.
- Guardrail against false mastery updates: A false-positive answer classification would incorrectly penalize or advance a student's Knowledge Tracing (KT) score. The secondary check ensures only legitimate answer submissions count toward attempts.

## Validation record

- Verified benchmark results across 281 synthetic evaluation cases (`backend/eval/message_router/`).
- Confirmed sub-5ms CPU latency on local runs without memory spikes.
- Tested boundary scenarios: student asking for a hint during an active question, student inputting bare numbers, student switching topics.
- Checked that backend unit tests pass (`uv run pytest -q`).
- Verified memory consumption remains well below Render's 512MB limit.

**References:** `backend/Guardrail_implementation_plan.md`, `backend/eval/message_router/REPORT.md`, `backend/app/services/guardrails.py`, `backend/app/services/tutor.py`.
