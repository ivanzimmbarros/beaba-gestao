import os
from datetime import date, timedelta

import pytest

from src.database.connection import create_tables
from src.modules.colaborador import cadastrar_colaborador, listar_servicos


@pytest.fixture(autouse=True)
def setup_db():
    if os.path.exists("data/beaba_gestao.db"):
        os.remove("data/beaba_gestao.db")
    create_tables()


def _adult_dob():
    return (date.today() - timedelta(days=365 * 25)).isoformat()


def _primeiro_servico_id() -> int:
    s = listar_servicos()
    assert s
    return s[0][0]


def _colab(**kw):
    base = dict(
        nome="Prof Teste",
        sexo="Feminino",
        data_nascimento=_adult_dob(),
        endereco_rua="Rua A",
        endereco_numero="1",
        endereco_complemento="",
        codigo_postal="4800-100",
        concelho="Guimarães",
        freguesia="Selho",
        distrito="",
        pais="Portugal",
        email="prof@beaba.pt",
        numero_contato="11999887766",
        observacoes="",
        servicos_repasse=[(_primeiro_servico_id(), 12.34)],
    )
    base.update(kw)
    return cadastrar_colaborador(**base)


def test_listar_servicos_seed():
    s = listar_servicos()
    assert len(s) >= 5


def test_cadastro_colaborador_ok():
    ok, msg = _colab()
    assert ok is True


def test_contacto_duplicado():
    _colab(numero_contato="11988776655")
    ok, msg = _colab(nome="Outro", email="o@b.pt", numero_contato="11988776655")
    assert ok is False
    assert "contacto" in msg.lower() or "já" in msg.lower()


def test_menos_de_18_anos():
    jovem = (date.today() - timedelta(days=365 * 17)).isoformat()
    ok, msg = _colab(data_nascimento=jovem)
    assert ok is False
    assert "18" in msg


def test_sem_servicos():
    ok, msg = _colab(servicos_repasse=[])
    assert ok is False


def test_servico_repetido():
    sid = _primeiro_servico_id()
    ok, msg = _colab(servicos_repasse=[(sid, 10.0), (sid, 20.0)])
    assert ok is False
