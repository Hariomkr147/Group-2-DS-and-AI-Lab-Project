# ncert akt skill (2026-11-25)

## Prompts
1. Incorporate AKT for NCERT: skill level per class and subject, shown on the right side on a 1 to 10 scale.
2. Can AKT read skill from chat? Use the existing resolvers; then: no regex, use the tutor's reply to decide if the answer was right.
3. Judge in the background so the learner gets no extra latency.

## Links
- None

## Tools and packages
- Claude Code (Claude Opus 5.5)
- FastAPI BackgroundTasks, SQLAlchemy, torch (AKT), React

## What the AI did
- `socratic.judge_attempt`: model labels the tutor's reply as correct / incorrect / none (MESSAGE_CLASSIFIER_PROVIDER).
- `tutor._ncert_reply`: review turns (learner sent an answer or working) are queued; `tutor.judge_and_record` judges and records them after the reply is sent (`routers/sessions.py`, background task).
- `akt.py`: `skill_of` maps an NCERT chapter concept (`7-maths-gegp1-8`) to the skill its mapped graph concepts share; skill map checksum ignores CRLF line endings (Windows checkout).
- `learner_model.estimate` / `skill_level`; new `GET /learners/{id}/skill?grade=&subject=` returns level 1 to 10 = round(1 + 9p), answer-weighted over answered chapters.
- Frontend: "Your skill level" card in the side panel for textbook chat; refreshes again 5 s after a reply.
- Tests: `tests/test_ncert_skill.py`, one new case in `tests/test_akt.py`. Full suite: 221 passed, 1 failed (`test_hosted_hint_leaves_the_student_a_question`, from the staged drop-explain-followup change, not this work).

- Fix after a manual test: attempts like "a+b=45; (a-5)(b-5)=124" were routed as a new exercise (explain mode), so
  they were never judged. Now every follow-up turn on an open topic is queued; the judge returns none when nothing was answered.

## Notes
- AKT only covers mapped maths chapters (ASSISTments skills); science and unmapped chapters use smoothed accuracy. The card says which was used.
- The verdict is the model's reading of the tutor reply, not a checked answer key.
- Knowledge state is not stored separately: AKT is recomputed from the answers table on each read.
- Frontend build was not run (local node_modules is incomplete).
