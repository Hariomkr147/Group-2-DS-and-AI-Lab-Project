# tier a shortlist (2026-11-19)

## Prompts
1. Let's work on skill mapping.
2. Go with the tier-A shortlist.

## Links
- notes/Mrityunjay Chakraborty/Ncert Pack (review sheet, README)

## Tools and packages
- Claude Code (Sonnet 5.5), Python csv module

## What the AI did
- Pulled the 93 tier-A rows (78 concepts) from Mrityunjay's review sheet into backend/models/akt/tier_a_review_shortlist.csv.
- Added a `claude_view` column (keep 44, partial 35, reject 14) and a blank `decision` column for the reviewer.
- concept_skill_map.json is unchanged.

## Notes
- `claude_view` is a quick judgment from concept and skill names, not a review. Fill `decision`, then add approved rows to the map. NCERT concept ids are not in the sample pack yet, so the map needs those ids first.

## Next step (same session)
- Prompt: "go with next step".
- Added backend/scripts/merge_skill_shortlist.py: reads rows marked `keep` in the shortlist, checks skill id against index in skill_map.csv, allows one skill per concept, and updates concept_skill_map.json only with `--write` and no problems.
- Added backend/tests/test_skill_shortlist.py (3 tests, pass). Dry run now: 0 concepts to add (no decisions filled).

## Fill and merge (same session)
- Prompt: "please fill it and then run script".
- Filled `decision`: 44 keep rows minus 11 skipped (ambiguous or a second skill for one concept: Mean/Median, Percent Of vs Percents, trapezoid, cuboid, cylinder); the rest skip. Result: 33 keep.
- Ran the merge script with `--write`: 33 NCERT concept ids added to concept_skill_map.json. Fixed the first test to match.
- Notes: decisions are Claude's, not a subject expert's. The backend does not use C0x-MAT ids yet, so these entries have no effect until an NCERT maths pack uses them. Backend suite shows the same 3 test_akt.py checksum errors (CRLF on Windows checkout).
