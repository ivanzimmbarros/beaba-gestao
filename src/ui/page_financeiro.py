"""Página Financeiro — sector «Gastos Operacionais» (categorias e lançamentos)."""

from __future__ import annotations

import html
from datetime import date

import pandas as pd
import streamlit as st

from src.database.connection import get_connection
from src.modules.financeiro_categorias_gasto import (
    listar_centros_custo_ativos,
    listar_linhas_tabela_tipos,
    listar_naturezas_ativas_so_nome,
    listar_naturezas_por_centro_ativas,
    listar_tipos_gasto_ativos_so_nome,
    listar_tipos_por_natureza_ativos,
    obter_tipo_com_caminho,
    resolver_salvar_formulario,
)
from src.modules.financeiro_lancamentos_gasto import (
    inserir_lancamentos_operacionais,
    iso_para_dd_mm_yyyy,
    listar_lancamentos_controle,
    parse_data_dd_mm_yyyy,
    parse_valor_euro,
    tipos_gasto_coerentes_com_seleccao,
)
from src.modules.financeiro_repasses_colaboradores import (
    listar_anos_com_repasses,
    listar_colaboradores_para_filtro_repasse,
    listar_linhas_gestao_repasses,
    listar_naturezas_servico_para_filtro_repasse,
    listar_servicos_para_filtro_repasse,
)
from src.ui.constituicao_visual_shell import inject_constituicao_fin_page
from src.ui.fmt_euro_constituicao import fmt_euro_centavos


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


_REP_MESES_PT = (
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)


def _fmt_mes_repasse_ui(m: int) -> str:
    if int(m) == 0:
        return "Todos"
    return _REP_MESES_PT[int(m) - 1]


def _fmt_pct_repasse_row(bp: object | None) -> str:
    if bp is None or int(bp) <= 0:
        return "—"
    x = int(bp) / 100.0
    return f"{str(x).replace('.', ',')} %"


_CAD_WIDGET_SUF = ("l1_cc", "l2_cc", "l2_nat_txt", "l3_cc", "l3_nat", "l3_tip_txt")


def _purge_fin_gxc_cadastro_widget_keys(*form_versions: int) -> None:
    """Remove widgets do cadastro (6 campos) para forçar repovoamento vazio após gravar/limpar."""
    for v in form_versions:
        for s in _CAD_WIDGET_SUF:
            st.session_state.pop(f"fin_gxc_{int(v)}_{s}", None)


def _limpar_tudo_fin_gxc_manutencao_expander(fv: int) -> None:
    """Cadastro, filtros, filtros aplicados (tabela), selecção na tabela e modo edição.

    Deve correr no início do rerun, *antes* de `st.multiselect` / `st.dataframe` com as
    mesmas keys — o Streamlit proíbe alterar `session_state` desses widgets depois de
    serem instanciados.

    Incrementa `fin_gxc_tbl_v` para trocar a `key` do `st.dataframe`; caso contrário o
    evento `ev` pode ainda trazer a linha seleccionada e o cadastro volta a ser
    preenchido via `_fin_gxc_prime` no mesmo rerun.

    Incrementa `fin_glxc_lanc_v` para repor o formulário de lançamentos (2.º expander)
    sem tocar em `session_state` dos widgets depois de instanciados.
    """
    _purge_fin_gxc_cadastro_widget_keys(fv)
    st.session_state.fin_gxc_form_v = fv + 1
    _purge_fin_gxc_cadastro_widget_keys(fv + 1)
    st.session_state.fin_gxc_edit_tipo_id = None
    st.session_state.pop("_fin_gxc_prev_sel", None)
    st.session_state.pop("_fin_gxc_prime", None)
    st.session_state.pop("_fin_glxc_prev_lanc", None)
    st.session_state.pop("_fin_glxc_lanc_prime", None)

    st.session_state["fin_gxc_ms_cc"] = []
    st.session_state["fin_gxc_ms_nat"] = []
    st.session_state["fin_gxc_ms_tip"] = []
    st.session_state.pop("fin_gxc_apl_cc", None)
    st.session_state.pop("fin_gxc_apl_nat", None)
    st.session_state.pop("fin_gxc_apl_tip", None)

    # Nova key do dataframe: senão o `ev` do rerun ainda traz a linha seleccionada e
    # o bloco `if sel:` volta a injectar `_fin_gxc_prime` (cadastro “não limpa”).
    st.session_state.pop("fin_gxc_tbl_df", None)
    st.session_state.fin_gxc_tbl_v = int(st.session_state.get("fin_gxc_tbl_v", 0)) + 1
    st.session_state.fin_glxc_lanc_v = int(st.session_state.get("fin_glxc_lanc_v", 0)) + 1


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
    if "fin_glxf_filt_v" not in st.session_state:
        st.session_state.fin_glxf_filt_v = 0
    if "fin_glxc_lanc_v" not in st.session_state:
        st.session_state.fin_glxc_lanc_v = 0
    if "fin_rep_filt_v" not in st.session_state:
        st.session_state.fin_rep_filt_v = 0

    if st.session_state.pop("_fin_gxc_limpar_pending", None):
        _limpar_tudo_fin_gxc_manutencao_expander(int(st.session_state.fin_gxc_form_v))

    if st.session_state.pop("_fin_glxf_limpar_pending", None):
        st.session_state.fin_glxf_filt_v = int(st.session_state.get("fin_glxf_filt_v", 0)) + 1
        st.session_state.pop("fin_glxf_apl_cc", None)
        st.session_state.pop("fin_glxf_apl_nat", None)
        st.session_state.pop("fin_glxf_apl_tip", None)
        st.session_state.fin_glxf_tbl_v = int(st.session_state.get("fin_glxf_tbl_v", 0)) + 1
        st.session_state.fin_glxc_lanc_v = int(st.session_state.get("fin_glxc_lanc_v", 0)) + 1
        st.session_state.pop("_fin_glxc_prev_lanc", None)
        st.session_state.pop("_fin_glxc_lanc_prime", None)

    if st.session_state.pop("_fin_rep_limpar_pending", None):
        st.session_state.fin_rep_filt_v = int(st.session_state.get("fin_rep_filt_v", 0)) + 1
        for _rk in (
            "fin_rep_apl_colab",
            "fin_rep_apl_nat",
            "fin_rep_apl_svc",
            "fin_rep_apl_mes",
            "fin_rep_apl_ano",
        ):
            st.session_state.pop(_rk, None)

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

    nat_f_opts = listar_naturezas_ativas_so_nome(conn)
    tip_f_opts = listar_tipos_gasto_ativos_so_nome(conn)
    nat_f_ids = [x[0] for x in nat_f_opts]
    nat_f_lbl = {x[0]: x[1] for x in nat_f_opts}
    tip_f_ids = [x[0] for x in tip_f_opts]
    tip_f_lbl = {x[0]: x[1] for x in tip_f_opts}

    def _fmt_nat_filtro(i: int) -> str:
        return nat_f_lbl.get(int(i), str(i))

    def _fmt_tipo_filtro(i: int) -> str:
        return tip_f_lbl.get(int(i), str(i))

    with st.expander("Manutenção das Categorias de Gastos", expanded=True):
        _h2("Cadastramento de Novas Categorias")

        cadastro = st.container()
        with cadastro:
            # Metade esquerda = só campos (L1–L3); metade direita = vazio, botão na L2 (à esquerda da coluna).
            r1_left, r1_right = st.columns([1, 1], vertical_alignment="top")
            with r1_left:
                st.text_input("Centro de Custo", key=f"{fk}l1_cc")
            with r1_right:
                pass

            r2_left, r2_right = st.columns([1, 1], vertical_alignment="center")
            with r2_left:
                l2a, l2b = st.columns([1, 1], vertical_alignment="center")
                with l2a:
                    if cc_ids:
                        st.selectbox(
                            "Centro de Custo",
                            options=cc_ids,
                            index=None,
                            placeholder="Escolher centro de custo",
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
            with r2_right:
                if st.button("SALVAR DADOS", key="fin_gxc_btn_salvar", type="primary"):
                    try:
                        ok, msg = _executar_salvamento_categorias(conn, fk=fk, fv=fv, cc_ids=cc_ids)
                        if ok:
                            conn.commit()
                            st.success("Dados gravados com sucesso.")
                            _purge_fin_gxc_cadastro_widget_keys(fv)
                            st.session_state.fin_gxc_form_v = fv + 1
                            _purge_fin_gxc_cadastro_widget_keys(fv + 1)
                            st.session_state.fin_gxc_edit_tipo_id = None
                            st.session_state.pop("_fin_gxc_prev_sel", None)
                            st.rerun()
                        else:
                            st.warning(msg or "Não foi possível gravar.")
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Erro ao gravar: {e}")

            r3_left, r3_right = st.columns([1, 1], vertical_alignment="top")
            with r3_left:
                l3a, l3b, l3c = st.columns(3)
                with l3a:
                    if cc_ids:
                        st.selectbox(
                            "Centro de Custo",
                            options=cc_ids,
                            index=None,
                            placeholder="Escolher centro de custo",
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
                            st.session_state[f"{fk}l3_nat"] = None
                        st.selectbox(
                            "Natureza",
                            options=nat_ids,
                            index=None,
                            placeholder="Escolher natureza",
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
            with r3_right:
                pass

        st.markdown(
            '<div style="height:18px" aria-hidden="true"></div>',
            unsafe_allow_html=True,
        )
        _h2("Filtros de Categorias Cadastradas")

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
                format_func=_fmt_nat_filtro,
                key="fin_gxc_ms_nat",
            )
        with f3:
            st.multiselect(
                "Tipo de Gasto",
                options=tip_f_ids,
                format_func=_fmt_tipo_filtro,
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
                st.session_state["_fin_gxc_limpar_pending"] = True
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

        tbl_v = int(st.session_state.get("fin_gxc_tbl_v", 0))
        tbl_key = f"fin_gxc_tbl_df_{tbl_v}"

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
                key=tbl_key,
                hide_index=True,
            )
            sel = _df_selected_rows(ev, tbl_key)
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

    with st.expander("Controle de Lançamentos de Gastos Operacionais", expanded=False):
        _lc = int(st.session_state.get("fin_glxc_lanc_v", 0))
        _lk = f"fin_glxc_L{_lc}_"

        if "_fin_glxc_lanc_prime" in st.session_state:
            pr = st.session_state.pop("_fin_glxc_lanc_prime")
            for k, v in pr.items():
                st.session_state[f"{_lk}{k}"] = v

        st.radio(
            "Tipo de registo do lançamento",
            ["Real", "Meta"],
            index=0,
            horizontal=True,
            key=f"{_lk}tipo_reg",
        )

        half_l, _half_r = st.columns([1, 1], vertical_alignment="top")
        with half_l:
            if cc_ids:
                gl1, gl2, gl3 = st.columns([1, 1, 1], vertical_alignment="top")
                with gl1:
                    st.selectbox(
                        "Centro de Custo",
                        options=cc_ids,
                        index=None,
                        placeholder="Escolher centro de custo",
                        format_func=_fmt_cc,
                        key=f"{_lk}sb_cc",
                    )
                sel_cc_gl = st.session_state.get(f"{_lk}sb_cc")
                sel_cc_i = int(sel_cc_gl) if sel_cc_gl is not None else None
                nat_opts_gl = listar_naturezas_por_centro_ativas(conn, sel_cc_i) if sel_cc_i else []
                nat_ids_gl = [n[0] for n in nat_opts_gl]
                nat_lbl_gl = {n[0]: n[1] for n in nat_opts_gl}

                def _fmt_nat_gl(i: int) -> str:
                    return nat_lbl_gl.get(int(i), str(i))

                with gl2:
                    if nat_ids_gl:
                        cur_nat_gl = st.session_state.get(f"{_lk}sb_nat")
                        if cur_nat_gl is not None and int(cur_nat_gl) not in nat_ids_gl:
                            st.session_state[f"{_lk}sb_nat"] = None
                        st.selectbox(
                            "Natureza",
                            options=nat_ids_gl,
                            index=None,
                            placeholder="Escolher natureza",
                            format_func=_fmt_nat_gl,
                            key=f"{_lk}sb_nat",
                        )
                    else:
                        st.selectbox(
                            "Natureza",
                            options=[0],
                            format_func=lambda _: "(sem naturezas neste centro)" if sel_cc_i else "(escolha o centro)",
                            disabled=True,
                            key=f"{_lk}sb_nat",
                        )
                sel_nat_gl = st.session_state.get(f"{_lk}sb_nat")
                sel_nat_i = int(sel_nat_gl) if sel_nat_gl is not None else None
                tip_opts_gl = listar_tipos_por_natureza_ativos(conn, sel_nat_i) if sel_nat_i else []
                tip_ids_gl = [t[0] for t in tip_opts_gl]
                tip_lbl_gl = {t[0]: t[1] for t in tip_opts_gl}

                def _fmt_tip_gl(i: int) -> str:
                    return tip_lbl_gl.get(int(i), str(i))

                with gl3:
                    if tip_ids_gl:
                        cur_tip_gl = st.session_state.get(f"{_lk}sb_tip")
                        if cur_tip_gl is not None and int(cur_tip_gl) not in tip_ids_gl:
                            st.session_state[f"{_lk}sb_tip"] = None
                        st.selectbox(
                            "Tipo de Gasto",
                            options=tip_ids_gl,
                            index=None,
                            placeholder="Escolher tipo de gasto",
                            format_func=_fmt_tip_gl,
                            key=f"{_lk}sb_tip",
                        )
                    else:
                        st.selectbox(
                            "Tipo de Gasto",
                            options=[0],
                            format_func=lambda _: "(sem tipos nesta natureza)" if sel_nat_i else "(escolha a natureza)",
                            disabled=True,
                            key=f"{_lk}sb_tip",
                        )
            else:
                st.caption(
                    "Cadastre centros de custo na primeira subárea para activar a selecção hierárquica."
                )

        r3a, r3b, r3c, r3d, r3e = st.columns(
            [1.05, 1.05, 1.0, 1.15, 0.65],
            vertical_alignment="top",
        )
        with r3a:
            st.text_input("Valor (€)", key=f"{_lk}valor", placeholder="0,00")
        with r3b:
            st.text_input("Data de lançamento", key=f"{_lk}data", placeholder="dd/mm/aaaa")
        with r3c:
            st.selectbox(
                "Status do lançamento",
                ["Agendado", "Pago"],
                index=0,
                key=f"{_lk}status",
            )
        with r3d:
            st.selectbox(
                "Deseja replicar o valor para outros meses?",
                ["Não", "Sim"],
                index=0,
                key=f"{_lk}replica",
            )
        with r3e:
            _rep = str(st.session_state.get(f"{_lk}replica", "Não"))
            st.selectbox(
                "Quantidade de meses",
                options=list(range(1, 25)),
                index=0,
                format_func=lambda n: str(int(n)),
                key=f"{_lk}n_meses",
                disabled=(_rep != "Sim"),
            )

        if st.button("GRAVAR LANÇAMENTO(S)", key="fin_glxc_btn_gravar", type="primary"):
            cc_gl = st.session_state.get(f"{_lk}sb_cc")
            nat_gl = st.session_state.get(f"{_lk}sb_nat")
            tip_gl = st.session_state.get(f"{_lk}sb_tip")
            if cc_gl is None or nat_gl is None or tip_gl is None:
                st.warning(
                    "Seleccione **Centro de Custo**, **Natureza** e **Tipo de gasto** (uma opção em cada)."
                )
            else:
                ms_cc = [int(cc_gl)]
                ms_nat = [int(nat_gl)]
                ms_tip = [int(tip_gl)]
                tipos_ok = tipos_gasto_coerentes_com_seleccao(
                    conn,
                    centro_ids=ms_cc,
                    natureza_ids=ms_nat,
                    tipo_ids=ms_tip,
                )
                if not tipos_ok:
                    st.warning(
                        "A combinação centro / natureza / tipo não é válida na hierarquia. Ajuste as caixas."
                    )
                else:
                    vtxt = str(st.session_state.get(f"{_lk}valor", "") or "")
                    dtxt = str(st.session_state.get(f"{_lk}data", "") or "")
                    cents = parse_valor_euro(vtxt)
                    diso = parse_data_dd_mm_yyyy(dtxt)
                    if cents is None:
                        st.warning("Indique um **valor** válido em euros.")
                    elif diso is None:
                        st.warning("Indique a **data** no formato **dd/mm/aaaa**.")
                    else:
                        rep_sim = str(st.session_state.get(f"{_lk}replica", "Não")) == "Sim"
                        n_m = int(st.session_state.get(f"{_lk}n_meses", 1) or 1)
                        if not rep_sim:
                            n_m = 1
                        tipo_reg_ui = str(st.session_state.get(f"{_lk}tipo_reg") or "Real")
                        classe = "real" if tipo_reg_ui.startswith("Real") else "meta"
                        status_ui = str(st.session_state.get(f"{_lk}status", "Agendado"))
                        try:
                            n_ins, err = inserir_lancamentos_operacionais(
                                conn,
                                tipos_ok,
                                valor_centavos=int(cents),
                                data_competencia_iso=diso,
                                status_lancamento=status_ui,
                                classe_lancamento=classe,
                                replicar=rep_sim,
                                meses_duracao=n_m,
                                observacao="",
                            )
                            if err:
                                st.warning(err)
                            else:
                                conn.commit()
                                st.session_state.fin_glxf_tbl_v = int(
                                    st.session_state.get("fin_glxf_tbl_v", 0)
                                ) + 1
                                st.success(f"{n_ins} lançamento(s) gravado(s).")
                                st.rerun()
                        except Exception as ex:
                            conn.rollback()
                            st.error(f"Erro ao gravar: {ex}")

        st.markdown(
            '<div style="height:18px" aria-hidden="true"></div>',
            unsafe_allow_html=True,
        )
        _h2("Filtros de Lançamentos")

        if cc_ids and nat_f_ids and tip_f_ids:
            _glxf_v = int(st.session_state.get("fin_glxf_filt_v", 0))
            _k_glxf_cc = f"fin_glxf_f{_glxf_v}_ms_cc"
            _k_glxf_nat = f"fin_glxf_f{_glxf_v}_ms_nat"
            _k_glxf_tip = f"fin_glxf_f{_glxf_v}_ms_tip"
            lf1, lf2, lf3, lf4, lf5 = st.columns(
                [1.0, 1.0, 1.0, 0.32, 0.38],
                vertical_alignment="center",
            )
            with lf1:
                st.multiselect(
                    "Centro de Custo",
                    options=cc_ids,
                    format_func=_fmt_cc,
                    key=_k_glxf_cc,
                )
            with lf2:
                st.multiselect(
                    "Natureza",
                    options=nat_f_ids,
                    format_func=_fmt_nat_filtro,
                    key=_k_glxf_nat,
                )
            with lf3:
                st.multiselect(
                    "Tipo de Gasto",
                    options=tip_f_ids,
                    format_func=_fmt_tipo_filtro,
                    key=_k_glxf_tip,
                )
            with lf4:
                if st.button("PESQUISAR", key="fin_glxf_btn_pesquisar"):
                    st.session_state.fin_glxf_apl_cc = list(st.session_state.get(_k_glxf_cc) or [])
                    st.session_state.fin_glxf_apl_nat = list(st.session_state.get(_k_glxf_nat) or [])
                    st.session_state.fin_glxf_apl_tip = list(st.session_state.get(_k_glxf_tip) or [])
                    st.rerun()
            with lf5:
                if st.button("LIMPAR FILTROS", key="fin_glxf_btn_limpar"):
                    st.session_state["_fin_glxf_limpar_pending"] = True
                    st.rerun()
        else:
            st.caption(
                "Cadastre centros de custo, naturezas e tipos na primeira subárea para filtrar lançamentos."
            )

        l_apl_cc = st.session_state.get("fin_glxf_apl_cc")
        l_apl_nat = st.session_state.get("fin_glxf_apl_nat")
        l_apl_tip = st.session_state.get("fin_glxf_apl_tip")
        l_f_cc = [int(x) for x in l_apl_cc] if l_apl_cc else None
        l_f_nat = [int(x) for x in l_apl_nat] if l_apl_nat else None
        l_f_tip = [int(x) for x in l_apl_tip] if l_apl_tip else None

        l_rows = listar_lancamentos_controle(
            conn,
            filtro_centro_ids=l_f_cc,
            filtro_natureza_ids=l_f_nat,
            filtro_tipo_ids=l_f_tip,
        )

        st.markdown(
            '<div class="bea-cv-cag-h2" style="font-size:1.05rem;margin-top:0.85rem;">'
            f"{html.escape('Controle de Lançamentos')}</div>",
            unsafe_allow_html=True,
        )

        if l_rows:
            l_tbl_v = int(st.session_state.get("fin_glxf_tbl_v", 0))
            l_tbl_key = f"fin_glxf_tbl_df_{l_tbl_v}"
            l_df = pd.DataFrame(
                {
                    "Centro de Custo": [r["centro"] for r in l_rows],
                    "Natureza": [r["natureza"] for r in l_rows],
                    "Tipo de Gasto": [r["tipo"] for r in l_rows],
                    "Valor": [r["valor"] for r in l_rows],
                    "Tipo de Registo": [r["tipo_registo"] for r in l_rows],
                    "Status do Lançamento": [r["status"] for r in l_rows],
                    "Data de Pagamento": [r["data_pagamento"] for r in l_rows],
                    "Data da Criação do Registo": [r["data_criacao"] for r in l_rows],
                }
            )
            ev_l = st.dataframe(
                l_df,
                width="stretch",
                on_select="rerun",
                selection_mode="single-row",
                key=l_tbl_key,
                hide_index=True,
            )
            sel_l = _df_selected_rows(ev_l, l_tbl_key)
            if sel_l:
                lix = int(sel_l[0])
                if 0 <= lix < len(l_rows):
                    rsel = l_rows[lix]
                    rid = int(rsel["lancamento_id"])
                    if st.session_state.get("_fin_glxc_prev_lanc") != rid:
                        nm = max(1, min(24, int(rsel.get("n_meses") or 1)))
                        st.session_state.fin_glxc_lanc_v = _lc + 1
                        st.session_state._fin_glxc_lanc_prime = {
                            "tipo_reg": str(rsel.get("tipo_registo") or "Real"),
                            "sb_cc": int(rsel["centro_custo_id"]),
                            "sb_nat": int(rsel["natureza_id"]),
                            "sb_tip": int(rsel["tipo_id"]),
                            "valor": str(rsel.get("valor") or ""),
                            "data": iso_para_dd_mm_yyyy(str(rsel.get("data_competencia_iso") or "")),
                            "status": str(rsel.get("status") or "Agendado"),
                            "replica": "Sim" if int(rsel.get("replica_flag") or 0) else "Não",
                            "n_meses": nm,
                        }
                        st.session_state._fin_glxc_prev_lanc = rid
                        st.rerun()
            lid = st.session_state.get("_fin_glxc_prev_lanc")
            if lid is not None:
                st.caption(
                    f"Linha da tabela seleccionada — Lançamento **#{lid}**. "
                    "Os campos acima reflectem esse registo; **GRAVAR** cria novo(s) lançamento(s)."
                )
        else:
            st.caption("Nenhum lançamento encontrado para os filtros actuais.")

    _h2("2. Repasses")

    with st.expander("Gestão de Repasses para os Colaboradores", expanded=False):
        rep_colab_opts = listar_colaboradores_para_filtro_repasse(conn)
        rep_nat_opts = listar_naturezas_servico_para_filtro_repasse(conn)
        rep_svc_opts = listar_servicos_para_filtro_repasse(conn)
        rep_anos = listar_anos_com_repasses(conn)
        if not rep_anos:
            rep_anos = [date.today().year]

        _rpv = int(st.session_state.get("fin_rep_filt_v", 0))
        _k_rep_col = f"fin_rep_f{_rpv}_ms_colab"
        _k_rep_nat = f"fin_rep_f{_rpv}_ms_nat"
        _k_rep_svc = f"fin_rep_f{_rpv}_ms_svc"
        _k_rep_mes = f"fin_rep_f{_rpv}_mes"
        _k_rep_ano = f"fin_rep_f{_rpv}_ano"

        rep_c_ids = [c[0] for c in rep_colab_opts]
        rep_c_lbl = {c[0]: c[1] for c in rep_colab_opts}
        rep_svc_ids = [s[0] for s in rep_svc_opts]
        rep_svc_lbl = {s[0]: s[1] for s in rep_svc_opts}

        def _fmt_rep_col(i: int) -> str:
            return rep_c_lbl.get(int(i), str(i))

        def _fmt_rep_svc(i: int) -> str:
            return rep_svc_lbl.get(int(i), str(i))

        rp1, rp2, rp3, rp4, rp5 = st.columns(5, vertical_alignment="top")
        with rp1:
            if rep_c_ids:
                st.multiselect(
                    "Nome do Colaborador",
                    options=rep_c_ids,
                    format_func=_fmt_rep_col,
                    key=_k_rep_col,
                )
            else:
                st.caption("Sem colaboradores cadastrados.")
        with rp2:
            if rep_nat_opts:
                st.multiselect(
                    "Natureza do Serviço",
                    options=rep_nat_opts,
                    key=_k_rep_nat,
                )
            else:
                st.caption("Sem naturezas no catálogo.")
        with rp3:
            if rep_svc_ids:
                st.multiselect(
                    "Nome do Serviço",
                    options=rep_svc_ids,
                    format_func=_fmt_rep_svc,
                    key=_k_rep_svc,
                )
            else:
                st.caption("Sem serviços no catálogo.")
        with rp4:
            st.selectbox(
                "Mês",
                options=list(range(0, 13)),
                index=0,
                format_func=_fmt_mes_repasse_ui,
                key=_k_rep_mes,
            )
        with rp5:
            st.selectbox(
                "Ano",
                options=[0] + list(rep_anos),
                index=0,
                format_func=lambda y: "Todos" if int(y) == 0 else str(int(y)),
                key=_k_rep_ano,
            )

        # Largura ao conteúdo (default `width='content'` nos botões).
        rb1, rb2, _rb_rest = st.columns([2.2, 3.2, 22], gap="small", vertical_alignment="center")
        with rb1:
            if st.button("PESQUISAR", key="fin_rep_btn_pesquisar"):
                st.session_state.fin_rep_apl_colab = (
                    list(st.session_state.get(_k_rep_col) or []) if rep_c_ids else []
                )
                st.session_state.fin_rep_apl_nat = (
                    list(st.session_state.get(_k_rep_nat) or []) if rep_nat_opts else []
                )
                st.session_state.fin_rep_apl_svc = (
                    list(st.session_state.get(_k_rep_svc) or []) if rep_svc_ids else []
                )
                _m = int(st.session_state.get(_k_rep_mes, 0) or 0)
                st.session_state.fin_rep_apl_mes = None if _m == 0 else _m
                _a = int(st.session_state.get(_k_rep_ano, 0) or 0)
                st.session_state.fin_rep_apl_ano = None if _a == 0 else _a
                st.rerun()
        with rb2:
            if st.button("Limpar Pesquisa", key="fin_rep_btn_limpar"):
                st.session_state["_fin_rep_limpar_pending"] = True
                st.rerun()

        _apl_rc = st.session_state.get("fin_rep_apl_colab")
        _apl_rn = st.session_state.get("fin_rep_apl_nat")
        _apl_rs = st.session_state.get("fin_rep_apl_svc")
        _apl_rm = st.session_state.get("fin_rep_apl_mes")
        _apl_ra = st.session_state.get("fin_rep_apl_ano")

        _f_rc = [int(x) for x in _apl_rc] if _apl_rc else None
        _f_rn = [str(x) for x in _apl_rn] if _apl_rn else None
        _f_rs = [int(x) for x in _apl_rs] if _apl_rs else None
        _f_rm = int(_apl_rm) if _apl_rm is not None else None
        _f_ra = int(_apl_ra) if _apl_ra is not None else None

        rep_rows = listar_linhas_gestao_repasses(
            conn,
            colaborador_ids=_f_rc,
            naturezas=_f_rn,
            servico_ids=_f_rs,
            mes=_f_rm,
            ano=_f_ra,
        )

        if rep_rows:
            rep_df = pd.DataFrame(
                {
                    "Nome da colaboradora": [r["colaborador_nome"] for r in rep_rows],
                    "Natureza do serviço prestado": [r["natureza_servico"] for r in rep_rows],
                    "Nome do serviço prestado": [r["nome_servico"] for r in rep_rows],
                    "Percentual de repasse acordado para este serviço": [
                        _fmt_pct_repasse_row(r.get("percentual_bp")) for r in rep_rows
                    ],
                    "Valor final do serviço": [
                        fmt_euro_centavos(int(r["base_calculo_centavos"])) for r in rep_rows
                    ],
                    "Valor do repasse": [
                        fmt_euro_centavos(int(r["valor_repasse_centavos"])) for r in rep_rows
                    ],
                    "Data de execução": [r["data_execucao_dm"] for r in rep_rows],
                }
            )
            st.dataframe(rep_df, width="stretch", hide_index=True)
        else:
            st.caption(
                "Nenhuma linha de repasse encontrada. Use **PESQUISAR** (filtros opcionais) "
                "ou confirme se existem agendamentos concluídos / com pagamento parcial com repasse calculado."
            )
