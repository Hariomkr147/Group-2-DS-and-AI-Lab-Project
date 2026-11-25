# uvicorn reload config (2026-11-25)

## Prompts
1. Can I run the backend API in reload mode in launch.json?
2. Yes, add it to launch.json.

## Links
- None

## Tools and packages
- Claude Code (Claude Opus 5.5)
- uvicorn, debugpy (VS Code)

## What the AI did
- Added a "Backend: API (uvicorn, reload)" config to `.vscode/launch.json` with `--reload --reload-dir app` and `subProcess: true`.

## Notes
- The original non-reload config and the full-stack compound are unchanged.
