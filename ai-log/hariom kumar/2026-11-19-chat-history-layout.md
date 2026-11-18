# Chat history and layout (2026-11-19)

## Prompts
1. Improve the frontend typography and accessibility and let students reopen previous chats saved in PostgreSQL.

## Links
- Local UI A11y and UI/UX Pro Max skill guides.

## Tools and packages
- Codex (GPT-6), React, FastAPI, SQLAlchemy, pytest, Playwright, Vite.

## What the AI did
- Added a paginated history query, a previous-chats dialog, and the ability to resume a saved lesson or start a new chat.
- Adjusted heading sizes, conversation spacing and mobile navigation. Added API and browser checks.
- Ran the production build, 86 backend tests and four browser tests.

## Notes
- People using the same project account share history. Browser checks used a temporary database. Production deployment and a manual screen-reader check remain pending.
