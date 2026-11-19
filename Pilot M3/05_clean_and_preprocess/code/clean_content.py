"""Conservative, reversible draft cleaning; preserve formula/table representations verbatim."""
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "00_setup_and_scope/code"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "04_extract_text_and_ocr/code"))
from pipeline import ROOT, SOURCES, local_path, read_csv, read_jsonl, run_record, write_csv, write_jsonl
from validate_extraction import validate_extraction

PHASE = ROOT / "05_clean_and_preprocess"
RAW = ROOT / "04_extract_text_and_ocr/outputs"
CORRECTIONS = PHASE / 'config/source_corrections.json'
CONTROLS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
RULES = [
    {"rule_id": "SOURCE_CHECKED_FIX", "reason": "Exact source-bound, reviewed currency/word correction", "limit": "Only immutable source-hash/before/after matches in config/source_corrections.json"},
    {"rule_id": "CRLF_TO_LF", "reason": "Represent line endings consistently", "limit": "No joining/reflow of lines"},
    {"rule_id": "CONTROL_TO_SPACE", "reason": "Prevent invisible controls joining tokens", "limit": "Affected blocks quarantined for source review"},
    {"rule_id": "TRIM_LINE_ENDS", "reason": "Remove trailing ASCII spacing and outer blank space", "limit": "Preserve internal spacing, lines and all Unicode/math characters"},
    {"rule_id": "REPEATED_REPRINT_FOOTER", "reason": "Exact source-edition footer repeated at bottom on at least three pages", "limit": "Full-block match only; original always retained"},
    {"rule_id": "REPEATED_RUNNING_HEADER", "reason": "Known book/chapter header repeated at top on at least three pages", "limit": "Exact allowlist and geometric boundary; never numeric-only text"},
]


def clean_text(text):
    rules = []
    after = text.replace("\r\n", "\n").replace("\r", "\n")
    if after != text:
        rules.append("CRLF_TO_LF")
    replaced = CONTROLS.sub(" ", after)
    if replaced != after:
        rules.append("CONTROL_TO_SPACE")
    trimmed = "\n".join(line.rstrip(" \t") for line in replaced.split("\n")).strip(" \t\n")
    if trimmed != replaced:
        rules.append("TRIM_LINE_ENDS")
    return trimmed, rules


def content_hash(text, latex, html):
    return hashlib.sha256(json.dumps({"text": text, "latex": latex, "html": html}, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def geometry(block, native_dimensions):
    bbox = block["bbox"]
    if bbox is None:
        return None
    if block["coordinate_system"].startswith("MinerU normalized"):
        return bbox
    width, height = native_dimensions[(block["source_id"], block["page_number"])]
    return [bbox[0] / width, bbox[1] / height, bbox[2] / width, bbox[3] / height]


def removable_margin(block, source, native_dimensions):
    text = block["raw_text"].strip(" \t\r\n")
    bbox = geometry(block, native_dimensions)
    if bbox is None or block["inline_formulas"] or block["raw_latex"] or block["raw_html"]:
        return None
    if bbox[1] >= 0.90 and text == source["edition"]:
        return "REPEATED_REPRINT_FOOTER"
    allowed = {source["book_title"], source["chapter_title"]}
    if source["book_title"].startswith("Ganita Prakash"):
        allowed.add(f"Ganita Prakash | Grade {source['grade']}")
    if source["book_title"] == "Curiosity":
        allowed.add(f"Curiosity | Textbook of Science | Grade {source['grade']}")
    if bbox[3] <= 0.14 and text in allowed:
        return "REPEATED_RUNNING_HEADER"
    return None


def clean_records(pages, blocks, sources, native_dimensions, run_id):
    corrections = json.loads(CORRECTIONS.read_text(encoding='utf-8')) if CORRECTIONS.exists() else {'blocks': [], 'page_orders': []}
    fixes = {row['block_id']: row for row in corrections['blocks']}
    orders = {bid: i for row in corrections['page_orders'] for i, bid in enumerate(row['block_ids'])}
    source_map = {s["source_id"]: s for s in sources}
    page_map = {(p["source_id"], p["page_number"]): p for p in pages}
    repeated = defaultdict(set)
    for block in blocks:
        rule = removable_margin(block, source_map[block["source_id"]], native_dimensions)
        if rule:
            repeated[(block["source_id"], block["raw_text"].strip(" \t\r\n"), rule)].add(block["page_number"])
    cleaned, transforms, quarantine, duplicates, examples = [], [], [], {}, []
    example_types = set()
    for block in blocks:
        text, rules = clean_text(block["raw_text"])
        latex, html = block['raw_latex'], block.get('raw_html')
        fix = fixes.get(block['block_id'])
        if fix:
            if fix['source_sha256'] != source_map[block['source_id']]['sha256'] or fix['before'] != dict(text=text,latex=latex,html=html):
                raise ValueError('Source correction does not match original block bytes')
            text, latex, html = (fix['after'][k] for k in ('text','latex','html'))
            rules.append('SOURCE_CHECKED_FIX')
        before = {"text": block["raw_text"], "latex": block["raw_latex"], "html": block.get("raw_html")}
        rule = removable_margin(block, source_map[block["source_id"]], native_dimensions)
        repeated_key = (block["source_id"], block["raw_text"].strip(" \t\r\n"), rule)
        if rule and len(repeated[repeated_key]) >= 3:
            text = ""
            rules.append(rule)
        reasons = []
        page = page_map[(block["source_id"], block["page_number"])]
        if page["status"] in {"failed", "quarantined"}:
            reasons.append("parent_page_" + page["status"])
        if any(0xE000 <= ord(c) <= 0xF8FF for c in block["raw_text"]) or "\ufffd" in block["raw_text"]:
            reasons.append("unresolved_unicode_glyphs")
        if CONTROLS.search(block["raw_text"]):
            reasons.append("unsafe_control_requires_source_check")
        if block["content_role"] == "chapter_content" and (block["content_type"] in {"formula", "table", "diagram/image", "unknown"} or block["inline_formulas"]):
            reasons.append("critical_math_table_or_visual_review_pending")
        after = {"text": text, "latex": latex, "html": html}
        chash = content_hash(**after)
        key = (block["source_id"], block["page_number"], tuple(block["bbox"] or []), chash, block["content_type"])
        duplicate_of = duplicates.get(key)
        if duplicate_of:
            reasons.append("duplicate_same_source_page_coordinates_content")
        else:
            duplicates[key] = block["block_id"]
        row = {"block_id": block["block_id"], "raw_block_id": block["block_id"],
               "source_id": block["source_id"], "page_number": block["page_number"],
               "cleaned_text": text, "cleaned_latex": latex, "cleaned_html": html,
               "applied_rule_ids": rules, "content_hash": chash,
               "review_status": "quarantined" if reasons else "pending", "corpus_version": None,
               "retrieval_visibility": block["retrieval_visibility"], "content_role": block["content_role"],
               "content_type": block["content_type"], "removed": bool(rule and rule in rules),
               "duplicate_of": duplicate_of, "quarantine_reasons": reasons, "run_id": run_id}
        cleaned.append(row)
        if block['block_id'] in orders:
            row['reading_order'] = orders[block['block_id']]
        if reasons:
            quarantine.append({"block_id": block["block_id"], "source_id": block["source_id"], "page_number": block["page_number"],
                               "reasons": ";".join(reasons), "review_status": "quarantined"})
        evidence = {"run_id": run_id, "transform_id": f"{run_id}:{block['block_id']}", "raw_block_id": block["block_id"],
                    "source_id": block["source_id"], "page_number": block["page_number"], "before": before, "after": after,
                    "rule_ids": rules, "reason": "; ".join(rules) if rules else "No change required",
                    "changed_or_removed": "removed" if row["removed"] else "changed" if before != after else "unchanged",
                    "reviewer": None, "review_status": row["review_status"], "evidence_ref": block["parent_raw_ref"]}
        if before != after:
            transforms.append(evidence)
        label = "removed" if row["removed"] else "quarantined" if reasons else "unchanged_math" if block["inline_formulas"] or block["raw_latex"] else "changed" if before != after else "unchanged"
        if block["content_role"] == "chapter_content" and label not in example_types:
            examples.append({"example_type": label, **evidence})
            example_types.add(label)
        if block["content_role"] == "chapter_content" and (block["inline_formulas"] or block["raw_latex"]) and before == after and "unchanged_math" not in example_types:
            examples.append({"example_type": "unchanged_math", **evidence})
            example_types.add("unchanged_math")
        for selected_rule in rules if block["content_role"] == "chapter_content" else []:
            label = "rule_" + selected_rule
            if label not in example_types:
                examples.append({"example_type": label, **evidence})
                example_types.add(label)
    clean_pages = [{"source_id": p["source_id"], "page_number": p["page_number"], "source_sha256": p["source_sha256"],
                    "raw_output_ref": p["raw_output_ref"], "status": p["status"], "review_status": "pending",
                    "content_role": p["content_role"], "retrieval_visibility": p["retrieval_visibility"], "corpus_version": None,
                    "block_ids": [b["block_id"] for b in cleaned if b["source_id"] == p["source_id"] and b["page_number"] == p["page_number"]]}
                   for p in pages]
    return cleaned, transforms, quarantine, examples, clean_pages


def main():
    inputs = [SOURCES, RAW / "pages.jsonl", RAW / "blocks.jsonl", RAW / "assets_manifest.csv"]
    if CORRECTIONS.exists():
        inputs.append(CORRECTIONS)
    with run_record("05_clean_and_preprocess", inputs) as run:
        sources, pages, blocks = read_csv(SOURCES), read_jsonl(inputs[1]), read_jsonl(inputs[2])
        validate_extraction(sources, pages, blocks, read_csv(inputs[3]))
        dimensions = {}
        for path in {local_path(p["raw_output_ref"]) for p in pages if p["parser_name"] == "PyMuPDF"}:
            for p in read_jsonl(path):
                for parent in pages:
                    if parent["parser_name"] == "PyMuPDF" and local_path(parent["raw_output_ref"]) == path and parent["page_number"] == p["page_number"] and "width" in p:
                        dimensions[(parent["source_id"], parent["page_number"])] = (p["width"], p["height"])
        cleaned, transforms, quarantine, examples, clean_pages = clean_records(pages, blocks, sources, dimensions, run["run_id"])
        output = PHASE / "outputs"
        if (output / "clean_blocks.jsonl").exists() and any(b["review_status"] == "approved" for b in read_jsonl(output / "clean_blocks.jsonl")):
            raise ValueError("Refusing to overwrite an approved release")
        write_jsonl(output / "clean_blocks.jsonl", cleaned)
        write_jsonl(output / "clean_pages.jsonl", clean_pages)
        write_jsonl(output / "transform_log.jsonl", transforms)
        write_jsonl(output / run["run_id"] / "clean_blocks.jsonl", cleaned)
        write_jsonl(output / run["run_id"] / "transform_log.jsonl", transforms)
        write_jsonl(PHASE / "evidence/before_after.jsonl", examples)
        write_csv(output / "quarantine.csv", quarantine, ["block_id", "source_id", "page_number", "reasons", "review_status"])
        write_csv(output / "cleaning_rules.csv", [{**r, "implementation": "05_clean_and_preprocess/code/clean_content.py", "fields": "raw_text derivative only; raw_latex/raw_html unchanged", "reversibility": "raw_block_id + complete before/after log"} for r in RULES],
                  ["rule_id", "reason", "limit", "implementation", "fields", "reversibility"])
        run["counts"] = {"input_blocks": len(blocks), "output_blocks": len(cleaned), "changes": len(transforms), "quarantined": len(quarantine),
                         "removed": sum(b["removed"] for b in cleaned), "rules": dict(Counter(rule for b in cleaned for rule in b["applied_rule_ids"]))}
        assert len(blocks) == len(cleaned) and {b["block_id"] for b in blocks} == {b["raw_block_id"] for b in cleaned}
        run["outputs"] = [output / name for name in ("clean_blocks.jsonl", "clean_pages.jsonl", "transform_log.jsonl", "quarantine.csv", "cleaning_rules.csv")]
        run["outputs"].extend([output / run["run_id"] / "clean_blocks.jsonl", output / run["run_id"] / "transform_log.jsonl", PHASE / "evidence/before_after.jsonl"])
        print(json.dumps(run["counts"], indent=2))


if __name__ == "__main__":
    main()
