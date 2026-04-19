"""Painel de Vendas — registo com descontos, bónus, split de meios e recebimentos previstos."""

from __future__ import annotations

from typing import Any, Literal

from src.database.connection import get_connection
from src.modules.constants import ESTADO_AGENDAMENTO_REALIZADO_PENDENTE_LABEL_PT
from src.modules.catalogo import resolver_snapshot_venda
from src.modules.credito_ledger import (
    meio_legacy_para_tipo_linha,
    obter_aberto_liquidacao_venda_centavos,
    registrar_uso_credito_em_venda,
    saldo_credito_cliente_centavos,
    venda_totalmente_liquidada,
)

PCT_BASIS = 10000  # 100,00% = 10000 (centésimos de ponto percentual)

EstadoPagamento = Literal["integral", "pendente", "parcial", "parcelado"]
MeioPagamento = Literal["dinheiro", "cartao_credito", "mbway", "iban"]


def _desconto_percent_sobre(bruto: int, basis: int) -> int:
    if bruto <= 0 or basis <= 0:
        return 0
    if basis > PCT_BASIS:
        basis = PCT_BASIS
    return int(round(bruto * basis / PCT_BASIS))


def _desconto_fixo_sobre(bruto: int, fixo: int) -> int:
    if fixo <= 0:
        return 0
    return min(fixo, bruto)


def calcular_totais_venda(
    linhas: list[dict[str, Any]],
    *,
    desconto_global_tipo: str | None = None,
    desconto_global_valor: int | None = None,
) -> tuple[bool, str, dict[str, int]]:
    """
    `linhas`: quantidade, preco_unitario_centavos, desconto_linha_tipo (none|percent|fixed),
      desconto_linha_valor (basis 1–10000 ou centavos).
    Desconto global: `desconto_global_tipo` percent|fixed|None e valor (basis ou centavos).
    """
    if not linhas:
        return False, "❌ Inclua pelo menos um item na venda.", {}

    subtotal_bruto = 0
    subtotal_apos_linhas = 0
    for ln in linhas:
        q = int(ln["quantidade"])
        if q < 1:
            return False, "❌ Quantidade deve ser ≥ 1 em cada linha.", {}
        unit = int(ln["preco_unitario_centavos"])
        bruto = q * unit
        subtotal_bruto += bruto
        dt = ln.get("desconto_linha_tipo") or "none"
        dv = ln.get("desconto_linha_valor")
        disc = 0
        if dt == "percent" and dv is not None:
            disc = _desconto_percent_sobre(bruto, int(dv))
        elif dt == "fixed" and dv is not None:
            disc = _desconto_fixo_sobre(bruto, int(dv))
        subtotal_apos_linhas += bruto - disc

    gtipo = desconto_global_tipo
    gval = desconto_global_valor
    global_aplicado = 0
    if gtipo == "percent" and gval is not None:
        global_aplicado = _desconto_percent_sobre(subtotal_apos_linhas, int(gval))
    elif gtipo == "fixed" and gval is not None:
        global_aplicado = _desconto_fixo_sobre(subtotal_apos_linhas, int(gval))

    total_final = subtotal_apos_linhas - global_aplicado
    if total_final < 0:
        total_final = 0

    return (
        True,
        "",
        {
            "subtotal_bruto_centavos": subtotal_bruto,
            "subtotal_apos_descontos_linha_centavos": subtotal_apos_linhas,
            "desconto_global_centavos_aplicado": global_aplicado,
            "total_final_centavos": total_final,
        },
    )


def _validar_pagamento(
    estado: EstadoPagamento,
    total_final: int,
    pagamentos: list[tuple[MeioPagamento, int]],
    previstos: list[tuple[str, int]],
    *,
    credito_abatido_centavos: int = 0,
    permite_parcial_sem_previsto: bool = False,
) -> tuple[bool, str]:
    cab = max(0, int(credito_abatido_centavos))
    pago = sum(v for _, v in pagamentos)
    agend = sum(v for _, v in previstos)
    if pago < 0 or agend < 0:
        return False, "❌ Valores de pagamento inválidos."
    liquido_necessario = total_final - cab
    if liquido_necessario < 0:
        return False, "❌ Abatimento de crédito não pode exceder o total da venda."
    if permite_parcial_sem_previsto:
        if agend != 0:
            return (
                False,
                "❌ Pagamento parcial: não utilize recebimentos previstos nesta modalidade.",
            )
        if pago <= 0:
            return False, "❌ Pagamento parcial: indique um valor pago maior que zero."
        if pago > liquido_necessario:
            return (
                False,
                f"❌ Pagamento parcial: o valor pago ({pago/100:.2f} €) não pode exceder "
                f"o total a liquidar ({liquido_necessario/100:.2f} €).",
            )
        return True, ""
    if pago + agend != liquido_necessario:
        return (
            False,
            f"❌ Soma dos meios ({pago/100:.2f} €) + recebimentos previstos ({agend/100:.2f} €) "
            f"deve igualar o total a liquidar ({liquido_necessario/100:.2f} €) "
            f"(total {total_final/100:.2f} € − crédito {cab/100:.2f} €).",
        )
    if estado == "integral":
        if pago != liquido_necessario or agend != 0:
            return False, "❌ Pagamento integral: liquidar o total nos meios indicados, sem recebimentos previstos."
    elif estado == "pendente":
        if pago != 0 or agend != liquido_necessario:
            return False, "❌ Pendente: nada liquidado agora; o total a receber deve constar nos recebimentos previstos."
    elif estado == "parcial":
        if pago <= 0 or agend <= 0:
            return False, "❌ Parcial: indique valor já liquidado (meios) e complementos previstos."
    elif estado == "parcelado":
        momentos = (1 if pago > 0 else 0) + len(previstos)
        if momentos < 2:
            return (
                False,
                "❌ Parcelado: indique pelo menos dois momentos de pagamento "
                "(ex.: parte nos meios + parcelas previstas, ou só parcelas previstas ≥ 2).",
            )
    return True, ""


def registrar_venda(
    cliente_id: int,
    estado_pagamento: EstadoPagamento,
    linhas_entrada: list[dict[str, Any]],
    desconto_global_tipo: str | None,
    desconto_global_valor: int | None,
    pagamentos: list[tuple[str, int]],
    recebimentos_previstos: list[tuple[str, int]],
    observacoes: str,
    *,
    agendamento_contexto_id: int | None = None,
    credito_abatido_centavos: int = 0,
    modo_pagamento_parcial_sem_previsto: bool = False,
    fatura_solicitada: bool | int = False,
) -> tuple[bool, str, int | None]:
    """
    `linhas_entrada`: servico_id, quantidade, is_bonus, evento_preco (adulto|crianca|None),
      desconto_linha_tipo, desconto_linha_valor (basis ou centavos);
      opcional `colaborador_id` (int) por linha — atribuição para relatórios.
    `pagamentos`: (meio, valor_centavos)
    `recebimentos_previstos`: (data YYYY-MM-DD, valor_centavos)
    `agendamento_contexto_id`: opcional — UC-B / rastreio de visita (cliente = do agendamento).

    Retorno: (ok, mensagem, venda_id ou None se falha).
    """
    cid = int(cliente_id)
    if cid < 1:
        return False, "❌ Cliente inválido.", None

    resolved: list[dict[str, Any]] = []
    for i, raw in enumerate(linhas_entrada):
        sid = int(raw["servico_id"])
        qty = int(raw["quantidade"])
        bonus = bool(raw.get("is_bonus"))
        evt = raw.get("evento_preco")
        evt_s = str(evt).strip() if evt else None
        if evt_s not in (None, "", "adulto", "crianca"):
            evt_s = None
        if evt_s == "":
            evt_s = None
        ok_s, msg_s, snap = resolver_snapshot_venda(
            sid, evento_preco=evt_s, is_bonus=bonus
        )
        if not ok_s:
            return False, f"Linha {i + 1}: {msg_s}", None

        override_raw = raw.get("preco_unitario_centavos_override")
        if override_raw is not None:
            try:
                unit_ov = int(override_raw)
            except (TypeError, ValueError):
                return False, f"❌ Linha {i + 1}: preço de liquidação inválido.", None
            if unit_ov < 0:
                return False, f"❌ Linha {i + 1}: preço de liquidação não pode ser negativo.", None
            pvo = raw.get("pendente_venda_id")
            if pvo is not None:
                try:
                    vid_p = int(pvo)
                except (TypeError, ValueError):
                    return False, f"❌ Linha {i + 1}: venda de pendência inválida.", None
                aberto = obter_aberto_liquidacao_venda_centavos(vid_p)
                if unit_ov > aberto:
                    return (
                        False,
                        f"❌ Linha {i + 1}: valor a liquidar ({unit_ov / 100:.2f} €) "
                        f"excede o em aberto ({aberto / 100:.2f} €) na venda #{vid_p}.",
                        None,
                    )
            unit = unit_ov
        else:
            unit = int(snap["preco_unitario_centavos"])

        dt = raw.get("desconto_linha_tipo") or "none"
        if dt not in ("none", "percent", "fixed"):
            return False, f"❌ Linha {i + 1}: tipo de desconto inválido.", None
        dv_raw = raw.get("desconto_linha_valor")
        dv: int | None = None
        if dt == "percent":
            if dv_raw is None:
                return False, f"❌ Linha {i + 1}: indique o desconto em %.", None
            pct = float(dv_raw)
            dv = int(round(pct * 100))
            if dv < 1 or dv > PCT_BASIS:
                return False, f"❌ Linha {i + 1}: desconto % entre 0,01 e 100.", None
        elif dt == "fixed":
            if dv_raw is None:
                return False, f"❌ Linha {i + 1}: indique o valor do desconto (€).", None
            from src.modules.catalogo import euros_para_centavos

            dv = euros_para_centavos(float(dv_raw))
            if dv is None or dv < 1:
                return False, f"❌ Linha {i + 1}: desconto em valor inválido.", None

        colab_raw = raw.get("colaborador_id")
        colab_id: int | None
        if colab_raw is None or colab_raw == "" or colab_raw == 0:
            colab_id = None
        else:
            try:
                colab_id = int(colab_raw)
            except (TypeError, ValueError):
                return False, f"❌ Linha {i + 1}: colaborador inválido.", None
            if colab_id < 1:
                colab_id = None

        row_d: dict[str, Any] = {
            "servico_id": sid,
            "quantidade": qty,
            "preco_unitario_centavos": int(unit),
            "nome_snapshot": str(snap["nome"]),
            "descricao_snapshot": str(snap["descricao"]),
            "unidade_medida_snapshot": str(snap["unidade_medida"]),
            "is_bonus": 1 if bonus else 0,
            "natureza": str(snap["natureza"]),
            "evento_preco_tipo": evt_s if str(snap["natureza"]) == "Evento" else None,
            "desconto_linha_tipo": dt,
            "desconto_linha_valor": dv,
            "colaborador_id": colab_id,
        }
        resolved.append(row_d)

    gtipo = desconto_global_tipo
    if gtipo not in (None, "percent", "fixed", ""):
        return False, "❌ Tipo de desconto global inválido.", None
    gval: int | None = desconto_global_valor
    if gtipo is None or gtipo == "":
        gtipo = None
        gval = None
    elif gtipo == "percent":
        if gval is None:
            return False, "❌ Indique o desconto global em %.", None
        if gval < 1 or gval > PCT_BASIS:
            return False, "❌ Desconto global % entre 0,01 e 100.", None
    elif gtipo == "fixed":
        if gval is None or gval < 1:
            return False, "❌ Indique o desconto global em valor (centavos > 0).", None

    slim: list[dict[str, Any]] = [
        {
            "quantidade": r["quantidade"],
            "preco_unitario_centavos": r["preco_unitario_centavos"],
            "desconto_linha_tipo": r["desconto_linha_tipo"],
            "desconto_linha_valor": r["desconto_linha_valor"],
        }
        for r in resolved
    ]
    ok_c, msg_c, totais = calcular_totais_venda(
        slim,
        desconto_global_tipo=gtipo,
        desconto_global_valor=gval,
    )
    if not ok_c:
        return False, msg_c, None

    total_final = totais["total_final_centavos"]
    sub_bruto = totais["subtotal_bruto_centavos"]
    sub_lin = totais["subtotal_apos_descontos_linha_centavos"]
    glob_apl = totais["desconto_global_centavos_aplicado"]

    meios_norm: list[tuple[MeioPagamento, int]] = []
    for meio, val in pagamentos:
        m = str(meio).strip()
        if m not in ("dinheiro", "cartao_credito", "mbway", "iban"):
            return False, f"❌ Meio de pagamento inválido: {meio}.", None
        meios_norm.append((m, int(val)))

    prev_norm = [(str(d)[:10], int(v)) for d, v in recebimentos_previstos]

    cab = max(0, int(credito_abatido_centavos))
    pago_pre = sum(v for _, v in meios_norm)
    liquido_pre = max(0, int(total_final) - cab)
    if modo_pagamento_parcial_sem_previsto:
        estado_efetivo: EstadoPagamento = (
            "integral" if pago_pre >= liquido_pre and liquido_pre > 0 else "parcial"
        )
    else:
        estado_efetivo = estado_pagamento

    ok_p, msg_p = _validar_pagamento(
        estado_efetivo,
        total_final,
        meios_norm,
        prev_norm,
        credito_abatido_centavos=cab,
        permite_parcial_sem_previsto=modo_pagamento_parcial_sem_previsto,
    )
    if not ok_p:
        return False, msg_p, None

    conn = get_connection()
    if not conn:
        return False, "❌ Não foi possível ligar à base de dados.", None

    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM clientes WHERE id = ?", (cid,))
        if cur.fetchone() is None:
            return False, "❌ Cliente não encontrado.", None

        if cab > 0:
            saldo = saldo_credito_cliente_centavos(cur, cid)
            if saldo < cab:
                return (
                    False,
                    f"❌ Saldo de crédito insuficiente (disponível {saldo / 100:.2f} €, pedido {cab / 100:.2f} €).",
                    None,
                )

        ag_ctx = agendamento_contexto_id
        if ag_ctx is not None:
            cur.execute(
                "SELECT cliente_id FROM agendamentos WHERE id = ?",
                (int(ag_ctx),),
            )
            ra = cur.fetchone()
            if ra is None:
                return False, "❌ Agendamento de contexto não encontrado.", None
            if int(ra[0]) != cid:
                return (
                    False,
                    "❌ Cliente da venda deve coincidir com o agendamento de contexto.",
                    None,
                )

        for i, r in enumerate(resolved):
            cob = r.get("colaborador_id")
            if cob is not None:
                cur.execute("SELECT id FROM colaboradores WHERE id = ?", (int(cob),))
                if cur.fetchone() is None:
                    return False, f"❌ Linha {i + 1}: colaborador não encontrado.", None

        cur.execute(
            """
            INSERT INTO vendas (
                cliente_id, estado_pagamento,
                subtotal_bruto_centavos, subtotal_apos_descontos_linha_centavos,
                desconto_global_tipo, desconto_global_valor, desconto_global_centavos_aplicado,
                total_final_centavos, observacoes, agendamento_contexto_id,
                credito_abatido_centavos, fatura_solicitada
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cid,
                estado_efetivo,
                sub_bruto,
                sub_lin,
                gtipo,
                gval,
                glob_apl,
                total_final,
                (observacoes or "").strip(),
                int(ag_ctx) if ag_ctx is not None else None,
                cab,
                1 if fatura_solicitada else 0,
            ),
        )
        vid = int(cur.lastrowid)
        marcar_parcial_itens = 1 if modo_pagamento_parcial_sem_previsto else 0

        for ordem, r in enumerate(resolved, start=1):
            q = int(r["quantidade"])
            unit = int(r["preco_unitario_centavos"])
            bruto = q * unit
            dt = r["desconto_linha_tipo"]
            dv = r.get("desconto_linha_valor")
            dcent = 0
            if dt == "percent" and dv is not None:
                dcent = _desconto_percent_sobre(bruto, int(dv))
            elif dt == "fixed" and dv is not None:
                dcent = _desconto_fixo_sobre(bruto, int(dv))
            tlin = bruto - dcent
            dtipo_db = dt if dt != "none" else None
            cur.execute(
                """
                INSERT INTO venda_itens (
                    venda_id, servico_id, ordem, quantidade,
                    preco_unitario_centavos, nome_snapshot, descricao_snapshot, unidade_medida_snapshot,
                    is_bonus, evento_preco_tipo,
                    desconto_linha_tipo, desconto_linha_valor,
                    subtotal_bruto_centavos, desconto_linha_centavos, total_linha_centavos,
                    colaborador_id, pagamento_parcial
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    vid,
                    int(r["servico_id"]),
                    ordem,
                    q,
                    unit,
                    r["nome_snapshot"],
                    r["descricao_snapshot"],
                    r["unidade_medida_snapshot"],
                    int(r["is_bonus"]),
                    r.get("evento_preco_tipo"),
                    dtipo_db,
                    int(dv) if dv is not None else None,
                    bruto,
                    dcent,
                    tlin,
                    r.get("colaborador_id"),
                    marcar_parcial_itens,
                ),
            )

        for o, (m, vc) in enumerate(meios_norm, start=1):
            if vc > 0:
                cur.execute(
                    """
                    INSERT INTO venda_pagamentos (venda_id, ordem, meio, valor_centavos)
                    VALUES (?, ?, ?, ?)
                    """,
                    (vid, o, m, vc),
                )
                cur.execute(
                    """
                    INSERT INTO venda_pagamento_linhas (venda_id, ordem, tipo_meio, valor_centavos)
                    VALUES (?, ?, ?, ?)
                    """,
                    (vid, o, meio_legacy_para_tipo_linha(m), vc),
                )

        if cab > 0:
            registrar_uso_credito_em_venda(
                cur, cliente_id=cid, venda_id=vid, valor_abatido_centavos=cab
            )

        for o, (dp, vc) in enumerate(prev_norm, start=1):
            if vc > 0:
                cur.execute(
                    """
                    INSERT INTO venda_recebimentos_previstos (venda_id, ordem, data_prevista, valor_centavos)
                    VALUES (?, ?, ?, ?)
                    """,
                    (vid, o, dp, vc),
                )

        conn.commit()
        return True, f"✅ Venda #{vid} registada — total {total_final / 100:.2f} €.", vid
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro ao guardar venda: {e}", None
    finally:
        conn.close()


def reconciliar_estado_pagamento_venda(venda_id: int) -> None:
    """
    Se a venda estiver totalmente liquidada, passa `estado_pagamento` a `integral`
    e limpa a marca `pagamento_parcial` nas linhas.
    """
    conn = get_connection()
    if not conn:
        return
    aplicou_integral = False
    try:
        cur = conn.cursor()
        if not venda_totalmente_liquidada(cur, int(venda_id)):
            return
        cur.execute(
            "UPDATE vendas SET estado_pagamento = 'integral' WHERE id = ?",
            (int(venda_id),),
        )
        try:
            cur.execute(
                "UPDATE venda_itens SET pagamento_parcial = 0 WHERE venda_id = ?",
                (int(venda_id),),
            )
        except Exception:
            pass
        conn.commit()
        aplicou_integral = True
    except Exception:
        conn.rollback()
    finally:
        conn.close()
    if aplicou_integral:
        from src.modules.agendamento import promover_agendamentos_realizado_pendente_apos_liquidacao_venda

        promover_agendamentos_realizado_pendente_apos_liquidacao_venda(int(venda_id))


def liquidar_pendencias_pos_venda_registo(
    venda_nova_id: int,
    cart_snapshot: list[dict[str, Any]],
) -> list[str]:
    f"""
    Regista na venda de origem os valores das linhas do carrinho marcadas como liquidação
    de pendência e invoca `alterar_status(..., CONCLUIDO)` por agendamento (o próprio fluxo
    mantém «{ESTADO_AGENDAMENTO_REALIZADO_PENDENTE_LABEL_PT}» se a venda origem ainda não estiver totalmente liquidada).
    """
    from src.modules.agendamento import alterar_status

    msgs: list[str] = []
    conn = get_connection()
    if not conn:
        return ["❌ Sem ligação à BD na liquidação de pendências."]
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT total_linha_centavos
            FROM venda_itens
            WHERE venda_id = ?
            ORDER BY ordem ASC, id ASC
            """,
            (int(venda_nova_id),),
        )
        tls = [int(r[0]) for r in cur.fetchall()]
        if len(tls) != len(cart_snapshot):
            msgs.append(
                f"⚠️ Liquidação pendências: {len(tls)} linhas na venda #{venda_nova_id} vs "
                f"{len(cart_snapshot)} itens no carrinho — sem repasse."
            )
            return msgs

        for pos, it in enumerate(cart_snapshot):
            ag = it.get("pendente_agendamento_id")
            vo = it.get("pendente_venda_id")
            if ag is None or vo is None:
                continue
            valor = int(tls[pos]) if pos < len(tls) else 0
            if valor < 1:
                continue
            cur.execute(
                "SELECT COALESCE(MAX(ordem), 0) FROM venda_pagamento_linhas WHERE venda_id = ?",
                (int(vo),),
            )
            o_next = int(cur.fetchone()[0]) + 1
            cur.execute(
                """
                INSERT INTO venda_pagamento_linhas (venda_id, ordem, tipo_meio, valor_centavos)
                VALUES (?, ?, 'DINHEIRO_MBWAY', ?)
                """,
                (int(vo), o_next, valor),
            )
            msgs.append(
                f"✅ Liquidados {valor / 100:.2f} € na venda origem #{int(vo)} (ag. #{int(ag)})."
            )

        conn.commit()
    except Exception as e:
        conn.rollback()
        return [f"❌ Erro na liquidação de pendências: {e}"]
    finally:
        conn.close()

    vid_origens = sorted(
        {
            int(it["pendente_venda_id"])
            for it in cart_snapshot
            if it.get("pendente_venda_id") is not None
        }
    )
    for vo in vid_origens:
        reconciliar_estado_pagamento_venda(int(vo))

    for it in cart_snapshot:
        ag = it.get("pendente_agendamento_id")
        if ag is None:
            continue
        _ok_s, msg_s = alterar_status(
            int(ag),
            "CONCLUIDO",
            actor="pdv_liquidacao_pendencia",
        )
        msgs.append(msg_s)
    return msgs


def listar_venda_item_ids_em_ordem(venda_id: int) -> list[int]:
    """Ids de `venda_itens` na mesma ordem de inserção de `registrar_venda` (ordem, id)."""
    conn = get_connection()
    if not conn:
        return []
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id FROM venda_itens
            WHERE venda_id = ?
            ORDER BY ordem ASC, id ASC
            """,
            (int(venda_id),),
        )
        return [int(r[0]) for r in cur.fetchall()]
    finally:
        conn.close()


__all__ = [
    "PCT_BASIS",
    "calcular_totais_venda",
    "liquidar_pendencias_pos_venda_registo",
    "listar_venda_item_ids_em_ordem",
    "reconciliar_estado_pagamento_venda",
    "registrar_venda",
]
