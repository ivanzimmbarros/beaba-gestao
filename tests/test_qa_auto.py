import os

import pytest

from src.database.connection import create_tables
from src.modules.cliente import cadastrar_cliente


@pytest.fixture(autouse=True)
def setup_db():
    """Prepara um banco de teste limpo antes de cada validação"""
    if os.path.exists("data/beaba_gestao.db"):
        os.remove("data/beaba_gestao.db")
    create_tables()


def _cli(**kw):
    base = dict(
        nome="Diretor Auto",
        numero_contato="11999998888",
        morada="Rua Teste 1",
        email="diretor@beaba.pt",
        sexo="Masculino",
        tem_filhos=False,
        filhos=[],
        gravida=None,
        data_parto_prevista=None,
        observacoes="",
        contatos_emergencia=[],
    )
    base.update(kw)
    return cadastrar_cliente(**base)


def test_cadastro_sucesso():
    ok, _msg = _cli()
    assert ok is True


def test_duplicidade_proibida():
    _cli(nome="Original", numero_contato="11888887777")
    ok, msg = _cli(nome="Clone", numero_contato="11888887777")
    assert ok is False
    assert "já" in msg.lower()


def test_numero_invalido_curto():
    ok, msg = _cli(numero_contato="123")
    assert ok is False
    assert "11" in msg


def test_limpeza_caracteres_especiais():
    ok, _msg = _cli(numero_contato="(11) 99999-9999")
    assert ok is True


def test_emergencia_parcial_invalida():
    ok, msg = _cli(contatos_emergencia=[("Só Nome", "")])
    assert ok is False
    assert "emergência" in msg.lower()


def test_emergencia_duplo_valido():
    ok, _msg = _cli(
        contatos_emergencia=[
            ("Maria", "11987654321"),
            ("João", "11912345678"),
        ]
    )
    assert ok is True


def test_filhos_sem_dados_invalido():
    ok, msg = _cli(tem_filhos=True, filhos=[])
    assert ok is False


def test_gravida_sem_data_invalido():
    ok, msg = _cli(
        sexo="Feminino",
        gravida=True,
        data_parto_prevista=None,
    )
    assert ok is False
