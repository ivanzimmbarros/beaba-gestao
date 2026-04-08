"""Agendamentos — buffer, calendário semanal e estados (E09)."""

from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from src.modules.agendamento import (
    alterar_status,
    atualizar_agendamento,
    cancelar_agendamento,
    contar_por_status_periodo,
    contar_pre_venda_futuros,
    criar_agendamento,
    criar_agendamento_pre_venda,
    listar_agendamentos,
    listar_buckets_credito_cliente,
    obter_agendamento,
)
from src.modules.catalogo import euros_para_centavos, listar_itens_catalogo
from src.modules.cliente import listar_clientes_resumo
from src.modules.colaborador import listar_colaboradores_resumo
from src.ui.theme import agenda_pagamento_dot, agenda_status_style, agenda_tipo_icon


def _week_range(anchor: date) -> tuple[date, date]:
    mon = anchor - timedelta(days=anchor.weekday())
    sun = mon + timedelta(days=6)
    return mon, sun


def _render_legenda() -> None:
    st.caption(
        "**Estados (fundo):** pré-ag. · agend. · confirm. · realizado/pgto · concl. · cancel.  |  "
        "**Tipos:** ◇ sessão · 📦 pacote · ⌂ cowork · 📅 evento  |  "
        "**Pagamento (ponto):** ● pago · ● parcial/atraso · ○ em aberto"
    )


def _html_escape(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_page_agendamentos(
    *,
    render_back_and_breadcrumb,
) -> None:
    render_back_and_breadcrumb(["Home", "Agendamentos"], back_key="bea_back_agenda")
    st.markdown("### Agendamentos")
    st.caption(
        "Créditos por linha de venda (sessão avulsa, pacote, coworking, evento), "
        "ocorrências com hora início/fim, colaboradores e estados. "
        "**Pré-venda:** marca sem venda (MVP: Sessão, Coworking, Evento); fecho no **Painel de Vendas**. "
        "No cancelamento com crédito, indique se o crédito volta ao buffer."
    )
    _render_legenda()

    if "agenda_week_anchor" not in st.session_state:
        st.session_state.agenda_week_anchor = date.today()
    anchor: date = st.session_state.agenda_week_anchor
    mon, sun = _week_range(anchor)

    clientes = listar_clientes_resumo()
    colabs = listar_colaboradores_resumo()
    cat = listar_itens_catalogo()
    servico_opts = [(int(r["id"]), str(r["nome"])) for r in cat]

    st.subheader("Indicadores (semana corrente e seguinte)")
    hoje = date.today()
    w0a, w0b = _week_range(hoje)
    w1a = w0a + timedelta(days=7)
    w1b = w0b + timedelta(days=7)
    c0 = contar_por_status_periodo(w0a.isoformat(), w0b.isoformat())
    c1 = contar_por_status_periodo(w1a.isoformat(), w1b.isoformat())
    a0 = (
        c0.get("PRE_AGENDADO", 0)
        + c0.get("AGENDADO", 0)
        + c0.get("CONFIRMADO", 0)
        + c0.get("REALIZADO_PENDENTE_PGTO", 0)
    )
    a1 = (
        c1.get("PRE_AGENDADO", 0)
        + c1.get("AGENDADO", 0)
        + c1.get("CONFIRMADO", 0)
        + c1.get("REALIZADO_PENDENTE_PGTO", 0)
    )
    mcols = st.columns(4)
    with mcols[0]:
        st.metric("Esta semana — ativos (operacionais)", a0)
    with mcols[1]:
        st.metric("Próxima semana — ativos (operacionais)", a1)
    with mcols[2]:
        st.metric("Esta semana — concluídos", c0.get("CONCLUIDO", 0))
    with mcols[3]:
        st.metric("Esta semana — cancelados", c0.get("CANCELADO", 0))
    st.metric(
        "Pré-vendas futuras (ativas)",
        contar_pre_venda_futuros(hoje.isoformat()),
    )

    st.subheader("Filtros")
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        sel_cli = st.multiselect(
            "Cliente",
            options=[c[0] for c in clientes],
            format_func=lambda i: next((n for cid, n in clientes if cid == i), str(i)),
            key="ag_f_cliente",
        )
    with fc2:
        sel_srv = st.multiselect(
            "Serviço (ocorrência)",
            options=[s[0] for s in servico_opts],
            format_func=lambda i: next((n for sid, n in servico_opts if sid == i), str(i)),
            key="ag_f_servico",
        )
    with fc3:
        sel_colab_f = st.multiselect(
            "Colaborador (em alguma ocorrência)",
            options=[c[0] for c in colabs],
            format_func=lambda i: next((n for cid, n in colabs if cid == i), str(i)),
            key="ag_f_colab",
        )
    fr1, fr2 = st.columns(2)
    with fr1:
        sel_status = st.multiselect(
            "Estado",
            options=[
                "PRE_AGENDADO",
                "AGENDADO",
                "CONFIRMADO",
                "REALIZADO_PENDENTE_PGTO",
                "CONCLUIDO",
                "CANCELADO",
            ],
            default=[
                "AGENDADO",
                "CONFIRMADO",
                "REALIZADO_PENDENTE_PGTO",
                "CONCLUIDO",
            ],
            key="ag_f_status",
        )
    with fr2:
        sel_tipo = st.multiselect(
            "Tipo de origem",
            options=["sessao_avulsa", "pacote", "coworking", "evento"],
            key="ag_f_tipo",
        )
    sel_modo = st.multiselect(
        "Modo na agenda",
        options=["credito_venda", "pre_venda"],
        default=["credito_venda", "pre_venda"],
        key="ag_f_modo",
    )
    modos_f = sel_modo if len(sel_modo) < 2 else None
    fd1, fd2, fd3 = st.columns(3)
    with fd1:
        data_de = st.date_input("Data desde", value=mon, key="ag_f_de")
    with fd2:
        data_ate = st.date_input("Data até", value=sun + timedelta(days=14), key="ag_f_ate")
    with fd3:
        st.write("")
        st.write("")
        if st.button("Reset filtros de estado", key="ag_reset_st"):
            st.session_state.ag_f_status = [
                "AGENDADO",
                "CONFIRMADO",
                "REALIZADO_PENDENTE_PGTO",
                "CONCLUIDO",
            ]
            st.rerun()

    rows = listar_agendamentos(
        data_de=data_de.isoformat(),
        data_ate=data_ate.isoformat(),
        cliente_ids=sel_cli if sel_cli else None,
        servico_ids=sel_srv if sel_srv else None,
        colaborador_ids=sel_colab_f if sel_colab_f else None,
        status_list=sel_status if sel_status else None,
        tipo_origem=sel_tipo if sel_tipo else None,
        modos_origem=modos_f,
    )

    st.subheader("Buffer — créditos por agendar")
    buf_cid = st.selectbox(
        "Cliente para ver buffer",
        options=[0] + [c[0] for c in clientes],
        format_func=lambda x: "—" if x == 0 else next((n for cid, n in clientes if cid == x), str(x)),
        key="ag_buf_cliente",
    )
    if buf_cid and buf_cid > 0:
        buckets = [b for b in listar_buckets_credito_cliente(int(buf_cid)) if b["saldo"] > 0]
        if not buckets:
            st.info("Sem saldo pendente de agendamento para este cliente.")
        else:
            st.dataframe(
                {
                    "Linha": [b["rotulo"] for b in buckets],
                    "Tipo": [b["tipo_origem"] for b in buckets],
                    "Saldo": [b["saldo"] for b in buckets],
                    "Pagamento": [b["pagamento"] for b in buckets],
                    "Venda": [b["venda_id"] for b in buckets],
                },
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.caption("Escolha um cliente para listar sessões/coworking/evento/pacote com saldo.")

    st.subheader("Nova ocorrência")
    if not clientes:
        st.warning("Cadastre clientes para criar agendamentos.")
    with st.form("ag_novo", clear_on_submit=False):
        choice_i: int | None = None
        nc1, nc2 = st.columns(2)
        with nc1:
            cli_novo = st.selectbox(
                "Cliente",
                options=[c[0] for c in clientes] if clientes else [0],
                format_func=lambda i: "—" if i == 0 else next((n for cid, n in clientes if cid == i), str(i)),
                key="ag_new_cli",
                disabled=not clientes,
            )
        buckets_n: list[dict] = (
            listar_buckets_credito_cliente(int(cli_novo)) if clientes and cli_novo else []
        )
        opts_labels: list[str] = []
        opts_idx: list[tuple[int, int | None]] = []
        for b in buckets_n:
            if b["saldo"] <= 0:
                continue
            label = f"[{b['tipo_origem']}] {b['rotulo']} — saldo {b['saldo']}"
            opts_labels.append(label)
            pid = b.get("pacote_sessao_id")
            opts_idx.append((int(b["venda_item_id"]), int(pid) if pid is not None else None))
        with nc2:
            if not opts_labels:
                st.caption("Sem créditos com saldo para este cliente.")
            else:
                choice_i = st.selectbox(
                    "Crédito / linha",
                    range(len(opts_labels)),
                    format_func=lambda i: opts_labels[i],
                )
        cdt, ct1, ct2 = st.columns(3)
        with cdt:
            d_ag = st.date_input("Data", value=date.today(), key="ag_new_data")
        with ct1:
            h_i = st.text_input("Hora início (HH:MM)", value="09:00", key="ag_new_hi")
        with ct2:
            h_f = st.text_input("Hora fim (HH:MM)", value="10:00", key="ag_new_hf")
        col_sel = st.multiselect(
            "Colaboradores",
            options=[c[0] for c in colabs],
            format_func=lambda i: next((n for cid, n in colabs if cid == i), str(i)),
            key="ag_new_colabs",
        )
        obs_n = st.text_area("Observações", key="ag_new_obs")
        sub = st.form_submit_button("Criar agendamento")
        if sub:
            if not clientes or not cli_novo:
                st.error("Escolha um cliente válido.")
            elif choice_i is None or not opts_labels:
                st.error("Escolha um cliente com crédito disponível.")
            else:
                vi_id, p_sid = opts_idx[int(choice_i)]
                ok, msg = criar_agendamento(
                    vi_id,
                    p_sid,
                    d_ag.isoformat(),
                    h_i,
                    h_f,
                    [int(x) for x in col_sel],
                    obs_n,
                )
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

    st.subheader("Pré-venda (sem crédito de venda)")
    srv_pre = [
        (int(r["id"]), f"{r['nome']} ({r['natureza']})")
        for r in cat
        if str(r.get("natureza", "")) in ("Sessão", "Coworking", "Evento")
    ]
    with st.form("ag_pre_venda", clear_on_submit=False):
        pv1, pv2 = st.columns(2)
        with pv1:
            cli_pv = st.selectbox(
                "Cliente",
                options=[c[0] for c in clientes] if clientes else [0],
                format_func=lambda i: "—" if i == 0 else next((n for cid, n in clientes if cid == i), str(i)),
                key="ag_pv_cli",
                disabled=not clientes,
            )
        with pv2:
            sid_pv = st.selectbox(
                "Serviço (MVP: Sessão / Coworking / Evento)",
                options=[s[0] for s in srv_pre] if srv_pre else [0],
                format_func=lambda i: "—" if i == 0 else next((lbl for sid, lbl in srv_pre if sid == i), str(i)),
                key="ag_pv_srv",
                disabled=not srv_pre,
            )
        pv3, pv4, pv5 = st.columns(3)
        with pv3:
            d_pv = st.date_input("Data", value=date.today(), key="ag_pv_data")
        with pv4:
            hi_pv = st.text_input("Hora início", value="09:00", key="ag_pv_hi")
        with pv5:
            hf_pv = st.text_input("Hora fim", value="10:00", key="ag_pv_hf")
        col_pv = st.multiselect(
            "Colaboradores",
            options=[c[0] for c in colabs],
            format_func=lambda i: next((n for cid, n in colabs if cid == i), str(i)),
            key="ag_pv_colabs",
        )
        use_pref = st.checkbox("Congelar preço de referência (€)", value=False, key="ag_pv_usep")
        pref_eur = 0.0
        if use_pref:
            pref_eur = float(
                st.number_input("Preço referência (€)", min_value=0.0, value=40.0, step=1.0, key="ag_pv_pref")
            )
        obs_pv = st.text_area("Observações", key="ag_pv_obs")
        if st.form_submit_button("Criar pré-venda"):
            if not clientes or not cli_pv:
                st.error("Escolha um cliente.")
            elif not srv_pre or not sid_pv:
                st.error("Sem serviço elegível no catálogo.")
            elif not col_pv:
                st.error("Indique pelo menos um colaborador.")
            else:
                pr_c = euros_para_centavos(pref_eur) if use_pref else None
                ok_pv, msg_pv = criar_agendamento_pre_venda(
                    int(cli_pv),
                    int(sid_pv),
                    d_pv.isoformat(),
                    hi_pv,
                    hf_pv,
                    [int(x) for x in col_pv],
                    obs_pv,
                    preco_referencia_centavos=pr_c,
                )
                (st.success(msg_pv) if ok_pv else st.error(msg_pv))

    st.subheader("Calendário (semana)")
    cnav1, cnav2, cnav3 = st.columns([1, 2, 1])
    with cnav1:
        if st.button("← Semana anterior", key="ag_prev_w"):
            st.session_state.agenda_week_anchor = anchor - timedelta(days=7)
            st.rerun()
    with cnav2:
        st.markdown(
            f"<div style='text-align:center;font-weight:600;'>"
            f"{mon.strftime('%d/%m')} — {sun.strftime('%d/%m/%Y')}</div>",
            unsafe_allow_html=True,
        )
    with cnav3:
        if st.button("Semana seguinte →", key="ag_next_w"):
            st.session_state.agenda_week_anchor = anchor + timedelta(days=7)
            st.rerun()

    week_rows = listar_agendamentos(
        data_de=mon.isoformat(),
        data_ate=sun.isoformat(),
        cliente_ids=sel_cli if sel_cli else None,
        servico_ids=sel_srv if sel_srv else None,
        colaborador_ids=sel_colab_f if sel_colab_f else None,
        status_list=sel_status if sel_status else None,
        tipo_origem=sel_tipo if sel_tipo else None,
        modos_origem=modos_f,
    )
    by_day: dict[str, list[dict]] = {}
    for ev in week_rows:
        by_day.setdefault(ev["data_agendamento"], []).append(ev)
    for k in by_day:
        by_day[k].sort(key=lambda x: (x["hora_inicio"], x["id"]))

    dias_pt = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    cells: list[str] = []
    for i in range(7):
        d = mon + timedelta(days=i)
        ds = d.isoformat()
        label = f"{dias_pt[i]}<br><small>{d.strftime('%d/%m')}</small>"
        inner_parts: list[str] = []
        for ev in by_day.get(ds, []):
            stl = agenda_status_style(ev["status"])
            ic = agenda_tipo_icon(ev["tipo_origem"])
            pg_sym, pg_col = agenda_pagamento_dot(str(ev.get("pagamento") or ""))
            pre_badge = "🔖 " if ev.get("modo_origem") == "pre_venda" else ""
            tit = f"{pre_badge}{ic} {_html_escape(ev['servico_nome'])} · {_html_escape(ev['cliente_nome'])}"
            sub = (
                f"{_html_escape(ev['hora_inicio'])}–{_html_escape(ev['hora_fim'])} · "
                f"{_html_escape(ev['status'])} · "
                f"<span style='color:{pg_col};font-weight:700' title='Pagamento'>{pg_sym}</span>"
            )
            inner_parts.append(
                f"<div style='margin:4px 0;padding:6px 8px;border-radius:10px;"
                f"background:{stl['bg']};border:1px solid {stl['border']};font-size:0.8rem;'>"
                f"<strong>#{ev['id']}</strong> {tit}<br><span style='opacity:0.9'>{sub}</span></div>"
            )
        inner = "".join(inner_parts) if inner_parts else "<span style='opacity:0.5'>—</span>"
        cells.append(f"<td style='vertical-align:top;width:14%;padding:6px;border:1px solid rgba(0,0,0,0.08);'>{label}{inner}</td>")

    st.markdown(
        "<table style='width:100%;border-collapse:collapse;font-family:Montserrat,sans-serif;'>"
        f"<tr>{''.join(cells)}</tr></table>",
        unsafe_allow_html=True,
    )

    st.subheader("Lista filtrada e ações")
    if not rows:
        st.info("Nenhum agendamento no intervalo e filtros escolhidos.")
    else:
        st.dataframe(
            {
                "ID": [r["id"] for r in rows],
                "Data": [r["data_agendamento"] for r in rows],
                "Início": [r["hora_inicio"] for r in rows],
                "Fim": [r["hora_fim"] for r in rows],
                "Estado": [r["status"] for r in rows],
                "Modo": [r.get("modo_origem", "credito_venda") for r in rows],
                "Tipo": [r["tipo_origem"] for r in rows],
                "Cliente": [r["cliente_nome"] for r in rows],
                "Serviço": [r["servico_nome"] for r in rows],
                "Colaboradores": [", ".join(r["colaboradores_nomes"]) for r in rows],
                "Pagamento": [r["pagamento"] for r in rows],
            },
            use_container_width=True,
            hide_index=True,
        )

        def _fmt_pick(i: int) -> str:
            for x in rows:
                if x["id"] == i:
                    return f"#{i} — {x['data_agendamento']} {x['hora_inicio']} {x['cliente_nome']}"
            return str(i)

        pick = st.selectbox(
            "Id para editar / mudar estado / cancelar",
            options=[r["id"] for r in rows],
            format_func=_fmt_pick,
        )
        ag = obter_agendamento(int(pick)) if pick else None
        if ag:
            vtxt = (
                f"Venda #{ag['venda_id']}"
                if ag.get("venda_id") is not None
                else "Sem venda (pré-venda)"
            )
            st.caption(
                f"{vtxt} · {ag['pagamento']} · "
                f"Cancel.devolve buffer: {ag['devolver_ao_buffer'] if ag['status']=='CANCELADO' else '—'}"
            )
            if ag.get("modo_origem") == "pre_venda" and ag["status"] in (
                "AGENDADO",
                "CONFIRMADO",
                "PRE_AGENDADO",
            ):
                if st.button(
                    "Fechar pré-venda no Painel de Vendas",
                    key="ag_btn_fechar_pv",
                ):
                    st.session_state.venda_fechar_agendamento_id = int(pick)
                    st.session_state.venda_cliente_id = int(ag["cliente_id"])
                    st.session_state.page = "vendas"
                    st.rerun()
            if (
                ag.get("modo_origem") == "credito_venda"
                and ag.get("venda_id")
                and ag["status"] in ("AGENDADO", "CONFIRMADO", "CONCLUIDO")
            ):
                if st.button(
                    "Nova venda nesta visita",
                    key="ag_btn_nv_visita",
                ):
                    st.session_state.venda_agendamento_contexto_id = int(pick)
                    st.session_state.venda_cliente_id = int(ag["cliente_id"])
                    st.session_state.venda_fechar_agendamento_id = None
                    st.session_state.page = "vendas"
                    st.rerun()
            with st.expander("Editar data, horas, colaboradores, observações"):
                e1, e2, e3 = st.columns(3)
                with e1:
                    nd = st.date_input("Nova data", value=date.fromisoformat(ag["data_agendamento"]), key="ag_ed_d")
                with e2:
                    nhi = st.text_input("Hora início", value=ag["hora_inicio"], key="ag_ed_hi")
                with e3:
                    nhf = st.text_input("Hora fim", value=ag["hora_fim"], key="ag_ed_hf")
                ecs = st.multiselect(
                    "Colaboradores",
                    default=ag["colaborador_ids"],
                    options=[c[0] for c in colabs],
                    format_func=lambda i: next((n for cid, n in colabs if cid == i), str(i)),
                    key="ag_ed_colab",
                )
                eo = st.text_area("Observações", value=ag["observacoes"], key="ag_ed_obs")
                if st.button("Guardar edição", key="ag_ed_save"):
                    ok, msg = atualizar_agendamento(
                        int(pick),
                        data_agendamento=nd.isoformat(),
                        hora_inicio=nhi,
                        hora_fim=nhf,
                        colaborador_ids=[int(x) for x in ecs],
                        observacoes=eo,
                    )
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

            ac1, ac2, ac3, ac4 = st.columns(4)
            with ac1:
                if st.button("→ Confirmado", key="ag_st_conf"):
                    if ag["status"] == "AGENDADO":
                        ok, msg = alterar_status(int(pick), "CONFIRMADO")
                        (st.success(msg) if ok else st.error(msg))
                        if ok:
                            st.rerun()
                    else:
                        st.warning("Só disponível em AGENDADO.")
            with ac2:
                if st.button("→ Realizado (pgto pendente)", key="ag_st_rp"):
                    if ag["status"] in ("AGENDADO", "CONFIRMADO"):
                        ok, msg = alterar_status(int(pick), "REALIZADO_PENDENTE_PGTO")
                        (st.success(msg) if ok else st.error(msg))
                        if ok:
                            st.rerun()
                    else:
                        st.warning("Só em AGENDADO ou CONFIRMADO.")
            with ac3:
                if st.button("→ Concluído", key="ag_st_done"):
                    if ag["status"] in (
                        "AGENDADO",
                        "CONFIRMADO",
                        "REALIZADO_PENDENTE_PGTO",
                    ):
                        ok, msg = alterar_status(int(pick), "CONCLUIDO")
                        (st.success(msg) if ok else st.error(msg))
                        if ok:
                            st.rerun()
                    else:
                        st.warning("Indisponível neste estado.")
            with ac4:
                dev = st.checkbox(
                    "Devolver crédito ao buffer ao cancelar",
                    value=True,
                    key="ag_can_dev",
                    disabled=ag.get("modo_origem") == "pre_venda",
                )
                cred_loja = st.checkbox(
                    "Converter valor sugerido em saldo de loja",
                    value=False,
                    key="ag_can_cred",
                )
                if ag.get("modo_origem") == "pre_venda":
                    st.caption("Pré-venda: sem crédito em buffer.")
                if st.button("Cancelar ocorrência", key="ag_can_btn"):
                    if ag["status"] in ("CONCLUIDO", "CANCELADO"):
                        st.error("Estado não permite cancelamento.")
                    else:
                        ok, msg = cancelar_agendamento(
                            int(pick),
                            devolver_ao_buffer=dev,
                            converter_valor_pago_em_credito_loja=cred_loja,
                        )
                        (st.success(msg) if ok else st.error(msg))
                        if ok:
                            st.rerun()
