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
    remover_regra,
)

_COR_SLOT = (
    "rgba(118, 148, 125, 0.22)",
    "rgba(212, 163, 115, 0.28)",
    "rgba(100, 116, 139, 0.2)",
    "rgba(167, 139, 250, 0.25)",
    "rgba(45, 51, 47, 0.12)",
)
_COR_BORDER = ("#76947D", "#D4A373", "#64748B", "#8B5CF6", "#2D332F")
_COR_OCUPADO_BG = "rgba(194,65,12,0.16)"
_COR_OCUPADO_TX = "#7C2D12"
_COR_OCUPADO_BD = "#C2410C"


def _html_bloco_calendario_disp(bl: dict[str, object], *, compact: bool) -> str:
    """Um cartão semanal ou mensal: disponível (tracejado + paleta do colaborador) vs marcado (sólido terracotta)."""
    tipo = str(bl.get("bloco") or "disponibilidade")
    nome = html.escape(str(bl.get("nome") or "—")[:56])
    hi = html.escape(str(bl.get("hora_inicio") or ""))
    hf = html.escape(str(bl.get("hora_fim") or ""))
    ci = int(bl.get("cor_idx") or 0) % len(_COR_SLOT)
    ff = "'Montserrat',sans-serif"

    if tipo == "agendamento":
        cli = html.escape(str(bl.get("cliente_nome") or "").strip()[:compact and 42 or 90])
        srv = html.escape(str(bl.get("servico_nome") or "").strip()[:compact and 32 or 100])
        if compact:
            return (
                f"<div title='Agendamento marcado' style='margin:3px 0;padding:5px 6px;border-radius:8px;"
                f"font-size:0.66rem;font-family:{ff};font-weight:650;background:{_COR_OCUPADO_BG};color:{_COR_OCUPADO_TX};"
                f"border:2px solid {_COR_OCUPADO_BD};box-shadow:0 0 0 1px rgba(194,65,12,0.12) inset'>"
                f"<span style='display:inline-block;line-height:1;padding:2px 5px;border-radius:4px;background:#FFF7ED;"
                f"font-size:0.58rem;color:{_COR_OCUPADO_BD};font-weight:700'>MARCADO</span>"
                f" · {nome}<br/><span>{hi}–{hf}</span>"
                + (f"<br/><small style='opacity:0.95'>{cli}</small>" if cli else "")
                + (f"<br/><small style='opacity:0.88'>{srv}</small>" if srv else "")
                + "</div>"
            )
        return (
            f"<div title='Agendamento marcado' style='margin:4px 0;padding:8px 9px;border-radius:10px;"
            f"font-size:0.78rem;font-family:{ff};font-weight:580;background:{_COR_OCUPADO_BG};color:{_COR_OCUPADO_TX};"
            f"border:2px solid {_COR_OCUPADO_BD};box-shadow:0 1px 0 rgba(124,45,18,0.08)'>"
            f"<span style='display:inline-block;margin-bottom:4px;padding:2px 7px;border-radius:6px;background:#FFF7ED;"
            f"font-size:0.65rem;color:{_COR_OCUPADO_BD};font-weight:700;letter-spacing:0.02em'>AGENDAMENTO</span>"
            f"<br/><strong>{nome}</strong><br/><span style='opacity:0.96'>{hi}–{hf}</span>"
            + (f"<br/><small style='opacity:0.92'><strong>{cli}</strong></small>" if cli else "")
            + (f"<br/><small style='opacity:0.85'>{srv}</small>" if srv else "")
            + "</div>"
        )

    esp = html.escape(str(bl.get("especialidades_txt") or "")[:compact and 36 or 120])
    tone = _COR_SLOT[ci]
    bd_s = _COR_BORDER[ci]
    if compact:
        return (
            f"<div title='Horário disponível' style='margin:2px 0;padding:4px 5px;border-radius:8px;"
            f"font-size:0.66rem;font-family:{ff};background:{tone};color:#1e293b;border:2px dashed {bd_s};'>"
            f"<span style='opacity:0.75;font-weight:700'>DISP.</span> {nome}<br/><span>{hi}–{hf}</span>"
            + (f"<br/><small style='opacity:0.82'>{esp}</small>" if esp else "")
            + "</div>"
        )
    return (
        f"<div title='Horário disponível' style='margin:4px 0;padding:6px 8px;border-radius:10px;"
        f"font-size:0.78rem;font-family:{ff};background:{tone};color:#1e293b;border:2px dashed {bd_s};'>"
        f"<strong style='opacity:0.75'>DISP.</strong> {nome}<br/><span style='opacity:0.95'>{hi}–{hf}</span><br/>"
        f"<small style='opacity:0.85'>{esp}</small></div>"
    )


def _disp_mapa_especialidades_opts(
    rows: list[tuple[int, str, str, str]],
    *,
    natureza: str | None = None,
) -> list[str]:
    from src.modules.catalogo import listar_especialidades_por_natureza

    nomes: set[str] = set()
    nat = str(natureza or "").strip()
    if nat:
        for r in listar_especialidades_por_natureza(nat):
            nm = str(r.get("nome") or "").strip()
            if nm:
                nomes.add(nm)
    for r in rows:
        ep = str(r[3]).strip()
        if ep:
            nomes.add(ep)
    out = sorted(nomes, key=str.casefold)
    if any(not str(r[3]).strip() for r in rows):
        if MAPA_EQUI_ESP_SEM_LABEL not in out:
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
            parts.append(_html_bloco_calendario_disp(bl, compact=False))
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
                inner_parts.append(_html_bloco_calendario_disp(bl, compact=True))
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
    st.markdown(
        '<p class="bea-col-disp-flag" aria-hidden="true" style="height:1px;margin:0;padding:0;">&nbsp;</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        _col_section_title_html("4. Disponibilidade e calendário operacional"),
        unsafe_allow_html=True,
    )
    resumo = listar_colaboradores_resumo()
    if not resumo:
        st.info("Cadastre colaboradores para gerir disponibilidade.")
        with st.expander("4.1 Pesquisa de Disponibilidade de Colaboradores", expanded=False):
            st.caption("Disponível após o primeiro cadastro na secção «Equipa» ou na ficha abaixo.")
        with st.expander("4.2 Plano de disponibilidade", expanded=False):
            st.caption("—")
        with st.expander("4.3 Calendário mestre (semanal / mensal)", expanded=False):
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

    with st.expander("4.1 Pesquisa de Disponibilidade de Colaboradores", expanded=False):
        st.markdown(
            "**Natureza → Especialidade → Serviço**",
            unsafe_allow_html=True,
        )
        _nat_ph = "— Todas as naturezas —"
        nat_opts = listar_naturezas_servicos_mapa_equipa()
        nat_labels = [_nat_ph] + list(nat_opts)
        st.selectbox("Natureza", nat_labels, key="col_disp_cal_nat")
        nat_l = str(st.session_state.get("col_disp_cal_nat") or _nat_ph)
        nat_q = None if nat_l == _nat_ph else [nat_l]
        svc_rows = listar_servicos_para_mapa_equipa(nat_q)

        esp_ph = "— Todas as especialidades —"
        esp_labels = [esp_ph] + _disp_mapa_especialidades_opts(
            svc_rows,
            natureza=nat_l if nat_l != _nat_ph else None,
        )
        st.selectbox("Especialidade", esp_labels, key="col_disp_cal_esp")
        esp_l = str(st.session_state.get("col_disp_cal_esp") or esp_ph)
        if esp_l == esp_ph:
            if nat_l == _nat_ph:
                cal_col_ids: list[int] | None = None
            else:
                ids_nat = [int(r[0]) for r in svc_rows]
                if not ids_nat:
                    cal_col_ids = []
                else:
                    rows_m = listar_colaboradores_mapa_equipa(ids_nat)
                    cal_col_ids = [int(r["id"]) for r in rows_m]
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

        if cal_col_ids is None:
            filt_resumo = list(resumo)
        else:
            _ok_cal = set(int(x) for x in cal_col_ids)
            filt_resumo = [(tid, nome) for tid, nome in resumo if int(tid) in _ok_cal]
        if not filt_resumo:
            st.warning(
                "Nenhum colaborador com habilitação nos serviços deste filtro — "
                "a lista mostra toda a equipa até existir correspondência (evita bloquear o ecrã)."
            )
            filt_resumo = list(resumo)
        colab_ids = [int(tid) for tid, nome in filt_resumo]
        nome_por_id = {int(tid): str(nome) for tid, nome in filt_resumo}
        if "col_disp_cid" not in st.session_state or int(st.session_state.col_disp_cid) not in colab_ids:
            st.session_state.col_disp_cid = colab_ids[0]
        st.selectbox(
            "Colaborador",
            colab_ids,
            format_func=lambda cid: nome_por_id[int(cid)],
            key="col_disp_cid",
        )

    _render_alertas_terracota()

    cid_sel = int(st.session_state.get("col_disp_cid") or resumo[0][0])

    with st.expander("4.2 Plano de disponibilidade", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            vd = st.date_input("Data Inicio", key="col_disp_valido_de", format="DD/MM/YYYY")
        with c2:
            va = st.date_input("Data Fim", key="col_disp_valido_ate", format="DD/MM/YYYY")

        datas_ok = bool(vd and va and vd <= va)
        if vd and va and vd > va:
            st.error("«Data Fim» deve ser igual ou posterior a «Data Inicio».")

        h1, h2 = st.columns(2)
        with h1:
            hi = st.text_input(
                "Hora início",
                value="09:00",
                key="col_disp_simp_hi",
                disabled=not datas_ok,
            )
        with h2:
            hf = st.text_input(
                "Hora fim",
                value="18:00",
                key="col_disp_simp_hf",
                disabled=not datas_ok,
            )

        if st.button(
            "Guardar as informações e publicar no calendário",
            type="primary",
            key="col_disp_btn_guardar_publicar",
            disabled=not datas_ok,
        ):
            hi_s, hf_s = str(hi or "").strip(), str(hf or "").strip()
            if not hi_s or not hf_s:
                st.error("Indique hora de início e hora de fim.")
            else:
                ok_d, msg_d, pid = criar_ou_atualizar_rascunho(
                    cid_sel,
                    valido_de=vd.isoformat() if vd else "",
                    valido_ate=va.isoformat() if va else "",
                )
                if not ok_d or pid is None:
                    st.error(msg_d)
                else:
                    for rr in listar_regras_plano(int(pid)):
                        ok_rm, msg_rm = remover_regra(int(rr["id"]))
                        if not ok_rm:
                            st.error(msg_rm)
                            break
                    else:
                        ok_ar, msg_ar = adicionar_regra(
                            int(pid),
                            tipo="custom_intervalo",
                            hora_inicio=hi_s,
                            hora_fim=hf_s,
                            intervalo_de=vd.isoformat(),
                            intervalo_ate=va.isoformat(),
                        )
                        if not ok_ar:
                            st.error(msg_ar)
                        else:
                            ok_c, msg_c = confirmar_plano_publicado(int(pid))
                            if ok_c:
                                st.success(msg_c)
                                st.rerun()
                            else:
                                st.error(msg_c)

    with st.expander("4.3 Calendário mestre (semanal / mensal)", expanded=False):
        st.radio(
            "Período de visualização",
            ["Semanal", "Mensal"],
            horizontal=True,
            key="col_disp_mode",
        )
        modo = str(st.session_state.get("col_disp_mode") or "Semanal")

        usar_filtro_ctx = st.checkbox(
            "Mostrar somente colaboradores alinhados com os filtros seleccionados",
            key="col_disp_cal_apply_ctx_filter",
            help="Se a opção for desmarcada, o calendário irá listar todos os colaboradores ativos, "
            "independentemente dos filtros seleccionados.",
        )

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

        col_ids = None
        if usar_filtro_ctx:
            filt = st.session_state.get("_col_disp_cal_filter_ids")
            if isinstance(filt, list):
                col_ids = filt if filt else [-1]

        by_day = agregar_slots_calendario_mestre(data_de=d_de, data_ate=d_ate, colaborador_ids=col_ids)
        if modo == "Semanal":
            cal_html = _week_cal_html(mon=mon, by_day=by_day)
        else:
            cal_html = _month_cal_html(ref=mon, by_day=by_day)

        st.markdown(f'<div class="bea-proto-scope">{cal_html}</div>', unsafe_allow_html=True)
        st.caption(
            "Legenda: **DISP.** — Horário disponível para agendamento; "
            "**AGENDAMENTO / MARCADO** — horário reservado, indisponível para novo agendamento."
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
