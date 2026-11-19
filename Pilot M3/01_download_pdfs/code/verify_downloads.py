"""Reopen every selected PDF and reconcile it against scope and saved hashes."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "00_setup_and_scope/code"))
from pipeline import SCOPE, SOURCES, read_csv, run_record
from validate_manifests import validate_scope, validate_sources


if __name__ == "__main__":
    with run_record("01_download_pdfs", [SCOPE, SOURCES]) as run:
        sources = validate_sources(validate_scope(read_csv(SCOPE)), read_csv(SOURCES))
        print(f"Verified {len(sources)} PDFs, {sum(int(s['pdf_pages']) for s in sources)} physical pages")
