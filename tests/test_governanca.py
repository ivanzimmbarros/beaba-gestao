"""Smoke: artefactos de governança e leitura de status."""

import json
from pathlib import Path


def test_status_demanda_json_valido():
    root = Path(__file__).resolve().parents[1]
    p = root / "docs" / "governanca" / "status_demanda.json"
    assert p.is_file()
    data = json.loads(p.read_text(encoding="utf-8"))
    assert "fase_actual" in data
    assert "pontos_controlo_concluidos" in data
    # Campos opcionais E12 — quando presentes, forma mínima
    if "fases_resumo" in data:
        fr = data["fases_resumo"]
        assert isinstance(fr, list)
        for item in fr:
            assert isinstance(item, dict)
            assert "id" in item
            assert "estado" in item
    if "diario_bordo_resumo" in data:
        assert isinstance(data["diario_bordo_resumo"], list)
    # E14 — telemetria (campos presentes no canónico)
    assert "live_status" in data
    assert isinstance(data["live_status"], str)
    assert "etapas_pendentes" in data
    assert isinstance(data["etapas_pendentes"], list)
    for step in data["etapas_pendentes"]:
        assert isinstance(step, str)
    assert "live_actualizado_iso" in data
    assert data["live_actualizado_iso"] is None or isinstance(data["live_actualizado_iso"], str)


def test_fluxo_sucesso_doc_existe():
    root = Path(__file__).resolve().parents[1]
    p = root / "docs" / "governanca" / "FLUXO_SUCESSO_E_FALHA.md"
    assert p.is_file()
    text = p.read_text(encoding="utf-8")
    assert "PC13" in text
    assert "PC12.5" in text
    assert "Portão Fortaleza" in text
    assert "Fluxo FALHA" in text
    assert "@Files" in text
    assert "EQUIPE" in text


def test_caderno_testes_master_existe():
    root = Path(__file__).resolve().parents[1]
    p = root / "docs" / "CADERNO_TESTES_MASTER.md"
    assert p.is_file()


def test_pytest_ini_declares_smoke_ui_module():
    """Camada 3: `smoke_test_ui.py` não segue o padrão `test_*.py`; `pytest.ini` garante descoberta."""
    root = Path(__file__).resolve().parents[1]
    ini = root / "pytest.ini"
    smoke = root / "tests" / "smoke_test_ui.py"
    assert ini.is_file(), "pytest.ini em falta — necessário para colectar tests/smoke_test_ui.py"
    assert smoke.is_file()
    text = ini.read_text(encoding="utf-8")
    assert "smoke_test_ui.py" in text


def test_monitor_governanca_script_existe_e_compila():
    root = Path(__file__).resolve().parents[1]
    p = root / "monitor_governanca.py"
    assert p.is_file()
    compile(p.read_text(encoding="utf-8"), str(p), "exec")


def test_e17_restore_certificate_existe():
    """E17 — certificado de restore versionado (emitido por scripts/generate_e17_restore_certificate.py)."""
    root = Path(__file__).resolve().parents[1]
    p = root / "tests" / "E17_RESTORE_CERTIFICATE.txt"
    assert p.is_file()
    text = p.read_text(encoding="utf-8")
    assert "E17 — CERTIFICADO" in text
    assert "exit_code=0" in text
    assert "CONCLUSÃO:" in text


def test_backup_dr_history_json_existe_e_schema_minimo():
    """E17.1 — telemetria canónica (schema v1; runs lista, entradas com type + groups)."""
    root = Path(__file__).resolve().parents[1]
    p = root / "docs" / "governanca" / "telemetry" / "backup_dr_history.json"
    if not p.is_file():
        p = root / "docs" / "governanca" / "telemetry" / "backup_dr_history.json.example"
    assert p.is_file(), "Falta backup_dr_history.json (local) ou .json.example (repo público)"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data.get("schema_version") == 1
    assert isinstance(data.get("runs"), list)
    for run in data["runs"]:
        assert isinstance(run, dict)
        assert "type" in run
        assert isinstance(run.get("groups"), dict)
