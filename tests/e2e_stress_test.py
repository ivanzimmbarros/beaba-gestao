"""
E20 — Fortaleza Operacional: stress & E2E (Jornada do Herói + fronteiras + concorrência).

- Jornada (N iterações): cadastro → pré-venda → venda integral → associação → verificações
  → **slice CAG** (`obter_cliente_completo`, resumo setor 2, `listar_agendamentos`,
  helpers `page_clientes_agendamentos`: identificação, HTML naturezas, ordenação,
  **contrato Setor 4** — listagem dentro do expander «Agendamentos», ver `cag_setor4_ui_contract`).
- **slice Vendas (UI Sereno):** Ilha Mãe + slot — `tests/vnd_ui_contract.py`,
  `tests/test_vnd_visual_sereno.py`.
- Execução completa (1000 iterações): `python tests/e2e_stress_test.py`
- Pytest (mais leve): `pytest tests/e2e_stress_test.py` (defeito N=35; sobrescrever com
  `E2E_STRESS_HERO_ITERATIONS=1000`).

Relatório: `tests/last_stress_report.txt` (sempre reescrito após cada corrida do módulo
ou do `main`).

2026-04-12 — Decomissionamento UI: módulos legados `page_clientes` / `page_agendamentos`
removidos; slice CAG permanece em `page_clientes_agendamentos`.

Requer `BEABA_SQLITE_PATH` apontando para um ficheiro isolado (o teste pytest define;
o `__main__` usa diretório temporário).
"""

from __future__ import annotations

import os
import sqlite3
import sys
import threading
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

REPORT_PATH = Path(__file__).resolve().parent / "last_stress_report.txt"


def _write_report(
    lines: list[str],
    *,
    hero_failures: list[str],
    boundary_failures: list[str],
    concurrency_failures: list[str],
    integrity_ok: bool,
    dw_ok: bool | None,
) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8") as fh:
        fh.write("=== BeaBa — relatório stress E20 (last_stress_report.txt) ===\n")
        fh.write(f"integrity_check final: {'OK' if integrity_ok else 'FALHOU'}\n")
        fh.write(f"DW pós-ETL: {dw_ok if dw_ok is not None else 'N/A'}\n")
        fh.write(f"Falhas jornada: {len(hero_failures)}\n")
        fh.write(f"Falhas fronteira: {len(boundary_failures)}\n")
        fh.write(f"Falhas concorrência: {len(concurrency_failures)}\n\n")
        for block, name in (
            (hero_failures, "— Jornada do herói —"),
            (boundary_failures, "— Testes de fronteira —"),
            (concurrency_failures, "— Concorrência —"),
            (lines, "— Notas —"),
        ):
            if block:
                fh.write(f"{name}\n")
                for x in block:
                    fh.write(f"  {x}\n")
                fh.write("\n")
        if not any([hero_failures, boundary_failures, concurrency_failures]):
            fh.write("Nenhuma falha registada nesta execução.\n")


def _seed_stress_prereqs() -> tuple[int, int]:
    """Preço de sessão + um colaborador. Devolve (servico_id, colaborador_id)."""
    from src.database.connection import get_connection

    conn = get_connection()
    if not conn:
        raise RuntimeError("get_connection() falhou")
    try:
        cur = conn.cursor()
        cur.execute("SELECT MIN(id) FROM servicos WHERE natureza = 'Sessão'")
        row = cur.fetchone()
        if not row or row[0] is None:
            raise RuntimeError("Sem serviço Sessão")
        sid = int(row[0])
        cur.execute(
            "UPDATE servicos SET sessao_valor_centavos = 5000 WHERE id = ?", (sid,)
        )
        cur.execute("SELECT COUNT(*) FROM colaboradores")
        if int(cur.fetchone()[0]) == 0:
            cur.execute(
                """
                INSERT INTO colaboradores (
                    nome, sexo, data_nascimento, email, whatsapp,
                    endereco_rua, endereco_numero, codigo_postal, concelho, freguesia
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "Colab Stress E20",
                    "Feminino",
                    "1990-05-01",
                    "colab-stress@e20.test",
                    "+351910000000",
                    "Rua Stress",
                    "1",
                    "4000-001",
                    "Porto",
                    "Paranhos",
                ),
            )
            cid = int(cur.lastrowid)
        else:
            cur.execute("SELECT MIN(id) FROM colaboradores")
            cid = int(cur.fetchone()[0])
        conn.commit()
        return sid, cid
    finally:
        conn.close()


def _run_single_hero(iteration: int, servico_id: int, colaborador_id: int) -> str | None:
    """Devolve mensagem de erro ou None se OK."""
    from src.modules.agendamento import (
        associar_agendamento_pre_venda_a_item,
        criar_agendamento_pre_venda,
        obter_primeiro_item_venda_por_servico,
    )
    from src.modules.cliente import cadastrar_cliente
    from src.modules.venda import registrar_venda

    tel = f"+351910{(200000 + iteration) % 1000000:06d}"
    email = f"hero{iteration}@e20-stress.test"
    doc = f"STRESS-{iteration:08d}-ID"

    ok, msg = cadastrar_cliente(
        nome=f"Herói Stress {iteration}",
        numero_contato=tel,
        endereco_rua="Rua E20",
        endereco_numero=str(iteration % 200),
        endereco_complemento="",
        codigo_postal="4000-007",
        concelho="Porto",
        freguesia="Centro",
        distrito="Porto",
        pais="Portugal",
        email=email,
        sexo="Masculino",
        tem_filhos=False,
        filhos=[],
        gravida=None,
        data_parto_prevista=None,
        observacoes="e2e stress",
        contatos_emergencia=[],
        nif=doc,
        documento_identificacao_internacional=True,
        data_nascimento="1992-01-15",
    )
    if not ok:
        return f"cadastro[{iteration}]: {msg}"

    from src.database.connection import get_connection

    conn = get_connection()
    if not conn:
        return f"db[{iteration}]"
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM clientes WHERE whatsapp = ?", (tel,))
        r = cur.fetchone()
        if not r:
            return f"cliente não encontrado [{iteration}]"
        cliente_id = int(r[0])
    finally:
        conn.close()

    d0 = date(2029, 1, 1) + timedelta(days=iteration % 500)
    ds = d0.isoformat()

    ok, msg = criar_agendamento_pre_venda(
        cliente_id,
        servico_id,
        ds,
        "09:00",
        "10:00",
        [colaborador_id],
        observacoes="pre",
        preco_referencia_centavos=5000,
    )
    if not ok:
        return f"pre_venda[{iteration}]: {msg}"

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM agendamentos WHERE cliente_id = ? ORDER BY id DESC LIMIT 1",
            (cliente_id,),
        )
        ag_row = cur.fetchone()
        if not ag_row:
            return f"sem agendamento[{iteration}]"
        ag_id = int(ag_row[0])
    finally:
        conn.close()

    linha = {
        "servico_id": servico_id,
        "quantidade": 1,
        "is_bonus": False,
        "evento_preco": None,
        "desconto_linha_tipo": "none",
        "desconto_linha_valor": None,
        "colaborador_id": colaborador_id,
    }
    ok, msg, vid = registrar_venda(
        cliente_id,
        "integral",
        [linha],
        None,
        None,
        [("dinheiro", 5000)],
        [],
        "venda e2e",
        agendamento_contexto_id=ag_id,
        credito_abatido_centavos=0,
    )
    if not ok or vid is None:
        return f"venda[{iteration}]: {msg}"

    vi = obter_primeiro_item_venda_por_servico(vid, servico_id)
    if vi is None:
        return f"sem item venda[{iteration}]"

    ok, msg = associar_agendamento_pre_venda_a_item(ag_id, vi)
    if not ok:
        return f"associar[{iteration}]: {msg}"

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT modo_origem, venda_id, venda_item_id FROM agendamentos WHERE id = ?",
            (ag_id,),
        )
        chk = cur.fetchone()
        if not chk or str(chk[0]) != "credito_venda":
            return f"modo_origem inválido após assoc[{iteration}]"
        if chk[1] is None or chk[2] is None:
            return f"FK venda não preenchida[{iteration}]"
    finally:
        conn.close()

    err_cag = _run_cag_consolidated_slice(cliente_id, ag_id)
    if err_cag:
        return err_cag

    err_home = _run_home_cockpit_slice()
    if err_home:
        return err_home

    return None


def _run_home_cockpit_slice() -> str | None:
    """E20 — snapshot SQL do cockpit Home + helpers visuais Fase 3 (sem Streamlit)."""
    from src.modules.home_cockpit_metrics import (
        obter_home_cockpit_snapshot,
        obter_home_evolucao_atendimentos,
    )
    from src.ui import page_home as ph
    from src.ui.home_cockpit_ui_helpers import (
        agenda_day_table_html,
        evolucao_atendimentos_html,
        panorama_card_block_html,
    )

    s = obter_home_cockpit_snapshot()
    if s is None:
        return "home_cockpit: snapshot None (DB?)"
    d = s.to_raw_dict()
    if not isinstance(d.get("referencia_data_iso"), str):
        return "home_cockpit: payload inválido"

    evo = obter_home_evolucao_atendimentos()
    if evo is None:
        return "home_cockpit: evolucao None (DB?)"

    ref_d = date.fromisoformat(str(s.referencia_data_iso)[:10])
    h_ag = agenda_day_table_html([], ref_date=ref_d, now=datetime.now())
    if "bea-home-agenda-empty" not in h_ag:
        return "home_cockpit: agenda HTML vazio inválido"

    h_ev = evolucao_atendimentos_html(
        variacao_delta=int(evo.variacao_semanal_delta),
        desempenho_pct_label=evo.desempenho_pct_label(),
        mes_atual=int(evo.mes_concluidos_atual),
        mes_ant=int(evo.mes_concluidos_anterior),
    )
    if "bea-home-evolucao" not in h_ev:
        return "home_cockpit: evolucao HTML"

    h_pan = panorama_card_block_html(
        material_icon="euro_symbol",
        title="T",
        value_display="0",
        testid="bea-home-e2e-pano",
    )
    if "bea-cv-pano-icon-wrap" not in h_pan or "material-symbols-outlined" not in h_pan:
        return "home_cockpit: panorama card HTML"

    if not callable(getattr(ph, "render_page_home", None)):
        return "home_cockpit: render_page_home ausente"
    fig0 = ph._figure_donut_hoje_semana(0, 0)
    if not getattr(fig0, "data", None):
        return "home_cockpit: plotly donut vazio"

    return None


def _run_cag_consolidated_slice(cliente_id: int, ag_id: int) -> str | None:
    """E20 — ciclo de dados da página consolidada Clientes+Agendamentos (sem Streamlit)."""
    from src.modules.agendamento import (
        listar_agendamentos,
        obter_agendamento,
        obter_resumo_agendamentos_cliente_setor2_proposta,
    )
    from src.modules.cliente import obter_cliente_completo
    from src.ui import page_clientes_agendamentos as cag
    from src.ui.constituicao_visual_shell import get_constituicao_cag_page_css

    css_cag = get_constituicao_cag_page_css()
    if "bea-cv-cag-slot" not in css_cag or "bea-cv-cag-metric-card" not in css_cag:
        return "cag: shell CSS Sereno incompleto"
    if ':has(.bea-cv-cag-slot)' not in css_cag:
        return "cag: CSS Ilha Mãe (:has slot) ausente"

    cli = obter_cliente_completo(cliente_id)
    if not cli:
        return "cag: obter_cliente_completo vazio"

    resumo = obter_resumo_agendamentos_cliente_setor2_proposta(cliente_id)
    if not isinstance(resumo, dict):
        return "cag: resumo setor2 inválido"

    rows = listar_agendamentos(cliente_ids=[cliente_id])
    ids = {int(r["id"]) for r in rows}
    if ag_id not in ids:
        return f"cag: agendamento {ag_id} ausente em listar_agendamentos"

    ag = obter_agendamento(ag_id)
    if not ag:
        return "cag: obter_agendamento vazio"

    nome, _doc, _tel, _mail = cag.cag_valores_setor2_identificacao_basica(cli)
    if not nome or str(nome).strip() == "-":
        return "cag: identificação setor2"

    prev = resumo.get("previstos_30d_por_natureza")
    pairs: list[tuple[str, int]] = []
    if isinstance(prev, list):
        for item in prev:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                pairs.append((str(item[0]), int(item[1])))
            elif isinstance(item, dict):
                pairs.append(
                    (str(item.get("natureza", "")), int(item.get("n", item.get("count", 0))))
                )
    _ = cag._html_linhas_natureza(pairs)

    sorted_rows = cag._cag_sort_ag_rows(list(rows), col="Data", asc=True)
    if len(sorted_rows) != len(rows):
        return "cag: _cag_sort_ag_rows alterou cardinalidade"

    h_mc = cag._cag_metric_card_html(
        material_icon="calendar_month",
        title="Total 30d",
        body_html="<p>0</p>",
    )
    if "bea-cv-cag-metric-card" not in h_mc or "material-symbols-outlined" not in h_mc:
        return "cag: card métrica Sereno inválido"

    try:
        from tests.cag_setor4_ui_contract import assert_cag_setor4_lista_dentro_expander_agendamentos

        assert_cag_setor4_lista_dentro_expander_agendamentos()
    except AssertionError as exc:
        return f"cag: setor4 expander/lista — {exc}"

    return None


def _run_boundary_tests(db_path: Path) -> list[str]:
    out: list[str] = []
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        cur = conn.cursor()
        cur.execute("SELECT MIN(id) FROM servicos")
        sid0 = cur.fetchone()
        sid_ins = int(sid0[0]) if sid0 and sid0[0] is not None else 1
        try:
            cur.execute(
                """
                INSERT INTO venda_itens (
                    venda_id, servico_id, ordem, quantidade,
                    preco_unitario_centavos, nome_snapshot, descricao_snapshot,
                    unidade_medida_snapshot, is_bonus,
                    subtotal_bruto_centavos, desconto_linha_centavos, total_linha_centavos
                ) VALUES (999999, ?, 1, 1, 100, 'x', '', 'un', 0, 100, 0, 100)
                """,
                (sid_ins,),
            )
            conn.commit()
            out.append("fronteira: esperava falha FK em venda_itens órfão")
        except sqlite3.IntegrityError:
            conn.rollback()
        cur.execute("SELECT MIN(id) FROM servicos")
        sid_row = cur.fetchone()
        sid = int(sid_row[0]) if sid_row and sid_row[0] is not None else 1
        try:
            cur.execute(
                """
                INSERT INTO agendamentos (
                    venda_id, venda_item_id, cliente_id, servico_id, tipo_origem,
                    data_agendamento, hora_inicio, hora_fim, status,
                    devolver_ao_buffer, modo_origem
                ) VALUES (NULL, NULL, 999999, ?, 'sessao_avulsa',
                    '2030-01-01', '10:00', '11:00', 'AGENDADO', 0, 'pre_venda')
                """,
                (sid,),
            )
            conn.commit()
            out.append("fronteira: esperava falha FK cliente inexistente em agendamentos")
        except sqlite3.IntegrityError:
            conn.rollback()

        from src.modules.cliente import cadastrar_cliente

        ok, msg = cadastrar_cliente(
            nome="Inválido CP",
            numero_contato="+351910333444",
            endereco_rua="Rua",
            endereco_numero="1",
            endereco_complemento="",
            codigo_postal="12",
            concelho="X",
            freguesia="Y",
            distrito="Z",
            pais="Portugal",
            email="badcp@e20.test",
            sexo="Masculino",
            tem_filhos=False,
            filhos=[],
            gravida=None,
            data_parto_prevista=None,
            observacoes="",
            contatos_emergencia=[],
            nif="DOC-CP-ERR",
            documento_identificacao_internacional=True,
            data_nascimento="1990-01-01",
        )
        if ok:
            out.append("fronteira: cadastro com CP inválido deveria falhar")
    finally:
        conn.close()
    return out


def _run_concurrency_tests(db_path: Path) -> list[str]:
    out: list[str] = []
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()
    cur.execute("SELECT MIN(id) FROM clientes")
    cr = cur.fetchone()
    if not cr or cr[0] is None:
        conn.close()
        return ["concorrência: sem cliente para teste"]
    cid = int(cr[0])
    cur.execute("SELECT MIN(id) FROM servicos")
    sid = int(cur.fetchone()[0])
    cur.execute(
        """
        INSERT INTO vendas (
            cliente_id, estado_pagamento, subtotal_bruto_centavos,
            subtotal_apos_descontos_linha_centavos, desconto_global_centavos_aplicado,
            total_final_centavos, observacoes, credito_abatido_centavos
        ) VALUES (?, 'integral', 100, 100, 0, 100, 'conc', 0)
        """,
        (cid,),
    )
    vid = int(cur.lastrowid)
    cur.execute(
        """
        INSERT INTO venda_itens (
            venda_id, servico_id, ordem, quantidade, preco_unitario_centavos,
            nome_snapshot, descricao_snapshot, unidade_medida_snapshot, is_bonus,
            subtotal_bruto_centavos, desconto_linha_centavos, total_linha_centavos
        ) VALUES (?, ?, 1, 1, 100, 'n', '', 'u', 0, 100, 0, 100)
        """,
        (vid, sid),
    )
    conn.commit()
    conn.close()

    barrier = threading.Barrier(2)
    errors: list[str] = []

    def t_delete():
        try:
            c = sqlite3.connect(db_path, timeout=5.0)
            c.execute("PRAGMA foreign_keys = ON")
            barrier.wait()
            c.execute("DELETE FROM vendas WHERE id = ?", (vid,))
            c.commit()
            c.close()
        except Exception as exc:
            errors.append(f"delete thread: {exc}")

    def t_insert_child():
        try:
            c = sqlite3.connect(db_path, timeout=5.0)
            c.execute("PRAGMA foreign_keys = ON")
            barrier.wait()
            time.sleep(0.05)
            try:
                c.execute(
                    """
                    INSERT INTO venda_itens (
                        venda_id, servico_id, ordem, quantidade, preco_unitario_centavos,
                        nome_snapshot, descricao_snapshot, unidade_medida_snapshot, is_bonus,
                        subtotal_bruto_centavos, desconto_linha_centavos, total_linha_centavos
                    ) VALUES (?, ?, 9, 1, 100, 'n2', '', 'u', 0, 100, 0, 100)
                    """,
                    (vid, sid),
                )
                c.commit()
            except sqlite3.IntegrityError:
                c.rollback()
            finally:
                c.close()
        except Exception as exc:
            errors.append(f"insert thread: {exc}")

    th1 = threading.Thread(target=t_delete)
    th2 = threading.Thread(target=t_insert_child)
    th1.start()
    th2.start()
    th1.join(timeout=15)
    th2.join(timeout=15)
    out.extend(errors)
    # O DELETE pode remover a venda e linhas em cascata; o resultado final não é determinístico.
    # O teste valida sobretudo ausência de excepções fora de IntegrityError esperado nas threads.
    return out


def _final_integrity(db_path: Path) -> bool:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("PRAGMA integrity_check").fetchone()
        return bool(row and row[0] == "ok")
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def _run_etl_and_check_dw(db_path: Path) -> tuple[bool | None, str]:
    try:
        from scripts.etl_analytics import run_etl
    except ImportError:
        return None, "ETL não importável"
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        run_etl(conn)
    except Exception as exc:
        return False, str(exc)
    finally:
        conn.close()
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM dw_cliente_kpi")
        n = int(cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM dw_fact_venda")
        v = int(cur.fetchone()[0])
        return (n >= 0 and v >= 0), f"dw kpi={n} vendas_fact={v}"
    except sqlite3.Error as exc:
        return False, str(exc)
    finally:
        conn.close()


def run_stress_pipeline(db_path: Path, hero_iterations: int) -> tuple[list[str], list[str], list[str], bool, bool | None]:
    sid, cid = _seed_stress_prereqs()
    hero_f: list[str] = []
    for i in range(hero_iterations):
        err = _run_single_hero(i, sid, cid)
        if err:
            hero_f.append(err)
            if len(hero_f) >= 50:
                hero_f.append("… truncado após 50 falhas na jornada")
                break
    boundary_f = _run_boundary_tests(db_path)
    conc_f = _run_concurrency_tests(db_path)
    ok_int = _final_integrity(db_path)
    dw_ok, _ = _run_etl_and_check_dw(db_path)
    return hero_f, boundary_f, conc_f, ok_int, dw_ok


@pytest.fixture
def stress_db_path(tmp_path, monkeypatch):
    db = tmp_path / "e2e_stress.db"
    monkeypatch.setenv("BEABA_SQLITE_PATH", str(db))
    from src.database.connection import create_tables

    create_tables()
    _seed_stress_prereqs()
    yield db
    monkeypatch.delenv("BEABA_SQLITE_PATH", raising=False)


def test_e2e_hero_journey(stress_db_path: Path):
    n = int(os.environ.get("E2E_STRESS_HERO_ITERATIONS", "35"))
    hero_f, boundary_f, conc_f, ok_i, dw_ok = run_stress_pipeline(stress_db_path, n)
    notes = [
        f"iterações jornada={n}",
        f"integrity={ok_i}",
        f"dw={dw_ok}",
    ]
    _write_report(
        notes,
        hero_failures=hero_f,
        boundary_failures=boundary_f,
        concurrency_failures=conc_f,
        integrity_ok=ok_i,
        dw_ok=dw_ok,
    )
    assert not hero_f, hero_f[:5]
    assert ok_i
    assert dw_ok is not False


def test_e2e_boundary_quick(stress_db_path: Path):
    b = _run_boundary_tests(stress_db_path)
    assert not b, b


def test_e2e_vnd_visual_shell_contract() -> None:
    """E2E leve: evidência de que o Painel de Vendas segue o mesmo padrão de área única que CAG."""
    from tests.vnd_ui_contract import assert_vnd_area_unica_shell

    assert_vnd_area_unica_shell()


if __name__ == "__main__":
    import tempfile

    _root = Path(__file__).resolve().parents[1]
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

    failures_notes: list[str] = []
    hero_iterations = int(os.environ.get("E2E_STRESS_HERO_ITERATIONS", "1000"))
    with tempfile.TemporaryDirectory(prefix="beaba_e20_") as td:
        db = Path(td) / "stress.db"
        os.environ["BEABA_SQLITE_PATH"] = str(db)
        from src.database.connection import create_tables

        create_tables()
        hero_f, boundary_f, conc_f, ok_i, dw_ok = run_stress_pipeline(db, hero_iterations)
        failures_notes.append(f"hero_iterations={hero_iterations}")
        code = 0
        if hero_f or boundary_f or conc_f or not ok_i or dw_ok is False:
            code = 1
        _write_report(
            failures_notes,
            hero_failures=hero_f,
            boundary_failures=boundary_f,
            concurrency_failures=conc_f,
            integrity_ok=ok_i,
            dw_ok=dw_ok,
        )
        print(REPORT_PATH.read_text(encoding="utf-8")[:2000])
    del os.environ["BEABA_SQLITE_PATH"]
    sys.exit(code)
