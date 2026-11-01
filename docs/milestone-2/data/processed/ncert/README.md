# processed/ncert

Text of the NCERT books in `raw/ncert`, made by `prep_ncert.py`; titles added by `build_chapter_titles.py`.

| File | What it holds |
|---|---|
| `chunks.jsonl` | Page text split into chunks; one per line with `subject`, `class`, `chapter`, `page`, `source`, `text`. Not committed (NCERT text). |
| `chapters.csv` | One row per chapter: subject, class, chapter, pages, file, title, `title_status` (`verified` or `needs_review`). |
| `stats.json` | Pages read, pages kept, chunks per book. |
