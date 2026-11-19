"""Validate complete physical-page accounting, block/asset lineage and draft visibility."""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "00_setup_and_scope/code"))
from pipeline import ROOT, SOURCES, local_path, read_csv, read_jsonl, run_record, sha256

PHASE = ROOT / "04_extract_text_and_ocr"
PAGE_FIELDS = "source_id source_sha256 page_number printed_page_label run_id parser_name parser_version engine model_revision extraction_route ocr_used status warnings raw_output_ref".split()
BLOCK_FIELDS = "block_id source_id page_number block_order bbox coordinate_system section_hint content_type raw_text raw_markdown raw_latex asset_ids parent_raw_ref review_status".split()
CONTENT_TYPES = {"heading", "prose", "formula", "table", "diagram/image", "question", "answer", "worked_example", "unknown"}


def validate_extraction(sources, pages, blocks, assets):
    by_id = {s["source_id"]: s for s in sources}
    expected = {(s["source_id"], n) for s in sources for n in range(1, int(s["pdf_pages"]) + 1)}
    page_ids = [(p["source_id"], p["page_number"]) for p in pages]
    if len(page_ids) != len(set(page_ids)) or set(page_ids) != expected:
        raise ValueError("Physical pages omitted, duplicated or out of bounds")
    page_map = dict(zip(page_ids, pages))
    checked = {}
    for page in pages:
        if set(PAGE_FIELDS) - page.keys():
            raise ValueError("Missing page provenance fields")
        if page["source_sha256"] != by_id[page["source_id"]]["sha256"]:
            raise ValueError("Wrong PDF hash")
        if page["status"] not in {"extracted", "accepted_empty", "failed", "quarantined"}:
            raise ValueError("Invalid page status")
        if page["review_status"] not in {"pending", "quarantined"} or page["retrieval_visibility"] not in {"private", "not_accepted"}:
            raise ValueError("Draft extraction cannot approve/open content")
        if page["confidence"] is not None or (page["ocr_used"] is not None and type(page["ocr_used"]) is not bool):
            raise ValueError("Invalid confidence or OCR provenance")
        if page["parser_name"] == "MinerU" and page["ocr_used"] is not None:
            raise ValueError("MinerU batch OCR observations cannot become per-page claims")
        path = local_path(page["raw_output_ref"])
        if not path.is_file():
            raise ValueError("Missing native page output")
        if path not in checked:
            checked[path] = sha256(path)
        if checked[path] != page["raw_output_sha256"]:
            raise ValueError("Changed native output")
    ids, orders = set(), set()
    asset_map = {a["asset_id"]: a for a in assets}
    if len(asset_map) != len(assets):
        raise ValueError("Duplicate assets")
    for block in blocks:
        if set(BLOCK_FIELDS) - block.keys() or block["block_id"] in ids:
            raise ValueError("Missing block fields or duplicate block ID")
        ids.add(block["block_id"])
        key = (block["source_id"], block["page_number"])
        if key not in page_map or block["source_sha256"] != page_map[key]["source_sha256"]:
            raise ValueError("Invalid block/source/page lineage")
        order = (*key, block["block_order"])
        if order in orders:
            raise ValueError("Duplicate block order")
        orders.add(order)
        if block["content_type"] not in CONTENT_TYPES or not isinstance(block["raw_text"], str):
            raise ValueError("Invalid block representation")
        if block["retrieval_visibility"] != page_map[key]["retrieval_visibility"] or block["review_status"] != page_map[key]["review_status"]:
            raise ValueError("Block visibility/review differs from parent page")
        bbox = block["bbox"]
        if bbox is not None and (len(bbox) != 4 or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in bbox)
                                 or bbox[0] > bbox[2] or bbox[1] > bbox[3]):
            raise ValueError("Invalid bounding box")
        if block["parent_raw_ref"] != page_map[key]["raw_output_ref"]:
            raise ValueError("Block raw reference differs from parent")
        path = local_path(block["parent_raw_ref"])
        if path not in checked:
            checked[path] = sha256(path)
        if checked[path] != block["raw_output_sha256"] or checked[path] != page_map[key]["raw_output_sha256"]:
            raise ValueError("Changed native output")
        for aid in block["asset_ids"]:
            if aid not in asset_map or asset_map[aid]["source_id"] != key[0] or int(asset_map[aid]["page_number"]) != key[1]:
                raise ValueError("Missing/cross-page asset")
        if block["content_role"] == "private_answer" and (block["retrieval_visibility"] != "private" or block["content_type"] != "answer"):
            raise ValueError("Answer material escaped private handling")
    for asset in assets:
        if asset["block_id"] not in ids or sha256(local_path(asset["local_path"])) != asset["sha256"]:
            raise ValueError("Invalid asset/block/hash lineage")
    json.dumps([pages, blocks], allow_nan=False)
    return {"pages": len(pages), "blocks": len(blocks), "assets": len(assets)}


if __name__ == "__main__":
    inputs = [SOURCES, PHASE / "outputs/pages.jsonl", PHASE / "outputs/blocks.jsonl", PHASE / "outputs/assets_manifest.csv"]
    with run_record("04_extract_text_and_ocr", inputs):
        print(validate_extraction(read_csv(SOURCES), read_jsonl(inputs[1]), read_jsonl(inputs[2]), read_csv(inputs[3])))
