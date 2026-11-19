# chat conversation layer (2026-11-19)

## Prompts
1. Test the real-time (streaming) backend and report issues.
2. Test the session messages endpoint with different questions; the replies feel too restrictive.
3. Take the decisions and give a good user experience.
4. Can the Socratic model make the decisions instead of deterministic rules? (open question)

## Links
- None.

## Tools and packages
- Claude Code (Claude Sonnet 5.5), pytest, curl.

## What the AI did
- Probed `/llm/stream` and `/sessions/{id}/messages` on the running server (about 55 messages, new sessions under `probe-learner`).
- Added `backend/app/services/conversation.py` (greetings, thanks, yes/next/harder/easier, "I don't know", examples, number words).
- Changed `backend/app/services/tutor.py`: conversation layer before the classifier, "what is X?" explains then asks, more answer formats ("ten", "it is 10", "is 10 correct?"), one-line steps acknowledged, helpful fallbacks instead of "Are you answering...?", topic menu on off-topic, NCERT greetings and `x = 2` style answers, `seen` kept after DONE.
- Changed `backend/app/services/socratic.py` (three rotating guide prompts) and `backend/app/services/llm.py` (missing openai/anthropic package gives 503, not 500).
- Added `backend/tests/test_conversation.py`. Full suite: 126 passed, 3 errors in `test_akt.py` (skill map checksum mismatch from the staged `concept_skill_map.json` edit, not from this work).

## Notes
- The classifier's intent head is below its 0.5 threshold on almost every short message; retraining or recalibrating it is still open.
- Still weak: "what is photosynthesis" during a question gets the stock hint (classifier), and Gemini can stream no text with a small `max_tokens`.
- Probe sessions left in the shared database: `df68c442...`, `0ceeb10d...`, `c88d12b4...`, `4d3b1c81...`, `fd570632...`, `76660ed3...`, `b65a05f8...`.
- Nothing committed.
