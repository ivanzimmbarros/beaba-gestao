"""E17 — scripts de backup e verificação semanal (subprocess + repo isolado)."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BACKUP_SCRIPT = REPO / "scripts" / "backup_sqlite_hourly.py"
VERIFY_SCRIPT = REPO / "scripts" / "verify_restore_weekly.py"


def _run_script(script: Path, repo_root: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["BEABA_REPO_ROOT"] = str(repo_root)
    env["BEABA_BACKUP_CLOUD_QUEUE"] = "0"
    return subprocess.run(
        [sys.executable, str(script)],
        env=env,
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )


def _minimal_db(repo: Path) -> None:
    data = repo / "data"
    data.mkdir(parents=True, exist_ok=True)
    db = data / "beaba_gestao.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE IF NOT EXISTS _e17_probe(x INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()


def test_backup_and_verify_scripts_compilam():
    compile(BACKUP_SCRIPT.read_text(encoding="utf-8"), str(BACKUP_SCRIPT), "exec")
    compile(VERIFY_SCRIPT.read_text(encoding="utf-8"), str(VERIFY_SCRIPT), "exec")


def test_backup_falha_sem_fonte(tmp_path: Path):
    (tmp_path / "data").mkdir(parents=True)
    r = _run_script(BACKUP_SCRIPT, tmp_path)
    assert r.returncode == 1


def test_backup_quick_check_e_verify_ok(tmp_path: Path):
    _minimal_db(tmp_path)
    r = _run_script(BACKUP_SCRIPT, tmp_path)
    assert r.returncode == 0, r.stderr + r.stdout
    hourly = tmp_path / "backups" / "hourly"
    dbs = list(hourly.glob("beaba_gestao_*.db"))
    assert len(dbs) == 1
    v = _run_script(VERIFY_SCRIPT, tmp_path)
    assert v.returncode == 0, v.stderr + v.stdout


def test_verify_falha_sem_backups(tmp_path: Path):
    _minimal_db(tmp_path)
    (tmp_path / "backups" / "hourly").mkdir(parents=True, exist_ok=True)
    v = _run_script(VERIFY_SCRIPT, tmp_path)
    assert v.returncode == 1


def test_rotacao_respeita_keep(tmp_path: Path):
    _minimal_db(tmp_path)
    env = os.environ.copy()
    env["BEABA_REPO_ROOT"] = str(tmp_path)
    env["BEABA_BACKUP_KEEP"] = "2"
    env["BEABA_BACKUP_CLOUD_QUEUE"] = "0"
    for _ in range(3):
        r = subprocess.run(
            [sys.executable, str(BACKUP_SCRIPT)],
            env=env,
            cwd=str(REPO),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, r.stderr + r.stdout
        time.sleep(0.002)
    dbs = sorted((tmp_path / "backups" / "hourly").glob("beaba_gestao_*.db"))
    assert len(dbs) == 2


def test_integrity_check_detecta_corrupcao(tmp_path: Path):
    _minimal_db(tmp_path)
    assert _run_script(BACKUP_SCRIPT, tmp_path).returncode == 0
    latest = max(
        (tmp_path / "backups" / "hourly").glob("beaba_gestao_*.db"),
        key=lambda p: p.stat().st_mtime,
    )
    # Substituir por conteúdo inválido — integrity_check deve falhar
    latest.write_bytes(b"not a sqlite database")
    v = _run_script(VERIFY_SCRIPT, tmp_path)
    assert v.returncode == 1
