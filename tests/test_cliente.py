"""Testes unitários — módulo cliente (E21: busca consolidada, data nascimento titular)."""

from src.modules.cliente import (
    buscar_cliente_por_whatsapp,
    buscar_clientes_por_nif_email_telefone,
    buscar_clientes_por_prefixo_nome,
    cadastrar_cliente,
)


def test_busca_sem_criterios_devolve_vazio():
    assert buscar_clientes_por_nif_email_telefone() == []


def _cadastro_busca(*, email: str, tel: str, nif: str):
    ok, msg = cadastrar_cliente(
        nome="Cliente Busca E21",
        numero_contato=tel,
        endereco_rua="Rua Teste",
        endereco_numero="9",
        endereco_complemento="",
        codigo_postal="4000-099",
        concelho="Porto",
        freguesia="Centro",
        distrito="",
        pais="Portugal",
        email=email,
        sexo="Masculino",
        tem_filhos=False,
        filhos=[],
        gravida=None,
        data_parto_prevista=None,
        observacoes="",
        contatos_emergencia=[],
        nif=nif,
        documento_identificacao_internacional=False,
        data_nascimento="1988-03-21",
    )
    assert ok, msg


def test_busca_por_telefone_email_e_nif():
    tel = "+351910555443"
    email = "busca_e21@example.com"
    nif = "286303850"
    _cadastro_busca(email=email, tel=tel, nif=nif)

    cid = buscar_cliente_por_whatsapp(tel)
    assert cid is not None

    assert buscar_clientes_por_nif_email_telefone(telefone=tel) == [(cid, "Cliente Busca E21")]
    assert buscar_clientes_por_nif_email_telefone(email=email) == [(cid, "Cliente Busca E21")]
    assert buscar_clientes_por_nif_email_telefone(nif=nif) == [(cid, "Cliente Busca E21")]


def _cadastro_prefixo_nome(*, nome: str, email: str, tel: str, doc: str):
    ok, msg = cadastrar_cliente(
        nome=nome,
        numero_contato=tel,
        endereco_rua="Rua Teste",
        endereco_numero="9",
        endereco_complemento="",
        codigo_postal="4000-099",
        concelho="Porto",
        freguesia="Centro",
        distrito="",
        pais="Portugal",
        email=email,
        sexo="Masculino",
        tem_filhos=False,
        filhos=[],
        gravida=None,
        data_parto_prevista=None,
        observacoes="",
        contatos_emergencia=[],
        nif=doc,
        documento_identificacao_internacional=True,
        data_nascimento="1988-03-21",
    )
    assert ok, msg


def test_busca_por_prefixo_nome_vazio_devolve_vazio():
    assert buscar_clientes_por_prefixo_nome("") == []
    assert buscar_clientes_por_prefixo_nome("   ") == []


def test_busca_por_prefixo_nome_encontra_e_ordena():
    _cadastro_prefixo_nome(
        nome="Zé Unificado Prefixo Alfa",
        email="prefixo_alfa@example.com",
        tel="+351910555601",
        doc="INT-PRF-ALFA-01",
    )
    _cadastro_prefixo_nome(
        nome="Zé Unificado Prefixo Beta",
        email="prefixo_beta@example.com",
        tel="+351910555602",
        doc="INT-PRF-BETA-02",
    )
    rows = buscar_clientes_por_prefixo_nome("Zé Unificado")
    assert len(rows) == 2
    assert [n for _, n in rows] == ["Zé Unificado Prefixo Alfa", "Zé Unificado Prefixo Beta"]


def test_busca_por_prefixo_nome_sem_match():
    assert buscar_clientes_por_prefixo_nome("NomeInexistenteZZZprefixo") == []


def test_busca_por_prefixo_nome_respeita_limite():
    for i in range(4):
        _cadastro_prefixo_nome(
            nome=f"LimNomeBusca {i:03d}",
            email=f"limnome_{i}@example.com",
            tel=f"+351910556{i:03d}",
            doc=f"INT-LIM-{i:03d}-DOC",
        )
    rows = buscar_clientes_por_prefixo_nome("LimNomeBusca", limit=2)
    assert len(rows) == 2


def test_busca_por_prefixo_nome_escapa_metacaracteres_like():
    _cadastro_prefixo_nome(
        nome="ClientePct%Underscore_Z",
        email="pct_under@example.com",
        tel="+351910557001",
        doc="INT-PCT-UNDER-01",
    )
    _cadastro_prefixo_nome(
        nome="Cliente_Meta_X",
        email="meta_x@example.com",
        tel="+351910557002",
        doc="INT-META-X-02",
    )
    r1 = buscar_clientes_por_prefixo_nome("ClientePct%")
    assert len(r1) == 1
    assert r1[0][1] == "ClientePct%Underscore_Z"
    r2 = buscar_clientes_por_prefixo_nome("Cliente_")
    assert len(r2) == 1
    assert r2[0][1] == "Cliente_Meta_X"


def test_cadastrar_sem_data_nascimento_rejeita():
    ok, msg = cadastrar_cliente(
        nome="Sem DN",
        numero_contato="+351910666778",
        endereco_rua="Rua",
        endereco_numero="1",
        endereco_complemento="",
        codigo_postal="4000-088",
        concelho="Porto",
        freguesia="Centro",
        distrito="",
        pais="Portugal",
        email="sem_dn_e21@example.com",
        sexo="Masculino",
        tem_filhos=False,
        filhos=[],
        gravida=None,
        data_parto_prevista=None,
        observacoes="",
        contatos_emergencia=[],
        nif="286303850",
        documento_identificacao_internacional=False,
        data_nascimento=None,
    )
    assert ok is False
    assert "nascimento" in msg.lower()
