"""
E17.1 — Job único de backup em GitHub Actions: prepara DB em CI, backup, encripta, estado para telemetria.
Escreve gha_backup_state.json e GITHUB_OUTPUT encrypted_path.

Nota 2026-04-12: UI consolidada em `page_clientes_agendamentos.py` (legado `page_clientes` /
`page_agendamentos` removido do repositório). CAG Setor 4: listagem dentro do expander
«Agendamentos» — testes `tests/cag_setor4_ui_contract.py` / `test_clientes_agendamentos_page.py`;
CAG `agendamentos`: colunas `tipo_atendimento`, `sala_virtual_disponibilizada` (restore integral). Painel de Vendas — `tests/vnd_ui_contract.py` (editar cliente: sem value= duplicado em number_input) / `test_vnd_visual_sereno.py`; Colaboradores —
`tests/col_ui_contract.py` / `test_col_visual_sereno.py`; Catálogo —
`tests/cat_ui_contract.py` / `test_cat_visual_sereno.py`; Início / Cockpit —
`tests/home_ui_contract.py` / `test_home_visual_sereno.py`.
Smoke UI: `tests/smoke_test_ui.py` + `pytest.ini`. Catálogo: wizard tipo→confirmação em `page_catalogo.py`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# Imports relativos ao repo
_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.backup_sqlite_hourly import run_backup  # noqa: E402
from scripts.e17_1_ci_prepare_db import prepare as prepare_ci_db  # noqa: E402
from scripts.e17_1_crypto import encrypt_file, parse_backup_key  # noqa: E402
from scripts.e17_1_sqlite_evidence import gather_evidence  # noqa: E402


def _gh_output(name: str, value: str) -> None:
    p = os.environ.get("GITHUB_OUTPUT")
    if not p:
        return
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(f"{name}={value}\n")


def _append_github_step_summary(markdown: str) -> None:
    p = os.environ.get("GITHUB_STEP_SUMMARY")
    if not p:
        return
    try:
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(markdown)
            if not markdown.endswith("\n"):
                fh.write("\n")
    except OSError:
        pass


def _pip_check_rc() -> int:
    return subprocess.run(
        [sys.executable, "-m", "pip", "check"],
        cwd=_REPO,
        capture_output=True,
        text=True,
    ).returncode


def _env_folder_slug() -> str:
    raw = (os.environ.get("ENV_TYPE") or os.environ.get("BEABA_ENV") or "dev").strip().lower()
    if raw in ("production", "prod", "main"):
        return "prod"
    if raw in ("staging", "stg"):
        return "stg"
    if raw in ("develop", "dev", "development", "local"):
        return "dev"
    return "dev"


def main() -> int:
    try:
        repo = Path(os.environ.get("GITHUB_WORKSPACE", _REPO)).resolve()
        load_dotenv(repo / ".env", override=False)
        env_slug = _env_folder_slug()
        git_ref = (os.environ.get("GITHUB_REF_NAME", "develop").strip() or "develop")
        t0 = time.time()
        start = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        steps: dict = {
            "python_version": sys.version.split()[0],
            "pip_check_rc": _pip_check_rc(),
        }

        vital = [
            repo / "scripts",
            repo / "docs" / "governanca" / "telemetry",
            repo / "src" / "database",
        ]
        steps["struct_ok"] = all(p.is_dir() for p in vital)
        steps["requirements_exists"] = (repo / "requirements.txt").is_file()
        steps["env_example_exists"] = (repo / ".env.example").is_file()

        key_raw = os.environ.get("BEABA_BACKUP_KEY", "").strip()
        print(f"DEBUG: Chave BEABA_BACKUP_KEY detectada? {'SIM' if key_raw else 'NÃO (Variável vazia)'}")
        steps["key_configured"] = bool(key_raw)

        prepare_ci_db(repo)

        os.environ.setdefault("BEABA_REPO_ROOT", str(repo))
        os.environ.setdefault("BEABA_BACKUP_CLOUD_QUEUE", "0")

        steps["backup_rc"], latest_db = run_backup(
            repo,
            keep=int(os.environ.get("BEABA_BACKUP_KEEP", "50")),
            copy_to_cloud_queue=False,
        )
        steps["backup_detail"] = ""

        steps["encrypt_rc"] = 1
        steps["encrypted_rel"] = ""
        steps["snapshot_table_counts"] = {}

        if (
            steps["backup_rc"] == 0
            and steps["key_configured"]
            and latest_db is not None
            and latest_db.is_file()
        ):
            latest = latest_db
            try:
                ev_snap = gather_evidence(latest)
                tc = ev_snap.get("table_counts")
                steps["snapshot_table_counts"] = dict(tc) if isinstance(tc, dict) else {}
            except Exception as exc:
                steps["snapshot_table_counts"] = {}
                steps["backup_detail"] = (steps.get("backup_detail") or "") + f"; snapshot: {exc}"
            try:
                key = parse_backup_key()
                out = repo / "backups" / env_slug / "gha_encrypted" / f"{latest.stem}.beaba.enc"
                out.parent.mkdir(parents=True, exist_ok=True)
                encrypt_file(latest, out, key)
                print(
                    f"DEBUG: Encriptação finalizada com sucesso. Path gerado: {str(out).replace('\\\\', '/')}",
                    flush=True,
                )
                steps["encrypt_rc"] = 0
                steps["encrypted_rel"] = str(out.relative_to(repo)).replace("\\", "/")
            except Exception as e:
                import traceback

                tb = traceback.format_exc()
                print("\n" + "=" * 50, flush=True)
                print("ERRO REVELADO NA ENCRIPTAÇÃO:", flush=True)
                print(tb, flush=True)
                print("=" * 50 + "\n", flush=True)
                try:
                    (repo / "ERRO_CRIPTOGRAFIA.txt").write_text(tb, encoding="utf-8")
                except OSError:
                    pass
                meta = "## Erro na encriptação\n\n"
                meta += f"- **Tipo:** `{type(e).__name__}`\n"
                meta += f"- **Mensagem:** {e!r}\n\n"
                meta += "```text\n" + tb + "```\n"
                _append_github_step_summary(meta)
                steps["encrypt_rc"] = 1
        elif steps["backup_rc"] == 0 and not steps["key_configured"]:
            steps["backup_detail"] = "backup ok; chave ausente — sem encriptação"

        print(f"DEBUG: Caminho do arquivo encriptado calculado: {steps['encrypted_rel']}", flush=True)
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
                fh.write(f"encrypted_path={steps['encrypted_rel']}\n")

        finished = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        sha = os.environ.get("GITHUB_SHA", "")
        state = {
            "type": "backup",
            "started_at": start,
            "finished_at": finished,
            "duration_seconds": int(time.time() - t0),
            "git_ref": git_ref,
            "git_sha": sha,
            "steps": steps,
        }
        (repo / "gha_backup_state.json").write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        ok = steps["backup_rc"] == 0 and steps["encrypt_rc"] == 0
        return 0 if ok else 1
    except Exception:
        import traceback

        print(traceback.format_exc(), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
