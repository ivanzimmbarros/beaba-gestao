"""Resiliência — gatilho cloud pós-escrita, debounce e arranque web sem bloqueio."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from scripts import sync_trigger as st_mod
from scripts.web_startup import (
    ALERT_NETWORK_NO_BOOT_BLOCK,
    _local_db_ready,
    _sqlite_operational_data_missing,
    ensure_web_environment_status,
)
from src.database.connection import create_tables, get_connection
from src.modules.cliente import atualizar_cliente, cadastrar_cliente
from src.modules.usuarios_db import criar_usuario
from src.modules.financeiro_entradas_convertidas import atualizar_fatura_venda
from src.modules.venda import registrar_venda


def test_sync_trigger_on_cliente_update(monkeypatch: pytest.MonkeyPatch) -> None:
    """Alteração de cliente em produção dispara o gatilho de sincronia."""
    calls: list[int] = []

    def _track(*_a, **_k) -> None:
        calls.append(1)

    monkeypatch.setattr(st_mod, "sync_to_cloud_after_change", _track)
    monkeypatch.setenv("BEABA_ENV", "prod")
    monkeypatch.setenv("S3_BUCKET_NAME", "bucket-test")

    suffix = str(int(time.time() * 1000) % 1_000_000)
    tel = f"+351910{suffix.zfill(6)}"
    nif = f"RES-{suffix}"
    ok, msg = cadastrar_cliente(
        nome="Resiliência Gatilho",
        numero_contato=tel,
        endereco_rua="Rua Teste",
        endereco_numero="1",
        endereco_complemento="",
        codigo_postal="4000-099",
        concelho="Porto",
        freguesia="Centro",
        distrito="",
        pais="Portugal",
        email=f"resiliencia.{suffix}@example.com",
        sexo="Masculino",
        tem_filhos=False,
        filhos=[],
        gravida=None,
        data_parto_prevista=None,
        observacoes="",
        contatos_emergencia=[],
        nif=nif,
        documento_identificacao_internacional=True,
        data_nascimento="1990-01-15",
    )
    assert ok, msg
    assert len(calls) == 1

    from src.modules.cliente import buscar_cliente_por_whatsapp

    cid = buscar_cliente_por_whatsapp(tel)
    assert cid is not None

    ok2, msg2 = atualizar_cliente(
        cid,
        nome="Resiliência Gatilho Atualizado",
        numero_contato=tel,
        endereco_rua="Rua Teste",
        endereco_numero="2",
        endereco_complemento="",
        codigo_postal="4000-099",
        concelho="Porto",
        freguesia="Centro",
        distrito="",
        pais="Portugal",
        email=f"resiliencia.{suffix}@example.com",
        sexo="Masculino",
        tem_filhos=False,
        filhos=[],
        gravida=None,
        data_parto_prevista=None,
        observacoes="atualizado",
        contatos_emergencia=[],
        nif=nif,
        documento_identificacao_internacional=True,
        data_nascimento="1990-01-15",
    )
    assert ok2, msg2
    assert len(calls) == 2


def test_sync_trigger_on_venda_update(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Status de fatura e venda directa no PDV disparam o gatilho de backup (mock)."""
    db = tmp_path / "venda_res.db"
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(db))
    create_tables()
    conn = get_connection()
    assert conn is not None
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO clientes (nome, whatsapp) VALUES (?, ?)",
            ("Cli Venda Res", "+351910888001"),
        )
        cid = int(cur.lastrowid)
        cur.execute(
            """
            INSERT INTO vendas (
                cliente_id, estado_pagamento,
                subtotal_bruto_centavos, subtotal_apos_descontos_linha_centavos,
                desconto_global_centavos_aplicado, total_final_centavos,
                observacoes, credito_abatido_centavos, fatura_emitida, fatura_numero
            ) VALUES (?, 'integral', 5000, 5000, 0, 5000, '', 0, 0, '')
            """,
            (cid,),
        )
        vid = int(cur.lastrowid)
        cur.execute(
            "INSERT INTO especialidades (natureza, nome, descritivo) VALUES (?, ?, ?)",
            ("Produto", "EspRes", ""),
        )
        eid = int(cur.lastrowid)
        cur.execute(
            """
            INSERT INTO servicos (
                nome, natureza, especialidade_id, ativo, descritivo, produto_valor_centavos
            ) VALUES (?, 'Produto', ?, 1, 'Desc.', 5000)
            """,
            ("Prod Res", eid),
        )
        sid = int(cur.lastrowid)
        conn.commit()
    finally:
        conn.close()

    calls: list[int] = []

    def _track(*_a, **_k) -> None:
        calls.append(1)

    monkeypatch.setattr(st_mod, "sync_to_cloud_after_change", _track)
    monkeypatch.setenv("BEABA_ENV", "prod")
    monkeypatch.setenv("S3_BUCKET_NAME", "bucket-test")

    conn = get_connection()
    assert conn is not None
    try:
        ok_f, msg_f = atualizar_fatura_venda(conn, vid, 1, "FT-RES-2026/001")
        assert ok_f, msg_f
        conn.commit()
        assert len(calls) == 1

        ok_v, msg_v, vid_new = registrar_venda(
            cid,
            "integral",
            [
                {
                    "servico_id": sid,
                    "quantidade": 1,
                    "is_bonus": False,
                    "evento_preco": None,
                    "desconto_linha_tipo": "none",
                    "desconto_linha_valor": None,
                }
            ],
            None,
            None,
            [("dinheiro", 5000)],
            [],
            "teste resiliência",
            fatura_solicitada=True,
        )
        assert ok_v, msg_v
        assert vid_new is not None
        assert len(calls) == 2
    finally:
        conn.close()


def test_sync_trigger_on_user_management(monkeypatch: pytest.MonkeyPatch) -> None:
    """Criação de utilizador no painel admin dispara gatilho de backup cloud (mock)."""
    calls: list[int] = []

    def _track(*_a, **_k) -> None:
        calls.append(1)

    monkeypatch.setattr(st_mod, "sync_to_cloud_after_change", _track)
    monkeypatch.setenv("BEABA_ENV", "prod")
    monkeypatch.setenv("S3_BUCKET_NAME", "bucket-test")

    suffix = str(int(time.time() * 1000) % 1_000_000)
    mail = f"resiliencia.user.{suffix}@example.com"
    new_id = criar_usuario(
        nome="Utilizador Resiliência",
        email=mail,
        perfil="usuario",
        logged_user_email="admin@test.local",
    )
    assert new_id > 0
    assert len(calls) == 1


def test_sync_trigger_auth_force_bypasses_debounce(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("BEABA_ENV", "prod")
    monkeypatch.setenv("S3_BUCKET_NAME", "bucket-test")
    monkeypatch.setenv("BEABA_REPO_ROOT", str(tmp_path))
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    runs: list[int] = []

    def _fake_cycle(repo: str, py: str) -> int:
        runs.append(1)
        return 0

    monkeypatch.setattr(st_mod, "_run_backup_cycle", _fake_cycle)
    st_mod.notify_auth_data_changed()
    st_mod.notify_auth_data_changed()
    assert len(runs) == 2


def test_sqlite_operational_data_missing_detects_bootstrap_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    db = tmp_path / "bootstrap.db"
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(db))
    create_tables()
    assert _sqlite_operational_data_missing(db) is True
    conn = get_connection()
    assert conn is not None
    try:
        conn.execute(
            "INSERT INTO clientes (nome, whatsapp) VALUES ('A', '+351910000001')"
        )
        conn.commit()
    finally:
        conn.close()
    assert _sqlite_operational_data_missing(db) is False
    assert _local_db_ready(db) is True


def test_sync_trigger_debounce_single_cloud_attempt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Duas alterações rápidas em prod só disparam um ciclo backup+sync."""
    monkeypatch.setenv("BEABA_ENV", "prod")
    monkeypatch.setenv("S3_BUCKET_NAME", "bucket-test")
    monkeypatch.setenv("BEABA_REPO_ROOT", str(tmp_path))
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)

    runs: list[int] = []

    def _fake_cycle(repo: str, py: str) -> int:
        runs.append(1)
        return 0

    monkeypatch.setattr(st_mod, "_run_backup_cycle", _fake_cycle)

    st_mod.sync_to_cloud_after_change()
    st_mod.sync_to_cloud_after_change()
    assert len(runs) == 1

    time.sleep(0.05)
    stamp = tmp_path / "data" / ".last_cloud_sync_trigger"
    old = stamp.stat().st_mtime
    import os

    os.utime(stamp, (old - 130, old - 130))
    st_mod.sync_to_cloud_after_change()
    assert len(runs) == 2


def test_web_startup_network_failure_alerts_without_blocking_boot(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Falha de rede na restauração: alerta ao gestor e arranque continua (base vazia)."""
    monkeypatch.setenv("S3_BUCKET_NAME", "bucket-test")
    monkeypatch.setenv("BEABA_BACKUP_KEY", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
    db = tmp_path / "data" / "beaba_gestao.db"
    if db.is_file():
        db.unlink()

    def _fail_client():
        raise OSError("[Errno 11001] getaddrinfo failed")

    monkeypatch.setattr("scripts.web_startup.boto3_client", _fail_client)

    ready, alert = ensure_web_environment_status(tmp_path)
    assert ready is True
    assert alert == ALERT_NETWORK_NO_BOOT_BLOCK
    assert "Sem ligação à nuvem" in (alert or "")


def test_web_startup_network_alert_surfaces_in_app(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """AppTest: aviso de rede visível e árvore limpa (boot não bloqueado)."""
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("BEABA_REPO_ROOT", str(tmp_path))
    monkeypatch.setenv("S3_BUCKET_NAME", "bucket-test")
    monkeypatch.setenv("BEABA_BACKUP_KEY", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
    db = tmp_path / "data" / "beaba_gestao.db"
    if db.is_file():
        db.unlink()

    monkeypatch.setattr(
        "scripts.web_startup.ensure_web_environment_status",
        lambda repo=None: (True, ALERT_NETWORK_NO_BOOT_BLOCK),
    )

    app_py = Path(__file__).resolve().parents[1] / "src" / "app.py"
    at = AppTest.from_file(str(app_py), default_timeout=120)
    at.session_state["authenticated"] = False
    at.session_state["page"] = "home"
    at.run()

    warnings = [str(getattr(w, "value", "") or "") for w in at.get("warning")]
    assert any("Sem ligação à nuvem" in w for w in warnings), warnings
    assert len(at.exception) == 0
