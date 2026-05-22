"""Consolidação Clientes + Agendamentos — Setores 1, 2, 3 (dados pessoais) e Setor 4 (agenda)."""

from __future__ import annotations

import html
import re
from calendar import monthcalendar, monthrange
from datetime import date, datetime, timedelta
from typing import Any, Literal, cast

import pandas as pd
import streamlit as st

from src.pages.theme import get_beaba_css  # noqa: F401 — BeaBa Sereno (CSS em app.main)
from src.modules.agendamento import (
    agendamento_elegivel_conversao_para_pacote_hoje,
    alterar_status,
    analisar_sessoes_pacote_pendentes_cag,
    atualizar_agendamento,
    cancelar_agendamento,
    converter_agendamento_avulso_para_consumo_pacote,
    criar_agendamento,
    criar_agendamento_pre_venda,
    listar_agendamentos,
    listar_buckets_pacote_com_saldo_disponivel,
    listar_opcoes_servicos_adquiridos_pendente_pre_agendamento,
    obter_agendamento,
    obter_resumo_agendamentos_cliente_setor2_proposta,
    validar_tipo_atendimento_e_sala,
)
from src.modules.catalogo import (
    listar_servicos_para_venda,
    listar_sessoes_do_pacote_catalogo,
    obter_duracao_referencia_agendamento_horas,
    obter_servico_para_formulario,
)
from src.modules.cliente import (
    atualizar_cliente,
    buscar_cliente_por_whatsapp,
    buscar_clientes_por_nif_email_telefone,
    buscar_clientes_por_prefixo_nome,
    cadastrar_cliente,
    obter_cliente_completo,
)
from src.modules.colaborador import listar_colaboradores_mapa_equipa, nome_colaborador_sem_sufixo_id_ui
from src.modules.constants import (
    ESTADO_AGENDAMENTO_REALIZADO_PENDENTE_LABEL_PT,
    NATUREZAS_CATALOGO_FASE3,
    SEXOS,
)
from src.modules.nif import normalizar_nif_armazenamento
from src.modules.telefone import normalizar_telefone_legado_ou_e164
from src.modules.validators import email_valido, parse_data_iso
from src.ui.telefone_widgets import ler_e164_de_widgets, preencher_session_telefone_de_e164, render_grupo_telefone
from src.ui.theme import agenda_pagamento_dot, agenda_status_style, agenda_tipo_icon
from src.ui.constituicao_visual_shell import inject_constituicao_cag_page
from src.ui.home_cockpit_ui_helpers import cag_home_drill_banner_html
from src.ui.fmt_euro_constituicao import fmt_euro_centavos
from src.ui.widgets.cliente_search import CLIENTE_SEARCH_DATE_MIN, render_cliente_search_widget

_CAG_PREFIX = "cag_"
_CAG_FICHA_FLASH_KEY = "cag_ficha_save_flash"

# Novo agendamento (pré-venda) neste ecrã: todas as naturezas excepto Produto.
_CAG_NATUREZAS_AGENDA_NOVO: tuple[str, ...] = tuple(
    n for n in NATUREZAS_CATALOGO_FASE3 if n != "Produto"
)

# Linha 1 de «Dados do Agendamento»: SAP · Natureza · Especialidades · Serviço · Colaboradores · Estado.
_CAG_ESP_PLACEHOLDER = "— Escolher especialidade —"
_CAG_ESP_SEM_LABEL = "(Sem especialidade)"
_CAG_SVC_PLACEHOLDER = "— Escolher serviço —"
_CAG_DADOS_AG_L1_COL_WIDTHS: tuple[float, float, float, float, float, float] = (
    1.08,
    0.82,
    0.82,
    1.02,
    1.22,
    0.84,
)
_CAG_SAP_TBL_COL_DATA = "Data do Registo"
_CAG_SAP_TBL_COL_CLIENTE = "Nome do Cliente"
_CAG_SAP_TBL_COL_NAT = "Natureza"
_CAG_SAP_TBL_COL_ESP = "Especialidade"
_CAG_SAP_TBL_COL_SVC = "Serviço"
_CAG_SAP_TBL_COL_PKG = "Nome do Pacote"
_CAG_SAP_TBL_COL_PAY = "Status do Pagamento"


def _cag_natureza_cmp_key(label: str) -> str:
    """Alinha rótulo da UI com `servicos.natureza` (espaços, capitalização, legado Pacote→Pack)."""
    from src.modules.constants import canon_natureza_catalogo

    return canon_natureza_catalogo(label).casefold()


def _cag_ag_build_esp_labels_ui(filtrados: list[dict[str, str | int]]) -> list[str]:
    esp_nonempty = sorted(
        {
            str(s.get("especialidade") or "").strip()
            for s in filtrados
            if str(s.get("especialidade") or "").strip()
        }
    )
    esp_sem = any(not str(s.get("especialidade") or "").strip() for s in filtrados)
    opts: list[str] = []
    if esp_nonempty:
        opts.extend(esp_nonempty)
    if esp_sem:
        opts.append(_CAG_ESP_SEM_LABEL)
    return [_CAG_ESP_PLACEHOLDER] + opts


def _cag_ag_filtrar_servicos_por_especialidade(
    filtrados: list[dict[str, str | int]], esp_lbl: str
) -> list[dict[str, str | int]]:
    if not esp_lbl or esp_lbl.strip() == "" or esp_lbl == _CAG_ESP_PLACEHOLDER:
        return []
    if esp_lbl == _CAG_ESP_SEM_LABEL:
        return [s for s in filtrados if not str(s.get("especialidade") or "").strip()]
    return [s for s in filtrados if str(s.get("especialidade") or "").strip() == esp_lbl]


def _cag_ag_sync_especialidade_state_de_servico_esc(esc: str) -> None:
    """Actualiza `cag_ag_especialidade_esc` a partir de `id|nome` do catálogo (SAP / estado)."""
    if "|" not in esc:
        st.session_state.pop("cag_ag_especialidade_esc", None)
        return
    try:
        sid = int(esc.split("|", 1)[0])
    except ValueError:
        st.session_state.pop("cag_ag_especialidade_esc", None)
        return
    if sid < 1:
        st.session_state.pop("cag_ag_especialidade_esc", None)
        return
    row = obter_servico_para_formulario(int(sid))
    if not row:
        st.session_state.pop("cag_ag_especialidade_esc", None)
        return
    en = str(row.get("especialidade_nome") or "").strip()
    st.session_state.cag_ag_especialidade_esc = en if en else _CAG_ESP_SEM_LABEL


def _cag_ag_sync_especialidade_de_sessao_pacote_escolhida() -> None:
    """Com Natureza=Pacote, alinha «Especialidades» (e cadeia) ao serviço da sessão em `cag_ag_pacote_sessao_esc`."""
    if not _cag_ag_ui_natureza_e_pacote():
        return
    pesc = str(st.session_state.get("cag_ag_pacote_sessao_esc") or "")
    _ps, sid_sess = _cag_parse_pacote_sessao_esc_val(pesc)
    if sid_sess is None or int(sid_sess) < 1:
        return
    row = obter_servico_para_formulario(int(sid_sess))
    if not row:
        return
    en = str(row.get("especialidade_nome") or "").strip()
    st.session_state.cag_ag_especialidade_esc = en if en else _CAG_ESP_SEM_LABEL
    st.session_state.cag_ag_chain_especialidade = str(
        st.session_state.get("cag_ag_especialidade_esc") or _CAG_ESP_PLACEHOLDER
    )


def _cag_ag_sync_servico_esc_de_sessao_pacote_escolhida() -> None:
    """Com Natureza=Pacote, alinha «Serviço» ao `sessao_servico_id` da linha em `cag_ag_pacote_sessao_esc`."""
    if not _cag_ag_ui_natureza_e_pacote():
        return
    pesc = str(st.session_state.get("cag_ag_pacote_sessao_esc") or "")
    _ps, sid_sess = _cag_parse_pacote_sessao_esc_val(pesc)
    if sid_sess is None or int(sid_sess) < 1:
        return
    row = obter_servico_para_formulario(int(sid_sess))
    if not row:
        return
    nm = str(row.get("nome") or "").strip() or "—"
    st.session_state.cag_ag_servico_esc = f"{int(sid_sess)}|{nm}"


def _cag_df_selected_rows(ev: object | None, session_key: str) -> list[int]:
    """Índices de linha seleccionada (Streamlit ≥ 1.33 `st.dataframe` com `on_select`)."""
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


def _cag_init_calendar_anchor(anc_k: str) -> None:
    """Primeira âncora do calendário; consome `cag_home_calendar_seed_month` vinda do cockpit."""
    if anc_k in st.session_state:
        return
    seed = st.session_state.pop("cag_home_calendar_seed_month", None)
    if isinstance(seed, dict):
        try:
            y = int(seed.get("y", seed.get("year", 0)))
            m = int(seed.get("m", seed.get("month", 0)))
            st.session_state[anc_k] = date(y, m, 1)
            return
        except (ValueError, TypeError):
            pass
    st.session_state[anc_k] = date.today()


def _cag_section_title_html(title: str) -> str:
    """Título de secção — serifado Master (#2D332F)."""
    t = html.escape(title)
    return f'<div class="bea-cv-cag-h2">{t}</div>'

_CAG_STATUS_DB_TO_LBL: dict[str, str] = {
    "PRE_AGENDADO": "Pré-agendado",
    "AGENDADO": "Agendado",
    "CONFIRMADO": "Confirmado",
    "REALIZADO_PENDENTE_PGTO": ESTADO_AGENDAMENTO_REALIZADO_PENDENTE_LABEL_PT,
    "CONCLUIDO": "Concluído",
    "CANCELADO": "Cancelado",
}

_CAG_AG_LIST_COL_DATA = "Data do Agendamento"
_CAG_AG_LIST_COL_PAGAMENTO = "Status do Pagamento"
_CAG_AG_LIST_COL_COLABORADOR = "Colaborador"
_CAG_AG_LIST_COL_CRIACAO = "Criação do Registo"
CAG_AG_LIST_PAGE_SIZE = 10


# Uma única chave para o select «Estado» no formulário. Chaves por `aid` faziam o utilizador
# editar `cag_ag_status_lbl_novo` (modo novo) enquanto o «Salvar» lia `cag_ag_status_lbl_{id}`
# → valor vazio → sempre AGENDADO + ramo errado de gravação.
CAG_AG_STATUS_UI_KEY = "cag_ag_status_edit_lbl"
# ID do serviço de catálogo do **pacote** (natureza Pacote); distinto de `cag_ag_servico_esc` quando este reflecte a sessão.
CAG_AG_PACOTE_CATALOG_SERVICO_ID_KEY = "cag_ag_pacote_catalog_servico_id"

StatusAg = Literal[
    "PRE_AGENDADO",
    "AGENDADO",
    "CONFIRMADO",
    "REALIZADO_PENDENTE_PGTO",
    "CONCLUIDO",
    "CANCELADO",
]


def _cag_status_lbl_para_db(lbl: str) -> str:
    t = " ".join(str(lbl or "").strip().split())
    rev = {v: k for k, v in _CAG_STATUS_DB_TO_LBL.items()}
    if t in rev:
        return rev[t]
    tl = t.lower()
    for k, v in _CAG_STATUS_DB_TO_LBL.items():
        if v.lower() == tl:
            return k
    return "AGENDADO"


def _cag_format_data_pt(iso_d: str) -> str:
    s = str(iso_d)[:10]
    try:
        d = datetime.strptime(s, "%Y-%m-%d").date()
        return d.strftime("%d/%m/%Y")
    except ValueError:
        return s


def _cag_format_criacao_registo_pt(raw: str | None) -> str:
    s = (raw or "").strip()
    if not s:
        return "—"
    s10 = s[:10]
    try:
        d = datetime.strptime(s10, "%Y-%m-%d").date()
        base = d.strftime("%d/%m/%Y")
    except ValueError:
        return s if s else "—"
    if len(s) >= 16 and s[10] in (" ", "T"):
        hm = s[11:16].strip()
        if len(hm) >= 4:
            return f"{base} {hm}"
    return base


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


def _cag_aplicar_linha_servico_adquirido_pendente(
    rows: list[dict[str, Any]], token: str
) -> None:
    """Preenche Natureza, Especialidade, Serviço, colaboradores e estado a partir da linha SAP seleccionada."""
    row = next((x for x in rows if x.get("token") == token), None)
    if not row:
        st.session_state.pop("cag_ag_credito_vi_id", None)
        st.session_state.pop("cag_ag_credito_ps_id", None)
        st.session_state.pop("cag_ag_especialidade_esc", None)
        st.session_state.pop("cag_ag_chain_natureza", None)
        st.session_state.pop("cag_ag_chain_especialidade", None)
        st.session_state.pop(CAG_AG_PACOTE_CATALOG_SERVICO_ID_KEY, None)
        return
    st.session_state.cag_ag_credito_vi_id = int(row["venda_item_id"])
    ps = row.get("pacote_sessao_id")
    if ps is not None:
        st.session_state.cag_ag_credito_ps_id = int(ps)
    else:
        st.session_state.pop("cag_ag_credito_ps_id", None)
    st.session_state.cag_ag_natureza = str(row.get("natureza") or "Sessão")
    st.session_state.cag_ag_servico_esc = str(row.get("servico_esc") or "")
    nat_row = str(st.session_state.cag_ag_natureza or "")
    if _cag_natureza_cmp_key(nat_row) == _cag_natureza_cmp_key("Pack"):
        try:
            scid = int(row.get("servico_catalog_id") or 0)
        except (TypeError, ValueError):
            scid = 0
        if scid < 1 and "|" in str(st.session_state.cag_ag_servico_esc or ""):
            try:
                scid = int(str(st.session_state.cag_ag_servico_esc).split("|", 1)[0])
            except ValueError:
                scid = 0
        if scid > 0:
            st.session_state[CAG_AG_PACOTE_CATALOG_SERVICO_ID_KEY] = int(scid)
        else:
            st.session_state.pop(CAG_AG_PACOTE_CATALOG_SERVICO_ID_KEY, None)
        # A especialidade correcta vem da sessão do pacote (`cag_ag_pacote_sessao_esc`), não do serviço-pacote.
        st.session_state.pop("cag_ag_especialidade_esc", None)
    else:
        st.session_state.pop(CAG_AG_PACOTE_CATALOG_SERVICO_ID_KEY, None)
        _cag_ag_sync_especialidade_state_de_servico_esc(str(st.session_state.cag_ag_servico_esc))
    st.session_state.cag_ag_chain_natureza = str(st.session_state.cag_ag_natureza or "")
    st.session_state.cag_ag_chain_especialidade = str(
        st.session_state.get("cag_ag_especialidade_esc") or _CAG_ESP_PLACEHOLDER
    )
    pesc = row.get("pacote_sessao_esc")
    if pesc:
        st.session_state.cag_ag_pacote_sessao_esc = str(pesc)
    else:
        st.session_state.pop("cag_ag_pacote_sessao_esc", None)
    st.session_state.cag_ag_colabs = []
    st.session_state[CAG_AG_STATUS_UI_KEY] = "Pré-agendado"
    st.session_state[_cag_ag_status_widget_key(None)] = "Pré-agendado"


def _cag_sincronizar_servicos_adquiridos_pendente(cliente_id: int) -> list[dict[str, Any]]:
    """Carrega linhas SAP; incrementa `cag_sap_df_v` quando o conjunto de tokens muda (tabela alinhada)."""
    rows = listar_opcoes_servicos_adquiridos_pendente_pre_agendamento(int(cliente_id))
    st.session_state["_cag_ag_sap_rows_flat"] = rows
    sig = "|".join(str(r.get("token") or "") for r in rows)
    if st.session_state.get("cag_sap_rows_sig") != sig:
        st.session_state.cag_sap_rows_sig = sig
        st.session_state["cag_sap_df_v"] = int(st.session_state.get("cag_sap_df_v", 0)) + 1
        st.session_state.pop("_cag_ag_sap_last_applied_tok", None)
    if not rows:
        st.session_state.pop("cag_ag_credito_vi_id", None)
        st.session_state.pop("cag_ag_credito_ps_id", None)
        st.session_state.pop("_cag_ag_sap_last_applied_tok", None)
    return rows


def _cag_sap_rows_para_dataframe(rows: list[dict[str, Any]]) -> pd.DataFrame:
    cols = [
        _CAG_SAP_TBL_COL_DATA,
        _CAG_SAP_TBL_COL_CLIENTE,
        _CAG_SAP_TBL_COL_NAT,
        _CAG_SAP_TBL_COL_ESP,
        _CAG_SAP_TBL_COL_SVC,
        _CAG_SAP_TBL_COL_PKG,
        _CAG_SAP_TBL_COL_PAY,
    ]
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(
        {
            _CAG_SAP_TBL_COL_DATA: [str(r.get("data_do_registo") or "—") for r in rows],
            _CAG_SAP_TBL_COL_CLIENTE: [str(r.get("cliente_nome") or "—") for r in rows],
            _CAG_SAP_TBL_COL_NAT: [str(r.get("natureza") or "—") for r in rows],
            _CAG_SAP_TBL_COL_ESP: [str(r.get("especialidade") or "—") for r in rows],
            _CAG_SAP_TBL_COL_SVC: [str(r.get("nome_servico_tabela") or "—") for r in rows],
            _CAG_SAP_TBL_COL_PKG: [str(r.get("nome_pacote_tabela") or "—") for r in rows],
            _CAG_SAP_TBL_COL_PAY: [str(r.get("status_pagamento") or "—") for r in rows],
        }
    )


def _cag_opt_pos_int(v: object) -> int | None:
    if v is None:
        return None
    try:
        n = int(v)
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def _cag_credito_venda_item_ainda_pendente_na_lista(
    cliente_id: int,
    vi_id: int,
    ps_id: int | None,
    ss: Any,
) -> bool:
    esc = str(ss.get("cag_ag_servico_esc") or "")
    pesc = str(ss.get("cag_ag_pacote_sessao_esc") or "")
    for op in listar_opcoes_servicos_adquiridos_pendente_pre_agendamento(int(cliente_id)):
        if int(op["venda_item_id"]) != int(vi_id):
            continue
        op_ps = op.get("pacote_sessao_id")
        if (int(op_ps) if op_ps is not None else None) != (
            int(ps_id) if ps_id is not None else None
        ):
            continue
        op_tok = str(op.get("token") or "")
        op_pkg_agg = (
            _cag_natureza_cmp_key(str(op.get("natureza") or "")) == _cag_natureza_cmp_key("Pack")
            and op_tok.endswith("|pkg")
        )
        if not op_pkg_agg and esc != str(op.get("servico_esc") or ""):
            continue
        if op.get("pacote_sessao_esc"):
            if pesc != str(op.get("pacote_sessao_esc") or ""):
                continue
        else:
            if pesc and not op_pkg_agg:
                continue
        return True
    return False


def _cag_colaboradores_lista_texto(ag: dict[str, Any]) -> str:
    """Nomes dos colaboradores do agendamento, só texto (sem identificadores internos)."""
    nomes = [
        nome_colaborador_sem_sufixo_id_ui(n)
        for n in (ag.get("colaboradores_nomes") or [])
        if str(n).strip()
    ]
    nomes = [n for n in nomes if n]
    return ", ".join(nomes) if nomes else "—"


def _cag_colab_multiselect_label(col_lbl: dict[int, str], opt_id: int) -> str:
    """Rótulo do multiselect: apenas o nome vindo do catálogo de colaboradores."""
    return nome_colaborador_sem_sufixo_id_ui(col_lbl.get(int(opt_id))) or "—"


def _cag_tipo_atendimento_lista_label(db_val: str | None) -> str:
    t = str(db_val or "").strip().lower()
    if t == "virtual":
        return "Virtual"
    if t == "presencial":
        return "Presencial"
    s = str(db_val or "").strip()
    return s if s else "—"


def _cag_sort_ag_rows(
    rows: list[dict[str, Any]], *, col: str = "", asc: bool = True
) -> list[dict[str, Any]]:
    """Ordem estável (data, hora início, id), alinhada com `listar_agendamentos`. `col`/`asc` ignorados (compat.)."""
    _ = (col, asc)
    return sorted(
        rows,
        key=lambda x: (
            str(x.get("data_agendamento") or ""),
            str(x.get("hora_inicio") or ""),
            int(x.get("id") or 0),
        ),
    )


def _cag_list_offset_para_agendamento(
    *,
    cliente_id: int,
    aid: int,
    page_size: int = CAG_AG_LIST_PAGE_SIZE,
) -> int:
    """`offset_key` da página da tabela que contém o agendamento (mesma ordenação que a listagem)."""
    raw = listar_agendamentos(cliente_ids=[int(cliente_id)])
    ordered = _cag_agrupar_listagem_cancelados_mesmo_pacote(raw)
    ps = max(1, int(page_size))
    for i, row in enumerate(ordered):
        rid = int(row["id"])
        grp = [int(x) for x in (row.get("_cag_lista_pacote_ids_agrupados") or [])]
        if rid == int(aid) or int(aid) in grp:
            return (i // ps) * ps
    return 0


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


def _cag_resolve_aid_edit_from_pick(*, cliente_id: int, pick_key: str) -> int | None:
    """Id do agendamento seleccionado na lista / sticky, ou None (fluxo novo / sem seleção)."""
    raw_pk = str(st.session_state.get(pick_key) or "__novo__")
    aid_edit: int | None = None
    if raw_pk.startswith("id:"):
        try:
            aid_edit = int(raw_pk.split(":", 1)[1])
        except ValueError:
            aid_edit = None
    if aid_edit is None:
        stx = st.session_state.get("cag_ag_sticky_aid")
        if stx is not None:
            try:
                cand = int(stx)
                ag_sc = obter_agendamento(cand)
                if ag_sc and int(ag_sc.get("cliente_id") or 0) == int(cliente_id):
                    aid_edit = cand
            except (TypeError, ValueError):
                pass
    return aid_edit


def _cag_ag_commit_wizard_payload(payload: dict[str, Any]) -> tuple[bool, str, str]:
    """Returns (ok, user_message, flash_extra). flash_extra may augment success toast."""
    aid_sel = payload.get("aid_sel")
    if aid_sel is None:
        return False, "Agendamento inválido.", ""
    aid_i = int(aid_sel)
    ag0 = obter_agendamento(aid_i)
    if not ag0:
        return False, "Agendamento não encontrado.", ""

    d_iso = str(payload.get("d_iso") or "")
    hi = str(payload.get("hi") or "").strip()
    hf = str(payload.get("hf") or "").strip()
    obs = str(payload.get("obs") or "").strip()
    colab_ids = [int(x) for x in (payload.get("colab_ids") or [])]

    # CORRIGIDO: usa sempre o status capturado no submit, nunca relê o widget
    # (no rerun do wizard o selectbox disabled reseta para o primeiro valor da lista)
    status_new = str(payload.get("status_new") or "AGENDADO")

    cancel_trans = status_new == "CANCELADO" and str(ag0["status"]) != "CANCELADO"
    if cancel_trans:
        dev_buf = bool(payload.get("dev_buf", True))
        if str(ag0.get("modo_origem") or "") == "pre_venda":
            dev_buf = False
        conv = bool(payload.get("converter_credito", False))
        ok_c, msg_c = cancelar_agendamento(
            aid_i,
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

    tipo_db = str(payload.get("tipo_atendimento") or "presencial")
    sala_raw = payload.get("sala_virtual_disponibilizada")
    sala_typed: int | None = None if sala_raw is None else int(sala_raw)

    ok_u, msg_u = atualizar_agendamento(
        aid_i,
        data_agendamento=d_iso,
        hora_inicio=hi,
        hora_fim=hf,
        colaborador_ids=colab_ids,
        observacoes=obs,
        tipo_atendimento=tipo_db,
        sala_virtual_disponibilizada=sala_typed,
    )
    if not ok_u:
        return False, msg_u, ""

    if status_new != str(ag0["status"]) and status_new != "CANCELADO":
        ok_s, msg_s = alterar_status(aid_i, cast(StatusAg, status_new))
        if not ok_s:
            ok_rev, msg_rev = atualizar_agendamento(
                aid_i,
                data_agendamento=str(ag0.get("data_agendamento") or "")[:10],
                hora_inicio=str(ag0.get("hora_inicio") or ""),
                hora_fim=str(ag0.get("hora_fim") or ""),
                colaborador_ids=list(ag0.get("colaborador_ids") or []),
                observacoes=str(ag0.get("observacoes") or ""),
                tipo_atendimento=str(ag0.get("tipo_atendimento") or "presencial"),
                sala_virtual_disponibilizada=ag0.get("sala_virtual_disponibilizada"),
            )
            extra_rev = f" ({msg_rev})" if not ok_rev and msg_rev else ""
            return False, f"{msg_s} Alterações aos dados revertidas.{extra_rev}", ""
        if "⚠️" in msg_s or "REALIZADO_PENDENTE_PGTO" in msg_s:
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


_CAG_PENDING_LIB_AG_EDIT_KEY = "_cag_pending_lib_ag_edit"


def _cag_schedule_lib_ag_edit(val: bool) -> None:
    """Agenda `cag_lib_ag_edit` para o próximo rerun antes de qualquer widget com essa key.

    O diálogo «Novo agendamento» / assistente corre *depois* do `st.checkbox(key=cag_lib_ag_edit)`;
    alterar `cag_lib_ag_edit` na mesma execução gera StreamlitAPIException."""
    st.session_state[_CAG_PENDING_LIB_AG_EDIT_KEY] = bool(val)


def _cag_flush_pending_lib_ag_edit() -> None:
    if _CAG_PENDING_LIB_AG_EDIT_KEY not in st.session_state:
        return
    st.session_state.cag_lib_ag_edit = bool(st.session_state.pop(_CAG_PENDING_LIB_AG_EDIT_KEY))


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


def _cag_preencher_barra_busca_de_cliente(data: dict) -> None:
    st.session_state["cag_busca_nome"] = str(data.get("nome") or "")
    st.session_state["cag_busca_nif"] = str(data.get("nif_ou_documento") or "")
    st.session_state["cag_busca_email"] = str(data.get("email") or "")
    st.session_state["cag_busca_tel_txt"] = str(data.get("whatsapp") or "").strip()


def _cag_tratar_sugestao_nome_clicada(cid: int) -> None:
    data = obter_cliente_completo(int(cid))
    if not data:
        st.error("Cliente não encontrado.")
        return
    st.session_state.cag_edit_id = int(cid)
    st.session_state.cag_form_v += 1
    st.session_state.pop("cag_busca_cands", None)
    st.session_state.cag_cli_carregado_pesquisa = True
    _cag_preencher_barra_busca_de_cliente(data)


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
        "_cag_post_save_lib_edit",
        "_cag_reload_ficha_after_save",
    ):
        st.session_state.pop(k, None)
    st.session_state.cag_form_v = 0
    st.session_state.cag_edit_id = None


def _cag_metric_card_html(*, material_icon: str, title: str, body_html: str) -> str:
    """Card métrica resumo cliente — ícone 15% sálvia; título sans e valores em negrito (CSS shell)."""
    ic = html.escape(str(material_icon).strip())
    tit_e = html.escape(str(title).strip())
    return (
        '<div class="bea-cv-cag-metric-card">'
        '<div class="bea-cv-cag-metric-icon" aria-hidden="true">'
        f'<span class="material-symbols-outlined">{ic}</span></div>'
        f'<p class="bea-cv-cag-metric-title">{tit_e}</p>'
        f'<div class="bea-cv-cag-metric-body">{body_html}</div></div>'
    )


def _html_linhas_natureza(rows: list[tuple[str, int]]) -> str:
    if not rows:
        return '<p style="margin:0;color:#64748B;font-size:0.88rem;">—</p>'
    parts: list[str] = []
    for nat, q in rows:
        parts.append(
            "<p style='margin:3px 0;font-size:0.9rem;font-family:var(--cv-sans,Montserrat),sans-serif;'>"
            f"<span style='font-weight:600;color:#2D332F;'>{html.escape(nat)}</span>: "
            f"<span class='bea-cv-cag-metric-val' style='font-size:1rem'>{int(q)}</span></p>"
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
        "Agendamentos nos próximos 30 dias",
        "Agendamentos nos próximos 10 dias",
        "Pendências de Pagamento",
        "Saldo Acumulado",
        "Histórico de Cancelamento",
    )
    bodies = (
        _html_linhas_natureza(list(c30)),
        _html_linhas_natureza(list(c10)),
        _html_linhas_natureza(list(pend_n)),
        f'<p class="bea-cv-cag-metric-val">{html.escape(_cag_valor_moeda_centavos(pend_v))}</p>',
        f'<p class="bea-cv-cag-metric-val">{html.escape(str(n_can))}</p>',
    )
    icons = ("calendar_month", "event", "payments", "euro_symbol", "history")
    for col, lab, body, icon in zip(r1, labels, bodies, icons):
        with col:
            st.markdown(
                _cag_metric_card_html(material_icon=icon, title=lab, body_html=body),
                unsafe_allow_html=True,
            )


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
        _cag_ficha_set_flash("error", str(err_t or "Contacto inválido."))
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
                _cag_ficha_set_flash("error", str(err_e or "❌ Contacto de emergência incompleto."))
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
            # Não alterar `cag_lib_edit` aqui: o checkbox já foi instanciado neste rerun.
            st.session_state["_cag_post_save_lib_edit"] = not bool(
                st.session_state.get("cag_cli_carregado_pesquisa")
            )
            # Recarregar ficha no próximo rerun (antes dos widgets): aqui `cag_*_nome` etc. já estão ligados a widgets.
            st.session_state["_cag_reload_ficha_after_save"] = (fk, int(eid))
            _cag_ficha_set_flash("success", str(msg))
            st.rerun()
        else:
            _cag_ficha_set_flash("error", str(msg))
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
        _cag_ficha_set_flash("error", str(msg))
        return
    cid_new = buscar_cliente_por_whatsapp(tel_e164)
    if cid_new:
        st.session_state.cag_edit_id = int(cid_new)
        st.session_state.cag_form_v += 1
        st.session_state.cag_ficha_loaded_sig = None
        st.session_state.cag_ag_hidr_pick = None
        st.session_state.cag_cli_carregado_pesquisa = False
        _cag_ficha_set_flash("success", str(msg) + f" Cliente #{cid_new} seleccionado.")
        st.rerun()
    _cag_ficha_set_flash("success", str(msg))


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
            fk_grav = f"{fk}_gravida"
            _grav = str(st.session_state.get(fk_grav, "Não"))
            # Coluna do rádio estreita para o date_input ficar logo a seguir (mais à esquerda na linha).
            _cw_grav = [0.88, 1.02] if _grav == "Sim" else [1.0, 0.02]
            c_grav, c_parto = st.columns(_cw_grav, gap="small", vertical_alignment="center")
            with c_grav:
                st.radio(
                    "Está grávida? *",
                    ["Não", "Sim"],
                    horizontal=True,
                    key=fk_grav,
                    disabled=dis,
                )
            with c_parto:
                if str(st.session_state.get(fk_grav, "Não")) == "Sim":
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
            st.text_input("Freguesia", key=f"{fk}_freg", disabled=dis)
        r3c1, r3c2 = st.columns(2)
        with r3c1:
            st.text_input("Distrito (opcional)", key=f"{fk}_dist", disabled=dis)
        with r3c2:
            _pais_k = f"{fk}_pais"
            if _pais_k not in st.session_state:
                st.session_state[_pais_k] = "Portugal"
            st.text_input("País *", key=_pais_k, disabled=dis)

        st.markdown("##### Filhos")
        fk_temf = f"{fk}_temf"
        st.session_state.setdefault(fk_temf, "Não")
        st.markdown(
            "<p style='margin:0 0 0.45rem 0;padding:0;font-size:0.95rem;'>Possui Filhos? *</p>",
            unsafe_allow_html=True,
        )
        _temf = str(st.session_state.get(fk_temf, "Não"))
        # Coluna estreita para o rádio, coluna estreita para a quantidade (só com «Sim»); o resto não absorve largura.
        c_pf_rad, c_pf_qtd, _c_pf_pad = st.columns([0.52, 0.28, 3.2], gap="small", vertical_alignment="center")
        with c_pf_rad:
            st.radio(
                "Possui Filhos?",
                ["Não", "Sim"],
                horizontal=True,
                key=fk_temf,
                disabled=dis,
                label_visibility="collapsed",
            )
        with c_pf_qtd:
            if _temf == "Sim":
                st.number_input(
                    "Quantos filhos?",
                    min_value=1,
                    max_value=20,
                    step=1,
                    key=f"{fk}_qtd",
                    disabled=dis,
                    label_visibility="collapsed",
                )
        tem_filhos = str(st.session_state.get(fk_temf, "Não")) == "Sim"
        qtd = int(st.session_state.get(f"{fk}_qtd", 1) or 1) if tem_filhos else 0
        if tem_filhos:
            for j in range(qtd):
                st.markdown(f"**Filho {j + 1}**")
                cf1, cf2, cf3 = st.columns(3)
                with cf1:
                    st.text_input("Nome *", key=f"{fk}_f_nom_{j}", disabled=dis)
                with cf2:
                    st.session_state.setdefault(f"{fk}_f_id_{j}", 0)
                    st.number_input(
                        "Idade (anos) *",
                        min_value=0,
                        max_value=120,
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
        _ficha_flash = st.session_state.pop(_CAG_FICHA_FLASH_KEY, None)
        if isinstance(_ficha_flash, tuple) and len(_ficha_flash) == 2:
            _fk, _fm = _ficha_flash
            if _fk == "success":
                st.success(_fm)
            elif _fk == "error":
                st.error(_fm)


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


_CAG_AG_COLAB_OPTS_EMPTY_SENTINEL = -1


def _cag_ag_colab_opts_para_servico_id(servico_id: int | None) -> tuple[list[int], dict[int, str]]:
    """Colaboradores com habilitação em ``servico_id`` (lista vazia se serviço inválido ou sem elegíveis)."""
    if servico_id is None or int(servico_id) < 1:
        return [], {}
    rows = listar_colaboradores_mapa_equipa([int(servico_id)])
    col_opts = [int(r["id"]) for r in rows]
    col_lbl = {int(r["id"]): str(r.get("nome") or "") for r in rows}
    return col_opts, col_lbl


def _cag_sync_ag_tipo_sala_state() -> None:
    st.session_state.setdefault("cag_ag_tipo_atendimento", "Presencial")
    tipo = str(st.session_state.get("cag_ag_tipo_atendimento") or "Presencial")
    if tipo != "Virtual":
        st.session_state.cag_ag_sala_virtual = "—"
    else:
        sv = str(st.session_state.get("cag_ag_sala_virtual") or "")
        if sv not in ("Sim", "Não"):
            st.session_state.cag_ag_sala_virtual = "Não"


def _cag_ficha_set_flash(kind: Literal["success", "error"], msg: str) -> None:
    st.session_state[_CAG_FICHA_FLASH_KEY] = (kind, str(msg).strip())


def _cag_format_duracao_catalogo_horas(h: float) -> str:
    """Formato de duração do catálogo («Duração (HH:MM) *», ex.: 1:30h)."""
    x = round(max(0.25, min(24.0, float(h))) / 0.25) * 0.25
    s = f"{x:.2f}".replace(".", ",").rstrip("0").rstrip(",")
    return f"{s} h" if s else "0,25 h"


def _cag_parse_hhmm(s: str) -> tuple[int, int] | None:
    m = re.match(r"^\s*(\d{1,2}):(\d{2})\s*$", s or "")
    if not m:
        return None
    hh, mm = int(m.group(1)), int(m.group(2))
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        return None
    return hh, mm


def _cag_agrupar_listagem_cancelados_mesmo_pacote(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sessões do mesmo item de venda (pacote), todas canceladas → uma linha (nome do pacote, natureza Pacote).

    Evita triplicar linhas na tabela de Clientes + Agendamentos quando todas as sessões do pacote
    estão canceladas; o registo representativo mantém o menor `id` para selecção / hidratação.
    """
    ordered = _cag_sort_ag_rows(rows)
    by_key: dict[tuple[int, int], list[dict[str, Any]]] = {}
    loose: list[dict[str, Any]] = []
    for ag in ordered:
        vi = ag.get("venda_item_id")
        pkg = str(ag.get("nome_do_pacote") or "").strip()
        if (
            vi is not None
            and int(vi) > 0
            and pkg
            and pkg != "-"
            and str(ag.get("tipo_origem") or "").strip().lower() == "pacote"
        ):
            by_key.setdefault((int(ag["cliente_id"]), int(vi)), []).append(ag)
        else:
            loose.append(ag)
    out: list[dict[str, Any]] = []
    for _k, g in by_key.items():
        by_id: dict[int, dict[str, Any]] = {}
        for x in g:
            by_id[int(x["id"])] = x
        g2 = sorted(by_id.values(), key=lambda x: (str(x.get("hora_inicio") or ""), int(x.get("id") or 0)))
        all_cancel = all(str(x.get("status") or "").strip().upper() == "CANCELADO" for x in g2)
        if all_cancel and len(g2) >= 2:
            base = dict(g2[0])
            ids_g = [int(x["id"]) for x in g2]
            hid = min(ids_g)
            hi_pairs: list[tuple[int, tuple[int, int]]] = []
            hf_pairs: list[tuple[int, tuple[int, int]]] = []
            for x in g2:
                hi = _cag_parse_hhmm(str(x.get("hora_inicio") or ""))
                hf = _cag_parse_hhmm(str(x.get("hora_fim") or ""))
                if hi is not None:
                    hi_pairs.append((hi[0] * 60 + hi[1], hi))
                if hf is not None:
                    hf_pairs.append((hf[0] * 60 + hf[1], hf))
            if hi_pairs:
                _, hi_best = min(hi_pairs, key=lambda t: t[0])
                base["hora_inicio"] = f"{hi_best[0]:02d}:{hi_best[1]:02d}"
            if hf_pairs:
                _, hf_best = max(hf_pairs, key=lambda t: t[0])
                base["hora_fim"] = f"{hf_best[0]:02d}:{hf_best[1]:02d}"
            base["id"] = hid
            base["servico_nome"] = pkg
            base["servico_natureza"] = "Pack"
            base["_cag_lista_pacote_ids_agrupados"] = ids_g
            out.append(base)
        else:
            out.extend(g2)
    out.extend(loose)
    return _cag_sort_ag_rows(out)


def _cag_ids_agendamentos_lista_expandidos(rows: list[dict[str, Any]]) -> set[int]:
    """Ids reais na listagem (inclui membros de grupo pacote cancelado)."""
    s: set[int] = set()
    for ag in rows:
        s.add(int(ag["id"]))
        for x in ag.get("_cag_lista_pacote_ids_agrupados") or []:
            s.add(int(x))
    return s


def _cag_add_hours_to_hhmm(hi: str, hours: float) -> str:
    t = _cag_parse_hhmm(hi)
    if t is None:
        return ""
    hh, mm = t
    base = datetime(2000, 1, 1, hh, mm)
    end = base + timedelta(hours=float(hours))
    return end.strftime("%H:%M")


def _cag_ag_ui_natureza_e_pacote() -> bool:
    nat = str(st.session_state.get("cag_ag_natureza") or "")
    return _cag_natureza_cmp_key(nat) == _cag_natureza_cmp_key("Pack")


def _cag_parse_pacote_sessao_esc_val(raw: str) -> tuple[int | None, int | None]:
    """Extrai `pacote_sessao_id` e `sessao_servico_id` de `psid|sid` ou `psid|sid|u{k}`."""
    s = str(raw or "").strip()
    parts = s.split("|")
    if len(parts) < 2:
        return None, None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None, None


def _cag_ag_servico_id_para_duracao(*, modo_novo: bool, aid_sel: int | None) -> int | None:
    if not modo_novo and aid_sel is not None:
        ag = obter_agendamento(int(aid_sel))
        if not ag:
            return None
        try:
            sid = int(ag.get("servico_id") or 0)
        except (TypeError, ValueError):
            return None
        return sid if sid > 0 else None
    if modo_novo:
        if _cag_ag_ui_natureza_e_pacote():
            pesc = str(st.session_state.get("cag_ag_pacote_sessao_esc") or "")
            _ps, sid = _cag_parse_pacote_sessao_esc_val(pesc)
            if sid is None or int(sid) <= 0:
                return None
            return int(sid)
        esc = str(st.session_state.get("cag_ag_servico_esc") or "")
        if "|" not in esc:
            return None
        try:
            sid = int(esc.split("|", 1)[0])
        except ValueError:
            return None
        return sid if sid > 0 else None
    return None


def _cag_ag_duracao_label_e_hf_para_state(*, modo_novo: bool, aid_sel: int | None) -> tuple[str, int | None]:
    """Actualiza `cag_ag_hf` (somente leitura na UI) a partir da hora início + duração do catálogo."""
    sid = _cag_ag_servico_id_para_duracao(modo_novo=modo_novo, aid_sel=aid_sel)
    if sid is None:
        st.session_state.cag_ag_hf = ""
        return "—", None
    dur = obter_duracao_referencia_agendamento_horas(int(sid))
    lbl = _cag_format_duracao_catalogo_horas(dur)
    hi = str(st.session_state.get("cag_ag_hi") or "").strip()
    st.session_state.cag_ag_hf = _cag_add_hours_to_hhmm(hi, dur) if hi else ""
    return lbl, sid


def _cag_read_tipo_sala_db_from_state() -> tuple[str | None, int | None, str | None]:
    """(tipo_db, sala_db, erro_ui)."""
    tipo_ui = str(st.session_state.get("cag_ag_tipo_atendimento") or "Presencial")
    if tipo_ui == "Virtual":
        sv = str(st.session_state.get("cag_ag_sala_virtual") or "")
        if sv not in ("Sim", "Não"):
            return None, None, "Indique se a sala virtual já foi disponibilizada (Sim ou Não)."
        ok, msg, tdb, sdb = validar_tipo_atendimento_e_sala("virtual", 1 if sv == "Sim" else 0)
        if not ok:
            return None, None, (msg or "").replace("❌ ", "").strip() or msg
        return str(tdb or "virtual"), sdb, None
    ok, msg, tdb, sdb = validar_tipo_atendimento_e_sala("presencial", None)
    if not ok:
        return None, None, (msg or "").replace("❌ ", "").strip() or msg
    return str(tdb or "presencial"), sdb, None


def _cag_ag_status_widget_key(aid_sel: int | None) -> str:
    """Chave por agendamento — evita `st.selectbox` a partilhar estado entre linhas (estado errado / duplicados)."""
    return f"cag_ag_status_lbl_{int(aid_sel)}" if aid_sel is not None else "cag_ag_status_lbl_novo"


def _cag_hidratar_form_ag(ag: dict[str, Any]) -> None:
    aid = int(ag["id"])
    st.session_state["cag_ag_sticky_aid"] = aid
    st.session_state.cag_ag_data = datetime.strptime(str(ag["data_agendamento"])[:10], "%Y-%m-%d").date()
    st.session_state.cag_ag_hi = str(ag["hora_inicio"])
    st.session_state.cag_ag_hf = str(ag["hora_fim"])
    st.session_state.cag_ag_obs = str(ag.get("observacoes") or "")
    _sl = _CAG_STATUS_DB_TO_LBL.get(str(ag["status"]), str(ag["status"]))
    st.session_state[CAG_AG_STATUS_UI_KEY] = _sl
    st.session_state[_cag_ag_status_widget_key(aid)] = _sl
    cids = list(ag.get("colaborador_ids") or [])
    st.session_state.cag_ag_colabs = cids
    ta = str(ag.get("tipo_atendimento") or "presencial")
    st.session_state.cag_ag_tipo_atendimento = "Virtual" if ta == "virtual" else "Presencial"
    sv = ag.get("sala_virtual_disponibilizada")
    if ta == "virtual" and sv is not None:
        st.session_state.cag_ag_sala_virtual = "Sim" if int(sv) == 1 else "Não"
    else:
        st.session_state.cag_ag_sala_virtual = "—"
    st.session_state.pop("cag_ag_pacote_sessao_esc", None)
    st.session_state.pop("_cag_ag_pkg_sess_sig", None)
    st.session_state.pop(CAG_AG_PACOTE_CATALOG_SERVICO_ID_KEY, None)
    psid = ag.get("pacote_sessao_id")
    pkg_cat = ag.get("pacote_servico_catalogo_id")
    nome_pkg = str(ag.get("nome_do_pacote") or "").strip()
    if psid and pkg_cat:
        st.session_state.cag_ag_natureza = "Pack"
        st.session_state.cag_ag_servico_esc = f"{int(pkg_cat)}|{nome_pkg or 'Pacote'}"
        st.session_state[CAG_AG_PACOTE_CATALOG_SERVICO_ID_KEY] = int(pkg_cat)
        cid_h = int(ag.get("cliente_id") or 0)
        _tot_h, _opts_h = analisar_sessoes_pacote_pendentes_cag(cid_h, int(pkg_cat))
        _vals_h = [v for v, _ in _opts_h]
        _pref = f"{int(psid)}|{int(ag['servico_id'])}|"
        _hit = next((v for v in _vals_h if v.startswith(_pref)), None)
        st.session_state.cag_ag_pacote_sessao_esc = _hit or (_vals_h[0] if _vals_h else f"{int(psid)}|{int(ag['servico_id'])}|u1")
        st.session_state._cag_ag_pkg_sess_sig = f"{int(pkg_cat)}:{cid_h}"
    else:
        st.session_state.cag_ag_natureza = str(ag.get("servico_natureza") or "Sessão")


_CAG_PENDING_HIDRATAR_AG_ID_KEY = "_cag_pending_hidratar_ag_id"
_CAG_PENDING_LIMPAR_AG_FORM_KEY = "_cag_pending_limpar_ag_form"


def _cag_schedule_hidratar_form_ag(*, agendamento_id: int) -> None:
    """Diferir `_cag_hidratar_form_ag` para antes do `st.form` no rerun (botões do assistente vêm depois dos widgets)."""
    st.session_state.pop(_CAG_PENDING_LIMPAR_AG_FORM_KEY, None)
    st.session_state[_CAG_PENDING_HIDRATAR_AG_ID_KEY] = int(agendamento_id)


def _cag_schedule_limpar_form_ag_novo() -> None:
    """Diferir `_cag_limpar_form_ag_novo` — idem (ex.: «Sim» no diálogo Novo agendamento)."""
    st.session_state.pop(_CAG_PENDING_HIDRATAR_AG_ID_KEY, None)
    st.session_state[_CAG_PENDING_LIMPAR_AG_FORM_KEY] = True


def _cag_flush_pending_form_ag_mutations() -> None:
    if st.session_state.pop(_CAG_PENDING_LIMPAR_AG_FORM_KEY, False):
        _cag_limpar_form_ag_novo()
    raw = st.session_state.pop(_CAG_PENDING_HIDRATAR_AG_ID_KEY, None)
    if raw is not None:
        ag = obter_agendamento(int(raw))
        if ag:
            _cag_hidratar_form_ag(ag)


def _cag_limpar_form_ag_novo() -> None:
    st.session_state.pop("cag_ag_sticky_aid", None)
    st.session_state.cag_ag_data = date.today()
    st.session_state.cag_ag_hi = "09:00"
    st.session_state.cag_ag_hf = "10:00"
    st.session_state.cag_ag_obs = ""
    st.session_state.cag_ag_natureza = "Sessão"
    st.session_state.pop("cag_ag_especialidade_esc", None)
    st.session_state.pop("cag_ag_servico_esc", None)
    st.session_state.pop("cag_ag_chain_natureza", None)
    st.session_state.pop("cag_ag_chain_especialidade", None)
    st.session_state.pop("cag_ag_pacote_sessao_esc", None)
    st.session_state.pop("_cag_ag_pkg_sess_sig", None)
    st.session_state.pop(CAG_AG_PACOTE_CATALOG_SERVICO_ID_KEY, None)
    st.session_state.pop("_cag_ag_sap_last_applied_tok", None)
    st.session_state.pop("cag_sap_rows_sig", None)
    st.session_state.cag_ag_tipo_atendimento = "Presencial"
    st.session_state.cag_ag_sala_virtual = "—"
    st.session_state[CAG_AG_STATUS_UI_KEY] = "Agendado"
    st.session_state[_cag_ag_status_widget_key(None)] = "Agendado"
    st.session_state.cag_ag_colabs = []


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


def _cag_migrate_legacy_agenda_keys(*, cliente_id: int, fv: int) -> None:
    """Copia estado legado `…_{cliente_id}_{fv}` para chaves só por cliente (uma vez por sessão)."""
    cid = int(cliente_id)
    fv_i = int(fv)
    nk = f"cag_ag_pick_{cid}"
    if nk not in st.session_state:
        for legacy_fv in range(max(0, fv_i - 8), fv_i + 1):
            lk = f"cag_ag_pick_{cid}_{legacy_fv}"
            if lk in st.session_state:
                st.session_state[nk] = st.session_state.pop(lk)
                break
    pairs = (
        ("offset_key", f"cag_agenda_offset_{cid}", f"cag_agenda_offset_{cid}_"),
        ("tbl_df_v_k", f"cag_ag_lst_tbv_{cid}", f"cag_ag_lst_tbv_{cid}_"),
        ("mode_k", f"cag_cal_mode_{cid}", f"cag_cal_mode_{cid}_"),
        ("anc_k", f"cag_cal_anchor_{cid}", f"cag_cal_anchor_{cid}_"),
    )
    for _label, new_k, prefix in pairs:
        if new_k in st.session_state:
            continue
        for legacy_fv in range(max(0, fv_i - 8), fv_i + 1):
            lk = f"{prefix}{legacy_fv}"
            if lk in st.session_state:
                st.session_state[new_k] = st.session_state.pop(lk)
                break


def _cag_setor4_agenda_keys(*, cliente_id: int, fv: int) -> dict[str, str]:
    """Estado da agenda/lista escopado só por `cliente_id`.

    Não incluir `cag_form_v` (`fv`) nas chaves: quando a ficha recarrega, `fv` incrementa
    e o utilizador perdia `pick_key` → modo «novo» e o gravador chamava `criar_agendamento_pre_venda`
    em vez de `atualizar_agendamento` (duplicados + tabela aparentemente desactualizada).
    """
    _ = fv  # mantido na assinatura para não rebentar chamadores.
    cid = int(cliente_id)
    return {
        "pick_key": f"cag_ag_pick_{cid}",
        "offset_key": f"cag_agenda_offset_{cid}",
        "mode_k": f"cag_cal_mode_{cid}",
        "anc_k": f"cag_cal_anchor_{cid}",
        "tbl_df_v_k": f"cag_ag_lst_tbv_{cid}",
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
        if int(pl0.get("cliente_id") or -1) != int(cliente_id):
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
                    _cag_schedule_hidratar_form_ag(agendamento_id=int(aid_d))
            _cag_schedule_lib_ag_edit(False)
            st.session_state.cag_ag_flash = "Todas as alterações foram descartadas."
            st.session_state.cag_ag_hidr_pick = (pk_w, str(st.session_state.get(pk_w) or ""))
            st.rerun()

        if step == "saldo":
            st.warning(
                "**Saldo de Pagamento Encontrado**\n\n"
                "Deseja transferir o valor pago anteriormente pelo cliente para uma reserva disponível para uso futuro?"
            )
            # Mesma largura relativa que «Seguinte (lista) ▶» (coluna peso 1 em [1,2,1]): par centrado.
            _spL, b1, b2, _spR = st.columns([1, 1, 1, 1])
            with _spL:
                st.empty()
            with b1:
                if st.button("Sim", key=f"cag_wz_saldo_y_{fv}", width="stretch"):
                    st.session_state.cag_ag_wizard = {
                        "step": "edit_alert",
                        "payload": {**pl, "converter_credito": True, "saldo_choice": "sim"},
                    }
                    st.rerun()
            with b2:
                if st.button("Não", key=f"cag_wz_saldo_n_{fv}", width="stretch"):
                    st.session_state.cag_ag_wizard = {
                        "step": "edit_alert",
                        "payload": {**pl, "converter_credito": False, "saldo_choice": "nao"},
                    }
                    st.rerun()
            with _spR:
                st.empty()
        elif step == "edit_alert":
            st.warning(
                "**Alerta de Edição de Informação Cadastrada**\n\n"
                "Tem certeza que quer seguir com a alteração dos dados do agendamento do cliente?"
            )
            _spL, b1, b2, _spR = st.columns([1, 1, 1, 1])
            with _spL:
                st.empty()
            with b1:
                if st.button("Sim", key=f"cag_wz_ed_y_{fv}", width="stretch"):
                    ok_c, msg_c, xtra = _cag_ag_commit_wizard_payload(pl)
                    if not ok_c:
                        st.error(msg_c)
                    else:
                        st.session_state.pop("cag_ag_wizard", None)
                        _cag_schedule_lib_ag_edit(_cag_lib_ag_edit_valor_apos_bloqueio())
                        aid_r = pl.get("aid_sel")
                        if aid_r is not None:
                            ag2 = obter_agendamento(int(aid_r))
                            if ag2:
                                _cag_schedule_hidratar_form_ag(agendamento_id=int(aid_r))
                            st.session_state[offset_key] = _cag_list_offset_para_agendamento(
                                cliente_id=int(cliente_id),
                                aid=int(aid_r),
                            )
                        else:
                            st.session_state[offset_key] = 0
                        base_ok = "Informações salvas com sucesso."
                        st.session_state.cag_ag_flash = (
                            f"{xtra} {base_ok}".strip() if xtra else base_ok
                        )
                        tvk = keys.get("tbl_df_v_k")
                        if tvk:
                            st.session_state[tvk] = int(st.session_state.get(tvk, 0)) + 1
                        st.session_state.pop("_cag_ag_df_prev_sel_id", None)
                        st.session_state.cag_ag_hidr_pick = (
                            pk_w,
                            str(st.session_state.get(pk_w) or ""),
                        )
                        st.rerun()
            with b2:
                if st.button("Não", key=f"cag_wz_ed_n_{fv}", width="stretch"):
                    _discard_wizard()
            with _spR:
                st.empty()

    pend = st.session_state.get("cag_ag_pending_novo_dialog")
    if pend == "ask" and tem_cliente:
        st.warning(
            "**Novo agendamento**\n\n"
            "Deseja realizar um novo agendamento para o mesmo cliente?"
        )
        _spL, b1, b2, _spR = st.columns([1, 1, 1, 1])
        with _spL:
            st.empty()
        with b1:
            if st.button("Sim", key=f"cag_novo_ag_sim_{fv}", type="primary", width="stretch"):
                st.session_state.pop("cag_ag_pending_novo_dialog", None)
                st.session_state.pop("cag_ag_last_created_id", None)
                st.session_state[pick_key] = "__novo__"
                st.session_state.cag_ag_hidr_pick = None
                _cag_schedule_limpar_form_ag_novo()
                _cag_schedule_lib_ag_edit(True)
                st.rerun()
        with b2:
            if st.button("Não", key=f"cag_novo_ag_nao_{fv}", width="stretch"):
                st.session_state.pop("cag_ag_pending_novo_dialog", None)
                last_id = st.session_state.pop("cag_ag_last_created_id", None)
                if last_id is not None:
                    st.session_state[pick_key] = f"id:{int(last_id)}"
                    st.session_state.cag_ag_hidr_pick = None
                _cag_schedule_lib_ag_edit(False)
                st.rerun()
        with _spR:
            st.empty()


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

    raw_all = listar_agendamentos(cliente_ids=[int(cliente_id)])
    todos_all = _cag_agrupar_listagem_cancelados_mesmo_pacote(raw_all)
    ids_all = _cag_ids_agendamentos_lista_expandidos(todos_all)
    raw_pick_top = str(st.session_state.get(pick_key) or "__novo__")
    if raw_pick_top.startswith("id:"):
        try:
            _tid = int(raw_pick_top.split(":", 1)[1])
            if _tid not in ids_all:
                st.session_state[pick_key] = "__novo__"
                st.session_state.cag_ag_hidr_pick = None
                st.session_state.pop("cag_ag_sticky_aid", None)
                raw_pick_top = "__novo__"
        except ValueError:
            st.session_state[pick_key] = "__novo__"
            st.session_state.cag_ag_hidr_pick = None
            st.session_state.pop("cag_ag_sticky_aid", None)
            raw_pick_top = "__novo__"

    # Se o assistente de gravação está aberto mas `pick_key` perdeu-se (ex.: rerun da lista),
    # o ecrã ficava em «modo novo» com dados antigos e «Salvar» chamava `criar_agendamento_pre_venda`.
    wiz_rep = st.session_state.get("cag_ag_wizard")
    if isinstance(wiz_rep, dict):
        st_wr = str(wiz_rep.get("step") or "")
        pl_wr = wiz_rep.get("payload") or {}
        if st_wr in ("edit_alert", "saldo") and pl_wr.get("aid_sel") is not None:
            try:
                waid = int(pl_wr["aid_sel"])
                if waid in ids_all:
                    exp = f"id:{waid}"
                    if not raw_pick_top.startswith("id:"):
                        st.session_state[pick_key] = exp
                        raw_pick_top = exp
                    st.session_state["cag_ag_sticky_aid"] = waid
            except (TypeError, ValueError):
                pass

    _force_hydrate = bool(st.session_state.pop("cag_ag_need_hydrate", False))
    hidr_sig_top = st.session_state.get("cag_ag_hidr_pick")
    wiz_blk = st.session_state.get("cag_ag_wizard")
    skip_hydrate = False
    if isinstance(wiz_blk, dict):
        st_w = str(wiz_blk.get("step") or "")
        pl_w = wiz_blk.get("payload") or {}
        if st_w in ("edit_alert", "saldo") and pl_w.get("aid_sel") is not None:
            # Evita repor o formulário a partir da BD por cima do estado escolhido antes de confirmar o assistente.
            skip_hydrate = True
    if not skip_hydrate and (_force_hydrate or hidr_sig_top != (pick_key, raw_pick_top)):
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
    if aid_sel is None:
        stx = st.session_state.get("cag_ag_sticky_aid")
        if stx is not None:
            try:
                sx = int(stx)
                if sx in ids_all:
                    agx = obter_agendamento(sx)
                    if agx and int(agx.get("cliente_id") or 0) == int(cliente_id):
                        aid_sel = sx
                        if not raw_pick_top.startswith("id:"):
                            st.session_state[pick_key] = f"id:{sx}"
                            raw_pick_top = f"id:{sx}"
            except (TypeError, ValueError):
                pass
    if aid_sel is None and isinstance(wiz_blk, dict):
        st_w2 = str(wiz_blk.get("step") or "")
        pl2 = wiz_blk.get("payload") or {}
        if st_w2 in ("edit_alert", "saldo") and pl2.get("aid_sel") is not None:
            try:
                wx = int(pl2["aid_sel"])
                if wx in ids_all:
                    agw = obter_agendamento(wx)
                    if agw and int(agw.get("cliente_id") or 0) == int(cliente_id):
                        aid_sel = wx
                        if not raw_pick_top.startswith("id:"):
                            st.session_state[pick_key] = f"id:{wx}"
                            raw_pick_top = f"id:{wx}"
            except (TypeError, ValueError):
                pass
    modo_novo = aid_sel is None

    if modo_novo:
        dis_ag = False
    else:
        dis_ag = not bool(st.session_state.get("cag_lib_ag_edit"))

    st.session_state.setdefault(mode_k, "Semanal")
    _cag_init_calendar_anchor(anc_k)

    return {
        **keys,
        "raw_pick_top": raw_pick_top,
        "aid_sel": aid_sel,
        "modo_novo": modo_novo,
        "dis_ag": dis_ag,
    }


def _cag_setor4_render_selecao_edicao_block(*, fv: int, ctx: dict[str, Any]) -> bool:
    modo_novo = ctx["modo_novo"]
    dis_ag = ctx["dis_ag"]
    st.markdown("##### Selecção e edição")

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
    return dis_ag


def _cag_setor4_render_calendario_only(*, cliente_id: int, fv: int, ctx: dict[str, Any]) -> None:
    mode_k = ctx["mode_k"]
    anc_k = ctx["anc_k"]

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

    raw_cal = listar_agendamentos(
        data_de=d_de,
        data_ate=d_ate,
        cliente_ids=[int(cliente_id)],
    )
    cal_rows = _cag_agrupar_listagem_cancelados_mesmo_pacote(raw_cal)
    if modo == "Semanal":
        cal_html = _cag_week_cal_table_html(mon=mon, week_rows=cal_rows)
        st.markdown(f'<div class="bea-proto-scope">{cal_html}</div>', unsafe_allow_html=True)
    else:
        cal_html = _cag_month_cal_table_html(ref=mon, month_rows=cal_rows)
        st.markdown(f'<div class="bea-proto-scope">{cal_html}</div>', unsafe_allow_html=True)


def _cag_render_conversao_pacote_hoje_block(
    *, cliente_id: int, fv: int, pick_key: str, dis_ag: bool
) -> None:
    """Conversão avulsa → consumo de pacote (regra: data de hoje, estados permitidos)."""
    raw_pk = str(st.session_state.get(pick_key) or "__novo__")
    if not raw_pk.startswith("id:"):
        return
    try:
        aid = int(raw_pk.split(":", 1)[1])
    except (IndexError, ValueError):
        return
    ag = obter_agendamento(aid)
    if not ag or int(ag.get("cliente_id") or 0) != int(cliente_id):
        return
    ok_e, _msg_ge = agendamento_elegivel_conversao_para_pacote_hoje(ag)
    if not ok_e:
        return
    buckets = listar_buckets_pacote_com_saldo_disponivel(int(cliente_id))
    if not buckets:
        return
    st.markdown(
        '<div class="bea-cv-cag-gap" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    with st.expander("Converter para consumo de pacote (hoje)", expanded=False):
        st.caption(
            f"Uma sessão com **data de hoje**, não concluída nem em «{ESTADO_AGENDAMENTO_REALIZADO_PENDENTE_LABEL_PT}», "
            "ligada a um componente do pacote com saldo disponível."
        )
        opts_vals: list[str] = []
        lbl_map: dict[str, str] = {}
        for b in buckets:
            vi = int(b["venda_item_id"])
            ps = int(b["pacote_sessao_id"])
            vk = f"{vi}|{ps}"
            opts_vals.append(vk)
            lbl_map[vk] = (
                f"{b.get('rotulo', '—')} · saldo {int(b.get('saldo', 0))} · {b.get('pagamento', '')}"
            )
        pick_ui = f"cag_conv_pac_pick_{cliente_id}_{fv}_{aid}"

        def _fmt_pacote_bucket(v: str) -> str:
            return lbl_map.get(str(v), str(v))

        st.selectbox(
            "Pacote / componente",
            options=opts_vals,
            format_func=_fmt_pacote_bucket,
            key=pick_ui,
        )
        if st.button(
            "Confirmar conversão para pacote",
            type="secondary",
            disabled=dis_ag,
            key=f"cag_conv_pac_go_{cliente_id}_{fv}_{aid}",
        ):
            pick = str(st.session_state.get(pick_ui) or "")
            if "|" not in pick:
                st.error("Seleccione um pacote.")
            else:
                a, _, b = pick.partition("|")
                try:
                    vi_c = int(a)
                    ps_c = int(b)
                except ValueError:
                    st.error("Opção inválida.")
                else:
                    ok_c, msg_c = converter_agendamento_avulso_para_consumo_pacote(
                        aid, vi_c, ps_c, actor="cag_ui"
                    )
                    if ok_c:
                        st.success(msg_c)
                        st.rerun()
                    else:
                        st.error(msg_c)


def _cag_render_select_sessoes_pacote_cag(*, cliente_id: int, dis_ag: bool) -> None:
    """Só com Natureza = Pacote: «Total» e «Lista de Sessoes…» na mesma linha (duas colunas)."""
    if not _cag_ag_ui_natureza_e_pacote():
        return
    pid = 0
    raw_cat = st.session_state.get(CAG_AG_PACOTE_CATALOG_SERVICO_ID_KEY)
    if raw_cat is not None:
        try:
            pid = int(raw_cat)
        except (TypeError, ValueError):
            pid = 0
    if pid < 1:
        esc_fb = str(st.session_state.get("cag_ag_servico_esc") or "")
        if "|" in esc_fb:
            try:
                pid = int(esc_fb.split("|", 1)[0])
            except ValueError:
                pid = 0
    if pid < 1:
        return
    if not listar_sessoes_do_pacote_catalogo(pid):
        st.warning("Este pacote não tem sessões configuradas no catálogo.")
        st.session_state.pop("cag_ag_pacote_sessao_esc", None)
        return

    total, opcoes = analisar_sessoes_pacote_pendentes_cag(int(cliente_id), pid)
    if int(total) == 0:
        st.warning(
            "Todas as sessões deste pacote para este cliente já foram devidamente agendadas."
        )
        st.session_state.pop("cag_ag_pacote_sessao_esc", None)
        return

    opts = [v for v, _ in opcoes]
    lbl_map = {v: lab for v, lab in opcoes}

    pkg_sig = f"{pid}:{int(cliente_id)}"
    if st.session_state.get("_cag_ag_pkg_sess_sig") != pkg_sig:
        st.session_state._cag_ag_pkg_sess_sig = pkg_sig
        st.session_state.pop("cag_ag_pacote_sessao_esc", None)
    curv = str(st.session_state.get("cag_ag_pacote_sessao_esc") or "")
    if curv not in opts:
        st.session_state.cag_ag_pacote_sessao_esc = opts[0]

    _lbl_tot = "Total de Agendamentos pendentes do Pacote"
    _lbl_lst = "Lista de Sessoes do Pacote Pendente Agendamento"
    c_tot, c_lst = st.columns([1, 1], gap="medium")
    with c_tot:
        st.markdown(
            '<p style="margin:0 0 0.2rem 0;text-align:left;white-space:nowrap;'
            "overflow-x:auto;font-size:0.88rem;font-weight:600;color:#2D332F;\">"
            f"{html.escape(_lbl_tot)}</p>",
            unsafe_allow_html=True,
        )
        st.text_input(
            "tot_pac_int",
            value=str(int(total)),
            key=f"cag_ag_pacote_pend_tot_{int(cliente_id)}_{pid}_{int(total)}",
            disabled=True,
            label_visibility="collapsed",
            width="stretch",
        )
    with c_lst:
        st.markdown(
            '<p style="margin:0 0 0.2rem 0;text-align:left;white-space:nowrap;'
            "overflow-x:auto;font-size:0.88rem;font-weight:600;color:#2D332F;\">"
            f"{html.escape(_lbl_lst)}</p>",
            unsafe_allow_html=True,
        )
        st.selectbox(
            "lst_pac_int",
            options=opts,
            format_func=lambda v, _m=lbl_map: _m.get(str(v), str(v)),
            key="cag_ag_pacote_sessao_esc",
            disabled=dis_ag,
            label_visibility="collapsed",
            width="stretch",
        )


def _cag_render_dados_ag_linha1_novo_fora_form(
    *,
    cliente_id: int,
    all_srv: list[dict[str, str | int]],
    col_opts: list[int],
    col_lbl: dict[int, str],
    dis_ag: bool,
    aid_sel: int | None,
) -> None:
    """Expander SAP em largura total + linha «Total / Lista» do pacote abaixo, só com linha Pacote seleccionada.

    Sem isto, o Streamlit atrasa `session_state` dos widgets do form até ao submit e o «Serviço»
    não reflecte a «Natureza» escolhida no mesmo rerun.
    """
    sap_rows = _cag_sincronizar_servicos_adquiridos_pendente(int(cliente_id))

    row_sel_sap: dict[str, Any] | None = None
    with st.expander(
        "Serviços adquiridos pendente agendamento",
        expanded=bool(sap_rows),
    ):
        if not sap_rows:
            st.caption("— Nenhum serviço pendente de agendamento neste estado —")
        else:
            df_sap = _cag_sap_rows_para_dataframe(sap_rows)
            tbl_v = int(st.session_state.get("cag_sap_df_v", 0))
            tbl_key = f"cag_sap_df_{int(cliente_id)}_{tbl_v}"
            ev_sap = st.dataframe(
                df_sap,
                width="stretch",
                on_select="rerun",
                selection_mode="single-row",
                key=tbl_key,
                hide_index=True,
            )
            sel_sap = _cag_df_selected_rows(ev_sap, tbl_key)
            tok = ""
            if sel_sap and 0 <= int(sel_sap[0]) < len(sap_rows):
                row_sel_sap = sap_rows[int(sel_sap[0])]
                tok = str(row_sel_sap.get("token") or "")
                if tok:
                    vi_row = int(row_sel_sap.get("venda_item_id") or 0)
                    vi_state = int(st.session_state.get("cag_ag_credito_vi_id") or 0)
                    stale_vi = vi_row > 0 and vi_state > 0 and vi_row != vi_state
                    stale_tok = str(st.session_state.get("_cag_ag_sap_last_applied_tok") or "") != tok
                    if stale_vi or stale_tok:
                        st.session_state._cag_ag_sap_last_applied_tok = tok
                        _cag_aplicar_linha_servico_adquirido_pendente(sap_rows, tok)

    if _cag_ag_ui_natureza_e_pacote() and (
        int(st.session_state.get(CAG_AG_PACOTE_CATALOG_SERVICO_ID_KEY) or 0) > 0
        or (
            row_sel_sap is not None
            and _cag_natureza_cmp_key(str(row_sel_sap.get("natureza") or ""))
            == _cag_natureza_cmp_key("Pack")
            and "|" in str(st.session_state.get("cag_ag_servico_esc") or "")
        )
    ):
        _cag_render_select_sessoes_pacote_cag(cliente_id=int(cliente_id), dis_ag=dis_ag)
    if _cag_ag_ui_natureza_e_pacote() and "|" in str(st.session_state.get("cag_ag_pacote_sessao_esc") or ""):
        _cag_ag_sync_especialidade_de_sessao_pacote_escolhida()
        _cag_ag_sync_servico_esc_de_sessao_pacote_escolhida()

    _w_rest = tuple(_CAG_DADOS_AG_L1_COL_WIDTHS[i] for i in range(1, 6))
    r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns(_w_rest, gap="small")
    with r1c1:
        naturezas_opts = list(_CAG_NATUREZAS_AGENDA_NOVO)
        cur_nat = str(st.session_state.get("cag_ag_natureza") or "").strip()
        if cur_nat not in naturezas_opts:
            st.session_state.cag_ag_natureza = naturezas_opts[0]
        st.selectbox("Natureza", naturezas_opts, key="cag_ag_natureza", disabled=dis_ag)
    nat = str(st.session_state.get("cag_ag_natureza") or "Sessão")
    _nat_ch = st.session_state.get("cag_ag_chain_natureza", "__unset__")
    if _nat_ch == "__unset__":
        st.session_state.cag_ag_chain_natureza = nat
    elif str(_nat_ch) != nat:
        st.session_state.cag_ag_chain_natureza = nat
        st.session_state.pop("cag_ag_especialidade_esc", None)
        st.session_state.pop("cag_ag_servico_esc", None)
        st.session_state.pop("cag_ag_chain_especialidade", None)
    nk = _cag_natureza_cmp_key(nat)
    filtrados = [s for s in all_srv if _cag_natureza_cmp_key(str(s.get("natureza") or "")) == nk]
    esp_labels_ui = _cag_ag_build_esp_labels_ui(filtrados)
    _raw_esp = st.session_state.get("cag_ag_especialidade_esc")
    if _raw_esp is not None and str(_raw_esp) not in esp_labels_ui:
        if nk == _cag_natureza_cmp_key("Pack"):
            esp_labels_ui = list(esp_labels_ui) + [str(_raw_esp)]
        else:
            st.session_state.pop("cag_ag_especialidade_esc", None)
    with r1c2:
        st.selectbox("Especialidades", options=esp_labels_ui, key="cag_ag_especialidade_esc", disabled=dis_ag)
    _esp_lbl = str(st.session_state.get("cag_ag_especialidade_esc") or _CAG_ESP_PLACEHOLDER)
    _esp_ch = st.session_state.get("cag_ag_chain_especialidade", "__unset__")
    if _esp_ch == "__unset__":
        st.session_state.cag_ag_chain_especialidade = _esp_lbl
    elif str(_esp_ch) != _esp_lbl:
        st.session_state.cag_ag_chain_especialidade = _esp_lbl
        st.session_state.pop("cag_ag_servico_esc", None)
    if nk == _cag_natureza_cmp_key("Pack"):
        filtrados_esp = list(filtrados)
    else:
        filtrados_esp = _cag_ag_filtrar_servicos_por_especialidade(filtrados, _esp_lbl)
    choices_real = [f"{int(s['id'])}|{s['nome']}" for s in filtrados_esp]
    if nk == _cag_natureza_cmp_key("Pack"):
        pesc_ch = str(st.session_state.get("cag_ag_pacote_sessao_esc") or "")
        _ps_ch, sid_ch = _cag_parse_pacote_sessao_esc_val(pesc_ch)
        if sid_ch is not None and int(sid_ch) > 0:
            row_ch = obter_servico_para_formulario(int(sid_ch))
            if row_ch:
                nm_ch = str(row_ch.get("nome") or "").strip() or "—"
                esc_ch = f"{int(sid_ch)}|{nm_ch}"
                if esc_ch not in choices_real:
                    choices_real = [esc_ch] + choices_real
    with r1c3:
        if not filtrados:
            st.warning(
                f"Não há serviços **{nat}** activos no catálogo. Crie ou active um serviço em **Catálogo**."
            )
            st.session_state.cag_ag_servico_esc = ""
        elif _esp_lbl == _CAG_ESP_PLACEHOLDER or not choices_real:
            if "cag_ag_servico_esc" not in st.session_state or st.session_state.cag_ag_servico_esc not in (
                _CAG_SVC_PLACEHOLDER,
            ):
                st.session_state.cag_ag_servico_esc = _CAG_SVC_PLACEHOLDER
            st.selectbox(
                "Serviço",
                options=[_CAG_SVC_PLACEHOLDER],
                key="cag_ag_servico_esc",
                disabled=dis_ag,
            )
        else:
            if "cag_ag_servico_esc" not in st.session_state or (
                st.session_state.cag_ag_servico_esc not in choices_real
            ):
                st.session_state.cag_ag_servico_esc = choices_real[0]
            st.selectbox("Serviço", options=choices_real, key="cag_ag_servico_esc", disabled=dis_ag)
    with r1c4:
        _opts_c = (
            col_opts
            if col_opts
            else [_CAG_AG_COLAB_OPTS_EMPTY_SENTINEL]
        )

        def _fmt_cag_colab_row(i: int, _m: dict[int, str] = col_lbl) -> str:
            if int(i) == _CAG_AG_COLAB_OPTS_EMPTY_SENTINEL:
                return "— Seleccione o serviço (colaboradores por habilitação) —"
            return _cag_colab_multiselect_label(_m, int(i))

        st.multiselect(
            "Colaborador(es)",
            options=_opts_c,
            format_func=_fmt_cag_colab_row,
            key="cag_ag_colabs",
            disabled=dis_ag or not col_opts,
        )
    with r1c5:
        ag_cur3 = obter_agendamento(int(aid_sel)) if aid_sel is not None else None
        opts_st = _cag_opcoes_status_edicao(str(ag_cur3["status"]) if ag_cur3 else "AGENDADO")
        cur_lbl = str(st.session_state.get(CAG_AG_STATUS_UI_KEY) or "Agendado")
        if cur_lbl not in opts_st:
            opts_st.insert(0, cur_lbl)
        opts_st = list(dict.fromkeys(opts_st))
        st.selectbox("Estado", opts_st, key=CAG_AG_STATUS_UI_KEY, disabled=dis_ag)
    nat_f = str(st.session_state.get("cag_ag_natureza") or "Sessão")
    if _cag_natureza_cmp_key(nat_f) != _cag_natureza_cmp_key("Pack"):
        st.session_state.pop("cag_ag_pacote_sessao_esc", None)
        st.session_state.pop("_cag_ag_pkg_sess_sig", None)
        st.session_state.pop(CAG_AG_PACOTE_CATALOG_SERVICO_ID_KEY, None)


def _cag_setor4_render_dados_ag_form_e_wizards(
    *, cliente_id: int, fv: int, tem_cliente: bool, ctx: dict[str, Any], dis_ag: bool
) -> None:
    pick_key = ctx["pick_key"]
    offset_key = ctx["offset_key"]
    aid_sel = ctx["aid_sel"]
    modo_novo = ctx["modo_novo"]

    _cag_dados_ag_shell = st.container(border=False)
    with _cag_dados_ag_shell:
        st.markdown("##### Dados do Agendamento")

        all_srv = listar_servicos_para_venda()
        _sid_colab = _cag_ag_servico_id_para_duracao(modo_novo=modo_novo, aid_sel=aid_sel)
        col_opts, col_lbl = _cag_ag_colab_opts_para_servico_id(_sid_colab)
        _allowed_c = set(col_opts)
        _cur_c = [int(x) for x in (st.session_state.get("cag_ag_colabs") or []) if int(x) != _CAG_AG_COLAB_OPTS_EMPTY_SENTINEL]
        st.session_state.cag_ag_colabs = [x for x in _cur_c if x in _allowed_c]

        if modo_novo:
            _cag_render_dados_ag_linha1_novo_fora_form(
                cliente_id=int(cliente_id),
                all_srv=all_srv,
                col_opts=col_opts,
                col_lbl=col_lbl,
                dis_ag=dis_ag,
                aid_sel=aid_sel,
            )

        with st.form(f"cag_ag_dados_form_{cliente_id}_{fv}", clear_on_submit=False):
            _cag_sync_ag_tipo_sala_state()

            if not modo_novo:
                # Linha 1 (edição): mesmo leiaute que «Novo» (1.ª coluna inactiva neste modo).
                r1c0, r1c1, r1c2, r1c3, r1c4, r1c5 = st.columns(_CAG_DADOS_AG_L1_COL_WIDTHS, gap="small")
                with r1c0:
                    st.selectbox(
                        "Serviços adquiridos pendente agendamento",
                        ["—"],
                        index=0,
                        key=f"cag_ag_sap_dis_edit_{aid_sel}_{fv}",
                        disabled=True,
                        help="Seleccionável em modo «Novo agendamento».",
                    )
                with r1c1:
                    ag_cur = obter_agendamento(int(aid_sel)) if aid_sel is not None else None
                    nat_cur = str(ag_cur.get("servico_natureza") or "") if ag_cur else ""
                    st.selectbox(
                        "Natureza",
                        [nat_cur] if nat_cur else ["—"],
                        disabled=True,
                        key=f"cag_ag_nat_combo_{aid_sel}_{fv}",
                    )
                with r1c2:
                    ag_cur_e = obter_agendamento(int(aid_sel)) if aid_sel is not None else None
                    esp_txt = "—"
                    if ag_cur_e:
                        try:
                            _sid_e = int(ag_cur_e.get("servico_id") or 0)
                        except (TypeError, ValueError):
                            _sid_e = 0
                        if _sid_e > 0:
                            sf = obter_servico_para_formulario(_sid_e)
                            if sf:
                                en = str(sf.get("especialidade_nome") or "").strip()
                                esp_txt = en if en else _CAG_ESP_SEM_LABEL
                    st.selectbox(
                        "Especialidades",
                        [esp_txt],
                        disabled=True,
                        key=f"cag_ag_esp_combo_{aid_sel}_{fv}",
                    )
                with r1c3:
                    ag_cur2 = obter_agendamento(int(aid_sel)) if aid_sel is not None else None
                    srv_cur = str(ag_cur2.get("servico_nome") or "") if ag_cur2 else ""
                    st.selectbox(
                        "Serviço",
                        [srv_cur] if srv_cur else ["—"],
                        disabled=True,
                        key=f"cag_ag_srv_combo_{aid_sel}_{fv}",
                    )
                with r1c4:
                    _opts_ce = (
                        col_opts
                        if col_opts
                        else [_CAG_AG_COLAB_OPTS_EMPTY_SENTINEL]
                    )

                    def _fmt_cag_colab_ed(i: int, _m: dict[int, str] = col_lbl) -> str:
                        if int(i) == _CAG_AG_COLAB_OPTS_EMPTY_SENTINEL:
                            return "— Sem colaboradores habilitados para este serviço —"
                        return _cag_colab_multiselect_label(_m, int(i))

                    st.multiselect(
                        "Colaborador(es)",
                        options=_opts_ce,
                        format_func=_fmt_cag_colab_ed,
                        key="cag_ag_colabs",
                        disabled=dis_ag or not col_opts,
                    )
                with r1c5:
                    ag_cur3 = obter_agendamento(int(aid_sel)) if aid_sel is not None else None
                    opts_st = _cag_opcoes_status_edicao(str(ag_cur3["status"]) if ag_cur3 else "AGENDADO")
                    cur_lbl = str(st.session_state.get(CAG_AG_STATUS_UI_KEY) or "Agendado")
                    if cur_lbl not in opts_st:
                        opts_st.insert(0, cur_lbl)
                    opts_st = list(dict.fromkeys(opts_st))
                    st.selectbox("Estado", opts_st, key=CAG_AG_STATUS_UI_KEY, disabled=dis_ag)
    
            # Linha 2: Data · Hora início · Duração (catálogo, só leitura) · Hora fim (calculada) · Tipo · Sala virtual
            # Nota: `text_input` da hora início vem antes do sync para, no mesmo rerun, actualizar `cag_ag_hf`.
            r2c1, r2c2, r2c3, r2c4, r2c5, r2c6 = st.columns(
                [1.05, 0.92, 1.0, 0.92, 1.02, 1.05], gap="small"
            )
            with r2c1:
                st.date_input(
                    "Data (dd/mm/aaaa)",
                    key="cag_ag_data",
                    format="DD/MM/YYYY",
                    disabled=dis_ag,
                )
            with r2c2:
                st.text_input("Hora início (HH:MM)", key="cag_ag_hi", disabled=dis_ag, placeholder="09:00")
    
            dur_lbl, sid_dur = _cag_ag_duracao_label_e_hf_para_state(modo_novo=modo_novo, aid_sel=aid_sel)
            _dur_sig = f"{sid_dur}:{dur_lbl}"
            if st.session_state.get("_cag_ag_dur_ro_sig") != _dur_sig:
                st.session_state._cag_ag_dur_ro_sig = _dur_sig
                st.session_state.cag_ag_dur_ro_v = int(st.session_state.get("cag_ag_dur_ro_v", 0)) + 1
            _dur_ro_v = int(st.session_state.get("cag_ag_dur_ro_v", 0))
    
            with r2c3:
                st.selectbox(
                    "Duração",
                    [dur_lbl],
                    index=0,
                    key=f"cag_ag_dur_ro_{_dur_ro_v}",
                    disabled=True,
                    help="Valor definido no catálogo para o serviço seleccionado (como «Duração (HH:MM) *»).",
                )
            with r2c4:
                st.text_input(
                    "Hora fim (HH:MM)",
                    key="cag_ag_hf",
                    disabled=True,
                    placeholder="—",
                    help="Calculada automaticamente: hora início + duração do serviço no catálogo.",
                )
            with r2c5:
                st.selectbox(
                    "Tipo de Atendimento *",
                    ["Presencial", "Virtual"],
                    key="cag_ag_tipo_atendimento",
                    disabled=dis_ag,
                )
            with r2c6:
                tipo_lbl = str(st.session_state.get("cag_ag_tipo_atendimento") or "Presencial")
                virt = tipo_lbl == "Virtual"
                opts_sala = ["Sim", "Não"] if virt else ["—"]
                dis_sala = dis_ag or not virt
                st.selectbox(
                    "Sala virtual disponibilizada?",
                    opts_sala,
                    key="cag_ag_sala_virtual",
                    disabled=dis_sala,
                    help="Indique se o link ou acesso à sala virtual já foi enviado/liberado para o cliente.",
                )
    
            if not modo_novo:
                ag_cur4 = obter_agendamento(int(aid_sel)) if aid_sel is not None else None
                modo_cred = ag_cur4 and str(ag_cur4.get("modo_origem") or "") != "pre_venda"
                if modo_cred and str(st.session_state.get(CAG_AG_STATUS_UI_KEY)) == "Cancelado":
                    st.checkbox(
                        "Devolver crédito ao buffer (saldo da linha de venda)",
                        key="cag_ag_devolver_buffer",
                        value=True,
                        disabled=dis_ag,
                    )
    
            st.text_area("Observações", key="cag_ag_obs", height=72, disabled=dis_ag)
    
            submitted = st.form_submit_button("Salvar Agendamento", type="secondary", disabled=dis_ag)

    _cag_render_conversao_pacote_hoje_block(
        cliente_id=cliente_id, fv=fv, pick_key=pick_key, dis_ag=dis_ag
    )

    if submitted:
        if not tem_cliente:
            st.warning("Carregue ou registe um cliente antes de gravar agendamentos.")
        else:
            d_ag = st.session_state.get("cag_ag_data")
            hi = str(st.session_state.get("cag_ag_hi") or "").strip()
            obs = str(st.session_state.get("cag_ag_obs") or "").strip()
            colab_ids_ui = [int(x) for x in (st.session_state.get("cag_ag_colabs") or [])]

            if d_ag is None or not hasattr(d_ag, "isoformat"):
                st.error("Indique a data.")
            else:
                aid_edit = _cag_resolve_aid_edit_from_pick(
                    cliente_id=int(cliente_id), pick_key=pick_key
                )
                ag_pick = obter_agendamento(aid_edit) if aid_edit is not None else None
                if ag_pick is None and not colab_ids_ui:
                    st.error("Seleccione pelo menos um colaborador.")
                else:
                    colab_ids = (
                        colab_ids_ui
                        if colab_ids_ui
                        else (
                            list(ag_pick.get("colaborador_ids") or [])
                            if ag_pick is not None
                            else []
                        )
                    )
                    t_db, s_db, err_ts = _cag_read_tipo_sala_db_from_state()
                    if err_ts:
                        st.error(err_ts)
                    else:
                        if ag_pick is not None and aid_edit is not None:
                            st.session_state[pick_key] = f"id:{int(aid_edit)}"
                            st.session_state["cag_ag_sticky_aid"] = int(aid_edit)

                        sid_sub: int | None = None
                        if ag_pick is not None:
                            try:
                                _xs = int(ag_pick.get("servico_id") or 0)
                                sid_sub = _xs if _xs > 0 else None
                            except (TypeError, ValueError):
                                sid_sub = None
                        elif modo_novo:
                            nat_ui = str(st.session_state.get("cag_ag_natureza") or "")
                            es_pac = _cag_natureza_cmp_key(nat_ui) == _cag_natureza_cmp_key("Pack")
                            sid_sub = None
                            if es_pac:
                                pesc = str(st.session_state.get("cag_ag_pacote_sessao_esc") or "")
                                _ps_u, sid_u = _cag_parse_pacote_sessao_esc_val(pesc)
                                sid_sub = sid_u if sid_u and int(sid_u) > 0 else None
                            else:
                                esc0 = str(st.session_state.get("cag_ag_servico_esc") or "")
                                if "|" in esc0:
                                    try:
                                        sid_sub = int(esc0.split("|", 1)[0])
                                    except ValueError:
                                        sid_sub = None
                        hf_save = ""
                        if sid_sub is not None:
                            hf_save = _cag_add_hours_to_hhmm(
                                hi, obter_duracao_referencia_agendamento_horas(int(sid_sub))
                            )

                        # Sempre gravar como EDIÇÃO se `pick_key` aponta para um agendamento real,
                        # mesmo que `ctx.modo_novo` esteja True (evita duplicar com `criar_agendamento_pre_venda`).
                        if ag_pick is not None:
                            if sid_sub and not hf_save:
                                st.error("Hora início inválida (use HH:MM).")
                            else:
                                ag0 = ag_pick
                                status_lbl = str(
                                    st.session_state.get(CAG_AG_STATUS_UI_KEY)
                                    or st.session_state.get(_cag_ag_status_widget_key(int(aid_edit)))
                                    or ""
                                ).strip()
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
                                    "aid_sel": int(aid_edit),
                                    "d_iso": d_iso,
                                    "hi": hi,
                                    "hf": hf_save,
                                    "obs": obs,
                                    "colab_ids": colab_ids,
                                    "status_lbl": status_lbl,
                                    "status_new": status_new,
                                    "dev_buf": dev_buf,
                                    "converter_credito": False,
                                    "saldo_choice": None,
                                    "tipo_atendimento": t_db,
                                    "sala_virtual_disponibilizada": s_db,
                                }
                                if is_b:
                                    st.session_state.cag_ag_wizard = {"step": "saldo", "payload": base_pl}
                                else:
                                    st.session_state.cag_ag_wizard = {"step": "edit_alert", "payload": base_pl}
                                st.rerun()
                        elif modo_novo:
                            esc = str(st.session_state.get("cag_ag_servico_esc") or "")
                            nat_ui = str(st.session_state.get("cag_ag_natureza") or "")
                            es_pac = _cag_natureza_cmp_key(nat_ui) == _cag_natureza_cmp_key("Pack")
                            vi_star = _cag_opt_pos_int(st.session_state.get("cag_ag_credito_vi_id"))
                            ps_use = _cag_opt_pos_int(st.session_state.get("cag_ag_credito_ps_id"))
                            ok_cred = vi_star is not None and _cag_credito_venda_item_ainda_pendente_na_lista(
                                int(cliente_id),
                                int(vi_star),
                                ps_use,
                                st.session_state,
                            )
                            if ok_cred:
                                err_cred: str | None = None
                                ps_arg: int | None = None
                                if "|" not in esc:
                                    err_cred = "Seleccione um serviço válido."
                                elif not hf_save:
                                    err_cred = "Hora início inválida (use HH:MM)."
                                elif es_pac:
                                    pesc = str(st.session_state.get("cag_ag_pacote_sessao_esc") or "")
                                    if "|" not in pesc:
                                        err_cred = (
                                            "Seleccione uma sessão em «Lista de Sessoes do Pacote Pendente "
                                            "Agendamento»."
                                        )
                                    else:
                                        ps_row, sid_sess = _cag_parse_pacote_sessao_esc_val(pesc)
                                        if ps_row is None or sid_sess is None:
                                            err_cred = "Opção de sessão do pacote inválida."
                                        elif ps_use is not None and int(ps_row) != int(ps_use):
                                            err_cred = (
                                                "A sessão do pacote não corresponde à opção "
                                                "«Serviços adquiridos pendente agendamento»."
                                            )
                                        else:
                                            ps_arg = int(ps_row)
                                if err_cred:
                                    st.error(err_cred)
                                else:
                                    d_iso = d_ag.isoformat()
                                    ok, msg = criar_agendamento(
                                        int(vi_star),
                                        ps_arg,
                                        d_iso,
                                        hi,
                                        hf_save,
                                        colab_ids,
                                        obs,
                                        tipo_atendimento=t_db,
                                        sala_virtual_disponibilizada=s_db,
                                    )
                                    if ok:
                                        new_id = _cag_ag_parse_novo_id(msg)
                                        if new_id is not None:
                                            st.session_state.cag_ag_last_created_id = new_id
                                            st.session_state[pick_key] = f"id:{int(new_id)}"
                                            st.session_state["cag_ag_sticky_aid"] = int(new_id)
                                            st.session_state.cag_ag_hidr_pick = None
                                            st.session_state[offset_key] = _cag_list_offset_para_agendamento(
                                                cliente_id=int(cliente_id),
                                                aid=int(new_id),
                                            )
                                        else:
                                            st.session_state[offset_key] = 0
                                        st.session_state.cag_ag_flash = "Informações salvas com sucesso."
                                        st.session_state.cag_ag_pending_novo_dialog = "ask"
                                        st.rerun()
                                    else:
                                        st.error(msg)
                            else:
                                st.session_state.pop("cag_ag_credito_vi_id", None)
                                st.session_state.pop("cag_ag_credito_ps_id", None)
                                if "|" not in esc:
                                    st.error("Seleccione um serviço válido.")
                                elif es_pac:
                                    pesc = str(st.session_state.get("cag_ag_pacote_sessao_esc") or "")
                                    if "|" not in pesc:
                                        st.error(
                                            "Seleccione uma sessão em «Lista de Sessoes do Pacote Pendente "
                                            "Agendamento»."
                                        )
                                    elif not hf_save:
                                        st.error("Hora início inválida (use HH:MM).")
                                    else:
                                        ps_row, sid_sess = _cag_parse_pacote_sessao_esc_val(pesc)
                                        if ps_row is None or sid_sess is None:
                                            st.error("Opção de sessão do pacote inválida.")
                                        else:
                                            d_iso = d_ag.isoformat()
                                            ok, msg = criar_agendamento_pre_venda(
                                                int(cliente_id),
                                                sid_sess,
                                                d_iso,
                                                hi,
                                                hf_save,
                                                colab_ids,
                                                obs,
                                                None,
                                                tipo_atendimento=t_db,
                                                sala_virtual_disponibilizada=s_db,
                                                pacote_sessao_id=ps_row,
                                            )
                                            if ok:
                                                new_id = _cag_ag_parse_novo_id(msg)
                                                if new_id is not None:
                                                    st.session_state.cag_ag_last_created_id = new_id
                                                    st.session_state[pick_key] = f"id:{int(new_id)}"
                                                    st.session_state["cag_ag_sticky_aid"] = int(new_id)
                                                    st.session_state.cag_ag_hidr_pick = None
                                                    st.session_state[offset_key] = _cag_list_offset_para_agendamento(
                                                        cliente_id=int(cliente_id),
                                                        aid=int(new_id),
                                                    )
                                                else:
                                                    st.session_state[offset_key] = 0
                                                st.session_state.cag_ag_flash = (
                                                    "Informações salvas com sucesso."
                                                )
                                                st.session_state.cag_ag_pending_novo_dialog = "ask"
                                                st.rerun()
                                            else:
                                                st.error(msg)
                                elif not hf_save:
                                    st.error("Hora início inválida (use HH:MM).")
                                else:
                                    sid = int(esc.split("|", 1)[0])
                                    d_iso = d_ag.isoformat()
                                    ok, msg = criar_agendamento_pre_venda(
                                        int(cliente_id),
                                        sid,
                                        d_iso,
                                        hi,
                                        hf_save,
                                        colab_ids,
                                        obs,
                                        None,
                                        tipo_atendimento=t_db,
                                        sala_virtual_disponibilizada=s_db,
                                    )
                                    if ok:
                                        new_id = _cag_ag_parse_novo_id(msg)
                                        if new_id is not None:
                                            st.session_state.cag_ag_last_created_id = new_id
                                            st.session_state[pick_key] = f"id:{int(new_id)}"
                                            st.session_state["cag_ag_sticky_aid"] = int(new_id)
                                            st.session_state.cag_ag_hidr_pick = None
                                            st.session_state[offset_key] = _cag_list_offset_para_agendamento(
                                                cliente_id=int(cliente_id),
                                                aid=int(new_id),
                                            )
                                        else:
                                            st.session_state[offset_key] = 0
                                        st.session_state.cag_ag_flash = "Informações salvas com sucesso."
                                        st.session_state.cag_ag_pending_novo_dialog = "ask"
                                        st.rerun()
                                    else:
                                        st.error(msg)
                        else:
                            st.error(
                                "Seleccione um agendamento na tabela (linha) ou use **Novo agendamento** "
                                "para criar um registo."
                            )

    # Flash, assistente de gravação e diálogo «Novo agendamento» — sempre abaixo do bloco do formulário
    # (incl. botão «Salvar Agendamento» e mensagens do `if submitted`).
    _cag_keys_ag = {
        "pick_key": ctx["pick_key"],
        "offset_key": ctx["offset_key"],
        "mode_k": ctx["mode_k"],
        "anc_k": ctx["anc_k"],
        "tbl_df_v_k": ctx["tbl_df_v_k"],
    }
    _cag_setor4_run_flash_wizards_pend(
        cliente_id=cliente_id, fv=fv, tem_cliente=tem_cliente, keys=_cag_keys_ag
    )


def _cag_setor4_render_list_island(*, cliente_id: int, fv: int, ctx: dict[str, Any]) -> None:
    pick_key = ctx["pick_key"]
    offset_key = ctx["offset_key"]
    tbl_df_v_k = ctx["tbl_df_v_k"]
    st.session_state.setdefault(tbl_df_v_k, 0)

    st.caption(
        "Clique numa linha da tabela para carregar o agendamento em **Dados do Agendamento** "
        "(acima). Use **Novo agendamento** para limpar o formulário para um novo registo. "
        "A listagem segue ordem estável (data, hora de início, número do registo); use os botões "
        "de página para navegar quando existir mais do que uma página."
    )

    raw_todos = listar_agendamentos(cliente_ids=[int(cliente_id)])
    todos_sorted = _cag_agrupar_listagem_cancelados_mesmo_pacote(raw_todos)
    n = len(todos_sorted)
    page_size = CAG_AG_LIST_PAGE_SIZE
    n_pages = max(1, (n + page_size - 1) // page_size)
    if offset_key not in st.session_state:
        st.session_state[offset_key] = 0
    off = int(st.session_state[offset_key])
    if off >= n and n > 0:
        off = max(0, ((n - 1) // page_size) * page_size)
        st.session_state[offset_key] = off
    chunk = todos_sorted[off : off + page_size]
    ids_all_page = _cag_ids_agendamentos_lista_expandidos(todos_sorted)
    rk_pick = str(st.session_state.get(pick_key) or "__novo__")
    if rk_pick.startswith("id:"):
        try:
            _pid_chk = int(rk_pick.split(":", 1)[1])
            if _pid_chk not in ids_all_page:
                st.session_state[pick_key] = "__novo__"
                st.session_state.pop("cag_ag_sticky_aid", None)
                st.session_state.cag_ag_need_hydrate = True
                st.rerun()
        except ValueError:
            st.session_state[pick_key] = "__novo__"
            st.session_state.pop("cag_ag_sticky_aid", None)
            st.session_state.cag_ag_need_hydrate = True
            st.rerun()

    lp1, lp2, lp3 = st.columns([1, 2, 1])
    with lp1:
        if st.button(
            "◀ Anterior (lista)",
            key=f"cag_ag_prev_{fv}",
            disabled=off <= 0,
            width="stretch",
        ):
            st.session_state[offset_key] = max(0, off - page_size)
            st.session_state[tbl_df_v_k] = int(st.session_state.get(tbl_df_v_k, 0)) + 1
            st.rerun()
    with lp2:
        st.caption(f"Página {off // page_size + 1} de {n_pages} · {n} registo(s)")
    with lp3:
        if st.button(
            "Seguinte (lista) ▶",
            key=f"cag_ag_next_{fv}",
            disabled=off + page_size >= n,
            width="stretch",
        ):
            st.session_state[offset_key] = min(max(0, n - page_size), off + page_size)
            st.session_state[tbl_df_v_k] = int(st.session_state.get(tbl_df_v_k, 0)) + 1
            st.rerun()

    if chunk:
        row_ids = [int(a["id"]) for a in chunk]
        df_ag = pd.DataFrame(
            {
                _CAG_AG_LIST_COL_CRIACAO: [
                    _cag_format_criacao_registo_pt(str(a.get("data_criacao_registo") or "").strip())
                    for a in chunk
                ],
                _CAG_AG_LIST_COL_DATA: [
                    _cag_format_data_pt(str(a["data_agendamento"])) for a in chunk
                ],
                _CAG_AG_LIST_COL_PAGAMENTO: [
                    (str(a.get("pagamento") or "").strip() or "—") for a in chunk
                ],
                "Nome do Cliente": [str(a.get("cliente_nome") or "").strip() for a in chunk],
                "Início": [str(a["hora_inicio"]) for a in chunk],
                "Fim": [str(a["hora_fim"]) for a in chunk],
                "Natureza": [str(a.get("servico_natureza") or "").strip() for a in chunk],
                "Serviço": [str(a["servico_nome"]) for a in chunk],
                _CAG_AG_LIST_COL_COLABORADOR: [
                    _cag_colaboradores_lista_texto(a) for a in chunk
                ],
                "Nome do Pacote": [
                    (str(a.get("nome_do_pacote") or "").strip() or "-") for a in chunk
                ],
                "Estado": [
                    _CAG_STATUS_DB_TO_LBL.get(str(a["status"]), str(a["status"])) for a in chunk
                ],
                "Tipo de Atendimento": [
                    _cag_tipo_atendimento_lista_label(str(a.get("tipo_atendimento") or ""))
                    for a in chunk
                ],
            }
        )
        tbl_v = int(st.session_state.get(tbl_df_v_k, 0))
        tbl_key = f"cag_ag_df_{cliente_id}_{tbl_v}"
        ev_df = st.dataframe(
            df_ag,
            width="stretch",
            on_select="rerun",
            selection_mode="single-row",
            key=tbl_key,
            hide_index=True,
        )
        sel_rows = _cag_df_selected_rows(ev_df, tbl_key)
        if sel_rows:
            lix = int(sel_rows[0])
            if 0 <= lix < len(row_ids):
                rid = row_ids[lix]
                prev_id = st.session_state.get("_cag_ag_df_prev_sel_id")
                if prev_id != rid:
                    st.session_state[pick_key] = f"id:{rid}"
                    st.session_state["cag_ag_sticky_aid"] = int(rid)
                    st.session_state._cag_ag_df_prev_sel_id = rid
                    st.session_state.cag_ag_need_hydrate = True
                    # Não incrementar `tbl_df_v_k` aqui: mudar a key do `st.dataframe` recria o widget e
                    # a selecção de linha desaparece; o utilizador perdia o contexto e o gravador podia cair
                    # em modo «novo» / `criar_agendamento_pre_venda` em reruns seguintes.
                    st.rerun()
    else:
        st.caption("Sem agendamentos para este cliente.")

    if st.button("Novo agendamento", key=f"cag_ag_tbl_novo_{cliente_id}_{fv}", type="secondary"):
        st.session_state[pick_key] = "__novo__"
        st.session_state.pop("cag_ag_sticky_aid", None)
        st.session_state.cag_ag_need_hydrate = True
        st.session_state[tbl_df_v_k] = int(st.session_state.get(tbl_df_v_k, 0)) + 1
        st.session_state.pop("_cag_ag_df_prev_sel_id", None)
        st.rerun()


def _render_cag_setor4_gestao_agendamentos(*, cliente_id: int, fv: int, tem_cliente: bool) -> None:
    """Setor 4: com cliente, calendário/formulário e listagem ficam no expander «Agendamentos»."""
    if tem_cliente:
        _cag_migrate_legacy_agenda_keys(cliente_id=int(cliente_id), fv=int(fv))
    keys = _cag_setor4_agenda_keys(cliente_id=cliente_id, fv=fv)
    _cag_flush_pending_lib_ag_edit()
    ctx = _cag_setor4_try_prepare_context(cliente_id=cliente_id, fv=fv, tem_cliente=tem_cliente, keys=keys)
    st.markdown(_cag_section_title_html("4. Agendamentos"), unsafe_allow_html=True)
    if ctx is None:
        st.info(
            "Seleccione ou **registe** um cliente na secção **3. Dados Pessoais** para criar ou alterar agendamentos."
        )
        st.caption("Seleccione ou registe um cliente para ver a listagem.")
        flash_sem_ctx = st.session_state.pop("cag_ag_flash", None)
        if flash_sem_ctx:
            st.success(str(flash_sem_ctx))
    else:
        # Calendário, formulário e listagem no mesmo expander (setor único «Agendamentos»).
        with st.expander("Agendamentos", expanded=True):
            _cag_flush_pending_form_ag_mutations()
            _cag_setor4_render_calendario_only(cliente_id=cliente_id, fv=fv, ctx=ctx)
            st.markdown(
                '<div class="bea-cv-cag-gap" aria-hidden="true"></div>',
                unsafe_allow_html=True,
            )
            dis_ag = _cag_setor4_render_selecao_edicao_block(fv=fv, ctx=ctx)
            _cag_setor4_render_dados_ag_form_e_wizards(
                cliente_id=cliente_id, fv=fv, tem_cliente=tem_cliente, ctx=ctx, dis_ag=dis_ag
            )
            st.markdown(
                '<div class="bea-cv-cag-gap" aria-hidden="true"></div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                _cag_section_title_html("Lista de agendamentos"),
                unsafe_allow_html=True,
            )
            _cag_setor4_render_list_island(cliente_id=cliente_id, fv=fv, ctx=ctx)


def render_page_clientes_agendamentos(*, render_back_and_breadcrumb) -> None:
    inject_constituicao_cag_page()
    _drill = st.session_state.pop("cag_home_drill_banner", None)
    if _drill:
        st.markdown(cag_home_drill_banner_html(str(_drill)), unsafe_allow_html=True)
    render_back_and_breadcrumb(
        ["Home", "Clientes e Agendamentos", "Cadastro"],
        back_key="bea_back_clientes_agendamentos",
    )
    if "cag_form_v" not in st.session_state:
        st.session_state.cag_form_v = 0
    if "cag_edit_id" not in st.session_state:
        st.session_state.cag_edit_id = None
    st.session_state.setdefault("cag_n_emergency", 1)
    if "_cag_post_save_lib_edit" in st.session_state:
        _lib = bool(st.session_state.pop("_cag_post_save_lib_edit"))
        st.session_state["cag_lib_edit"] = _lib
        st.session_state["_cag_lib_edit_prev"] = _lib
    st.session_state.setdefault("cag_lib_edit", True)

    _reload_fs = st.session_state.pop("_cag_reload_ficha_after_save", None)
    if _reload_fs is not None:
        _fk_sv, _eid_sv = _reload_fs
        _d_reload = obter_cliente_completo(int(_eid_sv))
        if _d_reload:
            _cag_carregar_ficha(str(_fk_sv), _d_reload)

    if st.session_state.pop("cag_busca_clear_pending", False):
        st.session_state["cag_busca_nome"] = ""
        st.session_state["cag_busca_nome_sug_list"] = []
        st.session_state["cag_busca_nif"] = ""
        st.session_state["cag_busca_email"] = ""
        st.session_state["cag_busca_tel_txt"] = ""
        st.session_state.pop("cag_busca_docintl", None)

    sug_cag = st.session_state.pop("cag_busca_suggestion_apply_id", None)
    if sug_cag is not None:
        _cag_tratar_sugestao_nome_clicada(int(sug_cag))

    st.markdown(
        '<h1 class="bea-cv-cag-h1">Cadastro de Clientes e Gestão de Agendamentos</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(_cag_section_title_html("1. Pesquisa de Clientes"), unsafe_allow_html=True)
    cag_busca_clicked = render_cliente_search_widget(
        key_prefix="cag_busca",
        button_type="secondary",
        minimal=True,
        pesquisa_unificada=True,
    )

    if cag_busca_clicked:
        nome_s = str(st.session_state.get("cag_busca_nome", "") or "").strip()
        nif_s = str(st.session_state.get("cag_busca_nif", "") or "").strip()
        em_s = str(st.session_state.get("cag_busca_email", "") or "").strip()
        tel_raw = str(st.session_state.get("cag_busca_tel_txt", "") or "").strip()
        use_tel = normalizar_telefone_legado_ou_e164(tel_raw) if tel_raw else ""

        msg_err: str | None = None
        if not nome_s and not nif_s and not em_s and not tel_raw:
            msg_err = "Indique nome, NIF, email ou telefone."
        elif em_s and not email_valido(em_s):
            msg_err = "❌ Email inválido para pesquisa."
        elif tel_raw and not use_tel:
            msg_err = "❌ Telefone inválido (ex.: +351912345678)."
        elif nif_s:
            ok_nf, msg_nf, _vx = normalizar_nif_armazenamento(
                nif_s, documento_identificacao_internacional=False
            )
            if not ok_nf:
                msg_err = msg_nf
        if msg_err:
            st.error(msg_err)
        else:
            merged: dict[int, str] = {}
            if nome_s:
                for cid, nm in buscar_clientes_por_prefixo_nome(nome_s, limit=80):
                    merged[int(cid)] = str(nm)
            for cid, nm in buscar_clientes_por_nif_email_telefone(
                nif=nif_s,
                email=em_s,
                telefone=use_tel,
                documento_internacional=False,
            ):
                merged[int(cid)] = str(nm)
            cands = sorted(merged.items(), key=lambda x: (x[1].lower(), x[0]))
            if len(cands) == 0:
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

    st.markdown(
        '<div class="bea-cv-cag-gap" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    st.markdown(_cag_section_title_html("2. Resumo do Cliente"), unsafe_allow_html=True)

    eid = st.session_state.cag_edit_id
    cli_data: dict | None = None
    if eid is not None:
        cli_data = obter_cliente_completo(int(eid))
        if cli_data is None:
            st.warning("Cliente seleccionado já não existe na base. Limpe o ecrã e pesquise novamente.")

    cid_resumo = int(eid) if eid is not None else 0
    resumo_ag = obter_resumo_agendamentos_cliente_setor2_proposta(cid_resumo)

    _render_cag_setor2_dados_pessoais(cli=cli_data)
    _render_cag_setor2_resumo_agendamentos(resumo=resumo_ag)

    st.markdown(
        '<div class="bea-cv-cag-gap" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
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

    st.markdown(
        '<div class="bea-cv-cag-gap" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    _render_cag_setor3_dados_pessoais_completo(
        fk=fk,
        tem_cliente=tem_cliente,
        eid=int(eid) if tem_cliente else None,
    )

    st.markdown(
        '<div class="bea-cv-cag-gap" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    _render_cag_setor4_gestao_agendamentos(cliente_id=cid_ag, fv=fv, tem_cliente=tem_cliente)
