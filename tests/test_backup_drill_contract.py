"""Contratos mínimos — drill apenas em staging; sync manifest; scheduler."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_REPO = Path(__file__).resolve().parents[1]


def test_restore_test_drill_rejects_non_staging() -> None:
    proc = subprocess.run(
        [sys.executable, str(_REPO / "scripts" / "restore_test_drill.py")],
        cwd=str(_REPO),
        env={**os.environ, "ENV_TYPE": "production"},
        text=True,
    )
    assert proc.returncode == 2


@pytest.fixture()
def hourly_dir(tmp_path: Path) -> Path:
    p = tmp_path / "backups" / "hourly"
    p.mkdir(parents=True)
    db = p / "beaba_gestao_20990101.db"
    conn = sqlite3.connect(db)
    try:
        conn.execute("CREATE TABLE q (id INTEGER)")
        conn.commit()
    finally:
        conn.close()
    return tmp_path


def test_backup_sync_dry_run_empty_ok(hourly_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for k in hourly_dir.glob("beaba_gestao_*.db"):
        k.unlink()
    monkeypatch.chdir(hourly_dir)
    monkeypatch.setenv("BEABA_REPO_ROOT", str(hourly_dir))
    from scripts.backup_sync_cloud import run_sync

    assert run_sync(hourly_dir, dry_run=True) == 0


def test_backup_sync_manifest_skips_stable_file(hourly_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dbs = list((hourly_dir / "backups" / "hourly").glob("*.db"))
    assert len(dbs) == 1
    db = dbs[0]
    manifest = hourly_dir / "backups" / "cloud_sync_manifest.json"
    st = db.stat()
    mt = getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000))
    upload = MagicMock(side_effect=AssertionError("put_object não deveria ser chamado"))

    monkeypatch.chdir(hourly_dir)

    monkeypatch.setenv("S3_BUCKET_NAME", "b")
    monkeypatch.setenv("S3_UPLOAD_PREFIX", "hourly/")
    monkeypatch.setenv("S3_ACCESS_KEY", "a")
    monkeypatch.setenv("S3_SECRET_KEY", "s")
    monkeypatch.setenv("BEABA_BACKUP_KEY", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
    monkeypatch.setenv("BEABA_REPO_ROOT", str(hourly_dir))

    class _Cli:
        def put_object(self, **_k):  # noqa: D401
            upload()

    import scripts.backup_sync_cloud as mod

    monkeypatch.setattr(mod, "boto3_client", lambda: _Cli())
    manifest.write_text(
        json.dumps(
            {
                "version": 1,
                "uploaded": {
                    db.name: {
                        "key": "hourly/x.beaba.enc",
                        "mtime_ns": int(mt),
                        "size": int(st.st_size),
                        "etag": "e",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    rc = mod.run_sync(hourly_dir, dry_run=False)
    assert rc == 0


def test_backup_sync_upload_when_no_manifest(monkeypatch: pytest.MonkeyPatch, hourly_dir: Path) -> None:
    monkeypatch.chdir(hourly_dir)
    monkeypatch.setenv("S3_BUCKET_NAME", "buck")
    monkeypatch.setenv("S3_UPLOAD_PREFIX", "pfx/")
    monkeypatch.setenv("S3_ACCESS_KEY", "ak")
    monkeypatch.setenv("S3_SECRET_KEY", "sec")
    monkeypatch.setenv("BEABA_BACKUP_KEY", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")

    cli = MagicMock()
    cli.put_object.return_value = {"ETag": "\"testetag\""}
    monkeypatch.setenv("BEABA_REPO_ROOT", str(hourly_dir))
    import scripts.backup_sync_cloud as mod

    monkeypatch.setattr(mod, "boto3_client", lambda: cli)

    rc = mod.run_sync(hourly_dir, dry_run=False)
    assert rc == 0
    assert cli.put_object.called


def test_scheduler_once(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("BEABA_REPO_ROOT", str(tmp_path))
    calls: list[str] = []

    def fake_run(args, **_k):  # type: ignore[no-untyped-def]
        calls.append(Path(args[1]).name)
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "argv", ["scheduler.py", "--once"])
    from scripts.scheduler import main

    assert main() == 0
    assert "backup_sqlite_hourly.py" in calls[0]
    assert "backup_sync_cloud.py" in calls[1]
