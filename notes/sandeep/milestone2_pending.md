# Milestone 2: pending items

Due 29 October 2026. Checked against the M2 requirements.

## Must do
- [ ] **Host the processed dataset (e.g. Kaggle) and add the link to the report.** Include `train/val/test.jsonl`, `skill_map.csv`, `stats.json`, scenarios and course packs. Leave out NCERT text (licence). The `.jsonl` files are git-ignored, so they exist only locally.
- [ ] **EDA and preprocessing notebook.** None of ours exists (only scripts in `data/scripts/`). Put it in `docs/milestone-2/` and include the visualisations.
- [ ] **Sign-off:** all 4 members sign and date the report and the work log.
- [ ] **Work log:** Hariom Kumar and Mrityunjay rows are blank.

## Report additions
- [ ] Add a "why we did it" reason for each preprocessing step.
- [ ] Add the folder tree of the processed dataset.
- [ ] Add sample records (ASSISTments row, MathDial example per label, NCERT chunk, a course-pack concept).
- [ ] Add per-class detail: skill list for ASSISTments, MathDial label counts.
- [ ] Embed the three figures from `docs/milestone-2/figures/`.

## Presentation
- [ ] Rebuild `Milestone2_Presentation.pdf` (via `build_presentation.py`) after the report changes: add Hariom Pandey's data, references, sample data and hosted link.

## Open decisions
- [ ] Pick one ASSISTments version: ours (149 skills, train/val/test) or Hariom Pandey's (82 skills, train/test only). Update the report to match.
- [ ] Hariom Pandey's DKT report has an unfilled placeholder ("file name and download link").
- [ ] Reference 1 is the ASSISTments **2011** page but we use 2009-2010: confirm or replace.
- [ ] Reference 3 (Google Drive file): confirm what it is.
- [ ] Optionally add MathDial and ASSISTments (Feng et al. 2009) paper citations.

## Housekeeping
- [ ] Nothing is committed yet: report/log edits, `notes/hariom pandey/`, this file.
- [ ] Second member to review scenario labels (`reviewed_by` is empty) and prerequisite links.
