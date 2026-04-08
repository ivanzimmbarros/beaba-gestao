"""
E17.2 — Restore local do backup encriptado (BEA1 / .beaba.enc) para data/beaba_gestao.db.

Trava: apenas na branch backup-and-restore (ou BEABA_ALLOW_RESTORE_OFF_BRANCH=1 para testes).
Compara contagens com o último registo de backup em backup_dr_history.json (snapshot_table_counts).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.e17_1_crypto import MAGIC, decrypt_file, parse_backup_key  # noqa: E402
from scripts.e17_1_sqlite_evidence import gather_evidence  # noqa: E402

TELEMETRY_REL = Path("docs") / "governanca" / "telemetry" / "backup_dr_history.json"
RESULT_JSON = "restore_result.json"


def _repo_root() -> Path:
    return Path(
        os.environ.get("GITHUB_WORKSPACE")
        or os.environ.get("BEABA_REPO_ROOT")
        or _REPO
    ).resolve()


def _branch_allowed(repo: Path) -> bool:
    raw = os.environ.get("BEABA_ALLOW_RESTORE_OFF_BRANCH", "").strip().lower()
    if raw in ("1", "true", "yes"):
        return True
    ref = (os.environ.get("GITHUB_REF_NAME") or "").strip()
    if ref == "backup-and-restore":
        return True
    try:
        p = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        if p.returncode == 0 and p.stdout.strip() == "backup-and-restore":
            return True
    except (OSError, subprocess.TimeoutExpired):
        pass
    return False


def _is_bea1_file(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            return fh.read(4) == MAGIC
    except OSError:
        return False


def _resolve_encrypted(arg: Path) -> Path | None:
    if arg.is_file():
        return arg if _is_bea1_file(arg) else None
    if not arg.is_dir():
        return None
    for pat in ("**/*.beaba.enc", "**/*.bin"):
        for p in sorted(arg.glob(pat)):
            if p.is_file() and _is_bea1_file(p):
                return p
    return None


def _latest_backup_snapshot(telemetry_path: Path) -> tuple[dict[str, int] | None, str | None]:
    if not telemetry_path.is_file():
        return None, None
    try:
        data = json.loads(telemetry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None, None
    runs = data.get("runs")
    if not isinstance(runs, list):
        return None, None
    for run in runs:
        if not isinstance(run, dict) or run.get("type") != "backup":
            continue
        snap = run.get("snapshot_table_counts")
        if isinstance(snap, dict) and snap:
            norm: dict[str, int] = {}
            for k, v in snap.items():
                if v is None:
                    continue
                try:
                    norm[str(k)] = int(v)
                except (TypeError, ValueError):
                    continue
            if norm:
                return norm, str(run.get("id") or "")
    return None, None


def _consistency_pct(baseline: dict[str, int] | None, current: dict[str, int | None]) -> tuple[float, int, int]:
    if not baseline:
        return 100.0, 0, 0
    ok = 0
    total = 0
    for k, want in baseline.items():
        total += 1
        got = current.get(k)
        if got is not None and int(got) == int(want):
            ok += 1
    if total == 0:
        return 100.0, 0, 0
    return round(100.0 * ok / total, 2), ok, total


def _write_result(repo: Path, payload: dict) -> None:
    out = repo / RESULT_JSON
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    repo = _repo_root()
    if len(argv) < 2:
        print(
            f"Uso: restore_sqlite.py <ficheiro.beaba.enc|pasta_com_artefacto>",
            file=sys.stderr,
        )
        return 1

    if not _branch_allowed(repo):
        print(
            "restore_sqlite.py: bloqueado — executar apenas na branch backup-and-restore.",
            file=sys.stderr,
        )
        return 2

    enc_arg = Path(argv[1]).expanduser()
    if not enc_arg.is_absolute():
        enc_arg = (repo / enc_arg).resolve()
    enc_path = _resolve_encrypted(enc_arg)
    if enc_path is None:
        print(f"restore_sqlite.py: ficheiro encriptado BEA1 não encontrado em {enc_arg}", file=sys.stderr)
        _write_result(
            repo,
            {
                "ok": False,
                "step": "resolve_encrypted",
                "error": "encrypted_not_found",
                "path": str(enc_arg),
            },
        )
        return 3

    data_dir = repo / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_target = data_dir / "beaba_gestao.db"

    telemetry_path = repo / TELEMETRY_REL
    baseline, baseline_id = _latest_backup_snapshot(telemetry_path)

    try:
        key = parse_backup_key()
    except ValueError as exc:
        print(f"restore_sqlite.py: chave: {exc}", file=sys.stderr)
        _write_result(repo, {"ok": False, "step": "parse_key", "error": str(exc)})
        return 4

    backups_dir = repo / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=backups_dir) as td:
        tmp_root = Path(td)
        decrypted = tmp_root / "restored.db"
        try:
            decrypt_file(enc_path, decrypted, key)
        except Exception as exc:
            print(f"restore_sqlite.py: decrypt falhou: {exc}", file=sys.stderr)
            _write_result(repo, {"ok": False, "step": "decrypt", "error": str(exc)})
            return 5

        try:
            shutil.copy2(decrypted, db_target)
        except OSError as exc:
            print(f"restore_sqlite.py: cópia para {db_target}: {exc}", file=sys.stderr)
            _write_result(repo, {"ok": False, "step": "copy_db", "error": str(exc)})
            return 6

    try:
        ev = gather_evidence(db_target)
    except Exception as exc:
        print(f"restore_sqlite.py: evidência SQLite: {exc}", file=sys.stderr)
        _write_result(repo, {"ok": False, "step": "gather_evidence", "error": str(exc)})
        return 7

    counts = ev.get("table_counts") if isinstance(ev.get("table_counts"), dict) else {}
    ic = ev.get("integrity_check")
    fk = int(ev.get("foreign_key_violations") or 0)
    integrity_ok = ic == "ok" and fk == 0

    pct, matched, compared = _consistency_pct(baseline, counts)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ok = integrity_ok and (compared == 0 or pct == 100.0)

    payload = {
        "ok": ok,
        "finished_at_utc": now,
        "encrypted_source": str(enc_path),
        "integrity_check": ic,
        "foreign_key_violations": fk,
        "table_counts": counts,
        "baseline_run_id": baseline_id,
        "baseline_table_counts": baseline,
        "consistency_match": matched,
        "consistency_compared": compared,
        "consistency_success_pct": pct,
    }
    _write_result(repo, payload)
    print(json.dumps(payload, ensure_ascii=False))

    if not integrity_ok:
        return 8
    if compared > 0 and pct < 100.0:
        return 9
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
