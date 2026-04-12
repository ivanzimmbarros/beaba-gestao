"""E17.2 — restore_sqlite.py: trava de branch e fluxo mínimo com flag de teste."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RESTORE_SCRIPT = REPO / "scripts" / "restore_sqlite.py"

# No GitHub Actions, GITHUB_WORKSPACE está sempre definido; o subprocess herda e, se tiver
# prioridade sobre BEABA_REPO_ROOT, restore_sqlite gravaria fora do tmp_path do pytest.


def _env_for_restore_subprocess(repo_root: Path, **extra: str) -> dict[str, str]:
    base = {k: v for k, v in os.environ.items() if k not in ("GITHUB_WORKSPACE", "PYTHONPATH")}
    base["BEABA_REPO_ROOT"] = str(repo_root)
    base["PYTHONPATH"] = str(REPO)
    base.update(extra)
    return base


def _key32_b64() -> str:
    import base64

    return base64.b64encode(b"x" * 32).decode("ascii")


def _minimal_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY)")
    conn.execute("INSERT INTO clientes DEFAULT VALUES")
    conn.commit()
    conn.close()


@pytest.fixture()
def tiny_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("BEABA_ALLOW_RESTORE_OFF_BRANCH", "1")
    monkeypatch.setenv("BEABA_REPO_ROOT", str(tmp_path))
    (tmp_path / "docs" / "governanca" / "telemetry").mkdir(parents=True, exist_ok=True)
    telemetry = tmp_path / "docs" / "governanca" / "telemetry" / "backup_dr_history.json"
    telemetry.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "runs": [
                    {
                        "id": "test-baseline",
                        "type": "backup",
                        "snapshot_table_counts": {"clientes": 1},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    db = tmp_path / "src.db"
    _minimal_db(db)
    enc = tmp_path / "b.beaba.enc"
    env = os.environ.copy()
    env["BEABA_BACKUP_KEY"] = _key32_b64()
    env["PYTHONPATH"] = str(REPO)
    r = subprocess.run(
        [
            sys.executable,
            "-c",
            "from pathlib import Path; from scripts.e17_1_crypto import encrypt_file, parse_backup_key; "
            "import os; p=Path(os.environ['P_IN']); o=Path(os.environ['P_OUT']); encrypt_file(p,o,parse_backup_key())",
        ],
        cwd=str(REPO),
        env={**env, "P_IN": str(db), "P_OUT": str(enc)},
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    return tmp_path


def test_restore_blocks_without_allowed_branch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("BEABA_ALLOW_RESTORE_OFF_BRANCH", raising=False)
    monkeypatch.delenv("GITHUB_REF_NAME", raising=False)
    env = _env_for_restore_subprocess(tmp_path)
    env.pop("BEABA_ALLOW_RESTORE_OFF_BRANCH", None)
    env.pop("GITHUB_REF_NAME", None)
    r = subprocess.run(
        [sys.executable, str(RESTORE_SCRIPT), str(tmp_path / "noop")],
        cwd=str(REPO),
        env=env,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2
    rr = tmp_path / "restore_result.json"
    assert rr.is_file(), "restore_result.json é obrigatório mesmo na trava de branch"
    data = json.loads(rr.read_text(encoding="utf-8"))
    assert data.get("step") == "branch_lock"
    assert data.get("consistency_success_pct") is None


def test_restore_ok_with_allow_flag_and_encrypted_file(tiny_repo: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("BEABA_ALLOW_RESTORE_OFF_BRANCH", "1")
    monkeypatch.setenv("BEABA_REPO_ROOT", str(tiny_repo))
    monkeypatch.setenv("BEABA_BACKUP_KEY", _key32_b64())
    enc = tiny_repo / "b.beaba.enc"
    env = _env_for_restore_subprocess(
        tiny_repo,
        BEABA_ALLOW_RESTORE_OFF_BRANCH="1",
        BEABA_BACKUP_KEY=_key32_b64(),
    )
    r = subprocess.run(
        [sys.executable, str(RESTORE_SCRIPT), str(enc)],
        cwd=str(REPO),
        env=env,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    db_out = tiny_repo / "data" / "beaba_gestao.db"
    assert db_out.is_file()
    res = json.loads((tiny_repo / "restore_result.json").read_text(encoding="utf-8"))
    assert res.get("ok") is True
    assert res.get("consistency_success_pct") == 100.0
