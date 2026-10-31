# Preprocessing (Milestone 2)

Every step that turns the downloaded datasets into the files the models read. Raw downloads and bulky outputs are not committed; the scripts rebuild them.

```bash
python -m venv docs/milestone-2/preprocessing/.venv
docs/milestone-2/preprocessing/.venv/Scripts/pip install -r docs/milestone-2/preprocessing/requirements.txt   # Linux/Mac: .venv/bin/pip
docs/milestone-2/preprocessing/.venv/Scripts/python docs/milestone-2/preprocessing/scripts/run_pipeline.py     # all steps below, in order
```

`run_pipeline.py` accepts `--skip-download` and `--skip-ncert`. Each script can also be run alone.

| # | Script | What it does | Output (`processed/` unless noted) |
|---|---|---|---|
| 1 | `download.py` | Downloads ASSISTments, MathDial (original release), SocraTeach and the NCERT chapter PDFs | `raw/` |
| 2 | `prep_dkt.py` | ASSISTments to DKT arrays: clean, number skills, encode `x = skill + N x correct`, cut to 200, mask, split by student, validation | `dkt/` |
| 3 | `prep_chat.py` | MathDial + SocraTeach to one chat corpus with labels and hybrid train/validation/test splits by problem | `chat/` |
| 4 | `prep_ncert.py` | NCERT PDFs to text chunks tagged with subject, class, chapter, page | `ncert/` |
| 5 | `build_chapter_titles.py` | Adds verified chapter titles | `ncert/chapters.csv` |
| 6 | `build_course_packs.py` | Builds the two course packs from `course_packs/specs.py` | `course_packs/` |
| 7 | `build_scenarios.py` | Writes our labelled test scenarios | `test_scenarios/` (committed) |
| 8 | `eval_misconception.py` | Scores the backend's dynamic misconception detector | `misconception_eval.json` |
| 9 | `make_figures.py` | Draws the report figures | `../figures/` |
| 10 | `check_data.py` | Runs all data checks; exits non-zero on failure | exit code |

Other files:
- `make_validation_splits.py` makes the validation split of the frozen DKT arrays (`../hosted_dataset/splits/dkt_validation.json`).
- `build_presentation.py` builds `../Milestone2_Presentation.pdf`.
- `course_packs/` holds the hand-written concepts, prerequisites and questions; `test_scenarios/` holds the evaluation sets (never used for training).
- `first_version_colab.ipynb` is the first version of the ASSISTments and chat steps. The chat steps in them are superseded by `prep_chat.py` (the MathDial copy they used had lost characters); the DKT arrays they produced are the frozen set in `../hosted_dataset/assistments_dkt/`.

Details, choices, results and limits are in `../Milestone2_Report.md`.
