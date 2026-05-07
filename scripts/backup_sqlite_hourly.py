"""
E17 / E19.1 — Hot-backup horário SQLite: Backup API (cópia integral do ficheiro, todas as
tabelas incluindo E18 ledger/repasse e E19 `dw_*`), verificação de integridade no destino,
rotação.

Variáveis de ambiente (opcionais):
  BEABA_REPO_ROOT      — raiz do repositório (defeito: pai de scripts/)
  BEABA_BACKUP_KEEP    — máximo de ficheiros em backups/hourly (defeito: 168)
  BEABA_BACKUP_CLOUD_QUEUE — "0" / "false" desliga cópia para backups/cloud_queue/
  BEABA_BACKUP_INTEGRITY_FULL — "1" / "true" para PRAGMA integrity_check no destino (mais lento)

Arquitectura UI (2026-04-12): removidos `src/ui/page_clientes.py` e `page_agendamentos.py`;
a área operacional única é `page_clientes_agendamentos.py` (registo de governação / PAINEL).

Cockpit Home (2026-04-12+): métricas e agenda leem apenas SQLite; cópia integral do `.db`
restaura também os dados exibidos em `page_home.py` (donuts, Panorama, Agenda). CSS/HTML
do cockpit versionados em git — não há ficheiros extra no backup além do já coberto D1/D4.

Catálogo — `especialidades` + `servicos.especialidade_id` (Natureza→Especialidade→Serviço) em D1 via cópia integral do `.db`.

CAG Clientes+Agendamentos (2026-04-12+): Horizonte Sereno, Ilha Mãe branca única e cards métricas
do cliente em `constituicao_visual_shell.py` + `page_clientes_agendamentos.py`; regressão em
`tests/test_cag_visual_sereno.py`, `tests/test_vnd_visual_sereno.py`, `tests/test_col_visual_sereno.py`,
`tests/test_cat_visual_sereno.py`, `tests/test_home_visual_sereno.py`,
`tests/vnd_ui_contract.py` (form editar cliente: number_input sem value= + session_state duplicado), `tests/col_ui_contract.py`, `tests/cat_ui_contract.py`,
`tests/home_ui_contract.py`,
`tests/cag_setor4_ui_contract.py` (Setor 4: lista no expander «Agendamentos»; Dados do Agendamento: tipo presencial/virtual + sala virtual) e fatia E20 em
`e2e_stress_test.py` — tudo em git, não no `.db`.

Financeiro (2026-04+): `page_financeiro.py` (sector **1. Resultado Operacional Consolidado** com
`financeiro_resultado_operacional.py` + gastos + sector **3. Repasses** com cadeia Natureza do Serviço → Especialidades
→ Nome do Serviço, 6 colunas + `financeiro_repasses_colaboradores.py` metadados `listar_servicos_metadados_para_filtro_repasse`;
filtro «Nome do Colaborador» restrito a habilitações via `listar_colaboradores_mapa_equipa` conforme serviços do contexto);
dados em cópia integral incluem `financeiro_*`, `repasse_linhas`, `agendamentos`, `especialidades`, `servicos`; regressão em
`tests/test_fin_visual_sereno.py`, `tests/fin_ui_contract.py` (`assert_fin_resultado_operacional_sector_na_pagina`,
`assert_fin_repasses_sector_na_pagina`, `assert_fin_repasses_filtros_cadeia_e_layout_na_pagina`),
`tests/test_financeiro_resultado_operacional.py`, `tests/test_financeiro_repasses_colaboradores.py`,
`e2e_stress_test.py::test_e2e_fin_visual_shell_contract`.
Smoke UI (camada 3): `tests/smoke_test_ui.py` + `pytest.ini` — `AppTest` por rota em `src/app.py`,
`test_smoke_financeiro_repasses_multiselect_chain`, `test_smoke_financeiro_resultado_operacional_panel` e `test_smoke_monitor_governanca` em
`monitor_governanca.py` (raiz). Catálogo: wizard «tipo → confirmação → cadastro» (`_render_cat_expander_cadastro` em `page_catalogo.py`).

Setor 5 Entradas (2026-04): `page_financeiro.py` (expander «Gestão de valores convertidos (vendas)»); 
gestão de faturas (`atualizar_fatura_venda` em `financeiro_entradas_convertidas.py`); 
contrato em `tests/fin_ui_contract.py` (`assert_fin_entradas_sector_na_pagina`) + 
`tests/test_financeiro_entradas_convertidas.py` + `tests/smoke_test_ui.py` (`test_smoke_financeiro_entradas_sector_widgets`).

Colaboradores — **Dados da Parceria** (2026-04): colunas extra em `colaboradores` (documento complementar, actividade
económica, contrato+data, IBAN) em **D1** via cópia integral do `.db`; domínio `src/modules/colaborador.py`; UI
`page_colaboradores.py`; regressão `tests/test_colaborador.py`, `tests/col_ui_contract.py` (`assert_col_dados_parceria_na_ficha`),
`tests/smoke_test_ui.py` (`test_smoke_colaboradores_dados_parceria_ficha_widgets`).

Colaboradores — **Disponibilidade** (2026-04+): tabelas `colaborador_disponibilidade_plano` e
`colaborador_disponibilidade_regra` (índices por colaborador/validade/regra) em **D1** integral;
`src/modules/colaborador_disponibilidade.py`, `src/ui/colaboradores_disponibilidade_ui.py`; testes
`tests/test_colaborador_disponibilidade.py`, `assert_col_disponibilidade_setor_na_pagina`, smoke
`test_smoke_colaboradores_disponibilidade_sector`; `scripts/seed_validacao_massiva.py` apaga/repõe estas tabelas no wipe.

Governança prod + Cloud DR (2026-05): página `src/ui/page_governanca.py` (Sereno `bea-cv-gov-slot` + `inject_constituicao_gov_page`),
fluxo `backup_sync_cloud.py`, orquestrador `scheduler.py`, drill `restore_test_drill.py`, verificação final `sqlite_backup_verify.py` (CLI);
regressão `tests/gov_ui_contract.py`, `tests/test_backup_drill_contract.py`,
`tests/smoke_test_ui.py::test_smoke_governanca_admin_sector_widgets`; `.github/workflows/deploy.yml` (job `backup-health-main`).
"""

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.sqlite_backup_verify import verify_backup_destination  # noqa: E402

DEFAULT_KEEP = 168

_logger = logging.getLogger("beaba.backup_hourly")


def repo_root() -> Path:
    override = os.environ.get("BEABA_REPO_ROOT")
    if override:
        return Path(override).resolve()
    return Path(__file__).resolve().parents[1]


def _configure_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "backup_hourly.log"
    fmt = logging.Formatter("%(asctime)sZ %(levelname)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.INFO)
    root.addHandler(fh)
    root.addHandler(sh)


def _rotate_hourly(hourly: Path, keep: int) -> None:
    files = sorted(hourly.glob("beaba_gestao_*.db"), key=lambda p: p.name)
    while len(files) > keep:
        oldest = files.pop(0)
        try:
            oldest.unlink()
            _logger.info("Rotação: removido %s", oldest.name)
        except OSError as exc:
            _logger.warning("Rotação: não removido %s: %s", oldest, exc)


def run_backup(
    root: Path | None = None,
    keep: int | None = None,
    *,
    copy_to_cloud_queue: bool | None = None,
) -> int:
    root = root or repo_root()
    env_keep = os.environ.get("BEABA_BACKUP_KEEP")
    keep = int(env_keep) if env_keep is not None else (keep if keep is not None else DEFAULT_KEEP)

    if copy_to_cloud_queue is None:
        flag = os.environ.get("BEABA_BACKUP_CLOUD_QUEUE", "1").lower()
        copy_to_cloud_queue = flag not in ("0", "false", "no")

    data_db = root / "data" / "beaba_gestao.db"
    hourly = root / "backups" / "hourly"
    log_dir = root / "backups" / "logs"
    cloud_queue = root / "backups" / "cloud_queue"
    hourly.mkdir(parents=True, exist_ok=True)
    _configure_logging(log_dir)

    if not data_db.is_file():
        _logger.error("Fonte inexistente: %s", data_db)
        return 1

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    dest = hourly / f"beaba_gestao_{ts}.db"

    try:
        src_uri = f"file:{data_db.resolve().as_posix()}?mode=ro"
        source = sqlite3.connect(src_uri, uri=True, timeout=60.0)
    except sqlite3.Error as exc:
        _logger.error("Abrir origem RO falhou: %s", exc)
        return 1

    try:
        dest_conn = sqlite3.connect(dest)
        try:
            source.backup(dest_conn)
        finally:
            dest_conn.close()
    except sqlite3.Error as exc:
        _logger.error("Backup API falhou: %s", exc)
        dest.unlink(missing_ok=True)
        return 1
    finally:
        source.close()

    ok_v, msg_v = verify_backup_destination(dest)
    if not ok_v:
        _logger.error("Verificação pós-backup falhou: %s", msg_v)
        dest.unlink(missing_ok=True)
        return 1

    _logger.info("Backup criado e verificado (header + pragma): %s", dest.name)
    _rotate_hourly(hourly, keep)

    if copy_to_cloud_queue:
        cloud_queue.mkdir(parents=True, exist_ok=True)
        try:
            cq_dest = cloud_queue / dest.name
            shutil.copy2(dest, cq_dest)
            ok_cq, msg_cq = verify_backup_destination(cq_dest)
            if not ok_cq:
                _logger.error("cloud_queue: cópia corrompida ou inválida — removida: %s", msg_cq)
                cq_dest.unlink(missing_ok=True)
            else:
                _logger.info("Cópia para cloud_queue verificada: %s", cq_dest.name)
        except OSError as exc:
            _logger.warning("cloud_queue: cópia falhou: %s", exc)

    return 0


def main() -> int:
    return run_backup()


if __name__ == "__main__":
    sys.exit(main())
