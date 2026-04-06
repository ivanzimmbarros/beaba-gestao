import os

import pytest

from src.database.connection import create_tables
from src.modules.catalogo import cadastrar_servico_fase1, listar_itens_catalogo


@pytest.fixture(autouse=True)
def setup_db():
    if os.path.exists("data/beaba_gestao.db"):
        os.remove("data/beaba_gestao.db")
    create_tables()


def test_cadastrar_sessao_ok():
    ok, msg = cadastrar_servico_fase1(
        "Sessão",
        "Sessão Teste QA",
        "Descritivo mínimo para validação.",
        True,
        sessao_duracao_horas=1.5,
        sessao_valor_euros=60.0,
    )
    assert ok, msg
    itens = [i for i in listar_itens_catalogo() if i["nome"] == "Sessão Teste QA"]
    assert len(itens) == 1
    assert itens[0]["natureza"] == "Sessão"
    assert "60" in str(itens[0]["detalhes"]) and "h" in str(itens[0]["detalhes"]).lower()


def test_cadastrar_dup_nome_falha():
    cadastrar_servico_fase1(
        "Produto",
        "Produto Único",
        "Óleo essencial.",
        True,
        produto_tipo="Cosmética",
        produto_descricao="",
        produto_valor_euros=15.0,
        produto_origem="proprio",
    )
    ok, msg = cadastrar_servico_fase1(
        "Produto",
        "Produto Único",
        "Tentativa duplicada.",
        True,
        produto_tipo="X",
        produto_descricao="",
        produto_valor_euros=10.0,
        produto_origem="proprio",
    )
    assert ok is False


def test_descritivo_obrigatorio():
    ok, _ = cadastrar_servico_fase1(
        "Coworking",
        "Sala A",
        "",
        True,
        cowork_sala_nome="Sala A",
        cowork_cobranca="hora",
        cowork_valor_euros=5.0,
    )
    assert ok is False
