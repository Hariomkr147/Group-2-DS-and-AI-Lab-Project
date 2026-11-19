"""PyMuPDF-first hybrid routing test.

Runs PyMuPDF on every chapter page, then checks a cheap page router against
MinerU's existing output (reference: page has a MinerU equation, inline formula
or table). Writes per-page results + summary. No MinerU is re-run.
"""
import csv, json, re, time, difflib, unicodedata
from collections import defaultdict
from pathlib import Path
import pymupdf

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "03_parser_benchmark/outputs/hybrid"
NUM = re.compile(r"^\s*\d+\s*$")
OPS = set("×÷=+−–<>%^")

def words(s):
    s = re.sub(r"\\[a-zA-Z]+|[{}_^$]", " ", s or "")
    return re.findall(r"[a-z0-9]+", s.lower())

def native_features(page):
    d = page.get_text("dict")
    text, num_lines, sup, pua, ops = [], 0, 0, 0, 0
    for blk in d["blocks"]:
        for line in blk.get("lines", []):
            lt = "".join(s["text"] for s in line["spans"])
            text.append(lt)
            num_lines += bool(NUM.match(lt))
            for s in line["spans"]:
                sup += bool(s["flags"] & 1) and bool(s["text"].strip())
            pua += sum(unicodedata.category(c) == "Co" for c in lt)
            ops += sum(c in OPS for c in lt)
    joined = "\n".join(text)
    notation = bool(re.search(r"[→⇌]|[A-Za-z][²³⁴⁵⁶⁷⁸⁹⁰₀₁₂₃₄₅₆₇₈₉]|(?:=\s*[-+]?\d|\d\s*=)|[A-Za-z]\s*\^\s*[-−]?\d", joined))
    # Reduced raised/lowered spans beside letters cover notation with baseline glyphs.
    for blk in d["blocks"]:
        for line in blk.get("lines", []):
            spans = line["spans"]
            if not any(re.search(r"[A-Za-z]", s["text"]) for s in spans):
                continue
            size = max((s["size"] for s in spans), default=0)
            notation |= any(bool(s["flags"] & 1) or (s["size"] < .85 * size and bool(re.search(r"\d|[+−-]", s["text"]))) for s in spans)
    tables = len(page.find_tables().tables)
    return joined, dict(tables=tables, num_lines=num_lines, superscripts=sup, pua=pua, ops=ops,
                                 notation=int(notation), table_caption=int(bool(re.search(r"\btable\s+\d+[.:]\d+", joined, re.I))),
                                 drawings=len(page.get_drawings()), images=len(page.get_images()))

def route(f, t):
    # ponytail: hand-set heuristic; retune when more books are labelled
    return "mineru" if (f["num_lines"] >= t["num"] or f["superscripts"] >= t["sup"] or f["pua"] > 0 or f["ops"] >= t["ops"]) else "pymupdf"

def subject_route(sid, f, role="chapter_content"):
    if role == "private_answer":
        return "mineru"
    if role != "chapter_content":
        return "pymupdf"
    if "-mathematics-" in sid:
        return "mineru"
    # Table captions recover the known pilot table missed by find_tables().
    return "mineru" if f.get("tables", 0) or f.get("table_caption", 0) or f.get("num_lines", 0) >= 4 or f.get("notation", 0) else "pymupdf"

def main():
    src = {r["source_id"]: ROOT / r["local_path"] for r in csv.DictReader(open(ROOT / "01_download_pdfs/manifests/sources.csv"))}
    role = {(r["source_id"], int(r["page_number"])): r["proposed_content_role"]
            for r in csv.DictReader(open(ROOT / "02_pdf_audit/outputs/source_page_dispositions.csv"))}
    mineru = defaultdict(lambda: dict(text=[], math=0, table=0))
    for line in open(ROOT / "04_extract_text_and_ocr/outputs/blocks.jsonl", encoding="utf-8"):
        b = json.loads(line)
        if b["content_role"] != "chapter_content":
            continue
        k = (b["source_id"], int(b["page_number"]))
        if b["native_content_type"] in ("header", "footer", "page_number"):
            continue
        m = mineru[k]
        m["text"].append(b["raw_text"] or "")
        m["math"] += (b["native_content_type"] == "equation") + (b["inline_formulas"] not in ("[]", [], None))
        m["table"] += b["native_content_type"] == "table"

    rows, t0 = [], time.perf_counter()
    for sid, path in src.items():
        doc = pymupdf.open(path)
        for i, page in enumerate(doc, 1):
            if role.get((sid, i)) != "chapter_content":
                continue
            ntext, f = native_features(page)
            m = mineru[(sid, i)]
            sim = difflib.SequenceMatcher(None, words(ntext), words(" ".join(m["text"])), autojunk=False).ratio()
            rows.append(dict(source_id=sid, page=i, subject_route=subject_route(sid, f), **f, mineru_math=m["math"], mineru_tables=m["table"],
                             needs_mineru=int(m["math"] + m["table"] > 0), word_similarity=round(sim, 3)))
    native_seconds = time.perf_counter() - t0

    grid = []
    for num in (1, 2, 3, 4, 6):
        for sup in (1, 3, 5, 10, 99):
            for ops in (1, 3, 5, 10, 99):
                t = dict(num=num, sup=sup, ops=ops)
                pred = [route(r, t) == "mineru" for r in rows]
                tp = sum(p and r["needs_mineru"] for p, r in zip(pred, rows))
                fn = sum((not p) and r["needs_mineru"] for p, r in zip(pred, rows))
                grid.append(dict(**t, mineru_pages=sum(pred), missed_math_pages=fn,
                                 recall=round(tp / max(1, tp + fn), 3)))
    # best = fewest MinerU pages with zero missed math pages
    safe = [g for g in grid if g["missed_math_pages"] == 0]
    best = min(safe, key=lambda g: g["mineru_pages"]) if safe else None

    with open(OUT / "page_routes.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    with open(OUT / "router_grid.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=grid[0].keys()); w.writeheader(); w.writerows(grid)
    plain = [r for r in rows if not r["needs_mineru"]]
    summary = dict(pymupdf_version=pymupdf.VersionBind, chapter_pages=len(rows),
                   pymupdf_seconds_all_pages=round(native_seconds, 2),
                   pages_needing_mineru_reference=sum(r["needs_mineru"] for r in rows),
                   plain_pages=len(plain),
                   plain_page_word_similarity_median=sorted(r["word_similarity"] for r in plain)[len(plain)//2] if plain else None,
                   best_safe_router=best,
                   subject_router=dict(
                       mineru_pages=sum(r["subject_route"] == "mineru" for r in rows),
                       missed_math_or_table_pages=[(r["source_id"], r["page"]) for r in rows if r["needs_mineru"] and r["subject_route"] == "pymupdf"],
                       extra_mineru_pages=[(r["source_id"], r["page"]) for r in rows if not r["needs_mineru"] and r["subject_route"] == "mineru"]),
                   mineru_seconds_per_page_measured=round((20*60+33)/79, 1),
                   reference_limit="MinerU output is the reference; MinerU-missed formulas are not detected")
    json.dump(summary, open(OUT / "summary.json", "w"), indent=1)
    print(json.dumps(summary, indent=1))

if __name__ == "__main__":
    main()
