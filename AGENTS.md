# AGENTS.md

Instructions for any AI assistant (Claude Code or similar) working in this repo.

## AI usage log

The log records the prompts we actually typed, word for word and in order, across every turn of a
conversation. Do not summarise or reword them. The AI does not write the log.

**Location:** `ai-log/<person>/<milestone>/YYYY-MM-DD.md`, one file per day with a section per session.
`<person>` is lowercase (for example `sandeep`), `<milestone>` is like `milestone-5`.
Do not edit another person's folder.

**Claude Code sessions:** run the exporter. It copies the prompts from the transcript that Claude Code
saves on your machine, and heads each section with the title Claude Code gave the session:

```
python ai-log/export_prompts.py --list                                  # find the session
python ai-log/export_prompts.py <person> <milestone>                    # latest session
python ai-log/export_prompts.py <person> <milestone> --session <id>
python ai-log/export_prompts.py <person> <milestone> --since YYYY-MM-DD [--until YYYY-MM-DD]
```

Running it again for a session rewrites only its section with the newer turns and keeps your Result line.

**Other tools (ChatGPT, Gemini, Copilot chat):** paste the prompts word for word in the same format,
or add the tool's share link.

**File format** (what the exporter writes):

```markdown
# AI usage: YYYY-MM-DD

## HH:MM <session title>

<tool> (<model>) · session <id>

### Prompts (verbatim, in order)

1. > first prompt
2. > follow-up
3. > [Request interrupted by user]

### Files the AI edited (Edit/Write tool calls; shell edits are not listed)

- path/to/file

Result (one line, by the person): <what you kept, changed or threw away>

## HH:MM <next session title>
...
```

## Rules for the AI assistant

- Do not create, edit or rewrite log entries on your own, and never write prompts from memory.
  If the person asks for a log, run `ai-log/export_prompts.py` and show them the result.
- The person reads the entry and writes the Result line themselves before committing.
- Never put passwords, API keys, tokens or connection strings in the log. The exporter replaces
  likely secrets with `[omitted]`, but check by eye.
- Keep `.env` files out of git.
