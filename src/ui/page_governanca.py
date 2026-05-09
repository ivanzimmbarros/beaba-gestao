"""
Painel para administradores — cópias de segurança, sync cloud e estado de restores.

Navegação apenas com perfil ``admin``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from src.database.connection import env_type_display_label_pt, get_beaba_env_type_raw
from src.modules.audit import listar_auditoria
from src.ui.constituicao_visual_shell import inject_constituicao_gov_page


DRILL_JSON = str(Path("docs") / "governanca" / "telemetry" / "staging_restore_drill_state.json")


def _env_folder_slug(raw: str) -> str:
    k = str(raw or "").strip().lower()
    if k in ("production", "prod", "main"):
        return "prod"
    if k in ("staging", "stg"):
        return "stg"
    return "dev"


def _repo_root() -> Path:
    raw = os.environ.get("BEABA_REPO_ROOT", "").strip()
    if raw:
        return Path(raw).resolve()
    return Path(__file__).resolve().parents[2]


def _tail_log_lines(path: Path, max_lines: int = 200) -> list[str]:
    if not path.is_file():
        return []
    raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return raw[-max_lines:] if len(raw) > max_lines else raw


def _read_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _run_script(repo: Path, relative: str) -> tuple[int, str, str]:
    script = repo / relative
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def render_page_governanca() -> None:
    inject_constituicao_gov_page()
    st.title("Governança")
    repo = _repo_root()
    env_slug = get_beaba_env_type_raw()
    env_folder = _env_folder_slug(env_slug)

    st.caption(
        f"Ambiente registado como **{env_type_display_label_pt()}** (`ENV_TYPE={env_slug}`)."
    )

    tab_backups, tab_audit = st.tabs(
        ["Cópias de segurança e recuperação", "Auditoria de utilizadores e acessos"]
    )

    with tab_backups:
        _render_governanca_backups(repo, env_slug, env_folder)

    with tab_audit:
        _render_governanca_auditoria_acessos()


def _render_governanca_backups(repo: Path, env_slug: str, env_folder: str) -> None:
    st.subheader("Cópias de segurança e ferramentas")

    log_path = repo / "backups" / env_folder / "logs" / "backup_hourly.log"
    lines = _tail_log_lines(log_path)
    st.subheader(f"Log horário (`backups/{env_folder}/logs/backup_hourly.log`)")
    if not lines:
        st.info("Ainda não existe log legível.")
    else:
        st.dataframe(
            pd.DataFrame({"linha": lines}),
            hide_index=True,
            width="stretch",
            height=min(420, 24 * len(lines) + 42),
        )

    st.divider()
    gh_path = repo / "gha_restore_state.json"
    drill_path = repo / DRILL_JSON

    st.subheader("Estados de recuperação")

    gh = _read_json(gh_path)
    if gh:
        # Resumo compatível CI GHA restore job
        row = pd.DataFrame(
            [
                {
                    "tipo": gh.get("type", ""),
                    "início": gh.get("started_at", ""),
                    "fim": gh.get("finished_at", ""),
                    "duração_s": gh.get("duration_seconds"),
                    "git_ref": gh.get("git_ref", ""),
                    "git_sha": (gh.get("git_sha") or "")[:12],
                    "passos": json.dumps(gh.get("steps", {}), ensure_ascii=False)[:4000],
                }
            ]
        )
        with st.expander("Último `gha_restore_state.json`"):
            st.dataframe(row, hide_index=True, width="stretch")
            st.download_button(
                label="Baixar JSON completo (`gha_restore_state.json`)",
                data=json.dumps(gh, ensure_ascii=False, indent=2),
                file_name="gha_restore_state.json",
                mime="application/json",
            )
    else:
        st.markdown("Sem `gha_restore_state.json` nesta raiz.")

    drill = _read_json(drill_path)
    if drill:
        dm = pd.DataFrame(
            [
                {
                    "ok": drill.get("ok"),
                    "início": drill.get("started_at", ""),
                    "fim": drill.get("finished_at", ""),
                    "chave_prod": drill.get("prod_remote_key"),
                    "verificado": drill.get("verify_ok"),
                    "mensagem": drill.get("verify_message", ""),
                    "erro": drill.get("error", ""),
                    "objectos_em_prod": drill.get("production_encrypted_objects_seen"),
                }
            ]
        )
        with st.expander("Último drill staging (`staging_restore_drill_state.json`)"):
            st.dataframe(dm, hide_index=True, width="stretch")
            st.download_button(
                label="Baixar JSON completo do drill",
                data=json.dumps(drill, ensure_ascii=False, indent=2),
                file_name="staging_restore_drill_state.json",
                mime="application/json",
            )
    else:
        st.markdown("Sem `staging_restore_drill_state.json` (drill automático ou manual em staging).")

    st.divider()
    st.subheader("Relatório de Auditoria de Dados (Drill)")
    if not drill:
        st.info("Sem relatório de auditoria ainda (execute o drill em staging ou aguarde o cron semanal).")
    else:
        ok = bool(drill.get("ok"))
        finished = str(drill.get("finished_at") or drill.get("finished_at_utc") or drill.get("started_at") or "").strip()
        proof = drill.get("row_counts_proof") if isinstance(drill.get("row_counts_proof"), dict) else {}
        clientes = proof.get("clientes")
        vendas = proof.get("vendas")
        err = str(drill.get("error") or drill.get("verify_message") or "").strip()
        rpo_status = str(drill.get("rpo_status") or "").strip().lower()
        rpo_msg = str(drill.get("rpo_message") or "").strip()

        def _fmt_int(v) -> str:
            try:
                return f"{int(v):,}".replace(",", ".")
            except (TypeError, ValueError):
                return "—"

        if rpo_status:
            icon = "✅" if rpo_status == "cumprido" else "⚠️"
            st.markdown(f"**RPO (1h):** {icon} {rpo_msg or '—'}")

        if ok:
            msg = (
                f"Staging sincronizado com Produção em {finished} — "
                f"{_fmt_int(clientes)} clientes validados; {_fmt_int(vendas)} vendas."
            )
            st.success(msg)
        else:
            st.error(f"Falha na auditoria (drill). Detalhe técnico: {err or '(sem detalhe)'}")

    st.divider()

    col_a, col_b = st.columns(2)

    if col_a.button("Executar Backup Agora", type="primary"):
        rc1, _, _ = _run_script(repo, "scripts/backup_sqlite_hourly.py")
        if rc1 != 0:
            st.error(f"Backup horário falhou (rc={rc1}). Veja cópias e logs.")
        else:
            st.success("Backup horário terminou.")
            rc2, cout, cerr = _run_script(repo, "scripts/backup_sync_cloud.py")
            if cerr:
                with st.expander("Stdout / stderr (`backup_sync_cloud`)"):
                    st.code((cout + "\n" + cerr).strip())
            if rc2 != 0:
                st.error(f"Sincronização cloud falhou (rc={rc2}). Credenciais S3/`BEABA_BACKUP_KEY`?")
            else:
                st.success("Sincronização cloud terminou.")

    if env_slug in ("staging", "stg"):
        if col_b.button("Correr drill de restore (produção → staging)"):
            rc, sout, serr = _run_script(repo, "scripts/restore_test_drill.py")
            blk = "\n".join(x for x in (sout, serr) if x).strip()
            if blk:
                with st.expander("Saída do drill"):
                    st.code(blk)
            if rc != 0:
                st.error(f"Drill terminou com rc={rc}")
            else:
                st.success("Drill terminou.")
            st.rerun()
    else:
        col_b.caption(
            "O drill de restore substitui o SQLite desta máquina; só está disponível com `ENV_TYPE=staging`."
        )


def _render_governanca_auditoria_acessos() -> None:
    st.subheader("Auditoria de utilizadores e acessos")
    st.caption("Registo de operações relacionadas com autenticação e gestão de utilizadores.")

    filtro_rotulo = {
        "Todos": None,
        "auth (login, senhas)": "auth",
        "usuarios (CRUD utilizadores)": "usuarios",
    }
    op = st.selectbox(
        "Filtrar registos por módulo",
        options=list(filtro_rotulo.keys()),
        index=0,
        help="'auth': tentativas de login e alterações de senha. 'usuarios': criação e edição de contas.",
    )
    modulo = filtro_rotulo[op]

    rows = listar_auditoria(limite=200, modulo_filtro=modulo)
    if not rows:
        st.info("Sem registos de auditoria neste filtro.")
        return

    df = pd.DataFrame(
        [
            {
                "Data/Hora": r["criado_em_exibicao_pt"],
                "Ator (E-mail)": r["ator_email"] or "—",
                "Ação": r["acao"] or "—",
                "Módulo": r["modulo"] or "—",
                "Detalhes (ID)": (r["registro_id"].strip() if r["registro_id"].strip() else "—"),
            }
            for r in rows
        ]
    )
    kw: dict[str, object] = {
        "hide_index": True,
        "width": "stretch",
        "height": min(460, max(280, len(df) * 36 + 48)),
        "disabled": True,
    }
    try:
        st.dataframe(df, **kw)
    except TypeError:
        kw.pop("disabled", None)
        st.dataframe(df, **kw)
