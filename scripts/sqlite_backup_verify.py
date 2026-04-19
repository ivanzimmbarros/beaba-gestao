"""
Verificações comuns para ficheiros SQLite após cópia/backup (E17 / E19.1).

- Cabeçalho mágico «SQLite format 3» (16 bytes) — detecta truncagem/corrupção grosseira.
- PRAGMA quick_check (rápido) ou integrity_check (completo, mais lento).

Governação 2026-04-12: remoção física do legado UI Clientes/Agendamentos em ficheiros separados;
perímetro de dados da app inalterado para este módulo.

Cockpit Home: agendamentos/créditos no mesmo SQLite — verify destino cobre métricas exibidas
em `page_home` após qualquer restore.

CAG: listagens e resumos vêm do mesmo `.db`; integridade do ficheiro cobre também a página
consolidada (dados); camada visual Sereno é código em git, não artefacto de backup.
Setor 4 (listagem dentro do expander «Agendamentos»; formulário com `tipo_atendimento` / `sala_virtual_disponibilizada` em `agendamentos`): contrato `tests/cag_setor4_ui_contract.py`.
Painel de Vendas Sereno: `tests/vnd_ui_contract.py` (contrato `assert_vnd_editar_cliente_number_input_sem_value_duplicado_session`), `tests/test_vnd_visual_sereno.py`.
Colaboradores Sereno: `tests/col_ui_contract.py`, `tests/test_col_visual_sereno.py`; ficha **Dados da Parceria** coberta por
`tests/smoke_test_ui.py::test_smoke_colaboradores_dados_parceria_ficha_widgets`.
Catálogo Sereno: `tests/cat_ui_contract.py`, `tests/test_cat_visual_sereno.py`.
Início / Cockpit Sereno: `tests/home_ui_contract.py`, `tests/test_home_visual_sereno.py`.
Setor 5 Entradas (2026-04): `tests/fin_ui_contract.py` (`assert_fin_entradas_sector_na_pagina`), `tests/test_financeiro_entradas_convertidas.py`.
Smoke UI: `tests/smoke_test_ui.py` + `pytest.ini`. Catálogo: wizard tipo→confirmação em `page_catalogo.py`.
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
