import pytest
from src.modules.cliente import cadastrar_cliente
from src.database.connection import create_tables
import os

@pytest.fixture(autouse=True)
def setup_db():
    """Prepara um banco de teste limpo antes de cada validação"""
    if os.path.exists("data/beaba_gestao.db"):
        os.remove("data/beaba_gestao.db")
    create_tables()

def test_cadastro_sucesso():
    ok, _msg = cadastrar_cliente("Diretor Auto", "11999998888")
    assert ok is True

def test_duplicidade_proibida():
    cadastrar_cliente("Original", "11888887777")
    ok, msg = cadastrar_cliente("Clone", "11888887777")
    assert ok is False
    assert "já" in msg.lower()

def test_whatsapp_invalido_curto():
    ok, msg = cadastrar_cliente("Erro Humano", "123")
    assert ok is False
    assert "11" in msg

def test_limpeza_caracteres_especiais():
    ok, _msg = cadastrar_cliente("Sujo", "(11) 99999-9999")
    assert ok is True
