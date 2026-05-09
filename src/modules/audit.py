"""Registo central na tabela ``auditoria_sistema`` (Épico 23)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from src.database.connection import get_connection


def _criado_em_exibicao_pt(raw: object) -> str:
    """Formata texto de ``criado_em`` para DD/MM/YYYY HH:MM (lista já ordenada no SQL)."""
    s = (str(raw).strip()) if raw is not None else ""
    if not s:
        return "—"
    norm = s.replace("T", " ").replace("Z", "")
    stem = norm[:19]
    try:
        return datetime.strptime(stem, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return s


def _str_cell(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    return str(v)


def listar_auditoria(limite: int = 100, modulo_filtro: str | None = None) -> list[dict[str, Any]]:
    """Consulta ``auditoria_sistema``, mais recentes primeiro.

    ``dados_antigos`` e ``dados_novos`` são sempre devolvidos como texto (para ``st.dataframe``).
    """
    conn = get_connection()
    if not conn:
        return []
    lim = max(1, min(int(limite), 5000))
    mf_raw = (modulo_filtro or "").strip() or None
    try:
        table_names = {
            r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        if "auditoria_sistema" not in table_names:
            return []
        cur = conn.cursor()
        base = """
            SELECT id, ator_email, acao, modulo, registro_id, dados_antigos, dados_novos, criado_em
            FROM auditoria_sistema
        """
        if mf_raw:
            cur.execute(
                base + " WHERE modulo = ? ORDER BY criado_em DESC LIMIT ?",
                (mf_raw, lim),
            )
        else:
            cur.execute(base + " ORDER BY criado_em DESC LIMIT ?", (lim,))
        out: list[dict[str, Any]] = []
        for row in cur.fetchall():
            rid, ator, acao, modulo, reg_id, dan, dnov, cem = row
            out.append(
                {
                    "id": int(rid),
                    "criado_em": _str_cell(cem),
                    "criado_em_exibicao_pt": _criado_em_exibicao_pt(cem),
                    "ator_email": _str_cell(ator),
                    "acao": _str_cell(acao),
                    "modulo": _str_cell(modulo),
                    "registro_id": _str_cell(reg_id),
                    "dados_antigos": _str_cell(dan),
                    "dados_novos": _str_cell(dnov),
                }
            )
        return out
    except Exception:
        return []
    finally:
        conn.close()


def _dump_json_maybe(data: dict[str, Any] | None) -> str | None:
    if data is None:
        return None
    try:
        return json.dumps(data, ensure_ascii=False)
    except (TypeError, ValueError):
        try:
            return json.dumps({"_repr": repr(data)}, ensure_ascii=False)
        except Exception:
            return None


def log_audit(
    ator_email: str,
    acao: str,
    modulo: str,
    registro_id: str | None = None,
    dados_antigos: dict[str, Any] | None = None,
    dados_novos: dict[str, Any] | None = None,
) -> bool:
    """Insere um evento de auditoria. Falhas silenciosas devolvem ``False``."""
    conn = get_connection()
    if not conn:
        return False
    try:
        tabs = {
            r[0]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        if "auditoria_sistema" not in tabs:
            return False
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO auditoria_sistema (
                ator_email, acao, modulo, registro_id, dados_antigos, dados_novos
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                ator_email or None,
                (acao or "").strip(),
                (modulo or "").strip(),
                registro_id,
                _dump_json_maybe(dados_antigos),
                _dump_json_maybe(dados_novos),
            ),
        )
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()
