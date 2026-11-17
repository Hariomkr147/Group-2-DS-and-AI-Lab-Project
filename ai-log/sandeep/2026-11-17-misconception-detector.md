# misconception-detector (2026-11-17)

## Prompts
1. Let's work on misconception detector.

## Links
- backend/EEDI_RUNTIME.md ("Where to pick up", item 1)

## Tools and packages
- Claude Code (Claude Fable 5.2), Python unittest

## What the AI did
- `Ncert work/09_skill_misconception_and_scope_mapping/code/error_rules.py`: added `plain_fractions()` so the candidate check and the working check both read LaTeX `\frac`, `\dfrac`, `\tfrac`, `\times`, `\div` the same way.
- `test_working_verifier.py`: added a LaTeX regression test (match for the three fraction rules, abstain on invalid or ambiguous working).
- Ran the unit tests: the 7 tests that can load pass.

- Reviewed `backend/EEDI_RUNTIME.md` and discussed detector design (rules and Eedi labels do not generalise; test an LLM step-finder instead).
- `backend/eval/misconception/step_finder_cases.jsonl`: 50 AI-written test cases (30 maths, 20 science; 29 misconception, 7 slip, 14 correct).
- `backend/eval/misconception/eval_step_finder.py`: asks a model for the first wrong step, scores right step and false suggestions.
- Ran the Gemini baseline (gemini-3-flash-preview): right step 36/36, false suggestion 0/14. Results in `backend/eval/misconception/results/`.
- Added `--provider qwen_finetuned` to the eval script for the hosted Qwen `/predict` route.
- Backend Qwen integration: `qwen_finetuned` provider in `app/services/llm.py` and `routers/llm.py`; `app/services/socratic.py` lets the model write hint and probe turns by default (`SOCRATIC_PROVIDER=templates` switches it off), with template fallback; `tutor.py` passes the learner text; `tests/test_socratic.py` added; `.env.example` and `README.md` updated.
- Fixed `guardrails.leaks_answer`: it missed an answer at the end of a sentence ("... is 10.").
- Backend tests: 30 passed. Not tested against the live Qwen server.
- Ran the hosted Qwen on the 50 cases: right step 36/36, false suggestion 3/14 (all three on valid alternative maths methods).
- Added `backend/eval/misconception/step_finder_cases_hard.jsonl` (8 AI-written cases: valid alternative method, then an error). Qwen 7/8, Gemini 8/8.
- Renamed the provider to `qwen_finetuned`, made it the default Socratic provider, moved the eval to `backend/eval/misconception/`.
- Added `--reference last` (model sees only the final reference line). Gemini: 36/36, 8/8, false suggestion 0/14. Qwen run failed with HTTP 530 (Kaggle tunnel down); to be rerun.
- Hugging Face Space for the fine-tuned Qwen: followed https://huggingface.co/new-space/agents.md and the `huggingface-spaces` skill; wrote `backend/model_hosting/hf-space/` (`app.py`, `requirements.txt`, `README.md`); installed the `hf` CLI with `uv tool install huggingface_hub`; user logged in; created a private ZeroGPU Space on the user's account and uploaded the files.
- Space first failed at startup (PEFT loaded the adapter to CUDA); fixed with `torch_device="cpu"`. Space runs; `/predict` returned a Socratic reply and a correct step-finder reply.
- Backend `qwen_finetuned` provider can now use the Hugging Face Space (when `QWEN_URL` is an `hf.space` address) as well as the Kaggle notebook. Backend tests: 34 passed; one live call to the Space through the provider worked.
- Answer-only test on the fine-tuned Qwen through the Space: right step 32/36 and 8/8 hard cases, false suggestion 2/14.
- At the user's request, reverted the two `Ncert work` edits (`error_rules.py`, `test_working_verifier.py`) and moved the Space files from `docs/milestone-3/` to `backend/model_hosting/hf-space/`. No files outside `backend/` and `ai-log/` are changed by this session.
- Fixed a typo in `backend/.env` (`QWEN_URL==` to `QWEN_URL=`).
- Step finder in the tutor: new `backend/app/services/step_finder.py` (arithmetic check by code, wrong method by the model), wired into `tutor.py` (working graded on its last line, tutor asks for steps after a bare wrong answer, reply points at the wrong step), `wrong_step` added to `TutorReply`, `tests/test_step_finder.py` added, eval script now imports the tutor's prompt. Backend tests: 66 passed. A live five-message conversation against the Space worked.

## Notes
- Qwen's Socratic replies in the live check were generic ("could you please walk me through your solution?"); it gets no conversation history yet.
- User preference: do not change `docs/milestone-*` or `Ncert work`; keep new work in `backend/`.
- The Space is private until the user asks for it to be public. Login token: omitted.
- The 50 cases are AI-written and not yet reviewed by a person (`reviewed_by` is null). Not real learner working.
- Qwen's weakness: it sometimes calls a valid method wrong because it differs from the reference. Next: step-finder in the backend, run only after a wrong answer, with learner working collected.
- 4 test modules do not load on this machine: `pipeline.py` is not in the checkout and `Ncert work/.venv` is missing. Not caused by this change.
- Still open: learner-working evaluation, and moving the working-evidence check into the main backend detector.
