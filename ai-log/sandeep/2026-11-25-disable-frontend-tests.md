# disable frontend tests (2026-11-25)

## Prompts
1. Disable frontend tests in CI pipeline.

## Links
- None

## Tools and packages
- Claude Code (Claude Opus 5.5)
- GitHub Actions

## What the AI did
- Edited `.github/workflows/ci.yml`: the frontend job now runs only `npm ci` and `npm run build`.
- Commented out the uv setup, Playwright install and `npm test` steps, and renamed the job to "Frontend build".

## Notes
- To re-enable browser tests, uncomment the three steps in the frontend job.
