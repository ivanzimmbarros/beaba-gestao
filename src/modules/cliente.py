import re
import sqlite3
from datetime import datetime

from src.database.connection import get_connection

SEXOS = ("Feminino", "Masculino", "Outro", "Prefiro não informar")


def validar_e_limpar_telefone(valor: str) -> str | None:
    num_limpo = re.sub(r"\D", "", valor or "")
    return num_limpo if len(num_limpo) == 11 else None


def _email_valido(email: str) -> bool:
    e = (email or "").strip()
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", e))


def _parse_data_iso(s: str | None) -> bool:
    if not s or not str(s).strip():
        return False
    try:
        datetime.strptime(str(s).strip()[:10], "%Y-%m-%d")
        return True
    except ValueError:
        return False


def cadastrar_cliente(
    nome: str,
    numero_contato: str,
    morada: str,
    email: str,
    sexo: str,
    tem_filhos: bool,
    filhos: list[tuple[int, str]],
    gravida: bool | None,
    data_parto_prevista: str | None,
    observacoes: str,
    contatos_emergencia: list[tuple[str, str]],
) -> tuple[bool, str]:
    """
    Persiste cliente + filhos + contactos de emergência.
    Coluna técnica `whatsapp` guarda o número principal (11 dígitos, UNIQUE).
    """
    nome = (nome or "").strip()
    if not nome:
        return False, "❌ O nome completo é obrigatório."

    tel = validar_e_limpar_telefone(numero_contato)
    if not tel:
        return False, "❌ O número de contato deve ter 11 dígitos numéricos."

    morada = (morada or "").strip()
    if not morada:
        return False, "❌ A morada é obrigatória."

    email = (email or "").strip()
    if not email:
        return False, "❌ O email é obrigatório."
    if not _email_valido(email):
        return False, "❌ Indique um email válido."

    if sexo not in SEXOS:
        return False, "❌ Selecione uma opção de sexo."

    if sexo == "Feminino":
        if gravida is None:
            return False, "❌ Indique se está grávida."
        if gravida is True:
            if not _parse_data_iso(data_parto_prevista):
                return False, "❌ Indique a estimativa de data de parto (data válida)."
    else:
        gravida = None
        data_parto_prevista = None

    if tem_filhos:
        if not filhos:
            return False, "❌ Indique os dados de cada filho (idade em anos completos e sexo)."
        for idade, sx in filhos:
            if idade < 0 or idade > 120:
                return False, "❌ Idade dos filhos deve estar entre 0 e 120 anos."
            if sx not in SEXOS:
                return False, "❌ Sexo de cada filho deve ser selecionado."
    else:
        filhos = []

    emerg_ok: list[tuple[str, str]] = []
    for n, t in contatos_emergencia:
        n = (n or "").strip()
        t_raw = validar_e_limpar_telefone(t or "")
        if not n and not t_raw:
            continue
        if not n or not t_raw:
            return (
                False,
                "❌ Cada contacto de emergência deve ter nome e número de contacto (11 dígitos).",
            )
        emerg_ok.append((n, t_raw))

    obs = (observacoes or "").strip()

    conn = get_connection()
    if not conn:
        return False, "❌ Não foi possível ligar à base de dados."

    tem_filhos_int = 1 if tem_filhos else 0
    gravida_db: int | None
    if sexo == "Feminino":
        gravida_db = 1 if gravida else 0
    else:
        gravida_db = None

    parto_db = None
    if sexo == "Feminino" and gravida is True and data_parto_prevista:
        parto_db = str(data_parto_prevista).strip()[:10]

    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO clientes (
                nome, whatsapp, morada, email, sexo, tem_filhos,
                gravida, data_parto_prevista, observacoes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nome,
                tel,
                morada,
                email,
                sexo,
                tem_filhos_int,
                gravida_db,
                parto_db,
                obs,
            ),
        )
        cid = cursor.lastrowid
        for i, (idade, sx) in enumerate(filhos, start=1):
            cursor.execute(
                """
                INSERT INTO cliente_filhos (cliente_id, ordem, idade_anos, sexo)
                VALUES (?, ?, ?, ?)
                """,
                (cid, i, int(idade), sx),
            )
        for i, (enome, etel) in enumerate(emerg_ok, start=1):
            cursor.execute(
                """
                INSERT INTO cliente_contatos_emergencia (cliente_id, ordem, nome, telefone)
                VALUES (?, ?, ?, ?)
                """,
                (cid, i, enome, etel),
            )
        conn.commit()
        return True, "✅ Cliente cadastrado com sucesso."
    except sqlite3.IntegrityError:
        conn.rollback()
        return False, "⚠️ Este número de contacto já está cadastrado."
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro ao guardar: {e}"
    finally:
        conn.close()
