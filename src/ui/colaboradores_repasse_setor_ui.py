"""E24 — Secção Streamlit «5. Relatórios globais de repasse por colaborador»."""

from __future__ import annotations

from datetime import date, datetime

import pandas as pd
import streamlit as st

from src.database.connection import get_connection
from src.modules.colaboradores_relatorio import (
    MODOS_REPASSE_LEGIVEL_PT,
    ModoDimensaoRepasse,
    agregar_metricas_repasse_linhas,
    formato_euro_centavos_pt,
    listar_colaboradores_opcoes_relatorio,
    listar_especialidades_opcoes_relatorio,
    listar_linhas_relatorio_repasse_global,
    listar_servicos_opcoes_relatorio,
    linhas_para_grid_pdf,
)
from src.modules.colaboradores_relatorio_pdf import montar_pdf_relatorio_repasse_landscape

_MODO_SEQUENCE: tuple[ModoDimensaoRepasse, ModoDimensaoRepasse, ModoDimensaoRepasse] = (
    "especialidade",
    "servico",
    "colaborador",
)

def render_setor4_relatorio_repasse_admin(*, fk: str) -> None:
    perfil_raw = str(st.session_state.get("auth_perfil") or "admin").strip().lower()
    if perfil_raw != "admin":
        return

    st.markdown(
        '<div class="bea-col-rel-repasse-flag" data-testid="bea-col-rel-repasse-flag"'
        ' style="display:none" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="bea-cv-cag-gap" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="bea-col-setor-rel-titulo" data-testid="bea-col-setor-rel-titulo">'
        "<strong>5. Relatórios globais de repasse por colaborador</strong>"
        "</div>",
        unsafe_allow_html=True,
    )

    modo_labels_pt = tuple(MODOS_REPASSE_LEGIVEL_PT[k] for k in _MODO_SEQUENCE)
    modo_label_to_key: dict[str, ModoDimensaoRepasse] = {
        MODOS_REPASSE_LEGIVEL_PT[k]: k for k in _MODO_SEQUENCE
    }

    conn = get_connection()
    if not conn:
        st.error("❌ Ligação BD indisponível.")
        return

    especialidades_opc = listar_especialidades_opcoes_relatorio(conn)
    serv_opc = listar_servicos_opcoes_relatorio(conn)
    colab_opc = listar_colaboradores_opcoes_relatorio(conn)
    colab_nome_map = dict(colab_opc)
    srv_opc_ids = [sid for sid, _ in serv_opc]

    dc1, dc2 = st.columns(2)
    with dc1:
        d_ini = st.date_input(
            "Data início (período)",
            key=f"{fk}_rep_d_ini",
            format="DD/MM/YYYY",
        )
    with dc2:
        d_fim = st.date_input(
            "Data fim (período)",
            key=f"{fk}_rep_d_fim",
            format="DD/MM/YYYY",
        )

    modo_lbl = st.selectbox(
        "Dimensão de filtro exclusiva para o relatório",
        modo_labels_pt,
        key=f"{fk}_rep_dim",
        help="Escolha exatamente um modo antes de usar o multiselect.",
    )
    modo_k = modo_label_to_key[modo_lbl]

    sel_esps = None
    sel_srv_ids = None
    sel_cids = None

    if modo_k == "especialidade":
        sel_txt = st.multiselect(
            "Especialidades seleccionadas",
            options=especialidades_opc,
            key=f"{fk}_rep_esps_ms",
            placeholder="Escolha uma ou várias especialidades…",
        )
        sel_esps = list(sel_txt)
    elif modo_k == "servico":
        sel_srv_ids_ui = st.multiselect(
            "Serviços seleccionados",
            options=srv_opc_ids,
            format_func=lambda sid: next((n for s, n in serv_opc if s == sid), str(sid)),
            key=f"{fk}_rep_srv_ms",
            placeholder="Escolha um ou vários serviços…",
        )
        sel_srv_ids = [int(x) for x in sel_srv_ids_ui]
    else:
        sel_c_ui = st.multiselect(
            "Colaboradores seleccionados",
            options=[cid for cid, _ in colab_opc],
            format_func=lambda cid: colab_nome_map.get(int(cid), str(cid)),
            key=f"{fk}_rep_col_ms",
            placeholder="Escolha um ou vários colaboradores…",
        )
        sel_cids = [int(x) for x in sel_c_ui]

    if st.button(
        "Gerar relatório de repasses",
        key=f"{fk}_rep_bt_gerar",
        width="stretch",
        type="primary",
    ):
        try:
            rows = listar_linhas_relatorio_repasse_global(
                conn,
                data_ini=d_ini,
                data_fim=d_fim,
                modo=modo_k,
                especialidades_escolhidas=sel_esps,
                servico_ids=sel_srv_ids,
                colaborador_ids=sel_cids,
            )
        except ValueError as err:
            st.warning(str(err))
            st.session_state.pop(f"{fk}_rep_saved_rows", None)
            st.session_state.pop(f"{fk}_rep_meta", None)
        else:
            if not rows:
                st.info("Não existem informações de repasse para as opções seleccionadas.")
                st.session_state.pop(f"{fk}_rep_saved_rows", None)
                st.session_state.pop(f"{fk}_rep_meta", None)
            else:
                st.session_state[f"{fk}_rep_saved_rows"] = list(rows)
                st.session_state[f"{fk}_rep_meta"] = {
                    "d_ini_iso": d_ini.isoformat(),
                    "d_fim_iso": d_fim.isoformat(),
                    "modo": modo_k,
                    "sel_esps": list(sel_esps or []),
                    "sel_srv_ids": list(sel_srv_ids or []),
                    "sel_cids": list(sel_cids or []),
                }

    saved_obj = st.session_state.get(f"{fk}_rep_saved_rows")
    if not saved_obj:
        return

    rows = saved_obj
    meta = st.session_state.get(f"{fk}_rep_meta") or {}
    dm = meta.get("d_ini_iso")
    fm = meta.get("d_fim_iso")
    d_ini_eff = (
        datetime.strptime(dm, "%Y-%m-%d").date()
        if isinstance(dm, str) and len(dm) >= 10
        else date.fromisoformat(d_ini.isoformat())
    )
    d_fim_eff = (
        datetime.strptime(fm, "%Y-%m-%d").date()
        if isinstance(fm, str) and len(fm) >= 10
        else date.fromisoformat(d_fim.isoformat())
    )
    modo_saved: ModoDimensaoRepasse = modo_k
    mr_raw = meta.get("modo")
    if mr_raw == "especialidade":
        modo_saved = "especialidade"
    elif mr_raw == "servico":
        modo_saved = "servico"
    elif mr_raw == "colaborador":
        modo_saved = "colaborador"
    modo_k_eff = modo_saved

    sel_esps_eff = meta.get("sel_esps") if modo_k_eff == "especialidade" else None
    sel_srv_eff = meta.get("sel_srv_ids") if modo_k_eff == "servico" else None
    sel_cols_eff = meta.get("sel_cids") if modo_k_eff == "colaborador" else None

    st.success(f"Total de Registros de Atendimento Listados: {len(rows)}")

    ordenado_cols = (
        "Colaborador",
        "Quando",
        "Área / Especialidade",
        "Serviço",
        "Cliente",
        "Repasse pactuado (%)",
        "Valor atendimento (EUR)",
        "Repasse (EUR)",
        "Estado pagamento repasse",
    )
    dados: list[dict[str, object]] = []
    for r in rows:
        dados.append(
            {
                "Colaborador": r.get("colaborador_nome") or "",
                "Quando": r.get("quando_display_pt_lisboa") or "",
                "Área / Especialidade": r.get("especialidade_nome") or "",
                "Serviço": r.get("servico_nome") or "",
                "Cliente": r.get("cliente_nome") or "",
                "Repasse pactuado (%)": r.get("percentual_repr_pt") or "—",
                "Valor atendimento (EUR)": formato_euro_centavos_pt(r.get("valor_base_centavos")),
                "Repasse (EUR)": formato_euro_centavos_pt(r.get("valor_repasse_centavos")),
                "Estado pagamento repasse": r.get("estado_pago_label_pt") or "",
            }
        )
    df = pd.DataFrame(dados)[list(ordenado_cols)]
    st.markdown("##### Tabela de detalhes", unsafe_allow_html=True)
    st.dataframe(df, use_container_width=True, hide_index=True)

    met = agregar_metricas_repasse_linhas(rows)
    gb = met["global"]
    st.markdown(
        "##### Resumo Quadro de Repasses dos Atendimentos Selecionados",
        unsafe_allow_html=True,
    )
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric("Total de Atendimentos Listados", f"{gb['n_linhas']}")
    with kpi2:
        st.metric("Total repasse", formato_euro_centavos_pt(gb["repasse_cent"]))
    with kpi3:
        st.metric("Pago ao colaborador", formato_euro_centavos_pt(gb["repasse_pago_cent"]))
    with kpi4:
        st.metric("Pendente de pagamento", formato_euro_centavos_pt(gb["repasse_pend_cent"]))

    pdf_rows = linhas_para_grid_pdf(rows)

    filtros_txt = [
        (
            "Periodo Selecionado: "
            f"{d_ini_eff.strftime('%d/%m/%Y')} — {d_fim_eff.strftime('%d/%m/%Y')}"
        ),
        f"Filtro Selecionado: {MODOS_REPASSE_LEGIVEL_PT[modo_k_eff]}",
    ]
    if modo_k_eff == "especialidade" and isinstance(sel_esps_eff, list):
        filtros_txt.append(
            "Lista de Especialidades selecionadas: " + "; ".join(str(x) for x in sel_esps_eff)
        )
    elif modo_k_eff == "servico" and isinstance(sel_srv_eff, list):
        nomes_srv: list[str] = []
        for sid in sel_srv_eff:
            try:
                sx = int(sid)
                nom = next((n for s, n in serv_opc if s == sx), str(sid))
                nomes_srv.append(f"{sx} ({nom})")
            except (TypeError, ValueError):
                nomes_srv.append(str(sid))
        filtros_txt.append("Lista de Serviços selecionados: " + "; ".join(nomes_srv))
    elif modo_k_eff == "colaborador" and isinstance(sel_cols_eff, list):
        nomes_co = []
        for cid in sel_cols_eff:
            try:
                ix = int(cid)
                nom = colab_nome_map.get(ix, str(ix))
                nomes_co.append(str(nom))
            except (TypeError, ValueError):
                nomes_co.append(str(cid))
        filtros_txt.append("Lista de Colaboradores selecionados: " + "; ".join(nomes_co))

    resumo_linhas = [
        f"Quantidade de Atendimentos listados: {gb['n_linhas']}",
        "Receita Total dos Atendimentos Realizados: "
        f"{formato_euro_centavos_pt(gb['base_cent'])}",
        (
            "Valor total de Repasse: "
            f"{formato_euro_centavos_pt(gb['repasse_cent'])} "
            f"— Pgto Realizado: {formato_euro_centavos_pt(gb['repasse_pago_cent'])} | "
            f"Pgto Pendente: {formato_euro_centavos_pt(gb['repasse_pend_cent'])}"
        ),
    ]
    for esp, buck in met["por_especialidade"].items():
        resumo_linhas.append(
            f"Resumo por Especialidade: {esp} — Total de Atendimentos: {buck['n_linhas']}; "
            f"Valor Previsto de Repasse: {formato_euro_centavos_pt(buck['repasse_cent'])} "
            f"(Total Repasses Pago {formato_euro_centavos_pt(buck['repasse_pago_cent'])} / "
            f"Total Repasses Pendente pgto: {formato_euro_centavos_pt(buck['repasse_pend_cent'])})"
        )
    for srv, buck in met["por_servico"].items():
        resumo_linhas.append(
            f"Resumo por Serviço: {srv} — Total de Atendimentos: {buck['n_linhas']}; "
            f"Valor Previsto de Repasse {formato_euro_centavos_pt(buck['repasse_cent'])} "
            f"(Total Repasse Pago / Total Repasses Pendente pgto: "
            f"{formato_euro_centavos_pt(buck['repasse_pago_cent'])} / "
            f"{formato_euro_centavos_pt(buck['repasse_pend_cent'])})"
        )

    try:
        nome_pdf = (
            "Relatorio de Calculo de Atendimentos e Repasses BeaBa - "
            + datetime.now().strftime("%Y%m%d_%H%M%S")
            + ".pdf"
        )
        pdf_bytes = montar_pdf_relatorio_repasse_landscape(
            titulo="Relatório Consolidado de Cálculo de Repasses - BeaBá",
            meta_filtros_texto=filtros_txt,
            resumo_texto=resumo_linhas,
            linhas_tabela=pdf_rows,
        )
        st.download_button(
            label="Descarregar Relatorio",
            data=pdf_bytes,
            file_name=nome_pdf,
            mime="application/pdf",
            key=f"{fk}_btn_pdf_repasse",
            type="secondary",
        )
    except RuntimeError as e_font:
        st.error(f"PDF indisponível neste hospedeiro (fontes do SO): {e_font}")

