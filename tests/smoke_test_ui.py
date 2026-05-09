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
(`page_colaboradores.py` + `colaborador.py`). **Disponibilidade:** `test_smoke_colaboradores_disponibilidade_sector`
confirma expanders 3.1–3.3 e filtros do calendário mestre. **E24 Repasse global:** `test_smoke_colaboradores_relatorio_repasse_setor_widgets`
confirma filtros de período, dimensão, multiselect e CTA «Gerar relatório de repasses» na rota Colaboradores (admin).

**Autenticação / MFA:** `test_smoke_auth_login_screen_boots` — ecrã de login Sereno (sem sessão autenticada; não envia SMTP).

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
        "page_auth",
        "page_catalogo",
        "page_clientes_agendamentos",
        "page_colaboradores",
        "page_dashboards",
        "page_financeiro",
        "page_governanca",
        "page_home",
        "page_usuarios",
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
    "usuarios",
    "governanca",
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


def _prep_sessao_perfil_usuario_smoke(at: AppTest, route: str) -> None:
    """Sessão autenticada com perfil restrito ``usuario`` (RBAC páginas internas)."""
    at.session_state["page"] = route
    at.session_state["authenticated"] = True
    at.session_state["auth_perfil"] = "usuario"
    at.session_state["auth_user_id"] = 2
    at.session_state["auth_user_email"] = "usuario.smoke@bea.pt"
    at.session_state["must_change"] = False
    at.session_state["auth_user_nome"] = "Smoke Usuario"


def _prep_sessao_autenticada_smoke(at: AppTest, route: str) -> None:
    """Ecrã inicial de login + MFA obriga identidade fictícia nos smokes."""
    at.session_state["page"] = route
    at.session_state["authenticated"] = True
    at.session_state["auth_perfil"] = "admin"
    at.session_state["auth_user_id"] = 1
    at.session_state["auth_user_email"] = "ivanzimmbarros@gmail.com"
    at.session_state["must_change"] = False
    at.session_state["auth_user_nome"] = "Smoke"


def _run_app_smoke(route: str, *, timeout: int) -> None:
    assert _APP_PY.is_file(), f"Em falta: {_APP_PY}"
    at = AppTest.from_file(str(_APP_PY), default_timeout=timeout)
    _prep_sessao_autenticada_smoke(at, route)
    at.run()
    _assert_app_tree_clean(at, context=f"Rota «{route}»")


@pytest.mark.parametrize("route", SMOKE_APP_ROUTES)
def test_smoke_streamlit_app_route_boots(route: str) -> None:
    """Cada rota do menu faz boot via `src/app.py` (AppTest isolado por invocação)."""
    _run_app_smoke(route, timeout=120)


def test_smoke_usuarios_rota_redirecciona_usuario_rest() -> None:
    """Gestão de utilizadores: perfil ``usuario`` não permanece na rota nem rebenta o bootstrap."""
    assert _APP_PY.is_file(), f"Em falta: {_APP_PY}"
    at = AppTest.from_file(str(_APP_PY), default_timeout=120)
    _prep_sessao_perfil_usuario_smoke(at, "usuarios")
    at.run()
    assert len(at.exception) == 0, "Área principal não deve expor st.exception"
    assert len(at.get("error")) >= 1
    try:
        page_after = str(at.session_state["page"])
    except Exception:
        page_after = ""
    assert page_after == "home"


@pytest.mark.parametrize("legacy", SMOKE_LEGACY_REDIRECT_ROUTES)
def test_smoke_streamlit_app_legacy_redirect_boots(legacy: str) -> None:
    """Rotas legadas redireccionadas não rebentam no primeiro render."""
    _run_app_smoke(legacy, timeout=120)


def test_smoke_auth_login_screen_boots() -> None:
    """Autenticação: boot do ecrã de login (ilha Sereno, formulário) sem `authenticated` nem MFA pendente."""
    assert _APP_PY.is_file(), f"Em falta: {_APP_PY}"
    at = AppTest.from_file(str(_APP_PY), default_timeout=120)
    at.session_state["authenticated"] = False
    # AppTest.session_state não suporta `.pop()` (Streamlit trata como chave).
    at.session_state["aguardando_mfa"] = False
    at.session_state["pending_mfa_user_id"] = None
    at.session_state["pending_mfa_email"] = None
    at.session_state["page"] = "home"
    at.run()
    _assert_app_tree_clean(at, context="Autenticação — ecrã de login")
    btn_labels = [str(getattr(b, "label", "") or "") for b in at.get("button")]
    assert any("Entrar" in l for l in btn_labels), btn_labels
    ti_labels = [str(getattr(ti, "label", "") or "") for ti in at.get("text_input")]
    assert any("E-mail" in t for t in ti_labels), ti_labels
    assert any("Senha" in t for t in ti_labels), ti_labels


def test_smoke_colaboradores_dados_parceria_ficha_widgets() -> None:
    """Colaboradores: «Dados da Parceria» — selects Sim/Não, IBAN, documento complementar (regressão UI)."""
    at = AppTest.from_file(str(_APP_PY), default_timeout=120)
    _prep_sessao_autenticada_smoke(at, "colaboradores")
    at.run()
    _assert_app_tree_clean(at, context="Colaboradores — dados da parceria (ficha)")
    sb_labels = [str(getattr(sb, "label", "") or "") for sb in at.get("selectbox")]
    assert "Atividade Econômica Aberta? *" in sb_labels
    assert "Contrato de Prestação de Serviço assinado? *" in sb_labels
    ti_labels = [str(getattr(ti, "label", "") or "") for ti in at.get("text_input")]
    assert any("Dados Bancários — IBAN *" in t for t in ti_labels), ti_labels
    assert any("Passaporte, Título de Residência ou Cartão Cidadão" in t for t in ti_labels), ti_labels


def test_smoke_colaboradores_disponibilidade_sector() -> None:
    """Colaboradores: setor 3 — expanders de pesquisa, plano e calendário mestre (sem excepção no boot)."""
    at = AppTest.from_file(str(_APP_PY), default_timeout=120)
    _prep_sessao_autenticada_smoke(at, "colaboradores")
    at.run()
    _assert_app_tree_clean(at, context="Colaboradores — disponibilidade (setor 3)")
    exp_titles = [str(getattr(e, "label", "") or "") for e in at.get("expander")]
    assert sum(1 for t in exp_titles if "3.1 Pesquisa de Disponibilidade de Colaboradores" in t) >= 1, exp_titles
    assert sum(1 for t in exp_titles if "3.2 Plano de disponibilidade" in t) >= 1, exp_titles
    assert sum(1 for t in exp_titles if "3.3 Calendário mestre" in t) >= 1, exp_titles


def test_smoke_colaboradores_relatorio_repasse_setor_widgets() -> None:
    """E24 — Sector 4: filtros período/modalidade/multiselect + CTA relatório PDF (boot admin smoke)."""
    at = AppTest.from_file(str(_APP_PY), default_timeout=120)
    _prep_sessao_autenticada_smoke(at, "colaboradores")
    at.run()
    _assert_app_tree_clean(at, context="Colaboradores — relatório global repasse (setor 4)")
    lbl_di = [str(getattr(d, "label", "") or "") for d in at.get("date_input")]
    assert any("Data início (período)" in x for x in lbl_di), lbl_di
    assert any("Data fim (período)" in x for x in lbl_di), lbl_di
    lbl_sb = [str(getattr(sb, "label", "") or "") for sb in at.get("selectbox")]
    assert "Dimensão de filtro exclusiva para o relatório" in lbl_sb
    lbl_ms = [str(getattr(m, "label", "") or "") for m in at.get("multiselect")]
    assert any(x == "Especialidades seleccionadas" for x in lbl_ms), lbl_ms
    btn_lbl = [str(getattr(b, "label", "") or "") for b in at.get("button")]
    assert "Gerar relatório de repasses" in btn_lbl


def test_smoke_financeiro_resultado_operacional_panel() -> None:
    """Financeiro: painel sector 1 — mês/ano, cenário das entradas e rótulo do expander."""
    at = AppTest.from_file(str(_APP_PY), default_timeout=120)
    _prep_sessao_autenticada_smoke(at, "financeiro")
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
    _prep_sessao_autenticada_smoke(at, "financeiro")
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
    if "Nome do Colaborador" in labels:
        assert labels.index("Nome do Colaborador") < i_nat, labels


def test_smoke_financeiro_entradas_sector_widgets() -> None:
    """Financeiro: widgets do sector «5. Entradas» (expander, caixas de totais, filtros)."""
    at = AppTest.from_file(str(_APP_PY), default_timeout=120)
    _prep_sessao_autenticada_smoke(at, "financeiro")
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


def test_smoke_governanca_admin_sector_widgets() -> None:
    """Governança (admin): título, subtítulos sector log/estado, botão cópia manual (sem executar scripts)."""
    at = AppTest.from_file(str(_APP_PY), default_timeout=120)
    _prep_sessao_autenticada_smoke(at, "governanca")
    at.run()
    _assert_app_tree_clean(at, context="Governança — sector operacional")
    btn_labels = [str(getattr(b, "label", "") or "") for b in at.get("button")]
    assert any("Executar Backup Agora" in l for l in btn_labels), btn_labels
    # Markdown inclui grandes blocos `<style>` de `inject_constituicao_gov_page` — filtrar.
    chunks: list[str] = []
    for m in at.get("markdown"):
        v = getattr(m, "value", None)
        txt = v if isinstance(v, str) else str(getattr(m, "body", "") or "")
        if "<style>" in txt and "bea-cv-gov-slot" in txt:
            continue
        chunks.append(txt)
    # st.title → AppTest `"title"`; st.subheader → `"subheader"` (não `"heading"`).
    for t in at.get("title"):
        chunks.append(str(getattr(t, "value", "") or ""))
    for sh in at.get("subheader"):
        chunks.append(str(getattr(sh, "value", "") or ""))
    for sb in at.get("selectbox"):
        lb = getattr(sb, "label", "") or getattr(sb, "_label", "") or ""
        lb = str(lb).strip()
        if lb:
            chunks.append(lb)
    digest = "\n".join(chunks)
    assert "Governança" in digest
    assert "Auditoria de utilizadores e acessos" in digest
    assert "Filtrar registos por módulo" in digest
    assert "backup_hourly.log" in digest or "Ainda não existe log legível" in digest
    assert "Estados de recuperação" in digest


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
