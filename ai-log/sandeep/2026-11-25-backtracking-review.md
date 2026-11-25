# backtracking review (2026-11-25)

## Prompts
1. Let's review backtracking, advance, and current functionality
2. Fix all the observed issues
3. ncert_path - use the socratic model instead of regex
4. Why MAX_DEPTH = 3? Remove the depth limit; does it step one level at a time?
5. Add multi-step jumps: straight to the deepest prerequisite, and straight back to the main topic

## Links
- none

## Tools and packages
- Claude Code (Opus 5.5), pytest

## What the AI did
- Reviewed tutor.py, ncert_path.py, ncert.py, ncert_graph.py, conversation.py and the backtracking tests.
- Fixed in tutor.py: picking a topic now clears the detour stack; "got it" in a detour resumes; the help count
  resets on a new topic and on any non-help message; step back and resume use the topic's own passage
  (new `topic_passage_id`), not the chunk a follow-up found; moving on skips headings with no passage and no
  longer fails when the corpus is down; "back to the main topic" with no detour says we are already on it;
  log lines tell resume and next-topic apart.
- ncert_path.new_ones also skips other chunks of a topic already on the stack.
- ncert.py: graph prerequisites can no longer be a later chapter of the same book.
- Replaced the ncert_path regexes (resume, understood, basics, prerequisites) with a model call,
  socratic.classify_path; tests use a fake (tests/fake_classifier.py, conftest.py).
- Added regression tests in tests/test_ncert_backtracking.py. Full suite: 193 passed, 1 skipped.
- Removed the detour depth limit (MAX_DEPTH, can_step_back); the depth-limit test now checks a 4-level detour
  and the climb back. MAX_DEPTH = 3 had no recorded reason.
- Multi-step jumps: two new classify_path labels, main_topic (empty the stack, back to the first topic) and
  deepest (follow the strongest prerequisite to the most basic topic; topics passed go on the stack).
  "back to the previous topic" now climbs one level. Replies and "where are we?" name both ways back.
  6 new tests; full suite 199 passed, 1 skipped.

## Notes
- classify_path adds one short model call per message (up to 120 characters) while a topic is open.
- The fine-tuned Qwen classifier was not trained on these four labels; check it on real messages.
- With the model off, learners cannot ask to step back or resume; the automatic step back after two help
  requests still works.
