"""
E17.1 — Restore de prova em GHA: descarregar .beaba.enc (pasta dl/), decriptar, evidências, verify_restore_weekly.

Nota 2026-04-12: decomissionamento UI legado Clientes/Agendamentos; ver `page_clientes_agendamentos.py`.
CAG Setor 4 (lista no expander «Agendamentos»): contrato em `tests/cag_setor4_ui_contract.py`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.e17_1_crypto import decrypt_file, parse_backup_key  # noqa: E402
from scripts.verify_restore_weekly import run_verify  # noqa: E402


def _pip_check_rc(cwd: Path) -> int:
    return subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        cwd=cwd,
        capture_output=True,
        text=True,
    ).returncode


def main() -> int:
    repo = Path(os.environ.get("GITHUB_WORKSPACE", _REPO)).resolve()
    t0 = time.time()
    start = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    steps: dict = {
        "python_version": sys.version.split()[0],
        "pip_check_rc": _pip_check_rc(repo),
    }
    vital = [
        repo / "scripts",
        repo / "docs" / "governanca" / "telemetry",
        repo / "backups" / "hourly",
    ]
    steps["struct_ok"] = all(p.is_dir() for p in vital)
    steps["requirements_exists"] = (repo / "requirements.txt").is_file()
    steps["env_example_exists"] = (repo / ".env.example").is_file()
    steps["key_configured"] = bool(os.environ.get("BEABA_BACKUP_KEY", "").strip())

    dl = repo / "dl"
    enc_files = list(dl.rglob("*.beaba.enc")) if dl.is_dir() else []
    steps["download_ok"] = len(enc_files) > 0
    steps["decrypt_rc"] = 1
    steps["verify_rc"] = 1
    evidence: dict = {}

    os.environ.setdefault("BEABA_REPO_ROOT", str(repo))

    if enc_files:
        try:
            key = parse_backup_key()
            hourly = repo / "backups" / "hourly"
            hourly.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
            db_out = hourly / f"beaba_gestao_{ts}.db"
            decrypt_file(enc_files[0], db_out, key)
            steps["decrypt_rc"] = 0
            ev_proc = subprocess.run(
                [sys.executable, str(repo / "scripts" / "e17_1_sqlite_evidence.py"), str(db_out)],
                cwd=repo,
                capture_output=True,
                text=True,
            )
            if ev_proc.stdout.strip():
                evidence = json.loads(ev_proc.stdout.strip())
            steps["verify_rc"] = run_verify(repo)
        except Exception as exc:
            evidence = {"error": str(exc)}

    finished = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state = {
        "type": "restore_proof",
        "started_at": start,
        "finished_at": finished,
        "duration_seconds": int(time.time() - t0),
        "git_ref": os.environ.get("GITHUB_REF_NAME", "develop"),
        "git_sha": os.environ.get("GITHUB_SHA", ""),
        "steps": steps,
        "evidence": evidence,
    }
    (repo / "gha_restore_state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    ok = (
        steps["download_ok"]
        and steps["decrypt_rc"] == 0
        and steps["verify_rc"] == 0
        and evidence.get("integrity_check") == "ok"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
