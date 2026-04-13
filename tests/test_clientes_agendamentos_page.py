"""Página consolidada Clientes + Agendamentos — reset, Setor 2 (Proposta), smoke.

Pós-decomissionamento 2026-04-12: `page_clientes.py` e `page_agendamentos.py` foram removidos;
esta suite cobre apenas `page_clientes_agendamentos.py`.

Pesquisa unificada CAG (2026-04): estado de sessão `cag_busca_nome` + widget
`src/ui/widgets/cliente_search.py` (`pesquisa_unificada`); testes de dados em `tests/test_cliente.py`.

Setor 4 (2026-04): listagem dentro do expander «Agendamentos» — ver `tests/cag_setor4_ui_contract.py`.
"""

from pathlib import Path

from tests.cag_setor4_ui_contract import (
    assert_cag_dados_agendamento_tipo_virtual_widgets,
    assert_cag_setor4_lista_dentro_expander_agendamentos,
)

from src.modules.agendamento import obter_resumo_agendamentos_cliente_setor2_proposta

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_cag_setor4_lista_obrigatoriamente_dentro_expander_agendamentos():
    assert_cag_setor4_lista_dentro_expander_agendamentos()


def test_cag_dados_agendamento_tipo_atendimento_virtual_contrato():
    assert_cag_dados_agendamento_tipo_virtual_widgets()


def test_cag_busca_nome_integrado_estado_sessao_na_pagina():
    """Contrato UI: pesquisa unificada lê `cag_busca_nome` (prefixo `cag_busca` + `_nome`)."""
    src = (_REPO_ROOT / "src" / "ui" / "page_clientes_agendamentos.py").read_text(encoding="utf-8")
    assert "cag_busca_nome" in src
    assert "pesquisa_unificada=True" in src


def test_page_clientes_agendamentos_importa_e_expoe_render():
    from src.ui import page_clientes_agendamentos as mod

    assert hasattr(mod, "render_page_clientes_agendamentos")
    assert callable(mod.render_page_clientes_agendamentos)
    assert hasattr(mod, "_render_cag_setor4_gestao_agendamentos")
    assert callable(mod._render_cag_setor4_gestao_agendamentos)


def test_reset_cag_page_state_remove_apenas_prefixo_cag(monkeypatch):
    """Garante que o reset usa prefixo `cag_` e não apaga chaves globais da app."""
    from src.ui import page_clientes_agendamentos as mod

    fake_state = {
        "page": "clientes_agendamentos",
        "cag_form_v": 2,
        "cag_edit_id": 99,
        "cag_busca_nome": "Ana",
        "cag_busca_nif": "123",
        "cli_edit_id": 1,
    }

    class _Sess:
        def __init__(self) -> None:
            object.__setattr__(self, "_d", dict(fake_state))

        def keys(self):
            return list(self._d.keys())

        def __getitem__(self, k):
            return self._d[k]

        def __setitem__(self, k, v):
            self._d[k] = v

        def __getattr__(self, k):
            if k == "_d":
                raise AttributeError(k)
            return self._d[k]

        def __setattr__(self, k, v):
            if k == "_d":
                object.__setattr__(self, k, v)
            else:
                self._d[k] = v

        def __contains__(self, k):
            return k in self._d

        def pop(self, k, default=None):
            return self._d.pop(k, default)

        def get(self, k, default=None):
            return self._d.get(k, default)

        def __delitem__(self, k):
            del self._d[k]

    sess = _Sess()
    monkeypatch.setattr(mod.st, "session_state", sess)
    mod._reset_cag_page_state()
    assert sess._d["page"] == "clientes_agendamentos"
    assert sess._d["cli_edit_id"] == 1
    assert sess._d["cag_form_v"] == 0
    assert sess._d["cag_edit_id"] is None
    assert "cag_busca_nome" not in sess._d
    assert "cag_busca_nif" not in sess._d


def test_cag_valores_setor2_identificacao_basica():
    from src.ui import page_clientes_agendamentos as mod

    assert mod.cag_valores_setor2_identificacao_basica(None) == ("-", "-", "-", "-")
    cli = {
        "nome": "Ana",
        "nif_ou_documento": "123456789",
        "whatsapp": "+351912000000",
        "email": "ana@exemplo.pt",
    }
    assert mod.cag_valores_setor2_identificacao_basica(cli) == (
        "Ana",
        "123456789",
        "+351912000000",
        "ana@exemplo.pt",
    )


def test_obter_resumo_agendamentos_setor2_proposta_id_invalido():
    r = obter_resumo_agendamentos_cliente_setor2_proposta(0)
    assert r["previstos_30d_por_natureza"] == []
    assert r["pendente_pgto_valor_total_centavos"] == 0
    assert r["cancelados_60d_total"] == 0


def test_html_linhas_natureza_vazio():
    from src.ui import page_clientes_agendamentos as mod

    h = mod._html_linhas_natureza([])
    assert "—" in h


def test_html_linhas_natureza_linhas():
    from src.ui import page_clientes_agendamentos as mod

    h = mod._html_linhas_natureza([("Sessão", 2), ("Evento", 1)])
    assert "Sessão" in h
    assert "Evento" in h
    assert "2" in h
