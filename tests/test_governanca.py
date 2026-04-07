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
    assert "Fluxo FALHA" in text
    assert "@Files" in text
    assert "EQUIPE" in text


def test_caderno_testes_master_existe():
    root = Path(__file__).resolve().parents[1]
    p = root / "docs" / "CADERNO_TESTES_MASTER.md"
    assert p.is_file()


def test_monitor_governanca_script_existe_e_compila():
    root = Path(__file__).resolve().parents[1]
    p = root / "monitor_governanca.py"
    assert p.is_file()
    compile(p.read_text(encoding="utf-8"), str(p), "exec")
