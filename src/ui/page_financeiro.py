"""Página Financeiro — sector 1 «Resultado Operacional Consolidado» + Gastos, Repasses, Saldos, Entradas."""

from __future__ import annotations

import html
import sqlite3
from datetime import date, datetime

import pandas as pd
import streamlit as st

from src.database.connection import get_connection
from src.modules.financeiro_categorias_gasto import (
    MSG_PEDIR_CONFIRMACAO_ALTERACAO,
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
from src.modules.financeiro_resultado_operacional import (
    agregar_resultado_operacional_consolidado,
)
from src.modules.financeiro_repasses_colaboradores import (
    REPASSE_ESP_SEM_LABEL,
    aplicar_edicao_repasse_linhas_gestao,
    filtra_metadados_servicos_por_especialidades,
    filtra_metadados_servicos_por_naturezas,
    listar_anos_com_repasses,
    listar_colaboradores_para_filtro_repasse,
    listar_linhas_gestao_repasses,
    listar_naturezas_servico_para_filtro_repasse,
    listar_servicos_metadados_para_filtro_repasse,
    marcar_repasses_como_pagos,
)
from src.modules.financeiro_entradas_convertidas import (
    fmt_estado_pagamento_ui,
    listar_clientes_com_venda_para_filtro_entradas,
    listar_linhas_gestao_entradas_convertidas_vendas,
    atualizar_fatura_venda,
)
from src.modules.financeiro_saldos_clientes import (
    listar_clientes_com_saldo_credito_positivo,
    listar_linhas_gestao_saldos_clientes_ativos,
    listar_vendas_com_consumo_credito_loja,
    totais_saldos_ativos_por_antiguidade_cancelamento,
)
from src.modules.colaborador import listar_colaboradores_mapa_equipa
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


def _repasse_iso_to_date(iso: object) -> date | None:
    s = str(iso or "").strip()[:10]
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        try:
            return date.fromisoformat(s)
        except ValueError:
            return None
    return None


def _normalize_repasse_date_cell(v: object) -> str:
    """Normaliza para ``YYYY-MM-DD`` ou string vazia (células do editor / pandas)."""
    if v is None:
        return ""
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    try:
        if pd.isna(v):
            return ""
    except TypeError:
        pass
    ts = pd.to_datetime(v, errors="coerce")
    if pd.isna(ts):
        return ""
    try:
        return ts.date().isoformat()
    except (ValueError, AttributeError):
        return ""


def _norm_repasse_sim_nao(x: object) -> str:
    s = str(x or "").strip().casefold()
    return "Sim" if s == "sim" else "Não"


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


# Caixas de totais (sectores 4. Saldos e 5. Entradas) — paleta BeaBa Sereno.
_FIN_TOTAIS_CAIXAS_STYLE = """
<style>
.bea-fin-ent-tot {
    border-radius: 12px;
    padding: 10px 12px;
    text-align: left;
    min-height: 3.25rem;
    box-sizing: border-box;
}
.bea-fin-ent-tot__lbl {
    display: block;
    white-space: nowrap;
    font-size: 0.8125rem;
    line-height: 1.25;
    margin-bottom: 0.35rem;
    color: #2D332F;
}
.bea-fin-ent-tot__val {
    display: block;
    font-size: 1rem;
    font-weight: 600;
    color: #2D332F;
    font-variant-numeric: tabular-nums;
}
.bea-fin-ent-tot--convertido {
    background: rgba(118, 148, 125, 0.12);
    border: 1px solid rgba(118, 148, 125, 0.5);
}
.bea-fin-ent-tot--recebido {
    background: #E8F0EA;
    border: 1px solid #76947D;
}
.bea-fin-ent-tot--diferenca {
    background: #FFF4E5;
    border: 1px solid #D4A373;
}
.bea-fin-ent-tot--diferenca .bea-fin-ent-tot__lbl { color: #A67C52; }
.bea-fin-ent-tot--diferenca .bea-fin-ent-tot__val { color: #6B4F38; }
.bea-fin-ent-tot--diferenca.bea-fin-ent-tot--alerta-ativa {
    border-width: 2px;
    border-color: #D4A373;
    box-shadow: 0 0 0 1px rgba(212, 163, 115, 0.35);
}
</style>
"""


def _fin_int_id_or_none(val: object) -> int | None:
    """Converte valor de widget para id inteiro; None se inválido (ex.: texto residual no session_state)."""
    if val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


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
    st.session_state.fin_gxc_pending_confirm_update = False
    st.session_state.pop("fin_gxc_flash", None)
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
    confirmar_alteracao: bool = False,
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

    l2_centro = _fin_int_id_or_none(l2_cc) if cc_ids else None
    if l2_centro is not None and l2_centro not in cc_ids:
        l2_centro = None
    l3_c = _fin_int_id_or_none(l3_cc) if cc_ids else None
    if l3_c is not None and l3_c not in cc_ids:
        l3_c = None
    l3_nat_opts = listar_naturezas_por_centro_ativas(conn, l3_c) if l3_c else []
    l3_nat_ids_btn = [n[0] for n in l3_nat_opts]
    l3_nat_i = _fin_int_id_or_none(l3_nat)
    l3_n = l3_nat_i if l3_nat_i is not None and l3_nat_i in l3_nat_ids_btn else None

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
        editando_tipo_id=_fin_int_id_or_none(edit_id),
        confirmar_alteracao=confirmar_alteracao,
    )


def _fin_gxc_after_success_save(fv: int) -> None:
    _purge_fin_gxc_cadastro_widget_keys(fv)
    st.session_state.fin_gxc_form_v = fv + 1
    _purge_fin_gxc_cadastro_widget_keys(fv + 1)
    st.session_state.fin_gxc_edit_tipo_id = None
    st.session_state.pop("_fin_gxc_prev_sel", None)
    st.session_state.fin_gxc_tbl_v = int(st.session_state.get("fin_gxc_tbl_v", 0)) + 1


def _fin_gxc_run_save_categorias(
    conn,
    *,
    fk: str,
    fv: int,
    cc_ids: list[int],
    confirmar_alteracao: bool,
) -> None:
    """Grava categorias; confirmação de alteração é tratada antes do commit."""
    try:
        ok, msg = _executar_salvamento_categorias(
            conn, fk=fk, fv=fv, cc_ids=cc_ids, confirmar_alteracao=confirmar_alteracao
        )
        if msg == MSG_PEDIR_CONFIRMACAO_ALTERACAO:
            st.session_state.fin_gxc_pending_confirm_update = True
            st.rerun()
            return
        if ok:
            conn.commit()
            if msg and "Nenhuma alteração" in msg:
                st.session_state.fin_gxc_flash = ("info", msg)
                st.rerun()
                return
            st.session_state.fin_gxc_flash = ("success", msg or "Operação concluída com sucesso.")
            _fin_gxc_after_success_save(fv)
            st.rerun()
            return
        st.session_state.fin_gxc_flash = ("warning", msg or "Não foi possível gravar.")
        st.rerun()
    except Exception as e:
        conn.rollback()
        st.session_state.fin_gxc_flash = ("error", f"Erro ao gravar: {e}")
        st.rerun()


def _render_fin_gxc_banner_mensagens() -> None:
    """Mensagens e confirmações do cadastro de categorias (acima de «Filtros…»)."""
    pending = bool(st.session_state.get("fin_gxc_pending_confirm_update"))
    flash = st.session_state.get("fin_gxc_flash")
    if not pending and not flash:
        return
    flash = st.session_state.pop("fin_gxc_flash", None)
    st.markdown(
        '<div class="bea-cv-fin-gxc-banner" role="region" aria-label="Mensagens do cadastro de categorias">',
        unsafe_allow_html=True,
    )
    if pending:
        st.markdown(
            '<p class="bea-cv-fin-gxc-banner-q">Deseja prosseguir com a alteração da informação?</p>',
            unsafe_allow_html=True,
        )
        c_yes, c_no = st.columns(2)
        with c_yes:
            if st.button("Sim", key="fin_gxc_conf_update_sim", type="primary"):
                st.session_state.fin_gxc_exec_confirmed_update = True
                st.session_state.fin_gxc_pending_confirm_update = False
                st.rerun()
        with c_no:
            if st.button("Não", key="fin_gxc_conf_update_nao"):
                st.session_state.fin_gxc_pending_confirm_update = False
                st.session_state.fin_gxc_flash = (
                    "info",
                    "Alteração cancelada. Ajuste os campos do formulário (por exemplo «Tipos de gasto» na linha 3) "
                    "e volte a gravar quando estiver pronto.",
                )
                st.rerun()
    elif flash is not None:
        kind, text = flash
        if kind == "success":
            st.success(text)
        elif kind == "warning":
            st.warning(text)
        elif kind == "error":
            st.error(text)
        else:
            st.info(text)
    st.markdown("</div>", unsafe_allow_html=True)


def _render_fin_resultado_operacional_panel(conn: sqlite3.Connection) -> None:
    """Mini-painel do sector 1 (caixas Sereno já injectadas em `_FIN_TOTAIS_CAIXAS_STYLE`)."""
    ro_anos = listar_anos_com_repasses(conn)
    if not ro_anos:
        ro_anos = [date.today().year]
    ro_anos = sorted({int(y) for y in ro_anos}, reverse=True)

    st.caption(
        "O **mês/ano** aplica-se às entradas (data da venda), aos gastos **Reais** (data de competência), "
        "aos repasses (data de execução do serviço) e aos saldos (mês do cancelamento). "
        "Filtros de **CC / Natureza / Tipo** de gastos: estado aplicado em «Filtros de Lançamentos» (PESQUISAR). "
        "Filtros de **repasse**: estado aplicado na secção 3 (PESQUISAR), quando existir."
    )
    c1, c2, c3 = st.columns([1, 1, 2.2], gap="small", vertical_alignment="center")
    with c1:
        st.selectbox(
            "Mês (referência)",
            options=list(range(0, 13)),
            index=0,
            format_func=_fmt_mes_repasse_ui,
            key="fin_ro_sb_mes",
        )
    with c2:
        st.selectbox(
            "Ano (referência)",
            options=[0] + list(ro_anos),
            index=0,
            format_func=lambda y: "Todos" if int(y) == 0 else str(int(y)),
            key="fin_ro_sb_ano",
        )
    with c3:
        st.radio(
            "Cenário das entradas",
            options=("convertido", "recebido"),
            horizontal=True,
            format_func=lambda x: (
                "Valor convertido (vendas)" if x == "convertido" else "Já recebido (tesouraria)"
            ),
            key="fin_ro_rad_cenario",
        )

    _m0 = int(st.session_state.get("fin_ro_sb_mes", 0) or 0)
    _a0 = int(st.session_state.get("fin_ro_sb_ano", 0) or 0)
    _rm = None if _m0 == 0 else _m0
    _ra = None if _a0 == 0 else _a0
    _cen = str(st.session_state.get("fin_ro_rad_cenario", "convertido") or "convertido")

    l_apl_cc = st.session_state.get("fin_glxf_apl_cc")
    l_apl_nat = st.session_state.get("fin_glxf_apl_nat")
    l_apl_tip = st.session_state.get("fin_glxf_apl_tip")
    g_cc = [int(x) for x in l_apl_cc] if l_apl_cc else None
    g_nat = [int(x) for x in l_apl_nat] if l_apl_nat else None
    g_tip = [int(x) for x in l_apl_tip] if l_apl_tip else None

    _rc = st.session_state.get("fin_rep_apl_colab")
    _rn = st.session_state.get("fin_rep_apl_nat")
    _rs = st.session_state.get("fin_rep_apl_svc")
    r_col = [int(x) for x in _rc] if _rc else None
    r_nat = [str(x) for x in _rn] if _rn else None
    r_svc = None if _rs is None else [int(x) for x in _rs]

    agg = agregar_resultado_operacional_consolidado(
        conn,
        mes_referencia=_rm,
        ano_referencia=_ra,
        cenario_entradas=_cen,
        gasto_filtro_centro_ids=g_cc,
        gasto_filtro_natureza_ids=g_nat,
        gasto_filtro_tipo_ids=g_tip,
        repasse_colaborador_ids=r_col,
        repasse_naturezas=r_nat,
        repasse_servico_ids=r_svc,
        entrada_cliente_ids=None,
        entrada_naturezas=None,
        entrada_servico_ids=None,
        entrada_estados_pagamento=None,
        saldo_cliente_ids=None,
        saldo_naturezas=None,
        saldo_servico_ids=None,
    )

    e = int(agg["entradas_centavos"])
    g = int(agg["gastos_real_centavos"])
    rp = int(agg["repasses_centavos"])
    s = int(agg["saldos_exposicao_centavos"])
    res = int(agg["resultado_fluxo_centavos"])

    _ve = html.escape(fmt_euro_centavos(e))
    _vg = html.escape(fmt_euro_centavos(g))
    _vrp = html.escape(fmt_euro_centavos(rp))
    _vs = html.escape(fmt_euro_centavos(s))
    _vres = html.escape(fmt_euro_centavos(res))
    _res_cls = (
        "bea-fin-ent-tot bea-fin-ent-tot--recebido"
        if res >= 0
        else "bea-fin-ent-tot bea-fin-ent-tot--diferenca bea-fin-ent-tot--alerta-ativa"
    )
    _lbl_e = "Entradas (convertido)" if _cen != "recebido" else "Entradas (recebido)"

    b1, b2, b3, b4 = st.columns([2, 2, 2, 2], gap="small")
    with b1:
        st.markdown(
            f'<div class="bea-fin-ent-tot bea-fin-ent-tot--convertido" role="group" '
            f'aria-label="{html.escape(_lbl_e)}">'
            f'<span class="bea-fin-ent-tot__lbl">{html.escape(_lbl_e)}</span>'
            f'<span class="bea-fin-ent-tot__val">{_ve}</span></div>',
            unsafe_allow_html=True,
        )
    with b2:
        st.markdown(
            '<div class="bea-fin-ent-tot bea-fin-ent-tot--diferenca" role="group" '
            'aria-label="Gastos operacionais (Real, competência)">'
            '<span class="bea-fin-ent-tot__lbl">Gastos (Real, competência)</span>'
            f'<span class="bea-fin-ent-tot__val">{_vg}</span></div>',
            unsafe_allow_html=True,
        )
    with b3:
        st.markdown(
            '<div class="bea-fin-ent-tot bea-fin-ent-tot--recebido" role="group" '
            'aria-label="Repasses">'
            '<span class="bea-fin-ent-tot__lbl">Repasses</span>'
            f'<span class="bea-fin-ent-tot__val">{_vrp}</span></div>',
            unsafe_allow_html=True,
        )
    with b4:
        st.markdown(
            '<div class="bea-fin-ent-tot bea-fin-ent-tot--convertido" role="group" '
            'aria-label="Saldos de exposição (não entra no resultado)">'
            '<span class="bea-fin-ent-tot__lbl">Saldos (exposição)</span>'
            f'<span class="bea-fin-ent-tot__val">{_vs}</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<div class="{_res_cls}" role="group" aria-label="Resultado de fluxo">'
        '<span class="bea-fin-ent-tot__lbl">Resultado (Entradas − Gastos − Repasses)</span>'
        f'<span class="bea-fin-ent-tot__val">{_vres}</span></div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Os **Saldos (exposição)** medem crédito activo por cancelamento no período; **não** integram a linha "
        "«Resultado (Entradas − Gastos − Repasses)», que reflecte apenas fluxo operacional directo."
    )


def render_page_financeiro(*, render_back_and_breadcrumb) -> None:
    inject_constituicao_fin_page()
    st.markdown(_FIN_TOTAIS_CAIXAS_STYLE, unsafe_allow_html=True)
    render_back_and_breadcrumb(["Home", "Financeiro"], back_key="bea_back_financeiro")

    st.markdown(
        '<h1 class="bea-cv-cag-h1">Financeiro</h1>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="bea-cv-cag-gap" aria-hidden="true"></div>', unsafe_allow_html=True)

    conn = get_connection()
    if conn is None:
        st.error("Não foi possível ligar à base de dados.")
        return

    if "fin_gxc_form_v" not in st.session_state:
        st.session_state.fin_gxc_form_v = 0
    if "fin_gxc_edit_tipo_id" not in st.session_state:
        st.session_state.fin_gxc_edit_tipo_id = None
    if "fin_gxc_pending_confirm_update" not in st.session_state:
        st.session_state.fin_gxc_pending_confirm_update = False
    if "fin_glxf_filt_v" not in st.session_state:
        st.session_state.fin_glxf_filt_v = 0
    if "fin_glxc_lanc_v" not in st.session_state:
        st.session_state.fin_glxc_lanc_v = 0
    if "fin_rep_filt_v" not in st.session_state:
        st.session_state.fin_rep_filt_v = 0
    if "fin_saldo_filt_v" not in st.session_state:
        st.session_state.fin_saldo_filt_v = 0
    if "fin_ent_filt_v" not in st.session_state:
        st.session_state.fin_ent_filt_v = 0
    if "fin_rep_tbl_v" not in st.session_state:
        st.session_state.fin_rep_tbl_v = 0
    if "fin_rep_ed_nonce" not in st.session_state:
        st.session_state.fin_rep_ed_nonce = 0
    if "fin_rep_liberar_nonce" not in st.session_state:
        st.session_state.fin_rep_liberar_nonce = 0

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
            "fin_rep_apl_esp",
            "fin_rep_apl_svc",
            "fin_rep_apl_mes",
            "fin_rep_apl_ano",
        ):
            st.session_state.pop(_rk, None)
        for _rk in (
            "fin_rep_pay_open",
            "fin_rep_pay_step",
            "fin_rep_pay_ids",
            "fin_rep_save_dlg_open",
        ):
            st.session_state.pop(_rk, None)
        st.session_state.fin_rep_tbl_v = int(st.session_state.get("fin_rep_tbl_v", 0)) + 1
        st.session_state.fin_rep_liberar_nonce = int(st.session_state.get("fin_rep_liberar_nonce", 0)) + 1

    if st.session_state.pop("_fin_saldo_limpar_pending", None):
        st.session_state.fin_saldo_filt_v = int(st.session_state.get("fin_saldo_filt_v", 0)) + 1
        for _sk in (
            "fin_saldo_apl_cli",
            "fin_saldo_apl_nat",
            "fin_saldo_apl_esp",
            "fin_saldo_apl_svc",
            "fin_saldo_apl_mes",
            "fin_saldo_apl_ano",
        ):
            st.session_state.pop(_sk, None)

    if st.session_state.pop("_fin_ent_limpar_pending", None):
        st.session_state.fin_ent_filt_v = int(st.session_state.get("fin_ent_filt_v", 0)) + 1

    _h2("1. Resultado Operacional Consolidado")
    with st.expander("Painel do resultado operacional (consolidado)", expanded=False):
        _render_fin_resultado_operacional_panel(conn)

    _h2("2. Gastos Operacionais")

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

    with st.expander("Manutenção das Categorias de Gastos", expanded=False):
        if st.session_state.pop("fin_gxc_exec_confirmed_update", False):
            _fin_gxc_run_save_categorias(
                conn, fk=fk, fv=fv, cc_ids=cc_ids, confirmar_alteracao=True
            )

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
                    _fin_gxc_run_save_categorias(
                        conn, fk=fk, fv=fv, cc_ids=cc_ids, confirmar_alteracao=False
                    )

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
                sel_cc = _fin_int_id_or_none(st.session_state.get(f"{fk}l3_cc")) or 0
                nat_opts = listar_naturezas_por_centro_ativas(conn, sel_cc) if sel_cc else []
                nat_ids = [n[0] for n in nat_opts]
                nat_lbl = {n[0]: n[1] for n in nat_opts}

                def _fmt_nat(i: int) -> str:
                    return nat_lbl.get(int(i), str(i))

                with l3b:
                    if nat_ids:
                        cur_nat = st.session_state.get(f"{fk}l3_nat")
                        cur_nat_i = _fin_int_id_or_none(cur_nat)
                        if cur_nat is not None and (cur_nat_i is None or cur_nat_i not in nat_ids):
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
        _render_fin_gxc_banner_mensagens()
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
                f"Linha da tabela seleccionada — tipo **#{eid}**. "
                "Ao gravar, o sistema insere um novo tipo ou altera o existente conforme a combinação "
                "Centro / Natureza / Nome na linha 3."
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
                sel_cc_i = _fin_int_id_or_none(sel_cc_gl)
                if sel_cc_i is not None and sel_cc_i not in cc_ids:
                    sel_cc_i = None
                nat_opts_gl = listar_naturezas_por_centro_ativas(conn, sel_cc_i) if sel_cc_i else []
                nat_ids_gl = [n[0] for n in nat_opts_gl]
                nat_lbl_gl = {n[0]: n[1] for n in nat_opts_gl}

                def _fmt_nat_gl(i: int) -> str:
                    return nat_lbl_gl.get(int(i), str(i))

                with gl2:
                    if nat_ids_gl:
                        cur_nat_gl = st.session_state.get(f"{_lk}sb_nat")
                        cur_nat_gli = _fin_int_id_or_none(cur_nat_gl)
                        if cur_nat_gl is not None and (cur_nat_gli is None or cur_nat_gli not in nat_ids_gl):
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
                sel_nat_i = _fin_int_id_or_none(sel_nat_gl)
                tip_opts_gl = listar_tipos_por_natureza_ativos(conn, sel_nat_i) if sel_nat_i else []
                tip_ids_gl = [t[0] for t in tip_opts_gl]
                tip_lbl_gl = {t[0]: t[1] for t in tip_opts_gl}

                def _fmt_tip_gl(i: int) -> str:
                    return tip_lbl_gl.get(int(i), str(i))

                with gl3:
                    if tip_ids_gl:
                        cur_tip_gl = st.session_state.get(f"{_lk}sb_tip")
                        cur_tip_gli = _fin_int_id_or_none(cur_tip_gl)
                        if cur_tip_gl is not None and (cur_tip_gli is None or cur_tip_gli not in tip_ids_gl):
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

    _h2("3. Repasses")

    with st.expander("Gestão de Repasses para os Colaboradores", expanded=False):
        rep_colab_opts = listar_colaboradores_para_filtro_repasse(conn)
        rep_nat_opts = listar_naturezas_servico_para_filtro_repasse(conn)
        rep_meta = listar_servicos_metadados_para_filtro_repasse(conn)
        rep_anos = listar_anos_com_repasses(conn)
        if not rep_anos:
            rep_anos = [date.today().year]

        _rpv = int(st.session_state.get("fin_rep_filt_v", 0))
        _fin_rep_flash = st.session_state.pop("fin_rep_flash", None)
        if isinstance(_fin_rep_flash, tuple) and len(_fin_rep_flash) == 2:
            _fk, _ft = _fin_rep_flash
            if _fk == "success":
                st.success(_ft)
            elif _fk == "warning":
                st.warning(_ft)
            elif _fk == "error":
                st.error(_ft)
            else:
                st.info(_ft)
        _k_rep_col = f"fin_rep_f{_rpv}_ms_colab"
        _k_rep_nat = f"fin_rep_f{_rpv}_ms_nat"
        _k_rep_esp = f"fin_rep_f{_rpv}_ms_esp"
        _k_rep_svc = f"fin_rep_f{_rpv}_ms_svc"
        _k_rep_mes = f"fin_rep_f{_rpv}_mes"
        _k_rep_ano = f"fin_rep_f{_rpv}_ano"

        def _rep_label_esp_row(r: tuple[int, str, str, str]) -> str:
            ep = str(r[3] or "").strip()
            return REPASSE_ESP_SEM_LABEL if not ep else ep

        nat_m = list(st.session_state.get(_k_rep_nat) or [])
        rows_nat = filtra_metadados_servicos_por_naturezas(rep_meta, nat_m if nat_m else None)
        esp_opts = sorted({_rep_label_esp_row(r) for r in rows_nat}, key=str.casefold)

        esp_raw = list(st.session_state.get(_k_rep_esp) or [])
        esp_m = [str(e) for e in esp_raw if str(e) in esp_opts]
        if esp_m != esp_raw:
            st.session_state[_k_rep_esp] = esp_m

        if esp_m:
            rows_esp = filtra_metadados_servicos_por_especialidades(rows_nat, esp_m)
        else:
            rows_esp = []

        rows_esp_sorted = sorted(rows_esp, key=lambda r: (str(r[1] or "").casefold(), int(r[0])))
        rep_svc_ids = [int(r[0]) for r in rows_esp_sorted]
        rep_svc_lbl = {int(r[0]): str(r[1] or "") for r in rows_esp_sorted}
        _rep_svc_id_set = set(rep_svc_ids)

        sv_raw = list(st.session_state.get(_k_rep_svc) or [])
        sv_ok = [int(x) for x in sv_raw if int(x) in _rep_svc_id_set]
        if sv_ok != sv_raw:
            st.session_state[_k_rep_svc] = sv_ok

        if sv_ok:
            eff_svc_ids_fin: list[int] | None = list(sv_ok)
        elif rep_svc_ids:
            eff_svc_ids_fin = list(rep_svc_ids)
        elif nat_m:
            eff_svc_ids_fin = [int(r[0]) for r in rows_nat]
        else:
            eff_svc_ids_fin = None

        if eff_svc_ids_fin is None:
            rep_colab_visible = rep_colab_opts
        elif not eff_svc_ids_fin:
            rep_colab_visible = []
        else:
            _hab_fin = listar_colaboradores_mapa_equipa(eff_svc_ids_fin)
            _hab_ids_fin = {int(r["id"]) for r in _hab_fin}
            rep_colab_visible = [c for c in rep_colab_opts if c[0] in _hab_ids_fin]

        rep_c_ids = [c[0] for c in rep_colab_visible]
        rep_c_lbl = {c[0]: c[1] for c in rep_colab_visible}
        _raw_rep_colab = [int(x) for x in (st.session_state.get(_k_rep_col) or [])]
        _pruned_rep_colab = [x for x in _raw_rep_colab if x in set(rep_c_ids)]
        if _pruned_rep_colab != _raw_rep_colab:
            st.session_state[_k_rep_col] = _pruned_rep_colab

        def _fmt_rep_col(i: int) -> str:
            return rep_c_lbl.get(int(i), str(i))

        _rep_svc_opts_ui = rep_svc_ids if rep_svc_ids else [0]

        def _fmt_rep_svc(i: int) -> str:
            if i == 0 and not rep_svc_ids:
                return "—"
            return rep_svc_lbl.get(int(i), str(i))

        _rep_pode_servico = bool(esp_m) and bool(rep_svc_ids)

        rp1, rp2, rp3, rp4, rp5, rp6 = st.columns(6, vertical_alignment="top")
        with rp1:
            if rep_c_ids:
                st.multiselect(
                    "Nome do Colaborador",
                    options=rep_c_ids,
                    format_func=_fmt_rep_col,
                    key=_k_rep_col,
                )
            elif not rep_colab_opts:
                st.caption("Sem colaboradores cadastrados.")
            else:
                st.caption(
                    "Nenhum colaborador com habilitação nos serviços do filtro — alargue natureza / "
                    "especialidade / serviço ou ajuste habilitações em **Colaboradores**."
                )
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
            if esp_opts:
                st.multiselect(
                    "Especialidades",
                    options=esp_opts,
                    key=_k_rep_esp,
                )
            else:
                st.multiselect(
                    "Especialidades",
                    options=["—"],
                    default=[],
                    key=_k_rep_esp,
                    disabled=True,
                )
        with rp4:
            st.multiselect(
                "Nome do Serviço",
                options=_rep_svc_opts_ui,
                format_func=_fmt_rep_svc,
                key=_k_rep_svc,
                disabled=not _rep_pode_servico,
            )
        with rp5:
            st.selectbox(
                "Mês",
                options=list(range(0, 13)),
                index=0,
                format_func=_fmt_mes_repasse_ui,
                key=_k_rep_mes,
            )
        with rp6:
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
                _pn = list(st.session_state.get(_k_rep_nat) or [])
                _pe = list(st.session_state.get(_k_rep_esp) or [])
                _ps = list(st.session_state.get(_k_rep_svc) or [])
                _rn = filtra_metadados_servicos_por_naturezas(rep_meta, _pn if _pn else None)
                _allowed = {int(r[0]) for r in _rn}
                if _pe:
                    _rf = filtra_metadados_servicos_por_especialidades(_rn, _pe)
                    _allowed = {int(r[0]) for r in _rf}
                if _ps:
                    _ft = [int(x) for x in _ps if int(x) in _allowed]
                    if not _ft:
                        _ft = [-1]
                elif _pe:
                    _ft = list(_allowed) if _allowed else [-1]
                else:
                    _ft = None
                st.session_state.fin_rep_apl_esp = list(_pe) if esp_opts else []
                if _ft is None:
                    st.session_state.pop("fin_rep_apl_svc", None)
                else:
                    st.session_state.fin_rep_apl_svc = _ft
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
        _f_rs = None if _apl_rs is None else [int(x) for x in _apl_rs]
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
            _tbl_v = int(st.session_state.get("fin_rep_tbl_v", 0))
            _ed_nonce = int(st.session_state.get("fin_rep_ed_nonce", 0))
            _k_rep_tbl = f"fin_rep_tbl_{_rpv}_{_tbl_v}"
            # Chave com nonce: após gravar incrementamos o nonce para novo widget (desmarcado), sem
            # escrever em session_state depois do checkbox ser instanciado (StreamlitAPIException).
            _lib_nonce = int(st.session_state.get("fin_rep_liberar_nonce", 0))
            _k_lib = f"fin_rep_liberar_{_rpv}_{_lib_nonce}"
            rep_lib_on = bool(st.session_state.get(_k_lib, False))

            _cols_base = {
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
                "Repasse Pago?": [str(r.get("repasse_pago_label") or "Não") for r in rep_rows],
                "Data de Pagamento do Repasse": [
                    str(r.get("data_pagamento_repasse_dm") or "").strip() for r in rep_rows
                ],
                "Data de execução do serviço": [r["data_execucao_dm"] for r in rep_rows],
            }
            rep_df_disp = pd.DataFrame(_cols_base)

            rep_df_ed = pd.DataFrame(
                {
                    **_cols_base,
                    "Data de Pagamento do Repasse": [
                        _repasse_iso_to_date(r.get("data_pagamento_repasse_iso")) for r in rep_rows
                    ],
                }
            )

            st.checkbox(
                "Liberar atualização de dados de repasse",
                key=_k_lib,
                help="Quando activo, só «Repasse Pago?» e «Data de Pagamento do Repasse» podem ser editados.",
            )

            edited_df: pd.DataFrame | None = None
            ev_df: object | None = None
            if rep_lib_on:
                _col_cfg = {
                    "Nome da colaboradora": st.column_config.TextColumn(disabled=True),
                    "Natureza do serviço prestado": st.column_config.TextColumn(disabled=True),
                    "Nome do serviço prestado": st.column_config.TextColumn(disabled=True),
                    "Percentual de repasse acordado para este serviço": st.column_config.TextColumn(
                        disabled=True
                    ),
                    "Valor final do serviço": st.column_config.TextColumn(disabled=True),
                    "Valor do repasse": st.column_config.TextColumn(disabled=True),
                    "Repasse Pago?": st.column_config.SelectboxColumn(
                        options=["Sim", "Não"],
                        required=True,
                    ),
                    "Data de Pagamento do Repasse": st.column_config.DateColumn(
                        format="DD/MM/YYYY",
                        step=86400,
                    ),
                    "Data de execução do serviço": st.column_config.TextColumn(disabled=True),
                }
                edited_df = st.data_editor(
                    rep_df_ed.copy(),
                    column_config=_col_cfg,
                    hide_index=True,
                    width="stretch",
                    num_rows="fixed",
                    key=f"fin_rep_ed_{_rpv}_{_ed_nonce}",
                )
            else:
                ev_df = st.dataframe(
                    rep_df_disp,
                    width="stretch",
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="multi-row",
                    key=_k_rep_tbl,
                )

            dirty = False
            if rep_lib_on and edited_df is not None:
                for i in range(len(edited_df)):
                    if _norm_repasse_sim_nao(edited_df.iloc[i]["Repasse Pago?"]) != _norm_repasse_sim_nao(
                        rep_df_ed.iloc[i]["Repasse Pago?"]
                    ):
                        dirty = True
                        break
                    if _normalize_repasse_date_cell(
                        edited_df.iloc[i]["Data de Pagamento do Repasse"]
                    ) != _normalize_repasse_date_cell(rep_df_ed.iloc[i]["Data de Pagamento do Repasse"]):
                        dirty = True
                        break

            sel_idx: list[int] = []
            if not rep_lib_on and ev_df is not None:
                sel_idx = _df_selected_rows(ev_df, _k_rep_tbl)

            if dirty:
                _b_save_only, _b_rest_dirty = st.columns([3.2, 22], gap="small", vertical_alignment="center")
                with _b_save_only:
                    if (
                        rep_lib_on
                        and edited_df is not None
                        and not bool(st.session_state.get("fin_rep_save_dlg_open"))
                    ):
                        if st.button("Salvar Alteração de Repasse", key=f"fin_rep_save_{_rpv}"):
                            st.session_state.fin_rep_save_dlg_open = True
                            st.rerun()
            else:
                _b_pay, _b_rest = st.columns([3.2, 22], gap="small", vertical_alignment="center")
                with _b_pay:
                    if st.button(
                        "Confirmar pagamento de Repasse?",
                        key=f"fin_rep_conf_pay_{_rpv}",
                        disabled=rep_lib_on,
                        help=(
                            "Desmarque «Liberar atualização de dados de repasse» e seleccione uma ou mais linhas."
                            if rep_lib_on
                            else None
                        ),
                    ):
                        if not sel_idx:
                            st.warning("Seleccione pelo menos uma linha na tabela.")
                        else:
                            _ids_pay = [
                                int(rep_rows[i]["repasse_linha_id"])
                                for i in sel_idx
                                if 0 <= int(i) < len(rep_rows)
                            ]
                            if not _ids_pay:
                                st.warning("Seleccione pelo menos uma linha na tabela.")
                            else:
                                st.session_state.fin_rep_pay_open = True
                                st.session_state.fin_rep_pay_step = 1
                                st.session_state.fin_rep_pay_ids = _ids_pay
                                st.rerun()

            if st.session_state.get("fin_rep_save_dlg_open"):

                @st.dialog("Confirmar alteração de repasses")
                def _fin_dlg_repasse_salvar_edicao() -> None:
                    if edited_df is None or not rep_lib_on:
                        st.session_state.pop("fin_rep_save_dlg_open", None)
                        st.rerun()
                        return
                    st.caption(f"{len(edited_df)} linha(s) na tabela.")
                    st.markdown("Deseja prosseguir com as alteracoes realizadas?")
                    _sda, _sdb = st.columns(2)
                    with _sda:
                        if st.button("Sim, continuar", key="fin_rep_save_dlg_cont", type="primary"):
                            linhas_sv: list[tuple[int, bool, str | None]] = []
                            err = False
                            for i in range(len(edited_df)):
                                rid = int(rep_rows[i]["repasse_linha_id"])
                                sim = _norm_repasse_sim_nao(edited_df.iloc[i]["Repasse Pago?"]) == "Sim"
                                d10 = _normalize_repasse_date_cell(
                                    edited_df.iloc[i]["Data de Pagamento do Repasse"]
                                )
                                if sim and not d10:
                                    st.error(
                                        "Para linhas com «Repasse Pago?» = Sim, indique a "
                                        "«Data de Pagamento do Repasse»."
                                    )
                                    err = True
                                    break
                                linhas_sv.append((rid, sim, d10 if sim else None))
                            if not err:
                                ok_sv, msg_sv, _n = aplicar_edicao_repasse_linhas_gestao(conn, linhas_sv)
                                if ok_sv:
                                    st.session_state.pop("fin_rep_save_dlg_open", None)
                                    st.session_state.fin_rep_liberar_nonce = (
                                        int(st.session_state.get("fin_rep_liberar_nonce", 0)) + 1
                                    )
                                    st.session_state.fin_rep_ed_nonce = (
                                        int(st.session_state.get("fin_rep_ed_nonce", 0)) + 1
                                    )
                                    st.session_state.fin_rep_tbl_v = (
                                        int(st.session_state.get("fin_rep_tbl_v", 0)) + 1
                                    )
                                    st.session_state.fin_rep_flash = ("success", msg_sv)
                                    st.rerun()
                                else:
                                    st.warning(msg_sv)
                    with _sdb:
                        if st.button("Cancelar", key="fin_rep_save_dlg_cancel"):
                            st.session_state.pop("fin_rep_save_dlg_open", None)
                            st.rerun()

                _fin_dlg_repasse_salvar_edicao()

            if st.session_state.get("fin_rep_pay_open"):

                @st.dialog("Confirmar pagamento de repasses")
                def _fin_dlg_repasse_pagar() -> None:
                    ids_d = [int(x) for x in (st.session_state.get("fin_rep_pay_ids") or [])]
                    step_d = int(st.session_state.get("fin_rep_pay_step", 1) or 1)
                    if not ids_d:
                        for k in ("fin_rep_pay_open", "fin_rep_pay_step", "fin_rep_pay_ids"):
                            st.session_state.pop(k, None)
                        st.rerun()
                        return
                    st.caption(f"{len(ids_d)} linha(s) seleccionada(s).")
                    if step_d == 1:
                        st.markdown(
                            "Deseja prosseguir com o registo do pagamento dos repasses seleccionados? "
                            "Na etapa seguinte será pedida a data em que o repasse foi pago."
                        )
                        d1a, d1b = st.columns(2)
                        with d1a:
                            if st.button("Sim, continuar", key="fin_rep_dlg_cont", type="primary"):
                                st.session_state.fin_rep_pay_step = 2
                                st.rerun()
                        with d1b:
                            if st.button("Cancelar", key="fin_rep_dlg_cancel1"):
                                for k in ("fin_rep_pay_open", "fin_rep_pay_step", "fin_rep_pay_ids"):
                                    st.session_state.pop(k, None)
                                st.rerun()
                    else:
                        if st.button("← Voltar", key="fin_rep_dlg_back"):
                            st.session_state.fin_rep_pay_step = 1
                            st.rerun()
                        d_pg = st.date_input(
                            "Data em que o repasse foi pago",
                            value=date.today(),
                            key="fin_rep_pay_dt_input",
                        )
                        if st.button("Confirmar pagamento", key="fin_rep_dlg_ok", type="primary"):
                            iso10 = d_pg.isoformat()
                            ok_p, msg_p, _n = marcar_repasses_como_pagos(
                                conn, ids_d, data_pagamento_iso10=iso10
                            )
                            for k in ("fin_rep_pay_open", "fin_rep_pay_step", "fin_rep_pay_ids"):
                                st.session_state.pop(k, None)
                            if ok_p:
                                st.session_state.fin_rep_tbl_v = (
                                    int(st.session_state.get("fin_rep_tbl_v", 0)) + 1
                                )
                                st.session_state.fin_rep_ed_nonce = (
                                    int(st.session_state.get("fin_rep_ed_nonce", 0)) + 1
                                )
                                st.session_state.fin_rep_flash = ("success", msg_p)
                                st.rerun()
                            else:
                                st.session_state.fin_rep_flash = ("warning", msg_p)
                                st.rerun()

                _fin_dlg_repasse_pagar()
        else:
            st.caption(
                "Nenhuma linha de repasse encontrada. Use **PESQUISAR** (filtros opcionais) "
                "ou confirme se existem agendamentos concluídos / com pagamento parcial com repasse calculado."
            )

    _h2("4. Saldos de serviço dos clientes")

    with st.expander("Gestão de saldos ativos dos clientes", expanded=False):
        sal_cli_opts = listar_clientes_com_saldo_credito_positivo(conn)
        sal_nat_opts = listar_naturezas_servico_para_filtro_repasse(conn)
        sal_meta = listar_servicos_metadados_para_filtro_repasse(conn)
        sal_anos = listar_anos_com_repasses(conn)
        if not sal_anos:
            sal_anos = [date.today().year]

        _sv = int(st.session_state.get("fin_saldo_filt_v", 0))
        _k_sal_cli = f"fin_saldo_f{_sv}_ms_cli"
        _k_sal_nat = f"fin_saldo_f{_sv}_ms_nat"
        _k_sal_esp = f"fin_saldo_f{_sv}_ms_esp"
        _k_sal_svc = f"fin_saldo_f{_sv}_ms_svc"
        _k_sal_mes = f"fin_saldo_f{_sv}_mes"
        _k_sal_ano = f"fin_saldo_f{_sv}_ano"

        def _sal_label_esp_row(r: tuple[int, str, str, str]) -> str:
            ep = str(r[3] or "").strip()
            return REPASSE_ESP_SEM_LABEL if not ep else ep

        nat_s = list(st.session_state.get(_k_sal_nat) or [])
        _sal_com_natureza = bool(nat_s)
        rows_nat_s = filtra_metadados_servicos_por_naturezas(
            sal_meta, nat_s if nat_s else None
        )
        if _sal_com_natureza:
            esp_opts_s = sorted(
                {_sal_label_esp_row(r) for r in rows_nat_s}, key=str.casefold
            )
        else:
            esp_opts_s = []

        esp_raw_s = list(st.session_state.get(_k_sal_esp) or [])
        if not _sal_com_natureza:
            if esp_raw_s:
                st.session_state[_k_sal_esp] = []
            esp_m_s = []
        else:
            esp_m_s = [str(e) for e in esp_raw_s if str(e) in esp_opts_s]
            if esp_m_s != esp_raw_s:
                st.session_state[_k_sal_esp] = esp_m_s

        if esp_m_s:
            rows_esp_s = filtra_metadados_servicos_por_especialidades(rows_nat_s, esp_m_s)
        else:
            rows_esp_s = []

        rows_esp_sorted_s = sorted(rows_esp_s, key=lambda r: (str(r[1] or "").casefold(), int(r[0])))
        sal_svc_ids = [int(r[0]) for r in rows_esp_sorted_s]
        sal_svc_lbl = {int(r[0]): str(r[1] or "") for r in rows_esp_sorted_s}
        _sal_svc_id_set = set(sal_svc_ids)

        sv_raw = list(st.session_state.get(_k_sal_svc) or [])
        sv_ok = [int(x) for x in sv_raw if int(x) in _sal_svc_id_set]
        if sv_ok != sv_raw:
            st.session_state[_k_sal_svc] = sv_ok

        sal_cli_ids = [c[0] for c in sal_cli_opts]
        sal_cli_lbl = {c[0]: c[1] for c in sal_cli_opts}

        def _fmt_sal_cli(i: int) -> str:
            return sal_cli_lbl.get(int(i), str(i))

        _sal_svc_opts_ui = sal_svc_ids if sal_svc_ids else [0]

        def _fmt_sal_svc(i: int) -> str:
            if i == 0 and not sal_svc_ids:
                return "—"
            return sal_svc_lbl.get(int(i), str(i))

        _sal_pode_servico = bool(esp_m_s) and bool(sal_svc_ids)

        sp1, sp2, sp3, sp4, sp5, sp6 = st.columns(6, vertical_alignment="top")
        with sp1:
            if sal_cli_ids:
                st.multiselect(
                    "Nome do Cliente",
                    options=sal_cli_ids,
                    format_func=_fmt_sal_cli,
                    key=_k_sal_cli,
                )
            else:
                st.caption("Nenhum cliente com saldo de crédito > 0.")
        with sp2:
            if sal_nat_opts:
                st.multiselect(
                    "Natureza do Serviço",
                    options=sal_nat_opts,
                    key=_k_sal_nat,
                )
            else:
                st.caption("Sem naturezas no catálogo.")
        with sp3:
            _sal_esp_help = (
                "Seleccione pelo menos uma natureza do serviço para filtrar por especialidade."
            )
            if not _sal_com_natureza:
                st.multiselect(
                    "Especialidades",
                    options=["—"],
                    default=[],
                    key=_k_sal_esp,
                    disabled=True,
                    help=_sal_esp_help,
                )
            elif esp_opts_s:
                st.multiselect(
                    "Especialidades",
                    options=esp_opts_s,
                    key=_k_sal_esp,
                )
            else:
                st.multiselect(
                    "Especialidades",
                    options=["—"],
                    default=[],
                    key=_k_sal_esp,
                    disabled=True,
                    help="Nenhuma especialidade nas naturezas seleccionadas.",
                )
        with sp4:
            st.multiselect(
                "Nome do Serviço",
                options=_sal_svc_opts_ui,
                format_func=_fmt_sal_svc,
                key=_k_sal_svc,
                disabled=not _sal_pode_servico,
            )
        with sp5:
            st.selectbox(
                "Mês",
                options=list(range(0, 13)),
                index=0,
                format_func=_fmt_mes_repasse_ui,
                key=_k_sal_mes,
            )
        with sp6:
            st.selectbox(
                "Ano",
                options=[0] + list(sal_anos),
                index=0,
                format_func=lambda y: "Todos" if int(y) == 0 else str(int(y)),
                key=_k_sal_ano,
            )

        sb_clear, _sb_rest = st.columns([3.2, 22], gap="small", vertical_alignment="center")
        with sb_clear:
            if st.button("Limpar Pesquisa", key="fin_saldo_btn_limpar"):
                st.session_state["_fin_saldo_limpar_pending"] = True
                st.rerun()

        # Filtros = estado actual dos widgets (tabela + totais actualizam em cada interacção).
        _pn_live = list(st.session_state.get(_k_sal_nat) or [])
        _pe_live = list(st.session_state.get(_k_sal_esp) or [])
        _ps_live = list(st.session_state.get(_k_sal_svc) or [])

        _rn_live = filtra_metadados_servicos_por_naturezas(
            sal_meta, _pn_live if _pn_live else None
        )
        _allowed_live = {int(r[0]) for r in _rn_live}
        if _pe_live:
            _rf_live = filtra_metadados_servicos_por_especialidades(_rn_live, _pe_live)
            _allowed_live = {int(r[0]) for r in _rf_live}
        if _ps_live:
            _ft_live = [int(x) for x in _ps_live if int(x) in _allowed_live]
            if not _ft_live:
                _ft_live = [-1]
        elif _pe_live:
            _ft_live = list(_allowed_live) if _allowed_live else [-1]
        else:
            _ft_live = None

        _cli_live = list(st.session_state.get(_k_sal_cli) or [])
        _f_scli = [int(x) for x in _cli_live] if (sal_cli_ids and _cli_live) else None
        _f_snat = [str(x) for x in _pn_live] if _pn_live else None
        _f_ssvc = None if _ft_live is None else _ft_live

        _m_live = int(st.session_state.get(_k_sal_mes, 0) or 0)
        _a_live = int(st.session_state.get(_k_sal_ano, 0) or 0)
        _f_smes = None if _m_live == 0 else _m_live
        _f_sano = None if _a_live == 0 else _a_live

        saldo_rows = listar_linhas_gestao_saldos_clientes_ativos(
            conn,
            cliente_ids=_f_scli,
            naturezas=_f_snat,
            servico_ids=_f_ssvc,
            mes=_f_smes,
            ano=_f_sano,
        )
        tot_s, r15_s, o15_s = totais_saldos_ativos_por_antiguidade_cancelamento(saldo_rows)

        uso_rows = listar_vendas_com_consumo_credito_loja(
            conn,
            cliente_ids=_f_scli,
            naturezas=_f_snat,
            servico_ids=_f_ssvc,
            mes=_f_smes,
            ano=_f_sano,
        )

        if saldo_rows:
            saldo_df = pd.DataFrame(
                {
                    "Nome do Cliente": [r["cliente_nome"] for r in saldo_rows],
                    "Natureza do serviço prestado": [r["natureza_servico"] for r in saldo_rows],
                    "Especialidades": [r["especialidade"] for r in saldo_rows],
                    "Nome do Serviço prestado": [r["nome_servico"] for r in saldo_rows],
                    "Referente a Pacote?": [r["referente_a_pacote"] for r in saldo_rows],
                    "Nome do Pacote": [r["nome_pacote"] for r in saldo_rows],
                    "Saldo do Cliente": [
                        fmt_euro_centavos(int(r["saldo_restante_centavos"])) for r in saldo_rows
                    ],
                    "Data de aquisição do serviço de origem": [
                        r["data_aquisicao_dm"] for r in saldo_rows
                    ],
                    "Data do cancelamento do serviço de origem": [
                        r["data_cancelamento_dm"] for r in saldo_rows
                    ],
                }
            )
            st.dataframe(saldo_df, width="stretch", hide_index=True)
        else:
            st.caption(
                "Nenhuma linha de saldo activo por cancelamento para os filtros actuais. "
                "Ajuste os filtros ou confirme se existem créditos de cancelamento ainda não totalmente consumidos em vendas."
            )

        # Totais (mesmos filtros que a tabela); mesmas caixas visuais que em 5. Entradas (≤50%: [2+2+2+6]).
        _sal_v_tot = html.escape(fmt_euro_centavos(int(tot_s)))
        _sal_v_r15 = html.escape(fmt_euro_centavos(int(r15_s)))
        _sal_v_o15 = html.escape(fmt_euro_centavos(int(o15_s)))
        _sal_o15_cls = (
            "bea-fin-ent-tot bea-fin-ent-tot--diferenca bea-fin-ent-tot--alerta-ativa"
            if int(o15_s) != 0
            else "bea-fin-ent-tot bea-fin-ent-tot--diferenca"
        )
        _sal_b1, _sal_b2, _sal_b3, _sal_bz = st.columns([2, 2, 2, 6], gap="small")
        with _sal_b1:
            st.markdown(
                f'<div class="bea-fin-ent-tot bea-fin-ent-tot--convertido" role="group" '
                f'aria-label="Total Acumulado - Saldo dos Clientes">'
                f'<span class="bea-fin-ent-tot__lbl">Total Acumulado - Saldo dos Clientes</span>'
                f'<span class="bea-fin-ent-tot__val">{_sal_v_tot}</span></div>',
                unsafe_allow_html=True,
            )
        with _sal_b2:
            st.markdown(
                f'<div class="bea-fin-ent-tot bea-fin-ent-tot--recebido" role="group" '
                f'aria-label="Saldo Acumulado (até 15 dias)">'
                f'<span class="bea-fin-ent-tot__lbl">Saldo Acumulado (até 15 dias)</span>'
                f'<span class="bea-fin-ent-tot__val">{_sal_v_r15}</span></div>',
                unsafe_allow_html=True,
            )
        with _sal_b3:
            st.markdown(
                f'<div class="{_sal_o15_cls}" role="group" '
                f'aria-label="Saldo Acumulado (mais de 15 dias)">'
                f'<span class="bea-fin-ent-tot__lbl">Saldo Acumulado (mais de 15 dias)</span>'
                f'<span class="bea-fin-ent-tot__val">{_sal_v_o15}</span></div>',
                unsafe_allow_html=True,
            )
        with _sal_bz:
            st.empty()

        st.markdown("**Registo de utilização de saldo em vendas**")
        if uso_rows:
            uso_df = pd.DataFrame(
                {
                    "Nome do Cliente": [r["cliente_nome"] for r in uso_rows],
                    "Data da venda": [r["data_venda_dm"] for r in uso_rows],
                    "Natureza do serviço": [r["natureza_servico"] for r in uso_rows],
                    "Especialidade": [r["especialidade"] for r in uso_rows],
                    "Nome do serviço adquirido": [r["nome_servico"] for r in uso_rows],
                    "Valor venda original (sem uso do saldo)": [
                        fmt_euro_centavos(int(r["valor_original_sem_saldo_centavos"])) for r in uso_rows
                    ],
                    "Valor do saldo utilizado": [
                        fmt_euro_centavos(int(r["valor_saldo_utilizado_centavos"])) for r in uso_rows
                    ],
                    "Valor final com saldo abatido": [
                        fmt_euro_centavos(int(r["valor_final_com_saldo_abatido_centavos"]))
                        for r in uso_rows
                    ],
                }
            )
            st.dataframe(uso_df, width="stretch", hide_index=True)
        else:
            st.caption("Nenhuma venda com consumo de crédito de loja para os filtros actuais.")

    _h2("5. Entradas")

    _fin_ent_sucesso = st.session_state.get("fin_ent_fatura_sucesso", False)
    _k_ent_exp_open = "fin_ent_expander_open"
    if _k_ent_exp_open not in st.session_state:
        st.session_state[_k_ent_exp_open] = False
    
    # Se acabou de ter sucesso, forçamos o expander a abrir se não estiver
    if _fin_ent_sucesso:
        st.session_state[_k_ent_exp_open] = True

    with st.expander("Gestão de valores convertidos (vendas)", expanded=st.session_state[_k_ent_exp_open]):
        # Se o usuário interagir com qualquer widget que cause rerun, 
        # o 'expanded' virá do session_state. 
        # No Streamlit, expanders não atualizam o session_state automaticamente ao abrir/fechar via clique,
        # mas aqui garantimos que se ele estava aberto por um sucesso ou interação, ele permaneça.
        # Para melhorar a UX, vamos setar como True sempre que entrarmos aqui, 
        # a menos que o usuário explicitamente feche (o que o Streamlit trata via JS/Frontend).
        # Contudo, ao selecionar uma linha na tabela (rerun), queremos que continue aberto.
        st.session_state[_k_ent_exp_open] = True

        ent_cli_opts = listar_clientes_com_venda_para_filtro_entradas(conn)
        ent_nat_opts = listar_naturezas_servico_para_filtro_repasse(conn)
        ent_meta = listar_servicos_metadados_para_filtro_repasse(conn)
        ent_anos = listar_anos_com_repasses(conn)
        if not ent_anos:
            ent_anos = [date.today().year]

        _ve = int(st.session_state.get("fin_ent_filt_v", 0))
        _k_ent_cli = f"fin_ent_f{_ve}_ms_cli"
        _k_ent_nat = f"fin_ent_f{_ve}_ms_nat"
        _k_ent_esp = f"fin_ent_f{_ve}_ms_esp"
        _k_ent_svc = f"fin_ent_f{_ve}_ms_svc"
        _k_ent_est = f"fin_ent_f{_ve}_sel_est"
        _k_ent_fat = f"fin_ent_f{_ve}_sel_fat"
        _k_ent_mes = f"fin_ent_f{_ve}_mes"
        _k_ent_ano = f"fin_ent_f{_ve}_ano"

        def _ent_label_esp_row(r: tuple[int, str, str, str]) -> str:
            ep = str(r[3] or "").strip()
            return REPASSE_ESP_SEM_LABEL if not ep else ep

        nat_e = list(st.session_state.get(_k_ent_nat) or [])
        _ent_com_natureza = bool(nat_e)
        rows_nat_e = filtra_metadados_servicos_por_naturezas(ent_meta, nat_e if nat_e else None)
        if _ent_com_natureza:
            esp_opts_e = sorted(
                {_ent_label_esp_row(r) for r in rows_nat_e}, key=str.casefold
            )
        else:
            esp_opts_e = []

        esp_raw_e = list(st.session_state.get(_k_ent_esp) or [])
        if not _ent_com_natureza:
            if esp_raw_e:
                st.session_state[_k_ent_esp] = []
            esp_m_e = []
        else:
            esp_m_e = [str(x) for x in esp_raw_e if str(x) in esp_opts_e]
            if esp_m_e != esp_raw_e:
                st.session_state[_k_ent_esp] = esp_m_e

        if esp_m_e:
            rows_esp_e = filtra_metadados_servicos_por_especialidades(rows_nat_e, esp_m_e)
        else:
            rows_esp_e = []

        rows_esp_sorted_e = sorted(
            rows_esp_e, key=lambda r: (str(r[1] or "").casefold(), int(r[0]))
        )
        ent_svc_ids = [int(r[0]) for r in rows_esp_sorted_e]
        ent_svc_lbl = {int(r[0]): str(r[1] or "") for r in rows_esp_sorted_e}
        _ent_svc_id_set = set(ent_svc_ids)

        sv_raw_e = list(st.session_state.get(_k_ent_svc) or [])
        sv_ok_e = [int(x) for x in sv_raw_e if int(x) in _ent_svc_id_set]
        if sv_ok_e != sv_raw_e:
            st.session_state[_k_ent_svc] = sv_ok_e

        ent_cli_ids = [c[0] for c in ent_cli_opts]
        ent_cli_lbl = {c[0]: c[1] for c in ent_cli_opts}

        def _fmt_ent_cli(i: int) -> str:
            return ent_cli_lbl.get(int(i), str(i))

        _ent_svc_opts_ui = ent_svc_ids if ent_svc_ids else [0]

        def _fmt_ent_svc(i: int) -> str:
            if i == 0 and not ent_svc_ids:
                return "—"
            return ent_svc_lbl.get(int(i), str(i))

        _ent_pode_servico = bool(esp_m_e) and bool(ent_svc_ids)

        _ent_est_opts = ["", "integral", "pendente", "parcial", "parcelado"]
        _ent_fat_opts = ["Todos", "Sim", "Não"]

        def _fmt_ent_estado_sel(ev: str) -> str:
            if not (ev or "").strip():
                return "Todos"
            return fmt_estado_pagamento_ui(str(ev))

        ec1, ec2, ec3, ec4, ec5, ec_fatura, ec6, ec7 = st.columns(
            8, vertical_alignment="top", gap="small"
        )
        with ec1:
            if ent_cli_ids:
                st.multiselect(
                    "Nome do Cliente",
                    options=ent_cli_ids,
                    format_func=_fmt_ent_cli,
                    key=_k_ent_cli,
                )
            else:
                st.caption("Sem vendas registadas.")
        with ec2:
            if ent_nat_opts:
                st.multiselect(
                    "Natureza do Serviço",
                    options=ent_nat_opts,
                    key=_k_ent_nat,
                )
            else:
                st.caption("Sem naturezas no catálogo.")
        with ec3:
            _ent_esp_help = (
                "Seleccione pelo menos uma natureza do serviço para filtrar por especialidade."
            )
            if not _ent_com_natureza:
                st.multiselect(
                    "Especialidades",
                    options=["—"],
                    default=[],
                    key=_k_ent_esp,
                    disabled=True,
                    help=_ent_esp_help,
                )
            elif esp_opts_e:
                st.multiselect(
                    "Especialidades",
                    options=esp_opts_e,
                    key=_k_ent_esp,
                )
            else:
                st.multiselect(
                    "Especialidades",
                    options=["—"],
                    default=[],
                    key=_k_ent_esp,
                    disabled=True,
                    help="Nenhuma especialidade nas naturezas seleccionadas.",
                )
        with ec4:
            st.multiselect(
                "Nome do Serviço",
                options=_ent_svc_opts_ui,
                format_func=_fmt_ent_svc,
                key=_k_ent_svc,
                disabled=not _ent_pode_servico,
            )
        with ec5:
            st.selectbox(
                "Estado de Pagamento",
                options=_ent_est_opts,
                index=0,
                format_func=_fmt_ent_estado_sel,
                key=_k_ent_est,
            )
        with ec_fatura:
            st.selectbox(
                "Fatura Solicitada",
                options=_ent_fat_opts,
                index=0,
                key=_k_ent_fat,
            )
        with ec6:
            st.selectbox(
                "Mês",
                options=list(range(0, 13)),
                index=0,
                format_func=_fmt_mes_repasse_ui,
                key=_k_ent_mes,
            )
        with ec7:
            st.selectbox(
                "Ano",
                options=[0] + list(ent_anos),
                index=0,
                format_func=lambda y: "Todos" if int(y) == 0 else str(int(y)),
                key=_k_ent_ano,
            )

        eb_clear, _eb_rest = st.columns([3.2, 22], gap="small", vertical_alignment="center")
        with eb_clear:
            if st.button("Limpar Pesquisa", key="fin_ent_btn_limpar"):
                st.session_state["_fin_ent_limpar_pending"] = True
                st.rerun()

        _pn_ent = list(st.session_state.get(_k_ent_nat) or [])
        _pe_ent = list(st.session_state.get(_k_ent_esp) or [])
        _ps_ent = list(st.session_state.get(_k_ent_svc) or [])

        _rn_ent = filtra_metadados_servicos_por_naturezas(
            ent_meta, _pn_ent if _pn_ent else None
        )
        _allowed_ent = {int(r[0]) for r in _rn_ent}
        if _pe_ent:
            _rf_ent = filtra_metadados_servicos_por_especialidades(_rn_ent, _pe_ent)
            _allowed_ent = {int(r[0]) for r in _rf_ent}
        if _ps_ent:
            _ft_ent = [int(x) for x in _ps_ent if int(x) in _allowed_ent]
            if not _ft_ent:
                _ft_ent = [-1]
        elif _pe_ent:
            _ft_ent = list(_allowed_ent) if _allowed_ent else [-1]
        else:
            _ft_ent = None

        _cli_ent = list(st.session_state.get(_k_ent_cli) or [])
        _f_ecli = [int(x) for x in _cli_ent] if (ent_cli_ids and _cli_ent) else None
        _f_enat = [str(x) for x in _pn_ent] if _pn_ent else None
        _f_esvc = None if _ft_ent is None else _ft_ent

        _m_ent = int(st.session_state.get(_k_ent_mes, 0) or 0)
        _a_ent = int(st.session_state.get(_k_ent_ano, 0) or 0)
        _f_emes = None if _m_ent == 0 else _m_ent
        _f_eano = None if _a_ent == 0 else _a_ent

        _est_sel = str(st.session_state.get(_k_ent_est) or "").strip().lower()
        _f_eest = None if not _est_sel else [_est_sel]

        _fat_sel = str(st.session_state.get(_k_ent_fat) or "Todos").strip()
        _f_efat = None
        if _fat_sel == "Sim":
            _f_efat = 1
        elif _fat_sel == "Não":
            _f_efat = 0

        ent_rows = listar_linhas_gestao_entradas_convertidas_vendas(
            conn,
            cliente_ids=_f_ecli,
            naturezas=_f_enat,
            servico_ids=_f_esvc,
            mes=_f_emes,
            ano=_f_eano,
            estados_pagamento=_f_eest,
            fatura_solicitada=_f_efat,
        )

        _ent_tot_conv = sum(int(r["valor_final_venda_centavos"]) for r in ent_rows)
        _ent_tot_rec = sum(int(r["total_valor_recebido_centavos"]) for r in ent_rows)
        _ent_tot_diff = int(_ent_tot_conv) - int(_ent_tot_rec)

        if ent_rows:
            _k_ent_tbl = f"fin_ent_tbl_{_ve}"
            
            page_size = 10
            total_pages = max(1, (len(ent_rows) + page_size - 1) // page_size)
            _k_page = f"fin_ent_page_{_ve}"
            if _k_page not in st.session_state:
                st.session_state[_k_page] = 1

            if st.session_state[_k_page] > total_pages:
                st.session_state[_k_page] = 1

            current_page = st.session_state[_k_page]
            start_idx = (current_page - 1) * page_size
            end_idx = start_idx + page_size
            
            page_rows = ent_rows[start_idx:end_idx]

            ent_df = pd.DataFrame(
                {
                    "Data de aquisição do serviço de origem": [
                        r["data_registo_dm"] for r in page_rows
                    ],
                    "Fatura Solicitada": [
                        "Sim" if r.get("fatura_solicitada", 0) else "Não" for r in page_rows
                    ],
                    "Fatura Emitida": [
                        "Sim" if r.get("fatura_emitida", 0) else "Não" for r in page_rows
                    ],
                    "Número da Fatura": [
                        r.get("fatura_numero", "") for r in page_rows
                    ],
                    "Nome do Cliente": [r["cliente_nome"] for r in page_rows],
                    "Natureza do serviço prestado": [
                        r["natureza_servico"] for r in page_rows
                    ],
                    "Especialidades": [r["especialidade"] for r in page_rows],
                    "Nome do Serviço prestado": [r["nome_servico"] for r in page_rows],
                    "Valor Final de Venda": [
                        fmt_euro_centavos(int(r["valor_final_venda_centavos"]))
                        for r in page_rows
                    ],
                    "Valor Bruto Original": [
                        fmt_euro_centavos(int(r["valor_bruto_centavos"])) for r in page_rows
                    ],
                    "Descontos": [
                        fmt_euro_centavos(int(r["descontos_centavos"])) for r in page_rows
                    ],
                    "% Descontos": [
                        f"{float(r.get('pct_descontos') or 0):.2f} %".replace(".", ",")
                        for r in page_rows
                    ],
                    "Saldo Aplicado": [
                        fmt_euro_centavos(int(r["saldo_aplicado_centavos"]))
                        for r in page_rows
                    ],
                    "Repasse do Colaborador": [
                        fmt_euro_centavos(int(r["repasse_colaborador_centavos"]))
                        for r in page_rows
                    ],
                    "Resultado Final Apurado": [
                        fmt_euro_centavos(int(r["resultado_final_apurado_centavos"]))
                        for r in page_rows
                    ],
                    "Estado Atual Pagamento": [
                        r["estado_pagamento_ui"] for r in page_rows
                    ],
                    "Total do valor recebido": [
                        fmt_euro_centavos(int(r["total_valor_recebido_centavos"]))
                        for r in page_rows
                    ],
                }
            )
            ev_ent = st.dataframe(
                ent_df,
                width="stretch",
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key=_k_ent_tbl
            )
            
            col_prev, col_info, col_next = st.columns([1, 2, 1])
            with col_prev:
                if st.button("⬅️ Anterior", disabled=current_page <= 1, key=f"fin_ent_prev_{_ve}"):
                    st.session_state[_k_page] = current_page - 1
                    st.rerun()
            with col_info:
                st.markdown(f"<div style='text-align: center;'>Página {current_page} de {total_pages} (Total: {len(ent_rows)} registos)</div>", unsafe_allow_html=True)
            with col_next:
                if st.button("Próxima ➡️", disabled=current_page >= total_pages, key=f"fin_ent_next_{_ve}"):
                    st.session_state[_k_page] = current_page + 1
                    st.rerun()

            sel_ent_rows = _df_selected_rows(ev_ent, _k_ent_tbl)
        else:
            sel_ent_rows = []
            st.caption(
                "Nenhum registo de venda para os filtros actuais. Ajuste os filtros ou registe vendas no **Painel de Vendas**."
            )

        st.markdown("<br/>", unsafe_allow_html=True)
        _v_conv = html.escape(fmt_euro_centavos(_ent_tot_conv))
        _v_rec = html.escape(fmt_euro_centavos(_ent_tot_rec))
        _v_dif = html.escape(fmt_euro_centavos(_ent_tot_diff))
        _ent_dif_cls = (
            "bea-fin-ent-tot bea-fin-ent-tot--diferenca bea-fin-ent-tot--alerta-ativa"
            if int(_ent_tot_diff) != 0
            else "bea-fin-ent-tot bea-fin-ent-tot--diferenca"
        )
        _ent_e1, _ent_e2, _ent_e3, _ent_ez = st.columns([2, 2, 2, 6], gap="small")
        with _ent_e1:
            st.markdown(
                f'<div class="bea-fin-ent-tot bea-fin-ent-tot--convertido" role="group" '
                f'aria-label="Valor Total Vendido">'
                f'<span class="bea-fin-ent-tot__lbl">Valor Total Vendido</span>'
                f'<span class="bea-fin-ent-tot__val">{_v_conv}</span></div>',
                unsafe_allow_html=True,
            )
        with _ent_e2:
            st.markdown(
                f'<div class="bea-fin-ent-tot bea-fin-ent-tot--recebido" role="group" '
                f'aria-label="Valor Total Recebido">'
                f'<span class="bea-fin-ent-tot__lbl">Valor Total Recebido</span>'
                f'<span class="bea-fin-ent-tot__val">{_v_rec}</span></div>',
                unsafe_allow_html=True,
            )
        with _ent_e3:
            st.markdown(
                f'<div class="{_ent_dif_cls}" role="group" '
                f'aria-label="Diferença - Vendido x Recebido">'
                f'<span class="bea-fin-ent-tot__lbl">Diferença - Vendido x Recebido</span>'
                f'<span class="bea-fin-ent-tot__val">{_v_dif}</span></div>',
                unsafe_allow_html=True,
            )
        with _ent_ez:
            st.empty()

        if st.session_state.pop("fin_ent_fatura_sucesso", False):
            st.success("Alteração concluída.")
        _fin_ent_err = st.session_state.pop("fin_ent_fatura_erro", None)
        if _fin_ent_err:
            st.error(_fin_ent_err)

        if ent_rows and sel_ent_rows:
            idx = start_idx + sel_ent_rows[0]
            if 0 <= idx < len(ent_rows):
                r_sel = ent_rows[idx]
                
                st.markdown("---")
                
                st.markdown("**Informações do Serviço Selecionado**")
                
                tc1, tc2, tc3, tc4 = st.columns(4)
                with tc1:
                    st.text_input("Nome do Cliente", value=r_sel["cliente_nome"], disabled=True, key="fin_ent_ro_cli")
                with tc2:
                    st.text_input("Data da Aquisicao", value=r_sel["data_registo_dm"], disabled=True, key="fin_ent_ro_data")
                with tc3:
                    st.text_input("Serviço Adquirido", value=r_sel["nome_servico"], disabled=True, key="fin_ent_ro_svc")
                with tc4:
                    st.text_input("Valor final de venda", value=fmt_euro_centavos(int(r_sel["valor_final_venda_centavos"])), disabled=True, key="fin_ent_ro_val")
                
                st.markdown("**Informações de Faturamento**")
                
                _k_lib = f"fin_ent_lib_ed_{r_sel['venda_id']}"
                liberar_edicao = st.checkbox("Liberar edicao de dados de faturamento", key=_k_lib)
                
                fc1, fc2 = st.columns(2)
                with fc1:
                    _cur_emit = "Sim" if r_sel.get("fatura_emitida", 0) else "Não"
                    fat_emit = st.selectbox(
                        "Fatura Emitida",
                        options=["Sim", "Não"],
                        index=0 if _cur_emit == "Sim" else 1,
                        key=f"fin_ent_fat_emit_{r_sel['venda_id']}",
                        disabled=not liberar_edicao
                    )
                with fc2:
                    _cur_num = str(r_sel.get("fatura_numero", ""))
                    fat_num = st.text_input(
                        "Número da fatura",
                        value=_cur_num,
                        key=f"fin_ent_fat_num_{r_sel['venda_id']}",
                        disabled=not liberar_edicao
                    )
                
                if st.button("Salvar Informacoes de Faturamento", type="primary", key=f"fin_ent_btn_salvar_fat_{r_sel['venda_id']}", disabled=not liberar_edicao):
                    st.session_state.fin_ent_show_fat_dialog = True
                    st.rerun()

                if st.session_state.get("fin_ent_show_fat_dialog"):
                    @st.dialog("Confirmar Alteração")
                    def confirmar_fatura_dialog():
                        st.markdown("Deseja mesmo salvar as alterações?")
                        dc1, dc2 = st.columns(2)
                        with dc1:
                            if st.button("Sim", use_container_width=True, type="primary", key="fin_ent_dlg_sim"):
                                _fat_emit_val = st.session_state.get(f"fin_ent_fat_emit_{r_sel['venda_id']}")
                                _fat_num_val = st.session_state.get(f"fin_ent_fat_num_{r_sel['venda_id']}", "").strip()
                                
                                if _fat_emit_val == "Sim" and not _fat_num_val:
                                    st.session_state.fin_ent_dlg_err = "Para salvar com Fatura Emitida = 'Sim', indique o Número da fatura."
                                elif _fat_emit_val == "Não" and _fat_num_val:
                                    st.session_state.fin_ent_dlg_err = "Não é possível informar o Número da fatura se a Fatura Emitida for 'Não'."
                                else:
                                    ok_f, msg_f = atualizar_fatura_venda(
                                        conn,
                                        int(r_sel["venda_id"]),
                                        1 if _fat_emit_val == "Sim" else 0,
                                        _fat_num_val
                                    )
                                    if ok_f:
                                        conn.commit()
                                        st.session_state.pop("fin_ent_show_fat_dialog", None)
                                        st.session_state[_k_lib] = False
                                        st.session_state.fin_ent_filt_v = _ve + 1
                                        st.session_state.fin_ent_fatura_sucesso = True
                                        st.rerun()
                                    else:
                                        st.session_state.fin_ent_dlg_err = msg_f
                        with dc2:
                            if st.button("Não", use_container_width=True, key="fin_ent_dlg_nao"):
                                st.session_state.pop("fin_ent_show_fat_dialog", None)
                                st.session_state.pop("fin_ent_dlg_err", None)
                                st.session_state[_k_lib] = False
                                st.session_state.pop(f"fin_ent_fat_emit_{r_sel['venda_id']}", None)
                                st.session_state.pop(f"fin_ent_fat_num_{r_sel['venda_id']}", None)
                                st.rerun()
                        
                        _dlg_err = st.session_state.get("fin_ent_dlg_err")
                        if _dlg_err:
                            st.error(_dlg_err)
                            
                    confirmar_fatura_dialog()
