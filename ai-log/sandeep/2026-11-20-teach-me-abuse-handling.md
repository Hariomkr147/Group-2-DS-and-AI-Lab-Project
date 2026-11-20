# teach-me-abuse-handling (2026-11-20)

## Prompts
1. Pasted NCERT tutor chat: "teach me a topic" got "I couldn't find a matching passage". Asked why.
2. "make change" (fix it).
3. "you idiot" got the same reply. Asked to handle abusive language.
4. Asked whether regex is used and whether the Qwen model should classify instead.
5. "build it that way, try qwen first" (regex first, Qwen only for messages retrieval cannot place).
6. Asked for this log.
7. "ok, let's get into topic" still failed. Asked why regex was used; said not to use regex (keep the code, just don't call it).
8. "on pressing enter key, please click 'Send' button".

## Links
- none

## Tools and packages
- Claude Code (Sonnet 5.5)
- Existing: fine-tuned Qwen (`qwen_finetuned` provider), pytest

## What the AI did
- backend/app/services/tutor.py: added `_START_LESSON` and `_start_first_topic` so a generic "teach me a topic" starts the chapter's first topic. Added `_ABUSE_REPLY`, an early abuse check in `handle_message`, and a model check in `_handle_ncert` when no passage is found.
- backend/app/services/guardrails.py: added `_ABUSE` word list and `is_abusive`.
- backend/app/services/socratic.py: added `classify_message` (Qwen returns one label: abusive, start_lesson, off_topic or topic_question; anything else is rejected). `MESSAGE_CLASSIFIER_PROVIDER` picks the provider, `off` disables it.
- Widened `_START_LESSON`, then switched both regex checks off (`_START_LESSON` and `guardrails.is_abusive` stay in the code, unused). The Qwen label now decides in `_handle_ncert`; with no label and no active topic, the first topic starts. Added a `log` and an info line for the label.
- frontend/src/components/Chat.jsx: Enter in the text box submits the form (like Send); Shift+Enter adds a new line; ignored during IME composition. Updated the hint text.
- Checked the regexes and the label parsing with stubbed model replies. Full test suite: 152 passed, 1 skipped.

## Notes
- Not tested against the real hosted Qwen or through the running app. If Qwen does not return a single label, try `MESSAGE_CLASSIFIER_PROVIDER=gemini`.
- The abuse word list is fixed and misses misspellings and other languages; the model check covers some of that.
- No unit tests were added for the new paths, and the Enter key change was not run in the browser or the Playwright tests.
- With Qwen down, an insult sent when no topic is active would start the first topic, since the word list is off.
