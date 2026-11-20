# where-are-we-fix (2026-11-20)

## Prompts
1. Screenshot of the NCERT tutor chat: "where are we on now?" and "what topic are we on now?" both got "I couldn't find a matching passage". Asked to fix it.

## Links
- none

## Tools and packages
- Claude Code (Sonnet 5.5)

## What the AI did
- backend/app/services/tutor.py: added `_WHERE_NOW` and `_where_are_we`; `_converse_ncert` now answers "where are we" style questions from session state (current topic heading, class, subject, chapter).
- backend/app/services/ncert.py: added `chapter_title(scope)`.
- Checked the regex on sample phrases with a one-line Python command.

## Notes
- Not tested through the running app or the full test suite.
- The non-NCERT (course pack) path is unchanged.
