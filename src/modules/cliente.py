import sqlite3

from src.database.connection import get_connection
from src.modules.constants import SEXOS
from src.modules.validators import (
    email_valido,
    normalizar_codigo_postal_pt,
    parse_data_iso,
    validar_e_limpar_telefone,
)


def cadastrar_cliente(
    nome: str,
    numero_contato: str,
    endereco_rua: str,
    endereco_numero: str,
    endereco_complemento: str,
    codigo_postal: str,
    concelho: str,
    freguesia: str,
    distrito: str,
    pais: str,
    email: str,
    sexo: str,
    tem_filhos: bool,
    filhos: list[tuple[str, int, str]],
    gravida: bool | None,
    data_parto_prevista: str | None,
    observacoes: str,
    contatos_emergencia: list[tuple[str, str]],
) -> tuple[bool, str]:
    """
    Persiste cliente + filhos + contactos de emergência.
    `filhos`: lista de (nome, idade_anos, sexo).
    Coluna técnica `whatsapp` guarda o número principal (11 dígitos, UNIQUE).
    """
    nome = (nome or "").strip()
    if not nome:
        return False, "❌ O nome completo é obrigatório."

    tel = validar_e_limpar_telefone(numero_contato)
    if not tel:
        return False, "❌ O número de contacto deve ter 11 dígitos numéricos."

    rua = (endereco_rua or "").strip()
    num = (endereco_numero or "").strip()
    comp = (endereco_complemento or "").strip()
    cp = normalizar_codigo_postal_pt(codigo_postal)
    conc = (concelho or "").strip()
    freg = (freguesia or "").strip()
    dist = (distrito or "").strip()
    pais_v = (pais or "").strip() or "Portugal"

    if not rua:
        return False, "❌ A rua (logradouro) é obrigatória."
    if not num:
        return False, "❌ O número de porta é obrigatório."
    if not cp:
        return False, "❌ O código postal é obrigatório (formato XXXX-XXX, ex.: 4800-123)."
    if not conc:
        return False, "❌ O concelho é obrigatório."
    if not freg:
        return False, "❌ A freguesia é obrigatória."

    email = (email or "").strip()
    if not email:
        return False, "❌ O email é obrigatório."
    if not email_valido(email):
        return False, "❌ Indique um email válido."

    if sexo not in SEXOS:
        return False, "❌ Selecione uma opção de sexo."

    if sexo == "Feminino":
        if gravida is None:
            return False, "❌ Indique se está grávida."
        if gravida is True:
            if not parse_data_iso(data_parto_prevista):
                return False, "❌ Indique a estimativa de data de parto (data válida)."
    else:
        gravida = None
        data_parto_prevista = None

    if tem_filhos:
        if not filhos:
            return (
                False,
                "❌ Indique os dados de cada filho (nome, idade em anos completos e sexo).",
            )
        for fn, idade, sx in filhos:
            fn = (fn or "").strip()
            if not fn:
                return False, "❌ O nome de cada filho é obrigatório."
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
                gravida, data_parto_prevista, observacoes,
                endereco_rua, endereco_numero, endereco_complemento,
                codigo_postal, concelho, freguesia, distrito, pais
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                nome,
                tel,
                "",
                email,
                sexo,
                tem_filhos_int,
                gravida_db,
                parto_db,
                obs,
                rua,
                num,
                comp,
                cp,
                conc,
                freg,
                dist,
                pais_v,
            ),
        )
        cid = cursor.lastrowid
        for i, (fnome, idade, sx) in enumerate(filhos, start=1):
            cursor.execute(
                """
                INSERT INTO cliente_filhos (cliente_id, ordem, nome, idade_anos, sexo)
                VALUES (?, ?, ?, ?, ?)
                """,
                (cid, i, fnome.strip(), int(idade), sx),
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
