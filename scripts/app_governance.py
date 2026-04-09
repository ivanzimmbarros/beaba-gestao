#!/usr/bin/env python3
"""
Dashboard Web Streamlit — Governança E17.2 (status + backup + cláusulas .cursorrules).

Arranque (raiz do repositório):
  streamlit run scripts/app_governance.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from monitor_governanca import (  # noqa: E402
    _BACKUP_GROUP_KEYS,
    _BACKUP_GROUP_LABELS,
    _ICONE_ESTADO,
    _backup_status_icon,
    carregar_backup_dr_history,
    carregar_status_demanda,
)

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None

_AUTOREFRESH_MS = 15_000
_APP_VERSION = "E17.2 Web"


def _fases_para_exibir(data: dict) -> list[dict]:
    raw = data.get("fases_resumo")
    default = [
        {"id": "A", "label": "Desenho", "pcs": "PC1→2", "estado": "pendente"},
        {"id": "B", "label": "Lógico", "pcs": "PC3→4", "estado": "pendente"},
        {"id": "C", "label": "Código 1", "pcs": "PC5→6", "estado": "pendente"},
        {"id": "D", "label": "Código 2", "pcs": "PC7→8", "estado": "pendente"},
        {"id": "E", "label": "QA", "pcs": "PC9–12", "estado": "pendente"},
        {"id": "F", "label": "Fecho", "pcs": "PC13", "estado": "pendente"},
    ]
    if not isinstance(raw, list) or len(raw) != 6:
        return list(default)
    out = []
    for i, row in enumerate(raw):
        if not isinstance(row, dict):
            return list(default)
        estado = str(row.get("estado") or "pendente").lower()
        if estado not in _ICONE_ESTADO:
            estado = "pendente"
        out.append(
            {
                "id": str(row.get("id") or default[i]["id"]),
                "label": str(row.get("label") or default[i]["label"]),
                "pcs": str(row.get("pcs") or default[i]["pcs"]),
                "estado": estado,
            }
        )
    return out


def _fase_weight(estado: str) -> float:
    e = (estado or "").strip().lower()
    if e == "feito":
        return 1.0
    if e in ("curso", "em curso", "andamento"):
        return 0.5
    return 0.0


def _sprint_progress_pct(fases: list[dict]) -> float:
    if not fases:
        return 0.0
    w = sum(_fase_weight(f.get("estado", "")) for f in fases)
    return round(100.0 * w / len(fases), 1)


def _clauses_from_cursorrules(path: Path) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame(columns=["Secção", "Cláusula", "Revisado (sessão)"])
    section = "Preâmbulo"
    rows: list[dict] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if line.startswith("### "):
            section = f"{section} · {line[4:].strip()}"
            continue
        s = line.strip()
        if not s or s == "---":
            continue
        if s.startswith(("- ", "* ")):
            rows.append({"Secção": section, "Cláusula": s[2:].strip(), "Revisado (sessão)": False})
        elif len(s) > 2 and s[0].isdigit():
            head = s.split(".", 1)[0]
            if head.isdigit() and int(head) < 30:
                rows.append({"Secção": section, "Cláusula": s, "Revisado (sessão)": False})
    return pd.DataFrame(rows)


def _backup_runs_table(runs: list[dict]) -> pd.DataFrame:
    rows_main: list[dict] = []
    for r in runs:
        if not isinstance(r, dict):
            continue
        g = r.get("groups") if isinstance(r.get("groups"), dict) else {}
        log_u = str(r.get("workflow_run_url") or r.get("log_url") or "").strip()
        snap = r.get("snapshot_table_counts")
        snap_s = json.dumps(snap, ensure_ascii=False) if isinstance(snap, dict) else "—"
        row_m = {
            "Início (UTC)": str(r.get("started_at") or "—"),
            "Tipo": str(r.get("type") or "—"),
            "Overall": _backup_status_icon(str(r.get("overall") or "")),
            "Duração s": r.get("duration_seconds", "—"),
            "snapshot_table_counts": snap_s[:200] + ("…" if len(snap_s) > 200 else ""),
            "Log": log_u if log_u else "—",
        }
        for k in _BACKUP_GROUP_KEYS:
            sg = g.get(k)
            stt = (sg.get("status") if isinstance(sg, dict) else None) or ""
            row_m[_BACKUP_GROUP_LABELS[k]] = _backup_status_icon(stt)
        rows_main.append(row_m)
    return pd.DataFrame(rows_main)


def _restore_rows(runs: list[dict]) -> pd.DataFrame:
    out: list[dict] = []
    for r in runs:
        if not isinstance(r, dict) or r.get("type") != "restore_proof":
            continue
        ev = r.get("evidence") if isinstance(r.get("evidence"), dict) else {}
        tc = ev.get("table_counts")
        tc_s = json.dumps(tc, ensure_ascii=False) if isinstance(tc, dict) else "—"
        out.append(
            {
                "Início (UTC)": str(r.get("started_at") or "—"),
                "integrity_check": str(ev.get("integrity_check") or "—"),
                "FK violations": ev.get("foreign_key_violations", "—"),
                "table_counts": tc_s[:300] + ("…" if len(tc_s) > 300 else ""),
                "Log": str(r.get("workflow_run_url") or r.get("log_url") or "—"),
            }
        )
    return pd.DataFrame(out)


def _local_restore_result() -> dict | None:
    p = _ROOT / "restore_result.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def main() -> None:
    st.set_page_config(
        page_title="Governança BeaBa — E17.2",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.sidebar.title("Protocolo **E17.2**")
    st.sidebar.success("Dashboard Web operacional")
    st.sidebar.caption(f"App: **{_APP_VERSION}**")
    st.sidebar.caption(f"Streamlit {st.__version__}")
    st.sidebar.caption(f"Python {sys.version.split()[0]}")
    st.sidebar.divider()
    st.sidebar.markdown(
        "**Branch técnica:** `backup-and-restore` — restore local (`restore_sqlite.py`) e "
        "`test_restore_weekly.yml`. **Integração:** `develop`."
    )

    st.markdown("## Dashboard Web — Governança (E17.2)")
    st.caption(
        "Fontes: `docs/governanca/status_demanda.json` · "
        "`docs/governanca/telemetry/backup_dr_history.json` · `.cursorrules`"
    )

    if st_autorefresh is not None:
        st_autorefresh(interval=_AUTOREFRESH_MS, key="bea_gov_web_tick")
        st.caption(f"Actualização automática a cada {_AUTOREFRESH_MS // 1000} s.")
    else:
        st.warning("Instale `streamlit-autorefresh` para refreshes automáticos.")

    if st.button("Actualizar agora", key="gov_refresh"):
        st.rerun()

    data = carregar_status_demanda()
    if "erro" in data:
        st.error(str(data["erro"]))
        return

    live = str(data.get("live_status") or "—")
    st.info(f"**Live status:** {live}")

    fases = _fases_para_exibir(data)
    pct = _sprint_progress_pct(fases)
    st.subheader("Progresso da sprint (fases A–F)")
    st.progress(min(max(pct / 100.0, 0.0), 1.0))
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Progresso global", f"{pct}%")
    with c2:
        st.metric("Fase / PC foco", f"{data.get('fase_actual') or '—'} · {data.get('pc_foco') or '—'}")
    with c3:
        st.metric("Demanda", str(data.get("demanda_id") or "—"))

    st.markdown("### Etapas")
    cols = st.columns(6)
    for col, f in zip(cols, fases):
        ic = _ICONE_ESTADO.get(f["estado"], "⚪")
        with col:
            st.markdown(f"**{ic} {f['id']}** — {f['label']}")
            st.caption(f["pcs"])
            st.caption(f"_{f['estado']}_")

    st.divider()
    st.subheader("Backup e teste de restore")

    runs, aviso = carregar_backup_dr_history()
    if aviso:
        st.warning(aviso)

    backups = [r for r in runs if isinstance(r, dict) and r.get("type") == "backup"][:12]
    restores = [r for r in runs if isinstance(r, dict) and r.get("type") == "restore_proof"][:12]

    st.markdown("#### Últimos backups (telemetria)")
    if backups:
        df_b = _backup_runs_table(backups)
        st.dataframe(df_b, hide_index=True, width="stretch")
        chart_df = pd.DataFrame(
            {
                "run": [str(x.get("started_at") or "")[:16] for x in backups],
                "overall": [str(x.get("overall") or "—") for x in backups],
            }
        )
        chart_df["n"] = 1
        fig = px.bar(
            chart_df,
            x="run",
            y="n",
            color="overall",
            title="Overall dos últimos backups",
            labels={"run": "Início (UTC truncado)", "n": ""},
        )
        fig.update_layout(showlegend=True, yaxis_visible=False, yaxis_showticklabels=False)
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("Sem registos de tipo `backup` em `backup_dr_history.json`.")

    st.markdown("#### Teste de restore (telemetria `restore_proof`)")
    df_r = _restore_rows(restores)
    if not df_r.empty:
        st.dataframe(df_r, hide_index=True, width="stretch")
    else:
        st.caption("Sem execuções `restore_proof` na telemetria.")

    loc = _local_restore_result()
    st.markdown("#### Resultado local (`restore_result.json` na raiz do repo)")
    if loc:
        pct_loc = loc.get("consistency_success_pct")
        st.metric(
            "Integridade vs último backup (telemetria)",
            f"{pct_loc}%" if pct_loc is not None else "N/D",
        )
        st.json(loc)
    else:
        st.caption("Ficheiro ausente — execute `scripts/restore_sqlite.py` na branch `backup-and-restore` para gerar.")

    st.divider()
    st.subheader("Checklist de cláusulas (.cursorrules)")
    st.caption("Marcações são apenas da **sessão** Streamlit (não gravam no repositório).")
    cr_path = _ROOT / ".cursorrules"
    clauses_df = _clauses_from_cursorrules(cr_path)
    if clauses_df.empty:
        st.warning("Não foi possível extrair cláusulas de `.cursorrules`.")
    else:
        edited = st.data_editor(
            clauses_df,
            hide_index=True,
            width="stretch",
            num_rows="fixed",
            column_config={
                "Revisado (sessão)": st.column_config.CheckboxColumn(
                    "Revisado (sessão)",
                    help="Checklist local ao Diretor nesta sessão.",
                    default=False,
                ),
                "Cláusula": st.column_config.TextColumn(width="large"),
            },
            key="cursorrules_checklist",
        )
        st.caption(f"**{len(edited)}** cláusulas listadas.")

    with st.expander("JSON status_demanda (auditoria)"):
        st.code(json.dumps(data, ensure_ascii=False, indent=2), language="json")


if __name__ == "__main__":
    main()
