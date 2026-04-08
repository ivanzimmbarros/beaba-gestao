"""
Monitor de Voo — telemetria E14 + Torre de Controle + Diário (stand-alone).

Arranque (raiz do repositório): streamlit run monitor_governanca.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None  # pragma: no cover

_FASES_DEFAULT = [
    {"id": "A", "label": "Desenho", "pcs": "PC1→2", "estado": "pendente"},
    {"id": "B", "label": "Lógico", "pcs": "PC3→4", "estado": "pendente"},
    {"id": "C", "label": "Código 1", "pcs": "PC5→6", "estado": "pendente"},
    {"id": "D", "label": "Código 2", "pcs": "PC7→8", "estado": "pendente"},
    {"id": "E", "label": "QA", "pcs": "PC9–12", "estado": "pendente"},
    {"id": "F", "label": "Fecho", "pcs": "PC13", "estado": "pendente"},
]

_ICONE_ESTADO = {
    "feito": "🟢",
    "curso": "🔵",
    "pendente": "⚪",
    "correccao": "🟠",
}

_LIVE_FILA_MAX = 8
_AUTOREFRESH_MS = 10_000

_BACKUP_GROUP_KEYS = (
    "ambiente",
    "estrutura",
    "configuracao",
    "arquivos",
    "user_data",
    "logs",
)
_BACKUP_GROUP_LABELS = {
    "ambiente": "Ambiente",
    "estrutura": "Estrutura",
    "configuracao": "Config",
    "arquivos": "Arquivos",
    "user_data": "User Data",
    "logs": "Logs",
}


def _backup_status_icon(status: str | None) -> str:
    s = (status or "").strip().lower()
    if s == "ok":
        return "✅"
    if s == "warn":
        return "⚠️"
    if s == "fail":
        return "❌"
    return "⚪"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent


def _path_backup_dr_history() -> Path:
    return _repo_root() / "docs" / "governanca" / "telemetry" / "backup_dr_history.json"


def carregar_backup_dr_history() -> tuple[list[dict], str | None]:
    """
    Lê `docs/governanca/telemetry/backup_dr_history.json` de forma resiliente.

    Retorna (runs, aviso): `runs` só inclui entradas que são dict; `aviso` é mensagem
    para o utilizador se o ficheiro falhar, estiver vazio ou o JSON for inválido.
    """
    p = _path_backup_dr_history()
    if not p.is_file():
        return [], (
            "Ficheiro de telemetria **não encontrado**: `docs/governanca/telemetry/backup_dr_history.json`. "
            "O Monitor continua operacional; aguarde commit inicial ou restaure o ficheiro."
        )
    try:
        raw = p.read_text(encoding="utf-8")
    except OSError as exc:
        return [], f"Não foi possível ler a telemetria de backup: {exc}"

    stripped = raw.strip()
    if not stripped:
        return [], (
            "Ficheiro de telemetria **vazio** — sem dados JSON. "
            "Preenchimento previsto pelos workflows E17.1 (`runs` permanece `[]` até primeira execução)."
        )
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as exc:
        return [], f"**JSON inválido** em `backup_dr_history.json`: {exc}"

    if not isinstance(data, dict):
        return [], "Conteúdo de telemetria inválido: raiz deve ser um objecto JSON."

    runs = data.get("runs")
    if runs is None:
        return [], (
            "Campo **`runs`** ausente — schema esperado: "
            '`{"schema_version": 1, "runs": []}`.'
        )
    if not isinstance(runs, list):
        return [], "Campo **`runs`** deve ser uma lista."

    clean = [r for r in runs if isinstance(r, dict)]
    return clean, None


def carregar_status_demanda() -> dict:
    p = _repo_root() / "docs" / "governanca" / "status_demanda.json"
    if not p.is_file():
        return {"erro": f"Ficheiro não encontrado: {p}"}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return {"erro": f"JSON inválido: {e}"}


def _fases_para_exibir(data: dict) -> list[dict]:
    raw = data.get("fases_resumo")
    if not isinstance(raw, list) or len(raw) != 6:
        return list(_FASES_DEFAULT)
    out = []
    for i, row in enumerate(raw):
        if not isinstance(row, dict):
            return list(_FASES_DEFAULT)
        estado = str(row.get("estado") or "pendente").lower()
        if estado not in _ICONE_ESTADO:
            estado = "pendente"
        out.append(
            {
                "id": str(row.get("id") or _FASES_DEFAULT[i]["id"]),
                "label": str(row.get("label") or _FASES_DEFAULT[i]["label"]),
                "pcs": str(row.get("pcs") or _FASES_DEFAULT[i]["pcs"]),
                "estado": estado,
            }
        )
    return out


def _render_secoes_painel_demandas(data: dict) -> None:
    """Painel v2: épicos em execução vs histórico concluído (`status_demanda.json`)."""
    sec_ab = data.get("secao_epicos_em_execucao")
    sec_hi = data.get("secao_historico_epicos_concluidos")
    if not isinstance(sec_ab, dict) and not isinstance(sec_hi, dict):
        return

    st.subheader("Painel de demandas (layout v2)")
    if isinstance(sec_ab, dict):
        st.markdown(f"**{sec_ab.get('titulo') or '[SEÇÃO: ÉPICOS EM EXECUÇÃO]'}**")
        if sec_ab.get("descricao"):
            st.caption(str(sec_ab["descricao"]))
        itens = sec_ab.get("itens")
        if isinstance(itens, list) and itens:
            for ep in itens:
                if not isinstance(ep, dict):
                    continue
                st.markdown(
                    f"- **{ep.get('titulo', '—')}** (`{ep.get('demanda_id', '—')}`) — "
                    f"**{ep.get('status_demanda', '—')}** · Fase {ep.get('fase_actual', '—')} · PC {ep.get('pc_foco', '—')}"
                )
                if ep.get("resumo_foco"):
                    st.caption(str(ep["resumo_foco"]))
        else:
            st.info("Nenhum épico em «Em Aberto» ou «Pendente».")

    st.divider()

    if isinstance(sec_hi, dict):
        st.markdown(f"**{sec_hi.get('titulo') or '[SEÇÃO: HISTÓRICO DE ÉPICOS CONCLUÍDOS]'}**")
        if sec_hi.get("descricao"):
            st.caption(str(sec_hi["descricao"]))
        itens = sec_hi.get("itens")
        if isinstance(itens, list) and itens:
            for ep in itens:
                if not isinstance(ep, dict):
                    continue
                st.markdown(
                    f"**{ep.get('data_conclusao', '—')}** — **{ep.get('titulo', '—')}** "
                    f"— `{ep.get('demanda_id', '—')}` — *{ep.get('status_demanda', 'CONCLUÍDO')}*"
                )
                if ep.get("entrega"):
                    st.caption(f"Entrega: {ep['entrega']}")
                if ep.get("validacao"):
                    st.caption(f"Validação: {ep['validacao']}")
                refs = ep.get("refs_docs")
                if isinstance(refs, list) and refs:
                    st.markdown("Documentos (auditoria):")
                    for r in refs:
                        st.markdown(f"- `{r}`")
        else:
            st.caption("Histórico vazio.")

    st.divider()


def _render_status_live(data: dict) -> None:
    st.subheader("STATUS LIVE — telemetria")
    st.caption(
        "Operação actual da **EQUIPE** e fila imediata (`status_demanda.json` no disco). "
        "O **Painel** `.md` mantém o histórico nos PCs."
    )

    live = data.get("live_status")
    live_s = str(live).strip() if live is not None else ""
    fila_raw = data.get("etapas_pendentes")
    if not isinstance(fila_raw, list):
        fila: list[str] = []
    else:
        fila = [str(x) for x in fila_raw if str(x).strip()]
    ts = data.get("live_actualizado_iso")
    ts_s = str(ts).strip() if ts is not None else ""

    if live_s:
        with st.container():
            st.markdown("🔄 **Em execução**")
            st.info(live_s)
    else:
        st.success("Sem actividade registada em `live_status` — repouso ou aguarda próxima microtarefa.")

    if fila:
        st.markdown("**Fila imediata**")
        for i, item in enumerate(fila[:_LIVE_FILA_MAX], start=1):
            st.markdown(f"{i}. {item}")
        if len(fila) > _LIVE_FILA_MAX:
            st.caption(f"… e mais {len(fila) - _LIVE_FILA_MAX} item(ns).")
    else:
        st.caption("Fila vazia (`etapas_pendentes`).")

    st.caption(f"**Última actualização telemetria:** {ts_s or '—'}")


def _render_governanca_tab(data: dict) -> None:
    _render_secoes_painel_demandas(data)
    _render_status_live(data)

    st.divider()

    percurso = str(data.get("percurso") or "normal")
    if percurso == "correccao" or data.get("falha"):
        st.warning("**Percurso de correção (FALHA)** — revalidar etapas afectadas conforme norma.")

    st.subheader("Torre de Controle")
    st.caption("🟢 feito · 🔵 em curso · ⚪ pendente · 🟠 correção")
    fases = _fases_para_exibir(data)
    cols = st.columns(6)
    for col, f in zip(cols, fases):
        ic = _ICONE_ESTADO.get(f["estado"], "⚪")
        with col:
            st.markdown(f"**{ic} Fase {f['id']}**")
            st.caption(f["label"])
            st.caption(f["pcs"])

    pc_foco = data.get("pc_foco")
    fg = data.get("fase_governanca")
    if pc_foco or (fg and str(fg).strip() and str(fg) != "—"):
        st.info(
            f"**Fase governança:** {fg or '—'} · **PC em foco:** {pc_foco or '—'}"
        )

    ultima = data.get("ultima_entrega_marco")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Demanda", data.get("demanda_id") or "—")
    with c2:
        st.metric("Fase / passo", str(data.get("fase_actual") or "—"))
    with c3:
        st.metric("Responsável", str(data.get("responsavel_actual") or "—"))
    with c4:
        st.metric("Último marco de produto", str(ultima) if ultima else "—")

    diario = data.get("diario_bordo_resumo")
    if isinstance(diario, list) and diario:
        st.subheader("Diário de Bordo (resumo)")
        for linha in diario:
            st.markdown(f"- {linha}")

    st.subheader("Pendente")
    st.write(str(data.get("pendente") or "—"))

    with st.expander("Pontos de controlo concluídos"):
        done = data.get("pontos_controlo_concluidos") or []
        if done:
            for x in done:
                st.success(str(x))
        else:
            st.caption("Nenhum PC listado.")

    falha = data.get("falha")
    with st.expander("Falha / fluxo reverso (detalhe)"):
        if falha:
            st.error(json.dumps(falha, ensure_ascii=False, indent=2))
        else:
            st.caption("Sem falha registada.")

    with st.expander("JSON completo (auditoria)"):
        st.code(json.dumps(data, ensure_ascii=False, indent=2), language="json")

    st.divider()
    st.caption(
        "Dossiers: `docs/governanca/demandas/<ID>/` · Painel executivo: `docs/PAINEL_OPERACIONAL.md` · "
        "Norma: `docs/governanca/FLUXO_SUCESSO_E_FALHA.md`"
    )


def _render_backup_dr_tab() -> None:
    st.subheader("Controle de Backup e Restore (E17.1)")
    st.caption(
        "Histórico canónico: `docs/governanca/telemetry/backup_dr_history.json` "
        "(workflows `backup_hourly` / `restore_weekly` + commits do bot)."
    )

    runs, aviso = carregar_backup_dr_history()
    if aviso:
        st.warning(aviso)

    if not runs:
        st.info(
            "⚪ **Sem execuções registadas** — `runs` está vazio ou indisponível. "
            "Dispare `backup_hourly` (workflow_dispatch) após configurar `BEABA_BACKUP_KEY`."
        )
        return

    st.success(f"**{len(runs)}** execução(ões) registadas.")

    rows_main: list[dict] = []
    rows_matrix: list[dict] = []
    for r in runs:
        if not isinstance(r, dict):
            continue
        g = r.get("groups")
        if not isinstance(g, dict):
            g = {}
        log_u = str(r.get("workflow_run_url") or r.get("log_url") or "").strip()
        row_m: dict = {
            "Início (UTC)": str(r.get("started_at") or "—"),
            "Tipo": str(r.get("type") or "—"),
            "Overall": _backup_status_icon(str(r.get("overall") or "")),
            "Duração s": r.get("duration_seconds", "—"),
            "SHA": (str(r.get("git_sha") or "")[:7] + "…") if r.get("git_sha") else "—",
            "Log (URL)": log_u if log_u else "—",
        }
        for k in _BACKUP_GROUP_KEYS:
            sg = g.get(k)
            stt = (sg.get("status") if isinstance(sg, dict) else None) or ""
            row_m[_BACKUP_GROUP_LABELS[k]] = _backup_status_icon(stt)
        rows_main.append(row_m)

        rm = {
            "Ano-Mês-Dia": str(r.get("started_at") or "")[:10],
            "Hora": str(r.get("started_at") or "")[11:16],
            "Tipo": str(r.get("type") or "—"),
        }
        for k in _BACKUP_GROUP_KEYS:
            sg = g.get(k)
            stt = (sg.get("status") if isinstance(sg, dict) else None) or ""
            rm[_BACKUP_GROUP_LABELS[k]] = _backup_status_icon(stt)
        rows_matrix.append(rm)

    df_main = pd.DataFrame(rows_main)
    st.markdown("### Tabela de execuções")
    st.dataframe(df_main, hide_index=True, width="stretch")
    st.markdown("**Links rápidos (Markdown)**")
    for r in runs[:8]:
        if not isinstance(r, dict):
            continue
        u = str(r.get("workflow_run_url") or r.get("log_url") or "").strip()
        if u:
            st.markdown(f"- `{r.get('started_at')}` — [{u}]({u})")

    st.markdown("### Matriz temporal (ícones por grupo)")
    st.caption("Colunas: Ambiente, Estrutura, Config, Arquivos, User Data, Logs — ✅ ok · ⚠️ aviso · ❌ falha · ⚪ desconhecido")
    df_mat = pd.DataFrame(rows_matrix)
    st.dataframe(df_mat, hide_index=True, width="stretch")

    with st.expander("Detalhe textual por grupo (última execução)"):
        last = runs[0] if runs else {}
        if isinstance(last, dict):
            lg = last.get("groups")
            if isinstance(lg, dict):
                for k in _BACKUP_GROUP_KEYS:
                    block = lg.get(k)
                    if isinstance(block, dict):
                        st.markdown(f"**{_BACKUP_GROUP_LABELS[k]}** ({block.get('status', '—')})")
                        st.caption(str(block.get("detail") or "—"))
            st.json(last)

    with st.expander("JSON bruto (auditoria)"):
        st.code(json.dumps(runs[:20], ensure_ascii=False, indent=2), language="json")


def main() -> None:
    st.set_page_config(
        page_title="Monitor de Voo — Governança BeaBa",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.markdown("## Monitor de Voo")
    st.caption(
        "Telemetria e fluxo oficial — leitura directa de `docs/governanca/status_demanda.json`. "
        "Entrada: **`@Files` → Analista**. Norma: `FLUXO_SUCESSO_E_FALHA.md`."
    )

    if st_autorefresh is None:
        st.error(
            "Pacote **streamlit-autorefresh** não encontrado. Instale com: `pip install streamlit-autorefresh`."
        )
    else:
        st_autorefresh(interval=_AUTOREFRESH_MS, key="bea_monitor_live_tick")
        st.caption(
            f"Renovação automática a cada {_AUTOREFRESH_MS // 1000} s. Feche o separador para parar refreshes."
        )

    c_btn, _ = st.columns([1, 4])
    with c_btn:
        if st.button("Actualizar agora", key="bea_monitor_manual"):
            st.rerun()

    data = carregar_status_demanda()
    if "erro" in data:
        st.error(str(data["erro"]))
        return

    tab_gov, tab_backup = st.tabs(["Governança", "Backup e Restore"])
    with tab_gov:
        _render_governanca_tab(data)
    with tab_backup:
        _render_backup_dr_tab()


main()
