"""Smoke: view_governance.py lê status_demanda.json e termina 0."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_view_governance_exit_zero():
    r = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "view_governance.py"), "--no-color"],
        cwd=str(REPO),
        env={**os.environ, "BEABA_REPO_ROOT": str(REPO)},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert r.returncode == 0, r.stderr
    assert "Painel de governança" in r.stdout
    assert "backup-and-restore" in r.stdout
    assert "Progresso da sprint" in r.stdout
