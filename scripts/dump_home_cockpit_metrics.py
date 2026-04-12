#!/usr/bin/env python3
"""
Dump JSON das métricas brutas do cockpit Home (Fase 2 — conferência Diretor).

Uso (base local habitual):
  python scripts/dump_home_cockpit_metrics.py

Respeita BEABA_SQLITE_PATH se definido.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from src.modules.home_cockpit_metrics import obter_home_cockpit_snapshot  # noqa: E402


def main() -> int:
    ref_s = sys.argv[1] if len(sys.argv) > 1 else None
    ref = date.fromisoformat(ref_s) if ref_s else None
    snap = obter_home_cockpit_snapshot(ref=ref)
    if snap is None:
        print(json.dumps({"erro": "sem ligação à base (get_connection None)"}, indent=2))
        return 1
    print(json.dumps(snap.to_raw_dict(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
