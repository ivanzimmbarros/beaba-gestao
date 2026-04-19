"""Camada 3 — Smoke UI (Streamlit AppTest).

Objectivo: garantir que `src/app.py` faz *boot* completo por rota (`session_state.page`)
sem erros de renderização típicos (ex.: argumentos inválidos em widgets → TypeError),
importações em falha, ou falhas capturadas por `st.exception` / `st.error`.

**Manutenção obrigatória:** ao acrescentar `src/ui/page_*.py` ou nova entrada de navegação
em `src/app.py` / `src/ui/shell_sidebar.py`, actualize `EXPECTED_PAGE_MODULES` e
`SMOKE_APP_ROUTES` neste ficheiro (o teste `test_smoke_ui_page_modules_sync_with_disk` falha
se existir divergência). O **Monitor de Voo** (`monitor_governanca.py` na raiz do repo) tem
smoke dedicado em `test_smoke_monitor_governanca`.

Execução isolada: ``python tests/smoke_test_ui.py`` (delega em pytest neste módulo).
Na CI / pre-push: incluído em ``python -m pytest tests/ -v`` (ficheiro em ``tests/``).

Referência técnica: `streamlit.testing.v1.AppTest` (Streamlit ≥ 1.28; projeto em 1.52+).

Colaboradores — **Dados da Parceria:** `test_smoke_colaboradores_dados_parceria_ficha_widgets` confirma na ficha os
selects obrigatórios (actividade económica / contrato), IBAN e documento complementar na linha do NIF
(`page_colaboradores.py` + `colaborador.py`).

Financeiro — **1. Resultado Operacional:** `test_smoke_financeiro_resultado_operacional_panel` confirma widgets do painel
(mês/ano, cenário das entradas). **3. Repasses:** `test_smoke_financeiro_repasses_multiselect_chain` confirma na árvore
de widgets os multiselects «Natureza do Serviço», «Especialidades» e «Nome do Serviço» na ordem
correcta (regressão da cadeia de filtros em `page_financeiro.py`).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_APP_PY = _REPO_ROOT / "src" / "app.py"
_MONITOR_GOVERNANCA_PY = _REPO_ROOT / "monitor_governanca.py"


# Módulos `src/ui/page_*.py` existentes (sem extensão). Deve coincidir com o disco.
EXPECTED_PAGE_MODULES: frozenset[str] = frozenset(
    {
        "page_catalogo",
        "page_clientes_agendamentos",
        "page_colaboradores",
        "page_dashboards",
        "page_financeiro",
        "page_home",
        "page_vendas",
    }
)

# Rotas `st.session_state.page` suportadas pelo ramo principal de `src.app:main()`
# (alinhado a `shell_sidebar.NAV_ITEMS` + Dashboards + Relatórios; ver também redirecções legadas).
SMOKE_APP_ROUTES: tuple[str, ...] = (
    "home",
    "vendas",
    "clientes_agendamentos",
    "catalogo",
    "colaboradores",
    "financeiro",
    "dashboards",
    "relatorios",
)

# Redirecções que `app.py` normaliza para rotas canónicas (smoke de regressão).
SMOKE_LEGACY_REDIRECT_ROUTES: tuple[str, ...] = (
    "colaboradoras",
    "clientes",
    "agendamentos",
)


def _discovered_page_module_stems() -> set[str]:
    ui = _REPO_ROOT / "src" / "ui"
    return {p.stem for p in ui.glob("page_*.py")}


def _assert_app_tree_clean(at: AppTest, *, context: str) -> None:
    """Falha com mensagem útil se Streamlit expôs exception, error ou trace na árvore."""
    problems: list[str] = []
    if len(at.exception) > 0:
        problems.append(f"Área principal: {len(at.exception)} elemento(s) st.exception")
    if len(at.get("error")) > 0:
        problems.append(f"Área principal: {len(at.get('error'))} st.error")
    sb = at.sidebar
    if sb is not None:
        if len(sb.exception) > 0:
            problems.append(f"Sidebar: {len(sb.exception)} st.exception")
        if len(sb.get("error")) > 0:
            problems.append(f"Sidebar: {len(sb.get('error'))} st.error")
    assert not problems, f"{context}: " + "; ".join(problems)


def _run_app_smoke(route: str, *, timeout: int) -> None:
    assert _APP_PY.is_file(), f"Em falta: {_APP_PY}"
    at = AppTest.from_file(str(_APP_PY), default_timeout=timeout)
    at.session_state["page"] = route
    at.run()
    _assert_app_tree_clean(at, context=f"Rota «{route}»")


@pytest.mark.parametrize("route", SMOKE_APP_ROUTES)
def test_smoke_streamlit_app_route_boots(route: str) -> None:
    """Cada rota do menu faz boot via `src/app.py` (AppTest isolado por invocação)."""
    _run_app_smoke(route, timeout=120)


@pytest.mark.parametrize("legacy", SMOKE_LEGACY_REDIRECT_ROUTES)
def test_smoke_streamlit_app_legacy_redirect_boots(legacy: str) -> None:
    """Rotas legadas redireccionadas não rebentam no primeiro render."""
    _run_app_smoke(legacy, timeout=120)


def test_smoke_colaboradores_dados_parceria_ficha_widgets() -> None:
    """Colaboradores: «Dados da Parceria» — selects Sim/Não, IBAN, documento complementar (regressão UI)."""
    at = AppTest.from_file(str(_APP_PY), default_timeout=120)
    at.session_state["page"] = "colaboradores"
    at.run()
    _assert_app_tree_clean(at, context="Colaboradores — dados da parceria (ficha)")
    sb_labels = [str(getattr(sb, "label", "") or "") for sb in at.get("selectbox")]
    assert "Atividade Econômica Aberta? *" in sb_labels
    assert "Contrato de Prestação de Serviço assinado? *" in sb_labels
    ti_labels = [str(getattr(ti, "label", "") or "") for ti in at.get("text_input")]
    assert any("Dados Bancários — IBAN *" in t for t in ti_labels), ti_labels
    assert any("Passaporte, Título de Residência ou Cartão Cidadão" in t for t in ti_labels), ti_labels


def test_smoke_financeiro_resultado_operacional_panel() -> None:
    """Financeiro: painel sector 1 — mês/ano, cenário das entradas e rótulo do expander."""
    at = AppTest.from_file(str(_APP_PY), default_timeout=120)
    at.session_state["page"] = "financeiro"
    at.run()
    _assert_app_tree_clean(at, context="Financeiro — resultado operacional (painel)")
    labels_sb = [str(getattr(sb, "label", "") or "") for sb in at.get("selectbox")]
    assert "Mês (referência)" in labels_sb
    assert "Ano (referência)" in labels_sb
    labels_radio = [str(getattr(r, "label", "") or "") for r in at.get("radio")]
    assert "Cenário das entradas" in labels_radio
    exp_titles = [str(getattr(e, "label", "") or "") for e in at.get("expander")]
    assert any("Painel do resultado operacional (consolidado)" in t for t in exp_titles), exp_titles


def test_smoke_financeiro_repasses_multiselect_chain() -> None:
    """Financeiro: multiselects do sector «3. Repasses» presentes e ordenados (Nat → Esp → Svc)."""
    at = AppTest.from_file(str(_APP_PY), default_timeout=120)
    at.session_state["page"] = "financeiro"
    at.run()
    _assert_app_tree_clean(at, context="Financeiro — repasses (multiselects)")
    labels = [str(getattr(m, "label", "") or "") for m in at.get("multiselect")]
    assert "Natureza do Serviço" in labels
    assert "Especialidades" in labels
    assert "Nome do Serviço" in labels
    i_nat = labels.index("Natureza do Serviço")
    i_esp = labels.index("Especialidades")
    i_svc = labels.index("Nome do Serviço")
    assert i_nat < i_esp < i_svc, labels


def test_smoke_financeiro_entradas_sector_widgets() -> None:
    """Financeiro: widgets do sector «5. Entradas» (expander, caixas de totais, filtros)."""
    at = AppTest.from_file(str(_APP_PY), default_timeout=120)
    at.session_state["page"] = "financeiro"
    at.run()
    _assert_app_tree_clean(at, context="Financeiro — entradas (widgets)")
    exp_titles = [str(getattr(e, "label", "") or "") for e in at.get("expander")]
    assert any("Gestão de valores convertidos (vendas)" in t for t in exp_titles), exp_titles
    # Verificar filtros da seção Entradas (estão noutro set de multiselects)
    labels_ms = [str(getattr(m, "label", "") or "") for m in at.get("multiselect")]
    assert labels_ms.count("Natureza do Serviço") >= 2 # Um no Repasse, outro nas Entradas
    assert labels_ms.count("Especialidades") >= 2
    assert labels_ms.count("Nome do Serviço") >= 2
    
    # Verificar botões
    btn_labels = [str(getattr(b, "label", "") or "") for b in at.get("button")]
    assert any("Limpar Pesquisa" in l for l in btn_labels)


def test_smoke_ui_page_modules_sync_with_disk() -> None:
    """Garante que toda a superfície `page_*.py` está inventariada (actualizar após novas páginas)."""
    found = _discovered_page_module_stems()
    assert found == EXPECTED_PAGE_MODULES, (
        "Inventário `EXPECTED_PAGE_MODULES` desactualizado.\n"
        f"  No disco: {sorted(found)}\n"
        f"  Esperado: {sorted(EXPECTED_PAGE_MODULES)}\n"
        "Actualize EXPECTED_PAGE_MODULES e, se houver nova página de produto, "
        "`SMOKE_APP_ROUTES` + `src/app.py` + `shell_sidebar.py` conforme aplicável."
    )


def test_smoke_monitor_governanca() -> None:
    """Monitor de Voo (stand-alone): boot completo sem `st.exception` / `st.error` visíveis."""
    assert _MONITOR_GOVERNANCA_PY.is_file(), f"Em falta: {_MONITOR_GOVERNANCA_PY}"
    at = AppTest.from_file(str(_MONITOR_GOVERNANCA_PY), default_timeout=120)
    at.run()
    _assert_app_tree_clean(at, context="Monitor de Voo (`monitor_governanca.py`)")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
