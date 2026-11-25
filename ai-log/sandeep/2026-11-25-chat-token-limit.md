# chat token limit (2026-11-25)

## Prompts
1. Check the 400 token limit in socratic.chat. Can we increase it?
2. Yes, make it env-configurable with 800 default.

## Links
- None

## Tools and packages
- Claude Code (Opus 5.5)

## What the AI did
- backend/app/services/socratic.py: chat() reads SOCRATIC_CHAT_MAX_TOKENS (default 800, minimum 64); the length check is now max_tokens * 4 characters instead of a fixed 1400.
- backend/.env.example: documented SOCRATIC_CHAT_MAX_TOKENS.

## Notes
- Gemini 3 Flash counts thinking tokens in max_output_tokens, so a low limit can cut replies short.
- qwen_finetuned still caps at 1096 tokens (MAX_NEW_TOKENS in llm.py).
- The prompt still asks for short replies; a higher limit only gives room to finish.
