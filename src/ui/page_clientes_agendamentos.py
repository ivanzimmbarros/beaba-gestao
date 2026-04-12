"""Consolidação Clientes + Agendamentos — Setores 1, 2, 3 (dados pessoais) e Setor 4 (agenda)."""

from __future__ import annotations

import html
import re
from calendar import monthcalendar, monthrange
from datetime import date, datetime, timedelta
from typing import Any, Literal, cast

import streamlit as st

from src.pages.theme import get_beaba_css  # noqa: F401 — BeaBa Sereno (CSS em app.main)
from src.modules.agendamento import (
    alterar_status,
    atualizar_agendamento,
    cancelar_agendamento,
    criar_agendamento_pre_venda,
    listar_agendamentos,
    obter_agendamento,
    obter_resumo_agendamentos_cliente_setor2_proposta,
)
from src.modules.catalogo import listar_servicos_para_venda
from src.modules.cliente import (
    atualizar_cliente,
    buscar_cliente_por_whatsapp,
    buscar_clientes_por_nif_email_telefone,
    cadastrar_cliente,
    obter_cliente_completo,
)
from src.modules.colaborador import listar_colaboradores_resumo
from src.modules.constants import NATUREZAS_CATALOGO_FASE3, SEXOS
from src.modules.nif import normalizar_nif_armazenamento
from src.modules.telefone import normalizar_telefone_legado_ou_e164
from src.modules.validators import email_valido, parse_data_iso
from src.ui.telefone_widgets import ler_e164_de_widgets, preencher_session_telefone_de_e164, render_grupo_telefone
from src.ui.theme import agenda_pagamento_dot, agenda_status_style, agenda_tipo_icon
from src.ui.constituicao_visual_shell import inject_constituicao_cag_page
from src.ui.fmt_euro_constituicao import fmt_euro_centavos
from src.ui.widgets.cliente_search import CLIENTE_SEARCH_DATE_MIN, render_cliente_search_widget

_CAG_PREFIX = "cag_"


def _cag_section_title_html(title: str) -> str:
    """Título de secção — serifado Master (#2D332F)."""
    t = html.escape(title)
    return f'<div class="bea-cv-cag-h2">{t}</div>'

_CAG_STATUS_DB_TO_LBL: dict[str, str] = {
    "PRE_AGENDADO": "Pré-agendado",
    "AGENDADO": "Agendado",
    "CONFIRMADO": "Confirmado",
    "REALIZADO_PENDENTE_PGTO": "Realizado (pendente pagamento)",
    "CONCLUIDO": "Concluído",
    "CANCELADO": "Cancelado",
}

StatusAg = Literal[
    "PRE_AGENDADO",
    "AGENDADO",
    "CONFIRMADO",
    "REALIZADO_PENDENTE_PGTO",
    "CONCLUIDO",
    "CANCELADO",
]


def _cag_status_lbl_para_db(lbl: str) -> str:
    rev = {v: k for k, v in _CAG_STATUS_DB_TO_LBL.items()}
    return rev.get(lbl, "AGENDADO")


def _cag_format_data_pt(iso_d: str) -> str:
    s = str(iso_d)[:10]
    try:
        d = datetime.strptime(s, "%Y-%m-%d").date()
        return d.strftime("%d/%m/%Y")
    except ValueError:
        return s


def _cag_ag_html_escape(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _cag_week_range(anchor: date) -> tuple[date, date]:
    mon = anchor - timedelta(days=anchor.weekday())
    sun = mon + timedelta(days=6)
    return mon, sun


def _cag_month_bounds(d: date) -> tuple[date, date]:
    first = d.replace(day=1)
    _, last_day = monthrange(first.year, first.month)
    last = first.replace(day=last_day)
    return first, last


def _cag_pagamento_pago_ou_parcial(rotulo: str) -> bool:
    r = (rotulo or "").strip()
    return r.startswith("Pago") or "Parcialmente" in r


def _cag_sort_ag_rows(
    rows: list[dict[str, Any]], *, col: str, asc: bool
) -> list[dict[str, Any]]:
    key_map = {
        "Data": lambda x: str(x.get("data_agendamento") or ""),
        "Início": lambda x: str(x.get("hora_inicio") or ""),
        "Fim": lambda x: str(x.get("hora_fim") or ""),
        "Serviço": lambda x: str(x.get("servico_nome") or "").lower(),
        "Estado": lambda x: str(x.get("status") or ""),
    }
    fn = key_map.get(col, key_map["Data"])
    out = sorted(rows, key=fn, reverse=not asc)
    return out


def _cag_week_cal_table_html(*, mon: date, week_rows: list[dict[str, Any]]) -> str:
    by_day: dict[str, list[dict[str, Any]]] = {}
    for ev in week_rows:
        by_day.setdefault(str(ev["data_agendamento"])[:10], []).append(ev)
    for k in by_day:
        by_day[k].sort(key=lambda x: (str(x["hora_inicio"]), int(x["id"])))
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
            tit = (
                f"{pre_badge}{ic} {_cag_ag_html_escape(str(ev['servico_nome']))} · "
                f"{_cag_ag_html_escape(str(ev['cliente_nome']))}"
            )
            sub = (
                f"{_cag_ag_html_escape(str(ev['hora_inicio']))}–{_cag_ag_html_escape(str(ev['hora_fim']))} · "
                f"{_cag_ag_html_escape(str(ev['status']))} · "
                f"<span style='color:{pg_col};font-weight:700' title='Pagamento'>{pg_sym}</span>"
            )
            inner_parts.append(
                f"<div style='margin:4px 0;padding:6px 8px;border-radius:10px;"
                f"background:{stl['bg']};border:1px solid {stl['border']};font-size:0.8rem;'>"
                f"<strong>#{ev['id']}</strong> {tit}<br><span style='opacity:0.9'>{sub}</span></div>"
            )
        inner = "".join(inner_parts) if inner_parts else "<span style='opacity:0.5'>—</span>"
        cells.append(
            "<td style='vertical-align:top;width:14%;padding:6px;border:1px solid rgba(0,0,0,0.08);'>"
            f"{label}{inner}</td>"
        )
    return (
        "<table style='width:100%;border-collapse:collapse;font-family:Montserrat,sans-serif;'>"
        f"<tr>{''.join(cells)}</tr></table>"
    )


def _cag_month_cal_table_html(*, ref: date, month_rows: list[dict[str, Any]]) -> str:
    y, m = ref.year, ref.month
    first, last = _cag_month_bounds(ref)
    by_day: dict[str, list[dict[str, Any]]] = {}
    for ev in month_rows:
        ds = str(ev["data_agendamento"])[:10]
        if first.isoformat() <= ds <= last.isoformat():
            by_day.setdefault(ds, []).append(ev)
    for k in by_day:
        by_day[k].sort(key=lambda x: (str(x["hora_inicio"]), int(x["id"])))
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
                tds.append("<td style='vertical-align:top;padding:4px;background:#f8fafc;'></td>")
                continue
            d = date(y, m, day)
            ds = d.isoformat()
            inner_parts: list[str] = []
            for ev in by_day.get(ds, []):
                _, pg_col = agenda_pagamento_dot(str(ev.get("pagamento") or ""))
                sn = _cag_ag_html_escape(str(ev.get("servico_nome") or ""))[:42]
                hi = _cag_ag_html_escape(str(ev.get("hora_inicio") or ""))
                inner_parts.append(
                    f"<div style='margin:2px 0;padding:3px 4px;border-radius:6px;font-size:0.72rem;"
                    f"border-left:3px solid {pg_col};background:#fff;line-height:1.2;'>"
                    f"<span style='color:{pg_col};font-weight:700'>●</span> {sn}<br/><span style='opacity:0.85'>{hi}</span></div>"
                )
            inner = "".join(inner_parts) if inner_parts else "<span style='opacity:0.35;font-size:0.7rem'>—</span>"
            tds.append(
                "<td style='vertical-align:top;padding:4px;border:1px solid rgba(0,0,0,0.06);"
                f"min-height:4.5rem;width:14%;'><div style='font-weight:600;font-size:0.78rem;margin-bottom:4px;'>"
                f"{day}</div>{inner}</td>"
            )
        body_rows.append(f"<tr>{''.join(tds)}</tr>")
    meses_pt = (
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
    tit = f"{meses_pt[m - 1]} {y}"
    return (
        f"<p style='text-align:center;font-weight:600;margin:0 0 6px 0;font-family:Montserrat,sans-serif;'>"
        f"{_cag_ag_html_escape(tit)}</p>"
        "<table style='width:100%;border-collapse:collapse;font-family:Montserrat,sans-serif;font-size:0.8rem;'>"
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"
    )


def _cag_ag_parse_novo_id(msg: str) -> int | None:
    m = re.search(r"#(\d+)", str(msg or ""))
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _cag_ag_commit_wizard_payload(payload: dict[str, Any]) -> tuple[bool, str, str]:
    """Returns (ok, user_message, flash_extra). flash_extra may augment success toast."""
    aid_sel = payload.get("aid_sel")
    if aid_sel is None:
        return False, "Agendamento inválido.", ""
    ag0 = obter_agendamento(int(aid_sel))
    if not ag0:
        return False, "Agendamento não encontrado.", ""

    d_iso = str(payload.get("d_iso") or "")
    hi = str(payload.get("hi") or "").strip()
    hf = str(payload.get("hf") or "").strip()
    obs = str(payload.get("obs") or "").strip()
    colab_ids = [int(x) for x in (payload.get("colab_ids") or [])]
    status_new = str(payload.get("status_new") or "AGENDADO")

    cancel_trans = status_new == "CANCELADO" and str(ag0["status"]) != "CANCELADO"
    if cancel_trans:
        dev_buf = bool(payload.get("dev_buf", True))
        if str(ag0.get("modo_origem") or "") == "pre_venda":
            dev_buf = False
        conv = bool(payload.get("converter_credito", False))
        ok_c, msg_c = cancelar_agendamento(
            int(aid_sel),
            devolver_ao_buffer=dev_buf,
            converter_valor_pago_em_credito_loja=conv,
        )
        extra = ""
        sc = payload.get("saldo_choice")
        if sc == "nao":
            extra = "Cancelamento realizado sem contabilização do saldo."
        elif sc == "sim" and conv:
            extra = "Saldo do cliente atualizado com sucesso."
        return ok_c, msg_c, extra

    ok_u, msg_u = atualizar_agendamento(
        int(aid_sel),
        data_agendamento=d_iso,
        hora_inicio=hi,
        hora_fim=hf,
        colaborador_ids=colab_ids,
        observacoes=obs,
    )
    if not ok_u:
        return False, msg_u, ""

    if status_new != str(ag0["status"]) and status_new != "CANCELADO":
        ok_s, msg_s = alterar_status(int(aid_sel), cast(StatusAg, status_new))
        if not ok_s:
            return False, msg_s, ""
        if "⚠️" in msg_s or "REALIZADO" in msg_s:
            return True, msg_u, msg_s
    return True, msg_u, ""


def _html_cli_result_card(*, nome_e: str, sub_e: str) -> str:
    return (
        '<div class="bea-proto-scope">'
        '<div class="bea-venda-comanda-item bea-comanda-min">'
        '<p style="margin:0 0 6px 0;text-align:right;font-size:0.95rem;opacity:0.5;">👤</p>'
        '<span class="bea-com-nome">'
        + nome_e
        + "</span><br/>"
        '<span class="bea-com-badge">'
        + sub_e
        + "</span>"
        "</div></div>"
    )


def cag_valores_setor2_identificacao_basica(cli: dict | None) -> tuple[str, str, str, str]:
    """Nome, NIF/documento, telefone (E.164), email — resumo setor 2; para testes."""
    if cli is None:
        return ("-", "-", "-", "-")
    return (
        str(cli.get("nome") or "-"),
        str(cli.get("nif_ou_documento") or "-"),
        str(cli.get("whatsapp") or "-"),
        str(cli.get("email") or "-"),
    )


def _cag_lib_ag_edit_valor_apos_bloqueio() -> bool:
    """Checkbox agenda: desmarcada após bloquear só se o cliente foi carregado pela pesquisa."""
    return not bool(st.session_state.get("cag_cli_carregado_pesquisa"))


def _cag_valor_moeda_centavos(c: int) -> str:
    return fmt_euro_centavos(int(c))


def _cag_status_badge_html(status_db: str, lbl: str) -> str:
    s = str(status_db)
    if s == "CONFIRMADO":
        cls = "bea-cv-badge-verde"
    elif s in ("PRE_AGENDADO", "AGENDADO", "REALIZADO_PENDENTE_PGTO"):
        cls = "bea-cv-badge-terracota"
    else:
        cls = "bea-cv-badge-neutro"
    return f'<span class="{cls}">{html.escape(lbl)}</span>'


def _cag_carregar_ficha(fk: str, d: dict) -> None:
    """Carrega a ficha do cliente no `session_state` (fluxo consolidado CAG), com `cag_n_emergency`."""
    st.session_state[f"{fk}_nome"] = d["nome"]
    st.session_state[f"{fk}_docintl"] = bool(d.get("identificacao_internacional"))
    st.session_state[f"{fk}_nif"] = str(d.get("nif_ou_documento") or "")
    preencher_session_telefone_de_e164(f"{fk}_tel_pri", str(d.get("whatsapp") or ""))
    st.session_state[f"{fk}_email"] = d["email"]
    st.session_state[f"{fk}_sexo"] = d["sexo"]
    st.session_state[f"{fk}_rua"] = d["endereco_rua"]
    st.session_state[f"{fk}_numero"] = d["endereco_numero"]
    st.session_state[f"{fk}_comp"] = d["endereco_complemento"]
    st.session_state[f"{fk}_cp"] = d["codigo_postal"]
    st.session_state[f"{fk}_conc"] = d["concelho"]
    st.session_state[f"{fk}_freg"] = d["freguesia"]
    st.session_state[f"{fk}_dist"] = d["distrito"]
    st.session_state[f"{fk}_pais"] = d.get("pais") or "Portugal"
    dn = d.get("data_nascimento")
    if dn and parse_data_iso(str(dn)[:10]):
        st.session_state[f"{fk}_dnasc"] = datetime.strptime(str(dn)[:10], "%Y-%m-%d").date()
    else:
        st.session_state[f"{fk}_dnasc"] = date(1990, 1, 1)
    if d["sexo"] == "Feminino":
        st.session_state[f"{fk}_gravida"] = "Sim" if d.get("gravida") else "Não"
        dp = d.get("data_parto_prevista")
        if dp and parse_data_iso(str(dp)[:10]):
            st.session_state[f"{fk}_parto"] = datetime.strptime(str(dp)[:10], "%Y-%m-%d").date()
    st.session_state[f"{fk}_temf"] = "Sim" if d["tem_filhos"] else "Não"
    if d["tem_filhos"]:
        filhos = d.get("filhos") or []
        st.session_state[f"{fk}_qtd"] = max(1, len(filhos))
        for j, row in enumerate(filhos):
            fn, ida, sx = row[0], row[1], row[2]
            st.session_state[f"{fk}_f_nom_{j}"] = fn
            st.session_state[f"{fk}_f_id_{j}"] = int(ida)
            st.session_state[f"{fk}_f_sx_{j}"] = sx
            dn_f = row[3] if len(row) >= 4 else None
            if dn_f and parse_data_iso(str(dn_f)[:10]):
                st.session_state[f"{fk}_f_hasdn_{j}"] = True
                st.session_state[f"{fk}_f_dn_{j}"] = datetime.strptime(str(dn_f)[:10], "%Y-%m-%d").date()
            else:
                st.session_state[f"{fk}_f_hasdn_{j}"] = False
    em = d.get("contatos_emergencia") or []
    if em:
        st.session_state[f"{fk}_tem_emerg"] = "Sim"
        st.session_state.cag_n_emergency = max(1, min(10, len(em)))
        for j, (en, et) in enumerate(em):
            st.session_state[f"{fk}_em_n_{j}"] = en
            preencher_session_telefone_de_e164(f"{fk}_emerg_{j}", str(et or ""))
    else:
        st.session_state[f"{fk}_tem_emerg"] = "Não"
        st.session_state.cag_n_emergency = 1
    st.session_state[f"{fk}_obs"] = d.get("observacoes") or ""


def _cag_garantir_defaults_formulario_vazio(fk: str) -> None:
    """Valores iniciais para cadastro sem pesquisa / cliente carregado (só `setdefault`)."""
    st.session_state.setdefault(f"{fk}_nome", "")
    st.session_state.setdefault(f"{fk}_docintl", False)
    st.session_state.setdefault(f"{fk}_nif", "")
    st.session_state.setdefault(f"{fk}_email", "")
    st.session_state.setdefault(f"{fk}_sexo", SEXOS[0])
    st.session_state.setdefault(f"{fk}_rua", "")
    st.session_state.setdefault(f"{fk}_numero", "")
    st.session_state.setdefault(f"{fk}_comp", "")
    st.session_state.setdefault(f"{fk}_cp", "")
    st.session_state.setdefault(f"{fk}_conc", "")
    st.session_state.setdefault(f"{fk}_freg", "")
    st.session_state.setdefault(f"{fk}_dist", "")
    st.session_state.setdefault(f"{fk}_pais", "Portugal")
    st.session_state.setdefault(f"{fk}_dnasc", date(1990, 1, 1))
    st.session_state.setdefault(f"{fk}_gravida", "Não")
    st.session_state.setdefault(f"{fk}_temf", "Não")
    st.session_state.setdefault(f"{fk}_qtd", 1)
    st.session_state.setdefault(f"{fk}_tem_emerg", "Não")
    st.session_state.setdefault(f"{fk}_obs", "")
    ink = f"{fk}_tel_pri_inited"
    if not st.session_state.get(ink):
        preencher_session_telefone_de_e164(f"{fk}_tel_pri", "")
        st.session_state[ink] = True


def _reset_cag_page_state() -> None:
    for k in list(st.session_state.keys()):
        if k.startswith(_CAG_PREFIX) or k == "_cag_prime":
            try:
                del st.session_state[k]
            except KeyError:
                pass
    for k in (
        "cag_ficha_loaded_sig",
        "cag_lib_edit",
        "_cag_lib_edit_prev",
        "cag_n_emergency",
        "cag_skip_uncheck_reload",
        "cag_ag_hidr_pick",
    ):
        st.session_state.pop(k, None)
    st.session_state.cag_form_v = 0
    st.session_state.cag_edit_id = None


def _card_shell(*, label: str, body_html: str) -> str:
    lab_e = html.escape(label)
    return (
        "<div style=\"background:#FFFFFF;border-radius:20px;padding:0.75rem 0.95rem;min-height:5.5rem;"
        "box-shadow:0 12px 40px rgba(118,148,125,0.12),0 2px 10px rgba(0,0,0,0.05);"
        "border:1px solid rgba(118,148,125,0.12);\">"
        f'<p style="margin:0 0 8px 0;font-size:0.72rem;color:#2D332F;font-family:var(--cv-sans,Montserrat),sans-serif;'
        f"line-height:1.25;opacity:0.65;font-weight:600;\">{lab_e}</p>"
        f"{body_html}</div>"
    )


def _html_linhas_natureza(rows: list[tuple[str, int]]) -> str:
    if not rows:
        return '<p style="margin:0;color:#64748B;font-size:0.88rem;">—</p>'
    parts: list[str] = []
    for nat, q in rows:
        parts.append(
            "<p style='margin:3px 0;font-size:0.9rem;'>"
            f"<span style='font-weight:600;color:#2D332F;'>"
            f"{html.escape(nat)}</span>: {int(q)}</p>"
        )
    return "".join(parts)


def _render_cag_setor2_dados_pessoais(*, cli: dict | None) -> None:
    st.markdown(
        '<div class="bea-cv-cag-h2" style="font-size:1.05rem;margin-bottom:0.35rem;">Dados Pessoais</div>',
        unsafe_allow_html=True,
    )
    nome, doc, tel, em = cag_valores_setor2_identificacao_basica(cli)
    key_suf = str(cli.get("id")) if cli else "none"
    lbl = (
        "Nome Completo",
        "NIF ou Documento de Identificação",
        "Telefone",
        "Email",
    )
    vals = (nome, doc, tel, em)
    keys_k = ("nome", "ndoc", "tel", "email")
    cols = st.columns(4)
    for c, label, val, kpart in zip(cols, lbl, vals, keys_k):
        with c:
            st.caption(label)
            st.text_input(
                label,
                value=val,
                key=f"cag_s2_dp_{key_suf}_{kpart}",
                disabled=True,
                label_visibility="collapsed",
            )
    st.divider()


def _render_cag_setor2_resumo_agendamentos(*, resumo: dict) -> None:
    st.markdown(
        '<div class="bea-cv-cag-h2" style="font-size:1.05rem;margin-bottom:0.35rem;">'
        "Resumo Geral: Agendamentos</div>",
        unsafe_allow_html=True,
    )
    c30 = resumo.get("previstos_30d_por_natureza") or []
    c10 = resumo.get("previstos_10d_por_natureza") or []
    pend_n = resumo.get("pendente_pgto_por_natureza") or []
    pend_v = int(resumo.get("pendente_pgto_valor_total_centavos") or 0)
    n_can = int(resumo.get("cancelados_60d_total") or 0)

    r1 = st.columns(5)
    labels = (
        "Total de Agendamentos previstos para os próximos 30 dias",
        "Total de Agendamentos previstos para os próximos 10 dias",
        "Qtde Total de Serviços com Pendência de Pagamento",
        "Valor Total Acumulado de Serviços com Pendencia de Pagamento",
        "Histórico de Cancelamento do Cliente",
    )
    bodies = (
        _html_linhas_natureza(list(c30)),
        _html_linhas_natureza(list(c10)),
        _html_linhas_natureza(list(pend_n)),
        f'<p style="margin:0;font-size:1.15rem;font-weight:700;color:#2D332F;">'
        f"{html.escape(_cag_valor_moeda_centavos(pend_v))}</p>",
        f'<p style="margin:0;font-size:1.15rem;font-weight:700;color:#2D332F;">'
        f"{html.escape(str(n_can))}</p>",
    )
    for col, lab, body in zip(r1, labels, bodies):
        with col:
            st.markdown(_card_shell(label=lab, body_html=body), unsafe_allow_html=True)


def _cag_executar_gravacao_ficha(*, eid: int | None, fk: str, tem_cliente: bool) -> None:
    sexo = str(st.session_state.get(f"{fk}_sexo", SEXOS[0]) or SEXOS[0])
    tem_filhos = str(st.session_state.get(f"{fk}_temf", "Não")) == "Sim"
    tem_emerg = str(st.session_state.get(f"{fk}_tem_emerg", "Não")) == "Sim"
    observacoes = str(st.session_state.get(f"{fk}_obs", "") or "")
    d_nasc_o = st.session_state.get(f"{fk}_dnasc")
    data_nasc_iso = (
        d_nasc_o.isoformat()
        if d_nasc_o is not None and hasattr(d_nasc_o, "isoformat")
        else ""
    )
    nome = str(st.session_state.get(f"{fk}_nome", "") or "")
    nif_val = str(st.session_state.get(f"{fk}_nif", "") or "")
    end_rua = str(st.session_state.get(f"{fk}_rua", "") or "")
    end_num = str(st.session_state.get(f"{fk}_numero", "") or "")
    end_comp = str(st.session_state.get(f"{fk}_comp", "") or "")
    end_cp = str(st.session_state.get(f"{fk}_cp", "") or "")
    end_conc = str(st.session_state.get(f"{fk}_conc", "") or "")
    end_freg = str(st.session_state.get(f"{fk}_freg", "") or "")
    end_dist = str(st.session_state.get(f"{fk}_dist", "") or "")
    end_pais = str(st.session_state.get(f"{fk}_pais", "") or "Portugal")
    gravida: bool | None = None
    data_parto: str | None = None
    if sexo == "Feminino":
        gravida = str(st.session_state.get(f"{fk}_gravida", "Não")) == "Sim"
        if gravida:
            dp = st.session_state.get(f"{fk}_parto")
            data_parto = dp.isoformat() if dp is not None and hasattr(dp, "isoformat") else None
    qtd_f = int(st.session_state.get(f"{fk}_qtd", 1) or 1) if tem_filhos else 0
    filhos = _cag_coletar_filhos_do_form(fk, tem_filhos, qtd_f)

    ok_t, tel_e164, err_t = ler_e164_de_widgets(f"{fk}_tel_pri")
    if not ok_t:
        st.error(err_t)
        return
    emerg_l: list[tuple[str, str]] = []
    em_err = False
    if tem_emerg:
        for i in range(st.session_state.cag_n_emergency):
            en = str(st.session_state.get(f"{fk}_em_n_{i}", "") or "").strip()
            ok_e, e164_e, err_e = ler_e164_de_widgets(f"{fk}_emerg_{i}")
            if not en and not ok_e:
                continue
            if not en or not ok_e:
                st.error(err_e or "❌ Contacto de emergência incompleto.")
                em_err = True
                break
            emerg_l.append((en, e164_e))
    if em_err:
        return

    if tem_cliente and eid is not None:
        ok, msg = atualizar_cliente(
            int(eid),
            nome=nome,
            numero_contato=tel_e164,
            endereco_rua=end_rua,
            endereco_numero=end_num,
            endereco_complemento=end_comp,
            codigo_postal=end_cp,
            concelho=end_conc,
            freguesia=end_freg,
            distrito=end_dist,
            pais=end_pais,
            email=str(st.session_state.get(f"{fk}_email", "") or ""),
            sexo=sexo,
            tem_filhos=tem_filhos,
            filhos=filhos,
            gravida=gravida,
            data_parto_prevista=data_parto,
            observacoes=observacoes or "",
            contatos_emergencia=emerg_l,
            nif=nif_val,
            documento_identificacao_internacional=bool(st.session_state.get(f"{fk}_docintl")),
            data_nascimento=data_nasc_iso,
        )
        if ok:
            st.session_state.cag_skip_uncheck_reload = True
            if st.session_state.get("cag_cli_carregado_pesquisa"):
                st.session_state.cag_lib_edit = False
                st.session_state._cag_lib_edit_prev = False
            else:
                st.session_state.cag_lib_edit = True
                st.session_state._cag_lib_edit_prev = True
            d2 = obter_cliente_completo(int(eid))
            if d2:
                _cag_carregar_ficha(fk, d2)
            st.success(msg)
            st.rerun()
        else:
            st.error(msg)
        return

    ok, msg = cadastrar_cliente(
        nome=nome,
        numero_contato=tel_e164,
        endereco_rua=end_rua,
        endereco_numero=end_num,
        endereco_complemento=end_comp,
        codigo_postal=end_cp,
        concelho=end_conc,
        freguesia=end_freg,
        distrito=end_dist,
        pais=end_pais,
        email=str(st.session_state.get(f"{fk}_email", "") or ""),
        sexo=sexo,
        tem_filhos=tem_filhos,
        filhos=filhos,
        gravida=gravida,
        data_parto_prevista=data_parto,
        observacoes=observacoes or "",
        contatos_emergencia=emerg_l,
        nif=nif_val,
        documento_identificacao_internacional=bool(st.session_state.get(f"{fk}_docintl")),
        data_nascimento=data_nasc_iso or None,
    )
    if not ok:
        st.error(msg)
        return
    cid_new = buscar_cliente_por_whatsapp(tel_e164)
    if cid_new:
        st.session_state.cag_edit_id = int(cid_new)
        st.session_state.cag_form_v += 1
        st.session_state.cag_ficha_loaded_sig = None
        st.session_state.cag_ag_hidr_pick = None
        st.session_state.cag_cli_carregado_pesquisa = False
        st.success(msg + f" Cliente #{cid_new} seleccionado.")
        st.rerun()
    st.success(msg)


def _render_cag_setor3_dados_pessoais_completo(*, fk: str, tem_cliente: bool, eid: int | None) -> None:
    st.markdown(_cag_section_title_html("3. Dados Pessoais"), unsafe_allow_html=True)
    with st.expander("Informações Detalhadas do Cliente", expanded=False):
        if tem_cliente and eid is not None:
            lib = st.checkbox(
                "Liberar edição de dados do cliente",
                key="cag_lib_edit",
            )
            prev = st.session_state.get("_cag_lib_edit_prev", False)
            if prev and not lib and not st.session_state.pop("cag_skip_uncheck_reload", False):
                d0 = obter_cliente_completo(int(eid))
                if d0:
                    _cag_carregar_ficha(fk, d0)
            st.session_state._cag_lib_edit_prev = lib
            dis = not lib
        else:
            st.checkbox(
                "Liberar edição de dados do cliente",
                value=True,
                disabled=True,
                key="cag_lib_edit_placeholder_novo",
            )
            dis = False

        st.markdown("##### Dados pessoais")
        st.text_input("Nome completo *", key=f"{fk}_nome", disabled=dis)
        st.checkbox(
            "Documento de identificação **não** é NIF português",
            key=f"{fk}_docintl",
            disabled=dis,
        )
        ph_doc = (
            "Documento internacional (3–40 caracteres)"
            if bool(st.session_state.get(f"{fk}_docintl"))
            else "9 dígitos (NIF PT)"
        )
        st.text_input(
            "NIF ou documento de identificação *",
            key=f"{fk}_nif",
            placeholder=ph_doc,
            disabled=dis,
        )
        st.date_input(
            "Data de nascimento *",
            min_value=CLIENTE_SEARCH_DATE_MIN,
            max_value=date.today(),
            format="DD/MM/YYYY",
            key=f"{fk}_dnasc",
            disabled=dis,
        )
        render_grupo_telefone(st, prefix=f"{fk}_tel_pri", label="Contacto principal *", disabled=dis)
        st.text_input("Email *", key=f"{fk}_email", disabled=dis)
        sexo = st.selectbox("Sexo *", SEXOS, key=f"{fk}_sexo", disabled=dis)

        if sexo == "Feminino":
            g_label = st.radio(
                "Está grávida? *",
                ["Não", "Sim"],
                horizontal=True,
                key=f"{fk}_gravida",
                disabled=dis,
            )
            if g_label == "Sim":
                st.date_input(
                    "Estimativa de data de parto *",
                    key=f"{fk}_parto",
                    format="DD/MM/YYYY",
                    min_value=CLIENTE_SEARCH_DATE_MIN,
                    disabled=dis,
                )

        st.markdown("##### Morada")
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            st.text_input("Rua / logradouro *", key=f"{fk}_rua", disabled=dis)
        with r1c2:
            st.text_input("Número *", key=f"{fk}_numero", disabled=dis)
        st.text_input(
            "Complemento (opcional)",
            key=f"{fk}_comp",
            placeholder="Andar, fração, etc.",
            disabled=dis,
        )
        r2c1, r2c2, r2c3 = st.columns(3)
        with r2c1:
            st.text_input("Código postal *", key=f"{fk}_cp", placeholder="4800-123", disabled=dis)
        with r2c2:
            st.text_input("Concelho *", key=f"{fk}_conc", disabled=dis)
        with r2c3:
            st.text_input("Freguesia *", key=f"{fk}_freg", disabled=dis)
        r3c1, r3c2 = st.columns(2)
        with r3c1:
            st.text_input("Distrito (opcional)", key=f"{fk}_dist", disabled=dis)
        with r3c2:
            _pais_k = f"{fk}_pais"
            if _pais_k not in st.session_state:
                st.session_state[_pais_k] = "Portugal"
            st.text_input("País *", key=_pais_k, disabled=dis)

        st.markdown("##### Filhos")
        tem_filhos = (
            st.radio("Possui filhos? *", ["Não", "Sim"], horizontal=True, key=f"{fk}_temf", disabled=dis)
            == "Sim"
        )
        if tem_filhos:
            qtd = int(
                st.number_input(
                    "Quantos filhos? *",
                    min_value=1,
                    max_value=20,
                    value=1,
                    step=1,
                    key=f"{fk}_qtd",
                    disabled=dis,
                )
            )
            for j in range(qtd):
                st.markdown(f"**Filho {j + 1}**")
                cf1, cf2, cf3 = st.columns(3)
                with cf1:
                    st.text_input("Nome *", key=f"{fk}_f_nom_{j}", disabled=dis)
                with cf2:
                    st.number_input(
                        "Idade (anos) *",
                        min_value=0,
                        max_value=120,
                        value=0,
                        key=f"{fk}_f_id_{j}",
                        disabled=dis,
                    )
                with cf3:
                    st.selectbox("Sexo *", SEXOS, key=f"{fk}_f_sx_{j}", disabled=dis)
                has_dn = st.checkbox(
                    "Indicar data de nascimento (opcional)",
                    key=f"{fk}_f_hasdn_{j}",
                    disabled=dis,
                )
                if has_dn:
                    st.date_input(
                        "Data de nascimento",
                        max_value=date.today(),
                        format="DD/MM/YYYY",
                        min_value=CLIENTE_SEARCH_DATE_MIN,
                        key=f"{fk}_f_dn_{j}",
                        disabled=dis,
                    )
        tem_emerg = (
            st.radio(
                "Possui contacto de emergência? *",
                ["Não", "Sim"],
                horizontal=True,
                key=f"{fk}_tem_emerg",
                disabled=dis,
            )
            == "Sim"
        )
        if tem_emerg:
            st.markdown("##### Contactos de emergência")
            c_add, _ = st.columns([2, 3])
            with c_add:
                if st.button("➕ Adicionar contacto de emergência", key=f"{fk}_add_em", disabled=dis):
                    st.session_state.cag_n_emergency = min(st.session_state.cag_n_emergency + 1, 10)
                    st.rerun()

            for i in range(st.session_state.cag_n_emergency):
                st.text_input(f"Nome (emergência {i + 1})", key=f"{fk}_em_n_{i}", disabled=dis)
                render_grupo_telefone(
                    st,
                    prefix=f"{fk}_emerg_{i}",
                    label=f"Telefone (emergência {i + 1})",
                    disabled=dis,
                )

        st.markdown("##### Observações")
        st.text_area(
            "Observações",
            key=f"{fk}_obs",
            height=100,
            placeholder="Detalhes especiais sobre a pessoa (opcional).",
            disabled=dis,
        )

        if st.button(
            "Salvar dados do cliente",
            type="secondary",
            key="cag_salvar_ficha",
            disabled=tem_cliente and dis,
        ):
            _cag_executar_gravacao_ficha(eid=eid, fk=fk, tem_cliente=tem_cliente)


def _cag_coletar_filhos_do_form(fk: str, tem_filhos: bool, qtd: int) -> list[tuple[str, int, str] | tuple[str, int, str, str]]:
    filhos: list[tuple[str, int, str] | tuple[str, int, str, str]] = []
    if not tem_filhos:
        return filhos
    for j in range(qtd):
        fn = str(st.session_state.get(f"{fk}_f_nom_{j}", "") or "")
        idade = int(st.session_state.get(f"{fk}_f_id_{j}", 0) or 0)
        sx = str(st.session_state.get(f"{fk}_f_sx_{j}", SEXOS[0]) or SEXOS[0])
        has_dn = bool(st.session_state.get(f"{fk}_f_hasdn_{j}", False))
        dn_iso: str | None = None
        if has_dn:
            d_birth = st.session_state.get(f"{fk}_f_dn_{j}")
            dn_iso = d_birth.isoformat() if d_birth is not None and hasattr(d_birth, "isoformat") else None
        if dn_iso:
            filhos.append((fn, idade, sx, dn_iso))
        else:
            filhos.append((fn, idade, sx))
    return filhos


def _cag_ag_default_colab_options(colabs: list[tuple[int, str]]) -> list[int]:
    if not colabs:
        return []
    return [colabs[0][0]]


def _cag_hidratar_form_ag(ag: dict[str, Any]) -> None:
    st.session_state.cag_ag_data = datetime.strptime(str(ag["data_agendamento"])[:10], "%Y-%m-%d").date()
    st.session_state.cag_ag_hi = str(ag["hora_inicio"])
    st.session_state.cag_ag_hf = str(ag["hora_fim"])
    st.session_state.cag_ag_obs = str(ag.get("observacoes") or "")
    st.session_state.cag_ag_status_lbl = _CAG_STATUS_DB_TO_LBL.get(
        str(ag["status"]), str(ag["status"])
    )
    cids = list(ag.get("colaborador_ids") or [])
    st.session_state.cag_ag_colabs = cids


def _cag_limpar_form_ag_novo() -> None:
    st.session_state.cag_ag_data = date.today()
    st.session_state.cag_ag_hi = "09:00"
    st.session_state.cag_ag_hf = "10:00"
    st.session_state.cag_ag_obs = ""
    st.session_state.cag_ag_natureza = "Sessão"
    colabs = listar_colaboradores_resumo()
    st.session_state.cag_ag_colabs = _cag_ag_default_colab_options(colabs)


def _cag_opcoes_status_edicao(status_db: str) -> list[str]:
    cur_lbl = _CAG_STATUS_DB_TO_LBL.get(status_db, status_db)
    out: list[str] = []
    for db, lb in _CAG_STATUS_DB_TO_LBL.items():
        if db == "CANCELADO":
            continue
        out.append(lb)
    out.append("Cancelado")
    if cur_lbl not in out:
        out.insert(0, cur_lbl)
    return out


def _cag_shift_month(d: date, delta: int) -> date:
    m0 = d.month - 1 + delta
    y = d.year + m0 // 12
    mo = m0 % 12 + 1
    ld = monthrange(y, mo)[1]
    return date(y, mo, min(d.day, ld))


def _cag_setor4_agenda_keys(*, cliente_id: int, fv: int) -> dict[str, str]:
    return {
        "pick_key": f"cag_ag_pick_{cliente_id}_{fv}",
        "offset_key": f"cag_agenda_offset_{cliente_id}_{fv}",
        "mode_k": f"cag_cal_mode_{cliente_id}_{fv}",
        "anc_k": f"cag_cal_anchor_{cliente_id}_{fv}",
        "sort_col_k": f"cag_ag_sort_col_{cliente_id}_{fv}",
        "sort_dir_k": f"cag_ag_sort_dir_{cliente_id}_{fv}",
        "sort_sig_k": f"cag_ag_sort_sig_{cliente_id}_{fv}",
    }


def _cag_setor4_run_flash_wizards_pend(
    *, cliente_id: int, fv: int, tem_cliente: bool, keys: dict[str, str]
) -> None:
    flash = st.session_state.pop("cag_ag_flash", None)
    if flash:
        st.success(str(flash))

    pick_key = keys["pick_key"]
    offset_key = keys["offset_key"]

    wz = st.session_state.get("cag_ag_wizard")
    if isinstance(wz, dict):
        pl0 = wz.get("payload") or {}
        if int(pl0.get("cliente_id") or -1) != int(cliente_id) or int(pl0.get("fv") or -1) != int(fv):
            st.session_state.pop("cag_ag_wizard", None)
            wz = None

    if isinstance(wz, dict) and tem_cliente:
        step = str(wz.get("step") or "")
        pl = dict(wz.get("payload") or {})
        pk_w = str(pl.get("pick_key") or pick_key)

        def _discard_wizard() -> None:
            st.session_state.pop("cag_ag_wizard", None)
            aid_d = pl.get("aid_sel")
            if aid_d is not None:
                ag_d = obter_agendamento(int(aid_d))
                if ag_d:
                    _cag_hidratar_form_ag(ag_d)
            st.session_state.cag_lib_ag_edit = False
            st.session_state.cag_ag_flash = "Todas as alterações foram descartadas."
            st.session_state.cag_ag_hidr_pick = (pk_w, str(st.session_state.get(pk_w) or ""))
            st.rerun()

        if step == "saldo":
            st.warning(
                "**Saldo de Pagamento Encontrado**\n\n"
                "Deseja transferir o valor pago anteriormente pelo cliente para uma reserva disponível para uso futuro?"
            )
            b1, b2 = st.columns(2)
            with b1:
                if st.button("Sim", key=f"cag_wz_saldo_y_{fv}"):
                    st.session_state.cag_ag_wizard = {
                        "step": "edit_alert",
                        "payload": {**pl, "converter_credito": True, "saldo_choice": "sim"},
                    }
                    st.rerun()
            with b2:
                if st.button("Não", key=f"cag_wz_saldo_n_{fv}"):
                    st.session_state.cag_ag_wizard = {
                        "step": "edit_alert",
                        "payload": {**pl, "converter_credito": False, "saldo_choice": "nao"},
                    }
                    st.rerun()
        elif step == "edit_alert":
            st.warning(
                "**Alerta de Edição de Informação Cadastrada**\n\n"
                "Tem certeza que quer seguir com a alteração dos dados do agendamento do cliente?"
            )
            b1, b2 = st.columns(2)
            with b1:
                if st.button("Sim", key=f"cag_wz_ed_y_{fv}"):
                    ok_c, msg_c, xtra = _cag_ag_commit_wizard_payload(pl)
                    if not ok_c:
                        st.error(msg_c)
                    else:
                        st.session_state.pop("cag_ag_wizard", None)
                        st.session_state.cag_lib_ag_edit = _cag_lib_ag_edit_valor_apos_bloqueio()
                        aid_r = pl.get("aid_sel")
                        if aid_r is not None:
                            ag2 = obter_agendamento(int(aid_r))
                            if ag2:
                                _cag_hidratar_form_ag(ag2)
                        base_ok = "Informações salvas com sucesso."
                        st.session_state.cag_ag_flash = (
                            f"{xtra} {base_ok}".strip() if xtra else base_ok
                        )
                        st.session_state[offset_key] = 0
                        st.session_state.cag_ag_hidr_pick = (
                            pk_w,
                            str(st.session_state.get(pk_w) or ""),
                        )
                        st.rerun()
            with b2:
                if st.button("Não", key=f"cag_wz_ed_n_{fv}"):
                    _discard_wizard()

    pend = st.session_state.get("cag_ag_pending_novo_dialog")
    if pend == "ask" and tem_cliente:
        st.warning(
            "**Novo agendamento**\n\n"
            "Deseja realizar um novo agendamento para o mesmo cliente?"
        )
        b1, b2 = st.columns(2)
        with b1:
            if st.button("Sim", key=f"cag_novo_ag_sim_{fv}", type="primary"):
                st.session_state.pop("cag_ag_pending_novo_dialog", None)
                st.session_state.pop("cag_ag_last_created_id", None)
                st.session_state[pick_key] = "__novo__"
                st.session_state.cag_ag_hidr_pick = None
                _cag_limpar_form_ag_novo()
                st.session_state.cag_lib_ag_edit = True
                st.rerun()
        with b2:
            if st.button("Não", key=f"cag_novo_ag_nao_{fv}"):
                st.session_state.pop("cag_ag_pending_novo_dialog", None)
                last_id = st.session_state.pop("cag_ag_last_created_id", None)
                if last_id is not None:
                    st.session_state[pick_key] = f"id:{int(last_id)}"
                    st.session_state.cag_ag_hidr_pick = None
                st.session_state.cag_lib_ag_edit = False
                st.rerun()


def _cag_setor4_try_prepare_context(
    *, cliente_id: int, fv: int, tem_cliente: bool, keys: dict[str, str]
) -> dict[str, Any] | None:
    pick_key = keys["pick_key"]
    mode_k = keys["mode_k"]
    anc_k = keys["anc_k"]

    if not tem_cliente:
        if not st.session_state.get("cag_ag_sem_cli_ready"):
            _cag_limpar_form_ag_novo()
            st.session_state.cag_ag_sem_cli_ready = True
        return None

    st.session_state.cag_ag_sem_cli_ready = False

    todos_all = listar_agendamentos(cliente_ids=[int(cliente_id)])
    ids_all = {int(a["id"]) for a in todos_all}
    raw_pick_top = str(st.session_state.get(pick_key) or "__novo__")
    if raw_pick_top.startswith("id:"):
        try:
            _tid = int(raw_pick_top.split(":", 1)[1])
            if _tid not in ids_all:
                st.session_state[pick_key] = "__novo__"
                st.session_state.cag_ag_hidr_pick = None
                raw_pick_top = "__novo__"
        except ValueError:
            st.session_state[pick_key] = "__novo__"
            st.session_state.cag_ag_hidr_pick = None
            raw_pick_top = "__novo__"

    _force_hydrate = bool(st.session_state.pop("cag_ag_need_hydrate", False))
    hidr_sig_top = st.session_state.get("cag_ag_hidr_pick")
    if _force_hydrate or hidr_sig_top != (pick_key, raw_pick_top):
        if raw_pick_top.startswith("id:"):
            try:
                _aid_h = int(raw_pick_top.split(":", 1)[1])
                ag0h = obter_agendamento(_aid_h)
                if ag0h:
                    _cag_hidratar_form_ag(ag0h)
                    st.session_state.cag_lib_ag_edit = _cag_lib_ag_edit_valor_apos_bloqueio()
            except ValueError:
                pass
        else:
            _cag_limpar_form_ag_novo()
            st.session_state.cag_lib_ag_edit = True
        st.session_state.cag_ag_hidr_pick = (pick_key, raw_pick_top)

    aid_sel: int | None = None
    if raw_pick_top.startswith("id:"):
        try:
            aid_sel = int(raw_pick_top.split(":", 1)[1])
        except ValueError:
            aid_sel = None
    modo_novo = aid_sel is None

    if modo_novo:
        dis_ag = False
    else:
        dis_ag = not bool(st.session_state.get("cag_lib_ag_edit"))

    st.session_state.setdefault(mode_k, "Semanal")
    st.session_state.setdefault(anc_k, date.today())

    return {
        **keys,
        "raw_pick_top": raw_pick_top,
        "aid_sel": aid_sel,
        "modo_novo": modo_novo,
        "dis_ag": dis_ag,
    }


def _cag_setor4_render_form_island(
    *, cliente_id: int, fv: int, tem_cliente: bool, ctx: dict[str, Any]
) -> None:
    pick_key = ctx["pick_key"]
    offset_key = ctx["offset_key"]
    mode_k = ctx["mode_k"]
    anc_k = ctx["anc_k"]
    aid_sel = ctx["aid_sel"]
    modo_novo = ctx["modo_novo"]
    dis_ag = ctx["dis_ag"]

    st.markdown("##### Agendamentos do Cliente")

    if modo_novo:
        st.checkbox(
            "Liberar edição do Agendamento Selecionado",
            value=True,
            disabled=True,
            key=f"cag_lib_ag_edit_novo_ph_{fv}",
        )
    else:
        st.checkbox(
            "Liberar edição do Agendamento Selecionado",
            key="cag_lib_ag_edit",
        )
        dis_ag = not bool(st.session_state.get("cag_lib_ag_edit"))

    modo = str(st.session_state.get(mode_k) or "Semanal")
    anchor: date = st.session_state[anc_k]
    if modo not in ("Semanal", "Mensal"):
        modo = "Semanal"
        st.session_state[mode_k] = modo

    st.radio(
        "Período de visualização do calendário",
        ["Semanal", "Mensal"],
        horizontal=True,
        key=mode_k,
    )
    modo = str(st.session_state.get(mode_k) or "Semanal")
    vis_lbl = "Visão Semanal" if modo == "Semanal" else "Visão Mensal"
    st.markdown(f"##### Calendário ({vis_lbl})")

    if modo == "Semanal":
        mon, sun = _cag_week_range(anchor)
        period_lbl = f"{mon.strftime('%d/%m')} — {sun.strftime('%d/%m/%Y')}"
        prev_lab, next_lab = "Semana Anterior", "Semana Seguinte"
        d_de, d_ate = mon.isoformat(), sun.isoformat()
    else:
        mon, sun = _cag_month_bounds(anchor)
        period_lbl = f"{mon.strftime('%d/%m/%Y')} — {sun.strftime('%d/%m/%Y')}"
        prev_lab, next_lab = "Mês Anterior", "Mês Seguinte"
        d_de, d_ate = mon.isoformat(), sun.isoformat()

    cnav1, cnav2, cnav3 = st.columns([1, 2, 1])
    with cnav1:
        if st.button(prev_lab, key=f"cag_cal_prev_{cliente_id}_{fv}"):
            if modo == "Semanal":
                st.session_state[anc_k] = anchor - timedelta(days=7)
            else:
                st.session_state[anc_k] = _cag_shift_month(anchor, -1)
            st.rerun()
    with cnav2:
        st.markdown(
            f"<div style='text-align:center;font-weight:600;color:#2D332F;'>{html.escape(period_lbl)}</div>",
            unsafe_allow_html=True,
        )
    with cnav3:
        if st.button(next_lab, key=f"cag_cal_next_{cliente_id}_{fv}"):
            if modo == "Semanal":
                st.session_state[anc_k] = anchor + timedelta(days=7)
            else:
                st.session_state[anc_k] = _cag_shift_month(anchor, 1)
            st.rerun()

    cal_rows = listar_agendamentos(
        data_de=d_de,
        data_ate=d_ate,
        cliente_ids=[int(cliente_id)],
    )
    if modo == "Semanal":
        cal_html = _cag_week_cal_table_html(mon=mon, week_rows=cal_rows)
    else:
        cal_html = _cag_month_cal_table_html(ref=mon, month_rows=cal_rows)
    st.markdown(f'<div class="bea-proto-scope">{cal_html}</div>', unsafe_allow_html=True)

    st.markdown("##### Dados do Agendamento")

    colabs_all = listar_colaboradores_resumo()
    col_opts = [c[0] for c in colabs_all]
    col_lbl = {c[0]: c[1] for c in colabs_all}

    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1:
        st.date_input(
            "Data (dd/mm/aaaa)",
            key="cag_ag_data",
            format="DD/MM/YYYY",
            disabled=dis_ag,
        )
    with r1c2:
        st.text_input("Hora início (HH:MM)", key="cag_ag_hi", disabled=dis_ag, placeholder="09:00")
    with r1c3:
        st.text_input("Hora fim (HH:MM)", key="cag_ag_hf", disabled=dis_ag, placeholder="10:00")

    all_srv = listar_servicos_para_venda()

    r2c1, r2c2, r2c3, r2c4 = st.columns([1.05, 1.25, 1.45, 1.1], gap="small")
    with r2c1:
        if modo_novo:
            naturezas_opts = list(NATUREZAS_CATALOGO_FASE3)
            st.selectbox("Natureza", naturezas_opts, key="cag_ag_natureza", disabled=dis_ag)
        else:
            ag_cur = obter_agendamento(int(aid_sel)) if aid_sel is not None else None
            nat_cur = str(ag_cur.get("servico_natureza") or "") if ag_cur else ""
            st.selectbox(
                "Natureza",
                [nat_cur] if nat_cur else ["—"],
                disabled=True,
                key=f"cag_ag_nat_combo_{aid_sel}_{fv}",
            )
    with r2c2:
        if modo_novo:
            nat = str(st.session_state.get("cag_ag_natureza") or "Sessão")
            filtrados = [s for s in all_srv if str(s.get("natureza")) == nat]
            choices = [f"{int(s['id'])}|{s['nome']}" for s in filtrados]
            if not choices:
                st.caption("—")
                st.session_state.cag_ag_servico_esc = ""
            else:
                if "cag_ag_servico_esc" not in st.session_state or (
                    st.session_state.cag_ag_servico_esc not in choices
                ):
                    st.session_state.cag_ag_servico_esc = choices[0]
                st.selectbox("Serviço", options=choices, key="cag_ag_servico_esc", disabled=dis_ag)
        else:
            ag_cur2 = obter_agendamento(int(aid_sel)) if aid_sel is not None else None
            srv_cur = str(ag_cur2.get("servico_nome") or "") if ag_cur2 else ""
            st.selectbox(
                "Serviço",
                [srv_cur] if srv_cur else ["—"],
                disabled=True,
                key=f"cag_ag_srv_combo_{aid_sel}_{fv}",
            )
    with r2c3:
        st.multiselect(
            "Colaborador(es)",
            options=col_opts,
            format_func=lambda i: col_lbl.get(int(i), str(i)),
            key="cag_ag_colabs",
            disabled=dis_ag,
        )
    with r2c4:
        ag_cur3 = obter_agendamento(int(aid_sel)) if aid_sel is not None else None
        opts_st = _cag_opcoes_status_edicao(str(ag_cur3["status"]) if ag_cur3 else "AGENDADO")
        cur_lbl = str(st.session_state.get("cag_ag_status_lbl") or "Agendado")
        if cur_lbl not in opts_st:
            opts_st.insert(0, cur_lbl)
        st.selectbox("Estado", opts_st, key="cag_ag_status_lbl", disabled=dis_ag)

    if not modo_novo:
        ag_cur4 = obter_agendamento(int(aid_sel)) if aid_sel is not None else None
        modo_cred = ag_cur4 and str(ag_cur4.get("modo_origem") or "") != "pre_venda"
        if modo_cred and str(st.session_state.get("cag_ag_status_lbl")) == "Cancelado":
            st.checkbox(
                "Devolver crédito ao buffer (saldo da linha de venda)",
                key="cag_ag_devolver_buffer",
                value=True,
                disabled=dis_ag,
            )

    st.text_area("Observações", key="cag_ag_obs", height=72, disabled=dis_ag)

    if st.button("Salvar Agendamento", type="secondary", key=f"cag_salvar_ag_{fv}", disabled=dis_ag):
        if not tem_cliente:
            st.warning("Carregue ou registe um cliente antes de gravar agendamentos.")
        else:
            d_ag = st.session_state.get("cag_ag_data")
            hi = str(st.session_state.get("cag_ag_hi") or "").strip()
            hf = str(st.session_state.get("cag_ag_hf") or "").strip()
            obs = str(st.session_state.get("cag_ag_obs") or "").strip()
            colab_ids = [int(x) for x in (st.session_state.get("cag_ag_colabs") or [])]

            if d_ag is None or not hasattr(d_ag, "isoformat"):
                st.error("Indique a data.")
            elif not colab_ids:
                st.error("Seleccione pelo menos um colaborador.")
            elif modo_novo:
                esc = str(st.session_state.get("cag_ag_servico_esc") or "")
                if "|" not in esc:
                    st.error("Seleccione um serviço válido.")
                else:
                    sid = int(esc.split("|", 1)[0])
                    d_iso = d_ag.isoformat()
                    ok, msg = criar_agendamento_pre_venda(
                        int(cliente_id),
                        sid,
                        d_iso,
                        hi,
                        hf,
                        colab_ids,
                        obs,
                        None,
                    )
                    if ok:
                        new_id = _cag_ag_parse_novo_id(msg)
                        if new_id is not None:
                            st.session_state.cag_ag_last_created_id = new_id
                        st.session_state.cag_ag_flash = "Informações salvas com sucesso."
                        st.session_state.cag_ag_pending_novo_dialog = "ask"
                        st.session_state[offset_key] = 0
                        st.rerun()
                    else:
                        st.error(msg)
            else:
                assert aid_sel is not None
                ag0 = obter_agendamento(int(aid_sel))
                if not ag0:
                    st.error("Agendamento não encontrado.")
                else:
                    status_lbl = str(st.session_state.get("cag_ag_status_lbl") or "")
                    status_new = _cag_status_lbl_para_db(status_lbl)
                    d_iso = d_ag.isoformat()
                    dev_buf = bool(st.session_state.get("cag_ag_devolver_buffer", True))
                    if str(ag0.get("modo_origem") or "") == "pre_venda":
                        dev_buf = False
                    cancel_trans = status_new == "CANCELADO" and str(ag0["status"]) != "CANCELADO"
                    is_b = cancel_trans and _cag_pagamento_pago_ou_parcial(
                        str(ag0.get("pagamento") or "")
                    )
                    base_pl: dict[str, Any] = {
                        "cliente_id": int(cliente_id),
                        "fv": int(fv),
                        "pick_key": pick_key,
                        "aid_sel": int(aid_sel),
                        "d_iso": d_iso,
                        "hi": hi,
                        "hf": hf,
                        "obs": obs,
                        "colab_ids": colab_ids,
                        "status_lbl": status_lbl,
                        "status_new": status_new,
                        "dev_buf": dev_buf,
                        "converter_credito": False,
                        "saldo_choice": None,
                    }
                    if is_b:
                        st.session_state.cag_ag_wizard = {"step": "saldo", "payload": base_pl}
                    else:
                        st.session_state.cag_ag_wizard = {"step": "edit_alert", "payload": base_pl}
                    st.rerun()


def _cag_setor4_render_list_island(*, cliente_id: int, fv: int, ctx: dict[str, Any]) -> None:
    pick_key = ctx["pick_key"]
    offset_key = ctx["offset_key"]
    sort_col_k = ctx["sort_col_k"]
    sort_dir_k = ctx["sort_dir_k"]
    sort_sig_k = ctx["sort_sig_k"]

    st.caption("Para realizar qualquer alteração, selecione a linha do agendamento desejado.")

    st.session_state.setdefault(sort_col_k, "Data")
    st.session_state.setdefault(sort_dir_k, "Ascendente")
    st.selectbox(
        "Ordenar por coluna",
        ["Data", "Início", "Fim", "Serviço", "Estado"],
        key=sort_col_k,
    )
    sort_dir = st.radio(
        "Ordem",
        ["Ascendente", "Descendente"],
        horizontal=True,
        key=sort_dir_k,
    )
    sort_col = str(st.session_state.get(sort_col_k) or "Data")
    sort_asc = sort_dir == "Ascendente"
    sig_now = (sort_col, sort_dir)
    if st.session_state.get(sort_sig_k) != sig_now:
        st.session_state[offset_key] = 0
        st.session_state[sort_sig_k] = sig_now

    todos = listar_agendamentos(cliente_ids=[int(cliente_id)])
    todos_sorted = _cag_sort_ag_rows(todos, col=sort_col, asc=sort_asc)
    n = len(todos_sorted)
    page_size = 5
    n_pages = max(1, (n + page_size - 1) // page_size)
    if offset_key not in st.session_state:
        st.session_state[offset_key] = 0
    off = int(st.session_state[offset_key])
    if off >= n and n > 0:
        off = max(0, ((n - 1) // page_size) * page_size)
        st.session_state[offset_key] = off
    chunk = todos_sorted[off : off + page_size]

    lp1, lp2, lp3 = st.columns([1, 2, 1])
    with lp1:
        if st.button(
            "◀ Anterior (lista)",
            key=f"cag_ag_prev_{fv}",
            disabled=off <= 0,
        ):
            st.session_state[offset_key] = max(0, off - page_size)
            st.rerun()
    with lp2:
        st.caption(f"Página {off // page_size + 1} de {n_pages} · {n} registo(s)")
    with lp3:
        if st.button(
            "Seguinte (lista) ▶",
            key=f"cag_ag_next_{fv}",
            disabled=off + page_size >= n,
        ):
            st.session_state[offset_key] = min(max(0, n - page_size), off + page_size)
            st.rerun()

    if chunk:
        rows_html = [
            "<tr>"
            f"<td>{html.escape(_cag_format_data_pt(str(a['data_agendamento'])))}</td>"
            f"<td>{html.escape(str(a['hora_inicio']))}</td>"
            f"<td>{html.escape(str(a['hora_fim']))}</td>"
            f"<td>{html.escape(str(a['servico_nome']))}</td>"
            "<td>"
            f"{_cag_status_badge_html(str(a['status']), _CAG_STATUS_DB_TO_LBL.get(str(a['status']), str(a['status'])))}"
            "</td>"
            "</tr>"
            for a in chunk
        ]
    else:
        rows_html = [
            "<tr><td colspan='5' style='padding:10px;color:#64748B;font-size:0.9rem;'>"
            f"{html.escape('Sem agendamentos para este cliente.')}</td></tr>"
        ]
    table = (
        "<table style='width:100%;border-collapse:collapse;font-size:0.9rem;font-family:var(--cv-sans,Montserrat),sans-serif;'>"
        "<thead><tr>"
        "<th style='text-align:left;padding:6px;border-bottom:1px solid rgba(118,148,125,0.2);color:#2D332F;'>Data</th>"
        "<th style='text-align:left;padding:6px;border-bottom:1px solid rgba(118,148,125,0.2);color:#2D332F;'>Início</th>"
        "<th style='text-align:left;padding:6px;border-bottom:1px solid rgba(118,148,125,0.2);color:#2D332F;'>Fim</th>"
        "<th style='text-align:left;padding:6px;border-bottom:1px solid rgba(118,148,125,0.2);color:#2D332F;'>Serviço</th>"
        "<th style='text-align:left;padding:6px;border-bottom:1px solid rgba(118,148,125,0.2);color:#2D332F;'>Estado</th>"
        "</tr></thead><tbody>"
        + "".join(rows_html)
        + "</tbody></table>"
    )
    st.markdown(f'<div class="bea-proto-scope">{table}</div>', unsafe_allow_html=True)

    opt_vals: list[str] = ["__novo__"]
    opt_labels: list[str] = ["— Novo agendamento —"]
    for a in chunk:
        opt_vals.append(f"id:{int(a['id'])}")
        opt_labels.append(
            f"#{a['id']} · {_cag_format_data_pt(str(a['data_agendamento']))} · "
            f"{a['hora_inicio']}–{a['hora_fim']} · {str(a['servico_nome'])[:40]}"
        )

    def _label_for_val(v: str) -> str:
        try:
            i = opt_vals.index(v)
            return opt_labels[i]
        except ValueError:
            return opt_labels[0]

    if pick_key not in st.session_state or st.session_state[pick_key] not in opt_vals:
        st.session_state[pick_key] = "__novo__"
        st.session_state.cag_ag_need_hydrate = True
        st.rerun()

    def _cag_ag_pick_changed() -> None:
        st.session_state.cag_ag_need_hydrate = True

    st.selectbox(
        "Seleccionar agendamento (página actual)",
        options=opt_vals,
        key=pick_key,
        format_func=_label_for_val,
        on_change=_cag_ag_pick_changed,
    )


def _render_cag_setor4_gestao_agendamentos(*, cliente_id: int, fv: int, tem_cliente: bool) -> None:
    keys = _cag_setor4_agenda_keys(cliente_id=cliente_id, fv=fv)
    _cag_setor4_run_flash_wizards_pend(cliente_id=cliente_id, fv=fv, tem_cliente=tem_cliente, keys=keys)
    ctx = _cag_setor4_try_prepare_context(cliente_id=cliente_id, fv=fv, tem_cliente=tem_cliente, keys=keys)
    st.markdown(_cag_section_title_html("4. Agendamentos"), unsafe_allow_html=True)
    with st.container(border=True):
        if ctx is None:
            st.info(
                "Seleccione ou **registe** um cliente na secção **3. Dados Pessoais** para criar ou alterar agendamentos."
            )
        else:
            _cag_setor4_render_form_island(cliente_id=cliente_id, fv=fv, tem_cliente=tem_cliente, ctx=ctx)
    st.markdown(
        '<div class="bea-cv-cag-gap" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.markdown(_cag_section_title_html("Lista de agendamentos"), unsafe_allow_html=True)
        if ctx is None:
            st.caption("Seleccione ou registe um cliente para ver a listagem.")
        else:
            _cag_setor4_render_list_island(cliente_id=cliente_id, fv=fv, ctx=ctx)


def render_page_clientes_agendamentos(*, render_back_and_breadcrumb) -> None:
    inject_constituicao_cag_page()
    render_back_and_breadcrumb(
        ["Home", "Clientes e Agendamentos", "Cadastro"],
        back_key="bea_back_clientes_agendamentos",
    )
    st.markdown(
        '<h1 class="bea-cv-cag-h1">Cadastro de Clientes e Gestão de Agendamentos</h1>',
        unsafe_allow_html=True,
    )

    if "cag_form_v" not in st.session_state:
        st.session_state.cag_form_v = 0
    if "cag_edit_id" not in st.session_state:
        st.session_state.cag_edit_id = None
    st.session_state.setdefault("cag_n_emergency", 1)
    st.session_state.setdefault("cag_lib_edit", True)

    if st.session_state.pop("cag_busca_clear_pending", False):
        st.session_state["cag_busca_nif"] = ""
        st.session_state["cag_busca_email"] = ""
        st.session_state["cag_busca_tel_txt"] = ""
        st.session_state["cag_busca_docintl"] = False

    st.markdown(_cag_section_title_html("1. Pesquisa de Clientes"), unsafe_allow_html=True)

    with st.container(border=True):
        cag_busca_clicked = render_cliente_search_widget(
            key_prefix="cag_busca",
            button_type="secondary",
            minimal=True,
        )

    if cag_busca_clicked:
        nif_s = str(st.session_state.get("cag_busca_nif", "") or "").strip()
        em_s = str(st.session_state.get("cag_busca_email", "") or "").strip()
        tel_raw = str(st.session_state.get("cag_busca_tel_txt", "") or "").strip()
        use_tel = normalizar_telefone_legado_ou_e164(tel_raw) if tel_raw else ""
        busca_doc_intl = bool(st.session_state.get("cag_busca_docintl"))

        msg_err: str | None = None
        if not nif_s and not em_s and not tel_raw:
            msg_err = "Indique NIF, email ou telefone."
        elif em_s and not email_valido(em_s):
            msg_err = "❌ Email inválido para pesquisa."
        elif tel_raw and not use_tel:
            msg_err = "❌ Telefone inválido (ex.: +351912345678)."
        elif nif_s:
            ok_nf, msg_nf, _vx = normalizar_nif_armazenamento(
                nif_s, documento_identificacao_internacional=bool(busca_doc_intl)
            )
            if not ok_nf:
                msg_err = msg_nf
        if msg_err:
            st.error(msg_err)
        else:
            cands = buscar_clientes_por_nif_email_telefone(
                nif=nif_s,
                email=em_s,
                telefone=use_tel,
                documento_internacional=bool(busca_doc_intl),
            )
            if len(cands) == 0:
                st.warning("Nenhum cliente encontrado com estes critérios.")
                st.session_state.pop("cag_busca_cands", None)
            elif len(cands) == 1:
                cid = cands[0][0]
                data = obter_cliente_completo(cid)
                if not data:
                    st.error("Cliente não encontrado.")
                else:
                    st.session_state.cag_edit_id = cid
                    st.session_state.cag_form_v += 1
                    st.session_state.pop("cag_busca_cands", None)
                    st.session_state.cag_busca_clear_pending = True
                    st.session_state.cag_cli_carregado_pesquisa = True
                    st.success(f"Cliente encontrado (#{cid}). Pesquisa limpa para nova consulta.")
                    st.rerun()
            else:
                st.session_state.cag_busca_cands = cands
                st.rerun()

    cands_m = st.session_state.get("cag_busca_cands")
    if cands_m and len(cands_m) > 1:
        st.markdown(
            '<div class="bea-cv-cag-h2" style="font-size:1.05rem;margin:0.6rem 0 0.35rem 0;">Resultados</div>',
            unsafe_allow_html=True,
        )
        n_c = len(cands_m)
        for row_start in range(0, n_c, 3):
            cols = st.columns(3)
            for i in range(3):
                ix = row_start + i
                if ix >= n_c:
                    break
                cid, nome = cands_m[ix]
                nome_e = html.escape(str(nome))
                sub_e = html.escape(f"#{cid}")
                with cols[i]:
                    with st.container(border=True):
                        st.markdown(
                            _html_cli_result_card(nome_e=nome_e, sub_e=sub_e),
                            unsafe_allow_html=True,
                        )
                        if st.button("Carregar ficha", key=f"cag_cand_load_{cid}", width="stretch"):
                            data = obter_cliente_completo(cid)
                            if not data:
                                st.error("Cliente não encontrado.")
                            else:
                                st.session_state.cag_edit_id = cid
                                st.session_state.cag_form_v += 1
                                st.session_state.pop("cag_busca_cands", None)
                                st.session_state.cag_busca_clear_pending = True
                                st.session_state.cag_cli_carregado_pesquisa = True
                                st.success(f"Cliente #{cid} selecionado. Pesquisa limpa.")
                                st.rerun()

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    st.markdown(_cag_section_title_html("2. Resumo do Cliente"), unsafe_allow_html=True)

    eid = st.session_state.cag_edit_id
    cli_data: dict | None = None
    if eid is not None:
        cli_data = obter_cliente_completo(int(eid))
        if cli_data is None:
            st.warning("Cliente seleccionado já não existe na base. Limpe o ecrã e pesquise novamente.")

    resumo_ag = (
        obter_resumo_agendamentos_cliente_setor2_proposta(int(eid))
        if eid is not None
        else obter_resumo_agendamentos_cliente_setor2_proposta(0)
    )

    _render_cag_setor2_dados_pessoais(cli=cli_data)
    _render_cag_setor2_resumo_agendamentos(resumo=resumo_ag)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if st.button("Limpar Informações Apresentadas", key="cag_btn_limpar_tela", type="secondary"):
        _reset_cag_page_state()
        st.rerun()

    fv = int(st.session_state.cag_form_v)
    fk = f"cag_{fv}"
    tem_cliente = eid is not None and cli_data is not None

    if tem_cliente:
        sig = (int(eid), fv)
        if st.session_state.get("cag_ficha_loaded_sig") != sig and cli_data is not None:
            _cag_carregar_ficha(fk, cli_data)
            st.session_state.cag_ficha_loaded_sig = sig
            st.session_state.cag_ag_hidr_pick = None
            if st.session_state.get("cag_cli_carregado_pesquisa"):
                st.session_state.cag_lib_edit = False
                st.session_state._cag_lib_edit_prev = False
            else:
                st.session_state.cag_lib_edit = True
                st.session_state._cag_lib_edit_prev = True
    else:
        _cag_garantir_defaults_formulario_vazio(fk)
        st.session_state.pop("cag_ficha_loaded_sig", None)

    cid_ag = int(eid) if tem_cliente else 0
    keys = _cag_setor4_agenda_keys(cliente_id=cid_ag, fv=fv)

    st.markdown(
        '<div class="bea-cv-cag-gap" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        _render_cag_setor3_dados_pessoais_completo(
            fk=fk,
            tem_cliente=tem_cliente,
            eid=int(eid) if tem_cliente else None,
        )
        st.markdown(_cag_section_title_html("4. Agendamentos"), unsafe_allow_html=True)
        _cag_setor4_run_flash_wizards_pend(cliente_id=cid_ag, fv=fv, tem_cliente=tem_cliente, keys=keys)
        ctx = _cag_setor4_try_prepare_context(cliente_id=cid_ag, fv=fv, tem_cliente=tem_cliente, keys=keys)
        if ctx is None:
            st.info(
                "Seleccione ou **registe** um cliente na secção **3. Dados Pessoais** "
                "para criar ou alterar agendamentos."
            )
        else:
            _cag_setor4_render_form_island(cliente_id=cid_ag, fv=fv, tem_cliente=tem_cliente, ctx=ctx)

    st.markdown(
        '<div class="bea-cv-cag-gap" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.markdown(_cag_section_title_html("Lista de agendamentos"), unsafe_allow_html=True)
        if ctx is None:
            st.caption("Seleccione ou registe um cliente para ver a listagem.")
        else:
            _cag_setor4_render_list_island(cliente_id=cid_ag, fv=fv, ctx=ctx)
