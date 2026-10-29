"""Download the raw datasets into notes/sandeep/milestone-2/data/raw/.

    python notes/sandeep/milestone-2/data/scripts/download.py            # all three
    python notes/sandeep/milestone-2/data/scripts/download.py assistments mathdial ncert

Files that already exist are skipped, so it is safe to re-run.
"""
import sys
from pathlib import Path

import requests

RAW = Path(__file__).resolve().parents[1] / "raw"
UA = {"User-Agent": "Mozilla/5.0"}  # ncert.nic.in rejects the default requests agent

ASSIST_URL = ("https://drive.usercontent.google.com/download"
              "?id=1NNXHFRxcArrU0ZJSb9BIL56vmUt5FhlE&export=download&confirm=t")
MATHDIAL_URL = "https://huggingface.co/datasets/eth-nlped/mathdial/resolve/main/{}.jsonl"
NCERT_URL = "https://ncert.nic.in/textbook/pdf/{}{:02d}.pdf"

# course, class, textbook code (chapter files are <code>01.pdf, <code>02.pdf, ...), max chapters to try
NCERT_BOOKS = [
    ("maths", 6, "fegp1", 10), ("maths", 7, "gegp1", 8), ("maths", 8, "hemh1", 13),
    ("maths", 9, "iemh1", 15), ("maths", 10, "jemh1", 15),
    ("science", 6, "fecu1", 12), ("science", 7, "gecu1", 12), ("science", 8, "hesc1", 13),
    ("science", 9, "iesc1", 15), ("science", 10, "jesc1", 16),
]


def fetch(url: str, dest: Path) -> bool:
    if dest.exists():
        return True
    r = requests.get(url, headers=UA, timeout=120)
    ctype = r.headers.get("content-type", "")
    if r.status_code != 200 or "html" in ctype:
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)
    return True


def assistments():
    ok = fetch(ASSIST_URL, RAW / "assistments" / "skill_builder_data_corrected.csv")
    print("assistments:", "ok" if ok else "FAILED")


def mathdial():
    for part in ("train", "test"):
        ok = fetch(MATHDIAL_URL.format(part), RAW / "mathdial" / f"{part}.jsonl")
        print(f"mathdial {part}:", "ok" if ok else "FAILED")


def ncert():
    for subject, cls, code, max_ch in NCERT_BOOKS:
        got = [n for n in range(1, max_ch + 1)
               if fetch(NCERT_URL.format(code, n), RAW / "ncert" / f"{subject}_class{cls}" / f"{code}{n:02d}.pdf")]
        print(f"ncert {subject} class {cls} ({code}): {len(got)} chapters")


JOBS = {"assistments": assistments, "mathdial": mathdial, "ncert": ncert}

if __name__ == "__main__":
    for name in sys.argv[1:] or JOBS:
        JOBS[name]()
