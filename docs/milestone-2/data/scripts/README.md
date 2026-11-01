# Data scripts (Milestone 2)

Every step (one folder per dataset) that turns the downloaded datasets into the files the models read. Raw downloads and bulky outputs are not committed; the scripts rebuild them.

```bash
python -m venv docs/milestone-2/data/scripts/.venv
docs/milestone-2/data/scripts/.venv/Scripts/pip install -r docs/milestone-2/data/scripts/requirements.txt   # Linux/Mac: .venv/bin/pip
docs/milestone-2/data/scripts/.venv/Scripts/python docs/milestone-2/data/scripts/run_pipeline.py     # all steps below, in order
```

`run_pipeline.py` accepts `--skip-download` and `--skip-ncert`. Each script can also be run alone.

| # | Script | What it does | Output (`processed/` unless noted) |
|---|---|---|---|
| 1 | `download/download.py` | Downloads ASSISTments, MathDial (original release), SocraTeach and the NCERT chapter PDFs | `../raw/` |
| 2 | `assistments/prep_dkt.py` | ASSISTments to DKT arrays: clean, number skills, encode `x = skill + N x correct`, cut to 200, mask, split by student, validation | `assistments/` |
| 3 | `socratic_chat/prep_chat.py` | MathDial + SocraTeach to one chat corpus with labels and hybrid train/validation/test splits by problem | `socratic_chat/` |
| 4 | `ncert/prep_ncert.py` | NCERT PDFs to text chunks tagged with subject, class, chapter, page | `ncert/` |
| 5 | `ncert/build_chapter_titles.py` | Adds verified chapter titles | `ncert/chapters.csv` |
| 6 | `ncert/build_course_packs.py` | Builds the two course packs from `../generated/ncert/specs.py` | `../../presentation/course_packs/` |
| 7 | `test_scenarios/build_scenarios.py` | Writes our labelled test scenarios | `../generated/test_scenarios/` |
| 8 | `test_scenarios/eval_misconception.py` | Scores the backend's dynamic misconception detector | `misconception/misconception_eval.json` |
| 9 | `report/make_figures.py` | Draws the report figures | `../../figures/` |
| 10 | `checks/check_data.py` | Runs all data checks; exits non-zero on failure | exit code |

Other files:
- `assistments/make_validation_splits.py` makes the validation split of the frozen DKT arrays (`../processed/assistments/frozen/dkt_validation.json`).
- `../../presentation/build_presentation.py` builds `../../Milestone2_Presentation.pdf` (run it directly; it is not part of `run_pipeline.py`).
- `../generated/ncert/` holds the AI-written, team-reviewed concepts, prerequisites, questions and chapter titles; `../generated/test_scenarios/` holds the evaluation sets (never used for training).
- `Milestone2_EDA.ipynb` explores every prepared dataset with sample records and plots, and explains each preprocessing step. It reads the prepared files and does not rebuild them; run it with Jupyter from any folder inside `docs/milestone-2/`.
- `preprocess_assistments_and_chat_colab.ipynb` is the first version (Colab notebook, kept for history; it does not run outside Colab) of the ASSISTments and chat steps. The chat steps in them are superseded by `prep_chat.py` (the MathDial copy they used had lost characters); the DKT arrays they produced are the frozen set in `../processed/assistments/frozen/`.

Details, choices, results and limits are in `../../Milestone2_Report.md`.
