import sqlite3
from datetime import date, datetime

from src.database.connection import get_connection
from src.modules.constants import SEXOS
from src.modules.nif import normalizar_nif_armazenamento
from src.modules.telefone import normalizar_telefone_legado_ou_e164
from src.modules.validators import (
    email_valido,
    normalizar_codigo_postal_pt,
    parse_data_iso,
)

FilhoInput = tuple[str, int, str] | tuple[str, int, str, str | None]

_DATA_NASC_TITULAR_MIN = date(1900, 1, 1)


def _notify_cloud_sync() -> None:
    try:
        from scripts.sync_trigger import notify_data_changed

        notify_data_changed()
    except Exception:
        pass


def _validar_data_nascimento_titular(data_nascimento: str | None) -> tuple[bool, str, str | None]:
    """Data de nascimento do titular: obrigatória, ISO AAAA-MM-DD, ≥ 1900-01-01, não futura."""
    raw = (data_nascimento or "").strip()
    if not raw:
        return False, "❌ A data de nascimento é obrigatória (formato AAAA-MM-DD).", None
    ds = raw[:10]
    if not parse_data_iso(ds):
        return False, "❌ Data de nascimento inválida.", None
    dt = datetime.strptime(ds, "%Y-%m-%d").date()
    if dt < _DATA_NASC_TITULAR_MIN:
        return False, "❌ Data de nascimento não pode ser anterior a 01/01/1900.", None
    if dt > date.today():
        return False, "❌ Data de nascimento não pode ser futura.", None
    return True, "", ds


def _idade_anos_de_data_nascimento(iso_yyyy_mm_dd: str) -> int:
    d = datetime.strptime(str(iso_yyyy_mm_dd).strip()[:10], "%Y-%m-%d").date()
    today = date.today()
    years = today.year - d.year - ((today.month, today.day) < (d.month, d.day))
    return max(0, min(120, years))


def _normalizar_filho(t: FilhoInput) -> tuple[bool, str, tuple[str, int, str, str | None]]:
    """Devolve (ok, msg, (nome, idade, sexo, data_nasc_iso|None))."""
    nome = (t[0] or "").strip()
    idade_in = int(t[1])
    sx = str(t[2] or "")
    dn: str | None = None
    if len(t) >= 4 and t[3] and str(t[3]).strip():
        ds = str(t[3]).strip()[:10]
        if not parse_data_iso(ds):
            return False, "❌ Data de nascimento do filho inválida.", ("", 0, "", None)
        dt = datetime.strptime(ds, "%Y-%m-%d").date()
        if dt > date.today():
            return False, "❌ Data de nascimento do filho não pode ser futura.", ("", 0, "", None)
        oldest = date.today().replace(year=date.today().year - 121)
        if dt < oldest:
            return False, "❌ Data de nascimento do filho demasiado antiga.", ("", 0, "", None)
        dn = ds
        idade_final = _idade_anos_de_data_nascimento(ds)
    else:
        idade_final = idade_in
        if idade_final < 0 or idade_final > 120:
            return False, "❌ Idade dos filhos deve estar entre 0 e 120 anos.", ("", 0, "", None)

    if not nome:
        return False, "❌ O nome de cada filho é obrigatório.", ("", 0, "", None)
    if sx not in SEXOS:
        return False, "❌ Sexo de cada filho deve ser selecionado.", ("", 0, "", None)
    return True, "", (nome, idade_final, sx, dn)


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
    filhos: list[FilhoInput],
    gravida: bool | None,
    data_parto_prevista: str | None,
    observacoes: str,
    contatos_emergencia: list[tuple[str, str]],
    *,
    nif: str,
    documento_identificacao_internacional: bool,
    data_nascimento: str | None,
) -> tuple[bool, str]:
    """
    `filhos`: (nome, idade, sexo) ou (nome, idade, sexo, data_nascimento_iso opcional).
    Coluna `whatsapp`: contacto principal em E.164.
    `data_nascimento`: data de nascimento do titular (ISO AAAA-MM-DD), obrigatória.
    """
    nome = (nome or "").strip()
    if not nome:
        return False, "❌ O nome completo é obrigatório."

    tel = normalizar_telefone_legado_ou_e164(numero_contato)
    if not tel:
        return False, (
            "❌ Número de contacto inválido. Use país + número no formulário ou formato internacional (+…)."
        )

    ok_n, msg_n, nif_v = normalizar_nif_armazenamento(
        nif, documento_identificacao_internacional=documento_identificacao_internacional
    )
    if not ok_n:
        return False, msg_n

    ok_dn, msg_dn, dn_iso = _validar_data_nascimento_titular(data_nascimento)
    if not ok_dn:
        return False, msg_dn

    doc_intl = 1 if documento_identificacao_internacional else 0

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

    filhos_norm: list[tuple[str, int, str, str | None]] = []
    if tem_filhos:
        if not filhos:
            return (
                False,
                "❌ Indique os dados de cada filho (nome, idade em anos completos e sexo).",
            )
        for row in filhos:
            ok_f, msg_f, expanded = _normalizar_filho(row)
            if not ok_f:
                return False, msg_f
            filhos_norm.append(expanded)
    else:
        filhos_norm = []

    emerg_ok: list[tuple[str, str]] = []
    for n, t in contatos_emergencia:
        n = (n or "").strip()
        t_e164 = normalizar_telefone_legado_ou_e164(t or "")
        if not n and not t_e164:
            continue
        if not n or not t_e164:
            return (
                False,
                "❌ Cada contacto de emergência deve ter nome e número de contacto válidos.",
            )
        emerg_ok.append((n, t_e164))

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
                codigo_postal, concelho, freguesia, distrito, pais,
                nif_ou_documento, identificacao_internacional, data_nascimento
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                nif_v,
                doc_intl,
                dn_iso,
            ),
        )
        cid = cursor.lastrowid
        for i, (fnome, idade, sx, dn) in enumerate(filhos_norm, start=1):
            cursor.execute(
                """
                INSERT INTO cliente_filhos (cliente_id, ordem, nome, idade_anos, sexo, data_nascimento)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (cid, i, fnome.strip(), int(idade), sx, dn),
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
        _notify_cloud_sync()
        return True, "✅ Cliente cadastrado com sucesso."
    except sqlite3.IntegrityError:
        conn.rollback()
        return False, "⚠️ Este número de contacto já está cadastrado."
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro ao guardar: {e}"
    finally:
        conn.close()


def buscar_cliente_por_whatsapp(numero_contato: str) -> int | None:
    """Retorna `id` do cliente ou None se não existir."""
    tel = normalizar_telefone_legado_ou_e164(numero_contato)
    if not tel:
        return None
    conn = get_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM clientes WHERE whatsapp = ?", (tel,))
        row = cur.fetchone()
        return int(row[0]) if row else None
    finally:
        conn.close()


def buscar_clientes_por_nif_email_telefone(
    *,
    nif: str = "",
    email: str = "",
    telefone: str = "",
    documento_internacional: bool = False,
) -> list[tuple[int, str]]:
    """
    Pesquisa por OR (NIF normalizado, email trim+lower, telefone E.164).
    Devolve lista `(id, nome)` sem duplicados, ordenada por nome (NOCASE).
    """
    merged: dict[int, str] = {}

    conn = get_connection()
    if not conn:
        return []

    def _add_rows(rows: list[tuple[int, str]]) -> None:
        for cid, nome in rows:
            merged[int(cid)] = str(nome)

    try:
        cur = conn.cursor()
        tel = normalizar_telefone_legado_ou_e164((telefone or "").strip())
        if tel:
            cur.execute(
                "SELECT id, nome FROM clientes WHERE whatsapp = ? ORDER BY nome COLLATE NOCASE",
                (tel,),
            )
            _add_rows([(int(a), str(b)) for a, b in cur.fetchall()])

        em = (email or "").strip().lower()
        if em and email_valido(em):
            cur.execute(
                """
                SELECT id, nome FROM clientes
                WHERE lower(trim(email)) = ?
                ORDER BY nome COLLATE NOCASE
                """,
                (em,),
            )
            _add_rows([(int(a), str(b)) for a, b in cur.fetchall()])

        nif_raw = (nif or "").strip()
        if nif_raw:
            ok_n, _, nif_v = normalizar_nif_armazenamento(
                nif_raw, documento_identificacao_internacional=documento_internacional
            )
            if ok_n:
                cur.execute(
                    """
                    SELECT id, nome FROM clientes
                    WHERE nif_ou_documento = ?
                    ORDER BY nome COLLATE NOCASE
                    """,
                    (nif_v,),
                )
                _add_rows([(int(a), str(b)) for a, b in cur.fetchall()])
    finally:
        conn.close()

    out = sorted(merged.items(), key=lambda x: (x[1].lower(), x[0]))
    return [(i, n) for i, n in out]


def buscar_clientes_por_prefixo_nome(prefixo: str, *, limit: int = 40) -> list[tuple[int, str]]:
    """
    Clientes cujo nome começa por `prefixo` (trim, comparação por LIKE case-insensitive).
    SQL parametrizado; `%` e `_` no prefixo são escapados. `limit` capa custo em bases grandes.
    """
    raw = (prefixo or "").strip()
    if not raw:
        return []
    lim = max(1, min(int(limit), 200))

    esc = raw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    like_arg = f"{esc}%"

    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, nome FROM clientes
            WHERE nome LIKE ? ESCAPE '\\'
            ORDER BY nome COLLATE NOCASE
            LIMIT ?
            """,
            (like_arg, lim),
        )
        return [(int(a), str(b)) for a, b in cur.fetchall()]
    finally:
        conn.close()


def listar_clientes_resumo() -> list[tuple[int, str]]:
    """Lista `(id, nome)` para filtros e selects (ex.: agendamentos)."""
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, nome FROM clientes ORDER BY nome COLLATE NOCASE")
        return [(int(a), str(b)) for a, b in cur.fetchall()]
    finally:
        conn.close()


def listar_clientes_resumo_com_credito(
    *, filtro_saldo: str = "todos"
) -> list[tuple[int, str, int]]:
    """`(id, nome, saldo_credito_centavos)` — `filtro_saldo`: todos | com_saldo | sem_saldo."""
    conn = get_connection()
    if not conn:
        return []
    f = str(filtro_saldo or "todos").strip().lower()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT c.id, c.nome, COALESCE(w.saldo_credito_centavos, 0)
            FROM clientes c
            LEFT JOIN vw_cliente_saldo_credito w ON w.cliente_id = c.id
            ORDER BY c.nome COLLATE NOCASE
            """
        )
        rows = [(int(a), str(b), int(c)) for a, b, c in cur.fetchall()]
        if f == "com_saldo":
            return [r for r in rows if r[2] > 0]
        if f == "sem_saldo":
            return [r for r in rows if r[2] <= 0]
        return rows
    finally:
        conn.close()


def obter_cliente_completo(cliente_id: int) -> dict | None:
    """Ficha completa para edição (cliente + filhos + emergência)."""
    cid = int(cliente_id)
    if cid < 1:
        return None
    conn = get_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, nome, whatsapp, email, sexo, tem_filhos, gravida, data_parto_prevista,
                   observacoes, endereco_rua, endereco_numero, endereco_complemento,
                   codigo_postal, concelho, freguesia, distrito, pais,
                   nif_ou_documento, identificacao_internacional, data_nascimento
            FROM clientes WHERE id = ?
            """,
            (cid,),
        )
        row = cur.fetchone()
        if not row:
            return None
        cur.execute(
            """
            SELECT nome, idade_anos, sexo, data_nascimento FROM cliente_filhos
            WHERE cliente_id = ? ORDER BY ordem
            """,
            (cid,),
        )
        filhos_raw = cur.fetchall()
        filhos: list[tuple[str, int, str, str | None]] = []
        for a, b, c, d in filhos_raw:
            dn = str(d).strip()[:10] if d else None
            if dn and not parse_data_iso(dn):
                dn = None
            filhos.append((str(a), int(b), str(c), dn))
        cur.execute(
            """
            SELECT nome, telefone FROM cliente_contatos_emergencia
            WHERE cliente_id = ? ORDER BY ordem
            """,
            (cid,),
        )
        emerg = [(str(a), str(b)) for a, b in cur.fetchall()]
        gf: bool | None
        if row[5]:
            gf = bool(row[5])
        else:
            gf = False
        sexo_v = str(row[4] or "")
        grav_v: bool | None
        if sexo_v == "Feminino":
            grav_v = bool(row[6]) if row[6] is not None else None
        else:
            grav_v = None
        nif_raw = row[17] if len(row) > 17 else None
        id_intl = int(row[18]) if len(row) > 18 and row[18] is not None else 0
        dn_tit = row[19] if len(row) > 19 else None
        dn_tit_s = str(dn_tit).strip()[:10] if dn_tit else None
        if dn_tit_s and not parse_data_iso(dn_tit_s):
            dn_tit_s = None
        return {
            "id": int(row[0]),
            "nome": str(row[1]),
            "whatsapp": str(row[2]),
            "email": str(row[3] or ""),
            "sexo": sexo_v,
            "tem_filhos": gf,
            "gravida": grav_v,
            "data_parto_prevista": str(row[7]) if row[7] else None,
            "observacoes": str(row[8] or ""),
            "endereco_rua": str(row[9] or ""),
            "endereco_numero": str(row[10] or ""),
            "endereco_complemento": str(row[11] or ""),
            "codigo_postal": str(row[12] or ""),
            "concelho": str(row[13] or ""),
            "freguesia": str(row[14] or ""),
            "distrito": str(row[15] or ""),
            "pais": str(row[16] or "Portugal"),
            "nif_ou_documento": str(nif_raw) if nif_raw is not None else "",
            "identificacao_internacional": bool(id_intl),
            "data_nascimento": dn_tit_s,
            "filhos": filhos,
            "contatos_emergencia": emerg,
        }
    finally:
        conn.close()


def atualizar_cliente(
    cliente_id: int,
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
    filhos: list[FilhoInput],
    gravida: bool | None,
    data_parto_prevista: str | None,
    observacoes: str,
    contatos_emergencia: list[tuple[str, str]],
    *,
    nif: str,
    documento_identificacao_internacional: bool,
    data_nascimento: str | None,
) -> tuple[bool, str]:
    """Atualiza ficha existente. Validações alinhadas a `cadastrar_cliente`."""
    cid = int(cliente_id)
    if cid < 1:
        return False, "❌ Cliente inválido."

    nome = (nome or "").strip()
    if not nome:
        return False, "❌ O nome completo é obrigatório."

    tel = normalizar_telefone_legado_ou_e164(numero_contato)
    if not tel:
        return False, (
            "❌ Número de contacto inválido. Use país + número no formulário ou formato internacional (+…)."
        )

    ok_n, msg_n, nif_v = normalizar_nif_armazenamento(
        nif, documento_identificacao_internacional=documento_identificacao_internacional
    )
    if not ok_n:
        return False, msg_n

    ok_dn, msg_dn, dn_iso = _validar_data_nascimento_titular(data_nascimento)
    if not ok_dn:
        return False, msg_dn

    doc_intl = 1 if documento_identificacao_internacional else 0

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

    filhos_norm: list[tuple[str, int, str, str | None]] = []
    if tem_filhos:
        if not filhos:
            return (
                False,
                "❌ Indique os dados de cada filho (nome, idade em anos completos e sexo).",
            )
        for row in filhos:
            ok_f, msg_f, expanded = _normalizar_filho(row)
            if not ok_f:
                return False, msg_f
            filhos_norm.append(expanded)
    else:
        filhos_norm = []

    emerg_ok: list[tuple[str, str]] = []
    for n, t in contatos_emergencia:
        n = (n or "").strip()
        t_e164 = normalizar_telefone_legado_ou_e164(t or "")
        if not n and not t_e164:
            continue
        if not n or not t_e164:
            return (
                False,
                "❌ Cada contacto de emergência deve ter nome e número de contacto válidos.",
            )
        emerg_ok.append((n, t_e164))

    obs = (observacoes or "").strip()
    tem_filhos_int = 1 if tem_filhos else 0
    gravida_db: int | None
    if sexo == "Feminino":
        gravida_db = 1 if gravida else 0
    else:
        gravida_db = None

    parto_db = None
    if sexo == "Feminino" and gravida is True and data_parto_prevista:
        parto_db = str(data_parto_prevista).strip()[:10]

    conn = get_connection()
    if not conn:
        return False, "❌ Não foi possível ligar à base de dados."

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM clientes WHERE id = ?", (cid,))
        if cursor.fetchone() is None:
            return False, "❌ Cliente não encontrado."

        cursor.execute(
            "SELECT id FROM clientes WHERE whatsapp = ? AND id != ?",
            (tel, cid),
        )
        if cursor.fetchone() is not None:
            return False, "⚠️ Este número de contacto já está associado a outro cliente."

        cursor.execute(
            """
            UPDATE clientes SET
                nome = ?, whatsapp = ?, morada = ?, email = ?, sexo = ?, tem_filhos = ?,
                gravida = ?, data_parto_prevista = ?, observacoes = ?,
                endereco_rua = ?, endereco_numero = ?, endereco_complemento = ?,
                codigo_postal = ?, concelho = ?, freguesia = ?, distrito = ?, pais = ?,
                nif_ou_documento = ?, identificacao_internacional = ?, data_nascimento = ?
            WHERE id = ?
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
                nif_v,
                doc_intl,
                dn_iso,
                cid,
            ),
        )
        cursor.execute("DELETE FROM cliente_filhos WHERE cliente_id = ?", (cid,))
        for i, (fnome, idade, sx, dn) in enumerate(filhos_norm, start=1):
            cursor.execute(
                """
                INSERT INTO cliente_filhos (cliente_id, ordem, nome, idade_anos, sexo, data_nascimento)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (cid, i, fnome.strip(), int(idade), sx, dn),
            )
        cursor.execute(
            "DELETE FROM cliente_contatos_emergencia WHERE cliente_id = ?",
            (cid,),
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
        _notify_cloud_sync()
        return True, "✅ Ficha de cliente atualizada."
    except sqlite3.IntegrityError:
        conn.rollback()
        return False, "⚠️ Conflito de dados (contacto duplicado?)."
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro ao guardar: {e}"
    finally:
        conn.close()


def listar_vendas_resumo_cliente(cliente_id: int, *, limit: int = 24) -> list[tuple[int, str, int, str]]:
    """
    Últimas vendas do cliente para painel «Histórico de Compras».
    Devolve (id, data_registo texto, total_final_centavos, estado_pagamento).
    """
    cid = int(cliente_id)
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, data_registo, total_final_centavos, estado_pagamento
            FROM vendas
            WHERE cliente_id = ?
            ORDER BY datetime(data_registo) DESC
            LIMIT ?
            """,
            (cid, int(limit)),
        )
        rows: list[tuple[int, str, int, str]] = []
        for vid, dr, tot, est in cur.fetchall():
            rows.append((int(vid), str(dr or "")[:19], int(tot or 0), str(est or "")))
        return rows
    finally:
        conn.close()
