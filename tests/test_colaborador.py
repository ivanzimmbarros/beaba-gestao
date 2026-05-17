from datetime import date, timedelta

import pytest

from src.database.connection import get_connection
from src.modules.colaborador import (
    atualizar_colaborador,
    buscar_colaboradores_por_prefixo_nome,
    cadastrar_colaborador,
    listar_colaboradores_mapa_equipa,
    listar_naturezas_servicos_mapa_equipa,
    listar_servicos,
    listar_servicos_para_mapa_equipa,
    media_repasse_percentual_servico,
    obter_colaborador,
    resolver_conjunto_servicos_mapa_equipa,
)


def _adult_dob():
    return (date.today() - timedelta(days=365 * 25)).isoformat()


def _primeiro_servico_id() -> int:
    s = listar_servicos()
    assert s
    return s[0][0]


def _linha_svc(sid: int, pct: float, data_linha: str | None = None):
    d = data_linha or date.today().isoformat()
    return (sid, pct, d)


_IBAN_COLAB_TESTE = "PT50000201231234567890152"


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
        email="prof@example.com",
        nif_ou_documento="123456789",
        identificacao_internacional=False,
        numero_contato="11999887766",
        observacoes="",
        servicos_repasse=[_linha_svc(_primeiro_servico_id(), 12.34)],
        iban_dados_bancarios=_IBAN_COLAB_TESTE,
    )
    base.update(kw)
    return cadastrar_colaborador(**base)


def test_listar_servicos_seed():
    s = listar_servicos()
    assert len(s) >= 5


def test_cadastro_colaborador_ok():
    ok, msg = _colab()
    assert ok is True


def test_freguesia_opcional_em_cadastro_colaborador():
    ok, msg = _colab(
        nome="Col Freg Opcional",
        email="col_freg_opcional@example.com",
        freguesia="",
    )
    assert ok is True


def test_nif_obrigatorio_em_cadastro_colaborador():
    sid = _primeiro_servico_id()
    ok, msg = cadastrar_colaborador(
        nome="Sem NIF",
        sexo="Masculino",
        data_nascimento=_adult_dob(),
        endereco_rua="Rua A",
        endereco_numero="1",
        endereco_complemento="",
        codigo_postal="4800-100",
        concelho="Guimarães",
        freguesia="Selho",
        distrito="",
        pais="Portugal",
        email="sem_nif_col@example.com",
        nif_ou_documento="",
        identificacao_internacional=False,
        numero_contato="11988776600",
        observacoes="",
        servicos_repasse=[_linha_svc(sid, 10.0)],
        iban_dados_bancarios=_IBAN_COLAB_TESTE,
    )
    assert ok is False
    assert "identificação" in msg.lower() or "nif" in msg.lower()


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
        nif_ou_documento="123456789",
        identificacao_internacional=False,
        numero_contato="11977665544",
        observacoes="",
        servicos_repasse=[(sid, 50.0, "")],
        iban_dados_bancarios=_IBAN_COLAB_TESTE,
    )
    assert ok is False
    assert "data" in msg.lower() or "inserção" in msg.lower() or "habilitação" in msg.lower()


def test_resolver_conjunto_servicos_mapa_equipa_vazio():
    assert (
        resolver_conjunto_servicos_mapa_equipa(naturezas_seleccionadas=[], servico_ids_seleccionados=[])
        == []
    )


def test_listar_colaboradores_mapa_equipa_sem_ids():
    assert listar_colaboradores_mapa_equipa([]) == []


def test_mapa_equipa_servicos_e_colaborador_habilitado():
    ok, _ = _colab(
        nome="Col Mapa Equipa X",
        email="mapa_equipa_x@example.com",
        numero_contato="11992001122",
    )
    assert ok
    nats = listar_naturezas_servicos_mapa_equipa()
    assert isinstance(nats, list)
    todas = listar_servicos_para_mapa_equipa(None)
    assert todas
    sid0 = int(todas[0][0])
    cj = resolver_conjunto_servicos_mapa_equipa(
        naturezas_seleccionadas=[],
        servico_ids_seleccionados=[sid0],
    )
    rows = listar_colaboradores_mapa_equipa(cj)
    nomes = [str(r["nome"]) for r in rows]
    assert "Col Mapa Equipa X" in nomes
    hit = next(r for r in rows if str(r["nome"]) == "Col Mapa Equipa X")
    assert isinstance(hit.get("servicos"), list)
    assert len(hit["servicos"]) >= 1
    assert all(len(t) == 3 for t in hit["servicos"])


def test_buscar_colaboradores_por_prefixo_nome_vazio():
    assert buscar_colaboradores_por_prefixo_nome("") == []
    assert buscar_colaboradores_por_prefixo_nome("   ") == []


def test_buscar_colaboradores_por_prefixo_nome_encontra_e_ordena():
    ok_a, _ = _colab(
        nome="Zé Col Prefixo Alfa",
        email="col_prefixo_alfa@example.com",
        numero_contato="11991055560",
    )
    ok_b, _ = _colab(
        nome="Zé Col Prefixo Beta",
        email="col_prefixo_beta@example.com",
        numero_contato="11991055561",
    )
    assert ok_a and ok_b
    rows = buscar_colaboradores_por_prefixo_nome("Zé Col Prefixo")
    assert len(rows) == 2
    assert [n for _, n in rows] == ["Zé Col Prefixo Alfa", "Zé Col Prefixo Beta"]


def test_buscar_colaboradores_por_prefixo_nome_sem_match():
    assert buscar_colaboradores_por_prefixo_nome("NomeInexistenteColZZZ") == []


def test_buscar_colaboradores_por_prefixo_nome_respeita_limite():
    for i in range(4):
        ok, _ = _colab(
            nome=f"LimColNomeBusca {i:03d}",
            email=f"limcol_{i}@example.com",
            numero_contato=f"119910556{i:02d}",
        )
        assert ok
    rows = buscar_colaboradores_por_prefixo_nome("LimColNomeBusca", limit=2)
    assert len(rows) == 2


def test_buscar_colaboradores_por_prefixo_nome_escapa_metacaracteres_like():
    ok1, _ = _colab(
        nome="ColPct%Underscore_Z",
        email="col_pct_under@example.com",
        numero_contato="11991055700",
    )
    ok2, _ = _colab(
        nome="Col_Meta_X",
        email="col_meta_x@example.com",
        numero_contato="11991055701",
    )
    assert ok1 and ok2
    r1 = buscar_colaboradores_por_prefixo_nome("ColPct%")
    assert len(r1) == 1
    assert r1[0][1] == "ColPct%Underscore_Z"
    r2 = buscar_colaboradores_por_prefixo_nome("Col_")
    assert len(r2) == 1
    assert r2[0][1] == "Col_Meta_X"


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
        nif_ou_documento=str(cur.get("nif_ou_documento") or "123456789"),
        identificacao_internacional=bool(cur.get("identificacao_internacional")),
        numero_contato=cur["whatsapp"],
        observacoes=cur["observacoes"],
        servicos_repasse=[
            (cur["linhas"][0]["servico_id"], 25.0, cur["linhas"][0]["data_insercao_linha"] or date.today().isoformat()),
        ],
        documento_passaporte_residencia_cc=str(cur.get("documento_passaporte_residencia_cc") or ""),
        atividade_economica_aberta=bool(cur.get("atividade_economica_aberta")),
        atividade_economica_codigo=str(cur.get("atividade_economica_codigo") or ""),
        atividade_economica_descricao=str(cur.get("atividade_economica_descricao") or ""),
        contrato_prestacao_assinado=bool(cur.get("contrato_prestacao_assinado")),
        contrato_prestacao_data_assinatura=str(cur.get("contrato_prestacao_data_assinatura") or ""),
        iban_dados_bancarios=str(cur.get("iban_dados_bancarios") or _IBAN_COLAB_TESTE),
    )
    assert ok3, msg3


def test_parceria_iban_obrigatorio():
    sid = _primeiro_servico_id()
    ok, msg = cadastrar_colaborador(
        nome="Sem IBAN",
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
        email="sem.iban.col@example.com",
        nif_ou_documento="123456789",
        identificacao_internacional=False,
        numero_contato="11988776633",
        observacoes="",
        servicos_repasse=[_linha_svc(sid, 10.0)],
        iban_dados_bancarios="",
    )
    assert ok is False
    assert "iban" in msg.lower()


def test_parceria_actividade_aberta_so_codigo_falha():
    sid = _primeiro_servico_id()
    ok, msg = cadastrar_colaborador(
        nome="AE incompleta",
        sexo="Masculino",
        data_nascimento=_adult_dob(),
        endereco_rua="Rua A",
        endereco_numero="1",
        endereco_complemento="",
        codigo_postal="4800-100",
        concelho="Guimarães",
        freguesia="Selho",
        distrito="",
        pais="Portugal",
        email="ae.incompleta@example.com",
        nif_ou_documento="123456789",
        identificacao_internacional=False,
        numero_contato="11988776634",
        observacoes="",
        servicos_repasse=[_linha_svc(sid, 11.0)],
        atividade_economica_aberta=True,
        atividade_economica_codigo="12345",
        atividade_economica_descricao="",
        iban_dados_bancarios=_IBAN_COLAB_TESTE,
    )
    assert ok is False
    assert "código" in msg.lower() or "descrição" in msg.lower() or "ambos" in msg.lower()


def test_parceria_contrato_sim_sem_data_falha():
    sid = _primeiro_servico_id()
    ok, msg = cadastrar_colaborador(
        nome="Contrato sem data",
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
        email="ctr.sem.data@example.com",
        nif_ou_documento="123456789",
        identificacao_internacional=False,
        numero_contato="11988776635",
        observacoes="",
        servicos_repasse=[_linha_svc(sid, 12.0)],
        contrato_prestacao_assinado=True,
        contrato_prestacao_data_assinatura="",
        iban_dados_bancarios=_IBAN_COLAB_TESTE,
    )
    assert ok is False
    assert "data" in msg.lower() or "assinatura" in msg.lower()


def test_parceria_actividade_aberta_ok():
    sid = _primeiro_servico_id()
    ok, msg = cadastrar_colaborador(
        nome="AE completa OK",
        sexo="Outro",
        data_nascimento=_adult_dob(),
        endereco_rua="Rua A",
        endereco_numero="1",
        endereco_complemento="",
        codigo_postal="4800-100",
        concelho="Guimarães",
        freguesia="Selho",
        distrito="",
        pais="Portugal",
        email="ae.ok@example.com",
        nif_ou_documento="123456789",
        identificacao_internacional=False,
        numero_contato="11988776636",
        observacoes="",
        servicos_repasse=[_linha_svc(sid, 13.0)],
        documento_passaporte_residencia_cc="CC 123",
        atividade_economica_aberta=True,
        atividade_economica_codigo="CAE-X",
        atividade_economica_descricao="Serviços de bem-estar",
        contrato_prestacao_assinado=True,
        contrato_prestacao_data_assinatura="2024-06-01",
        iban_dados_bancarios=_IBAN_COLAB_TESTE,
    )
    assert ok, msg
    conn = get_connection()
    assert conn
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT atividade_economica_codigo, iban_dados_bancarios FROM colaboradores WHERE nome = ?",
            ("AE completa OK",),
        )
        row = cur.fetchone()
        assert row and row[0] == "CAE-X"
        assert row[1] == _IBAN_COLAB_TESTE
    finally:
        conn.close()
