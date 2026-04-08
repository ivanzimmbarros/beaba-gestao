"""E17.1 — Evidências sobre ficheiro SQLite: integrity_check, FK, contagens, SHA-256."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path


def gather_evidence(db_path: Path) -> dict:
    raw = db_path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    conn = sqlite3.connect(db_path)
    try:
        ic_row = conn.execute("PRAGMA integrity_check").fetchone()
        ic = ic_row[0] if ic_row else ""
        fk_bad = conn.execute("PRAGMA foreign_key_check").fetchall()
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            if not str(r[0]).startswith("sqlite_")
        ]
        counts: dict[str, int | None] = {}
        critical = ("clientes", "vendas", "agendamentos", "colaboradores")
        for name in tables:
            if name not in critical:
                continue
            try:
                n = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
                counts[name] = int(n)
            except sqlite3.Error:
                counts[name] = None
    finally:
        conn.close()
    return {
        "integrity_check": ic,
        "foreign_key_violations": len(fk_bad),
        "sha256": sha,
        "table_counts": counts,
        "tables_present": tables,
    }


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: e17_1_sqlite_evidence.py <ficheiro.db>", file=sys.stderr)
        return 1
    p = Path(sys.argv[1])
    if not p.is_file():
        print(json.dumps({"error": f"não encontrado: {p}"}), file=sys.stderr)
        return 1
    ev = gather_evidence(p)
    print(json.dumps(ev, ensure_ascii=False))
    return 0 if ev.get("integrity_check") == "ok" and ev.get("foreign_key_violations", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
