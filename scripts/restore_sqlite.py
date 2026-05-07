"""
E17.2 — Restore local do backup encriptado (BEA1 / .beaba.enc) para data/beaba_gestao.db.

Trava: apenas na branch backup-and-restore (ou BEABA_ALLOW_RESTORE_OFF_BRANCH=1 para testes).
Compara contagens com o último registo de backup em backup_dr_history.json (snapshot_table_counts).

Arquitectura UI (2026-04-12): legado `page_clientes.py` / `page_agendamentos.py` descontinuado;
consolidação em `page_clientes_agendamentos.py` (ver PAINEL / status_demanda.json).

Após restore: o Cockpit Home (`page_home`, `home_cockpit_metrics`) reflecte o estado do
SQLite reposto; UI Master (ilhas, Horizonte) acompanha o código no repositório.

CAG: o mesmo restore repõe dados de clientes/agendamentos no SQLite; o aspeto Sereno
(Horizonte, ilhas, cards) vem do código (`constituicao_visual_shell`, `page_clientes_agendamentos`)
e dos testes `test_cag_visual_sereno`, `test_vnd_visual_sereno`, `test_col_visual_sereno`,
`test_cat_visual_sereno`, `test_home_visual_sereno` / E20. Setor 4
(lista no expander «Agendamentos»): contrato em `tests/cag_setor4_ui_contract.py` +
`test_clientes_agendamentos_page.py` (incl. pesquisa unificada `cag_busca_nome`); E2E em
`tests/e2e_stress_test.py` (_run_cag_consolidated_slice) valida contrato do widget em
`src/ui/widgets/cliente_search.py`; tabela `agendamentos`: `tipo_atendimento` (presencial/virtual),
`sala_virtual_disponibilizada` (NULL se presencial, 0/1 se virtual); dados de busca por prefixo de nome: `tests/test_cliente.py`; Painel de Vendas:
`tests/vnd_ui_contract.py`, `test_vnd_visual_sereno` (pesquisa unificada; form editar cliente sem value= duplicado
em `st.number_input` com chaves `*_vc_nem` / `*_vc_qfil` primadas por `_prime_cliente_form` em `page_vendas.py`); Colaboradores:
`tests/col_ui_contract.py`, `test_col_visual_sereno` (pesquisa unificada + **Mapa da Equipa** + **Dados da Parceria** +
setor **Disponibilidade** em `page_colaboradores.py` / `colaboradores_disponibilidade_ui.py`);
prefixo de nome, filtros mapa, disponibilidade (`colaborador_disponibilidade_*`) e campos de parceria/IBAN em `tests/test_colaborador.py`,
`tests/test_colaborador_disponibilidade.py`; smoke `tests/smoke_test_ui.py`
(`test_smoke_colaboradores_dados_parceria_ficha_widgets`, `test_smoke_colaboradores_disponibilidade_sector`); Catálogo: `tests/cat_ui_contract.py`; Início: `tests/home_ui_contract.py`;
Financeiro: `tests/fin_ui_contract.py`, `tests/test_fin_visual_sereno.py`, `tests/test_financeiro_resultado_operacional.py`,
`tests/test_financeiro_repasses_colaboradores.py`, fatia `e2e_stress_test.py::test_e2e_fin_visual_shell_contract`;
sector **1. Resultado Operacional Consolidado** (`financeiro_resultado_operacional.py`, painel em `page_financeiro.py`);
sector **3. Repasses** (cadeia Natureza→Especialidades→Serviço; multiselect colaborador filtrado por `listar_colaboradores_mapa_equipa`)
+ metadados em `financeiro_repasses_colaboradores.py`.
Setor 5 Entradas (2026-04): `page_financeiro.py` (expander «Gestão de valores convertidos (vendas)»); 
gestão de faturas (`atualizar_fatura_venda` em `financeiro_entradas_convertidas.py`); 
contrato em `tests/fin_ui_contract.py` (`assert_fin_entradas_sector_na_pagina`) + 
`tests/test_financeiro_entradas_convertidas.py` + `tests/smoke_test_ui.py` (`test_smoke_financeiro_entradas_sector_widgets`).
Smoke UI: `tests/smoke_test_ui.py` (`test_smoke_colaboradores_dados_parceria_ficha_widgets`, `test_smoke_financeiro_repasses_multiselect_chain`, `test_smoke_financeiro_resultado_operacional_panel`, `test_smoke_financeiro_entradas_sector_widgets`, `test_smoke_governanca_admin_sector_widgets`) + `pytest.ini`. Catálogo: wizard tipo→confirmação em `page_catalogo.py`.
Cloud sync + drill staging: `scripts/backup_sync_cloud.py`, `scripts/restore_test_drill.py`, `scripts/scheduler.py`, `tests/test_backup_drill_contract.py`, `tests/gov_ui_contract.py`, `e2e_stress_test.py::test_e2e_governanca_backup_visual_shell_contract`.
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
    # BEABA_REPO_ROOT primeiro: testes/pytest com tmp_path no CI definem-no explicitamente;
    # GITHUB_WORKSPACE existe sempre no runner e não deve mascarar o sandbox.
    return Path(
        os.environ.get("BEABA_REPO_ROOT")
        or os.environ.get("GITHUB_WORKSPACE")
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
    """Grava sempre restore_result.json na raiz do repo (obrigatório em todos os exits)."""
    out = repo / RESULT_JSON
    if "consistency_success_pct" not in payload:
        payload = {**payload, "consistency_success_pct": None}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    repo = _repo_root()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if len(argv) < 2:
        print(
            f"Uso: restore_sqlite.py <ficheiro.beaba.enc|pasta_com_artefacto>",
            file=sys.stderr,
        )
        _write_result(
            repo,
            {
                "ok": False,
                "finished_at_utc": now,
                "step": "usage",
                "error": "argumentos em falta",
                "consistency_success_pct": None,
            },
        )
        return 1

    if not _branch_allowed(repo):
        print(
            "restore_sqlite.py: bloqueado — executar apenas na branch backup-and-restore "
            "(excepção: BEABA_ALLOW_RESTORE_OFF_BRANCH=1 em testes locais).",
            file=sys.stderr,
        )
        _write_result(
            repo,
            {
                "ok": False,
                "finished_at_utc": now,
                "step": "branch_lock",
                "error": "branch != backup-and-restore",
                "consistency_success_pct": None,
            },
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
                "finished_at_utc": now,
                "step": "resolve_encrypted",
                "error": "encrypted_not_found",
                "path": str(enc_arg),
                "consistency_success_pct": None,
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
        _write_result(
            repo,
            {
                "ok": False,
                "finished_at_utc": now,
                "step": "parse_key",
                "error": str(exc),
                "consistency_success_pct": None,
            },
        )
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
            _write_result(
                repo,
                {
                    "ok": False,
                    "finished_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "step": "decrypt",
                    "error": str(exc),
                    "consistency_success_pct": None,
                },
            )
            return 5

        try:
            shutil.copy2(decrypted, db_target)
        except OSError as exc:
            print(f"restore_sqlite.py: cópia para {db_target}: {exc}", file=sys.stderr)
            _write_result(
                repo,
                {
                    "ok": False,
                    "finished_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "step": "copy_db",
                    "error": str(exc),
                    "consistency_success_pct": None,
                },
            )
            return 6

    try:
        ev = gather_evidence(db_target)
    except Exception as exc:
        print(f"restore_sqlite.py: evidência SQLite: {exc}", file=sys.stderr)
        _write_result(
            repo,
            {
                "ok": False,
                "finished_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "step": "gather_evidence",
                "error": str(exc),
                "consistency_success_pct": None,
            },
        )
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
