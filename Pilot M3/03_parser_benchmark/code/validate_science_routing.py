"""Check the shared router against a full Grade 9 chapter parsed by MinerU."""
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "00_setup_and_scope/code"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "04_extract_text_and_ocr/code"))
from pipeline import ROOT, run_record, sha256, write_csv
from benchmark_parsers import CLI, verify_page_set
from extract_content import leaves
from hybrid_route_test import native_features, subject_route

PHASE = ROOT / "03_parser_benchmark"
PDF = PHASE / "evidence/routing_validation/iesc108.pdf"
MODEL_FILES = PHASE / "outputs/mineru_model_files.json"
ROUTER = PHASE / "code/hybrid_route_test.py"


def main():
    with run_record("03_parser_benchmark", [PDF, MODEL_FILES, ROUTER]) as run:
        source_hash = sha256(PDF)
        with pymupdf.open(PDF) as doc:
            if "Journey Inside" not in doc[0].get_text() or not any("Grade 9" in page.get_text() for page in doc):
                raise ValueError("Official chapter title/grade does not match the validation source")
            features = {n: native_features(p)[1] for n, p in enumerate(doc, 1)}
        python = CLI.with_name("python.exe")
        version = subprocess.check_output([str(python), "-c", "import importlib.metadata; print(importlib.metadata.version('mineru'))"], text=True).strip()
        env = {**os.environ, "MINERU_HOME": str(ROOT / ".mineru-state"), "MINERU_MODEL_ONNX_DEVICE": "cpu", "MINERU_MODEL_SOURCE": "local"}
        reference = {}
        for offset in range(0, len(features), 8):
            numbers = list(range(offset + 1, min(offset + 8, len(features)) + 1))
            folder = PHASE / "evidence/routing_validation" / f"{source_hash[:16]}-{version}-{numbers[0]}-{numbers[-1]}"
            folder.mkdir(parents=True, exist_ok=True)
            archive, receipt, log = folder / "reference.zip", folder / "receipt.json", folder / "mineru.log"
            request = dict(source_sha256=source_hash, pages=numbers, parser_version=version, model_manifest_sha256=sha256(MODEL_FILES), tier="basic", ocr_mode="auto")
            if receipt.exists():
                saved = json.loads(receipt.read_text(encoding="utf-8"))
                if saved["request"] != request or saved["sha256"] != sha256(archive):
                    raise ValueError("Changed validation parser cache")
            else:
                with log.open("w", encoding="utf-8") as stream:
                    subprocess.run([str(python), "-c", "from mineru.kit.main import main; main()", "parse", str(PDF), "--pages", ",".join(map(str, numbers)),
                                    "--tier", "basic", "--ocr-mode", "auto", "--format", "zip", "-o", str(archive)], env=env, stdout=stream, stderr=subprocess.STDOUT,
                                   check=True, timeout=1800, creationflags=subprocess.CREATE_NO_WINDOW)
                receipt.write_text(json.dumps(dict(request=request, sha256=sha256(archive)), indent=2) + "\n", encoding="utf-8")
            with zipfile.ZipFile(archive) as bundle:
                middle = json.loads(bundle.read("middle_json.json"))
            verify_page_set(middle, numbers)
            for page in middle["pages"]:
                nodes = list(leaves(page["blocks"]))
                reference[page["page_idx"] + 1] = dict(formulas=sum(n.get("type") in {"equation", "equation_inline"} for n in nodes),
                                                       tables=sum(n.get("type") == "table" for n in nodes))
            run["outputs"].extend([archive, receipt, log])
            print("Grade 9 reference pages", numbers, "checked", flush=True)
        rows = [dict(page_number=n, route=subject_route("ncert-en-science-g9-routing-check", f), **f,
                     reference_formulas=reference[n]["formulas"], reference_tables=reference[n]["tables"]) for n, f in features.items()]
        missed = [r["page_number"] for r in rows if r["route"] == "pymupdf" and (r["reference_formulas"] or r["reference_tables"])]
        out = PHASE / "outputs/hybrid"
        write_csv(out / "grade9_page_routes.csv", rows, list(rows[0]))
        summary = dict(run_id=run["run_id"], source_url="https://ncert.nic.in/textbook/pdf/iesc108.pdf", source_sha256=source_hash,
                       title="Journey Inside the Atom", grade=9, pages=len(rows), pymupdf_version=pymupdf.VersionBind, mineru_version=version,
                       mineru_routed_pages=sum(r["route"] == "mineru" for r in rows), missed_reference_formula_or_table_pages=missed,
                       gate="pass" if not missed else "fail", limitation="MinerU structural detections are the reference; formulas missed by both parsers are not measured")
        path = out / "grade9_routing_validation.json"
        path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        run["outputs"].extend([out / "grade9_page_routes.csv", path]); run["counts"] = summary
        print(json.dumps(summary))
        if missed:
            raise ValueError(f"Do not run the new extraction route yet: missed source pages {missed}")


if __name__ == "__main__":
    main()
