# bare-sum-clarification (2026-11-20)

## Prompts
1. Pasted a chat: "explain 4 x 5" -> class/subject question -> "class 8 maths" -> "I couldn't find a matching NCERT passage."

## Links
- None

## Tools and packages
- Claude Code (Sonnet 5.5), pytest

## What the AI did
- backend/app/services/tutor.py: bare-sum checks now read the resolved query (not the latest message) and accept "explain / show me / teach me" prefixes, so a plain sum no longer asks for a class and no longer dead-ends after the class reply.
- backend/tests/test_ncert.py: added test_explain_sum_then_class_reply_does_not_dead_end.
- Ran the backend tests: 177 passed, 1 skipped.

## Notes
- Not committed.
