"""Initialize only the NCERT-owned loopback PostgreSQL cluster."""
import json
import secrets
import socket
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "00_setup_and_scope/code"))
from pipeline import ROOT, run_record

PHASE = ROOT / "10_embeddings_and_database"
BIN = Path("C:/Program Files/PostgreSQL/18/bin")
DATA = PHASE / "postgres/data"
CONNECTION = PHASE / ".database_connection.json"
PORT = 54329


def command(name, *args):
    # A daemon can inherit PIPE handles after pg_ctl exits; use a real file.
    with (PHASE / "logs/database_setup.log").open("ab") as log:
        return subprocess.run([str(BIN / (name + ".exe")), *map(str, args)], check=True, stdout=log, stderr=log,
                              timeout=120, creationflags=subprocess.CREATE_NO_WINDOW)


def main():
    import psycopg
    with run_record("10_embeddings_and_database") as run:
        if not (BIN / "initdb.exe").is_file():
            raise FileNotFoundError("Installed PostgreSQL 18 initdb not found")
        if not CONNECTION.exists():
            if DATA.exists():
                raise ValueError("Unidentified cluster directory; refusing initialization")
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", PORT))
            CONNECTION.write_text(json.dumps(dict(host="127.0.0.1", port=PORT, user="ncert", password=secrets.token_urlsafe(32), dbname="postgres")), encoding="utf-8")
        config = json.loads(CONNECTION.read_text(encoding="utf-8"))
        if config["host"] != "127.0.0.1" or config["port"] != PORT or config["user"] != "ncert":
            raise ValueError("Connection does not identify the dedicated NCERT cluster")
        if not DATA.exists():
            password = PHASE / "postgres/.init_password"
            password.parent.mkdir(parents=True, exist_ok=True)
            password.write_text(config["password"] + "\n", encoding="utf-8")
            try:
                command("initdb", "-D", DATA, "-U", "ncert", "--auth=scram-sha-256", "--encoding=UTF8", "--locale=C", "--pwfile", password)
            finally:
                password.unlink(missing_ok=True)
        status = subprocess.run([str(BIN / "pg_ctl.exe"), "-D", str(DATA), "status"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        if status.returncode == 3:
            command("pg_ctl", "-D", DATA, "-l", PHASE / "logs/postgres.log", "-o", f"-p {PORT} -h 127.0.0.1", "-w", "start")
        elif status.returncode != 0:
            raise RuntimeError("Cannot inspect dedicated cluster status")
        with psycopg.connect(**{**config, "dbname": "postgres"}, autocommit=True, connect_timeout=5) as db:
            with db.cursor() as cur:
                cur.execute("SHOW data_directory")
                if Path(cur.fetchone()[0]).resolve() != DATA.resolve():
                    raise ValueError("Connected server is outside the NCERT-owned directory")
                cur.execute("SELECT 1 FROM pg_database WHERE datname='ncert_pilot'")
                if not cur.fetchone():
                    cur.execute("CREATE DATABASE ncert_pilot")
        config["dbname"] = "ncert_pilot"
        CONNECTION.write_text(json.dumps(config), encoding="utf-8")
        with psycopg.connect(**config, connect_timeout=5) as db:
            with db.cursor() as cur:
                cur.execute("SELECT current_database(), version()")
                name, version = cur.fetchone()
                cur.execute("SELECT installed_version FROM pg_available_extensions WHERE name='vector'")
                vector = cur.fetchone()
        out = PHASE / "outputs/database_environment.json"
        out.write_text(json.dumps(dict(database=name, version=version, listen="127.0.0.1", port=PORT, dedicated_cluster=True,
                                       pgvector_available=vector is not None, vector_search="exact local NumPy fallback if extension unavailable",
                                       auth="scram-sha-256; generated secret in ignored connection file", run_id=run["run_id"]), indent=2) + "\n", encoding="utf-8")
        run["outputs"].append(out)
        print(json.dumps(dict(database=name, port=PORT, pgvector_available=vector is not None)))


if __name__ == "__main__":
    main()
