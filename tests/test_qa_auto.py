import pytest
from src.modules.cliente import cadastrar_cliente
from src.database.connection import get_connection, create_tables
import os

@pytest.fixture(autouse=True)
def setup_db():
    """Prepara um banco de teste limpo antes de cada validação"""
    if os.path.exists("data/beaba_gestao.db"):
        os.remove("data/beaba_gestao.db")
    create_tables()

def test_cadastro_sucesso():
    assert cadastrar_cliente("Diretor Auto", "11999998888") == True

def test_duplicidade_proibida():
    cadastrar_cliente("Original", "11888887777")
    # O robô tenta cadastrar o mesmo número com outro nome
    resultado = cadastrar_cliente("Clone", "11888887777")
    assert "já está cadastrado" in str(resultado)

def test_whatsapp_invalido_curto():
    resultado = cadastrar_cliente("Erro Humano", "123")
    assert "quantidade de números está errada" in str(resultado)

def test_limpeza_caracteres_especiais():
    # O robô testa se o sistema limpa (11) 99999-9999 automaticamente
    assert cadastrar_cliente("Sujo", "(11) 99999-9999") == True
