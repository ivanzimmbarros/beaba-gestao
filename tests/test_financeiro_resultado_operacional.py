"""Financeiro — resultado operacional consolidado (sector 1)."""

from __future__ import annotations

import pytest

from src.database.connection import create_tables, get_connection
from src.modules.financeiro_categorias_gasto import salvar_linha1_tres_textos
from src.modules.financeiro_lancamentos_gasto import inserir_lancamentos_operacionais
from src.modules.financeiro_resultado_operacional import (
    agregar_resultado_operacional_consolidado,
)


@pytest.fixture()
def ro_conn(tmp_path, monkeypatch):
    db = tmp_path / "fin_ro.db"
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(db))
    create_tables()
    c = get_connection()
    assert c is not None
    yield c
    c.close()


def test_agregar_vazio_zeros(ro_conn: sqlite3.Connection) -> None:
    out = agregar_resultado_operacional_consolidado(
        ro_conn,
        mes_referencia=None,
        ano_referencia=None,
        cenario_entradas="convertido",
    )
    assert out["entradas_centavos"] == 0
    assert out["gastos_real_centavos"] == 0
    assert out["repasses_centavos"] == 0
    assert out["saldos_exposicao_centavos"] == 0
    assert out["resultado_fluxo_centavos"] == 0


def test_gastos_real_filtra_competencia(ro_conn: sqlite3.Connection) -> None:
    salvar_linha1_tres_textos(ro_conn, "CCRO", "NATRO", "TIPRO")
    ro_conn.commit()
    tid = int(
        ro_conn.execute(
            "SELECT t.id FROM financeiro_tipo_gasto t "
            "JOIN financeiro_natureza n ON n.id = t.natureza_id WHERE t.nome = 'TIPRO'"
        ).fetchone()[0]
    )
    n, err = inserir_lancamentos_operacionais(
        ro_conn,
        [tid],
        valor_centavos=1_200,
        data_competencia_iso="2026-04-10",
        status_lancamento="Pago",
        classe_lancamento="real",
        replicar=False,
        meses_duracao=1,
    )
    assert not err and n == 1
    ro_conn.commit()

    out_abril = agregar_resultado_operacional_consolidado(
        ro_conn,
        mes_referencia=4,
        ano_referencia=2026,
        cenario_entradas="convertido",
    )
    assert out_abril["gastos_real_centavos"] == 1_200

    out_marco = agregar_resultado_operacional_consolidado(
        ro_conn,
        mes_referencia=3,
        ano_referencia=2026,
        cenario_entradas="convertido",
    )
    assert out_marco["gastos_real_centavos"] == 0


def test_meta_nao_conta_gastos(ro_conn: sqlite3.Connection) -> None:
    salvar_linha1_tres_textos(ro_conn, "CCM", "NATM", "TIPM")
    ro_conn.commit()
    tid = int(
        ro_conn.execute(
            "SELECT t.id FROM financeiro_tipo_gasto t "
            "JOIN financeiro_natureza n ON n.id = t.natureza_id WHERE t.nome = 'TIPM'"
        ).fetchone()[0]
    )
    n, err = inserir_lancamentos_operacionais(
        ro_conn,
        [tid],
        valor_centavos=99,
        data_competencia_iso="2026-05-01",
        status_lancamento="Agendado",
        classe_lancamento="meta",
        replicar=False,
        meses_duracao=1,
    )
    assert not err and n == 1
    ro_conn.commit()
    out = agregar_resultado_operacional_consolidado(
        ro_conn,
        mes_referencia=5,
        ano_referencia=2026,
        cenario_entradas="convertido",
    )
    assert out["gastos_real_centavos"] == 0


def test_cenario_recebido_vs_convertido(ro_conn: sqlite3.Connection) -> None:
    """Uma venda integral: convertido = total linha; recebido = total recebido (coincide)."""
    cur = ro_conn.cursor()
    cur.execute(
        "INSERT INTO especialidades (natureza, nome, descritivo) VALUES (?, ?, ?)",
        ("Sessão", "EspRO", ""),
    )
    eid = int(cur.lastrowid)
    cur.execute(
        """
        INSERT INTO servicos (nome, natureza, especialidade_id)
        VALUES (?, 'Sessão', ?)
        """,
        ("SrvRO", eid),
    )
    sid = int(cur.lastrowid)
    cur.execute(
        """
        INSERT INTO colaboradores (
            nome, sexo, data_nascimento, email, whatsapp,
            endereco_rua, endereco_numero, codigo_postal, concelho, freguesia
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "Col RO",
            "Feminino",
            "1990-05-01",
            "ro@test.local",
            "+351910000088",
            "Rua",
            "1",
            "4000-001",
            "Porto",
            "Centro",
        ),
    )
    col_id = int(cur.lastrowid)
    cur.execute(
        """
        INSERT INTO colaborador_servicos (
            colaborador_id, servico_id, percentual_centesimos, ordem, data_insercao_linha
        ) VALUES (?, ?, 1000, 1, '2026-01-01')
        """,
        (col_id, sid),
    )
    cur.execute("INSERT INTO clientes (nome, whatsapp) VALUES (?, ?)", ("CliRO", "+351910000077"))
    cid = int(cur.lastrowid)
    cur.execute(
        """
        INSERT INTO vendas (
            cliente_id, data_registo, estado_pagamento,
            subtotal_bruto_centavos, subtotal_apos_descontos_linha_centavos,
            desconto_global_tipo, desconto_global_valor, desconto_global_centavos_aplicado,
            total_final_centavos, observacoes, credito_abatido_centavos
        ) VALUES (?, '2026-06-15 12:00:00', 'integral',
            5000, 5000, NULL, NULL, 0, 5000, '', 0)
        """,
        (cid,),
    )
    vid = int(cur.lastrowid)
    cur.execute(
        """
        INSERT INTO venda_itens (
            venda_id, servico_id, ordem, quantidade, preco_unitario_centavos,
            nome_snapshot, descricao_snapshot, unidade_medida_snapshot,
            is_bonus, desconto_linha_tipo, desconto_linha_valor,
            subtotal_bruto_centavos, desconto_linha_centavos, total_linha_centavos,
            colaborador_id, pagamento_parcial
        ) VALUES (?, ?, 1, 1, 5000, 'Snap', '', 'un', 0, NULL, NULL, 5000, 0, 5000, ?, 0)
        """,
        (vid, sid, col_id),
    )
    ro_conn.commit()

    oc = agregar_resultado_operacional_consolidado(
        ro_conn,
        mes_referencia=6,
        ano_referencia=2026,
        cenario_entradas="convertido",
    )
    or_ = agregar_resultado_operacional_consolidado(
        ro_conn,
        mes_referencia=6,
        ano_referencia=2026,
        cenario_entradas="recebido",
    )
    assert oc["entradas_centavos"] == 5_000
    assert or_["entradas_centavos"] == 5_000

    cur.execute("UPDATE vendas SET estado_pagamento = 'parcial' WHERE id = ?", (vid,))
    cur.execute(
        """
        INSERT INTO venda_pagamento_linhas (venda_id, ordem, tipo_meio, valor_centavos)
        VALUES (?, 1, 'CARTAO_CREDITO', 2000)
        """,
        (vid,),
    )
    ro_conn.commit()
    oc2 = agregar_resultado_operacional_consolidado(
        ro_conn,
        mes_referencia=6,
        ano_referencia=2026,
        cenario_entradas="convertido",
    )
    or2 = agregar_resultado_operacional_consolidado(
        ro_conn,
        mes_referencia=6,
        ano_referencia=2026,
        cenario_entradas="recebido",
    )
    assert oc2["entradas_centavos"] == 5_000
    assert or2["entradas_centavos"] == 2_000
