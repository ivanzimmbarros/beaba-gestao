"""
E17.1 — Telemetria backup/DR: taxonomia de grupos + append a backup_dr_history.json.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

TELEMETRY_REL = Path("docs") / "governanca" / "telemetry" / "backup_dr_history.json"
MAX_RUNS = 400

_GROUP_KEYS = ("ambiente", "estrutura", "configuracao", "arquivos", "user_data", "logs")


def _repo_root() -> Path:
    return Path(
        os.environ.get("GITHUB_WORKSPACE")
        or os.environ.get("BEABA_REPO_ROOT")
        or Path(__file__).resolve().parents[1]
    ).resolve()


def _telemetry_path(repo: Path) -> Path:
    return repo / TELEMETRY_REL


def _run_urls() -> tuple[str, str]:
    server = (os.environ.get("GITHUB_SERVER_URL") or "https://github.com").rstrip("/")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    if not repo or not run_id:
        return "", ""
    base = f"{server}/{repo}/actions/runs/{run_id}"
    return base, base


def _g(_label: str, status: str, detail: str) -> dict:
    return {"status": status, "detail": (detail or "")[:2000]}


def build_groups_backup(steps: dict, upload_ok: bool | None) -> dict[str, dict]:
    pip_rc = int(steps.get("pip_check_rc", 1))
    py_ver = str(steps.get("python_version") or sys.version.split()[0])
    amb = _g(
        "ambiente",
        "ok" if pip_rc == 0 else "fail",
        f"Python {py_ver}; pip check rc={pip_rc}",
    )

    struct_ok = bool(steps.get("struct_ok", False))
    estr = _g(
        "estrutura",
        "ok" if struct_ok else "fail",
        "Pastas vitais (scripts, docs/governanca/telemetry, src/database)" if struct_ok else "Falta pasta vital ou sem permissão",
    )

    key_ok = bool(steps.get("key_configured", False))
    cfg = _g(
        "configuracao",
        "ok" if key_ok else "fail",
        "Secret BEABA_BACKUP_KEY presente" if key_ok else "BEABA_BACKUP_KEY ausente — encriptação impossível",
    )

    req = bool(steps.get("requirements_exists", False))
    env_ex = bool(steps.get("env_example_exists", False))
    arq_st = "ok" if req and env_ex else ("warn" if req else "fail")
    arq = _g(
        "arquivos",
        arq_st,
        f"requirements.txt={'sim' if req else 'não'}; .env.example={'sim' if env_ex else 'não'}",
    )

    brc = int(steps.get("backup_rc", 1))
    erc = int(steps.get("encrypt_rc", 1))
    ud_st = "ok" if brc == 0 and erc == 0 else "fail"
    ud_detail = f"backup_rc={brc}; encrypt_rc={erc}"
    if steps.get("backup_detail"):
        ud_detail += f"; {steps['backup_detail']}"
    ud = _g("user_data", ud_st, ud_detail)

    if upload_ok is None:
        log_st = "warn"
        log_detail = "Upload não avaliado nesta execução"
    elif upload_ok:
        log_st = "ok"
        art = (os.environ.get("BEABA_GHA_ARTIFACT_NAME") or "").strip()
        rlab = (os.environ.get("BEABA_GHA_RETENTION_LABEL") or "").strip()
        log_detail = f"Artefacto encriptado publicado"
        if art:
            log_detail += f" ({art})"
        if rlab:
            log_detail += f" — {rlab}"
    else:
        log_st = "fail"
        log_detail = "Falha ou omissão no upload do artefacto"

    wf_url, log_url = _run_urls()
    logs = _g("logs", log_st, f"Run: {wf_url or log_url or 'local'}")

    return {
        "ambiente": amb,
        "estrutura": estr,
        "configuracao": cfg,
        "arquivos": arq,
        "user_data": ud,
        "logs": {**logs, "workflow_run_url": wf_url, "log_url": log_url or wf_url},
    }


def build_groups_restore(steps: dict, evidence: dict | None) -> dict[str, dict]:
    pip_rc = int(steps.get("pip_check_rc", 1))
    py_ver = str(steps.get("python_version") or sys.version.split()[0])
    amb = _g("ambiente", "ok" if pip_rc == 0 else "fail", f"Python {py_ver}; pip check rc={pip_rc}")

    struct_ok = bool(steps.get("struct_ok", False))
    estr = _g("estrutura", "ok" if struct_ok else "fail", "Layout repo + backups/hourly" if struct_ok else "Estrutura incompleta")

    key_ok = bool(steps.get("key_configured", False))
    cfg = _g("configuracao", "ok" if key_ok else "fail", "BEABA_BACKUP_KEY para decrypt" if key_ok else "Chave ausente")

    req = bool(steps.get("requirements_exists", False))
    env_ex = bool(steps.get("env_example_exists", False))
    arq_st = "ok" if req and env_ex else ("warn" if req else "fail")
    arq = _g("arquivos", arq_st, f"requirements.txt; .env.example")

    dl_ok = bool(steps.get("download_ok", False))
    drc = int(steps.get("decrypt_rc", 1))
    vrc = int(steps.get("verify_rc", 1))
    ev = evidence or {}
    ic = ev.get("integrity_check", "")
    counts = ev.get("table_counts") or {}
    sha = ev.get("sha256", "")
    ud_st = "ok" if dl_ok and drc == 0 and vrc == 0 and ic == "ok" else "fail"
    ud_detail = (
        f"download={dl_ok}; decrypt_rc={drc}; verify_rc={vrc}; "
        f"integrity_check={ic}; sha256={sha[:16]}…; contagens={counts}"
    )
    ud = _g("user_data", ud_st, ud_detail)

    wf_url, log_url = _run_urls()
    logs = _g("logs", "ok" if wf_url else "warn", wf_url or "URL indisponível")

    out = {
        "ambiente": amb,
        "estrutura": estr,
        "configuracao": cfg,
        "arquivos": arq,
        "user_data": ud,
        "logs": {**logs, "workflow_run_url": wf_url, "log_url": log_url or wf_url},
    }
    return out


def _worst_group(groups: dict) -> str:
    order = {"fail": 3, "warn": 2, "ok": 1}
    w = 0
    for k in _GROUP_KEYS:
        g = groups.get(k) or {}
        s = str(g.get("status") or "warn").lower()
        w = max(w, order.get(s, 2))
    return {3: "fail", 2: "warn", 1: "ok"}[w]


def _normalize_groups(groups: dict) -> dict:
    out = {}
    for k in _GROUP_KEYS:
        g = groups.get(k)
        if not isinstance(g, dict):
            g = {"status": "warn", "detail": "grupo ausente"}
        out[k] = {
            "status": str(g.get("status") or "warn").lower(),
            "detail": str(g.get("detail") or ""),
        }
        if k == "logs":
            for extra in ("workflow_run_url", "log_url"):
                if g.get(extra):
                    out[k][extra] = str(g[extra])
    return out


def build_run_record(
    *,
    run_type: str,
    started_at: str,
    finished_at: str,
    duration_seconds: int,
    git_ref: str,
    git_sha: str,
    groups: dict,
    snapshot_table_counts: dict | None = None,
) -> dict:
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    rid = f"gha-{run_id}-{run_type}-{started_at.replace(':', '').replace('-', '')[:15]}"
    wf_url, log_url = _run_urls()
    groups = _normalize_groups(groups)
    if "logs" in groups and wf_url:
        groups["logs"]["workflow_run_url"] = wf_url
        groups["logs"]["log_url"] = log_url or wf_url
    rec: dict = {
        "id": rid,
        "type": run_type,
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_seconds": duration_seconds,
        "git_ref": git_ref,
        "git_sha": git_sha,
        "workflow_run_url": wf_url,
        "log_url": log_url or wf_url,
        "overall": _worst_group(groups),
        "groups": groups,
    }
    if snapshot_table_counts is not None and isinstance(snapshot_table_counts, dict) and snapshot_table_counts:
        rec["snapshot_table_counts"] = snapshot_table_counts
    return rec


def append_run(repo: Path, run: dict) -> None:
    path = _telemetry_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {"schema_version": 1, "runs": []}
    runs = data.get("runs")
    if not isinstance(runs, list):
        runs = []
    runs.insert(0, run)
    data["runs"] = runs[:MAX_RUNS]
    data["schema_version"] = 1
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cmd_append_backup() -> int:
    repo = _repo_root()
    state_path = repo / "gha_backup_state.json"
    if not state_path.is_file():
        print("gha_backup_state.json não encontrado", file=sys.stderr)
        return 1
    state = json.loads(state_path.read_text(encoding="utf-8"))
    steps = state.get("steps") or {}
    upload_raw = os.environ.get("TELEMETRY_UPLOAD_OK", "").strip().lower()
    if upload_raw in ("1", "true", "yes"):
        upload_ok = True
    elif upload_raw in ("0", "false", "no"):
        upload_ok = False
    else:
        enc_ok = int(steps.get("encrypt_rc", 1)) == 0 and bool(steps.get("encrypted_rel"))
        upload_ok = True if enc_ok else None

    groups = build_groups_backup(steps, upload_ok)
    snap = steps.get("snapshot_table_counts")
    snap_dict = snap if isinstance(snap, dict) else None
    run = build_run_record(
        run_type="backup",
        started_at=state["started_at"],
        finished_at=state["finished_at"],
        duration_seconds=int(state.get("duration_seconds", 0)),
        git_ref=str(state.get("git_ref") or "develop"),
        git_sha=str(state.get("git_sha") or ""),
        groups=groups,
        snapshot_table_counts=snap_dict,
    )
    append_run(repo, run)
    return 0


def cmd_append_restore() -> int:
    repo = _repo_root()
    state_path = repo / "gha_restore_state.json"
    if not state_path.is_file():
        print("gha_restore_state.json não encontrado", file=sys.stderr)
        return 1
    state = json.loads(state_path.read_text(encoding="utf-8"))
    steps = state.get("steps") or {}
    evidence = state.get("evidence")
    groups = build_groups_restore(steps, evidence if isinstance(evidence, dict) else None)
    run = build_run_record(
        run_type="restore_proof",
        started_at=state["started_at"],
        finished_at=state["finished_at"],
        duration_seconds=int(state.get("duration_seconds", 0)),
        git_ref=str(state.get("git_ref") or "develop"),
        git_sha=str(state.get("git_sha") or ""),
        groups=groups,
    )
    append_run(repo, run)
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Uso: e17_1_telemetry.py append-backup | append-restore", file=sys.stderr)
        return 1
    if argv[1] == "append-backup":
        return cmd_append_backup()
    if argv[1] == "append-restore":
        return cmd_append_restore()
    print("Subcomando inválido", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
