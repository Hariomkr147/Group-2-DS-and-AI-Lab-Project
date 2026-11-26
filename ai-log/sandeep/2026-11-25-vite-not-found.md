# vite-not-found (2026-11-25)

## Prompts
1. `npm run dev` in frontend fails with "'vite' is not recognized".

## Links
- none

## Tools and packages
- Claude Code (Opus 5.5), npm

## What the AI did
- Found `frontend/node_modules` present but incomplete (no `vite` binary).
- Ran `npm install` in `frontend/` (added 62 packages).

## Notes
- npm audit reports 2 vulnerabilities; did not run `npm audit fix --force` since it may bump major versions.
