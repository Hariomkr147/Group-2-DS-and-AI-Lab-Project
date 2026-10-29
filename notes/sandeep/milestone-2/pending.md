# Milestone 2: pending items

Due 29 October 2026. Only open items are listed; finished work is in the git history.

## Do first
- [ ] **Re-upload the Drive folder.** The local `notes/sandeep/milestone-2/hosted_dataset/` (67 MB) now holds only Hariom Pandey's data plus our NCERT metadata, pack specs, scenarios and validation splits. The Drive folder still has the old layout (it also has `version_a_assistments/` and `mathdial/`, and `version_b_*` names). Replace its contents with the local folder: `assistments_dkt/`, `socratic_chat/`, `splits/`, `ncert_metadata/`, `course_pack_specs/`, `test_scenarios/` plus the README. Keep the same folder link and sharing ("Anyone with the link").

## Needs the team
- [ ] **Hariom Pandey:** fill the placeholder in his DKT report ("exact file name and download link"); confirm he is fine with his files (his write-up says "frozen" and "not re-shared") being in the repo and the Drive folder; confirm the Drive link in reference [4] is his source file.
- [ ] **Hariom Kumar and Mrityunjay:** confirm or edit their work-log rows (written as assigned responsibilities) and confirm they reviewed the final report before the signatures stand.
- [ ] A second member reviews scenario labels (`reviewed_by` is empty) and the prerequisite links.

## Known limits, deliberately left (all stated in the report)
- Class 8 maths still uses the older NCERT book; the new one needs ncert.nic.in (unreachable on submission day).
- Moved to Milestone 3: IITM pack, guardrail methods comparison, controller and misconception baselines, Class 3-5 content.
- Model choice: report keeps Qwen3-4B + LoRA (Milestone 1) as the target; Hariom Pandey's write-up used Qwen2.5-1.5B.
- The chat corpus has no answer-leak flag and no validation for SocraTeach (no problem text to group by).
