# explain not prerequisite (2026-11-26)

## Prompts
1. "no, you only explain" sent the tutor to a prerequisite (Prime Numbers). It should explain the current topic instead.

## Links
- none

## Tools and packages
- Claude Code (Claude Opus 5.5)

## What the AI did
- backend/app/services/socratic.py: the path classifier gets a new "explain" label. "basics" and "deepest" now need an explicit request for earlier topics.
- backend/app/services/tutor.py: _move_through_lesson explains the topic on screen when the label is "explain".
- backend/tests/fake_classifier.py and test_ncert_backtracking.py: new test that "no, you only explain" stays on the topic.
- Ran pytest: 216 passed, 1 failed.

## Notes
- The one failure (test_ncert.py::test_hosted_hint_leaves_the_student_a_question) comes from the earlier uncommitted socratic.py change and passes on HEAD.
