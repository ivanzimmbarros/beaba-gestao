"""Setor «Disponibilidade e calendário operacional» na página Colaboradores (ilha + sub-expanderes)."""

from __future__ import annotations

import html
from calendar import monthcalendar
from datetime import date, timedelta

import streamlit as st

from src.modules.colaborador import (
    MAPA_EQUI_ESP_SEM_LABEL,
    listar_colaboradores_mapa_equipa,
    listar_colaboradores_resumo,
    listar_naturezas_servicos_mapa_equipa,
    listar_servicos_para_mapa_equipa,
    resolver_conjunto_servicos_mapa_equipa,
)
from src.modules.colaborador_disponibilidade import (
    adicionar_regra,
    agregar_slots_calendario_mestre,
    confirmar_plano_publicado,
    criar_ou_atualizar_rascunho,
    listar_alertas_confirmados,
    listar_regras_plano,
    obter_rascunho_aberto,
    remover_regra,
)

_DIAS_SEMANA_OPTS = [
    ("Segunda", 0),
    ("Terça", 1),
    ("Quarta", 2),
    ("Quinta", 3),
    ("Sexta", 4),
    ("Sábado", 5),
    ("Domingo", 6),
]
_COR_SLOT = (
    "rgba(118, 148, 125, 0.22)",
    "rgba(212, 163, 115, 0.28)",
    "rgba(100, 116, 139, 0.2)",
    "rgba(167, 139, 250, 0.25)",
    "rgba(45, 51, 47, 0.12)",
)
_COR_BORDER = ("#76947D", "#D4A373", "#64748B", "#8B5CF6", "#2D332F")


def _disp_mapa_especialidades_opts(rows: list[tuple[int, str, str, str]]) -> list[str]:
    nomes = sorted({str(r[3]).strip() for r in rows if str(r[3]).strip()})
    out = list(nomes)
    if any(not str(r[3]).strip() for r in rows):
        out.append(MAPA_EQUI_ESP_SEM_LABEL)
    return out


def _disp_mapa_filtra_rows_por_especialidades(
    rows: list[tuple[int, str, str, str]], esp_sel: list[str]
) -> list[tuple[int, str, str, str]]:
    if not esp_sel:
        return []
    eset = {str(x) for x in esp_sel}
    sem = MAPA_EQUI_ESP_SEM_LABEL in eset
    reals = [e for e in eset if e != MAPA_EQUI_ESP_SEM_LABEL]
    out: list[tuple[int, str, str, str]] = []
    for r in rows:
        ep = str(r[3] or "").strip()
        ok = False
        if sem and not ep:
            ok = True
        if ep and ep in reals:
            ok = True
        if ok:
            out.append(r)
    return out


def _week_mon_sun(anchor: date) -> tuple[date, date]:
    mon = anchor - timedelta(days=int(anchor.weekday()))
    sun = mon + timedelta(days=6)
    return mon, sun


def _month_bounds(ref: date) -> tuple[date, date]:
    first = date(ref.year, ref.month, 1)
    if ref.month == 12:
        last = date(ref.year, 12, 31)
    else:
        nxt = date(ref.year, ref.month + 1, 1)
        last = nxt - timedelta(days=1)
    return first, last


def _shift_month(d: date, delta: int) -> date:
    y, m = d.year, d.month + delta
    while m < 1:
        m += 12
        y -= 1
    while m > 12:
        m -= 12
        y += 1
    return date(y, m, 1)


def _week_cal_html(*, mon: date, by_day: dict[str, list[dict[str, object]]]) -> str:
    dias_pt = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    cells: list[str] = []
    for i in range(7):
        d = mon + timedelta(days=i)
        ds = d.isoformat()
        label = f"{dias_pt[i]}<br><small>{d.strftime('%d/%m')}</small>"
        parts: list[str] = []
        for bl in by_day.get(ds, []):
            nome = html.escape(str(bl["nome"]))
            hi = html.escape(str(bl["hora_inicio"]))
            hf = html.escape(str(bl["hora_fim"]))
            esp = html.escape(str(bl["especialidades_txt"])[:120])
            ci = int(bl.get("cor_idx") or 0) % len(_COR_SLOT)
            bg = _COR_SLOT[ci]
            bd = _COR_BORDER[ci]
            parts.append(
                f"<div style='margin:4px 0;padding:6px 8px;border-radius:10px;"
                f"background:{bg};border:1px solid {bd};font-size:0.78rem;font-family:Montserrat,sans-serif;'>"
                f"<strong>●</strong> {nome}<br><span style='opacity:0.95'>{hi}–{hf}</span><br>"
                f"<small style='opacity:0.85'>{esp}</small></div>"
            )
        inner = "".join(parts) if parts else "<span style='opacity:0.5'>—</span>"
        cells.append(
            "<td style='vertical-align:top;width:14%;padding:6px;border:1px solid rgba(0,0,0,0.08);'>"
            f"{label}{inner}</td>"
        )
    return (
        "<table style='width:100%;border-collapse:collapse;font-family:Montserrat,sans-serif;'>"
        "<tr>" + "".join(cells) + "</tr></table>"
    )


def _month_cal_html(*, ref: date, by_day: dict[str, list[dict[str, object]]]) -> str:
    y, m = ref.year, ref.month
    weeks = monthcalendar(y, m)
    dias_cab = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    head = "".join(
        f"<th style='padding:4px;font-size:0.75rem;color:#64748B;border-bottom:1px solid #e2e8f0;'>{c}</th>"
        for c in dias_cab
    )
    body_rows: list[str] = []
    for wk in weeks:
        tds: list[str] = []
        for day in wk:
            if day == 0:
                tds.append('<td style="padding:4px;background:#f8fafc;"></td>')
                continue
            d = date(y, m, day)
            ds = d.isoformat()
            inner_parts: list[str] = []
            for bl in by_day.get(ds, []):
                nome = html.escape(str(bl["nome"])[:18])
                hi = html.escape(str(bl["hora_inicio"]))
                hf = html.escape(str(bl["hora_fim"]))
                ci = int(bl.get("cor_idx") or 0) % len(_COR_SLOT)
                inner_parts.append(
                    f"<div style='margin:2px 0;padding:3px 4px;border-radius:6px;font-size:0.68rem;"
                    f"background:{_COR_SLOT[ci]};border:1px solid {_COR_BORDER[ci]};'>● {nome} {hi}-{hf}</div>"
                )
            inner = "".join(inner_parts) if inner_parts else "<span style='opacity:0.35'>·</span>"
            tds.append(
                f"<td style='vertical-align:top;padding:4px;border:1px solid rgba(0,0,0,0.06);'>"
                f"<div style='font-weight:700;font-size:0.72rem;color:#2D332F'>{day}</div>{inner}</td>"
            )
        body_rows.append("<tr>" + "".join(tds) + "</tr>")
    return (
        "<table style='width:100%;border-collapse:collapse;font-family:Montserrat,sans-serif;'>"
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"
    )


def _col_section_title_html(title: str) -> str:
    t = html.escape(title)
    return f'<div class="bea-cv-cag-h2">{t}</div>'


def render_colaboradores_disponibilidade_setor() -> None:
    st.markdown(
        '<div class="bea-cv-cag-gap" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    _, mid, _ = st.columns([0.02, 0.96, 0.02])
    with mid:
        st.markdown(
            '<p class="bea-col-disp-flag" aria-hidden="true" style="height:1px;margin:0;padding:0;">&nbsp;</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            _col_section_title_html("3. Disponibilidade e calendário operacional"),
            unsafe_allow_html=True,
        )
        st.caption(
            "Pesquisa hierárquica, plano com validade explícita, regras semanais / excepções / intervalos "
            "customizados, confirmação para publicar no calendário mestre e alertas 15 / 10 / 5 dias."
        )

        resumo = listar_colaboradores_resumo()
        if not resumo:
            st.info("Cadastre colaboradores para gerir disponibilidade.")
            with st.expander("3.1 Pesquisa e filtro de contexto", expanded=False):
                st.caption("Disponível após o primeiro cadastro na secção «Equipa» ou na ficha abaixo.")
            with st.expander("3.2 Plano de disponibilidade (validade + regras)", expanded=False):
                st.caption("—")
            with st.expander("3.3 Calendário mestre (semanal / mensal)", expanded=False):
                st.caption("—")
            return

        if "col_disp_anchor" not in st.session_state:
            st.session_state.col_disp_anchor = date.today()
        if "col_disp_mode" not in st.session_state:
            st.session_state.col_disp_mode = "Semanal"
        today = date.today()
        if "col_disp_valido_de" not in st.session_state:
            st.session_state.col_disp_valido_de = today
        if "col_disp_valido_ate" not in st.session_state:
            st.session_state.col_disp_valido_ate = today + timedelta(days=30)

        with st.expander("3.1 Pesquisa e filtro de contexto", expanded=False):
            st.markdown(
                "**Natureza → Especialidade → Serviço** (filtro para o calendário mestre; opcional).",
                unsafe_allow_html=True,
            )
            _nat_ph = "— Todas as naturezas —"
            nat_opts = listar_naturezas_servicos_mapa_equipa()
            nat_labels = [_nat_ph] + list(nat_opts)
            st.selectbox("Natureza (calendário)", nat_labels, key="col_disp_cal_nat")
            nat_l = str(st.session_state.get("col_disp_cal_nat") or _nat_ph)
            nat_q = None if nat_l == _nat_ph else [nat_l]
            svc_rows = listar_servicos_para_mapa_equipa(nat_q)

            esp_ph = "— Todas as especialidades —"
            esp_labels = [esp_ph] + _disp_mapa_especialidades_opts(svc_rows)
            st.selectbox("Especialidade (calendário)", esp_labels, key="col_disp_cal_esp")
            esp_l = str(st.session_state.get("col_disp_cal_esp") or esp_ph)
            if esp_l == esp_ph:
                cal_col_ids: list[int] | None = None
            else:
                rows_e = _disp_mapa_filtra_rows_por_especialidades(svc_rows, [esp_l])
                ids_sv = [int(r[0]) for r in rows_e]
                if not ids_sv:
                    cal_col_ids = []
                else:
                    cj = resolver_conjunto_servicos_mapa_equipa(
                        naturezas_seleccionadas=[nat_l] if nat_l != _nat_ph else [],
                        especialidades_seleccionadas=[esp_l],
                        servico_ids_seleccionados=ids_sv,
                    )
                    rows_m = listar_colaboradores_mapa_equipa(cj)
                    cal_col_ids = [int(r["id"]) for r in rows_m]
            st.session_state["_col_disp_cal_filter_ids"] = cal_col_ids

            opts_c = [(f"#{int(tid)} — {nome}", int(tid)) for tid, nome in resumo]
            labels = [x[0] for x in opts_c]
            if "col_disp_pick_label" not in st.session_state:
                st.session_state.col_disp_pick_label = labels[0]
            st.selectbox(
                "Colaborador alvo (plano + alertas)",
                labels,
                key="col_disp_pick_label",
            )
            pick = str(st.session_state.get("col_disp_pick_label") or labels[0])
            cid = next(x[1] for x in opts_c if x[0] == pick)
            st.session_state["col_disp_cid"] = int(cid)

        _render_alertas_terracota()

        cid_sel = int(st.session_state.get("col_disp_cid") or resumo[0][0])

        with st.expander("3.2 Plano de disponibilidade (validade + regras)", expanded=True):
            st.markdown(
                "**Período de validade** do plano (obrigatório). Depois adicione janelas horárias: "
                "padrão semanal, excepção por data ou intervalo customizado.",
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns(2)
            with c1:
                vd = st.date_input("Válido de *", key="col_disp_valido_de", format="DD/MM/YYYY")
            with c2:
                va = st.date_input("Válido até *", key="col_disp_valido_ate", format="DD/MM/YYYY")

            if st.button("Gravar / actualizar rascunho (datas)", key="col_disp_save_draft_dates"):
                ok, msg, pid = criar_ou_atualizar_rascunho(
                    cid_sel,
                    valido_de=vd.isoformat() if vd else "",
                    valido_ate=va.isoformat() if va else "",
                )
                if ok:
                    st.session_state["col_disp_last_plano_id"] = pid
                    st.success(msg)
                else:
                    st.error(msg)

            draft = obter_rascunho_aberto(cid_sel)
            if not draft:
                st.info("Crie um rascunho com as datas acima para adicionar regras.")
            else:
                pid = int(draft["id"])
                st.caption(f"Rascunho **#{pid}** — {draft['valido_de']} → {draft['valido_ate']}")

                st.markdown("**Padrão semanal** (um horário aplicado aos dias seleccionados)", unsafe_allow_html=True)
                dias_sel = st.multiselect(
                    "Dias da semana",
                    options=[f"{a}|{b}" for a, b in _DIAS_SEMANA_OPTS],
                    format_func=lambda x: x.split("|", 1)[0],
                    key="col_disp_wd_sel",
                )
                w1, w2 = st.columns(2)
                with w1:
                    h1 = st.text_input("Início", value="09:00", key="col_disp_w_h1")
                with w2:
                    h2 = st.text_input("Fim", value="13:00", key="col_disp_w_h2")
                if st.button("Adicionar padrão semanal", key="col_disp_add_weekly"):
                    if not dias_sel:
                        st.error("Seleccione pelo menos um dia da semana.")
                    else:
                        for chunk in dias_sel:
                            wd = int(chunk.split("|", 1)[1])
                            ok, msg = adicionar_regra(
                                pid,
                                tipo="semanal",
                                hora_inicio=h1,
                                hora_fim=h2,
                                dia_semana=wd,
                            )
                            if not ok:
                                st.error(msg)
                                break
                        else:
                            st.success("Regras semanais adicionadas.")
                            st.rerun()

                st.markdown("**Excepção por data** (janela num dia específico)", unsafe_allow_html=True)
                ex_d = st.date_input("Data da excepção", key="col_disp_ex_d", format="DD/MM/YYYY")
                e1, e2 = st.columns(2)
                with e1:
                    ex_hi = st.text_input("Início (excepção)", value="14:00", key="col_disp_ex_hi")
                with e2:
                    ex_hf = st.text_input("Fim (excepção)", value="18:00", key="col_disp_ex_hf")
                if st.button("Adicionar excepção", key="col_disp_add_ex"):
                    ok, msg = adicionar_regra(
                        pid,
                        tipo="excecao_dia",
                        hora_inicio=ex_hi,
                        hora_fim=ex_hf,
                        data_especifica=ex_d.isoformat() if ex_d else "",
                    )
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

                st.markdown(
                    "**Intervalo customizado** (datas de início/fim; opcionalmente restrinja a dias da semana)",
                    unsafe_allow_html=True,
                )
                k1, k2 = st.columns(2)
                with k1:
                    kd0 = st.date_input("De", key="col_disp_cust_de", format="DD/MM/YYYY")
                with k2:
                    kd1 = st.date_input("Até", key="col_disp_cust_ate", format="DD/MM/YYYY")
                cust_dias = st.multiselect(
                    "Dias da semana no intervalo (vazio = todos os dias)",
                    options=[f"{a}|{b}" for a, b in _DIAS_SEMANA_OPTS],
                    format_func=lambda x: x.split("|", 1)[0],
                    key="col_disp_cust_wd",
                )
                u1, u2 = st.columns(2)
                with u1:
                    cu_hi = st.text_input("Início (custom)", value="10:00", key="col_disp_cust_hi")
                with u2:
                    cu_hf = st.text_input("Fim (custom)", value="12:30", key="col_disp_cust_hf")
                if st.button("Adicionar intervalo customizado", key="col_disp_add_cust"):
                    mask = None
                    if cust_dias:
                        mask = ",".join(sorted({chunk.split("|", 1)[1] for chunk in cust_dias}, key=int))
                    ok, msg = adicionar_regra(
                        pid,
                        tipo="custom_intervalo",
                        hora_inicio=cu_hi,
                        hora_fim=cu_hf,
                        intervalo_de=kd0.isoformat() if kd0 else "",
                        intervalo_ate=kd1.isoformat() if kd1 else "",
                        dias_mascara=mask,
                    )
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

                st.markdown("**Regras actuais (rascunho)**", unsafe_allow_html=True)
                regras = listar_regras_plano(pid)
                if not regras:
                    st.caption("— Ainda sem regras —")
                else:
                    for rr in regras:
                        lbl = f"{rr['tipo']} · {rr['hora_inicio']}–{rr['hora_fim']}"
                        if rr["tipo"] == "semanal":
                            lbl += f" · dia {_DIAS_SEMANA_OPTS[int(rr['dia_semana'] or 0)][0]}"
                        elif rr["tipo"] == "excecao_dia":
                            lbl += f" · {rr['data_especifica']}"
                        elif rr["tipo"] == "custom_intervalo":
                            lbl += f" · {rr['intervalo_de']}…{rr['intervalo_ate']}"
                            if rr.get("dias_mascara"):
                                lbl += f" · máscara {rr['dias_mascara']}"
                        cA, cB = st.columns([4, 1])
                        with cA:
                            st.caption(lbl)
                        with cB:
                            if st.button("Remover", key=f"col_disp_rm_{rr['id']}"):
                                ok_r, msg_r = remover_regra(int(rr["id"]))
                                if ok_r:
                                    st.success(msg_r)
                                    st.rerun()
                                st.error(msg_r)

                st.markdown(
                    '<div style="margin-top:12px;padding:10px 12px;border-radius:12px;'
                    'background:#FFF4E5;color:#D4A373;font-weight:600;font-size:0.9rem;">'
                    "Confirmação obrigatória para publicar no calendário mestre (rascunhos não aparecem no mapa).</div>",
                    unsafe_allow_html=True,
                )
                ack = st.checkbox(
                    "Confirmo que o plano foi revisto e deve ser **recebido como definitivo** para alimentar o calendário.",
                    key="col_disp_ack_confirm",
                )
                if st.button("Confirmar plano publicado", type="primary", key="col_disp_btn_confirm"):
                    if not ack:
                        st.error("Marque a confirmação para publicar.")
                    else:
                        ok_c, msg_c = confirmar_plano_publicado(pid)
                        if ok_c:
                            st.success(msg_c)
                            st.session_state.pop("col_disp_ack_confirm", None)
                            st.rerun()
                        else:
                            st.error(msg_c)

        with st.expander("3.3 Calendário mestre (semanal / mensal)", expanded=False):
            st.radio(
                "Período de visualização",
                ["Semanal", "Mensal"],
                horizontal=True,
                key="col_disp_mode",
            )
            modo = str(st.session_state.get("col_disp_mode") or "Semanal")
            anchor: date = st.session_state["col_disp_anchor"]
            if modo == "Semanal":
                mon, sun = _week_mon_sun(anchor)
                period_lbl = f"{mon.strftime('%d/%m')} — {sun.strftime('%d/%m/%Y')}"
                prev_lab, next_lab = "Semana anterior", "Semana seguinte"
                d_de, d_ate = mon.isoformat(), sun.isoformat()
            else:
                mon, sun = _month_bounds(anchor)
                period_lbl = f"{mon.strftime('%d/%m/%Y')} — {sun.strftime('%d/%m/%Y')}"
                prev_lab, next_lab = "Mês anterior", "Mês seguinte"
                d_de, d_ate = mon.isoformat(), sun.isoformat()

            n1, n2, n3 = st.columns([1, 2, 1])
            with n1:
                if st.button(prev_lab, key="col_disp_cal_prev"):
                    if modo == "Semanal":
                        st.session_state.col_disp_anchor = anchor - timedelta(days=7)
                    else:
                        st.session_state.col_disp_anchor = _shift_month(anchor, -1)
                    st.rerun()
            with n2:
                st.markdown(
                    f"<div style='text-align:center;font-weight:600;color:#2D332F;'>{html.escape(period_lbl)}</div>",
                    unsafe_allow_html=True,
                )
            with n3:
                if st.button(next_lab, key="col_disp_cal_next"):
                    if modo == "Semanal":
                        st.session_state.col_disp_anchor = anchor + timedelta(days=7)
                    else:
                        st.session_state.col_disp_anchor = _shift_month(anchor, 1)
                    st.rerun()

            filt = st.session_state.get("_col_disp_cal_filter_ids")
            col_ids = None
            if isinstance(filt, list):
                col_ids = filt if filt else [-1]

            by_day = agregar_slots_calendario_mestre(data_de=d_de, data_ate=d_ate, colaborador_ids=col_ids)
            if modo == "Semanal":
                cal_html = _week_cal_html(mon=mon, by_day=by_day)
            else:
                cal_html = _month_cal_html(ref=mon, by_day=by_day)

            st.markdown(f'<div class="bea-proto-scope">{cal_html}</div>', unsafe_allow_html=True)
            st.caption(
                "Legenda: ● bloco confirmado; cores distinguem colaboradores no período. Filtre por natureza/especialidade "
                "em 3.1 para reduzir o conjunto."
            )


def _render_alertas_terracota() -> None:
    cid = st.session_state.get("col_disp_cid")
    cid_int = int(cid) if cid is not None else None
    alerts = listar_alertas_confirmados(cid_int)
    if not alerts:
        return
    parts = []
    for a in alerts:
        parts.append(
            f"<strong>{html.escape(a['colaborador_nome'])}</strong>: faltam "
            f"<strong>{a['dias']}</strong> dias para o fim da validade ({html.escape(a['valido_ate'])})."
        )
    inner = "<br/>".join(parts)
    st.markdown(
        f'<div class="bea-cv-badge-terracota" style="display:block;padding:10px 14px;border-radius:12px;'
        f"margin:8px 0 12px 0;line-height:1.45;white-space:normal;font-weight:500;background:#FFF4E5;"
        f'color:#D4A373;">{inner}</div>',
        unsafe_allow_html=True,
    )
