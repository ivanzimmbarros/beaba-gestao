"""E17.1 — criptografia GCM, telemetria append, evidências SQLite."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_aes_gcm_roundtrip(tmp_path, monkeypatch):
    key = b"k" * 32
    monkeypatch.setenv("BEABA_BACKUP_KEY", base64.b64encode(key).decode())
    from scripts.e17_1_crypto import decrypt_file, encrypt_file

    p_in = tmp_path / "a.db"
    p_out = tmp_path / "a.beaba.enc"
    p_back = tmp_path / "b.db"
    p_in.write_bytes(b"sqlite-test-bytes")
    encrypt_file(p_in, p_out, key)
    decrypt_file(p_out, p_back, key)
    assert p_back.read_bytes() == b"sqlite-test-bytes"


def test_sqlite_evidence_minimal(tmp_path):
    import sqlite3

    db = tmp_path / "t.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE clientes (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()
    r = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "e17_1_sqlite_evidence.py"), str(db)],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["integrity_check"] == "ok"
    assert "sha256" in data


def test_telemetry_append_backup_from_state(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs" / "governanca" / "telemetry").mkdir(parents=True)
    hist = tmp_path / "docs" / "governanca" / "telemetry" / "backup_dr_history.json"
    hist.write_text('{"schema_version":1,"runs":[]}\n', encoding="utf-8")

    state = {
        "started_at": "2026-04-09T12:00:00Z",
        "finished_at": "2026-04-09T12:01:00Z",
        "duration_seconds": 60,
        "git_ref": "develop",
        "git_sha": "abc1234",
        "steps": {
            "python_version": "3.12.0",
            "pip_check_rc": 0,
            "struct_ok": True,
            "requirements_exists": True,
            "env_example_exists": True,
            "key_configured": True,
            "backup_rc": 0,
            "encrypt_rc": 0,
            "encrypted_rel": "x/y.beaba.enc",
        },
    }
    (tmp_path / "gha_backup_state.json").write_text(json.dumps(state), encoding="utf-8")

    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("GITHUB_RUN_ID", "12345")
    monkeypatch.setenv("GITHUB_REPOSITORY", "org/repo")
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
    monkeypatch.setenv("TELEMETRY_UPLOAD_OK", "1")

    r = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "e17_1_telemetry.py"), "append-backup"],
        cwd=str(tmp_path),
        env={**os.environ, "PYTHONPATH": str(REPO)},
    )
    assert r.returncode == 0
    data = json.loads(hist.read_text(encoding="utf-8"))
    assert len(data["runs"]) == 1
    assert data["runs"][0]["type"] == "backup"
    assert data["runs"][0]["groups"]["ambiente"]["status"] == "ok"
