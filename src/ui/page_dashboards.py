"""Dashboards e relatórios — UI Streamlit (E08 + E19 DW)."""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.database.connection import get_connection
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


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _db_path() -> Path:
    return _repo_root() / "data" / "beaba_gestao.db"


def _dw_table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (name,),
    ).fetchone()
    return row is not None


def _run_etl_subprocess() -> tuple[int, str]:
    root = _repo_root()
    script = root / "scripts" / "etl_analytics.py"
    dbp = _db_path()
    if not script.is_file():
        return 1, f"Script em falta: {script}"
    if not dbp.is_file():
        return 1, f"Base em falta: {dbp}"
    proc = subprocess.run(
        [sys.executable, str(script), "--db", str(dbp)],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=120,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip() or "(sem saída)"


def _render_dw_analytics_block() -> None:
    """
    E19 — métricas só a partir de tabelas `dw_*` (sem cálculos de cohort/LTV na UI).
    """
    st.subheader("Analytics — Data Warehouse (E19)")
    st.caption(
        "Fonte: apenas tabelas **`dw_*`** geridas por `scripts/etl_analytics.py`. "
        "LTV Real respeita o ledger E18 (exclui vendas **pendentes** no ETL)."
    )

    c_run, _ = st.columns([1, 3])
    with c_run:
        if st.button("Actualizar Data Warehouse (ETL)", key="bea_dw_refresh_etl"):
            with st.spinner("A executar ETL…"):
                code, msg = _run_etl_subprocess()
            if code == 0:
                st.success("ETL concluído com sucesso.")
            else:
                st.error(f"ETL terminou com código {code}.")
            with st.expander("Saída do ETL", expanded=code != 0):
                st.code(msg, language="text")
            st.rerun()

    conn = get_connection()
    if not conn:
        st.error("Sem ligação à base de dados.")
        return
    try:
        if not _dw_table_exists(conn, "dw_fact_agendamento") or not _dw_table_exists(
            conn, "dw_cliente_kpi"
        ):
            st.warning(
                "Tabelas **`dw_*`** ainda não existem. Use o botão **Actualizar Data Warehouse (ETL)**."
            )
            return

        row = conn.execute(
            """
            SELECT
              (SELECT COALESCE(SUM(carga_horaria_h), 0)
               FROM dw_fact_agendamento
               WHERE is_cancelado = 0 AND carga_horaria_h IS NOT NULL) AS ocupacao_h,
              (SELECT COALESCE(SUM(receita_ltv_real_total_centavos), 0)
               FROM dw_cliente_kpi) AS ltv_real_c
            """
        ).fetchone()
        ocup_h = float(row[0] or 0)
        ltv_c = int(row[1] or 0)

        m1, m2 = st.columns(2)
        with m1:
            st.metric(
                "Ocupação agendada (horas)",
                f"{ocup_h:.2f} h",
                help="Soma de `carga_horaria_h` em `dw_fact_agendamento` (não cancelados).",
            )
        with m2:
            st.metric(
                "LTV Real acumulado",
                f"{ltv_c / 100:.2f} €",
                help="Soma de `receita_ltv_real_total_centavos` em `dw_cliente_kpi` (ETL / ledger E18).",
            )

        st.markdown("##### Risco de churn — maior intervalo médio entre visitas")
        st.caption(
            "Ordenação: maior `media_dias_entre_visitas` primeiro (clientes com mais dias entre visitas consecutivas). "
            "Apenas dados de `dw_cliente_kpi`."
        )
        df_kpi = pd.read_sql_query(
            """
            SELECT *
            FROM dw_cliente_kpi
            ORDER BY
              (CASE WHEN media_dias_entre_visitas IS NULL THEN 1 ELSE 0 END),
              media_dias_entre_visitas DESC
            """,
            conn,
        )
        if df_kpi.empty:
            st.info("Sem linhas em `dw_cliente_kpi`.")
        else:
            display = df_kpi.copy()
            if "receita_ltv_real_total_centavos" in display.columns:
                display["ltv_real_€"] = (
                    display["receita_ltv_real_total_centavos"].fillna(0).astype(int) / 100.0
                )
            if "ticket_medio_ltv_real_centavos" in display.columns:
                display["ticket_medio_€"] = display["ticket_medio_ltv_real_centavos"].apply(
                    lambda x: (int(x) / 100.0) if pd.notna(x) and x is not None else None
                )
            st.dataframe(display, hide_index=True, width="stretch")

    except Exception as e:
        st.error(f"Erro ao ler `dw_*`: {e}")
    finally:
        conn.close()


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

    _render_dw_analytics_block()

    st.markdown("---")
    st.markdown("#### Relatórios operacionais (E08)")
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
        st.plotly_chart(_bea_plotly_layout(fig_l), width="stretch")
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
            st.plotly_chart(_bea_plotly_layout(fig_b), width="stretch")
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
            st.plotly_chart(_bea_plotly_layout(fig_p), width="stretch")
        else:
            st.caption("Sem dados.")

    st.markdown("---")
    st.subheader("Relatório tabular")
    tab = tabela_agregada(filt, dim_gb)
    if tab:
        st.dataframe(pd.DataFrame(tab), hide_index=True, width="stretch")
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
