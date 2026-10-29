# Milestone 2: pending items

Due 29 October 2026. Checked against the M2 requirements and the review feedback.

## Done
- [x] EDA and preprocessing notebook: `docs/milestone-2/Milestone2_EDA.ipynb` (outputs saved, 6 plots, reasons for each step).
- [x] Report rewritten: reasons per step, sample records, per-class counts, figures embedded, folder tree, version A/B comparison, status against the M1 plan, references fixed.
- [x] Presentation rebuilt (14 slides): version B, sample records, folders and splits, M1 status, AUC source, sign-off.
- [x] Scenario fixes: careless vs hint cases now differ by `mastery`; two guardrail labels corrected (47 items, 161 scenarios total); a check enforces "same inputs, same label".
- [x] Hints that gave the answer away rewritten; new check fails if a hint contains its answer (26 checks pass).
- [x] Level 1 concept renamed and the chapter mismatch documented; mixed NCERT editions, 17 hand-typed answers, "15 chapters used / 20 verified" corrected in the report.
- [x] Dedup wording: the `order_id` dedup removes 0 rows in our corrected file (version B keeps multi-skill steps).
- [x] Hosted dataset folder staged: `notes/sandeep/milestone-2/hosted_dataset/` (113 MB, README and Kaggle metadata included).
- [x] Root README status line updated.

## Needs you or the team (cannot be done from here)
- [ ] **Upload `hosted_dataset/` to Kaggle** (set your username in `dataset-metadata.json`) and paste the link at the top of the report and on slide 10. Report text says "link to be added".
- [ ] **Hariom Pandey:** fill the placeholder in his DKT report ("exact file name and download link"); confirm the "frozen / not re-shared" wording is OK now that the files are in the repo and in the hosted folder; confirm the Drive link in reference [4] is his source file.
- [ ] **Hariom Pandey / team:** decide model (Qwen2.5-1.5B in his write-up vs Qwen3-4B in M1 and README); avoid training on his corpus and validating on version A's validation split.
- [ ] **Hariom Kumar and Mrityunjay:** confirm or edit their rows in the work log (they are written as responsibilities, not finished work), and confirm they reviewed the final report before the signatures stand.
- [ ] Confirm reference [1] (2011 ASSISTments page) is intended; it is not our dataset.
- [ ] Second member reviews scenario labels (`reviewed_by` is empty) and prerequisite links.
- [ ] Class 8 maths still uses the older NCERT book; switching to the new book needs ncert.nic.in (unreachable today).
- [ ] Not done by choice (moved to M3 in the report): IITM pack, guardrail methods comparison, controller and misconception baselines, Class 3-5 content.

## Housekeeping
- [ ] Nothing from this round is committed yet.
- [ ] Moved `.venv` inside `data/` is broken; recreate it from `data/README.md` if needed (git-ignored).
