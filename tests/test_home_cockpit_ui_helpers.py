"""Fase 3 — HTML da Agenda do Dia e bloco de evolução (sem Streamlit)."""

from __future__ import annotations

from datetime import date, datetime

from src.ui.home_cockpit_ui_helpers import (
    agenda_day_table_html,
    evolucao_atendimentos_html,
    row_is_proxima,
    status_badge_html,
)


def test_agenda_empty_wrapper():
    h = agenda_day_table_html([], ref_date=date(2026, 4, 12), now=datetime(2026, 4, 12, 10, 0))
    assert "bea-home-agenda-empty" in h


def test_agenda_confirmado_badge_verde():
    h = agenda_day_table_html(
        [
            {
                "id": 1,
                "hora_inicio": "10:00",
                "cliente_nome": "Ana",
                "servico_nome": "Sessão",
                "colaboradores_nomes": ["Bia"],
                "status": "CONFIRMADO",
                "data_agendamento": "2026-04-12",
            }
        ],
        ref_date=date(2026, 4, 12),
        now=datetime(2026, 4, 12, 9, 0),
    )
    assert "bea-cv-badge-verde" in h
    assert "bea-cv-agenda-tr-proxima" not in h


def test_agenda_proxima_15min():
    h = agenda_day_table_html(
        [
            {
                "id": 2,
                "hora_inicio": "09:10",
                "cliente_nome": "Rui",
                "servico_nome": "Massagem",
                "colaboradores_nomes": [],
                "status": "AGENDADO",
                "data_agendamento": "2026-04-12",
            }
        ],
        ref_date=date(2026, 4, 12),
        now=datetime(2026, 4, 12, 9, 0),
        prox_minutos=15,
    )
    assert "bea-cv-agenda-tr-proxima" in h
    assert 'data-bea-proxima="1"' in h


def test_row_is_proxima_limites():
    d = date(2026, 4, 12)
    now = datetime(2026, 4, 12, 9, 0)
    assert row_is_proxima(now, d, "09:10", minutos=15) is True
    assert row_is_proxima(now, d, "09:16", minutos=15) is False


def test_status_badge_terracota_em_atendimento():
    h, _ = status_badge_html("REALIZADO_PENDENTE_PGTO")
    assert "terracota" in h


def test_evolucao_html_smoke():
    h = evolucao_atendimentos_html(
        variacao_delta=2,
        desempenho_pct_label="+1.0 %",
        mes_atual=5,
        mes_ant=4,
    )
    assert "bea-home-evolucao" in h
    assert "Variação semanal" in h
