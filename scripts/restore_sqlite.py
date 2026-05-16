"""
E17.2 — Restore local do backup encriptado (BEA1 / .beaba.enc) para data/beaba_gestao.db.

Contexto: ambiente identificado por ENV_TYPE / BEABA_ENV (dev, stg, prod). Restore permitido em
qualquer branch (incl. MAIN em desastre) desde que seja fornecido o artefacto encriptado BEA1.
No CI, test_restore_weekly pode fazer checkout da branch backup-and-restore para o kit de código;
a matriz altera apenas a origem dos artefactos de dados.
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
Smoke UI: `tests/smoke_test_ui.py` (`test_smoke_colaboradores_dados_parceria_ficha_widgets`, `test_smoke_colaboradores_relatorio_repasse_setor_widgets`, `test_smoke_financeiro_repasses_multiselect_chain`, `test_smoke_financeiro_resultado_operacional_panel`, `test_smoke_financeiro_entradas_sector_widgets`, `test_smoke_governanca_admin_sector_widgets`, `test_smoke_auth_login_screen_boots`) + `pytest.ini`. Catálogo: wizard tipo→confirmação em `page_catalogo.py`.
Colaboradores E24 (2026-05): `colaboradores_relatorio` + PDF + `colaboradores_repasse_setor_ui`; contrato `assert_col_relatorio_global_repasse_e24_contract`; unit `tests/test_colaboradores_relatorio.py`.
Autenticação MFA (2026-05): SMTP em `src/modules/email_utils.py` (`.env` `SMTP_*` / `EMAIL_*`; Gmail palavra-passe de aplicação), `src/ui/page_auth.py`; `tests/test_email_utils.py`, `e2e_stress_test.py::test_e2e_mfa_email_smtp_contract` — segredos fora do `.db` (D1 cópia integral inalterada em caminhos).
Cloud sync + drill staging: `scripts/backup_sync_cloud.py`, `scripts/restore_test_drill.py`, `scripts/scheduler.py`, `tests/test_backup_drill_contract.py`, `tests/gov_ui_contract.py`, `e2e_stress_test.py::test_e2e_governanca_backup_visual_shell_contract`.
"""

from __future__ import annotations

import json
import os
import shutil
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


def _env_folder_slug() -> str:
    raw = (os.environ.get("ENV_TYPE") or os.environ.get("BEABA_ENV") or "dev").strip().lower()
    if raw in ("production", "prod", "main"):
        return "prod"
    if raw in ("staging", "stg"):
        return "stg"
    if raw in ("develop", "dev", "development", "local"):
        return "dev"
    return "dev"


def _emit_manager_message(message: str, *, err: bool = False) -> None:
    """Mensagem legível para gestão; tolera consola Windows (cp1252) sem abortar o restore."""
    stream = sys.stderr if err else sys.stdout
    try:
        print(message, file=stream, flush=True)
    except UnicodeEncodeError:
        buf = getattr(stream, "buffer", None)
        line = message + "\n"
        if buf is not None:
            buf.write(line.encode("utf-8", errors="replace"))
            buf.flush()
        else:
            print(line.encode("ascii", errors="replace").decode("ascii"), file=stream, flush=True)


def _print_restore_start(env_slug: str) -> None:
    if env_slug == "prod":
        _emit_manager_message(
            "⚠️ [RECUPERAÇÃO DE PRODUÇÃO] Iniciando restauração CRÍTICA dos dados reais dos clientes "
            "no ambiente MAIN..."
        )
    else:
        _emit_manager_message(
            "🛠️ [RECUPERAÇÃO DE TESTE] Iniciando restauração no ambiente de "
            "homologação/desenvolvimento..."
        )


def _print_restore_success() -> None:
    _emit_manager_message(
        "✅ [RESTORE CONCLUÍDO] Os dados foram recuperados e validados com sucesso. "
        "O sistema está pronto para uso."
    )


def _print_restore_failure(step: str, error: str) -> None:
    _emit_manager_message(
        f"❌ [FALHA NO RESTORE] Não foi possível recuperar o banco de dados. "
        f"Etapa falha: {step}. Motivo técnico: {error}",
        err=True,
    )


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


def _restore_audit_block() -> dict[str, str] | None:
    """Metadados de rastreio no CI (ex.: test_restore_weekly): origem dos dados vs código em backup-and-restore."""
    out: dict[str, str] = {}
    t = (os.environ.get("BEABA_GHA_TARGET_BRANCH") or "").strip()
    if t:
        out["artifact_data_source_ref"] = t
    kb = (os.environ.get("BEABA_GHA_RESTORE_KIT_BRANCH") or "").strip()
    if kb:
        out["restore_execution_branch"] = kb
    ks = (os.environ.get("BEABA_GHA_RESTORE_KIT_SHA_SHORT") or "").strip()
    if ks:
        out["restore_kit_commit_short"] = ks
    kf = (os.environ.get("BEABA_GHA_RESTORE_KIT_SHA_FULL") or "").strip()
    if kf:
        out["restore_kit_commit_full"] = kf
    tw = (os.environ.get("BEABA_GHA_RESTORE_TEST_WORKFLOW") or "").strip()
    if tw:
        out["calling_workflow"] = tw
    rid = (os.environ.get("GITHUB_RUN_ID") or "").strip()
    if rid:
        out["github_run_id"] = rid
    repo = (os.environ.get("GITHUB_REPOSITORY") or "").strip()
    srv = (os.environ.get("GITHUB_SERVER_URL") or "https://github.com").rstrip("/")
    if repo and rid:
        out["github_run_url"] = f"{srv}/{repo}/actions/runs/{rid}"
    if not out:
        return None
    out["audit_message_source"] = "scripts/restore_sqlite.py#restore_audit"
    return out


def _write_result(repo: Path, payload: dict) -> dict:
    """Grava restore_result.json. Injeta restore_audit quando variáveis CI estão definidas. Devolve o dict gravado."""
    merged: dict = dict(payload)
    if "consistency_success_pct" not in merged:
        merged["consistency_success_pct"] = None
    audit = _restore_audit_block()
    if audit:
        merged["restore_audit"] = audit
    out = repo / RESULT_JSON
    out.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return merged


def main(argv: list[str]) -> int:
    repo = _repo_root()
    env_slug = _env_folder_slug()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if len(argv) < 2:
        _print_restore_failure("usage", "argumentos em falta — indique o ficheiro ou pasta encriptada")
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

    _print_restore_start(env_slug)

    enc_arg = Path(argv[1]).expanduser()
    if not enc_arg.is_absolute():
        enc_arg = (repo / enc_arg).resolve()
    enc_path = _resolve_encrypted(enc_arg)
    if enc_path is None:
        _print_restore_failure("resolve_encrypted", f"ficheiro encriptado BEA1 não encontrado em {enc_arg}")
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
        _print_restore_failure("parse_key", str(exc))
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
            _print_restore_failure("decrypt", str(exc))
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
            _print_restore_failure("copy_db", str(exc))
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
        _print_restore_failure("gather_evidence", str(exc))
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
    merged = _write_result(repo, payload)
    if ok:
        _print_restore_success()
    else:
        if not integrity_ok:
            detail = f"integrity_check={ic!r}, foreign_key_violations={fk}"
            _print_restore_failure("validação_integridade", detail)
        elif compared > 0 and pct < 100.0:
            _print_restore_failure(
                "validação_consistência",
                f"consistência {pct}% ({matched}/{compared} tabelas alinhadas com o último backup)",
            )
        else:
            _print_restore_failure("validação_final", "falha não classificada após restore")
    print(json.dumps(merged, ensure_ascii=False))

    if not integrity_ok:
        return 8
    if compared > 0 and pct < 100.0:
        return 9
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
