"""Gestão de repasses (Financeiro) — consulta sobre repasse_linhas + agendamentos."""

from __future__ import annotations

import sqlite3

import pytest

from src.database.connection import create_tables, get_connection
from src.modules.colaborador import cadastrar_colaborador
from src.modules.financeiro_repasses_colaboradores import (
    aplicar_edicao_repasse_linhas_gestao,
    listar_linhas_gestao_repasses,
    marcar_repasses_como_pagos,
)


@pytest.fixture()
def rep_conn(tmp_path, monkeypatch):
    db = tmp_path / "fin_repasse.db"
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(db))
    create_tables()
    c = get_connection()
    assert c is not None
    yield c
    c.close()


def _seed_repasse_row(conn: sqlite3.Connection) -> tuple[int, int]:
    """Devolve (colaborador_id, servico_id) após inserir venda + agendamento CONCLUIDO + repasse_linhas."""
    cur = conn.cursor()
    cur.execute("SELECT id, nome, natureza FROM servicos ORDER BY id LIMIT 1")
    srow = cur.fetchone()
    assert srow is not None
    sid = int(srow[0])

    ok, _ = cadastrar_colaborador(
        nome="Colab Repasse Fin",
        sexo="Feminino",
        data_nascimento="1990-05-10",
        endereco_rua="Rua X",
        endereco_numero="10",
        endereco_complemento="",
        codigo_postal="4700-223",
        concelho="Braga",
        freguesia="Sé",
        distrito="",
        pais="Portugal",
        email="colab.rep.fin@beaba.test",
        nif_ou_documento="123456789",
        identificacao_internacional=False,
        numero_contato="11977665544",
        observacoes="",
        servicos_repasse=[(sid, 25.0, "2026-01-01")],
    )
    assert ok
    cur.execute("SELECT id FROM colaboradores WHERE nome = ?", ("Colab Repasse Fin",))
    cid = int(cur.fetchone()[0])

    cur.execute(
        "INSERT INTO clientes (nome, whatsapp) VALUES (?, ?)",
        ("Cliente Rep Fin", "+351919001199"),
    )
    cli_id = int(cur.lastrowid)

    cur.execute(
        """
        INSERT INTO vendas (
            cliente_id, estado_pagamento,
            subtotal_bruto_centavos, subtotal_apos_descontos_linha_centavos,
            desconto_global_centavos_aplicado, total_final_centavos, observacoes
        ) VALUES (?, 'integral', 10000, 10000, 0, 10000, '')
        """,
        (cli_id,),
    )
    vid = int(cur.lastrowid)

    cur.execute(
        """
        INSERT INTO venda_itens (
            venda_id, servico_id, ordem, quantidade, preco_unitario_centavos,
            nome_snapshot, descricao_snapshot, unidade_medida_snapshot,
            subtotal_bruto_centavos, total_linha_centavos
        ) VALUES (?, ?, 1, 1, 10000, 'Snap', '', 'un', 10000, 10000)
        """,
        (vid, sid),
    )
    viid = int(cur.lastrowid)

    cur.execute(
        """
        INSERT INTO agendamentos (
            venda_id, venda_item_id, cliente_id, servico_id, pacote_sessao_id,
            tipo_origem, data_agendamento, hora_inicio, hora_fim, status,
            devolver_ao_buffer, observacoes, modo_origem
        ) VALUES (?, ?, ?, ?, NULL, 'sessao_avulsa', '2026-03-20', '09:00', '10:00',
            'CONCLUIDO', 0, '', 'credito_venda')
        """,
        (vid, viid, cli_id, sid),
    )
    ag_id = int(cur.lastrowid)

    cur.execute(
        "INSERT INTO agendamento_colaboradores (agendamento_id, colaborador_id, ordem) VALUES (?, ?, 1)",
        (ag_id, cid),
    )

    cur.execute(
        """
        INSERT INTO repasse_linhas (
            agendamento_id, colaborador_id, base_calculo_centavos,
            percentual_bp, valor_repasse_centavos, status_repasse
        ) VALUES (?, ?, 10000, 2500, 2500, 'PENDENTE_REPASSE')
        """,
        (ag_id, cid),
    )
    conn.commit()
    return cid, sid


def test_listar_repasses_vazio(rep_conn: sqlite3.Connection) -> None:
    assert listar_linhas_gestao_repasses(rep_conn) == []


def test_listar_repasses_concluido_e_filtros(rep_conn: sqlite3.Connection) -> None:
    cid, sid = _seed_repasse_row(rep_conn)
    rows = listar_linhas_gestao_repasses(rep_conn)
    assert len(rows) == 1
    assert rows[0]["colaborador_nome"] == "Colab Repasse Fin"
    assert int(rows[0]["base_calculo_centavos"]) == 10000
    assert int(rows[0]["valor_repasse_centavos"]) == 2500
    assert rows[0]["data_execucao_dm"] == "20/03/2026"
    assert rows[0]["repasse_pago_label"] == "Não"
    assert rows[0]["data_pagamento_repasse_dm"] == ""
    assert int(rows[0]["repasse_linha_id"]) > 0

    rows_m = listar_linhas_gestao_repasses(rep_conn, mes=3, ano=2026)
    assert len(rows_m) == 1

    rows_m2 = listar_linhas_gestao_repasses(rep_conn, mes=4, ano=2026)
    assert rows_m2 == []

    rows_c = listar_linhas_gestao_repasses(rep_conn, colaborador_ids=[cid])
    assert len(rows_c) == 1

    rows_x = listar_linhas_gestao_repasses(rep_conn, colaborador_ids=[cid + 9999])
    assert rows_x == []

    rows_s = listar_linhas_gestao_repasses(rep_conn, servico_ids=[sid])
    assert len(rows_s) == 1

    rows_empty_svc = listar_linhas_gestao_repasses(rep_conn, servico_ids=[])
    assert rows_empty_svc == []


def test_listar_repasses_filtro_natureza(rep_conn: sqlite3.Connection) -> None:
    _cid, sid = _seed_repasse_row(rep_conn)
    cur = rep_conn.cursor()
    nat = str(cur.execute("SELECT natureza FROM servicos WHERE id = ?", (sid,)).fetchone()[0] or "")
    assert nat
    rows_ok = listar_linhas_gestao_repasses(rep_conn, naturezas=[nat])
    assert len(rows_ok) == 1
    rows_bad = listar_linhas_gestao_repasses(rep_conn, naturezas=["__natureza_inexistente__"])
    assert rows_bad == []


def test_realizado_pendente_pgto_incluido(rep_conn: sqlite3.Connection) -> None:
    cid, sid = _seed_repasse_row(rep_conn)
    cur = rep_conn.cursor()
    cur.execute("UPDATE agendamentos SET status = 'REALIZADO_PENDENTE_PGTO' WHERE id = (SELECT MAX(id) FROM agendamentos)")
    rep_conn.commit()
    rows = listar_linhas_gestao_repasses(rep_conn)
    assert len(rows) == 1


def test_metadados_servicos_repasse_nat_esp_e_sem_especialidade(rep_conn: sqlite3.Connection) -> None:
    """Filtros em cadeia usados na UI: natureza, especialidade e «(Sem especialidade)»."""
    from src.modules.financeiro_repasses_colaboradores import (
        REPASSE_ESP_SEM_LABEL,
        filtra_metadados_servicos_por_especialidades,
        filtra_metadados_servicos_por_naturezas,
        listar_servicos_metadados_para_filtro_repasse,
    )

    cur = rep_conn.cursor()
    cur.execute(
        "INSERT INTO especialidades (natureza, nome, descritivo, ativo, ordem) VALUES (?, ?, '', 1, 0)",
        ("NMetaNat", "NMetaEspA"),
    )
    e1 = int(cur.lastrowid)
    cur.execute(
        "INSERT INTO especialidades (natureza, nome, descritivo, ativo, ordem) VALUES (?, ?, '', 1, 0)",
        ("NMetaNat", "NMetaEspB"),
    )
    e2 = int(cur.lastrowid)
    cur.execute(
        "INSERT INTO servicos (nome, natureza, especialidade_id) VALUES (?, ?, ?)",
        ("TMetaRep_SvA", "NMetaNat", e1),
    )
    id_a = int(cur.lastrowid)
    cur.execute(
        "INSERT INTO servicos (nome, natureza, especialidade_id) VALUES (?, ?, ?)",
        ("TMetaRep_SvB", "NMetaNat", e2),
    )
    id_b = int(cur.lastrowid)
    cur.execute(
        "INSERT INTO servicos (nome, natureza, especialidade_id) VALUES (?, ?, ?)",
        ("TMetaRep_SvSemEsp", "NMetaNatB", None),
    )
    id_c = int(cur.lastrowid)
    rep_conn.commit()

    meta = listar_servicos_metadados_para_filtro_repasse(rep_conn)
    by_id = {int(r[0]): r for r in meta}
    assert by_id[id_a][2] == "NMetaNat" and str(by_id[id_a][3]) == "NMetaEspA"

    r_nat = filtra_metadados_servicos_por_naturezas(meta, ["NMetaNat"])
    assert {int(r[0]) for r in r_nat} == {id_a, id_b}

    r_esp = filtra_metadados_servicos_por_especialidades(r_nat, ["NMetaEspA"])
    assert {int(r[0]) for r in r_esp} == {id_a}

    r_nb = filtra_metadados_servicos_por_naturezas(meta, ["NMetaNatB"])
    r_sem = filtra_metadados_servicos_por_especialidades(r_nb, [REPASSE_ESP_SEM_LABEL])
    assert {int(r[0]) for r in r_sem} == {id_c}


def test_marcar_repasses_como_pagos_ok(rep_conn: sqlite3.Connection) -> None:
    _cid, _sid = _seed_repasse_row(rep_conn)
    rows = listar_linhas_gestao_repasses(rep_conn)
    rid = int(rows[0]["repasse_linha_id"])
    ok, msg, n = marcar_repasses_como_pagos(rep_conn, [rid], data_pagamento_iso10="2026-04-10")
    assert ok and n == 1 and "actualizada" in msg.casefold()
    rows2 = listar_linhas_gestao_repasses(rep_conn)
    assert rows2[0]["repasse_pago_label"] == "Sim"
    assert rows2[0]["data_pagamento_repasse_iso"] == "2026-04-10"


def test_marcar_repasses_como_pagos_sem_actualizacao_se_ja_pago(rep_conn: sqlite3.Connection) -> None:
    _cid, _sid = _seed_repasse_row(rep_conn)
    rid = int(listar_linhas_gestao_repasses(rep_conn)[0]["repasse_linha_id"])
    assert marcar_repasses_como_pagos(rep_conn, [rid], data_pagamento_iso10="2026-04-01")[0]
    ok2, _msg2, n2 = marcar_repasses_como_pagos(rep_conn, [rid], data_pagamento_iso10="2026-04-02")
    assert not ok2 and n2 == 0


def test_aplicar_edicao_repasse_linhas_gestao(rep_conn: sqlite3.Connection) -> None:
    _cid, _sid = _seed_repasse_row(rep_conn)
    rid = int(listar_linhas_gestao_repasses(rep_conn)[0]["repasse_linha_id"])
    assert marcar_repasses_como_pagos(rep_conn, [rid], data_pagamento_iso10="2026-05-01")[0]
    ok, msg, _n = aplicar_edicao_repasse_linhas_gestao(rep_conn, [(rid, False, None)])
    assert ok
    r = listar_linhas_gestao_repasses(rep_conn)[0]
    assert r["repasse_pago_label"] == "Não"
    assert r["data_pagamento_repasse_iso"] == ""


def test_aplicar_edicao_repasse_sim_sem_data_falha(rep_conn: sqlite3.Connection) -> None:
    _cid, _sid = _seed_repasse_row(rep_conn)
    rid = int(listar_linhas_gestao_repasses(rep_conn)[0]["repasse_linha_id"])
    ok, msg, ntot = aplicar_edicao_repasse_linhas_gestao(rep_conn, [(rid, True, "")])
    assert not ok
    assert ntot == 0
