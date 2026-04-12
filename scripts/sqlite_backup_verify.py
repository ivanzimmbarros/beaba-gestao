"""
Verificações comuns para ficheiros SQLite após cópia/backup (E17 / E19.1).

- Cabeçalho mágico «SQLite format 3» (16 bytes) — detecta truncagem/corrupção grosseira.
- PRAGMA quick_check (rápido) ou integrity_check (completo, mais lento).

Governação 2026-04-12: remoção física do legado UI Clientes/Agendamentos em ficheiros separados;
perímetro de dados da app inalterado para este módulo.

Cockpit Home: agendamentos/créditos no mesmo SQLite — verify destino cobre métricas exibidas
em `page_home` após qualquer restore.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

SQLITE_MAGIC = b"SQLite format 3\x00"
HEADER_READ_LEN = 16


def verify_sqlite_magic_header(path: Path) -> tuple[bool, str]:
    """True se os primeiros 16 bytes correspondem ao header canónico SQLite3."""
    try:
        with path.open("rb") as fh:
            head = fh.read(HEADER_READ_LEN)
    except OSError as exc:
        return False, f"leitura header: {exc}"
    if len(head) < len(SQLITE_MAGIC):
        return False, "ficheiro demasiado curto para header SQLite"
    if head[: len(SQLITE_MAGIC)] != SQLITE_MAGIC:
        return False, "header inválido (não é SQLite 3)"
    return True, "ok"


def verify_sqlite_pragmas(
    path: Path,
    *,
    full_integrity: bool = False,
) -> tuple[bool, str]:
    """
    `full_integrity=False`: PRAGMA quick_check (recomendado pós-backup frequente).
    `full_integrity=True`: PRAGMA integrity_check (mais pesado; BEABA_BACKUP_INTEGRITY_FULL=1).
    """
    pragma = "integrity_check" if full_integrity else "quick_check"
    try:
        conn = sqlite3.connect(path, timeout=30.0)
        try:
            row = conn.execute(f"PRAGMA {pragma}").fetchone()
            result = row[0] if row else ""
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return False, f"{pragma}: {exc}"
    if result != "ok":
        return False, f"{pragma} falhou: {result!r}"
    return True, "ok"


def verify_backup_destination(
    path: Path,
    *,
    full_integrity: bool | None = None,
) -> tuple[bool, str]:
    """
    Sucesso só se header + pragma passarem.
    `full_integrity` None → lê BEABA_BACKUP_INTEGRITY_FULL (1/true/yes).
    """
    if full_integrity is None:
        raw = os.environ.get("BEABA_BACKUP_INTEGRITY_FULL", "").strip().lower()
        full_integrity = raw in ("1", "true", "yes", "on")

    ok_h, msg_h = verify_sqlite_magic_header(path)
    if not ok_h:
        return False, msg_h

    ok_p, msg_p = verify_sqlite_pragmas(path, full_integrity=full_integrity)
    if not ok_p:
        return False, msg_p

    return True, "ok"
