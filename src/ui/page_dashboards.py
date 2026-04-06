"""Dashboards e relatórios — UI Streamlit (E08)."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.modules.relatorios import (
    DimensaoGroupBy,
    FiltrosDashboard,
    GranularidadeTemporal,
    kpis,
    listar_opcoes_filtro_clientes,
    listar_opcoes_filtro_colaboradores,
    listar_opcoes_filtro_servicos,
    pareto_dimensao,
    serie_receita_temporal,
    tabela_agregada,
    top_n_dimensao,
)
from src.ui.theme import ANALYTICS_COLORS, COLORS


def _bea_plotly_layout(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        paper_bgcolor=COLORS["bg"],
        plot_bgcolor="#FAFAFA",
        font=dict(family="Montserrat, sans-serif", color=COLORS["text"], size=12),
        margin=dict(l=48, r=24, t=48, b=48),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(gridcolor="rgba(0,0,0,0.06)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(0,0,0,0.06)", zeroline=False)
    return fig


def render_page_dashboards(
    *,
    render_back_and_breadcrumb,
) -> None:
    render_back_and_breadcrumb(["Home", "Dashboards e Relatórios"], back_key="bea_back_dash")
    st.markdown("### Dashboards e relatórios")
    st.caption(
        "**Fase A:** receita com base em vendas registadas; «margem / lucro» = receita (sem custos). "
        "Desconto global na venda pode fazer divergir soma das linhas do total do cabeçalho — ambos os valores são mostrados."
    )

    hoje = date.today()
    c1, c2, c3 = st.columns(3)
    with c1:
        d0 = st.date_input("Período — início", value=hoje - timedelta(days=90), key="dash_d0")
    with c2:
        d1 = st.date_input("Período — fim", value=hoje, key="dash_d1")
    with c3:
        top_n = st.slider("Top N (ranking / Pareto)", min_value=5, max_value=25, value=10, key="dash_topn")

    st.subheader("Filtros")
    fc = listar_opcoes_filtro_clientes()
    fs = listar_opcoes_filtro_servicos()
    fcol = listar_opcoes_filtro_colaboradores()
    f1, f2 = st.columns(2)
    with f1:
        sel_cli = st.multiselect(
            "Cliente(s)",
            options=[x[0] for x in fc],
            format_func=lambda i: next(l for v, l in fc if v == i),
            default=[],
            key="dash_f_cli",
        )
        sel_svc = st.multiselect(
            "Serviço(s) (catálogo)",
            options=[x[0] for x in fs],
            format_func=lambda i: next(l for v, l in fs if v == i),
            default=[],
            key="dash_f_svc",
        )
    with f2:
        sel_colab = st.multiselect(
            "Colaborador(es) (linha de venda)",
            options=[x[0] for x in fcol],
            format_func=lambda i: next(l for v, l in fcol if v == i),
            default=[],
            key="dash_f_col",
        )
        apenas_prod = st.checkbox("Apenas natureza **Produto** no catálogo", key="dash_f_prod")

    st.subheader("Agrupamento (tabela e ranking)")
    gb_labels: dict[str, DimensaoGroupBy] = {
        "Serviço (nome na venda)": "servico",
        "Cliente": "cliente",
        "Colaborador": "colaborador",
        "Natureza (catálogo)": "natureza",
        "Dia (data venda)": "dia",
        "Mês (AAAA-MM)": "mes",
    }
    group_pick = st.selectbox("Group by", list(gb_labels.keys()), key="dash_gb")
    dim_gb = gb_labels[group_pick]

    gran: GranularidadeTemporal = st.radio(
        "Granularidade série temporal",
        ["dia", "mes"],
        horizontal=True,
        format_func=lambda x: "Dia" if x == "dia" else "Mês",
        key="dash_gran",
    )

    if d0 > d1:
        st.error("A data de início deve ser anterior ou igual à data de fim.")
        return

    filt = FiltrosDashboard(
        data_inicio=d0.isoformat(),
        data_fim=d1.isoformat(),
        cliente_ids=list(sel_cli),
        servico_ids=list(sel_svc),
        colaborador_ids=list(sel_colab),
        apenas_natureza_produto=apenas_prod,
    )

    k = kpis(filt)
    if not k:
        st.error("Não foi possível ler a base de dados.")
        return

    st.markdown("---")
    st.subheader("Totalizações")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric(
            "Receita (linhas)",
            f"{k['receita_itens_centavos'] / 100:.2f} €",
            help="Soma dos totais por linha (após desconto de linha). Fase A = proxy de «margem» sem custos.",
        )
    with m2:
        st.metric(
            "Receita (vendas)",
            f"{k['receita_cabecalhos_centavos'] / 100:.2f} €",
            help="Soma dos totais finais por venda (inclui desconto global no cabeçalho).",
        )
    with m3:
        st.metric("Nº vendas", str(k["n_vendas"]))
    with m4:
        st.metric(
            "Ticket médio (venda)",
            f"{k['ticket_medio_centavos'] / 100:.2f} €",
        )

    m5, m6 = st.columns(2)
    with m5:
        st.metric("Linhas de item", str(k["n_linhas"]))
    with m6:
        st.metric("Quantidade (unidades/sessões)", str(k["quantidade_total"]))

    st.markdown("---")
    st.subheader("Evolução temporal (receita por linha)")
    ser = serie_receita_temporal(filt, gran)
    if ser:
        df_s = pd.DataFrame(ser, columns=["Período", "Receita (€)"])
        df_s["Receita (€)"] = df_s["Receita (€)"] / 100.0
        fig_l = go.Figure()
        fig_l.add_trace(
            go.Scatter(
                x=df_s["Período"],
                y=df_s["Receita (€)"],
                mode="lines+markers",
                name="Receita",
                line=dict(color=ANALYTICS_COLORS[0], width=2),
                marker=dict(size=8, color=ANALYTICS_COLORS[1], line=dict(width=1, color=COLORS["text"])),
            )
        )
        fig_l.update_layout(title="Receita agregada no período", xaxis_title="Período", yaxis_title="€")
        st.plotly_chart(_bea_plotly_layout(fig_l), use_container_width=True)
    else:
        st.info("Sem dados no período e filtros selecionados.")

    st.markdown("---")
    c_left, c_right = st.columns(2)
    with c_left:
        st.subheader(f"Top {top_n} — {group_pick}")
        top = top_n_dimensao(filt, dim_gb, top_n)
        if top:
            df_t = pd.DataFrame(
                [(a, b / 100.0, c) for a, b, c in top],
                columns=["Dimensão", "Receita (€)", "Qtd"],
            )
            colors_bar = (ANALYTICS_COLORS * ((len(df_t) // len(ANALYTICS_COLORS)) + 1))[: len(df_t)]
            fig_b = go.Figure(
                go.Bar(
                    x=df_t["Receita (€)"],
                    y=df_t["Dimensão"],
                    orientation="h",
                    marker=dict(color=colors_bar, line=dict(width=0)),
                    text=df_t["Receita (€)"].map(lambda x: f"{x:.2f} €"),
                    textposition="outside",
                )
            )
            fig_b.update_layout(title="Ranking por receita (linhas)", yaxis=dict(autorange="reversed"))
            st.plotly_chart(_bea_plotly_layout(fig_b), use_container_width=True)
        else:
            st.caption("Sem dados.")

    with c_right:
        st.subheader("Pareto (% cumulativo)")
        par = pareto_dimensao(filt, dim_gb, limite_barras=max(10, top_n))
        if par:
            df_p = pd.DataFrame(par, columns=["Dimensão", "Receita (c)", "Cum %"])
            df_p["Receita (€)"] = df_p["Receita (c)"] / 100.0
            fig_p = go.Figure()
            fig_p.add_trace(
                go.Bar(
                    x=df_p["Dimensão"],
                    y=df_p["Receita (€)"],
                    name="Receita",
                    marker_color=ANALYTICS_COLORS[2],
                )
            )
            fig_p.add_trace(
                go.Scatter(
                    x=df_p["Dimensão"],
                    y=df_p["Cum %"],
                    name="% acumulado",
                    yaxis="y2",
                    mode="lines+markers",
                    line=dict(color=ANALYTICS_COLORS[0], width=2),
                    marker=dict(size=6),
                )
            )
            fig_p.update_layout(
                title="Concentração (sobre categorias exibidas)",
                yaxis=dict(title="Receita (€)"),
                yaxis2=dict(title="% acumulado", overlaying="y", side="right", range=[0, 105]),
            )
            fig_p.update_xaxes(tickangle=-28)
            st.plotly_chart(_bea_plotly_layout(fig_p), use_container_width=True)
        else:
            st.caption("Sem dados.")

    st.markdown("---")
    st.subheader("Relatório tabular")
    tab = tabela_agregada(filt, dim_gb)
    if tab:
        st.dataframe(pd.DataFrame(tab), use_container_width=True, hide_index=True)
        csv = pd.DataFrame(tab).to_csv(index=False).encode("utf-8")
        st.download_button(
            "Descarregar CSV",
            csv,
            file_name="relatorio_beaba.csv",
            mime="text/csv",
            key="dash_dl",
        )
    else:
        st.caption("Sem linhas para exportar.")
