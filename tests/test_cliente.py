"""Testes unitários — módulo cliente (E21: busca consolidada, data nascimento titular)."""

from src.modules.cliente import (
    buscar_cliente_por_whatsapp,
    buscar_clientes_por_nif_email_telefone,
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
