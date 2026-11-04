"""Reconcile stages and gate a local cleaned release on explicit source reviews."""
import json
import hashlib
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "00_setup_and_scope/code"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "04_extract_text_and_ocr/code"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "05_clean_and_preprocess/code"))
from pipeline import ROOT, SOURCES, read_csv, read_jsonl, run_record, sha256, write_csv, write_jsonl
from validate_extraction import validate_extraction
from clean_content import CONTROLS, content_hash, CORRECTIONS

PHASE = ROOT / "06_eda_and_quality"
RAW = ROOT / "04_extract_text_and_ocr/outputs"
CLEAN = ROOT / "05_clean_and_preprocess/outputs"
ANNOTATIONS = PHASE / "outputs/quality_annotations.csv"
BLOCK_REVIEWS = PHASE / "outputs/block_reviews.csv"
REVIEW_POLICY = ROOT / "00_setup_and_scope/config/review_policy.json"
FIELDS = "source_id page_number source_sha256 cleaned_page_hash split review_status reviewer review_date review_method source_check critical_checks evidence_ref notes".split()


def visible_characters(text):
    return "".join(c for c in text if not c.isspace() and not CONTROLS.fullmatch(c))


def validate_cleaning(raw, clean, transforms):
    fixes = {r['block_id']: r for r in json.loads(CORRECTIONS.read_text(encoding='utf-8'))['blocks']} if CORRECTIONS.exists() else {}
    original = {b["block_id"]: b for b in raw}
    cleaned = {b["raw_block_id"]: b for b in clean}
    logged = {t["raw_block_id"]: t for t in transforms}
    if len(original) != len(raw) or len(cleaned) != len(clean) or set(original) != set(cleaned) or len(logged) != len(transforms):
        raise ValueError("Cleaning lost, duplicated or fabricated block lineage")
    changed = set()
    for identifier, before in original.items():
        after = cleaned[identifier]
        fix = fixes.get(identifier)
        checked_fix = bool(fix and fix['review_status']=='approved' and fix['source_sha256']==before.get('source_sha256')
                           and fix['after']==dict(text=after['cleaned_text'],latex=after['cleaned_latex'],html=after['cleaned_html'])
                           and fix['before']==dict(text=before['raw_text'].strip(),latex=before['raw_latex'],html=before.get('raw_html')))
        if not checked_fix and (before["raw_latex"] != after["cleaned_latex"] or before.get("raw_html") != after["cleaned_html"]):
            raise ValueError("Formula/table representation changed without a reviewed correction")
        expected = content_hash(after["cleaned_text"], after["cleaned_latex"], after["cleaned_html"])
        if after["content_hash"] != expected:
            raise ValueError("Cleaned content hash mismatch")
        if after["retrieval_visibility"] != before["retrieval_visibility"] or after["content_role"] != before["content_role"]:
            raise ValueError("Cleaning changed content privacy/scope")
        if not checked_fix and not after["removed"] and visible_characters(before["raw_text"]) != visible_characters(after["cleaned_text"]):
            raise ValueError("Cleaning changed non-whitespace mathematical/scientific characters")
        old = {"text": before["raw_text"], "latex": before["raw_latex"], "html": before.get("raw_html")}
        new = {"text": after["cleaned_text"], "latex": after["cleaned_latex"], "html": after["cleaned_html"]}
        if old != new:
            changed.add(identifier)
            if identifier not in logged or logged[identifier]["before"] != old or logged[identifier]["after"] != new or logged[identifier]["rule_ids"] != after["applied_rule_ids"]:
                raise ValueError("Changed block lacks exact transformation evidence")
    if set(logged) != changed:
        raise ValueError("Transform log and actual changes disagree")
    return len(changed)


def accepted_blocks(clean, annotations, parser_policy, review_policy=None, block_reviews=()):
    allowed = set((review_policy or {}).get("allowed_review_methods", []))
    approved = {}
    reviewed_blocks = {}
    cleaned_by_id = {b["block_id"]: b for b in clean}
    for row in [*annotations, *block_reviews]:
        if row.get("block_id"):
            if row["block_id"] not in cleaned_by_id or row["block_id"] in reviewed_blocks:
                raise ValueError("Unknown/duplicate block review")
            block = cleaned_by_id[row["block_id"]]
            if row["content_hash"] != block["content_hash"] or row["source_id"] != block["source_id"] or int(row["page_number"]) != block["page_number"]:
                raise ValueError("Block review belongs to changed or different content")
            reviewed_blocks[row["block_id"]] = row
        if row["review_status"] != "approved":
            continue
        if not all(row.get(k) for k in ("reviewer", "review_date", "evidence_ref")) or row.get("review_method") not in allowed or row.get("source_check") != "pass" or row.get("critical_checks") != "pass":
            raise ValueError("Approved material lacks authorized source and critical-check evidence")
        if not row.get("block_id"):
            approved[(row["source_id"], int(row["page_number"]))] = row
    if not parser_policy.get("accepted_default_parser") or not parser_policy.get("accepted_ocr_policy"):
        return []
    accepted = []
    for block in clean:
        row = reviewed_blocks.get(block["block_id"], approved.get((block["source_id"], block["page_number"])))
        if not row or row["review_status"] != "approved" or block["content_role"] != "chapter_content" or block["retrieval_visibility"] == "private" or block["removed"]:
            continue
        unresolved = set(block["quarantine_reasons"]) - {"critical_math_table_or_visual_review_pending"}
        if not unresolved and block["content_type"] not in {"unknown", "diagram/image"}:
            accepted.append({**{k: v for k, v in block.items() if k != "run_id"}, "review_status": "approved", "reviewer": row["reviewer"],
                             "review_date": row["review_date"], "review_method": row["review_method"], "review_evidence_ref": row["evidence_ref"],
                             "quarantine_reasons": [], "resolved_quarantine_reasons": block["quarantine_reasons"], "retrieval_visibility": "evidence"})
    return accepted


def main():
    inputs = [SOURCES, RAW / "pages.jsonl", RAW / "blocks.jsonl", RAW / "assets_manifest.csv", CLEAN / "clean_blocks.jsonl", CLEAN / "transform_log.jsonl",
              ROOT / "03_parser_benchmark/outputs/selected_parser_policy.json", PHASE / "outputs/quality_sample_pages.csv"]
    if ANNOTATIONS.exists():
        inputs.append(ANNOTATIONS)
    if CORRECTIONS.exists():
        inputs.append(CORRECTIONS)
    inputs.append(REVIEW_POLICY)
    if BLOCK_REVIEWS.exists():
        inputs.append(BLOCK_REVIEWS)
    with run_record("06_eda_and_quality", inputs) as run:
        sources, pages, raw, clean, transforms = read_csv(SOURCES), read_jsonl(inputs[1]), read_jsonl(inputs[2]), read_jsonl(inputs[4]), read_jsonl(inputs[5])
        validate_extraction(sources, pages, raw, read_csv(inputs[3]))
        changes = validate_cleaning(raw, clean, transforms)
        page_map = {(p["source_id"], p["page_number"]): p for p in pages}
        clean_by_page = defaultdict(list)
        for block in clean:
            clean_by_page[(block["source_id"], block["page_number"])].append(block)
        benchmark = {(r["source_id"], int(r["page_number"])) for r in read_csv(ROOT / "02_pdf_audit/outputs/parser_benchmark_pages.csv")}
        heldout = {(r["source_id"], int(r["page_number"])) for r in read_csv(PHASE / "outputs/quality_sample_pages.csv")}
        if benchmark & heldout or not heldout <= set(page_map):
            raise ValueError("Held-out quality sample overlaps parser development pages or source bounds")
        existing = {(r["source_id"], int(r["page_number"])): r for r in read_csv(ANNOTATIONS)} if ANNOTATIONS.exists() else {}
        annotations = []
        for key, page in page_map.items():
            if page["content_role"] != "chapter_content":
                continue
            items = clean_by_page[key]
            signature = content_hash("".join(b["content_hash"] for b in items), None, None)
            row = {"source_id": key[0], "page_number": key[1], "source_sha256": page["source_sha256"], "cleaned_page_hash": signature,
                   "split": "held_out_quality" if key in heldout else "parser_development" if key in benchmark else "quality_review",
                   "review_status": "pending", "reviewer": "", "review_date": "", "review_method": "",
                   "source_check": "pending", "critical_checks": "pending", "evidence_ref": page["raw_output_ref"], "notes": ""}
            if key in existing:
                prior = existing[key]
                if prior["review_status"] == "approved" and (prior["source_sha256"] != row["source_sha256"] or prior["cleaned_page_hash"] != signature):
                    raise ValueError("Approved review belongs to changed source/cleaned page")
                if prior["cleaned_page_hash"] == signature and prior["source_sha256"] == row["source_sha256"]:
                    row = prior
            annotations.append(row)
        write_csv(ANNOTATIONS, annotations, FIELDS)
        block_reviews = read_csv(BLOCK_REVIEWS) if BLOCK_REVIEWS.exists() else []
        for row in block_reviews:
            if row["source_sha256"] != page_map[(row["source_id"], int(row["page_number"]))]["source_sha256"]:
                raise ValueError("Block review belongs to changed PDF bytes")
        accepted = accepted_blocks(clean, annotations, json.loads(inputs[6].read_text(encoding="utf-8")), json.loads(REVIEW_POLICY.read_text(encoding="utf-8")), block_reviews)
        by_source = []
        for source in sources:
            sid = source["source_id"]
            r = [b for b in raw if b["source_id"] == sid]
            c = [b for b in clean if b["source_id"] == sid]
            by_source.append({"source_id": sid, "subject": source["subject"], "grade": source["grade"], "edition": source["edition"],
                              "source_pages": int(source["pdf_pages"]), "accounted_pages": sum(p["source_id"] == sid for p in pages),
                              "raw_blocks": len(r), "clean_blocks": len(c), "removed_blocks": sum(b["removed"] for b in c),
                              "quarantined_blocks": sum(b["review_status"] == "quarantined" for b in c),
                              "accepted_blocks": sum(b["source_id"] == sid for b in accepted),
                              "private_blocks": sum(b["retrieval_visibility"] == "private" for b in c),
                              "raw_chars": sum(len(b["raw_text"]) for b in r), "clean_chars": sum(len(b["cleaned_text"]) for b in c)})
        assert all(r["source_pages"] == r["accounted_pages"] and r["raw_blocks"] == r["clean_blocks"] for r in by_source)
        output = PHASE / "outputs"
        write_csv(output / "stage_counts.csv", by_source, list(by_source[0]))
        type_counts = []
        for source in sources:
            for kind in sorted({b["content_type"] for b in raw if b["source_id"] == source["source_id"]}):
                group = [b for b in clean if b["source_id"] == source["source_id"] and b["content_type"] == kind]
                type_counts.append({**{k: source[k] for k in ("source_id", "subject", "grade", "edition")},
                                    "content_type": kind, "raw_blocks": len(group), "clean_blocks": len(group),
                                    "removed_blocks": sum(b["removed"] for b in group), "quarantined_blocks": sum(b["review_status"] == "quarantined" for b in group)})
        write_csv(output / "content_type_counts.csv", type_counts, list(type_counts[0]))
        lengths = [len(b["cleaned_text"]) for b in clean]
        summary = {"run_id": run["run_id"], "sources": len(sources), "pages": len(pages), "raw_blocks": len(raw), "clean_blocks": len(clean),
                   "changes": changes, "removed_blocks": sum(b["removed"] for b in clean), "quarantined_blocks": sum(b["review_status"] == "quarantined" for b in clean),
                   "accepted_blocks": len(accepted), "missing_lineage": 0, "raw_content_types": dict(Counter(b["content_type"] for b in raw)),
                   "page_routes": dict(Counter(p["extraction_route"] for p in pages)), "page_roles": dict(Counter(p["content_role"] for p in pages)),
                   "unicode_flags": {"raw_private_use": sum(0xE000 <= ord(c) <= 0xF8FF for b in raw for c in b["raw_text"]),
                                     "clean_private_use": sum(0xE000 <= ord(c) <= 0xF8FF for b in clean for c in b["cleaned_text"]),
                                     "raw_replacement": sum(b["raw_text"].count("\ufffd") for b in raw),
                                     "chapter_content_private_use": sum(0xE000 <= ord(c) <= 0xF8FF for b in raw if b["content_role"] == "chapter_content" for c in b["raw_text"])},
                   "block_length_chars": {"min": min(lengths, default=0), "max": max(lengths, default=0), "median": statistics.median(lengths) if lengths else None},
                   "quality_sample": {"held_out_pages": len(heldout), "development_overlap": 0, "human_reviewed_pages": sum(a["review_status"] == "approved" and a["review_method"] == "human" for a in annotations),
                                      "ai_reviewed_blocks": sum(b["review_method"] == "ai_visual_source_check" for b in accepted), "accuracy": None},
                   "limitations": ["Character invariants do not establish formula semantics", "User-delegated AI reviews are identified separately from human reviews", "No unsupported diagram enters accepted evidence"]}
        (output / "eda_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        release = {"status": "accepted" if accepted else "pending", "corpus_version": None, "run_id": run["run_id"],
                   "record_count": len(accepted), "input_hashes": {p.relative_to(ROOT).as_posix(): sha256(p) for p in inputs},
                   "review_annotations_sha256": sha256(ANNOTATIONS), "publication": "local only; public permissions not granted",
                   "blockers": [] if accepted else ["No eligible approved source/critical checks or accepted parser policy"]}
        if accepted:
            corpus = hashlib.sha256(json.dumps(sorted(accepted, key=lambda b: b["block_id"]), sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            release["corpus_version"] = f"ncert-clean-{corpus[:16]}"
            for block in accepted:
                block["corpus_version"] = release["corpus_version"]
            accepted_path = output / release["corpus_version"] / "accepted_blocks.jsonl"
            if accepted_path.exists() and read_jsonl(accepted_path) != accepted:
                raise ValueError("Refusing to change a frozen accepted release")
            write_jsonl(accepted_path, accepted)
            release.update(artifact_path=accepted_path.relative_to(ROOT).as_posix(), artifact_sha256=sha256(accepted_path))
            run["outputs"].append(accepted_path)
        (output / "clean_release_manifest.json").write_text(json.dumps(release, indent=2) + "\n", encoding="utf-8")
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 2, figsize=(12, 4), layout="constrained")
        chapters = [r for r in by_source if r["raw_blocks"] and next(s for s in sources if s["source_id"] == r["source_id"])["chapter_title"] != "Prelims"]
        labels = [f"{r['subject']} {r['grade']}" for r in chapters]
        axes[0].bar(labels, [r["raw_chars"] for r in chapters], label="Raw")
        axes[0].bar(labels, [r["clean_chars"] for r in chapters], alpha=0.65, label="Clean")
        axes[0].set(title="Draft text lengths, including private/excluded pages", ylabel="Characters")
        axes[0].legend(); axes[0].tick_params(axis="x", rotation=20)
        axes[1].hist(lengths, bins=30)
        axes[1].set(title="All cleaned blocks; no accuracy/acceptance claim", xlabel="Characters per block", ylabel="Blocks")
        figure = PHASE / "figures/content_quality.png"
        figure.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(figure, dpi=130); plt.close(fig)
        run["outputs"].extend([output / "stage_counts.csv", output / "content_type_counts.csv", output / "eda_summary.json", output / "clean_release_manifest.json", ANNOTATIONS, figure])
        run["counts"] = summary
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
