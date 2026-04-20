"""Testes unitários — disponibilidade de colaboradores (planos, regras, alertas, calendário)."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from src.modules.colaborador import cadastrar_colaborador, listar_servicos

_tel_seq = 0
from src.modules.colaborador_disponibilidade import (
    adicionar_regra,
    agregar_slots_calendario_mestre,
    confirmar_plano_publicado,
    criar_ou_atualizar_rascunho,
    dias_ate_fim_validade,
    expandir_slots_plano,
    listar_alertas_confirmados,
    niveis_alerta_validade,
    obter_rascunho_aberto,
)


def _primeiro_servico_id() -> int:
    s = listar_servicos()
    assert s
    return int(s[0][0])


def _colab_minimal(unique: str) -> tuple[bool, str]:
    global _tel_seq
    _tel_seq += 1
    tail = 910_000_000 + (_tel_seq % 89_999_999)
    tel = f"+351{tail:09d}"
    sid = _primeiro_servico_id()
    return cadastrar_colaborador(
        nome=f"Disp Test {unique}",
        sexo="Masculino",
        data_nascimento="1990-01-01",
        endereco_rua="Rua A",
        endereco_numero="1",
        endereco_complemento="",
        codigo_postal="4000-001",
        concelho="Porto",
        freguesia="Paranhos",
        distrito="Porto",
        pais="Portugal",
        email=f"disp_{unique}@t.test",
        numero_contato=tel,
        observacoes="",
        servicos_repasse=[(sid, 40.0, date.today().isoformat())],
        nif_ou_documento=f"DOC-DISP-{unique}",
        identificacao_internacional=True,
        documento_passaporte_residencia_cc="",
        atividade_economica_aberta=False,
        atividade_economica_codigo="",
        atividade_economica_descricao="",
        contrato_prestacao_assinado=False,
        contrato_prestacao_data_assinatura="",
        iban_dados_bancarios="PT50000201231234567890152",
    )


def test_dias_ate_fim_validade():
    h = date(2026, 4, 1)
    assert dias_ate_fim_validade(hoje=h, valido_ate=date(2026, 4, 16)) == 15


def test_niveis_alerta_exactamente_15_10_5():
    h = date(2026, 4, 1)
    assert niveis_alerta_validade(hoje=h, valido_ate=date(2026, 4, 16)) == (15,)
    assert niveis_alerta_validade(hoje=h, valido_ate=date(2026, 4, 11)) == (10,)
    assert niveis_alerta_validade(hoje=h, valido_ate=date(2026, 4, 6)) == (5,)
    assert niveis_alerta_validade(hoje=h, valido_ate=date(2026, 4, 20)) == ()


def test_expandir_slots_semanal_e_custom():
    d0 = date(2026, 4, 6)  # segunda
    d1 = date(2026, 4, 12)
    regras = [
        {"tipo": "semanal", "dia_semana": 0, "hora_inicio": "09:00", "hora_fim": "12:00"},
        {
            "tipo": "custom_intervalo",
            "intervalo_de": "2026-04-07",
            "intervalo_ate": "2026-04-09",
            "dias_mascara": "2",
            "hora_inicio": "14:00",
            "hora_fim": "16:00",
        },
    ]
    m = expandir_slots_plano(valido_de=d0, valido_ate=d1, regras=regras)
    assert "2026-04-06" in m
    assert any(x[0] == "09:00" for x in m["2026-04-06"])
    # 2026-04-08 is Wednesday = 2
    assert "2026-04-08" in m
    assert any(x[0] == "14:00" for x in m["2026-04-08"])


def test_confirmar_arquiva_sobreposto():
    u1, u2 = uuid.uuid4().hex[:10], uuid.uuid4().hex[:10]
    ok, _ = _colab_minimal(u1)
    assert ok
    ok2, _ = _colab_minimal(u2)
    assert ok2
    from src.database.connection import get_connection

    conn = get_connection()
    assert conn
    try:
        cur = conn.cursor()
        id_a = int(
            cur.execute("SELECT id FROM colaboradores WHERE nome = ?", (f"Disp Test {u1}",)).fetchone()[0]
        )
        id_b = int(
            cur.execute("SELECT id FROM colaboradores WHERE nome = ?", (f"Disp Test {u2}",)).fetchone()[0]
        )
    finally:
        conn.close()

    ok_p1, _, pid1 = criar_ou_atualizar_rascunho(
        id_a, valido_de="2026-05-01", valido_ate="2026-05-31"
    )
    assert ok_p1 and pid1
    assert confirmar_plano_publicado(int(pid1))[0]

    ok_p2, _, pid2 = criar_ou_atualizar_rascunho(
        id_a, valido_de="2026-05-15", valido_ate="2026-06-15"
    )
    assert ok_p2 and pid2
    assert confirmar_plano_publicado(int(pid2))[0]

    conn = get_connection()
    assert conn
    try:
        st1 = conn.execute(
            "SELECT estado FROM colaborador_disponibilidade_plano WHERE id = ?", (int(pid1),)
        ).fetchone()[0]
        st2 = conn.execute(
            "SELECT estado FROM colaborador_disponibilidade_plano WHERE id = ?", (int(pid2),)
        ).fetchone()[0]
        assert st1 == "arquivado"
        assert st2 == "confirmado"
    finally:
        conn.close()

    ok_p3, _, pid3 = criar_ou_atualizar_rascunho(id_b, valido_de="2026-07-01", valido_ate="2026-07-20")
    assert ok_p3 and pid3
    adicionar_regra(int(pid3), tipo="semanal", hora_inicio="10:00", hora_fim="11:00", dia_semana=1)
    assert confirmar_plano_publicado(int(pid3))[0]
    h = date(2026, 7, 5)
    alerts = listar_alertas_confirmados(id_b, hoje=h)
    assert any(a["dias"] == 15 for a in alerts)

    by = agregar_slots_calendario_mestre(
        data_de="2026-07-07",
        data_ate="2026-07-13",
        colaborador_ids=[id_b],
    )
    assert "2026-07-07" in by
    assert len(by["2026-07-07"]) >= 1


def test_obter_rascunho_aberto():
    u3 = uuid.uuid4().hex[:10]
    ok, _ = _colab_minimal(u3)
    assert ok
    from src.database.connection import get_connection

    conn = get_connection()
    assert conn
    try:
        cid = int(
            conn.execute("SELECT id FROM colaboradores WHERE nome = ?", (f"Disp Test {u3}",)).fetchone()[0]
        )
    finally:
        conn.close()
    ok_d, _, pid = criar_ou_atualizar_rascunho(cid, valido_de="2026-08-01", valido_ate="2026-08-10")
    assert ok_d
    r = obter_rascunho_aberto(cid)
    assert r and int(r["id"]) == int(pid)
