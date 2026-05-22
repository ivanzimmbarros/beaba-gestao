#!/usr/bin/env python3
"""
E17.2 — Painel de demanda no terminal: lê status_demanda.json + backup_dr_history.json
e imprime um dashboard formatado (sem dependências externas além da stdlib).
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


def _utf8_stdio() -> None:
    """Windows (cp1252): evitar UnicodeEncodeError com emojis no dashboard."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


_utf8_stdio()

PROTOCOL_VERSION = "E17.2"
STATUS_ATIVO = "Ativo"
DEFAULT_LIVE = "Governança Ativa com Alertas via E-mail e Retenção"

_REPO = Path(__file__).resolve().parents[1]
_STATUS = Path("docs") / "governanca" / "status_demanda.json"
_TELEMETRY = Path("docs") / "governanca" / "telemetry" / "backup_dr_history.json"
_RESTORE_RESULT = Path("restore_result.json")


def _repo_root() -> Path:
    return Path(
        os.environ.get("BEABA_REPO_ROOT") or os.environ.get("GITHUB_WORKSPACE") or _REPO
    ).resolve()


def _load_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _protocol_from_status(data: dict | None) -> str:
    if not data:
        return PROTOCOL_VERSION
    did = str(data.get("demanda_id") or "")
    if re.search(r"E17[_-]2", did, re.I):
        return "E17.2"
    tit = str(data.get("titulo") or "")
    m = re.search(r"E17\.\d+", tit, re.I)
    if m:
        return m.group(0)
    return PROTOCOL_VERSION


def _latest_backup_snapshot(runs: list) -> dict[str, int] | None:
    for run in runs:
        if not isinstance(run, dict) or run.get("type") != "backup":
            continue
        snap = run.get("snapshot_table_counts")
        if isinstance(snap, dict) and snap:
            out: dict[str, int] = {}
            for k, v in snap.items():
                try:
                    if v is not None:
                        out[str(k)] = int(v)
                except (TypeError, ValueError):
                    pass
            if out:
                return out
    return None


def _latest_restore_counts(runs: list) -> dict[str, int] | None:
    for run in runs:
        if not isinstance(run, dict) or run.get("type") != "restore_proof":
            continue
        ev = run.get("evidence")
        if not isinstance(ev, dict):
            continue
        tc = ev.get("table_counts")
        if isinstance(tc, dict) and tc:
            out: dict[str, int] = {}
            for k, v in tc.items():
                try:
                    if v is not None:
                        out[str(k)] = int(v)
                except (TypeError, ValueError):
                    pass
            if out:
                return out
    return None


def _print_dashboard(repo: Path) -> int:
    status_path = repo / _STATUS
    telem_path = _telemetry_path(repo)
    restore_path = repo / _RESTORE_RESULT

    status = _load_json(status_path)
    telem = _load_json(telem_path) or {}
    runs = telem.get("runs") if isinstance(telem.get("runs"), list) else []

    ver = _protocol_from_status(status)
    live = (status or {}).get("live_status") or DEFAULT_LIVE

    print()
    print(f"🟢 Versão: {ver} | Status: {STATUS_ATIVO}")
    print(f'🔵 Live Status: "{live}"')
    print()

    esperados = _latest_backup_snapshot(runs)
    restaurados: dict[str, int | str] | None = None
    pct_note = ""

    if restore_path.is_file():
        rr = _load_json(restore_path)
        if isinstance(rr, dict):
            tc = rr.get("table_counts")
            if isinstance(tc, dict):
                restaurados = {}
                for k, v in tc.items():
                    try:
                        restaurados[str(k)] = int(v) if v is not None else "—"
                    except (TypeError, ValueError):
                        restaurados[str(k)] = str(v)
            pct = rr.get("consistency_success_pct")
            if pct is not None:
                pct_note = f"  (validação telemetria: {pct}% linha com baseline)"

    if restaurados is None:
        lr = _latest_restore_counts(runs)
        if lr:
            restaurados = {k: int(v) for k, v in lr.items()}
            pct_note = "  (último restore_proof em telemetria)"

    print("📊 Tabelas Críticas — registos restaurados vs esperados (baseline último backup):")
    if not esperados and not restaurados:
        print("   (sem snapshot_table_counts na telemetria nem restore local — execute backups GHA ou restore_sqlite)")
    else:
        tables = sorted(set((esperados or {}).keys()) | set((restaurados or {}).keys()))
        if not tables:
            print("   —")
        for t in tables:
            exp = esperados.get(t) if esperados else None
            res = restaurados.get(t) if restaurados else None
            exp_s = str(exp) if exp is not None else "—"
            res_s = str(res) if res is not None else "—"
            print(f"   • {t}: restaurados={res_s}  |  esperados={exp_s}")
    if pct_note:
        print(pct_note)
    print()

    print("🔴 Últimos Eventos (backup / restore):")
    br = [r for r in runs if isinstance(r, dict) and r.get("type") in ("backup", "restore_proof")]
    br = br[:5]
    if not br:
        print("   (nenhum registo em backup_dr_history.json)")
    else:
        for i, r in enumerate(br, 1):
            rid = r.get("id", "?")
            rt = r.get("type", "?")
            started = r.get("started_at", "")
            overall = r.get("overall", "")
            url = r.get("log_url") or r.get("workflow_run_url") or ""
            line = f"   {i}. [{rt}] {started}  overall={overall}  id={rid}"
            print(line)
            if url:
                print(f"      {url}")
    print()
    return 0


def _telemetry_path(repo: Path) -> Path:
    p = repo / _TELEMETRY
    if p.is_file():
        return p
    example = p.with_suffix(".json.example")
    return example if example.is_file() else p


def main() -> int:
    repo = _repo_root()
    telem_path = _telemetry_path(repo)
    missing = []
    if not (repo / _STATUS).is_file():
        missing.append(str(_STATUS))
    if not telem_path.is_file():
        missing.append(str(_TELEMETRY))
    if missing:
        print(
            "monitor_demanda.py: ficheiros em falta (execute a partir da raiz do repo):",
            file=sys.stderr,
        )
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        return 1
    return _print_dashboard(repo)


if __name__ == "__main__":
    raise SystemExit(main())
