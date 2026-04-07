"""Dashboard do Fluxo oficial — telemetria ao vivo + Torre de Controle + estado (JSON)."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None  # pragma: no cover — CI instala requirements.txt

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


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


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


def _render_status_live(data: dict) -> None:
    st.subheader("STATUS LIVE — telemetria")
    st.caption(
        "Operação actual da **EQUIPE** e fila imediata (ficheiro `status_demanda.json` no disco). "
        "O **Painel** `.md` mantém o histórico nos PCs."
    )

    live = data.get("live_status")
    if live is None:
        live = ""
    live_s = str(live).strip()
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


def render_page_fluxo_gestao(
    *,
    render_back_and_breadcrumb,
) -> None:
    render_back_and_breadcrumb(
        ["Home", "Fluxo e governança"],
        back_key="bea_back_fluxo",
    )
    st.markdown("### Fluxo e governança")
    st.caption(
        "**STATUS LIVE** + **Torre de Controle**. Fonte: `docs/governanca/status_demanda.json`. "
        "Entrada: **`@Files` → Analista**. Norma: `FLUXO_SUCESSO_E_FALHA.md` (Fluxo oficial)."
    )

    data = carregar_status_demanda()
    if "erro" in data:
        st.error(str(data["erro"]))
        return

    c_auto, c_btn, _ = st.columns([2, 1, 2])
    with c_auto:
        auto = st.checkbox(
            "Renovar página automaticamente (10 s)",
            value=True,
            key="bea_fluxo_autorefresh",
        )
    with c_btn:
        if st.button("Actualizar agora", key="bea_fluxo_manual"):
            st.rerun()

    if auto and st_autorefresh is not None:
        st_autorefresh(interval=10_000, key="bea_fluxo_live_tick")

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

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Demanda", data.get("demanda_id") or "—")
    with c2:
        st.metric("Fase / passo", str(data.get("fase_actual") or "—"))
    with c3:
        st.metric("Responsável", str(data.get("responsavel_actual") or "—"))

    ultima = data.get("ultima_entrega_marco")
    if ultima:
        st.metric("Último marco de produto", str(ultima))

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
        "Dossiers: `docs/governanca/demandas/<ID>/` · Painel executivo: `docs/PAINEL_OPERACIONAL.md`"
    )
