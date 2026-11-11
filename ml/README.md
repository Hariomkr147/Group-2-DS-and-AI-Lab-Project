# ML

Model and retrieval code that the tutor depends on. The backend imports from here; it does not hold model logic itself.

## Folders

| Folder | Purpose |
|---|---|
| `rag/` | Embeddings, retrieval over NCERT chunks, retrieval evaluation |
| `kt/` | Knowledge tracing (DKT, AKT) training and inference |

## Notes

- Data preparation and the NCERT pipeline stay in `Ncert work/` for now. Code moves here once it is used by the backend.
- Do not commit model weights or keys. Record how to rebuild them instead.
