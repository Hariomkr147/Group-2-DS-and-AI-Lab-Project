"""Extract NCERT's own questions, worked examples and answer-key solutions.

Nothing is written or derived by an AI: question text comes from chapter pages,
answers come only from NCERT's appended solution pages (MinerU-parsed). Questions
with no NCERT answer keep answer_available=False.
"""
import json, re, difflib, hashlib, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "00_setup_and_scope/code"))
from pipeline import SOURCES, read_csv, read_jsonl, run_record, write_jsonl, sha256
OUT = ROOT / "07_concepts_questions_and_chunks/outputs"

SECTION = re.compile(r"^\s*(figure it out|try these|exercise\s*\d+(\.\d+)?|think,? discuss and write|let us enhance our learning)\b", re.I)
NUMBERED = re.compile(r"^\s*(\d{1,2})\s*[.)]\s+")
EXAMPLE = re.compile(r"^\s*example\s*(\d+)", re.I)
SOLUTION = re.compile(r"^\s*solution\b", re.I)
SKIP = {"header", "footer", "page_number", "aside_text"}
# Questions the learner cannot answer without seeing or drawing a figure are not extracted
# (decision 4 Nov 2026) until the app can show figures. Hints ("[Hint: draw ...]") do not count,
# and a nearby image block alone does not count: decorative pictures sit next to many text questions.
NEEDS_FIGURE = re.compile(r"\bfig(ure)?s?\b|\bpictures?\b|\bdiagrams?\b|\bshown\s+(below|above|alongside|here|in)\b|"
                          r"\bgiven\s+below\b|\bempty\s+box|\bshaded?\b|\bdraw\b|\bnumber\s+line\b|\bcolou?r\b|"
                          r"\bmatch\s+each\b|\bgrid\b|\\boxed", re.I)
HINT = re.compile(r"\[\s*hint\s*:.*?\]", re.I | re.S)


def needs_figure(text):
    return bool(NEEDS_FIGURE.search(HINT.sub(" ", text or "")))

def words(s):
    s = re.sub(r"\\[a-zA-Z]+|[{}_^$*\\]", " ", s or "")
    return re.findall(r"[a-z0-9]+", s.lower())

def sim(a, b, n=20):
    # compare question openings: key items sometimes carry extra table/answer text after the stem
    a, b = words(a), words(b)
    if b and b[0].isdigit():
        b = b[1:]  # drop the printed question number
    return difflib.SequenceMatcher(None, a[:n], b[:n], autojunk=False).ratio()

def text_sim(a, b):
    """Similarity that ignores LaTeX markup and OCR digit spacing (\\frac { 1 0 } == \\frac{10})."""
    def norm(t):
        t = re.sub(r"\\[a-zA-Z]+|[{}$_^*\\]", " ", t or "").lower()
        t = re.sub(r"(?<=\d)\s+(?=\d)", "", t)
        return " ".join(re.findall(r"[a-z0-9]+", t))
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def page_offsets():
    """Printed page = physical page + offset; the most common offset among printed page numbers wins."""
    found = {}
    for line in open(ROOT / "04_extract_text_and_ocr/outputs/blocks.jsonl", encoding="utf-8"):
        b = json.loads(line); t = (b["raw_text"] or "").strip()
        if re.fullmatch(r"\d{2,3}", t):
            found.setdefault(b["source_id"], Counter())[int(t) - b["page_number"]] += 1
    return {sid: c.most_common(1)[0][0] for sid, c in found.items() if c.most_common(1)[0][1] >= 3}


def locate_in_chapter(question, sid, phys, chapter_blocks, used, threshold=0.75):
    page = [b for b in chapter_blocks if b["source_id"] == sid and b["page"] in (phys, phys + 1)
            and b["id"] not in used and b["kind"] not in ("image", "chart") and b["text"]]
    best, best_score = None, 0
    for i in range(len(page)):
        for width in (1, 2, 3):
            window = page[i:i + width]
            if len(window) < width:
                continue
            text = " ".join(b["text"] for b in window)
            score = text_sim(question, text[:len(question) + 60])
            if score > best_score:
                best, best_score = window, score
    return (best, best_score) if best_score >= threshold else (None, best_score)


def qid(*parts):
    return "ncert-q-" + hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:16]

def load_blocks():
    raw = {}
    for line in open(ROOT / "04_extract_text_and_ocr/outputs/blocks.jsonl", encoding="utf-8"):
        b = json.loads(line); raw[b["block_id"]] = b
    out = []
    for line in open(ROOT / "05_clean_and_preprocess/outputs/clean_blocks.jsonl", encoding="utf-8"):
        c = json.loads(line)
        if c["content_role"] not in {"chapter_content", "private_answer"} or c["removed"]:
            continue
        r = raw[c["raw_block_id"]]
        if r["native_content_type"] in SKIP:
            continue
        text = c["cleaned_text"] or c["cleaned_latex"] or ""
        out.append(dict(id=c["block_id"], source_id=c["source_id"], source_sha256=r["source_sha256"], role=c["content_role"],
                        page=int(c["page_number"]), order=int(c.get('reading_order',r["block_order"])), kind=r["native_content_type"],
                        text=text.strip(), assets=json.loads(r["asset_ids"]) if isinstance(r["asset_ids"], str) else r["asset_ids"]))
    out.sort(key=lambda b: (b["source_id"], b["page"], b["order"]))
    return out

def extract(blocks):
    questions, examples = [], []
    section = cur = ex = None
    instruction = ""

    def close():
        nonlocal cur, ex
        if cur: questions.append(cur)
        if ex: examples.append(ex)
        cur = ex = None

    prev_source = None
    for b in blocks:
        t = b["text"]
        if b["source_id"] != prev_source:
            close(); section = None; prev_source = b["source_id"]
        m_sec, m_ex = SECTION.match(t), EXAMPLE.match(t)
        inner = re.search(r"\s(?=example\s*\d+\s*:)", t, re.I)
        if ex and inner and not m_ex:  # MinerU merged the next example into this block
            ex["prompt"].append(t[:inner.start()].strip()); ex["block_ids"].append(b["id"])
            close(); m_ex = EXAMPLE.match(t[inner.end():]); t = t[inner.end():]
        title = b["kind"] in ("paragraph_title", "doc_title")
        if m_sec:
            close(); section = dict(name=m_sec.group(1).strip().title(), page=b["page"]); instruction = ""
            rest = t[m_sec.end():].strip(" :.")
            if rest: instruction = rest
            continue
        if m_ex:
            close(); section = None
            ex = dict(example_number=int(m_ex.group(1)), source_id=b["source_id"], page_start=b["page"], page_end=b["page"],
                      prompt=[t], solution=[], block_ids=[b["id"]], asset_ids=list(b["assets"]))
            continue
        if ex:
            if title and not SOLUTION.match(t):
                close()
            else:
                (ex["solution"] if (ex["solution"] or SOLUTION.match(t)) else ex["prompt"]).append(t)
                ex["block_ids"].append(b["id"]); ex["asset_ids"] += b["assets"]; ex["page_end"] = b["page"]
                continue
        if section and title and not NUMBERED.match(t) and not t.startswith("("):
            close(); section = None
        if not section:
            continue
        m_num = NUMBERED.match(t)
        if m_num:
            if cur: questions.append(cur)
            cur = dict(source_id=b["source_id"], section=section["name"], section_page=section["page"], number=int(m_num.group(1)),
                       page_start=b["page"], page_end=b["page"], instruction=instruction, text=[t], block_ids=[b["id"]],
                       asset_ids=list(b["assets"]), has_image=b["kind"] in ("image", "chart"))
        elif cur:
            if b["kind"] in ("image", "chart"):
                cur["has_image"] = True
            if t: cur["text"].append(t)
            cur["block_ids"].append(b["id"]); cur["asset_ids"] += b["assets"]; cur["page_end"] = b["page"]
        elif t and b["kind"] not in ("image", "chart"):
            instruction = (instruction + " " + t).strip()
        # unnumbered sections (e.g. Try These with only (i), (ii)) become one question
        if not cur and section and t.startswith("("):
            cur = dict(source_id=b["source_id"], section=section["name"], section_page=section["page"], number=0,
                       page_start=b["page"], page_end=b["page"], instruction=instruction, text=[t], block_ids=[b["id"]],
                       asset_ids=list(b["assets"]), has_image=False)
    close()
    return questions, examples

def parse_key(md, answer_only=False):
    """Split retained canonical solution blocks, preserving their physical-page lineage."""
    records = [{"text": md}] if isinstance(md, str) else md
    if answer_only:
        records = [{**r, "text": re.sub(r"(?<![\w.])(\d{1,2})\.\s+(?=\S)", r"\n\1. ", r["text"])} for r in records]
    items, page, buf, exercise = [], None, None, None
    for record, line in ((r, line) for r in records for line in (r["text"].splitlines() or [""])):
        s = line.strip().replace("**", "")
        section = re.match(r"^\s*exercise\s*(\d+(?:\.\d+)?)\b", s, re.I)
        if section:
            if buf: items.append(buf); buf = None
            exercise = "Exercise " + section.group(1)
            continue
        if buf and record.get("assets"):
            buf["has_image"] = True
            buf["asset_ids"] = sorted(set(buf["asset_ids"] + record["assets"]))
        mp = re.search(r"page\s*no\.?\s*(\d+)", s, re.I)
        if mp:
            page = int(mp.group(1))
            s = (s[:mp.start()] + s[mp.end():]).strip()
        if re.match(r"^(section\s*\d|figure it out|chapter|#|!\[)", s, re.I) or not s:
            if not re.match(r"^q\d*\s*[.:]", s, re.I) and not s.lower().startswith("ans"):
                if buf and s.startswith("!["):
                    buf["has_image"] = True
                continue
        mq = re.match(r"^(?:q\s*(\d*)|(\d{1,2}))\s*[.:)]\s*(.*)", s, re.I)
        if mq and (s.lower().startswith("q") or buf is None or buf["in_answer"]):
            if buf: items.append(buf)
            buf = dict(page_label=page, number=int(mq.group(1) or mq.group(2) or 0), exercise=exercise,
                       question="", answer="", has_image=False, in_answer=answer_only, source_block_ids=[],
                       question_block_ids=[], answer_block_ids=[], physical_pages=[], asset_ids=[])
            s = mq.group(3)
        if buf is None:
            continue
        ma = re.search(r"\bans(wer)?\s*[.:]\s*", s, re.I)
        if record.get("id"):
            if record["id"] not in buf["source_block_ids"]: buf["source_block_ids"].append(record["id"])
            if record["page"] not in buf["physical_pages"]: buf["physical_pages"].append(record["page"])
            field = "answer_block_ids" if ma or buf["in_answer"] else "question_block_ids"
            if record["id"] not in buf[field]: buf[field].append(record["id"])
        if ma:
            if record.get("id") and s[:ma.start()].strip() and record["id"] not in buf["question_block_ids"]:
                buf["question_block_ids"].append(record["id"])
            buf["question"] += " " + s[:ma.start()]
            buf["answer"] += s[ma.end():]; buf["in_answer"] = True
        elif buf["in_answer"]:
            buf["answer"] += ("\n" if buf["answer"] else "") + s
        else:
            buf["question"] += " " + s
    if buf: items.append(buf)
    for it in items:
        it["question"], it["answer"] = it["question"].strip(), it["answer"].strip()
        it.pop("in_answer")
    return items

def build_bank():
    blocks = load_blocks()
    questions, examples = extract([b for b in blocks if b["role"] == "chapter_content"])
    qrows = []
    for q in questions:
        text = "\n".join(q["text"])
        qrows.append(dict(question_id=qid(q["source_id"], q["page_start"], q["section"], q["section_page"], q["number"], text[:80]),
                          source_id=q["source_id"], kind="exercise" if q["section"].lower().startswith("exercise") or "enhance" in q["section"].lower() else "in_chapter",
                          section=q["section"], number=q["number"], instruction=q["instruction"], prompt=text,
                          page_start=q["page_start"], page_end=q["page_end"], requires_diagram=needs_figure(text), image_nearby=q["has_image"],
                          asset_ids=q["asset_ids"], source_block_ids=q["block_ids"], provenance="ncert_extracted",
                          answer_available=False, answer_source=None, concept_ids=[], review_status="pending"))
    erows = [dict(example_id=qid(e["source_id"], e["page_start"], "example", e["example_number"]), source_id=e["source_id"],
                  example_number=e["example_number"], prompt="\n".join(e["prompt"]), solution="\n".join(e["solution"]),
                  page_start=e["page_start"], page_end=e["page_end"], asset_ids=e["asset_ids"], source_block_ids=e["block_ids"],
                  provenance="ncert_extracted", concept_ids=[], review_status="pending") for e in examples]

    answers, key_stats = [], {}
    offsets = page_offsets()
    chapter_blocks = [b for b in blocks if b["role"] == "chapter_content"]
    used_blocks = {b for q in qrows for b in q["source_block_ids"]} | {b for e in erows for b in e["source_block_ids"]}
    for sid in sorted({b["source_id"] for b in blocks if b["role"] == "private_answer"}):
        key_blocks = [b for b in blocks if b["source_id"] == sid and b["role"] == "private_answer"]
        answer_only = sid.endswith("-an")
        items = parse_key(key_blocks, answer_only=answer_only)
        pool = [q for q in qrows if q["source_id"] == sid or (answer_only and q["source_id"].rsplit("-", 1)[0] == sid.rsplit("-", 1)[0])]
        offset = offsets.get(sid)
        matched = located = 0
        for it in items:
            candidates = [q for q in pool if not q["answer_available"]]
            best, score, how = None, 0, None
            if answer_only:
                candidates = [q for q in candidates if q["section"] == it["exercise"] and q["number"] == it["number"]]
                best, how = (candidates[0], "exercise_number") if len(candidates) == 1 else (None, None)
            else:
                # New books restate each question under its printed page ("Page no. 152"): look on that chapter page first.
                phys = it["page_label"] - offset if it["page_label"] is not None and offset is not None else None
                if phys is not None:
                    near = sorted(((text_sim(it["question"], q["prompt"]), q) for q in candidates
                                   if q["page_start"] - 1 <= phys <= q["page_end"] + 1), key=lambda p: -p[0])
                    if near and (near[0][0] >= 0.6 or (near[0][0] >= 0.4 and near[0][1]["number"] == it["number"])):
                        score, best, how = near[0][0], near[0][1], "printed_page_and_text"
                if not best and candidates:
                    cand = max(candidates, key=lambda q: text_sim(it["question"], q["prompt"]))
                    if text_sim(it["question"], cand["prompt"]) >= 0.85:
                        score, best, how = text_sim(it["question"], cand["prompt"]), cand, "text"
                if not best and phys is not None and it["question"].strip():
                    # The chapter extractor only reads numbered section items; find in-text questions on the page itself.
                    window, score = locate_in_chapter(it["question"], sid, phys, chapter_blocks, used_blocks)
                    if window:
                        prompt = " ".join(b["text"] for b in window)
                        best = dict(question_id=qid(sid, "located", window[0]["page"], it["number"], prompt[:80]), source_id=sid,
                                    kind="in_chapter", section=None, number=it["number"], instruction="", prompt=prompt,
                                    page_start=window[0]["page"], page_end=window[-1]["page"], requires_diagram=needs_figure(prompt),
                                    image_nearby=any(b["assets"] for b in window), asset_ids=sorted({a for b in window for a in b["assets"]}),
                                    source_block_ids=[b["id"] for b in window], provenance="ncert_extracted", located_by="answer_key_printed_page",
                                    answer_available=False, answer_source=None, concept_ids=[], review_status="pending")
                        qrows.append(best); pool.append(best); used_blocks.update(best["source_block_ids"]); located += 1
                        how = "located_in_chapter_page"
            if best:
                best["answer_available"] = True; best["answer_source"] = "ncert_solution_pages"; matched += 1
            answers.append(dict(question_id=best["question_id"] if best else None, source_id=sid, source_sha256=key_blocks[0]["source_sha256"],
                                page_start=min(it["physical_pages"]) if it["physical_pages"] else None,
                                page_end=max(it["physical_pages"]) if it["physical_pages"] else None,
                                source_block_ids=it["source_block_ids"], answer_block_ids=it["answer_block_ids"], question_block_ids=it["question_block_ids"],
                                key_page_label=it["page_label"], key_number=it["number"], key_question=it["question"],
                                exercise_label=it["exercise"], answer=it["answer"], answer_has_image=it["has_image"], asset_ids=it["asset_ids"],
                                match_similarity=None if answer_only else round(score, 3), match_method=how, link_needs_review=False,
                                provenance="ncert_solution_pages", access_policy="backend_scoring_only; never retrieval context or learner export",
                                review_status="pending"))
        # Keys that match no chapter question are reported, never turned into questions.
        key_stats[sid] = dict(items=len(items), linked_to_chapter_question=matched, located_in_chapter_page=located,
                              unmatched_keys=len(items) - matched, page_offset=offset,
                              physical_page_provenance="Canonical solution blocks; chapter page from printed-page offset")

    with_text = {a["question_id"] for a in answers if a["question_id"] and a["answer"]}
    for q in qrows:  # an answer that is only a picture does not count as available
        q["answer_available"] = q["question_id"] in with_text
        q["answer_source"] = "ncert_solution_pages" if q["answer_available"] else None

    # Drop figure-dependent questions and their keys; keep an audit record of what was skipped.
    skipped = [q for q in qrows if q["requires_diagram"]]
    skipped_ids = {q["question_id"] for q in skipped}
    skipped_answers = [a for a in answers if a["question_id"] in skipped_ids]
    qrows = [q for q in qrows if q["question_id"] not in skipped_ids]
    answers = [a for a in answers if a["question_id"] not in skipped_ids]

    sources = {s["source_id"]: s for s in read_csv(SOURCES)}
    raw = {b["block_id"]: b for b in read_jsonl(ROOT / "04_extract_text_and_ocr/outputs/blocks.jsonl")}
    for collection, identity in [(qrows + skipped, "question_id"), (erows, "example_id")]:
        if len(collection) != len({r[identity] for r in collection}):
            raise ValueError("Duplicate extracted NCERT identity")
        for row in collection:
            if not row["source_block_ids"] or not 1 <= row["page_start"] <= row["page_end"] <= int(sources[row["source_id"]]["pdf_pages"]):
                raise ValueError("Question/example lacks physical source lineage")
            if any(b not in raw or raw[b]["source_id"] != row["source_id"] or not row["page_start"] <= raw[b]["page_number"] <= row["page_end"] for b in row["source_block_ids"]):
                raise ValueError("Question/example source blocks do not resolve")
            row["source_sha256"] = sources[row["source_id"]]["sha256"]
    for answer in answers:
        if not answer["source_block_ids"] or any(raw[b]["content_role"] != "private_answer" for b in answer["source_block_ids"]):
            raise ValueError("Answer did not originate in official private solution pages")
    # Skipped questions keep their block role so their text never becomes explanation evidence.
    question_blocks = {b: [q["question_id"] for q in qrows + skipped if b in q["source_block_ids"]] for q in qrows + skipped for b in q["source_block_ids"]}
    example_blocks = {b: [e["example_id"] for e in erows if b in e["source_block_ids"]] for e in erows for b in e["source_block_ids"]}
    roles = []
    for clean in read_jsonl(ROOT / "05_clean_and_preprocess/outputs/clean_blocks.jsonl"):
        bid = clean["block_id"]
        role = "answer" if clean["content_role"] == "private_answer" else "excluded" if clean["content_role"] != "chapter_content" or clean["removed"] else "worked_example" if bid in example_blocks else "question" if bid in question_blocks else "content"
        roles.append(dict(block_id=bid, source_id=clean["source_id"], page_number=clean["page_number"], role=role,
                          record_ids=example_blocks.get(bid, []) if role == "worked_example" else question_blocks.get(bid, []) if role == "question" else [],
                          role_conflict=bid in question_blocks and bid in example_blocks,
                          review_status="quarantined" if bid in question_blocks and bid in example_blocks else clean["review_status"]))
    if len(roles) != len(raw) or len({r["block_id"] for r in roles}) != len(raw):
        raise ValueError("Cleaned-block role partition lost or duplicated input records")
    write_jsonl(OUT / "block_roles.jsonl", roles)

    for name, rows in [("ncert_questions.jsonl", qrows), ("ncert_worked_examples.jsonl", erows), ("ncert_answers_private.jsonl", answers)]:
        write_jsonl(OUT / name, rows)
    write_jsonl(OUT / "skipped_figure_questions.jsonl",
                [dict(**q, skipped_reason="needs_figure", skipped_answer_ids=[a["source_block_ids"] for a in skipped_answers if a["question_id"] == q["question_id"]]) for q in skipped])
    summary = dict(questions=len(qrows), by_source_provenance=Counter(f'{q["source_id"].split("-")[2]}-{q["source_id"].split("-")[3]} {q["kind"]} {q["provenance"]}' for q in qrows),
                   questions_with_ncert_answer=sum(q["answer_available"] for q in qrows),
                   questions_with_ncert_answer_by_source=Counter(q["source_id"].split("-")[3] for q in qrows if q["answer_available"]),
                   skipped_figure_questions=len(skipped), skipped_figure_answers=len(skipped_answers),
                   worked_examples=len(erows), worked_examples_by_source=Counter(e["source_id"].split("-")[3] for e in erows),
                   answer_key=key_stats, invented_questions=0, invented_answers=0,
                   block_role_counts=Counter(r["role"] for r in roles), role_conflicts=sum(r["role_conflict"] for r in roles),
                   not_extracted="figure-dependent questions (skipped), unnumbered in-text prompts without an NCERT key; extraction does not approve scoring")
    json.dump(summary, open(OUT / "ncert_question_summary.json", "w"), indent=1, default=dict)
    print(json.dumps(summary, indent=1, default=dict))
    return summary


def main():
    inputs = [SOURCES, ROOT / "04_extract_text_and_ocr/outputs/blocks.jsonl", ROOT / "05_clean_and_preprocess/outputs/clean_blocks.jsonl"]
    checks=ROOT/'07_concepts_questions_and_chunks/config/item_source_checks.json'
    if checks.exists():inputs.append(checks)
    with run_record("07_concepts_questions_and_chunks", inputs) as run:
        summary = build_bank()
        checks=ROOT/'07_concepts_questions_and_chunks/config/item_source_checks.json'
        if checks.exists():
            from review_source_items import audit_bank
            summary['item_reviews']=audit_bank()
        outputs = [OUT / name for name in ["ncert_questions.jsonl", "ncert_worked_examples.jsonl", "ncert_answers_private.jsonl", "skipped_figure_questions.jsonl", "block_roles.jsonl", "ncert_question_summary.json"]]
        if checks.exists():outputs.extend([OUT/'question_item_reviews.jsonl',OUT/'item_review_summary.json'])
        manifest = dict(run_id=run["run_id"], input_hashes={p.relative_to(ROOT).as_posix(): sha256(p) for p in inputs},
                        artifact_hashes={p.relative_to(ROOT).as_posix(): sha256(p) for p in outputs},
                        review_status="item_dispositions_complete; only scoring_eligible approved pairs may be graded" if checks.exists() else "pending; source extraction is not an approved scoring bank", invented_questions=0, invented_answers=0)
        if checks.exists():
            manifest['source_check_decisions_sha256']=sha256(checks)
        path = OUT / "ncert_bank_manifest.json"; path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        run["outputs"].extend([*outputs, path]); run["counts"] = summary

if __name__ == "__main__":
    main()
