"""Fatia de domínio E2E (pytest) — catálogo Especialidades sem browser.

Reutilizada por `tests/e2e_stress_test.py` para alargar a «jornada» transversal
sem Playwright: valida listagens, duplicados, rejeição de natureza errada e
chaves de `listar_servicos_para_venda`.
"""

from __future__ import annotations


def run_catalogo_especialidades_domain_slice() -> str | None:
    """Devolve mensagem de erro ou `None` se todos os passos passarem."""
    from src.modules.catalogo import (
        cadastrar_especialidade,
        cadastrar_servico_fase1,
        listar_especialidades_por_natureza,
        listar_servicos_para_venda,
    )

    if not any(str(r.get("nome") or "") == "Geral" for r in listar_especialidades_por_natureza("Pack")):
        return "e2e esp: falta «Geral» em Pack após migração"

    ok, msg = cadastrar_especialidade("Sessão", "E2E Slice Dup Nome X", "")
    if not ok:
        return f"e2e esp: cadastrar especialidade 1: {msg}"
    ok2, msg2 = cadastrar_especialidade("Sessão", "E2E Slice Dup Nome X", "")
    if ok2:
        return "e2e esp: duplicado de especialidade devia falhar"

    rows_p = listar_especialidades_por_natureza("Produto")
    eid_prod = next((int(r["id"]) for r in rows_p if str(r.get("nome") or "") == "Geral"), None)
    if eid_prod is None:
        return "e2e esp: sem Geral em Produto"
    ok3, msg3 = cadastrar_servico_fase1(
        "Sessão",
        "E2E Slice Mau Nat",
        "D.",
        True,
        especialidade_id=eid_prod,
        sessao_duracao_horas=1.0,
        sessao_valor_euros=40.0,
    )
    if ok3:
        return "e2e esp: serviço com especialidade de outra natureza devia falhar"

    for r in listar_servicos_para_venda():
        if "especialidade_id" not in r or "especialidade" not in r:
            return "e2e esp: listar_servicos_para_venda sem chaves especialidade*"

    return None
