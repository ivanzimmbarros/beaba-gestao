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
