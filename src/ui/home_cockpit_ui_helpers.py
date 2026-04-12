"""Fase 3 — HTML/CSS puro para Agenda do Dia e utilitários do cockpit (testáveis sem Streamlit)."""

from __future__ import annotations

import html
import re
from datetime import date, datetime, time, timedelta
from typing import Any

# Marcador para CSS :has() — ilha = 1ª coluna com este nó (Template Master)
HOME_ISLAND_MARK_CLASS = "bea-cv-home-island-mark"


def home_island_mark_html() -> str:
    return f'<p class="{HOME_ISLAND_MARK_CLASS}" aria-hidden="true"></p>'


def panorama_card_block_html(
    *,
    material_icon: str,
    title: str,
    value_display: str,
    testid: str,
) -> str:
    """
    Card Panorama Global: ícone Material em círculo 15% sálvia + título serif + valor (sans).
    `material_icon`: nome do glifo (ex.: euro_symbol).
    """
    ic = html.escape(str(material_icon).strip())
    ti = html.escape(str(title).strip())
    vd = html.escape(str(value_display))
    tid_raw = str(testid).strip()
    if not re.match(r"^[a-zA-Z0-9_.-]+$", tid_raw):
        tid_raw = "bea-home-pano-card"
    tid_esc = html.escape(tid_raw)
    return (
        f'<div class="bea-cv-pano-card" data-testid="{tid_esc}">'
        '<div class="bea-cv-pano-icon-wrap" aria-hidden="true">'
        f'<span class="material-symbols-outlined">{ic}</span></div>'
        f'<p class="bea-cv-pano-card-h">{ti}</p>'
        f'<div class="bea-cv-panorama-card-val">{vd}</div>'
        "</div>"
    )


def home_section_heading_html(*, text: str, tag: str = "h3") -> str:
    t = html.escape(str(text).strip())
    tg = tag if tag in ("h2", "h3", "h4") else "h3"
    return f'<{tg} class="bea-cv-home-block-h">{t}</{tg}>'


def _parse_time_hhmm(s: str) -> time | None:
    raw = (s or "").strip()
    if not raw:
        return None
    m = re.match(r"^(\d{1,2})[:.](\d{2})", raw)
    if not m:
        return None
    try:
        return time(int(m.group(1)), int(m.group(2)), 0)
    except ValueError:
        return None


def agendamento_slot_datetime(d: date, hora_raw: str) -> datetime | None:
    t = _parse_time_hhmm(hora_raw)
    if t is None:
        return None
    return datetime(d.year, d.month, d.day, t.hour, t.minute, t.second)


def row_is_proxima(
    now: datetime,
    row_date: date,
    hora_raw: str,
    *,
    minutos: int = 15,
) -> bool:
    slot = agendamento_slot_datetime(row_date, hora_raw)
    if slot is None:
        return False
    lim = now + timedelta(minutes=minutos)
    return now <= slot <= lim


def status_badge_html(status: str) -> tuple[str, str]:
    """Devolve (fragmento HTML do badge, rótulo legível)."""
    st = str(status or "").strip().upper()
    if st == "CONFIRMADO":
        return (
            '<span class="bea-cv-badge-verde">Confirmado</span>',
            "Confirmado",
        )
    if st in ("REALIZADO_PENDENTE_PGTO", "REALIZADO"):
        return (
            '<span class="bea-cv-badge-terracota">Em atendimento</span>',
            "Em atendimento",
        )
    if st == "PRE_AGENDADO":
        return (
            '<span class="bea-cv-badge-terracota">Pré-agendado</span>',
            "Pré-agendado",
        )
    if st == "AGENDADO":
        return (
            '<span class="bea-cv-badge-terracota">Pendente</span>',
            "Pendente",
        )
    if st == "CONCLUIDO":
        return (
            '<span class="bea-cv-badge-neutro">Concluído</span>',
            "Concluído",
        )
    lbl = st.replace("_", " ").title() if st else "—"
    return (
        f'<span class="bea-cv-badge-neutro">{html.escape(lbl)}</span>',
        lbl,
    )


def agenda_day_table_html(
    rows: list[dict[str, Any]],
    *,
    ref_date: date,
    now: datetime,
    prox_minutos: int = 15,
) -> str:
    """
    Tabela HTML da Agenda do Dia (Master: badges sálvia/terracota; destaque ≤ prox_minutos).
    `rows`: dicts compatíveis com `listar_agendamentos` (ordenados pelo chamador).
    """
    if not rows:
        return (
            '<div class="bea-cv-agenda-empty" data-testid="bea-home-agenda-empty">'
            "Sem compromissos para hoje nesta visão operacional."
            "</div>"
        )

    head = (
        "<table class='bea-cv-agenda-table' data-testid='bea-home-agenda-table'>"
        "<thead><tr>"
        "<th>Hora</th><th>Cliente</th><th>Serviço</th>"
        "<th>Colaborador</th><th>Estado</th>"
        "</tr></thead><tbody>"
    )
    parts = [head]
    for r in rows:
        hora = html.escape(str(r.get("hora_inicio") or ""))
        cli = html.escape(str(r.get("cliente_nome") or ""))
        srv = html.escape(str(r.get("servico_nome") or ""))
        nomes = r.get("colaboradores_nomes") or []
        col_txt = html.escape(", ".join(str(x) for x in nomes) if nomes else "—")
        st = str(r.get("status") or "")
        badge_fr, _ = status_badge_html(st)
        da = str(r.get("data_agendamento") or "")[:10]
        try:
            rd = date.fromisoformat(da) if da else ref_date
        except ValueError:
            rd = ref_date
        prox = row_is_proxima(now, rd, str(r.get("hora_inicio") or ""), minutos=prox_minutos)
        tr_cls = "bea-cv-agenda-tr-proxima" if prox else ""
        data_attr = ' data-bea-proxima="1"' if prox else ""
        parts.append(
            f"<tr class='{tr_cls}'{data_attr}>"
            f"<td>{hora}</td><td>{cli}</td><td>{srv}</td>"
            f"<td>{col_txt}</td><td>{badge_fr}</td></tr>"
        )
    parts.append("</tbody></table>")
    return "".join(parts)


def evolucao_atendimentos_html(
    *,
    variacao_delta: int,
    desempenho_pct_label: str,
    mes_atual: int,
    mes_ant: int,
) -> str:
    """Bloco direito «Evolução de Atendimentos» (valores já calculados)."""
    v_esc = html.escape(str(variacao_delta))
    p_esc = html.escape(desempenho_pct_label)
    ma = html.escape(str(mes_atual))
    mb = html.escape(str(mes_ant))
    return (
        '<div class="bea-cv-evolucao" data-testid="bea-home-evolucao">'
        '<p class="bea-cv-evolucao-linha">'
        '<span class="bea-cv-evolucao-k">Variação semanal (confirmados)</span>'
        f'<span class="bea-cv-evolucao-v bea-cv-evolucao-sage">{v_esc}</span>'
        "</p>"
        '<p class="bea-cv-evolucao-linha">'
        '<span class="bea-cv-evolucao-k">Desempenho mensal (concluídos)</span>'
        f'<span class="bea-cv-evolucao-pill">{p_esc}</span>'
        "</p>"
        '<p class="bea-cv-evolucao-foot">'
        f"Mês corrente: {ma} · Mês anterior: {mb}"
        "</p>"
        "</div>"
    )
