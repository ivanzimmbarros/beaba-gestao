"""E16 — NIF PT e normalização telefone (domínio)."""

from src.modules.nif import normalizar_nif_armazenamento, validar_nif_portugal
from src.modules.telefone import normalizar_telefone_legado_ou_e164


def test_nif_pt_valido():
    assert validar_nif_portugal("123456789") is True


def test_nif_pt_invalido_digito():
    assert validar_nif_portugal("123456788") is False


def test_normalizar_nif_pt():
    ok, err, v = normalizar_nif_armazenamento(
        "123 456 789", documento_identificacao_internacional=False
    )
    assert ok and err == "" and v == "123456789"


def test_normalizar_doc_internacional():
    ok, err, v = normalizar_nif_armazenamento(
        "AB-12.34", documento_identificacao_internacional=True
    )
    assert ok and v == "AB-12.34"


def test_e164_legado_onze_digitos():
    assert normalizar_telefone_legado_ou_e164("91234567890") == "+5591234567890"


def test_e164_prefixo_mais():
    assert normalizar_telefone_legado_ou_e164("+351912345678") == "+351912345678"
