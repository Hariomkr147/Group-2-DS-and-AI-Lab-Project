# AGENTS.md

Instructions for any AI assistant (Claude Code or similar) working in this repo.

## Log every AI session

Each teammate keeps their own AI usage log, so logs never conflict.

**Location:** `ai-log/<person>/YYYY-MM-DD-<topic>.md`

- `<person>` matches the folder names under `notes/` (for example `sandeep`, `hariom kumar`, `hariom pandey`). Create one if you are new, in lowercase.
- `YYYY-MM-DD` is the session date.
- `<topic>` is 2-4 lowercase words joined by hyphens, for example `supabase-setup`.
- One file per session. Do not edit another person's folder.

**Template:**

```markdown
# <topic> (YYYY-MM-DD)

## Prompts
1. <the user's prompt, shortened if long>

## Links
- <urls or docs used>

## Tools and packages
- <assistant and model, libraries, services>

## What the AI did
- <files created or changed, commands run>

## Notes
- <follow-ups, risks>
```

## Rules

- Never write passwords, API keys, tokens or connection strings into the log. Write "omitted" instead.
- Keep `.env` files out of git.
- Keep logs short and plain.
- At the end of a session, create the log file for the person who ran it.
