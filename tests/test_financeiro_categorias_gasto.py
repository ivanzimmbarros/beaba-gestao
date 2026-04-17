"""Regras e persistência — categorias de gasto operacional (Financeiro)."""

from __future__ import annotations

import sqlite3

import pytest

from src.database.connection import create_tables, get_connection
from src.modules.financeiro_categorias_gasto import (
    MSG_PEDIR_CONFIRMACAO_ALTERACAO,
    MSG_REGISTRO_DUPLICADO,
    atualizar_tipo_a_partir_formulario,
    listar_linhas_tabela_tipos,
    listar_naturezas_ativas_so_nome,
    listar_tipos_gasto_ativos_so_nome,
    natureza_tem_lancamentos,
    obter_tipo_com_caminho,
    resolver_salvar_formulario,
    salvar_linha1_tres_textos,
    tipo_tem_lancamentos,
)


@pytest.fixture()
def fin_conn(tmp_path, monkeypatch):
    db = tmp_path / "fin_cat.db"
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(db))
    create_tables()
    c = get_connection()
    assert c is not None
    yield c
    c.close()


def test_linha1_cria_hierarquia_completa(fin_conn: sqlite3.Connection):
    ok, msg = salvar_linha1_tres_textos(fin_conn, "  CC-A ", "Nat-1", "Tipo-X")
    assert ok and "Tipo de Gasto criado com sucesso" in msg
    fin_conn.commit()
    rows = listar_linhas_tabela_tipos(fin_conn)
    assert len(rows) == 1
    assert rows[0]["centro_nome"] == "CC-A"
    assert rows[0]["natureza_nome"] == "Nat-1"
    assert rows[0]["tipo_nome"] == "Tipo-X"


def test_linha1_duplicado_tipo_mesma_natureza_rejeita(fin_conn: sqlite3.Connection):
    salvar_linha1_tres_textos(fin_conn, "C", "N", "T")
    fin_conn.commit()
    ok, msg = salvar_linha1_tres_textos(fin_conn, "C", "N", "T")
    assert not ok
    assert msg == MSG_REGISTRO_DUPLICADO


def test_resolver_prioridade_edicao_sobre_linha1(fin_conn: sqlite3.Connection):
    salvar_linha1_tres_textos(fin_conn, "C", "N", "T1")
    fin_conn.commit()
    tid = listar_linhas_tabela_tipos(fin_conn)[0]["tipo_id"]
    ok, msg = resolver_salvar_formulario(
        fin_conn,
        linha1_cc="C",
        linha1_natureza="",
        linha1_tipo="",
        linha2_centro_id=None,
        linha2_natureza_texto="",
        linha3_centro_id=obter_tipo_com_caminho(fin_conn, tid)["centro_custo_id"],
        linha3_natureza_id=obter_tipo_com_caminho(fin_conn, tid)["natureza_id"],
        linha3_tipo_texto="T1-alt",
        editando_tipo_id=tid,
        confirmar_alteracao=True,
    )
    assert ok and "Dados alterados com sucesso" in msg
    fin_conn.commit()
    path = obter_tipo_com_caminho(fin_conn, tid)
    assert path is not None
    assert path["tipo_nome"] == "T1-alt"


def test_resolver_linha3_segundo_tipo_mesma_natureza_insere(fin_conn: sqlite3.Connection):
    """Sem id de edição, novo nome na mesma natureza cria segunda linha."""
    salvar_linha1_tres_textos(fin_conn, "C", "N", "T1")
    fin_conn.commit()
    tid = listar_linhas_tabela_tipos(fin_conn)[0]["tipo_id"]
    path0 = obter_tipo_com_caminho(fin_conn, tid)
    assert path0 is not None
    ok, msg = resolver_salvar_formulario(
        fin_conn,
        linha1_cc="C",
        linha1_natureza="",
        linha1_tipo="",
        linha2_centro_id=None,
        linha2_natureza_texto="",
        linha3_centro_id=path0["centro_custo_id"],
        linha3_natureza_id=path0["natureza_id"],
        linha3_tipo_texto="T2",
        editando_tipo_id=None,
    )
    assert ok and "Tipo de Gasto criado com sucesso" in msg
    fin_conn.commit()
    rows = listar_linhas_tabela_tipos(fin_conn)
    assert len(rows) == 2
    nomes = sorted(r["tipo_nome"] for r in rows)
    assert nomes == ["T1", "T2"]


def test_linha2_natureza_duplicado_ignora_acentos(fin_conn: sqlite3.Connection):
    salvar_linha1_tres_textos(fin_conn, "Salas", "Operação", "Arrendamento")
    fin_conn.commit()
    tid = listar_linhas_tabela_tipos(fin_conn)[0]["tipo_id"]
    cid = int(obter_tipo_com_caminho(fin_conn, tid)["centro_custo_id"])
    ok, msg = resolver_salvar_formulario(
        fin_conn,
        linha1_cc="",
        linha1_natureza="",
        linha1_tipo="",
        linha2_centro_id=cid,
        linha2_natureza_texto="Operacao",
        linha3_centro_id=None,
        linha3_natureza_id=None,
        linha3_tipo_texto="",
        editando_tipo_id=None,
    )
    assert not ok and msg == MSG_REGISTRO_DUPLICADO


def test_tipo_duplicado_case_insensitive(fin_conn: sqlite3.Connection):
    salvar_linha1_tres_textos(fin_conn, "C", "N", "energia")
    fin_conn.commit()
    path0 = obter_tipo_com_caminho(fin_conn, listar_linhas_tabela_tipos(fin_conn)[0]["tipo_id"])
    ok, msg = resolver_salvar_formulario(
        fin_conn,
        linha1_cc="C",
        linha1_natureza="",
        linha1_tipo="",
        linha2_centro_id=None,
        linha2_natureza_texto="",
        linha3_centro_id=path0["centro_custo_id"],
        linha3_natureza_id=path0["natureza_id"],
        linha3_tipo_texto="Energia",
        editando_tipo_id=None,
    )
    assert not ok and msg == MSG_REGISTRO_DUPLICADO


def test_tipo_duplicado_ignora_acentos(fin_conn: sqlite3.Connection):
    salvar_linha1_tres_textos(fin_conn, "C", "N", "Água")
    fin_conn.commit()
    path0 = obter_tipo_com_caminho(fin_conn, listar_linhas_tabela_tipos(fin_conn)[0]["tipo_id"])
    ok, msg = resolver_salvar_formulario(
        fin_conn,
        linha1_cc="",
        linha1_natureza="",
        linha1_tipo="",
        linha2_centro_id=None,
        linha2_natureza_texto="",
        linha3_centro_id=path0["centro_custo_id"],
        linha3_natureza_id=path0["natureza_id"],
        linha3_tipo_texto="Agua",
        editando_tipo_id=None,
    )
    assert not ok and msg == MSG_REGISTRO_DUPLICADO


def test_resolver_linha3_duplicado_mesmo_nome_sem_edicao(fin_conn: sqlite3.Connection):
    salvar_linha1_tres_textos(fin_conn, "C", "N", "T1")
    fin_conn.commit()
    path0 = obter_tipo_com_caminho(fin_conn, listar_linhas_tabela_tipos(fin_conn)[0]["tipo_id"])
    ok, msg = resolver_salvar_formulario(
        fin_conn,
        linha1_cc="C",
        linha1_natureza="",
        linha1_tipo="",
        linha2_centro_id=None,
        linha2_natureza_texto="",
        linha3_centro_id=path0["centro_custo_id"],
        linha3_natureza_id=path0["natureza_id"],
        linha3_tipo_texto="T1",
        editando_tipo_id=None,
    )
    assert not ok and msg == MSG_REGISTRO_DUPLICADO


def test_resolver_linha3_alteracao_pede_confirmacao_sem_flag(fin_conn: sqlite3.Connection):
    salvar_linha1_tres_textos(fin_conn, "C", "N", "T1")
    fin_conn.commit()
    tid = listar_linhas_tabela_tipos(fin_conn)[0]["tipo_id"]
    path0 = obter_tipo_com_caminho(fin_conn, tid)
    ok, msg = resolver_salvar_formulario(
        fin_conn,
        linha1_cc="C",
        linha1_natureza="",
        linha1_tipo="",
        linha2_centro_id=None,
        linha2_natureza_texto="",
        linha3_centro_id=path0["centro_custo_id"],
        linha3_natureza_id=path0["natureza_id"],
        linha3_tipo_texto="T1-alt",
        editando_tipo_id=tid,
        confirmar_alteracao=False,
    )
    assert not ok and msg == MSG_PEDIR_CONFIRMACAO_ALTERACAO


def test_tipo_com_lancamento_renomear_desactiva_e_cria_novo(fin_conn: sqlite3.Connection):
    salvar_linha1_tres_textos(fin_conn, "C", "N", "Told")
    fin_conn.commit()
    tid = listar_linhas_tabela_tipos(fin_conn)[0]["tipo_id"]
    assert not tipo_tem_lancamentos(fin_conn, tid)
    fin_conn.execute(
        "INSERT INTO financeiro_gasto_lancamentos (tipo_gasto_id, valor_centavos) VALUES (?, 100)",
        (tid,),
    )
    fin_conn.commit()
    assert tipo_tem_lancamentos(fin_conn, tid)
    ok, _ = atualizar_tipo_a_partir_formulario(
        fin_conn,
        tid,
        obter_tipo_com_caminho(fin_conn, tid)["centro_custo_id"],
        obter_tipo_com_caminho(fin_conn, tid)["natureza_id"],
        "Tnew",
    )
    assert ok
    fin_conn.commit()
    n_old = fin_conn.execute(
        "SELECT ativo FROM financeiro_tipo_gasto WHERE id = ?", (tid,)
    ).fetchone()[0]
    assert int(n_old) == 0
    rows = listar_linhas_tabela_tipos(fin_conn)
    assert len(rows) == 1
    assert rows[0]["tipo_nome"] == "Tnew"


def test_filtros_so_nome_sem_rotulo_hierarquico(fin_conn: sqlite3.Connection):
    salvar_linha1_tres_textos(fin_conn, "C1", "N1", "T1")
    fin_conn.commit()
    nat = listar_naturezas_ativas_so_nome(fin_conn)
    tip = listar_tipos_gasto_ativos_so_nome(fin_conn)
    assert any(n[1] == "N1" for n in nat)
    assert all("—" not in n[1] for n in nat)
    assert any(t[1] == "T1" for t in tip)
    assert all("·" not in t[1] for t in tip)


def test_resolver_linha1_apenas_cria_centro(fin_conn: sqlite3.Connection):
    ok, msg = resolver_salvar_formulario(
        fin_conn,
        linha1_cc="  ApenasCC ",
        linha1_natureza="",
        linha1_tipo="",
        linha2_centro_id=None,
        linha2_natureza_texto="",
        linha3_centro_id=None,
        linha3_natureza_id=None,
        linha3_tipo_texto="",
        editando_tipo_id=None,
    )
    assert ok and "Centro de Custo criado com sucesso" in msg
    fin_conn.commit()
    rows = fin_conn.execute(
        "SELECT nome FROM financeiro_centro_custo WHERE ativo = 1 AND nome = ?",
        ("ApenasCC",),
    ).fetchall()
    assert len(rows) == 1


def test_natureza_tem_lancamentos_detecta_via_tipo(fin_conn: sqlite3.Connection):
    salvar_linha1_tres_textos(fin_conn, "C", "N", "T")
    fin_conn.commit()
    tid = listar_linhas_tabela_tipos(fin_conn)[0]["tipo_id"]
    nid = obter_tipo_com_caminho(fin_conn, tid)["natureza_id"]
    assert not natureza_tem_lancamentos(fin_conn, nid)
    fin_conn.execute(
        "INSERT INTO financeiro_gasto_lancamentos (tipo_gasto_id, valor_centavos) VALUES (?, 1)",
        (tid,),
    )
    fin_conn.commit()
    assert natureza_tem_lancamentos(fin_conn, nid)
