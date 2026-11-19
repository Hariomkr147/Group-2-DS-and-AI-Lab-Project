"""Acquire the selected official PDFs; verify existing bytes instead of replacing them."""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "00_setup_and_scope/code"))
from pipeline import ROOT, SCOPE, SOURCES, local_path, now, read_csv, run_record, write_csv
from validate_manifests import SOURCE_FIELDS, check_identity, inspect_pdf, validate_scope, validate_sources

FAILURES = ROOT / "01_download_pdfs/manifests/download_failures.csv"
FAILURE_FIELDS = "run_id source_id source_url attempted_at error retry_decision final_disposition".split()
RIGHTS = ("NCERT copyrighted; local textbook/reference copy only. No public PDF/excerpt/software "
          "redistribution approved. See https://ncert.nic.in/textbook.php and PDF prelims p2; "
          "permission review required before retrieval-system/public-content release.")


def acquire(row, transport=None):
    destination = local_path(row["local_path"])
    if destination.exists():
        raise ValueError(f"Unmanifested file exists; inspect before recovery: {row['local_path']}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    curl = transport or shutil.which("curl.exe") or shutil.which("curl")
    if not curl:
        raise RuntimeError("curl not available; install it or use the documented environment")
    with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".part", delete=False) as stream:
        temp = Path(stream.name)
    try:
        response = subprocess.run([
            curl, "--silent", "--show-error", "--fail", "--location",
            "--proto", "=https", "--proto-redir", "=https", "--retry", "2", "--retry-all-errors",
            "--connect-timeout", "15", "--max-time", "90", "--user-agent", "Mozilla/5.0",
            "--output", str(temp), "--write-out", "%{http_code}\n%{content_type}\n%{url_effective}",
            row["source_url"]], capture_output=True, text=True, timeout=300)
        if response.returncode:
            raise RuntimeError(f"curl {response.returncode}: {response.stderr.strip()}")
        status, content_type, effective_url = response.stdout.strip().splitlines()
        if status != "200" or content_type.split(";")[0].lower() not in {"application/pdf", "application/octet-stream"}:
            raise ValueError(f"Unexpected HTTP response: {status} {content_type}")
        if urlsplit(effective_url).hostname not in {"ncert.nic.in", "www.ncert.nic.in"}:
            raise ValueError("Download redirected outside official NCERT hosts")
        info = inspect_pdf(temp)
        check_identity(row, info)
        # A hard link publishes the complete verified file atomically and refuses an existing target.
        os.link(temp, destination)
        return {**{k: row[k] for k in SOURCE_FIELDS if k in row},
                **{k: info[k] for k in ("sha256", "bytes", "pdf_pages")},
                "downloaded_at": now(), "rights_note": RIGHTS}
    finally:
        temp.unlink(missing_ok=True)


def main():
    inputs = [SCOPE, *([SOURCES] if SOURCES.exists() else [])]
    with run_record("01_download_pdfs", inputs) as run:
        scope = validate_scope(read_csv(SCOPE))
        sources = read_csv(SOURCES) if SOURCES.exists() else []
        validate_sources(scope, sources, require_complete=False)
        existing = {r["source_id"] for r in sources}
        failures = read_csv(FAILURES) if FAILURES.exists() else []
        run["downloaded"] = 0
        run["reused_verified"] = len(existing)
        for row in scope:
            if row["included"] != "yes" or row["source_id"] in existing:
                continue
            try:
                result = acquire(row)
                sources.append(result)
                write_csv(SOURCES, sources, SOURCE_FIELDS)
                run["downloaded"] += 1
                print(f"Verified {row['source_id']}: {result['pdf_pages']} pages")
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
                failures.append({"run_id": run["run_id"], "source_id": row["source_id"],
                                 "source_url": row["source_url"], "attempted_at": now(),
                                 "error": str(exc), "retry_decision": "configured --retry 2 --retry-all-errors; rerun after inspection",
                                 "final_disposition": "not included in verified manifest"})
                run["failures"].append(f"{row['source_id']}: {exc}")
                write_csv(FAILURES, failures, FAILURE_FIELDS)
        if not FAILURES.exists():
            write_csv(FAILURES, [], FAILURE_FIELDS)
        run["outputs"] = [SOURCES, FAILURES, *[local_path(r["local_path"]) for r in sources]]
        if run["failures"]:
            return 1
        validate_sources(scope, sources)
        hashes = {}
        for row in sources:
            hashes.setdefault(row["sha256"], []).append(row["source_id"])
        run["duplicate_hash_groups"] = [ids for ids in hashes.values() if len(ids) > 1]
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
