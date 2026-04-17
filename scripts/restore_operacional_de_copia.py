#!/usr/bin/env python3
"""
E19.1 / E17.1 — Restaurar `data/beaba_gestao.db` a partir de uma cópia local verificada.

Cenário: falha do disco local ou corrupção; existe réplica em `backups/hourly/` ou
`backups/cloud_queue/` (espelho para OneDrive/S3/rclone) gerada por `backup_sqlite_hourly.py`.

Não substitui `restore_sqlite.py` (artefacto encriptado GHA). Complementa o percurso
«nuvem → máquina» quando o operador tem apenas ficheiros `.db` claros.

Segurança: exige `--confirmar` ou `BEABA_RESTORE_OPERACIONAL=1`. Pare a app Streamlit
antes de restaurar para evitar bloqueio de ficheiro no Windows.

Arquitectura UI (2026-04-12): páginas legadas Clientes/Agendamentos substituídas por
`page_clientes_agendamentos.py` (registo em governança). Shell Sereno CAG
(`constituicao_visual_shell`) e testes `test_cag_visual_sereno`, `test_vnd_visual_sereno`,
`test_col_visual_sereno`, `test_cat_visual_sereno`, `test_home_visual_sereno` / E20 seguem o repo, não a cópia `.db`.
Após recuperação, validar UI CAG Setor 4 (listagem dentro do expander «Agendamentos») com
`tests/cag_setor4_ui_contract.py` / pytest nos ficheiros de teste CAG; Vendas `tests/vnd_ui_contract.py`;
Colaboradores `tests/col_ui_contract.py`; Catálogo `tests/cat_ui_contract.py`; Início `tests/home_ui_contract.py`;
Financeiro `tests/fin_ui_contract.py`, `tests/test_fin_visual_sereno.py`, `tests/test_financeiro_resultado_operacional.py`,
`tests/test_financeiro_repasses_colaboradores.py` (sector **1. Resultado Operacional** + **3. Repasses**; cópia `.db` inclui `especialidades` / `servicos`).
Smoke UI: `tests/smoke_test_ui.py` (`test_smoke_financeiro_repasses_multiselect_chain`, `test_smoke_financeiro_resultado_operacional_panel`) + `pytest.ini`. Catálogo: wizard tipo→confirmação em `page_catalogo.py`.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.sqlite_backup_verify import verify_backup_destination  # noqa: E402


def _repo_root() -> Path:
    return Path(os.environ.get("BEABA_REPO_ROOT") or _REPO).resolve()


def _latest_in_dir(folder: Path, pattern: str) -> Path | None:
    files = sorted(folder.glob(pattern), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Restaurar beaba_gestao.db a partir de cópia local")
    p.add_argument(
        "--fonte",
        choices=("hourly", "cloud_queue", "ficheiro"),
        default="hourly",
        help="hourly=último em backups/hourly; cloud_queue=último em backups/cloud_queue; ficheiro=--caminho",
    )
    p.add_argument("--caminho", type=Path, help="Ficheiro .db quando --fonte=ficheiro")
    p.add_argument(
        "--confirmar",
        action="store_true",
        help="Obrigatório (ou env BEABA_RESTORE_OPERACIONAL=1) para executar escrita em data/",
    )
    args = p.parse_args(argv)

    if not args.confirmar and os.environ.get("BEABA_RESTORE_OPERACIONAL", "").strip() != "1":
        print(
            "Recusei-se a gravar: passe --confirmar ou defina BEABA_RESTORE_OPERACIONAL=1",
            file=sys.stderr,
        )
        return 2

    root = _repo_root()
    data_dir = root / "data"
    target = data_dir / "beaba_gestao.db"

    if args.fonte == "ficheiro":
        if not args.caminho:
            print("--caminho é obrigatório com --fonte ficheiro", file=sys.stderr)
            return 1
        src = args.caminho.expanduser().resolve()
    elif args.fonte == "cloud_queue":
        src = _latest_in_dir(root / "backups" / "cloud_queue", "beaba_gestao_*.db")
    else:
        src = _latest_in_dir(root / "backups" / "hourly", "beaba_gestao_*.db")

    if not src or not src.is_file():
        print("Nenhuma cópia .db encontrada para a fonte indicada.", file=sys.stderr)
        return 1

    ok, msg = verify_backup_destination(src)
    if not ok:
        print(f"Cópia rejeitada (integridade): {msg}", file=sys.stderr)
        return 1

    data_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    if target.is_file():
        bak = data_dir / f"beaba_gestao.db.pre_restore_{ts}"
        try:
            shutil.copy2(target, bak)
            print(f"Backup do actual gravado em {bak.name}")
        except OSError as exc:
            print(f"Não foi possível preservar o ficheiro actual: {exc}", file=sys.stderr)
            return 1

    try:
        shutil.copy2(src, target)
    except OSError as exc:
        print(f"Falha ao copiar para {target}: {exc}", file=sys.stderr)
        return 1

    ok_t, msg_t = verify_backup_destination(target)
    if not ok_t:
        print(f"Destino após cópia falhou verificação: {msg_t}", file=sys.stderr)
        return 1

    print(f"OK — restaurado a partir de {src}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
