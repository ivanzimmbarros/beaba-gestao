"""
Orquestra cópias locais para ``backups/hourly/`` e sincronização S3 compatível em sequência.

Uso típico (defeito cada 3600 s):
  python scripts/scheduler.py

Uma execução isolada / cron dentro do hospedeiro:
  python scripts/scheduler.py --once

Intervalo configurável via ``BACKUP_CYCLE_SECONDS`` ou ``--interval-seconds``.

Em Docker/Linux costuma usar-se systemd timer ou Cron em detrimento de loops longos —
este script encadeia os dois comandos já existentes.

Coberturas QA: ``tests/test_backup_drill_contract.py::test_scheduler_once``; encadeamento com ``backup_sync_cloud.py`` e ``backup_sqlite_hourly.py`` (docstrings cruzadas).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

_MSG_AGENDADOR_FALHA = (
    "❌ [FALHA NO AGENDADOR] O ciclo de backup automático foi interrompido ou apresentou erro. "
    "Nenhuma cópia está sendo enviada no momento."
)


def repo_root_from_env() -> str:
    raw = os.environ.get("BEABA_REPO_ROOT") or ""
    if raw.strip():
        return str(Path(raw).resolve())
    return str(Path(__file__).resolve().parents[1])


def _hora_atual_legivel() -> str:
    return datetime.now().strftime("%H:%M")


def _print_agendador_sucesso() -> None:
    print(f"✅ [AGENDADOR] Ciclo de backup concluído com sucesso às {_hora_atual_legivel()}.")


def _print_agendador_falha() -> None:
    print(_MSG_AGENDADOR_FALHA, file=sys.stderr)


def run_backup_cycle(repo: str, py: str) -> int:
    hourly = subprocess.run([py, str(Path(repo) / "scripts" / "backup_sqlite_hourly.py")], cwd=repo)
    sync = subprocess.run([py, str(Path(repo) / "scripts" / "backup_sync_cloud.py")], cwd=repo)
    if hourly.returncode != 0:
        return hourly.returncode
    return sync.returncode


def main() -> int:
    repo = repo_root_from_env()
    py = sys.executable
    ap = argparse.ArgumentParser(description="Agendar backup SQLite + sincronização S3.")
    ap.add_argument("--once", action="store_true", help="Executar um ciclo apenas e sair.")
    ap.add_argument(
        "--interval-seconds",
        type=int,
        default=int(os.environ.get("BACKUP_CYCLE_SECONDS", "3600")),
        help="Espera entre ciclos (defeito: 3600 ou BACKUP_CYCLE_SECONDS).",
    )
    args = ap.parse_args()

    if args.once:
        rc = run_backup_cycle(repo, py)
        if rc != 0:
            _print_agendador_falha()
            return rc
        _print_agendador_sucesso()
        return 0

    interval = max(60, args.interval_seconds)
    while True:
        rc = run_backup_cycle(repo, py)
        if rc != 0:
            _print_agendador_falha()
        else:
            _print_agendador_sucesso()
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
