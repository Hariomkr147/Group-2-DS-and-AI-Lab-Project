# Backend topic audit (2026-11-19)

## Prompts
1. Audit the backend and fix textbook chat across all topics.

## Links
- https://huggingface.co/spaces/21f1006125/Qwen-3-test

## Tools and packages
- Codex (GPT-6), FastAPI, pytest, Playwright, Supabase, Hugging Face.

## What the AI did
- Updated chat routing, passage reuse and follow-up prompts. Added course-pack validation and regression tests.
- Ran the backend and browser suites. Checked fallback replies and citation fields for 2,346 topic entries. Exercised two chat turns per grade and subject using local sessions and the real corpus.

## Notes
- One two-turn Maths conversation used the hosted tutor. The other nine used the textbook fallback. Production deployment and team review are pending.
