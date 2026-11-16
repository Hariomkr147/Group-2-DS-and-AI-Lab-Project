r"""Can a model find the first wrong step in a learner's working?

The model sees the question, a reference solution and the learner's numbered working. It must return the number
of the first wrong step, or 0 when the working is correct (a different valid method is still correct).

Run from the backend folder:
    .venv\Scripts\python.exe eval\misconception\eval_step_finder.py --provider qwen_finetuned   # our fine-tuned Qwen
    .venv\Scripts\python.exe eval\misconception\eval_step_finder.py --provider gemini           # API baseline
    .venv\Scripts\python.exe eval\misconception\eval_step_finder.py --dry-run                   # print one prompt only

Settings are read from backend/.env (QWEN_URL and QWEN_API_KEY for qwen_finetuned).

The providers and their env vars are described in app/services/llm.py.
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parents[1]
sys.path.insert(0, str(BACKEND))

SYSTEM = (
    "You check a school learner's working against a reference solution. "
    "Find the first step in the learner's working that is wrong. "
    "A different method that is valid and reaches the correct answer is not an error. "
    "If no step is wrong, answer 0. Do not invent errors. "
    'Reply with JSON only: {"first_wrong_step": <number>, "error": "<one short sentence, empty if 0>"}'
)


def build_prompt(case: dict, reference_steps: str = "full") -> str:
    # "last" keeps only the final line of the reference, close to what the backend has today (an answer, no steps)
    steps = case["reference"] if reference_steps == "full" else case["reference"][-1:]
    reference = "\n".join(f"- {s}" for s in steps)
    working = "\n".join(f"{i}. {s}" for i, s in enumerate(case["working"], 1))
    return f"Question: {case['question']}\n\nReference solution:\n{reference}\n\nLearner's working:\n{working}"


def parse(reply: str) -> tuple[int | None, str]:
    """Return (step, error). step is None when the reply cannot be read."""
    for block in re.findall(r"\{.*?\}", reply, re.S):
        try:
            data = json.loads(block)
            return int(data["first_wrong_step"]), str(data.get("error", ""))
        except (ValueError, KeyError, TypeError):
            continue
    cut_off = re.search(r'"first_wrong_step"\s*:\s*(\d+)', reply)   # reply ended before the JSON closed
    return (int(cut_off[1]), "") if cut_off else (None, "")


def score(rows: list[dict]) -> dict:
    """rows need: subject, kind, gold, pred (None = unreadable, counted as 'no error')."""
    def rate(items, test):
        return (sum(test(r) for r in items), len(items))

    def block(items):
        errors = [r for r in items if r["gold"] != 0]
        clean = [r for r in items if r["gold"] == 0]
        return {"right_step": rate(errors, lambda r: r["pred"] == r["gold"]),
                "error_noticed": rate(errors, lambda r: bool(r["pred"])),
                "false_suggestion": rate(clean, lambda r: bool(r["pred"]))}

    groups = defaultdict(list)
    for r in rows:
        groups[r["subject"]].append(r)
        groups[r["kind"]].append(r)
    out = {"all": block(rows), **{name: block(items) for name, items in sorted(groups.items())}}
    out["unreadable_replies"] = sum(r["pred"] is None for r in rows)
    return out


def show(summary: dict) -> None:
    def cell(pair):
        hit, total = pair
        return f"{hit}/{total} ({100 * hit / total:.0f}%)" if total else "-"

    print(f"{'group':<22}{'right step':<16}{'error noticed':<16}{'false suggestion':<16}")
    for name, b in summary.items():
        if isinstance(b, dict):
            print(f"{name:<22}{cell(b['right_step']):<16}{cell(b['error_noticed']):<16}{cell(b['false_suggestion']):<16}")
    print(f"unreadable replies: {summary['unreadable_replies']}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default=None, help="qwen_finetuned | gemini | openai | anthropic | ollama (default: LLM_PROVIDER)")
    ap.add_argument("--cases", default=str(HERE / "step_finder_cases.jsonl"))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--reference", choices=("full", "last"), default="full",
                    help="full = all reference steps; last = only the final line (answer without the method)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cases = [json.loads(line) for line in Path(args.cases).read_text(encoding="utf-8").splitlines() if line.strip()]
    cases = cases[:args.limit]
    if args.dry_run:
        print(SYSTEM, "\n", build_prompt(cases[0], args.reference), sep="\n")
        return

    try:
        from dotenv import load_dotenv
    except ImportError:
        sys.exit("python-dotenv is missing: run this with the backend's .venv\\Scripts\\python.exe")
    load_dotenv(BACKEND / ".env")
    from app.services import llm

    try:
        provider = llm.get_provider(args.provider)
        provider.ready()   # stop now with the reason if a setting is missing
    except Exception as e:
        sys.exit(f"Cannot start: {getattr(e, 'detail', e)}")
    rows = []
    for case in cases:
        try:
            reply = provider.generate(build_prompt(case, args.reference), SYSTEM, 1024)
        except Exception as e:  # keep going; a failed call counts as unreadable
            reply = f"CALL FAILED: {type(e).__name__}: {str(getattr(e, 'detail', e))[:200]}"
            print("   ", reply)
            if len(rows) == 2 and all(r["reply"].startswith("CALL FAILED") for r in rows):
                sys.exit("Stopped: the first three calls failed, so the model is not reachable. Nothing was saved.")
        pred, error = parse(reply)
        rows.append({"id": case["id"], "subject": case["subject"], "kind": case["kind"],
                     "gold": case["first_wrong_step"], "pred": pred,
                     "gold_error": case["error"], "pred_error": error, "reply": reply})
        print(f"{case['id']}  gold={case['first_wrong_step']}  pred={pred}")

    trial = f"first{args.limit}_" if args.limit else ""   # a trial run must not replace a full run's file
    trial += "answer_only_" if args.reference == "last" else ""
    out = HERE / "results" / f"{trial}{Path(args.cases).stem}_{provider.name}_{re.sub(r'[^A-Za-z0-9.-]+', '_', provider.model)}.jsonl"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    print(f"\n{provider.name} / {provider.model}   saved to {out}\n")
    show(score(rows))


if __name__ == "__main__":
    main()
