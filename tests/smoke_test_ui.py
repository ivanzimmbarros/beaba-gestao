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
