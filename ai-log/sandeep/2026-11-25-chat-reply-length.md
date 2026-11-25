# chat reply length (2026-11-25)

## Prompts
1. "1 to 3 sentences is too restrictive" (about CHAT_SYSTEM and TALK_SYSTEM in socratic.py)

## Links
- none

## Tools and packages
- Claude Code (Opus 5.5)

## What the AI did
- backend/app/services/socratic.py: replaced the "one to three short sentences" rule in CHAT_SYSTEM and TALK_SYSTEM with "a line or two for small talk, a short paragraph when explaining".
- Raised the chat token budget from 256 to 400 and the reply length cap from 700 to 1400 characters, so longer replies are not cut or rejected.

## Notes
- The self-hosted model still caps output at 192 tokens (llm.py MAX_NEW_TOKENS), so its replies stay shorter.
