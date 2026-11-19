# Guardrail audit, benchmark and implementation (2026-11-18)

**Contributor:** Hariom Kumar  
**Context:** Designing a lightweight, real-time message router and safety guardrail for a Render free-tier instance (512MB RAM).

## 1. AI Tools Utilized

- **Tool Name:** Antigravity and Codex (GPT-6)
- **Skills Invoked:** **`ponytail`** skill (invoked during backend audit to enforce senior developer simplicity, eliminate over-engineered dependencies, and prioritize lightweight native/stdlib solutions over heavy neural architectures).
- **Purpose of Use:** Existing guardrail code inspection, CPU latency and RAM profiling, synthetic evaluation case generation, and classifier pipeline serialization.
- **Shared Chat Link / Conversation File:** Local CLI interaction logs.
- **Contribution and Validation:** I formulated the problem by separating Intent from Scope, applied the **`ponytail`** skill during backend audit to reject bloated transformer dependencies in favor of a fast scikit-learn classifier suitable for Render's 512MB RAM limit, and designed the attempt gating safety rule. I verified confusion matrices, latency (<3ms), and all 73 backend unit tests locally.

## 2. My Contribution and Independent Engineering

I structured the message routing guardrail around two separate questions:
1. Student Intent: What is the student trying to do? (Submit an answer attempt, ask for a hint, clarify a doubt, or off-topic conversation).
2. Curriculum Scope: Is the question within the allowed course syllabus? (such as asking biology questions in a pure maths course).

During the backend audit, I applied the **`ponytail`** skill to rigorously evaluate candidate approaches under our deployment hardware constraints (Render Free tier: 512MB RAM, shared vCPU). Heavy transformer models or zero-shot bi-encoders (such as DeBERTa-v3 or RoBERTa) would cause out-of-memory errors and second-level latency spikes. Following the ponytail principle of choosing the simplest working solution, I directed the AI to evaluate lightweight CPU-friendly options.

After comparing benchmark metrics across candidate models, I selected TF-IDF with Logistic Regression. Examining the benchmark confusion matrix, I noticed the raw classifier occasionally mistook student doubts or arithmetic remarks for an answer attempt. To prevent accidental mastery score updates, I designed and added a safety gating check in `backend/app/services/tutor.py`: the tutor backend only grades an input if there is an active question pending and the student's message contains an explicit calculation or answer token.

## 3. Significant Prompts and Responses

| Problem Addressed | Prompt (as typed) | Relevant AI Response | Action Taken |
|---|---|---|---|
| Guardrail audit with Ponytail | `Audit backend/app/services/guardrails.py and tutor.py using the ponytail skill guidelines: identify unnecessary complexity and evaluate current regex guards. We are deploying on a Render free tier instance with only 512MB RAM and shared vCPU, so we must eliminate heavy dependencies, avoid speculative abstractions, and keep the solution minimal.` | Traced both course-pack and NCERT chat paths in `app/services/guardrails.py` and `tutor.py`; highlighted regex limitations and recommended against heavy deep learning runtimes. | Confirmed regex checks for direct-answer requests exist, but identified that conversational follow-ups could bypass scope checks without a classifier. |
| Candidate selection | `Formulate a two-stage routing specification that strictly separates student intent (attempt, hint, doubt, conversation) from curriculum scope (in-scope vs out-of-scope). Propose three candidate models that can execute within our 512MB RAM ceiling and provide empirical evaluation code.` | Outlined three candidates under 512MB: TF-IDF + Logistic Regression, MiniLM-L6 embeddings, and DeBERTa-v3 zero-shot baseline. | Selected all three for controlled empirical CPU benchmarking before writing production code. |
| Benchmarking | `Run an empirical CPU benchmark comparing TF-IDF + Logistic Regression, MiniLM-L6 embeddings, and DeBERTa-v3 zero-shot on 281 synthetic evaluation cases (backend/eval/message_router/cases.json). Report memory usage, p50/p95 latency on CPU, intent accuracy, and scope accuracy.` | Ran benchmark scripts measuring CPU execution latency, memory footprint, and intent/scope accuracy across 281 synthetic cases. | Analyzed trade-offs: TF-IDF achieved 78.8% intent accuracy and 93.3% scope accuracy in <3ms CPU time, whereas DeBERTa took >800ms. Selected TF-IDF for production. |
| Implementation | `The benchmark proves TF-IDF + Logistic Regression achieves 78.8% intent accuracy and 93.3% scope accuracy with sub-3ms CPU latency and under 25MB RAM. Implement the TF-IDF pipeline in guardrails.py, serialize the model to message_router.joblib, and ensure graceful fallback to regex if the asset is missing.` | Updated `backend/app/services/guardrails.py`, serialized the TF-IDF feature pipeline, and added integration tests. | Verified model serialization (`message_router.joblib`) and confirmed all 73 backend tests pass cleanly. |
| Edge-case hardening | `Looking at the confusion matrix, numerical queries like 'Step 2 has 4 legs' are sometimes flagged as answer attempts. Add gating logic in tutor.py so that answer grading only occurs when session state has an active question pending, leaving hint requests and conceptual doubts to the conversational tutor.` | Drafted gating logic in `tutor.py` ensuring answers are only evaluated when an active question is pending. | Tested boundary behavior: confirmed hints leave attempt counters unchanged, while valid calculations advance student sessions. |

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
