"""Syntax-only check: app_governance.py compila (evita regressão em CI)."""

from __future__ import annotations

import py_compile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_app_governance_compiles():
    py_compile.compile(str(REPO / "scripts" / "app_governance.py"), doraise=True)
