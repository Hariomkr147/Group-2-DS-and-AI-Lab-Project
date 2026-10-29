# Data

Scripts that download and prepare the three datasets. Raw files and bulky outputs are not committed; run the scripts to rebuild them.

```bash
python -m venv notes/sandeep/milestone-2/data/.venv
notes/sandeep/milestone-2/data/.venv/Scripts/pip install -r notes/sandeep/milestone-2/data/requirements.txt      # Linux/Mac: notes/sandeep/milestone-2/data/.venv/bin/pip
notes/sandeep/milestone-2/data/.venv/Scripts/python notes/sandeep/milestone-2/data/scripts/download.py            # raw files -> notes/sandeep/milestone-2/data/raw/
notes/sandeep/milestone-2/data/.venv/Scripts/python notes/sandeep/milestone-2/data/scripts/prep_assistments.py
notes/sandeep/milestone-2/data/.venv/Scripts/python notes/sandeep/milestone-2/data/scripts/prep_mathdial.py
notes/sandeep/milestone-2/data/.venv/Scripts/python notes/sandeep/milestone-2/data/scripts/prep_ncert.py
notes/sandeep/milestone-2/data/.venv/Scripts/python notes/sandeep/milestone-2/data/scripts/build_chapter_titles.py
notes/sandeep/milestone-2/data/.venv/Scripts/python notes/sandeep/milestone-2/data/scripts/build_course_packs.py
notes/sandeep/milestone-2/data/.venv/Scripts/python notes/sandeep/milestone-2/data/scripts/build_scenarios.py
notes/sandeep/milestone-2/data/.venv/Scripts/python notes/sandeep/milestone-2/data/scripts/check_data.py          # sanity checks
```

| Dataset | Used for | Output in `notes/sandeep/milestone-2/data/processed/` |
|---|---|---|
| ASSISTments 2009-2010 (corrected) | Train and test the learner model (DKT) | `assistments/`: `train/val/test.jsonl` (one window of up to 200 answers per line), `skill_map.csv`, `stats.json` |
| MathDial | Fine-tune the Socratic model | `mathdial/`: `train/val/test.jsonl` (one tutor reply per line, chat format), `stats.json` |
| NCERT Maths and Science, classes 6-10 | Course pack (study material for search) | `ncert/`: `chunks.jsonl`, `chapters.csv`, `stats.json` |
| Course packs (hand-written) | Concepts, prerequisite links and practice questions for the tutor | `course_packs/` (specs, committed) -> `processed/course_packs/*.json` (built, includes NCERT text, not committed) |
| Test scenarios (hand-written) | Evaluate backtracking, misconception detection and guardrails | `test_scenarios/*.jsonl` (committed): backtracking, misconceptions, guardrails |

Details, choices and limits are in `docs/milestone-2/Milestone2_Report.md`.
