"""Automatic passage builder: turn extracted layout blocks into readable, citable passages.

Replaces per-chunk manual grouping. Blocks are walked in reading order within each chapter;
consecutive explanation blocks under the same heading are merged into passages of up to
TARGET tokens. Questions, worked examples, answers, figures, tables, running heads, page
numbers and teacher-only notes never enter a passage. Every decision is rule-based and
recorded, so the same code scales to Classes 6-10 without per-item review.
"""
import hashlib
import re
import unicodedata
from collections import Counter, defaultdict

TARGET, HARD_MAX, MIN_TOKENS, MIN_WORDS = 300, 400, 25, 15
SECTION = re.compile(r"^\s*(\d+(?:\.\d+)+)\s+([A-Za-z].*)$")
PAGE_NUMBER = re.compile(r"^\s*\d{1,3}\s*$")
TEACHER_ONLY = re.compile(r"teacher.?s\s+note", re.I)
# Boxes that hold learner questions; their text belongs to the question bank, never to evidence.
QUESTION_BOX = re.compile(r"^\s*(figure it out|try these|think,? discuss and write|exercise\s*\d|let us enhance|keep the curiosity alive)", re.I)
DIALOGUE = re.compile(r"^\s*[A-Z][a-z]+(\s[A-Z][a-z]+)?\s*:")
PRIVATE_USE = re.compile("[\ue000-\uf8ff\ufffd]")
QUESTION_LIKE = re.compile(r"\?.*\(a\).*\(b\)|\(a\).*\(b\).*\?", re.S)
BLOCKING = {"unresolved_unicode_glyphs", "unsafe_control_requires_source_check"}


def tidy_latex(text):
    """Whitespace-only normalisation of MinerU LaTeX: \\frac { 1 0 } { 2 7 } -> \\frac{10}{27}."""
    def word(m):
        return m.group(1) + "{" + re.sub(r"\s+", "", m.group(2)) + "}"
    text = re.sub(r"(\\(?:operatorname|mathrm|mathbf|text))\s*\{([^{}]*)\}", word, text)
    for _ in range(4):
        text = re.sub(r"\{\s*([^{}]*?)\s*\}", lambda m: "{" + re.sub(r"(?<=\d)\s+(?=\d)", "", m.group(1)) + "}", text)
    text = re.sub(r"\\(frac|sqrt)\s+\{", r"\\\1{", text)
    text = re.sub(r"\}\s+\{", "}{", text)
    text = re.sub(r"([\ufb01\ufb02])\s+(?=[a-z])", r"\1", text)   # OCR split ligatures: "\ufb01 ndings" -> "findings"
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", text).strip()


def math_ok(text):
    return text.count("{") == text.count("}") and "\\boxed" not in text and not PRIVATE_USE.search(text)


def block_text(b):
    return (b["cleaned_text"] or b["cleaned_latex"] or "").strip()


def order_key(b, raw_order):
    return (b["page_number"], b.get("reading_order", raw_order.get(b["block_id"], 0)))


def running_heads(blocks):
    pages = defaultdict(set)
    for b in blocks:
        t = block_text(b).lower()
        if t and len(t) < 60:
            pages[t].add(b["page_number"])
    return {t for t, p in pages.items() if len(p) >= 3}


def section_concept(section_map, sid, number):
    parts = number.split(".")
    for n in range(len(parts), 0, -1):
        hit = section_map.get(sid, {}).get(".".join(parts[:n]))
        if hit:
            return hit
    return None


def build(clean, roles, sources, raw_order, count_tokens, section_map, offsets, unresolved, version, tokenizer_revision):
    """Return (passages, exclusions, section_concepts)."""
    passages, exclusions, section_concepts = [], Counter(), {}
    by_source = defaultdict(list)
    for b in clean:
        if b["content_role"] == "chapter_content" and not b["removed"]:
            by_source[b["source_id"]].append(b)
    for sid, blocks in sorted(by_source.items()):
        source = sources[sid]
        blocks.sort(key=lambda b: order_key(b, raw_order))
        heads = running_heads(blocks)
        chapter = re.sub(r"\W+", "-", source["chapter_title"].lower()).strip("-")
        section = dict(number="0", title=source["chapter_title"] + " (introduction)")
        current, skip_aside = [], False

        def close():
            nonlocal current
            if current:
                emit(current, section)
            current = []

        def emit(group, sec):
            text = tidy_latex(" ".join(block_text(b) for b in group))
            tokens = count_tokens(text)
            dialogue = sum(bool(DIALOGUE.match(block_text(b))) for b in group) / len(group)
            prev = passages[-1] if passages else None
            if (tokens < MIN_TOKENS or len(text.split()) < MIN_WORDS) and prev and prev["source_id"] == sid \
                    and prev["section_number"] == sec["number"] and count_tokens(prev["text"] + " " + text) <= HARD_MAX:
                prev["text"] = tidy_latex(prev["text"] + " " + text)
                prev["block_ids"] += [b["block_id"] for b in group]
                prev["page_end"] = max(prev["page_end"], group[-1]["page_number"])
                prev["token_count"] = count_tokens(prev["text"])
                return
            if tokens < MIN_TOKENS or len(text.split()) < MIN_WORDS:
                exclusions["too_short_fragment"] += len(group); return
            if dialogue >= 0.6 and tokens < 80:
                exclusions["dialogue_only_fragment"] += len(group); return
            page = group[0]["page_number"]
            mapped = section_concept(section_map, sid, sec["number"])
            if mapped:
                concepts = [mapped]
            else:
                cid = f"g{source['grade']}-{source['subject'][:4]}-{chapter}-{sec['number']}"
                section_concepts.setdefault(cid, dict(
                    concept_id=cid, title=sec["title"], subject=source["subject"], grade=int(source["grade"]), aliases=[],
                    learning_objective=f"{source['chapter_title']}: {sec['title']}", description=f"Section {sec['number']} of {source['book_title']}, {source['chapter_title']}",
                    review_status="approved", reviewer="pipeline", review_method="automatic_section_heading",
                    review_scope="Concept taken from the textbook's own section heading", source_block_ids=[],
                    book_source_ids=[sid], evidence_refs=[], corpus_version=version))
                concepts = [cid]
                section_concepts[cid]["source_block_ids"] += [b["block_id"] for b in group]
            ids = [b["block_id"] for b in group]
            offset = offsets.get(sid)
            passages.append(dict(
                chunk_id="ncert-chunk-" + hashlib.sha256("|".join(ids).encode()).hexdigest()[:20],
                content_hash=hashlib.sha256(text.encode()).hexdigest(), text=text, content_type="explanation",
                source_id=sid, source_sha256=source["sha256"], source_url=source["source_url"], book_title=source["book_title"],
                subject=source["subject"], grade=int(source["grade"]), section_number=sec["number"],
                section_ref=f"{source['chapter_title']} / {sec['number']} {sec['title']}".replace(" / 0 ", " / "),
                page_start=page, page_end=group[-1]["page_number"],
                printed_page_labels=sorted({b["page_number"] + offset for b in group}) if offset is not None else [None],
                block_ids=ids, concept_ids=concepts, token_count=tokens, tokenizer_revision=tokenizer_revision,
                review_status="approved", reviewer="pipeline", review_method="automatic_rule_gate",
                passage_method="automatic_section_merge", corpus_version=version, retrieval_visibility="evidence",
                embedding_status="accepted"))

        for b in blocks:
            t = block_text(b)
            role = roles[b["block_id"]]["role"]
            if not t or PAGE_NUMBER.match(t) or t.lower() in heads:
                exclusions["page_number_or_running_head"] += 1; continue
            first_line = t.split("\n")[0].strip()
            is_title = b["content_type"] == "heading" or (len(t) <= 40 and bool(SECTION.match(first_line)))
            if is_title:
                t = first_line
                close()
                m = SECTION.match(t)
                skip_aside = bool(TEACHER_ONLY.search(t) or QUESTION_BOX.match(t))
                if m:
                    section = dict(number=m.group(1), title=m.group(2).strip())
                    current = [b] if role == "content" else []
                elif not skip_aside and role == "content" and len(t) > 3:
                    current = [b]          # sub-heading leads the next passage
                continue
            if skip_aside:
                exclusions["question_box_or_teacher_note"] += 1; continue
            if role != "content":
                close(); exclusions[f"role_{role}"] += 1; continue
            if QUESTION_LIKE.search(t):
                close(); exclusions["unextracted_exercise_text"] += 1; continue
            if b["content_type"] in ("diagram/image", "table") or b["block_id"] in unresolved \
                    or BLOCKING & set(b["quarantine_reasons"] or []) or not math_ok(t):
                close()
                reason = ("figure" if b["content_type"] == "diagram/image" else "table" if b["content_type"] == "table"
                          else "unresolved_currency" if b["block_id"] in unresolved else "unreadable_symbols")
                exclusions[reason] += 1; continue
            if current and count_tokens(tidy_latex(" ".join(block_text(x) for x in current + [b]))) > TARGET:
                close()
            if count_tokens(tidy_latex(t)) > HARD_MAX:
                exclusions["oversize_single_block"] += 1; continue
            current.append(b)
        close()
    kept = list(section_concepts.values())
    return passages, exclusions, kept
