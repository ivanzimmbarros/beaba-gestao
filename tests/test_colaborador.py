import os
from datetime import date, timedelta

import pytest

from src.database.connection import create_tables
from src.modules.colaborador import (
    atualizar_colaborador,
    cadastrar_colaborador,
    listar_servicos,
    media_repasse_percentual_servico,
    obter_colaborador,
)


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


def _linha_svc(sid: int, pct: float, data_linha: str | None = None):
    d = data_linha or date.today().isoformat()
    return (sid, pct, d)


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
        servicos_repasse=[_linha_svc(_primeiro_servico_id(), 12.34)],
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
    ok, msg = _colab(servicos_repasse=[_linha_svc(sid, 10.0), _linha_svc(sid, 20.0)])
    assert ok is False


def test_data_linha_obrigatoria():
    sid = _primeiro_servico_id()
    ok, msg = cadastrar_colaborador(
        nome="X",
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
        email="x@b.pt",
        numero_contato="11977665544",
        observacoes="",
        servicos_repasse=[(sid, 50.0, "")],
    )
    assert ok is False
    assert "data" in msg.lower() or "inserção" in msg.lower() or "habilitação" in msg.lower()


def test_atualizar_colaborador_e_media_repasse():
    ok, _ = _colab(numero_contato="11966554433", email="a1@b.pt")
    assert ok
    ok2, _ = _colab(nome="Segundo", numero_contato="11966554422", email="a2@b.pt")
    assert ok2
    sid = _primeiro_servico_id()
    m = media_repasse_percentual_servico(sid)
    assert m is not None
    assert abs(m - 12.34) < 0.01 or m > 0

    cur = obter_colaborador(1)
    assert cur is not None
    ok3, msg3 = atualizar_colaborador(
        colaborador_id=1,
        nome=cur["nome"] + " Editado",
        sexo=cur["sexo"],
        data_nascimento=cur["data_nascimento"],
        endereco_rua=cur["endereco_rua"],
        endereco_numero=cur["endereco_numero"],
        endereco_complemento=cur["endereco_complemento"],
        codigo_postal=cur["codigo_postal"],
        concelho=cur["concelho"],
        freguesia=cur["freguesia"],
        distrito=cur["distrito"],
        pais=cur["pais"],
        email=cur["email"],
        numero_contato=cur["whatsapp"],
        observacoes=cur["observacoes"],
        servicos_repasse=[
            (cur["linhas"][0]["servico_id"], 25.0, cur["linhas"][0]["data_insercao_linha"] or date.today().isoformat()),
        ],
    )
    assert ok3, msg3
