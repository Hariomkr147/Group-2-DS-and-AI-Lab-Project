# tutor conversation (2026-11-20)

## Prompts
1. Rename `docs/milestone 4` to `milestone-4`; fix signature image links in the M4 work log.
2. Tutor repeats the same question/hint and gives a canned menu after "yes"; wants a more conversational tutor, Qwen allowed for replies.

## Links
- none

## Tools and packages
- Claude Code (Sonnet 5.5), pytest

## What the AI did
- Fixed signature file extensions in `docs/milestone-4/Work_Contribution_Log.md`; renamed the folder.
- `backend/app/services/conversation.py`: "different question" phrases, repeat-complaint detector.
- `backend/app/services/socratic.py`: `chat()` asks the Qwen model for a short conversational reply (falls back if unavailable or it leaks the answer).
- `backend/app/services/tutor.py`: new hint each time, apology + different/related question on a repeat complaint, friendlier end-of-topic message, model-written fallback for unrecognised messages.
- Added tests in `backend/tests/`.

## Notes
- The hosted Qwen was not called in tests (mocked). Try it live with `SOCRATIC_PROVIDER=qwen_finetuned`.
- The demo pack has one Percentages question, so new questions need more pack content.
