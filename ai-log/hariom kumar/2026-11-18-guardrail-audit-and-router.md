# Guardrail audit, benchmark and implementation (2026-11-18)

**Contributor:** Hariom Kumar  
**Context:** Designing a lightweight, real-time message router and safety guardrail for a Render free-tier instance (512MB RAM).

## 1. AI Tools Utilized

- **Tool Name:** Antigravity and Codex
- **Purpose of Use:** Existing guardrail code inspection, candidate model trade-off analysis, synthetic evaluation case generation, and classifier serialization scripting.
- **Shared Chat Link / Conversation File:** Local CLI interaction logs.
- **Contribution and Validation:** I formulated the problem into decoupled Intent and Scope decisions, established the Render 512MB RAM memory constraint, and chose the final model architecture. The AI was used to draft benchmark scripts and synthetic test cases. I verified all confusion matrices, latency measurements, and regression tests locally.

## 2. My Contribution and Independent Engineering

I structured the message routing guardrail around two separate questions:
1. Student Intent: What is the student trying to do? (Submit an answer attempt, ask for a hint, clarify a doubt, or off-topic conversation).
2. Curriculum Scope: Is the question within the allowed course syllabus? (such as asking biology questions in a pure maths course).

I set the deployment hardware constraints early. Because our backend runs on a Render Free instance (512MB RAM, shared vCPU), large transformer models or heavy zero-shot classifiers (like DeBERTa) risk out-of-memory errors or multi-second latency on each request. I directed the AI to evaluate lightweight CPU-friendly options.

After comparing the benchmark metrics, I chose TF-IDF with Logistic Regression. Looking at the benchmark confusion matrix, I noticed the raw classifier sometimes mistook student doubts or arithmetic remarks for an answer attempt. To prevent accidental mastery score updates, I added a safety check: the tutor backend only grades an input if there is an active question pending and the student's message contains an explicit calculation or answer token.

## 3. Significant Prompts and Responses

| Problem Addressed | Prompt (as typed) | Relevant AI Response | Action Taken |
|---|---|---|---|
| Guardrail audit | `what guardrails do we already have in backend? check both chat paths` | Traced both course-pack and NCERT chat paths in `app/services/guardrails.py` and `tutor.py`. | Confirmed regex checks for direct-answer requests exist, but identified that conversational follow-ups could bypass scope checks. |
| Candidate selection | `we are on render free tier with 512mb ram, give me 3 lightweight models to classify intent and scope` | Outlined three candidates under 512MB: TF-IDF + Logistic Regression, MiniLM-L6 embeddings, and DeBERTa-v3 zero-shot baseline. | Selected all three for controlled empirical CPU benchmarking before writing production code. |
| Benchmarking | `benchmark these 3 on cpu and show latency and accuracy` | Ran benchmark scripts measuring CPU execution latency, memory footprint, and intent/scope accuracy across 281 synthetic cases. | Analyzed trade-offs: TF-IDF achieved 78.8% intent accuracy and 93.3% scope accuracy in <3ms CPU time, whereas DeBERTa took >800ms. Selected TF-IDF for production. |
| Implementation | `tfidf is fastest and has good accuracy. implement the tfidf router plan and add tests` | Updated `backend/app/services/guardrails.py`, serialized the TF-IDF feature pipeline, and added integration tests. | Verified model serialization (`message_router.joblib`) and confirmed all 73 backend tests pass cleanly. |
| Edge-case hardening | `make sure it doesn't grade normal questions as answers if student just says a number or asks doubt` | Drafted gating logic in `tutor.py` ensuring answers are only evaluated when an active question is pending. | Tested boundary behavior: confirmed hints leave attempt counters unchanged, while valid calculations advance student sessions. |

## 4. Reasoning I Can Substantiate in Review

- Separation of Intent vs Scope: A student asking "How do plants make food?" has an informational intent, but whether it is allowed depends on the course: it is valid in NCERT Science, but out of scope in NCERT Mathematics. Decoupling intent classification from scope verification makes course boundaries configurable without retraining.
- Why TF-IDF and Logistic Regression: Sub-5ms CPU execution time with low memory use (under 25MB RAM). For school tutoring dialogues, character and word n-grams capture relevant patterns (arithmetic symbols, inquiry keywords, off-topic conversational markers) without the operational overhead of a heavy transformer pipeline.
- Guardrail against false mastery updates: A false-positive answer classification would incorrectly penalize or advance a student's Knowledge Tracing (KT) score. The secondary check ensures only legitimate answer submissions count toward attempts.

## 5. Validation Record

- Verified benchmark results across 281 synthetic evaluation cases (`backend/eval/message_router/`).
- Confirmed sub-5ms CPU latency on local runs without memory spikes.
- Tested boundary scenarios: student asking for a hint during an active question, student inputting bare numbers, student switching topics.
- Checked that backend unit tests pass (`uv run pytest -q`).
- Verified memory consumption remains well below Render's 512MB limit.

## 6. Team Accountability Declaration

- All AI-assisted code, models, and test cases incorporated into this stage have been reviewed and appropriately validated by me.
- Architectural decisions, benchmark methodologies, model choices, and edge-case guards are supported by my independent reasoning and experimental verification.
- I understand all contributions and can explain, justify, debug, and defend the guardrail and routing implementation independently during review and assessment.

**References:** `backend/Guardrail_implementation_plan.md`, `backend/eval/message_router/REPORT.md`, `backend/eval/message_router/cases.json`, `backend/app/services/guardrails.py`, `backend/app/services/tutor.py`, [arXiv:2502.15096](https://arxiv.org/abs/2502.15096).
