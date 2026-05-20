import os

import pytest

from datetime import date, timedelta

from src.modules.catalogo import (
    cadastrar_especialidade,
    cadastrar_evento,
    cadastrar_pacote,
    cadastrar_servico_fase1,
    listar_especialidades_por_natureza,
    listar_itens_catalogo,
    listar_servicos_para_venda,
    obter_servico_para_formulario,
    repasse_medio_ponderado_pacote,
)
from src.modules.catalogo_atualizacao import atualizar_servico_fase1_existente
from src.modules.colaborador import cadastrar_colaborador, listar_servicos
from src.ui.page_catalogo import _cat_format_duration_hm_h, _cat_parse_duration_hm_h


def test_listar_especialidades_inclui_geral_sessao():
    rows = listar_especialidades_por_natureza("Sessão")
    assert any(str(r.get("nome") or "") == "Geral" for r in rows)


def test_cadastrar_especialidade_e_usar_em_servico():
    ok_e, msg_e = cadastrar_especialidade("Sessão", "Pilates Avançado", "Subgrupo teste")
    assert ok_e, msg_e
    esp_rows = listar_especialidades_por_natureza("Sessão")
    eid = next(int(r["id"]) for r in esp_rows if r["nome"] == "Pilates Avançado")
    ok, msg = cadastrar_servico_fase1(
        "Sessão",
        "Sessão Com Esp Custom",
        "Descritivo.",
        True,
        especialidade_id=eid,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=55.0,
    )
    assert ok, msg
    d = obter_servico_para_formulario(
        next(i["id"] for i in listar_itens_catalogo() if i["nome"] == "Sessão Com Esp Custom")
    )
    assert d is not None
    assert int(d.get("especialidade_id") or 0) == eid


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
    assert str(itens[0].get("especialidade") or "") != ""
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

    cur = __import__("sqlite3").connect(os.environ["BEABA_SQLITE_PATH"])
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
        email="pac@example.com",
        nif_ou_documento="123456789",
        identificacao_internacional=False,
        numero_contato="11955443322",
        observacoes="",
        servicos_repasse=[(sid_a, 40.0, date.today().isoformat())],
        iban_dados_bancarios="PT50000201231234567890152",
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
    assert row["natureza"] == "Pack"
    assert "2×" in str(row["detalhes"]) and "Óleo" in str(row["detalhes"])

    cur2 = __import__("sqlite3").connect(os.environ["BEABA_SQLITE_PATH"])
    pk_id = int(cur2.execute("SELECT id FROM servicos WHERE nome = 'Pacote Integração'").fetchone()[0])
    cur2.close()
    form = obter_servico_para_formulario(pk_id)
    assert form is not None
    assert form["natureza"] == "Pack"
    assert form.get("pacote_linhas"), "Pacote deve trazer linhas de composição para a ficha (validade do pacote)"
    assert "pacote_valor_euros" in form and "pacote_repasse_ref_pct" in form


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
        email="ev@example.com",
        nif_ou_documento="123456789",
        identificacao_internacional=False,
        numero_contato="11944332211",
        observacoes="",
        servicos_repasse=[(_sid_habilitacao(), 30.0, date.today().isoformat())],
        iban_dados_bancarios="PT50000201231234567890152",
    )
    cur = __import__("sqlite3").connect(os.environ["BEABA_SQLITE_PATH"])
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
        email="dupev@example.com",
        nif_ou_documento="123456789",
        identificacao_internacional=False,
        numero_contato="11933221100",
        observacoes="",
        servicos_repasse=[(_sid_habilitacao(), 40.0, date.today().isoformat())],
        iban_dados_bancarios="PT50000201231234567890152",
    )
    cur = __import__("sqlite3").connect(os.environ["BEABA_SQLITE_PATH"])
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
    cur = __import__("sqlite3").connect(os.environ["BEABA_SQLITE_PATH"])
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


def test_cat_format_duration_hm_h():
    assert _cat_format_duration_hm_h(1.5) == "1:30h"
    assert _cat_format_duration_hm_h(1.0) == "1:00h"
    assert _cat_format_duration_hm_h(0.25) == "0:15h"
    assert _cat_format_duration_hm_h(24.0) == "24:00h"


def test_cat_parse_duration_hm_h_ok():
    ok, v, err = _cat_parse_duration_hm_h("1:30h")
    assert ok and abs(v - 1.5) < 1e-9 and err == ""
    ok2, v2, _ = _cat_parse_duration_hm_h("0:15")
    assert ok2 and abs(v2 - 0.25) < 1e-9
    ok3, v3, _ = _cat_parse_duration_hm_h("24:00h")
    assert ok3 and abs(v3 - 24.0) < 1e-9


def test_cat_parse_duration_hm_h_errors():
    assert _cat_parse_duration_hm_h("")[0] is False
    assert _cat_parse_duration_hm_h("0:10h")[0] is False
    assert _cat_parse_duration_hm_h("1:60h")[0] is False
    assert _cat_parse_duration_hm_h("25:00h")[0] is False


def test_cadastrar_servico_rejeita_especialidade_natureza_errada():
    rows_p = listar_especialidades_por_natureza("Produto")
    eid_prod = next(int(r["id"]) for r in rows_p if str(r.get("nome") or "") == "Geral")
    ok, msg = cadastrar_servico_fase1(
        "Sessão",
        "Sessão Edge Mau Nat",
        "D.",
        True,
        especialidade_id=eid_prod,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=40.0,
    )
    assert ok is False
    assert "não pertence" in msg.lower() or "natureza" in msg.lower()


def test_cadastrar_servico_rejeita_especialidade_inativa():
    ok_e, msg_e = cadastrar_especialidade("Sessão", "Esp Inactiva Edge Z", "", ativo=False)
    assert ok_e, msg_e
    cur = __import__("sqlite3").connect(os.environ["BEABA_SQLITE_PATH"])
    row = cur.execute(
        "SELECT id FROM especialidades WHERE nome = ?", ("Esp Inactiva Edge Z",)
    ).fetchone()
    cur.close()
    assert row is not None
    eid = int(row[0])
    ok, msg = cadastrar_servico_fase1(
        "Sessão",
        "Sessão Edge Inact Esp",
        "D.",
        True,
        especialidade_id=eid,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=40.0,
    )
    assert ok is False
    assert "inativa" in msg.lower()


def test_cadastrar_especialidade_nome_duplicado_rejeita():
    ok1, _ = cadastrar_especialidade("Coworking", "DupNomeEspEdge772", "")
    assert ok1
    ok2, msg2 = cadastrar_especialidade("Coworking", "DupNomeEspEdge772", "")
    assert ok2 is False
    assert "Já existe" in msg2 or "já existe" in msg2


def test_listar_servicos_para_venda_inclui_campos_especialidade():
    rows = listar_servicos_para_venda()
    assert isinstance(rows, list)
    for r in rows:
        assert "especialidade_id" in r
        assert "especialidade" in r


def test_create_tables_idempotente_nao_duplica_geral_por_natureza():
    from src.database.connection import create_tables
    from src.modules.constants import NATUREZAS_CATALOGO_FASE3

    create_tables()
    create_tables()
    cur = __import__("sqlite3").connect(os.environ["BEABA_SQLITE_PATH"])
    n = int(
        cur.execute("SELECT COUNT(*) FROM especialidades WHERE nome = ?", ("Geral",)).fetchone()[0]
    )
    cur.close()
    assert n == len(NATUREZAS_CATALOGO_FASE3)


def test_migrate_repreenche_especialidade_id_nulo():
    from src.database.connection import create_tables

    ok, msg = cadastrar_servico_fase1(
        "Sessão",
        "Sessão Mig Null Edge",
        "Para teste de repreenchimento.",
        True,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=44.0,
    )
    assert ok, msg
    path = os.environ["BEABA_SQLITE_PATH"]
    conn = __import__("sqlite3").connect(path)
    conn.execute(
        "UPDATE servicos SET especialidade_id = NULL WHERE nome = ?",
        ("Sessão Mig Null Edge",),
    )
    conn.commit()
    conn.close()
    create_tables()
    conn = __import__("sqlite3").connect(path)
    row = conn.execute(
        "SELECT especialidade_id FROM servicos WHERE nome = ?",
        ("Sessão Mig Null Edge",),
    ).fetchone()
    conn.close()
    assert row is not None and row[0] is not None


def test_atualizar_servico_altera_especialidade():
    ok_a, _ = cadastrar_especialidade("Sessão", "EspUpAx8831", "")
    ok_b, _ = cadastrar_especialidade("Sessão", "EspUpBx8831", "")
    assert ok_a and ok_b
    rows = listar_especialidades_por_natureza("Sessão")
    m = {str(r["nome"]): int(r["id"]) for r in rows}
    eid_a = m["EspUpAx8831"]
    eid_b = m["EspUpBx8831"]
    ok, _ = cadastrar_servico_fase1(
        "Sessão",
        "Sessão Troca Esp 8831",
        "Desc.",
        True,
        especialidade_id=eid_a,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=50.0,
    )
    assert ok
    sid = next(i["id"] for i in listar_itens_catalogo() if i["nome"] == "Sessão Troca Esp 8831")
    ok2, msg2 = atualizar_servico_fase1_existente(
        sid,
        "Sessão",
        "Sessão Troca Esp 8831",
        "Desc.",
        True,
        especialidade_id=eid_b,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=51.0,
    )
    assert ok2, msg2
    d = obter_servico_para_formulario(sid)
    assert d is not None
    assert int(d.get("especialidade_id") or 0) == eid_b
