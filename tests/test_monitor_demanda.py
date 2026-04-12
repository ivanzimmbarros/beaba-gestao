"""E17.2 — monitor_demanda.py smoke (exit 0 na raiz do repo)."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_monitor_demanda_runs_zero():
    r = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "monitor_demanda.py")],
        cwd=str(REPO),
        env={**os.environ, "BEABA_REPO_ROOT": str(REPO), "PYTHONUTF8": "1"},
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    assert r.returncode == 0, r.stderr
    assert "Live Status" in r.stdout
    assert re.search(r"Vers.o:\s*E\d", r.stdout) or "E17.1" in r.stdout or "E17.2" in r.stdout
