import os

import pytest

from src.database.connection import create_tables
from datetime import date, timedelta

from src.modules.catalogo import (
    cadastrar_evento,
    cadastrar_pacote,
    cadastrar_servico_fase1,
    listar_itens_catalogo,
    repasse_medio_ponderado_pacote,
)
from src.modules.colaborador import cadastrar_colaborador, listar_servicos


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


def _adult_dob():
    return (date.today() - timedelta(days=365 * 30)).isoformat()


def test_pacote_ok_e_listagem():
    ok_s, _ = cadastrar_servico_fase1(
        "Sessão",
        "Sessão Pac Alpha",
        "Para teste de pacote.",
        True,
        sessao_duracao_horas=1.5,
        sessao_valor_euros=40.0,
    )
    assert ok_s
    ok_s2, _ = cadastrar_servico_fase1(
        "Sessão",
        "Sessão Pac Beta",
        "Para teste de pacote.",
        True,
        sessao_duracao_horas=2.0,
        sessao_valor_euros=50.0,
    )
    assert ok_s2
    ok_p, _ = cadastrar_servico_fase1(
        "Produto",
        "Óleo Pac",
        "Produto no pacote.",
        True,
        produto_tipo="Aromaterapia",
        produto_descricao="",
        produto_valor_euros=12.0,
        produto_origem="proprio",
    )
    assert ok_p

    cur = __import__("sqlite3").connect("data/beaba_gestao.db")
    sid_a = cur.execute("SELECT id FROM servicos WHERE nome = 'Sessão Pac Alpha'").fetchone()[0]
    sid_b = cur.execute("SELECT id FROM servicos WHERE nome = 'Sessão Pac Beta'").fetchone()[0]
    pid = cur.execute("SELECT id FROM servicos WHERE nome = 'Óleo Pac'").fetchone()[0]
    cur.close()

    cadastrar_colaborador(
        nome="Prof Pacote",
        sexo="Feminino",
        data_nascimento=_adult_dob(),
        endereco_rua="Rua P",
        endereco_numero="1",
        endereco_complemento="",
        codigo_postal="4800-200",
        concelho="Guimarães",
        freguesia="Selho",
        distrito="",
        pais="Portugal",
        email="pac@beaba.pt",
        numero_contato="11955443322",
        observacoes="",
        servicos_repasse=[(sid_a, 40.0, date.today().isoformat())],
    )
    w = repasse_medio_ponderado_pacote([(sid_a, 2), (sid_b, 1)])
    assert w is not None
    assert abs(w - 40.0) < 0.02

    ok_pk, msg = cadastrar_pacote(
        "Pacote Integração",
        "Pacote de teste automatizado.",
        True,
        [(sid_a, 2, None), (sid_b, 1, None)],
        (int(pid), 1),
        35.0,
        199.0,
    )
    assert ok_pk, msg
    itens = listar_itens_catalogo()
    nomes = [x["nome"] for x in itens]
    assert "Pacote Integração" in nomes
    row = next(x for x in itens if x["nome"] == "Pacote Integração")
    assert row["natureza"] == "Pacote"
    assert "2×" in str(row["detalhes"]) and "Óleo" in str(row["detalhes"])


def _sid_habilitacao():
    s = listar_servicos()
    assert s
    return s[0][0]


def test_evento_ok_e_listagem():
    cadastrar_colaborador(
        nome="Colab Evento",
        sexo="Masculino",
        data_nascimento=_adult_dob(),
        endereco_rua="Rua E",
        endereco_numero="2",
        endereco_complemento="",
        codigo_postal="4800-300",
        concelho="Guimarães",
        freguesia="Selho",
        distrito="",
        pais="Portugal",
        email="ev@beaba.pt",
        numero_contato="11944332211",
        observacoes="",
        servicos_repasse=[(_sid_habilitacao(), 30.0, date.today().isoformat())],
    )
    cur = __import__("sqlite3").connect("data/beaba_gestao.db")
    cid = cur.execute("SELECT id FROM colaboradores WHERE nome = 'Colab Evento'").fetchone()[0]
    cur.close()

    ok, msg = cadastrar_evento(
        "Workshop Teste",
        "Evento de integração.",
        True,
        date.today().isoformat(),
        "Sede BeaBa",
        "Notas internas.",
        "interno",
        8.0,
        12.0,
        2.0,
        [("colaborador", int(cid), "", "percentual", 20.0, None)],
    )
    assert ok, msg
    itens = listar_itens_catalogo()
    row = next(x for x in itens if x["nome"] == "Workshop Teste")
    assert row["natureza"] == "Evento"
    assert "Workshop" in str(row["detalhes"]) or "Sede" in str(row["detalhes"]) or "Colab Evento" in str(row["detalhes"])


def test_evento_sem_participantes_falha():
    ok, _ = cadastrar_evento(
        "Ev Vazio",
        "X.",
        True,
        date.today().isoformat(),
        "Local",
        "",
        "convidado",
        5.0,
        10.0,
        0.0,
        [],
    )
    assert ok is False


def test_evento_colaborador_duplicado_falha():
    cadastrar_colaborador(
        nome="Dup Ev",
        sexo="Feminino",
        data_nascimento=_adult_dob(),
        endereco_rua="Rua D",
        endereco_numero="1",
        endereco_complemento="",
        codigo_postal="4800-400",
        concelho="Guimarães",
        freguesia="Selho",
        distrito="",
        pais="Portugal",
        email="dupev@beaba.pt",
        numero_contato="11933221100",
        observacoes="",
        servicos_repasse=[(_sid_habilitacao(), 40.0, date.today().isoformat())],
    )
    cur = __import__("sqlite3").connect("data/beaba_gestao.db")
    cid = cur.execute("SELECT id FROM colaboradores WHERE nome = 'Dup Ev'").fetchone()[0]
    cur.close()
    ok, _ = cadastrar_evento(
        "Ev Dup",
        "Y.",
        True,
        date.today().isoformat(),
        "L",
        "",
        "interno",
        1.0,
        2.0,
        0.0,
        [
            ("colaborador", int(cid), "", "valor", None, 10.0),
            ("colaborador", int(cid), "", "valor", None, 20.0),
        ],
    )
    assert ok is False


def test_pacote_sessao_duplicada_rejeita():
    cadastrar_servico_fase1(
        "Sessão",
        "Sessão Dup",
        "X.",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=10.0,
    )
    cur = __import__("sqlite3").connect("data/beaba_gestao.db")
    sid = cur.execute("SELECT id FROM servicos WHERE nome = 'Sessão Dup'").fetchone()[0]
    cur.close()
    ok, msg = cadastrar_pacote(
        "Pac Ruim",
        "Y.",
        True,
        [(sid, 1, None), (sid, 1, None)],
        None,
        50.0,
        50.0,
    )
    assert ok is False
