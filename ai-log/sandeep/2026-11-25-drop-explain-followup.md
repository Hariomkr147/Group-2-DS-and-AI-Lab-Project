# drop explain followup (2026-11-25)

## Prompts
1. Drop the repetitive "How would you explain that idea in your own words?" sentence.

## Links
- none

## Tools and packages
- Claude Code (Claude Opus 5.5)

## What the AI did
- Changed backend/app/services/socratic.py: explain-mode replies no longer get that follow-up question appended. Other modes still get "What would you try next?" when the reply has no question.

## Notes
- No tests referenced the removed sentence.
