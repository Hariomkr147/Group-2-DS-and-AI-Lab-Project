# llm-conversation-classifier (2026-11-25)

## Prompts
1. I don't want to use regex in conversation.py; we already use the LLM for these tasks.

## Links
- none

## Tools and packages
- Claude Code (Claude Opus 5.5)
- pytest, existing `app/services/llm.py` providers

## What the AI did
- `backend/app/services/conversation.py`: replaced the regex intent rules (classify, asks_where, complains_of_repeat, explain_request) with one model call, `classify(text, question)`. It returns greeting, bye, thanks, idk, menu, harder, easier, example, practice, yes, no, where, repeat or explain. It uses `MESSAGE_CLASSIFIER_PROVIDER`, skips messages over 120 characters, and returns None when the model is off or replies with anything else.
- Same file: rewrote the answer helpers (unwrap_answer, loose_number, normalize) as plain string code without regex. Grading stays exact and does not use the model.
- `backend/app/services/tutor.py`: `_converse_pack` and `_converse_ncert` make one classify call instead of four rule checks.
- Tests: added `tests/fake_classifier.py` and an autouse fixture in `conftest.py` (fixed labels for test phrases). Replaced the regex phrase tests with tests of classify against a fake model. Ran `uv run pytest`: 180 passed; the 3 AKT errors were already failing before this change.

## Notes
- Every short message now costs one model call, and on NCERT a later fallback may call `classify_message` too.
- When the model is down, "next", "harder", "yes" and the others are not recognised and fall through to the normal flow.
- Check label quality of the fine-tuned Qwen on these labels before the demo.
