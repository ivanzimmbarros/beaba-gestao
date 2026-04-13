#!/usr/bin/env python3
"""
E17 — Gera `tests/E17_RESTORE_CERTIFICATE.txt`: saída de pytest (restore + verify)
e prova roundtrip backup SQLite → BEA1 (AES-GCM) → decrypt → PRAGMA integrity_check.

Inclui o teste de contrato CAG Setor 4 (listagem dentro do expander «Agendamentos») para
alinhamento pós-recuperação com a UI versionada em git.

Uso (na raiz do repo): python scripts/generate_e17_restore_certificate.py
"""

from __future__ import annotations

import base64
import io
import json
import logging
import os
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_CERT_REL = Path("tests") / "E17_RESTORE_CERTIFICATE.txt"


def _pytest_block() -> str:
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_restore_sqlite.py",
            "tests/test_sqlite_backup_verify.py",
            "tests/test_clientes_agendamentos_page.py::test_cag_setor4_lista_obrigatoriamente_dentro_expander_agendamentos",
            "-v",
            "--tb=short",
        ],
        cwd=_REPO,
        capture_output=True,
        text=True,
        env=os.environ | {"PYTHONPATH": str(_REPO)},
    )
    buf = io.StringIO()
    buf.write(f"exit_code={r.returncode}\n")
    buf.write("--- stdout ---\n")
    buf.write(r.stdout or "")
    buf.write("\n--- stderr ---\n")
    buf.write(r.stderr or "")
    buf.write("\n")
    return buf.getvalue()


def _roundtrip_block() -> str:
    key_b64 = base64.b64encode(b"x" * 32).decode("ascii")
    lines: list[str] = []

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        root = Path(td)
        (root / "docs" / "governanca" / "telemetry").mkdir(parents=True)
        (root / "docs" / "governanca" / "telemetry" / "backup_dr_history.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "runs": [
                        {
                            "id": "cert-baseline",
                            "type": "backup",
                            "snapshot_table_counts": {"clientes": 1},
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (root / "backups" / "hourly").mkdir(parents=True)
        # Fonte do backup (run_backup copia data/beaba_gestao.db) — prepare_ci_db só actua com GITHUB_ACTIONS=true
        data_db = root / "data" / "beaba_gestao.db"
        data_db.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(data_db)
        conn.execute("CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO clientes DEFAULT VALUES")
        conn.commit()
        conn.close()

        old_root = os.environ.get("BEABA_REPO_ROOT")
        old_cloud = os.environ.get("BEABA_BACKUP_CLOUD_QUEUE")
        old_ci = os.environ.get("BEABA_CI_PREPARE_EMPTY_DB")
        old_key = os.environ.get("BEABA_BACKUP_KEY")
        try:
            os.environ["BEABA_REPO_ROOT"] = str(root)
            os.environ["BEABA_BACKUP_CLOUD_QUEUE"] = "0"
            os.environ["BEABA_CI_PREPARE_EMPTY_DB"] = "1"
            os.environ["BEABA_BACKUP_KEY"] = key_b64

            sys.path.insert(0, str(_REPO))
            from scripts.backup_sqlite_hourly import run_backup  # noqa: E402
            from scripts.e17_1_crypto import MAGIC, decrypt_file, encrypt_file, parse_backup_key  # noqa: E402
            from scripts.sqlite_backup_verify import verify_backup_destination  # noqa: E402

            rc_backup = run_backup(root, keep=8, copy_to_cloud_queue=False)
            logging.shutdown()
            lines.append(f"(A) run_backup (cópia integral API) rc={rc_backup}")
            hourly = root / "backups" / "hourly"
            dbs = sorted(hourly.glob("beaba_gestao_*.db"), key=lambda p: p.stat().st_mtime)
            if not dbs:
                lines.append("ERRO: nenhum .db em backups/hourly após run_backup")
                return "\n".join(lines)
            latest = dbs[-1]
            ok_v, msg_v = verify_backup_destination(latest)
            lines.append(f"(B) verify_backup_destination (header + quick_check) ok={ok_v} msg={msg_v!r}")

            enc = root / "certificado.beaba.enc"
            encrypt_file(latest, enc, parse_backup_key())
            hdr = enc.read_bytes()[:4]
            lines.append(f"(C) encrypt_file AES-256-GCM → magic==BEA1: {hdr == MAGIC} ({hdr!r})")

            dec = root / "restaurado.db"
            decrypt_file(enc, dec, parse_backup_key())
            lines.append("(D) decrypt_file → restaurado.db escrito")

            conn = sqlite3.connect(dec)
            try:
                ic = conn.execute("PRAGMA integrity_check").fetchone()[0]
                fk = conn.execute("PRAGMA foreign_key_check").fetchall()
            finally:
                conn.close()
            lines.append(f"(E) PRAGMA integrity_check={ic!r} foreign_key_violations={len(fk)}")
            lines.append(
                "CONCLUSÃO: backup gerado, ficheiro encriptado BEA1, decrypt OK, integridade SQLite ok."
                if ic == "ok" and len(fk) == 0 and ok_v
                else "CONCLUSÃO: rever passos com falha acima."
            )
        finally:
            if old_root is None:
                os.environ.pop("BEABA_REPO_ROOT", None)
            else:
                os.environ["BEABA_REPO_ROOT"] = old_root
            if old_cloud is None:
                os.environ.pop("BEABA_BACKUP_CLOUD_QUEUE", None)
            else:
                os.environ["BEABA_BACKUP_CLOUD_QUEUE"] = old_cloud
            if old_ci is None:
                os.environ.pop("BEABA_CI_PREPARE_EMPTY_DB", None)
            else:
                os.environ["BEABA_CI_PREPARE_EMPTY_DB"] = old_ci
            if old_key is None:
                os.environ.pop("BEABA_BACKUP_KEY", None)
            else:
                os.environ["BEABA_BACKUP_KEY"] = old_key

    return "\n".join(lines)


def main() -> int:
    iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    parts = [
        "=" * 72,
        "E17 — CERTIFICADO DE RESTORE / BACKUP ENCRIPTADO (BeaBa Gestão)",
        f"Emitido em (UTC): {iso}",
        f"Repositório: {_REPO}",
        "",
        "1) Pytest: tests/test_restore_sqlite.py + tests/test_sqlite_backup_verify.py",
        "-" * 72,
        _pytest_block(),
        "",
        "2) Roundtrip local (CI mirror): prepare DB → backup → encrypt → decrypt → integridade",
        "-" * 72,
        _roundtrip_block(),
        "",
        "3) Secret em GitHub Actions (repositório)",
        "-" * 72,
        "BEABA_BACKUP_KEY — base64(32 bytes) ou hex(64 chars). Não usar GPG neste trilho.",
        "Ver: .github/workflows/backup_encrypt_callable.yml (comentário no topo).",
        "=" * 72,
    ]
    out_path = _REPO / _CERT_REL
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"Escrito: {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
