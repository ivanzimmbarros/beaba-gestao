"""Painel de Vendas — UI Streamlit (E07)."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from src.modules.catalogo import (
    centavos_para_texto_euros,
    euros_para_centavos,
    listar_servicos_para_venda,
    resolver_snapshot_venda,
)
from src.modules.cliente import (
    atualizar_cliente,
    buscar_cliente_por_whatsapp,
    cadastrar_cliente,
    obter_cliente_completo,
)
from src.modules.colaborador import listar_colaboradores_resumo
from src.modules.constants import SEXOS
from src.modules.validators import parse_data_iso
from src.modules.agendamento import (
    associar_agendamento_pre_venda_a_item,
    obter_agendamento,
    obter_primeiro_item_venda_por_servico,
)
from src.modules.venda import calcular_totais_venda, registrar_venda


def _prime_cliente_form(prefix: str, d: dict) -> None:
    """Preenche widgets Streamlit a partir de ficha carregada."""
    st.session_state[f"{prefix}_nome"] = d["nome"]
    st.session_state[f"{prefix}_num"] = d["whatsapp"]
    st.session_state[f"{prefix}_email"] = d["email"]
    st.session_state[f"{prefix}_sexo"] = d["sexo"]
    st.session_state[f"{prefix}_rua"] = d["endereco_rua"]
    st.session_state[f"{prefix}_numero"] = d["endereco_numero"]
    st.session_state[f"{prefix}_comp"] = d["endereco_complemento"]
    st.session_state[f"{prefix}_cp"] = d["codigo_postal"]
    st.session_state[f"{prefix}_conc"] = d["concelho"]
    st.session_state[f"{prefix}_freg"] = d["freguesia"]
    st.session_state[f"{prefix}_dist"] = d["distrito"]
    st.session_state[f"{prefix}_pais"] = d["pais"] or "Portugal"
    st.session_state[f"{prefix}_obs"] = d["observacoes"]
    st.session_state[f"{prefix}_temf"] = "Sim" if d["tem_filhos"] else "Não"
    if d["sexo"] == "Feminino":
        st.session_state[f"{prefix}_grav"] = "Sim" if d.get("gravida") else "Não"
        dp = d.get("data_parto_prevista")
        if dp and parse_data_iso(str(dp)[:10]):
            st.session_state[f"{prefix}_parto"] = datetime.strptime(str(dp)[:10], "%Y-%m-%d").date()
    filhos = d.get("filhos") or []
    st.session_state[f"{prefix}_qfil"] = max(1, len(filhos)) if d["tem_filhos"] else 1
    for j, (fn, ida, sx) in enumerate(filhos):
        st.session_state[f"{prefix}_fn_{j}"] = fn
        st.session_state[f"{prefix}_fi_{j}"] = int(ida)
        st.session_state[f"{prefix}_fs_{j}"] = sx
    em = d.get("contatos_emergencia") or []
    st.session_state[f"{prefix}_nem"] = max(1, len(em))
    for j, (en, et) in enumerate(em):
        st.session_state[f"{prefix}_em_n_{j}"] = en
        st.session_state[f"{prefix}_em_t_{j}"] = et


def _collect_filhos(prefix: str, tem: bool, qtd: int) -> list[tuple[str, int, str]]:
    if not tem:
        return []
    out: list[tuple[str, int, str]] = []
    for j in range(qtd):
        fn = st.session_state.get(f"{prefix}_fn_{j}", "")
        ida = int(st.session_state.get(f"{prefix}_fi_{j}", 0))
        sx = st.session_state.get(f"{prefix}_fs_{j}", SEXOS[0])
        out.append((str(fn), ida, str(sx)))
    return out


def _collect_emerg(prefix: str, n: int) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for j in range(n):
        en = st.session_state.get(f"{prefix}_em_n_{j}", "")
        et = st.session_state.get(f"{prefix}_em_t_{j}", "")
        out.append((str(en), str(et)))
    return out


def render_page_vendas(
    *,
    render_back_and_breadcrumb,
) -> None:
    render_back_and_breadcrumb(["Home", "Vendas", "Registo"], back_key="bea_back_vendas")
    st.markdown("### Painel de vendas")
    st.caption(
        "Cliente (pesquisa ou cadastro) → itens ativos do catálogo → descontos → "
        "estado de pagamento com split de meios e recebimentos previstos. "
        "Após registar, use **Agendamentos** no Início para marcar sessões com saldo da venda."
    )

    if "venda_fv" not in st.session_state:
        st.session_state.venda_fv = 0
    fv = st.session_state.venda_fv
    fk = f"vnd_{fv}"

    if "venda_cliente_id" not in st.session_state:
        st.session_state.venda_cliente_id = None
    if "venda_cart" not in st.session_state:
        st.session_state.venda_cart = []
    if "venda_n_meios" not in st.session_state:
        st.session_state.venda_n_meios = 1
    if "venda_n_prev" not in st.session_state:
        st.session_state.venda_n_prev = 1
    if "venda_fechar_agendamento_id" not in st.session_state:
        st.session_state.venda_fechar_agendamento_id = None
    if "venda_agendamento_contexto_id" not in st.session_state:
        st.session_state.venda_agendamento_contexto_id = None

    if "_vnda_prime" in st.session_state:
        prime = st.session_state.pop("_vnda_prime")
        _prime_cliente_form(prime["prefix"], prime["data"])

    fechar_aid = st.session_state.get("venda_fechar_agendamento_id")
    ctx_aid = st.session_state.get("venda_agendamento_contexto_id")
    if fechar_aid:
        st.info(
            f"**Pré-venda:** após registar a venda, o agendamento **#{fechar_aid}** será associado "
            "à linha do **mesmo serviço** da reserva."
        )
    elif ctx_aid:
        st.info(
            f"**Contexto de visita:** esta venda ficará ligada ao agendamento **#{ctx_aid}** (auditoria)."
        )

    # --- Cliente ---
    st.subheader("1. Cliente")
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        tel_busca = st.text_input(
            "Número de contacto (11 dígitos)",
            key=f"{fk}_tel_busca",
            placeholder="Procurar na base",
        )
    with c2:
        st.write("")
        if st.button("Procurar cliente", key=f"{fk}_btn_busca"):
            cid = buscar_cliente_por_whatsapp(tel_busca)
            if cid is None:
                st.session_state.venda_cliente_id = None
                st.warning("Nenhum cliente com este contacto. Pode cadastrar abaixo.")
            else:
                st.session_state.venda_cliente_id = cid
                d = obter_cliente_completo(cid)
                if d:
                    st.session_state._vnda_prime = {"prefix": f"{fk}_vc", "data": d}
                st.success(f"Cliente encontrado (#{cid}).")
                st.rerun()
    with c3:
        if st.session_state.venda_cliente_id and st.button("Limpar seleção", key=f"{fk}_clr_cli"):
            st.session_state.venda_cliente_id = None
            st.rerun()

    cli_id = st.session_state.venda_cliente_id

    if cli_id:
        st.info(f"Cliente selecionado: **#{cli_id}**. Pode atualizar a ficha antes de fechar a venda.")
        with st.expander("Editar ficha do cliente", expanded=False):
            p = f"{fk}_vc"
            st.text_input("Nome completo *", key=f"{p}_nome")
            st.text_input("Número de contacto *", key=f"{p}_num")
            st.text_input("Email *", key=f"{p}_email")
            sx = st.selectbox("Sexo *", SEXOS, key=f"{p}_sexo")
            gravida: bool | None = None
            data_parto: str | None = None
            if sx == "Feminino":
                g = st.radio("Está grávida? *", ["Não", "Sim"], horizontal=True, key=f"{p}_grav")
                gravida = g == "Sim"
                if gravida:
                    dpp = st.date_input("Estimativa de data de parto *", key=f"{p}_parto")
                    data_parto = dpp.isoformat() if dpp else None
            st.markdown("**Morada**")
            a1, a2 = st.columns(2)
            with a1:
                st.text_input("Rua *", key=f"{p}_rua")
            with a2:
                st.text_input("Número *", key=f"{p}_numero")
            st.text_input("Complemento", key=f"{p}_comp")
            b1, b2, b3 = st.columns(3)
            with b1:
                st.text_input("Código postal *", key=f"{p}_cp")
            with b2:
                st.text_input("Concelho *", key=f"{p}_conc")
            with b3:
                st.text_input("Freguesia *", key=f"{p}_freg")
            c1, c2 = st.columns(2)
            with c1:
                st.text_input("Distrito", key=f"{p}_dist")
            with c2:
                st.text_input("País *", key=f"{p}_pais")
            temf = st.radio("Possui filhos? *", ["Não", "Sim"], horizontal=True, key=f"{p}_temf") == "Sim"
            qfil = 1
            if temf:
                qfil = int(
                    st.number_input(
                        "Quantos filhos? *",
                        min_value=1,
                        max_value=20,
                        value=int(st.session_state.get(f"{p}_qfil", 1)),
                        key=f"{p}_qfil",
                    )
                )
                for j in range(qfil):
                    st.markdown(f"**Filho {j + 1}**")
                    f1, f2, f3 = st.columns(3)
                    with f1:
                        st.text_input("Nome *", key=f"{p}_fn_{j}")
                    with f2:
                        st.number_input("Idade (anos) *", 0, 120, key=f"{p}_fi_{j}")
                    with f3:
                        st.selectbox("Sexo *", SEXOS, key=f"{p}_fs_{j}")
            nem = int(
                st.number_input(
                    "Linhas de contacto de emergência (0–10)",
                    min_value=0,
                    max_value=10,
                    value=min(10, int(st.session_state.get(f"{p}_nem", 1))),
                    key=f"{p}_nem",
                )
            )
            for j in range(nem):
                e1, e2 = st.columns(2)
                with e1:
                    st.text_input(f"Nome emerg. {j + 1}", key=f"{p}_em_n_{j}")
                with e2:
                    st.text_input(f"Telefone emerg. {j + 1}", key=f"{p}_em_t_{j}")
            st.text_area("Observações", key=f"{p}_obs")
            if st.button("Guardar alterações na ficha", key=f"{p}_save"):
                filhos_l = _collect_filhos(p, temf, qfil if temf else 0)
                em_l = _collect_emerg(p, nem)
                ok_u, msg_u = atualizar_cliente(
                    int(cli_id),
                    nome=str(st.session_state.get(f"{p}_nome", "")),
                    numero_contato=str(st.session_state.get(f"{p}_num", "")),
                    endereco_rua=str(st.session_state.get(f"{p}_rua", "")),
                    endereco_numero=str(st.session_state.get(f"{p}_numero", "")),
                    endereco_complemento=str(st.session_state.get(f"{p}_comp", "")),
                    codigo_postal=str(st.session_state.get(f"{p}_cp", "")),
                    concelho=str(st.session_state.get(f"{p}_conc", "")),
                    freguesia=str(st.session_state.get(f"{p}_freg", "")),
                    distrito=str(st.session_state.get(f"{p}_dist", "")),
                    pais=str(st.session_state.get(f"{p}_pais", "Portugal")),
                    email=str(st.session_state.get(f"{p}_email", "")),
                    sexo=str(st.session_state.get(f"{p}_sexo", SEXOS[0])),
                    tem_filhos=temf,
                    filhos=filhos_l,
                    gravida=gravida,
                    data_parto_prevista=data_parto,
                    observacoes=str(st.session_state.get(f"{p}_obs", "")),
                    contatos_emergencia=em_l,
                )
                if ok_u:
                    st.success(msg_u)
                else:
                    st.error(msg_u)
    else:
        st.markdown("**Novo cliente** (cadastro completo — mesmas regras do menu Clientes)")
        pn = f"{fk}_nv"
        st.text_input("Nome completo *", key=f"{pn}_nome")
        st.text_input("Número de contacto *", key=f"{pn}_num")
        st.text_input("Email *", key=f"{pn}_email")
        sxn = st.selectbox("Sexo *", SEXOS, key=f"{pn}_sexo")
        gn: bool | None = None
        dpn: str | None = None
        if sxn == "Feminino":
            gn = st.radio("Está grávida? *", ["Não", "Sim"], horizontal=True, key=f"{pn}_grav") == "Sim"
            if gn:
                dpn_d = st.date_input("Estimativa DPP *", key=f"{pn}_parto")
                dpn = dpn_d.isoformat() if dpn_d else None
        r1, r2 = st.columns(2)
        with r1:
            st.text_input("Rua *", key=f"{pn}_rua")
        with r2:
            st.text_input("Número *", key=f"{pn}_numero")
        st.text_input("Complemento", key=f"{pn}_comp")
        s1, s2, s3 = st.columns(3)
        with s1:
            st.text_input("Código postal *", key=f"{pn}_cp")
        with s2:
            st.text_input("Concelho *", key=f"{pn}_conc")
        with s3:
            st.text_input("Freguesia *", key=f"{pn}_freg")
        t1, t2 = st.columns(2)
        with t1:
            st.text_input("Distrito", key=f"{pn}_dist")
        with t2:
            st.text_input("País *", value="Portugal", key=f"{pn}_pais")
        temfn = st.radio("Possui filhos? *", ["Não", "Sim"], horizontal=True, key=f"{pn}_temf") == "Sim"
        qfn = 1
        if temfn:
            qfn = int(st.number_input("Quantos filhos? *", 1, 20, 1, key=f"{pn}_qfil"))
            for j in range(qfn):
                u1, u2, u3 = st.columns(3)
                with u1:
                    st.text_input(f"Nome filho {j + 1} *", key=f"{pn}_fn_{j}")
                with u2:
                    st.number_input(f"Idade {j + 1} *", 0, 120, key=f"{pn}_fi_{j}")
                with u3:
                    st.selectbox(f"Sexo {j + 1} *", SEXOS, key=f"{pn}_fs_{j}")
        nemn = int(st.number_input("Contactos emergência (0–10)", 0, 10, 0, key=f"{pn}_nem"))
        for j in range(nemn):
            v1, v2 = st.columns(2)
            with v1:
                st.text_input(f"Emerg. nome {j + 1}", key=f"{pn}_em_n_{j}")
            with v2:
                st.text_input(f"Emerg. tel {j + 1}", key=f"{pn}_em_t_{j}")
        st.text_area("Observações", key=f"{pn}_obs")
        if st.button("Cadastrar e usar este cliente", key=f"{pn}_cad"):
            fl = _collect_filhos(pn, temfn, qfn if temfn else 0)
            el = _collect_emerg(pn, nemn)
            ok_c, msg_c = cadastrar_cliente(
                nome=str(st.session_state.get(f"{pn}_nome", "")),
                numero_contato=str(st.session_state.get(f"{pn}_num", "")),
                endereco_rua=str(st.session_state.get(f"{pn}_rua", "")),
                endereco_numero=str(st.session_state.get(f"{pn}_numero", "")),
                endereco_complemento=str(st.session_state.get(f"{pn}_comp", "")),
                codigo_postal=str(st.session_state.get(f"{pn}_cp", "")),
                concelho=str(st.session_state.get(f"{pn}_conc", "")),
                freguesia=str(st.session_state.get(f"{pn}_freg", "")),
                distrito=str(st.session_state.get(f"{pn}_dist", "")),
                pais=str(st.session_state.get(f"{pn}_pais", "Portugal")),
                email=str(st.session_state.get(f"{pn}_email", "")),
                sexo=str(st.session_state.get(f"{pn}_sexo", SEXOS[0])),
                tem_filhos=temfn,
                filhos=fl,
                gravida=gn,
                data_parto_prevista=dpn,
                observacoes=str(st.session_state.get(f"{pn}_obs", "")),
                contatos_emergencia=el,
            )
            if ok_c:
                cid2 = buscar_cliente_por_whatsapp(str(st.session_state.get(f"{pn}_num", "")))
                st.session_state.venda_cliente_id = cid2
                st.session_state.venda_fv += 1
                st.success(msg_c)
                st.rerun()
            else:
                st.error(msg_c)

    # --- Catálogo / carrinho ---
    st.subheader("2. Itens (catálogo ativo)")
    cat = listar_servicos_para_venda()
    if not cat:
        st.error("Sem serviços ativos. Abra o Catálogo.")
        return
    id_to = {int(c["id"]): c for c in cat}
    labels = [f"{c['nome']} ({c['natureza']})" for c in cat]
    ids_list = [int(c["id"]) for c in cat]

    pick_lbl = st.selectbox("Adicionar serviço", labels, key=f"{fk}_pick_svc")
    if st.button("➕ Adicionar à venda", key=f"{fk}_add_svc"):
        idx = labels.index(pick_lbl)
        sid = ids_list[idx]
        st.session_state.venda_cart.append(
            {
                "servico_id": sid,
                "qty": 1,
                "bonus": False,
                "disc_t": "Nenhum",
                "disc_pct": 0.01,
                "disc_eur": 0.0,
                "evt": "Adulto",
                "colab_id": None,
            }
        )
        st.rerun()

    cart = st.session_state.venda_cart
    if not cart:
        st.warning("Adicione pelo menos um serviço.")
    else:
        to_remove: int | None = None
        for idx, it in enumerate(cart):
            meta = id_to.get(int(it["servico_id"]), {})
            nat = str(meta.get("natureza", ""))
            st.markdown(f"**Linha {idx + 1}** — {meta.get('nome', '?')} ({nat})")
            c_a, c_b, c_c = st.columns([1, 1, 2])
            with c_a:
                it["qty"] = int(
                    st.number_input(
                        "Quantidade",
                        min_value=1,
                        max_value=999,
                        value=int(it.get("qty", 1)),
                        key=f"{fk}_q_{idx}",
                    )
                )
            with c_b:
                it["bonus"] = st.checkbox(
                    "Bónus (preço 0)",
                    value=bool(it.get("bonus")),
                    key=f"{fk}_bon_{idx}",
                )
            with c_c:
                if nat == "Evento":
                    it["evt"] = st.radio(
                        "Preço evento",
                        ["Adulto", "Criança"],
                        horizontal=True,
                        key=f"{fk}_evt_{idx}",
                    )
            _dopts = ["Nenhum", "Percentagem", "Valor (€)"]
            it["disc_t"] = st.selectbox(
                "Desconto nesta linha",
                _dopts,
                index=_dopts.index(it["disc_t"])
                if it.get("disc_t") in _dopts
                else 0,
                key=f"{fk}_dt_{idx}",
            )
            if it["disc_t"] == "Percentagem":
                it["disc_pct"] = float(
                    st.number_input(
                        "% desconto",
                        min_value=0.01,
                        max_value=100.0,
                        value=float(it.get("disc_pct", 0.01)),
                        step=0.01,
                        key=f"{fk}_dp_{idx}",
                    )
                )
            elif it["disc_t"] == "Valor (€)":
                it["disc_eur"] = float(
                    st.number_input(
                        "Valor desconto (€)",
                        min_value=0.01,
                        value=float(it.get("disc_eur", 0.01)),
                        step=0.01,
                        key=f"{fk}_de_{idx}",
                    )
                )
            _colab_opts: list[tuple[str, int | None]] = [("— Nenhum —", None)]
            _colab_opts.extend(
                (f"{nome} (#{cid})", int(cid)) for cid, nome in listar_colaboradores_resumo()
            )
            _sel_col = st.selectbox(
                "Colaborador (opcional)",
                options=_colab_opts,
                format_func=lambda x: x[0],
                key=f"{fk}_col_{idx}",
            )
            it["colab_id"] = _sel_col[1]
            evt_key = "adulto" if str(it.get("evt", "Adulto")) == "Adulto" else "crianca"
            ok_r, msg_r, snap = resolver_snapshot_venda(
                int(it["servico_id"]),
                evento_preco=evt_key if nat == "Evento" else None,
                is_bonus=bool(it["bonus"]),
            )
            if ok_r:
                q = int(it["qty"])
                unit = int(snap["preco_unitario_centavos"])
                bruto = q * unit
                dtipo = "none"
                dval: int | None = None
                if it["disc_t"] == "Percentagem":
                    dtipo = "percent"
                    dval = int(round(float(it["disc_pct"]) * 100))
                elif it["disc_t"] == "Valor (€)":
                    dtipo = "fixed"
                    ce = euros_para_centavos(float(it["disc_eur"]))
                    dval = ce
                st.caption(
                    f"{snap['nome']} · {snap['descricao'] or '—'} · "
                    f"**{snap['unidade_medida']}** × {q} → "
                    f"subtotal bruto {centavos_para_texto_euros(bruto)}"
                )
            else:
                st.warning(msg_r)
            if st.button("🗑️ Remover linha", key=f"{fk}_rm_{idx}"):
                to_remove = idx
        if to_remove is not None:
            st.session_state.venda_cart.pop(to_remove)
            st.rerun()

    # Totais parciais (global discount below)
    st.subheader("3. Desconto sobre o total")
    g_opt = st.radio(
        "Desconto global",
        ["Nenhum", "Percentagem", "Valor (€)"],
        horizontal=True,
        key=f"{fk}_gopt",
    )
    g_pct = 0.01
    g_eur = 0.01
    gtipo: str | None = None
    gval: int | None = None
    if g_opt == "Percentagem":
        g_pct = float(st.number_input("% sobre o subtotal (após descontos de linha)", 0.01, 100.0, key=f"{fk}_gpct"))
        gtipo = "percent"
        gval = int(round(g_pct * 100))
    elif g_opt == "Valor (€)":
        g_eur = float(st.number_input("Valor a descontar (€)", 0.01, 1_000_000.0, key=f"{fk}_geur"))
        gtipo = "fixed"
        ge = euros_para_centavos(g_eur)
        gval = ge if ge is not None else None

    tot_preview = None
    if cart:
        slim_all: list[dict] = []
        for it in cart:
            meta = id_to.get(int(it["servico_id"]), {})
            nat = str(meta.get("natureza", ""))
            evt_key = "adulto" if str(it.get("evt", "Adulto")) == "Adulto" else "crianca"
            ok_r, _, snap = resolver_snapshot_venda(
                int(it["servico_id"]),
                evento_preco=evt_key if nat == "Evento" else None,
                is_bonus=bool(it["bonus"]),
            )
            if not ok_r:
                continue
            q = int(it["qty"])
            unit = int(snap["preco_unitario_centavos"])
            dtipo = "none"
            dval = None
            if it["disc_t"] == "Percentagem":
                dtipo = "percent"
                dval = int(round(float(it["disc_pct"]) * 100))
            elif it["disc_t"] == "Valor (€)":
                dtipo = "fixed"
                ce = euros_para_centavos(float(it["disc_eur"]))
                dval = ce
            slim_all.append(
                {
                    "quantidade": q,
                    "preco_unitario_centavos": unit,
                    "desconto_linha_tipo": dtipo,
                    "desconto_linha_valor": dval,
                }
            )
        ok_t, msg_t, tot_preview = calcular_totais_venda(
            slim_all,
            desconto_global_tipo=gtipo,
            desconto_global_valor=gval,
        )
        if ok_t and tot_preview:
            st.success(
                f"**Subtotal (bruto):** {centavos_para_texto_euros(tot_preview['subtotal_bruto_centavos'])} · "
                f"**Após linhas:** {centavos_para_texto_euros(tot_preview['subtotal_apos_descontos_linha_centavos'])} · "
                f"**Desconto global:** {centavos_para_texto_euros(tot_preview['desconto_global_centavos_aplicado'])} · "
                f"**Total final:** {centavos_para_texto_euros(tot_preview['total_final_centavos'])}"
            )
        elif not ok_t:
            st.error(msg_t)

    st.subheader("4. Pagamento")
    est_label = st.selectbox(
        "Estado do pagamento",
        [
            ("integral", "Pagamento integral"),
            ("pendente", "Pendente"),
            ("parcial", "Pagamento parcial"),
            ("parcelado", "Pagamento parcelado"),
        ],
        format_func=lambda x: x[1],
        key=f"{fk}_est",
    )
    estado = est_label[0]

    st.markdown("**Meios já liquidados** (split — várias linhas)")
    n_m = int(
        st.number_input(
            "Quantas linhas de meio",
            min_value=1,
            max_value=10,
            value=int(st.session_state.venda_n_meios),
            key=f"{fk}_n_meios",
        )
    )
    st.session_state.venda_n_meios = n_m
    meios_opts = [
        ("dinheiro", "Dinheiro"),
        ("cartao_credito", "Cartão de crédito"),
        ("mbway", "MBWay"),
    ]
    pag_rows: list[tuple[str, int]] = []
    for j in range(n_m):
        m1, m2 = st.columns([2, 1])
        with m1:
            mi = st.selectbox(
                f"Meio {j + 1}",
                meios_opts,
                format_func=lambda x: x[1],
                key=f"{fk}_m_{j}",
            )
        with m2:
            ve = st.number_input(f"Valor (€) {j + 1}", min_value=0.0, value=0.0, step=0.01, key=f"{fk}_mv_{j}")
        vc = euros_para_centavos(float(ve)) or 0
        pag_rows.append((mi[0], vc))

    st.markdown("**Recebimentos previstos** (complementos / parcelas futuras)")
    n_pr = int(
        st.number_input(
            "Quantas linhas previstas",
            min_value=0,
            max_value=24,
            value=int(st.session_state.venda_n_prev),
            key=f"{fk}_n_prev",
        )
    )
    st.session_state.venda_n_prev = n_pr
    prev_rows: list[tuple[str, int]] = []
    for j in range(n_pr):
        p1, p2 = st.columns([2, 1])
        with p1:
            dv = st.date_input(f"Data prevista {j + 1}", key=f"{fk}_pd_{j}")
        with p2:
            ve2 = st.number_input(f"Valor (€) prev. {j + 1}", min_value=0.0, value=0.0, step=0.01, key=f"{fk}_pv_{j}")
        vc2 = euros_para_centavos(float(ve2)) or 0
        prev_rows.append((dv.isoformat(), vc2))

    obs = st.text_area("Observações da venda", key=f"{fk}_obs_v")

    if st.button("Registar venda", type="primary", key=f"{fk}_submit"):
        if not st.session_state.venda_cliente_id:
            st.error("Selecione ou cadastre um cliente.")
            return
        if not cart:
            st.error("Adicione pelo menos um item.")
            return
        # rebuild linhas_reg for backend
        linhas_b: list[dict] = []
        for it in cart:
            meta = id_to.get(int(it["servico_id"]), {})
            nat = str(meta.get("natureza", ""))
            evt_key = "adulto" if str(it.get("evt", "Adulto")) == "Adulto" else "crianca"
            raw_val: float | None = None
            if it["disc_t"] == "Percentagem":
                raw_val = float(it["disc_pct"])
            elif it["disc_t"] == "Valor (€)":
                raw_val = float(it["disc_eur"])
            linhas_b.append(
                {
                    "servico_id": int(it["servico_id"]),
                    "quantidade": int(it["qty"]),
                    "is_bonus": bool(it["bonus"]),
                    "evento_preco": evt_key if nat == "Evento" else None,
                    "desconto_linha_tipo": (
                        "percent"
                        if it["disc_t"] == "Percentagem"
                        else "fixed"
                        if it["disc_t"] == "Valor (€)"
                        else "none"
                    ),
                    "desconto_linha_valor": raw_val,
                    "colaborador_id": it.get("colab_id"),
                }
            )
        fechar_before = st.session_state.get("venda_fechar_agendamento_id")
        ctx_before = st.session_state.get("venda_agendamento_contexto_id")
        ctx_arg = fechar_before or ctx_before
        ok_f, msg_f, vid_new = registrar_venda(
            int(st.session_state.venda_cliente_id),
            estado,  # type: ignore[arg-type]
            linhas_b,
            gtipo,
            gval,
            pag_rows,
            prev_rows,
            obs,
            agendamento_contexto_id=int(ctx_arg) if ctx_arg else None,
        )
        if ok_f:
            if fechar_before and vid_new is not None:
                agd = obter_agendamento(int(fechar_before))
                if agd and str(agd.get("modo_origem")) == "pre_venda":
                    vi_item = obter_primeiro_item_venda_por_servico(
                        int(vid_new), int(agd["servico_id"])
                    )
                    if vi_item:
                        ok_as, msg_as = associar_agendamento_pre_venda_a_item(
                            int(fechar_before), int(vi_item)
                        )
                        if ok_as:
                            st.success(msg_as)
                        else:
                            st.warning(
                                f"Venda registada, mas associação ao agendamento falhou: {msg_as}"
                            )
                    else:
                        st.warning(
                            "Venda registada, mas não foi encontrada linha com o serviço da pré-venda — associe manualmente no código ou refaça a venda."
                        )
            st.session_state.venda_cart = []
            st.session_state.venda_fv += 1
            st.session_state.venda_fechar_agendamento_id = None
            st.session_state.venda_agendamento_contexto_id = None
            st.success(msg_f)
            st.balloons()
            st.rerun()
        else:
            st.error(msg_f)
