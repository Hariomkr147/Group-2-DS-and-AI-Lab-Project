"""Copy the real prompts of Claude Code sessions into ai-log/<person>/<milestone>/YYYY-MM-DD.md.

The prompts come word for word from the session transcript that Claude Code saves under
~/.claude/projects/<project>/<session>.jsonl, in the order they were sent (every turn,
including follow-ups and interruptions). The AI does not write or summarise them.

    python ai-log/export_prompts.py --list                               # recent sessions
    python ai-log/export_prompts.py sandeep milestone-5                  # latest session
    python ai-log/export_prompts.py sandeep milestone-5 --session 158ebd09
    python ai-log/export_prompts.py sandeep milestone-5 --since 2026-11-25
    python ai-log/export_prompts.py sandeep milestone-4 --since 2026-11-06 --until 2026-11-24
    python ai-log/export_prompts.py sandeep milestone-5 --print          # preview only, write nothing

There is one file per day. Each session is a section in it, headed by the title Claude Code gave
the session. Running it again for a session rewrites only that section, with the newer turns,
and keeps your Result line.
Read the file before committing: anything that looks like a key or password is replaced by
[omitted], but check by eye too.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LOG_DIR = Path(__file__).resolve().parent

SECRETS = [
    re.compile(r"\b(?:sk|pk|rk)-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bhf_[A-Za-z0-9]{20,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}"),
    re.compile(r"\bsb_(?:publishable|secret)_[A-Za-z0-9_-]{10,}"),                 # Supabase keys
    # .env lines such as SUPABASE_KEY=..., QWEN_API_KEY=..., DATABASE_URL=...
    re.compile(r"\b([A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASS|DSN|DATABASE_URL|SUPABASE_URL)[A-Z0-9_]*)"
               r"(\s*=\s*)(?!\d+\b)\S+"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),          # JWTs
    re.compile(r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://\S+", re.I),
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password|passwd)\b(\s*[:=]\s*)\S+"),
]


def transcripts_dir() -> Path:
    root = Path.home() / ".claude" / "projects"
    want = re.sub(r"[^A-Za-z0-9]", "-", str(REPO)).lower()
    for d in root.iterdir() if root.exists() else []:
        if d.is_dir() and d.name.lower() == want:
            return d
    sys.exit(f"No Claude Code transcripts found for this repo under {root}")


def redact(text: str) -> str:
    for pattern in SECRETS:
        text = pattern.sub(lambda m: (m.group(1) + m.group(2) + "[omitted]") if pattern.groups == 2 else "[omitted]", text)
    return text


def clean(text: str) -> str:
    """The words the person typed: drop text the tool adds around them, keep a marker for attachments."""
    text = re.sub(r"<system-reminder>.*?</system-reminder>", "", text, flags=re.S)
    text = re.sub(r"<ide_selection>.*?</ide_selection>", "[editor selection attached]", text, flags=re.S)
    text = re.sub(r"<ide_opened_file>.*?</ide_opened_file>", "", text, flags=re.S)
    command = re.search(r"<command-name>(.*?)</command-name>", text, flags=re.S)
    if command:
        args = re.search(r"<command-args>(.*?)</command-args>", text, flags=re.S)
        text = f"{command.group(1).strip()} {args.group(1).strip() if args else ''}".strip()
    if re.match(r"\s*<(?:local-command|command-message|bash-stdout|bash-stderr|task-notification)", text):
        return ""
    return text.strip()


def read_session(path: Path) -> dict:
    prompts, models, files, first_time, title = [], set(), [], None, ""
    for line in path.open(encoding="utf-8"):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if entry.get("isSidechain") or entry.get("isMeta") or entry.get("isCompactSummary"):
            continue
        if entry.get("type") == "ai-title" and entry.get("aiTitle"):
            title = entry["aiTitle"]
        message = entry.get("message") or {}
        content = message.get("content")
        if entry.get("type") == "user":
            parts = [{"type": "text", "text": content}] if isinstance(content, str) else (content or [])
            if any(p.get("type") == "tool_result" for p in parts):
                continue                                  # tool output, not something the person typed
            text = "\n".join(clean(p.get("text", "")) for p in parts if p.get("type") == "text").strip()
            images = sum(p.get("type") == "image" for p in parts)
            text = (text + ("\n" if text else "") + "[image attached]" * min(images, 1)).strip()
            if text:
                prompts.append(redact(text))
                first_time = first_time or entry.get("timestamp")
        elif entry.get("type") == "assistant":
            if message.get("model") and not message["model"].startswith("<"):
                models.add(message["model"])
            for part in content if isinstance(content, list) else []:
                if part.get("type") == "tool_use" and part.get("name") in ("Edit", "Write", "NotebookEdit"):
                    target = (part.get("input") or {}).get("file_path") or (part.get("input") or {}).get("notebook_path")
                    if target:
                        try:
                            target = Path(target).resolve().relative_to(REPO).as_posix()
                        except ValueError:
                            continue                      # outside the repo (memory, scratch files)
                        if target not in files:
                            files.append(target)
    when = (datetime.fromisoformat(first_time.replace("Z", "+00:00")).astimezone()
            if first_time else datetime.fromtimestamp(path.stat().st_mtime))
    return {"id": path.stem, "date": when.strftime("%Y-%m-%d"), "time": when.strftime("%H:%M"), "prompts": prompts,
            "models": sorted(models), "files": files, "title": title}


RESULT = re.compile(r"(?m)^Result \(one line, by the person\):.*$")


def render(s: dict) -> str:
    lines = [f"## {s['time']} {s['title'] or 'Untitled session'}", "",
             f"Claude Code ({', '.join(s['models']) or 'model unknown'}) · session {s['id'][:8]}",
             "", "### Prompts (verbatim, in order)", ""]
    for n, prompt in enumerate(s["prompts"], 1):
        body = prompt.splitlines() or [""]
        lines.append(f"{n}. > {body[0]}" if len(body) == 1 else f"{n}.")
        if len(body) > 1:
            lines += ["   > " + row if row else "   >" for row in body]
    lines += ["", "### Files the AI edited (Edit/Write tool calls; shell edits are not listed)", ""]
    lines += [f"- {f}" for f in s["files"]] or ["- none"]
    lines += ["", "Result (one line, by the person): "]
    return "\n".join(lines) + "\n"


def save(person: str, milestone: str, s: dict) -> Path:
    """Put the session's section into its day file, replacing an older copy of the same session."""
    folder = LOG_DIR / person.lower() / milestone.lower()
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / f"{s['date']}.md"
    text = out.read_text(encoding="utf-8") if out.exists() else ""
    sections = [b for b in re.split(r"(?m)^(?=## )", text) if b.startswith("## ")]
    entry = render(s)
    tag = f"· session {s['id'][:8]}"
    old = next((b for b in sections if tag in b), None)
    if old:
        kept = RESULT.search(old)
        if kept:                                          # keep what the person already wrote
            entry = RESULT.sub(lambda _: kept.group(0), entry)
        sections.remove(old)
    sections = sorted([*sections, entry], key=lambda b: b.split("\n", 1)[0])   # "## HH:MM title": by start time
    out.write_text(f"# AI usage: {s['date']}\n\n" + "\n".join(b.rstrip("\n") + "\n" for b in sections), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("person", nargs="?", help="your folder name under ai-log/, e.g. sandeep")
    ap.add_argument("milestone", nargs="?", help="milestone folder, e.g. milestone-5")
    which = ap.add_mutually_exclusive_group()
    which.add_argument("--session", help="session id or its first characters (default: latest)")
    which.add_argument("--since", help="every session that started on or after this date (YYYY-MM-DD)")
    ap.add_argument("--until", help="with --since: last date to include (YYYY-MM-DD)")
    ap.add_argument("--list", action="store_true", help="list recent sessions")
    ap.add_argument("--print", action="store_true", help="print the files instead of saving them")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    paths = sorted(transcripts_dir().glob("*.jsonl"), key=os.path.getmtime, reverse=True)
    if args.list:
        for path in paths[:20]:
            s = read_session(path)
            print(f"{s['id'][:8]}  {s['date']}  {len(s['prompts']):>3} prompts  {s['title'][:60]}")
        return
    if not args.print and not (args.person and args.milestone):
        ap.error("give your name and the milestone, e.g. sandeep milestone-5")
    if args.since:
        chosen = [s for s in map(read_session, paths)
                  if s["date"] >= args.since and (not args.until or s["date"] <= args.until)]
    else:
        matches = paths[:1] if not args.session else [p for p in paths if p.stem.startswith(args.session)]
        if len(matches) != 1:
            sys.exit(f"{'No' if not matches else 'More than one'} session matches '{args.session}'. Use --list.")
        chosen = [read_session(matches[0])]
    chosen = sorted((s for s in chosen if s["prompts"]), key=lambda s: (s["date"], s["time"]))
    if not chosen:
        sys.exit("No sessions with prompts found.")
    for s in chosen:
        if args.print:
            print(render(s))
        else:
            print(f"{len(s['prompts']):>3} prompts -> {save(args.person, args.milestone, s).relative_to(REPO).as_posix()}")


if __name__ == "__main__":
    main()
