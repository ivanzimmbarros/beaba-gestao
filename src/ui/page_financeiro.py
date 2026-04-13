"""Página Financeiro — sector «Gastos Operacionais» (categorias hierárquicas)."""

from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from src.database.connection import get_connection
from src.modules.financeiro_categorias_gasto import (
    listar_centros_custo_ativos,
    listar_linhas_tabela_tipos,
    listar_naturezas_ativas_com_rotulo,
    listar_naturezas_por_centro_ativas,
    listar_tipos_ativos_com_rotulo,
    obter_tipo_com_caminho,
    resolver_salvar_formulario,
)
from src.ui.constituicao_visual_shell import inject_constituicao_fin_page


def _df_selected_rows(ev: object | None, session_key: str) -> list[int]:
    rows: list[int] = []

    def _rows_from_selection(sel: object | None) -> list[int]:
        if sel is None:
            return []
        r = getattr(sel, "rows", None)
        if r is None and isinstance(sel, dict):
            r = sel.get("rows")
        if not r:
            return []
        return [int(x) for x in r]

    if ev is not None:
        sel = getattr(ev, "selection", None)
        if sel is None and isinstance(ev, dict):
            sel = ev.get("selection")
        rows = _rows_from_selection(sel)
    if rows:
        return rows
    raw = st.session_state.get(session_key)
    if raw is None:
        return []
    sel2 = getattr(raw, "selection", None)
    if sel2 is None and isinstance(raw, dict):
        sel2 = raw.get("selection")
    return _rows_from_selection(sel2)


def _h2(text: str) -> None:
    t = html.escape(text)
    st.markdown(f'<div class="bea-cv-cag-h2">{t}</div>', unsafe_allow_html=True)


def _executar_salvamento_categorias(
    conn,
    *,
    fk: str,
    fv: int,
    cc_ids: list[int],
) -> tuple[bool, str]:
    """Persistência com `resolver_salvar_formulario`; sem UI."""
    l1_cc = str(st.session_state.get(f"{fk}l1_cc", "")).strip()
    l1_nat = ""
    l1_tip = ""
    l2_cc = st.session_state.get(f"{fk}l2_cc")
    l2_txt = str(st.session_state.get(f"{fk}l2_nat_txt", "")).strip()
    l3_cc = st.session_state.get(f"{fk}l3_cc")
    l3_nat = st.session_state.get(f"{fk}l3_nat")
    l3_tip = str(st.session_state.get(f"{fk}l3_tip_txt", "")).strip()
    edit_id = st.session_state.get("fin_gxc_edit_tipo_id")

    l2_centro = int(l2_cc) if l2_cc is not None and cc_ids else None
    l3_c = int(l3_cc) if l3_cc is not None and cc_ids else None
    l3_nat_opts = (
        listar_naturezas_por_centro_ativas(conn, int(l3_cc)) if l3_cc is not None and cc_ids else []
    )
    l3_nat_ids_btn = [n[0] for n in l3_nat_opts]
    l3_n = (
        int(l3_nat)
        if l3_nat is not None and l3_nat_ids_btn and int(l3_nat) in l3_nat_ids_btn
        else None
    )

    return resolver_salvar_formulario(
        conn,
        linha1_cc=l1_cc,
        linha1_natureza=l1_nat,
        linha1_tipo=l1_tip,
        linha2_centro_id=l2_centro,
        linha2_natureza_texto=l2_txt,
        linha3_centro_id=l3_c,
        linha3_natureza_id=l3_n,
        linha3_tipo_texto=l3_tip,
        editando_tipo_id=int(edit_id) if edit_id is not None else None,
    )


def render_page_financeiro(*, render_back_and_breadcrumb) -> None:
    inject_constituicao_fin_page()
    render_back_and_breadcrumb(["Home", "Financeiro"], back_key="bea_back_financeiro")

    st.markdown(
        '<h1 class="bea-cv-cag-h1">Financeiro</h1>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="bea-cv-cag-gap" aria-hidden="true"></div>', unsafe_allow_html=True)

    _h2("1. Gastos Operacionais")

    conn = get_connection()
    if conn is None:
        st.error("Não foi possível ligar à base de dados.")
        return

    if "fin_gxc_form_v" not in st.session_state:
        st.session_state.fin_gxc_form_v = 0
    if "fin_gxc_edit_tipo_id" not in st.session_state:
        st.session_state.fin_gxc_edit_tipo_id = None

    fv = int(st.session_state.fin_gxc_form_v)
    fk = f"fin_gxc_{fv}_"

    if "_fin_gxc_prime" in st.session_state:
        pr = st.session_state.pop("_fin_gxc_prime")
        for k, v in pr.items():
            st.session_state[f"{fk}{k}"] = v

    centros = listar_centros_custo_ativos(conn)
    cc_ids = [c[0] for c in centros]
    cc_lbl = {c[0]: c[1] for c in centros}

    def _fmt_cc(i: int) -> str:
        return cc_lbl.get(int(i), str(i))

    with st.expander("Manutenção das Categorias de Gastos", expanded=True):
        t_inner = "Cadastramento e Manutenção de Novas Categorias de Gastos"
        st.markdown(
            f'<div class="bea-cv-cag-h2" style="font-size:1.15rem;">{html.escape(t_inner)}</div>',
            unsafe_allow_html=True,
        )

        _h2("Cadastramento de Novas Categorias")

        form_blk, _spacer = st.columns([2.65, 1.35])
        with form_blk:
            # —— Linha 1: só texto «Centro de Custo» ——
            st.text_input("Centro de Custo", key=f"{fk}l1_cc")

            # —— Linha 2: seleção CC + texto Natureza + SALVAR DADOS (sempre visível na mesma linha) ——
            l2a, l2b, l2btn = st.columns([1.2, 1.2, 0.42], vertical_alignment="center")
            with l2a:
                if cc_ids:
                    st.selectbox(
                        "Centro de Custo",
                        options=cc_ids,
                        format_func=_fmt_cc,
                        key=f"{fk}l2_cc",
                    )
                else:
                    st.selectbox(
                        "Centro de Custo",
                        options=[0],
                        format_func=lambda _: "(sem centros — use a linha 1 + SALVAR DADOS)",
                        disabled=True,
                        key=f"{fk}l2_cc",
                    )
            with l2b:
                st.text_input("Natureza", key=f"{fk}l2_nat_txt")
            with l2btn:
                if st.button("SALVAR DADOS", key="fin_gxc_btn_salvar", type="primary"):
                    try:
                        ok, msg = _executar_salvamento_categorias(conn, fk=fk, fv=fv, cc_ids=cc_ids)
                        if ok:
                            conn.commit()
                            st.success("Dados gravados com sucesso.")
                            st.session_state.fin_gxc_form_v = fv + 1
                            st.session_state.fin_gxc_edit_tipo_id = None
                            st.session_state.pop("_fin_gxc_prev_sel", None)
                            st.rerun()
                        else:
                            st.warning(msg or "Não foi possível gravar.")
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Erro ao gravar: {e}")

            # —— Linha 3: 2 seleções + texto «Tipos de gasto» ——
            l3a, l3b, l3c = st.columns(3)
            with l3a:
                if cc_ids:
                    st.selectbox(
                        "Centro de Custo",
                        options=cc_ids,
                        format_func=_fmt_cc,
                        key=f"{fk}l3_cc",
                    )
                else:
                    st.selectbox(
                        "Centro de Custo",
                        options=[0],
                        format_func=lambda _: "(sem centros)",
                        key=f"{fk}l3_cc",
                    )
            sel_cc = int(st.session_state.get(f"{fk}l3_cc") or 0)
            nat_opts = listar_naturezas_por_centro_ativas(conn, sel_cc) if sel_cc else []
            nat_ids = [n[0] for n in nat_opts]
            nat_lbl = {n[0]: n[1] for n in nat_opts}

            def _fmt_nat(i: int) -> str:
                return nat_lbl.get(int(i), str(i))

            with l3b:
                if nat_ids:
                    cur_nat = st.session_state.get(f"{fk}l3_nat")
                    if cur_nat is not None and int(cur_nat) not in nat_ids:
                        st.session_state[f"{fk}l3_nat"] = nat_ids[0]
                    st.selectbox(
                        "Natureza",
                        options=nat_ids,
                        format_func=_fmt_nat,
                        key=f"{fk}l3_nat",
                    )
                else:
                    st.selectbox(
                        "Natureza",
                        options=[0],
                        format_func=lambda _: "(sem naturezas)",
                        key=f"{fk}l3_nat",
                    )
            with l3c:
                st.text_input("Tipos de gasto", key=f"{fk}l3_tip_txt")

        st.markdown(
            '<div style="height:18px" aria-hidden="true"></div>',
            unsafe_allow_html=True,
        )
        _h2("Filtros de Categorias Cadastradas")

        nat_f_opts = listar_naturezas_ativas_com_rotulo(conn)
        tip_f_opts = listar_tipos_ativos_com_rotulo(conn)
        nat_f_ids = [x[0] for x in nat_f_opts]
        nat_f_lbl = {x[0]: x[1] for x in nat_f_opts}
        tip_f_ids = [x[0] for x in tip_f_opts]
        tip_f_lbl = {x[0]: x[1] for x in tip_f_opts}

        # Mesma linha: 3 multiselects + Pesquisar + Limpar Campos (alinhamento vertical ao centro)
        f1, f2, f3, f4, f5 = st.columns(
            [1.0, 1.0, 1.0, 0.32, 0.38],
            vertical_alignment="center",
        )
        with f1:
            st.multiselect(
                "Centro de Custo",
                options=cc_ids,
                format_func=_fmt_cc,
                key="fin_gxc_ms_cc",
            )
        with f2:
            st.multiselect(
                "Natureza",
                options=nat_f_ids,
                format_func=lambda i: nat_f_lbl.get(int(i), str(i)),
                key="fin_gxc_ms_nat",
            )
        with f3:
            st.multiselect(
                "Tipo de Gasto",
                options=tip_f_ids,
                format_func=lambda i: tip_f_lbl.get(int(i), str(i)),
                key="fin_gxc_ms_tip",
            )
        with f4:
            if st.button("PESQUISAR", key="fin_gxc_btn_pesquisar"):
                st.session_state.fin_gxc_apl_cc = list(st.session_state.get("fin_gxc_ms_cc") or [])
                st.session_state.fin_gxc_apl_nat = list(st.session_state.get("fin_gxc_ms_nat") or [])
                st.session_state.fin_gxc_apl_tip = list(st.session_state.get("fin_gxc_ms_tip") or [])
                st.rerun()
        with f5:
            if st.button("LIMPAR CAMPOS", key="fin_gxc_btn_limpar_form"):
                st.session_state.fin_gxc_form_v = fv + 1
                st.session_state.fin_gxc_edit_tipo_id = None
                st.session_state.pop("_fin_gxc_prev_sel", None)
                st.rerun()

        apl_cc = st.session_state.get("fin_gxc_apl_cc")
        apl_nat = st.session_state.get("fin_gxc_apl_nat")
        apl_tip = st.session_state.get("fin_gxc_apl_tip")
        f_cc = [int(x) for x in apl_cc] if apl_cc else None
        f_nat = [int(x) for x in apl_nat] if apl_nat else None
        f_tip = [int(x) for x in apl_tip] if apl_tip else None

        rows = listar_linhas_tabela_tipos(
            conn,
            filtro_centro_ids=f_cc,
            filtro_natureza_ids=f_nat,
            filtro_tipo_ids=f_tip,
        )
        row_ids = [int(r["tipo_id"]) for r in rows]

        st.markdown(
            '<div class="bea-cv-cag-h2" style="font-size:1.05rem;margin-top:0.85rem;">'
            f"{html.escape('Lista de Categorias de Gasto Cadastradas')}</div>",
            unsafe_allow_html=True,
        )

        if rows:
            df = pd.DataFrame(
                {
                    "Centro de Custo": [r["centro_nome"] for r in rows],
                    "Natureza": [r["natureza_nome"] for r in rows],
                    "Tipo de Gasto": [r["tipo_nome"] for r in rows],
                }
            )
            ev = st.dataframe(
                df,
                width="stretch",
                on_select="rerun",
                selection_mode="single-row",
                key="fin_gxc_tbl_df",
                hide_index=True,
            )
            sel = _df_selected_rows(ev, "fin_gxc_tbl_df")
            if sel:
                idx = int(sel[0])
                if 0 <= idx < len(row_ids):
                    tid = row_ids[idx]
                    if st.session_state.get("_fin_gxc_prev_sel") != tid:
                        path = obter_tipo_com_caminho(conn, tid)
                        if path:
                            st.session_state.fin_gxc_form_v = fv + 1
                            st.session_state._fin_gxc_prime = {
                                "l1_cc": path["centro_nome"],
                                "l2_cc": path["centro_custo_id"],
                                "l2_nat_txt": path["natureza_nome"],
                                "l3_cc": path["centro_custo_id"],
                                "l3_nat": path["natureza_id"],
                                "l3_tip_txt": path["tipo_nome"],
                            }
                            st.session_state.fin_gxc_edit_tipo_id = tid
                            st.session_state._fin_gxc_prev_sel = tid
                            st.rerun()
        else:
            st.caption("Nenhuma categoria encontrada para os filtros actuais.")

        eid = st.session_state.get("fin_gxc_edit_tipo_id")
        if eid is not None:
            st.caption(
                f"Linha da tabela seleccionada — Tipo de gasto **#{eid}**. "
                "Alterações só ficam válidas após **SALVAR DADOS**."
            )
