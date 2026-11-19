# ncert skill mapping files (2026-11-19)

## Prompts
1. Create the NCERT to ASSISTments skill mapping files (concept list, skill vocabulary, maths candidate review sheet, science unmapped list). <add your original prompt, shortened>
2. Write an AI log per AGENTS.md describing how all these files were created.

## Links
- https://ncert.nic.in/textbook/pdf/ (textbook PDFs behind `passages.csv`)
- ASSISTments 2009 skill builder data: <add link>

## Tools and packages
- <assistant and model>
- <libraries, e.g. pandas, text similarity, embedding model>
- Services: omitted

## What the AI did
- `passages.csv`: 92,366 NCERT textbook passages with source PDF, sha256, heading, content, review flags and embedding.
- `ncert_concept_list.csv`: 932 NCERT concepts (classes 6 to 10, maths and science).
- `skill_vocabulary_2009_with_checkpoint_index.csv`: 123 ASSISTments skills mapped to model checkpoint indexes; 102 named, 21 unnamed.
- `candidate_review_sheet_maths_2009_with_checkpoint_index.csv`: 937 rows for 365 maths concepts, up to 3 automatic text-similarity skill suggestions each (tier A, B or none); 30 rows have no suggestion.
- `science_unmapped.csv`: 567 science concepts marked `unmapped` (all model skills are maths).
- `README.md` and `AGENTS.md`: file descriptions and AI log rules.
- Commands run: <add scripts or commands>

## Notes
- Unreviewed: maths mappings are suggestions only. A subject expert must fill `mapping_type`, `evidence` and `review_status`, and confirm the 30 no-suggestion concepts as unmapped.
- Look up skills by `original_assistments_skill_id`, not name (skills 85 and 163 share a name; 21 have none).
- `checkpoint_skill_index` is not the raw skill id.
- Model probability is evidence of learner state, not a direct mastery measure.
- Science should use a labelled per-concept assessment history, not a model score.
