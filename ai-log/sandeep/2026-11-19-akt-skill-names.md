# akt skill names (2026-11-19)

## Prompts
1. Explain concept_skill_map.json and skill_map.csv.
2. Add more concept mappings using skill names found in the repo.
3. Copy the skill-name table into backend/models/akt.

## Links
- notes/Mrityunjay Chakraborty/Ncert Pack/skill_vocabulary_2009_with_checkpoint_index.csv

## Tools and packages
- Claude Code (Sonnet 5.5), Python csv module

## What the AI did
- Found no clean new concept mappings for the sample pack, so concept_skill_map.json is unchanged.
- Created backend/models/akt/skill_names.csv (index, original skill id, name, name flag) and checked it against skill_map.csv.

## Notes
- 21 skills have no name. Multiplication, division and fractions have no clean match and use the accuracy fallback.
