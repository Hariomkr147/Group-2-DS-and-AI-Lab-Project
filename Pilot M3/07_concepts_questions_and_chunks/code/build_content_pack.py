"""Build the bounded reviewed pilot; preserve source text and separate scoring keys."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "00_setup_and_scope/code"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "06_eda_and_quality/code"))
from pipeline import ROOT, SOURCES, local_path, read_csv, read_jsonl, run_record, sha256, write_csv, write_jsonl
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_passages import build as build_passages
from extract_ncert_questions import page_offsets

PHASE = ROOT / "07_concepts_questions_and_chunks"
ACCEPTED_CHUNKS = PHASE / "outputs/accepted_chunks.jsonl"
MODEL_ID = "BAAI/bge-small-en-v1.5"
REVISION = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
MODEL_DIR = ROOT / "10_embeddings_and_database/models/bge-small-en-v1.5" / REVISION
PRIVATE_FIELDS = {"gold_answer", "acceptable_forms", "solution_steps", "answer", "answer_source", "derivation_method"}


def resolve_group(group, blocks):
    selected = sorted((b for b in blocks if b["source_id"] == group["source_id"] and b["page_number"] == group["page"]
                       and int(b["block_id"].rsplit(":b", 1)[1]) in group["orders"]), key=lambda b: int(b["block_id"].rsplit(":b", 1)[1]))
    if len(selected) != len(group["orders"]) or any(b["review_status"] != "approved" or b["retrieval_visibility"] != "evidence"
                                                  or b["quarantine_reasons"] or b["content_role"] != "chapter_content" for b in selected):
        raise ValueError("Group contains missing, private or unapproved source blocks")
    return selected


def validate_pack(concepts, chunks, questions, answers, blocks):
    for collection, key in [(concepts, "concept_id"), (chunks, "chunk_id"), (questions, "question_id"), (answers, "question_id")]:
        if len(collection) != len({r[key] for r in collection}):
            raise ValueError("Duplicate content identity")
    ids = {c["concept_id"] for c in concepts}
    approved = {b["block_id"] for b in blocks}
    if {q["question_id"] for q in questions} != {a["question_id"] for a in answers}:
        raise ValueError("Question/scoring alignment differs")
    for c in chunks:
        if not set(c["concept_ids"]) <= ids or not set(c["block_ids"]) <= approved or c["token_count"] > 400:
            raise ValueError("Unresolved chunk lineage or token bound")
    for q in questions:
        if PRIVATE_FIELDS & q.keys() or not set(q["concept_ids"]) <= ids or not set(q["source_block_ids"]) <= approved:
            raise ValueError("Private answer leakage or unresolved question lineage")


def main():
    release_path = ROOT / "06_eda_and_quality/outputs/clean_release_manifest.json"
    decisions = PHASE / "config/concept_decisions.json"
    release = json.loads(release_path.read_text(encoding="utf-8"))
    if release["status"] != "accepted":
        raise ValueError("Accepted cleaned release required")
    accepted = local_path(release["artifact_path"])
    if sha256(accepted) != release["artifact_sha256"]:
        raise ValueError("Accepted cleaned release changed")
    if sha256(SOURCES) != release["input_hashes"][SOURCES.relative_to(ROOT).as_posix()]:
        raise ValueError("Source manifest differs from the accepted release")
    tokenizer_files = [MODEL_DIR / name for name in ["tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "vocab.txt"]]
    all_clean = ROOT / "05_clean_and_preprocess/outputs/clean_blocks.jsonl"
    roles_path = PHASE / "outputs/block_roles.jsonl"
    bank_path = PHASE / "outputs/ncert_bank_manifest.json"
    bank = json.loads(bank_path.read_text(encoding="utf-8"))
    if bank["input_hashes"][all_clean.relative_to(ROOT).as_posix()] != sha256(all_clean) or bank["artifact_hashes"][roles_path.relative_to(ROOT).as_posix()] != sha256(roles_path):
        raise ValueError("Question/example split belongs to a different extraction")
    section_map_path = PHASE / "config/section_concepts.json"
    corrections_path = ROOT / "05_clean_and_preprocess/config/source_corrections.json"
    builder_path = Path(__file__).resolve().parent / "build_passages.py"
    inputs = [release_path, accepted, decisions, SOURCES, all_clean, roles_path, bank_path, section_map_path, corrections_path, builder_path, *tokenizer_files]
    with run_record("07_concepts_questions_and_chunks", inputs) as run:
        from tokenizers import Tokenizer
        tokenizer = Tokenizer.from_file(str(MODEL_DIR / "tokenizer.json"))
        tokenizer.no_truncation()
        tokenizer.no_padding()
        blocks = read_jsonl(accepted)
        roles = {r["block_id"]: r for r in read_jsonl(roles_path)}
        clean = read_jsonl(all_clean)
        if set(roles) != {b["block_id"] for b in clean}:
            raise ValueError("Every cleaned block must have exactly one role disposition")
        sources = {s["source_id"]: s for s in read_csv(SOURCES)}
        proposals = json.loads(decisions.read_text(encoding="utf-8"))
        version = "ncert-pilot-" + hashlib.sha256("|".join(sha256(p) for p in [accepted, decisions, all_clean, roles_path, section_map_path, corrections_path, builder_path]).encode()).hexdigest()[:16]
        concepts = []
        for proposal in proposals:
            if proposal["review_status"] != "approved":
                raise ValueError("Unapproved concept decision")
            selected = [b for g in proposal["groups"] for b in resolve_group(g, blocks)]
            if any(roles[b["block_id"]]["role"] != "content" for b in selected):
                raise ValueError("A curated explanation overlaps a question/example/answer; review that group")
            concept = {k: v for k, v in proposal.items() if k != "groups"}
            concept.update(source_block_ids=[b["block_id"] for b in selected], book_source_ids=sorted({b["source_id"] for b in selected}),
                           evidence_refs=sorted({b["review_evidence_ref"] for b in selected}), corpus_version=version)
            concepts.append(concept)
        # Evidence passages are built automatically from every chapter; see build_passages.py for the rules.
        corrections = json.loads(corrections_path.read_text(encoding="utf-8"))
        unresolved = {r.get("block_id") for r in corrections["currency_unresolved"] if r.get("block_id")}
        section_map = {k: v for k, v in json.loads(section_map_path.read_text(encoding="utf-8")).items() if not k.startswith("_")}
        if not {c for m in section_map.values() for c in m.values()} <= {c["concept_id"] for c in concepts}:
            raise ValueError("Section map names an unknown pilot concept")
        raw_order = {b["block_id"]: b["block_order"] for b in read_jsonl(ROOT / "04_extract_text_and_ocr/outputs/blocks.jsonl")}
        count = lambda text: len(tokenizer.encode(text, add_special_tokens=True).ids)
        chunks, exclusions, section_concepts = build_passages(clean, roles, sources, raw_order, count, section_map,
                                                              page_offsets(), unresolved, version, REVISION)
        concepts.extend(section_concepts)
        questions, answers = [], []
        allowed = [b for b in clean if roles[b["block_id"]]["role"] == "content"]
        validate_pack(concepts, chunks, questions, answers, allowed)
        if any(roles[b]["role"] != "content" for c in chunks for b in c["block_ids"]) or any(set(c["block_ids"]) & unresolved for c in chunks):
            raise ValueError("Question/example/answer or unresolved currency escaped into evidence passages")
        if len({c["chunk_id"] for c in chunks}) != len(chunks) or len({b for c in chunks for b in c["block_ids"]}) != sum(len(c["block_ids"]) for c in chunks):
            raise ValueError("A block was used in two passages")
        candidates = chunks
        out = PHASE / "outputs"
        artifacts = {"concepts.jsonl": concepts, "chunks.jsonl": candidates, "accepted_chunks.jsonl": chunks, "questions.jsonl": questions, "answers_private.jsonl": answers}
        for name, rows in artifacts.items():
            write_jsonl(out / name, rows)
        hierarchy = [{"parent_id": b, "child_id": c["concept_id"], "relation_type": "contains", "review_status": "approved"}
                     for c in concepts for b in c["book_source_ids"]]
        links = [{"chunk_id": c["chunk_id"], "concept_id": k} for c in candidates for k in c["concept_ids"]]
        block_links = [{"chunk_id": c["chunk_id"], "block_id": k} for c in candidates for k in c["block_ids"]]
        support = [{"concept_id": c["concept_id"], "subject": c["subject"], "grade": c["grade"], "supported_objective": c["learning_objective"],
                    "approved_questions": sum(c["concept_id"] in q["concept_ids"] for q in questions),
                    "evidence_chunks": sum(c["concept_id"] in x["concept_ids"] for x in chunks), "support_status": "bounded_pilot_only",
                    "exclusions": "Figures, tables, question boxes and unresolved symbols are excluded by rule; KT mapping deferred"} for c in concepts]
        for name, rows in [("hierarchy_edges.csv", hierarchy), ("chunk_concepts.csv", links), ("chunk_blocks.csv", block_links), ("content_support_matrix.csv", support)]:
            write_csv(out / name, rows, list(rows[0]))
        paths = [out / name for name in [*artifacts, "hierarchy_edges.csv", "chunk_concepts.csv", "chunk_blocks.csv", "content_support_matrix.csv"]]
        manifest = dict(status="accepted_local_pilot", corpus_version=version, cleaned_release=release["corpus_version"], run_id=run["run_id"],
                        concepts=len(concepts), chunks=len(chunks), candidate_chunks=len(candidates), accepted_chunks=len(chunks),
                        candidate_status_counts={"approved": len(chunks), "pending": 0, "quarantined": 0},
                        excluded_blocks_by_rule=dict(sorted(exclusions.items())), pilot_concepts=len(proposals), section_concepts=len(section_concepts),
                        all_non_question_content_processed=True, questions=len(questions), private_answers=len(answers),
                        question_bank_manifest="07_concepts_questions_and_chunks/outputs/ncert_bank_manifest.json",
                        accepted_chunk_path=ACCEPTED_CHUNKS.relative_to(ROOT).as_posix(),
                        tokenizer_model=MODEL_ID, tokenizer_revision=REVISION, tokenizer_file_hashes={p.name: sha256(p) for p in tokenizer_files},
                        document_format="source blocks joined in reading order under their section heading; whitespace-only LaTeX and ligature normalisation; no metadata prefix",
                        passage_method="automatic_section_merge (build_passages.py)", target_max_tokens=400, model_max_tokens=512,
                        max_actual_tokens=max(c["token_count"] for c in chunks), review_method="automatic rule gate (passages, section map); pilot concept records from earlier AI source checks",
                        independent_human_review=False, skill_mapping="deferred_by_user", publication="local only",
                        artifact_hashes={p.relative_to(ROOT).as_posix(): sha256(p) for p in paths})
        manifest_path = out / "content_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        run["outputs"].extend([*paths, manifest_path]); run["counts"] = {k: manifest[k] for k in ["concepts", "chunks", "questions", "private_answers", "max_actual_tokens"]}
        print(json.dumps(run["counts"]))


if __name__ == "__main__":
    main()
