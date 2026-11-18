# NCERT to ASSISTments skill mapping: files

**Status: unreviewed.** Maths rows are automatic text-similarity suggestions, not approved mappings. `mapping_type` and `review_status` are blank until a subject expert fills them.

## 1. candidate_review_sheet_maths_2009_with_checkpoint_index.csv
The main mapping file. 365 NCERT maths concepts (classes 6 to 10), 937 rows.
- Up to 3 suggested ASSISTments skills per concept (`rank` 1 to 3).
- 30 rows are concepts with no suggestion (blank skill id, `suggestion_tier` = none). The reviewer should confirm these as unmapped.
- Key columns:
  - `ncert_concept_id`: concept identifier.
  - `original_assistments_skill_id`: the skill's id in the ASSISTments data.
  - `checkpoint_skill_index`: the skill's index in the trained model (filled in; not the same as the raw id).
  - `suggestion_tier`: A means every word of the skill name appears in the concept text. B means only some do (weak). none means no overlap.
  - `similarity_score`: strength of the text match.
  - `mapping_type` (exact, partial or unmapped), `evidence` and `review_status`: for the reviewer to complete.
  - Context columns: class, chapter, concept, learning_objective, skill_name, skill_name_source, skill_name_flag, skill_n_log_rows.

## 2. skill_vocabulary_2009_with_checkpoint_index.csv
Lookup table for the 123 skills the trained model knows.
- 102 skills have a name and 21 have none (they cannot be matched yet).
- Key columns:
  - `original_assistments_skill_id` and `checkpoint_skill_index`: the two ids for each skill.
  - `skill_name`: the skill's name.
  - `skill_name_source`: single_id_row means the name was read directly. inferred_first_position_of_joined_id means it was inferred from combined ids. none_in_this_file means no name is available.
  - `name_flag`: no_name, single_word, duplicate_name_across_ids (skills 85 and 163 share a name) or standards_code_not_a_name.
  - `n_log_rows`, `n_distinct_problems`: how much data the skill has.
  - `n_concepts_suggested`, `n_concepts_tierA`: how many NCERT concepts point to it.

## 3. science_unmapped.csv
All 567 NCERT science concepts (classes 6 to 10), each marked `unmapped` because the model's 123 skills are all maths. These concepts should use a clearly labelled per-concept assessment history, not a model score.

## Notes
- Always look up skills by `original_assistments_skill_id`, not by name.
- The model's predicted probability of a correct answer is evidence about a learner's state, not a direct measure of mastery.
