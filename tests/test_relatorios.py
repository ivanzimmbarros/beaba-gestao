import os
from datetime import date, timedelta

import pytest

from src.database.connection import create_tables, get_connection
from src.modules.catalogo import cadastrar_servico_fase1
from src.modules.cliente import buscar_cliente_por_whatsapp, cadastrar_cliente
from src.modules.colaborador import cadastrar_colaborador
from src.modules.relatorios import (
    FiltrosDashboard,
    kpis,
    pareto_dimensao,
    serie_receita_temporal,
    top_n_dimensao,
)
from src.modules.venda import registrar_venda


@pytest.fixture(autouse=True)
def setup_db():
    if os.path.exists("data/beaba_gestao.db"):
        os.remove("data/beaba_gestao.db")
    create_tables()


def test_venda_itens_coluna_colaborador_id():
    conn = get_connection()
    assert conn
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(venda_itens)")
        cols = {row[1] for row in cur.fetchall()}
        assert "colaborador_id" in cols
    finally:
        conn.close()


def test_kpis_sem_dados():
    k = kpis(
        FiltrosDashboard(
            data_inicio="2020-01-01",
            data_fim="2030-12-31",
        )
    )
    assert k["n_vendas"] == 0
    assert k["receita_itens_centavos"] == 0


def _cliente():
    cadastrar_cliente(
        nome="C Dash",
        numero_contato="91333333330",
        endereco_rua="Rua A",
        endereco_numero="1",
        endereco_complemento="",
        codigo_postal="4000-001",
        concelho="Porto",
        freguesia="Centro",
        distrito="",
        pais="Portugal",
        email="dash@example.com",
        sexo="Outro",
        tem_filhos=False,
        filhos=[],
        gravida=None,
        data_parto_prevista=None,
        observacoes="",
        contatos_emergencia=[],
    )
    return buscar_cliente_por_whatsapp("91333333330")


def test_relatorio_apos_venda_e_filtro_colaborador():
    cid = _cliente()
    assert cid
    cadastrar_servico_fase1(
        "Produto",
        "Prod Dash",
        "X.",
        True,
        produto_tipo="t",
        produto_descricao="",
        produto_valor_euros=25.0,
        produto_origem="proprio",
    )
    dob = (date.today() - timedelta(days=365 * 25)).isoformat()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM servicos WHERE nome = ?", ("Prod Dash",))
    prod_id = int(cur.fetchone()[0])
    conn.close()

    ok_c, _ = cadastrar_colaborador(
        nome="Colab Dash",
        sexo="Feminino",
        data_nascimento=dob,
        endereco_rua="Rua B",
        endereco_numero="2",
        endereco_complemento="",
        codigo_postal="4000-002",
        concelho="Porto",
        freguesia="Centro",
        distrito="",
        pais="Portugal",
        email="colabdash@example.com",
        numero_contato="91444444440",
        observacoes="",
        servicos_repasse=[(prod_id, 15.0, date.today().isoformat())],
    )
    assert ok_c
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM colaboradores WHERE nome = ?", ("Colab Dash",))
    col_id = int(cur.fetchone()[0])
    conn.close()

    ok_v, msg_v = registrar_venda(
        int(cid),
        "integral",
        [
            {
                "servico_id": prod_id,
                "quantidade": 2,
                "is_bonus": False,
                "evento_preco": None,
                "desconto_linha_tipo": "none",
                "desconto_linha_valor": None,
                "colaborador_id": col_id,
            }
        ],
        None,
        None,
        [("dinheiro", 5000)],
        [],
        "",
    )
    assert ok_v, msg_v

    d0 = (date.today() - timedelta(days=1)).isoformat()
    d1 = (date.today() + timedelta(days=1)).isoformat()
    f_all = FiltrosDashboard(data_inicio=d0, data_fim=d1)
    k = kpis(f_all)
    assert k["n_vendas"] == 1
    assert k["receita_itens_centavos"] == 5000

    f_colab = FiltrosDashboard(data_inicio=d0, data_fim=d1, colaborador_ids=[col_id])
    assert kpis(f_colab)["n_vendas"] == 1

    f_out = FiltrosDashboard(data_inicio=d0, data_fim=d1, colaborador_ids=[col_id + 9999])
    assert kpis(f_out)["n_vendas"] == 0

    top = top_n_dimensao(f_all, "servico", 5)
    assert top and top[0][1] == 5000

    par = pareto_dimensao(f_all, "servico", limite_barras=10)
    assert par and par[-1][2] == 100.0

    ser = serie_receita_temporal(f_all, "dia")
    assert len(ser) >= 1
