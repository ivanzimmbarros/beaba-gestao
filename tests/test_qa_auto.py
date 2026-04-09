import pytest

from src.modules.cliente import cadastrar_cliente
from src.modules.validators import normalizar_codigo_postal_pt


def _cli(**kw):
    base = dict(
        nome="Diretor Auto",
        numero_contato="11999998888",
        endereco_rua="Rua das Flores",
        endereco_numero="10",
        endereco_complemento="",
        codigo_postal="4800-123",
        concelho="Guimarães",
        freguesia="Oliveira do Castelo",
        distrito="Braga",
        pais="Portugal",
        email="diretor@beaba.pt",
        sexo="Masculino",
        tem_filhos=False,
        filhos=[],
        gravida=None,
        data_parto_prevista=None,
        observacoes="",
        contatos_emergencia=[],
        nif="123456789",
        documento_identificacao_internacional=False,
    )
    base.update(kw)
    return cadastrar_cliente(**base)


def test_normalizar_cp():
    assert normalizar_codigo_postal_pt("4800123") == "4800-123"
    assert normalizar_codigo_postal_pt("4800-123") == "4800-123"
    assert normalizar_codigo_postal_pt("48") is None


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
    assert "inválido" in msg.lower() or "contacto" in msg.lower()


def test_limpeza_caracteres_especiais():
    ok, _msg = _cli(numero_contato="(11) 99999-9999")
    assert ok is True


def test_codigo_postal_invalido():
    ok, msg = _cli(codigo_postal="123")
    assert ok is False
    assert "postal" in msg.lower()


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


def test_filho_sem_nome_invalido():
    ok, msg = _cli(tem_filhos=True, filhos=[("", 5, "Feminino")])
    assert ok is False
    assert "filho" in msg.lower()


def test_filhos_com_nome_valido():
    ok, _msg = _cli(
        tem_filhos=True,
        filhos=[("Ana", 4, "Feminino"), ("Miguel", 7, "Masculino")],
    )
    assert ok is True


def test_gravida_sem_data_invalido():
    ok, msg = _cli(
        sexo="Feminino",
        gravida=True,
        data_parto_prevista=None,
    )
    assert ok is False
