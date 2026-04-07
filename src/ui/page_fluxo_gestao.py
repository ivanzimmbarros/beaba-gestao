"""Dashboard de status do Fluxo oficial de governança (governança)."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st


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
        "Estado da evolução (**Fluxo oficial de governança**: percurso normal ou correção). "
        "Fonte: `docs/governanca/status_demanda.json`. "
        "Entrada da demanda: Cursor **@Files** → Analista. **EQUIPE** mantém este JSON, o Git e o Painel — "
        "sem exigir documentação manual do Diretor."
    )
    st.markdown(
        "Documentação normativa (**nome do ficheiro histórico**): `docs/governanca/FLUXO_SUCESSO_E_FALHA.md` · "
        "`docs/governanca/demandas/README.md`"
    )

    data = carregar_status_demanda()
    if "erro" in data:
        st.error(str(data["erro"]))
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Demanda", data.get("demanda_id") or "—")
    with c2:
        st.metric("Fase / passo", str(data.get("fase_actual") or "—"))
    with c3:
        st.metric("Responsável", str(data.get("responsavel_actual") or "—"))

    st.subheader("Pendente e concluídos")
    st.write(str(data.get("pendente") or "—"))
    done = data.get("pontos_controlo_concluidos") or []
    if done:
        for x in done:
            st.success(str(x))
    else:
        st.info("Nenhum ponto de controlo listado como concluído.")

    falha = data.get("falha")
    st.subheader("Falha (fluxo reverso)")
    if falha:
        st.error(json.dumps(falha, ensure_ascii=False, indent=2))
    else:
        st.success("Sem falha registada.")

    with st.expander("JSON completo (auditoria)"):
        st.code(json.dumps(data, ensure_ascii=False, indent=2), language="json")

    st.divider()
    st.caption(
        "Dossiers: `docs/governanca/demandas/<ID>/` · Caderno de testes: `docs/CADERNO_TESTES_MASTER.md`"
    )
