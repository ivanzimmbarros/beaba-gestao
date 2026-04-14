"""Painel de Vendas — UI Streamlit (E07)."""

from __future__ import annotations

import html
from datetime import date, datetime

import streamlit as st

from src.modules.catalogo import (
    euros_para_centavos,
    listar_servicos_para_venda,
    resolver_snapshot_venda,
)
from src.modules.cliente import (
    atualizar_cliente,
    buscar_cliente_por_whatsapp,
    buscar_clientes_por_nif_email_telefone,
    buscar_clientes_por_prefixo_nome,
    cadastrar_cliente,
    obter_cliente_completo,
)
from src.modules.colaborador import listar_colaboradores_resumo
from src.modules.constants import SEXOS
from src.modules.nif import normalizar_nif_armazenamento
from src.modules.telefone import normalizar_telefone_legado_ou_e164
from src.modules.validators import email_valido, parse_data_iso
from src.modules.agendamento import (
    associar_agendamento_pre_venda_a_item,
    listar_agendamentos_elegiveis_associacao_linha_venda,
    obter_agendamento,
    obter_primeiro_item_venda_por_servico,
    pos_venda_associar_agendamentos_por_linha,
)
from src.modules.credito_ledger import obter_saldo_credito_cliente
from src.modules.venda import calcular_totais_venda, registrar_venda
from src.ui.telefone_widgets import (
    ler_e164_de_widgets,
    preencher_session_telefone_de_e164,
    render_grupo_telefone,
)
from src.pages.theme import get_beaba_css  # noqa: F401 — BeaBa Sereno (CSS em app.main)
from src.ui.constituicao_visual_shell import inject_constituicao_vnd_page
from src.ui.fmt_euro_constituicao import fmt_euro_centavos
from src.ui.widgets.cliente_search import CLIENTE_SEARCH_DATE_MIN, render_cliente_search_widget


def _vnd_fmt_cent(c: int | None) -> str:
    if c is None:
        return "—"
    return fmt_euro_centavos(int(c))


def _vnd_section_title_html(title: str) -> str:
    t = html.escape(title)
    return f'<div class="bea-cv-cag-h2">{t}</div>'


def _vnd_label_ag_para_combo(a: dict) -> str:
    cols = ", ".join(a.get("colaboradores_nomes") or []) or "—"
    return (
        f"#{a['id']} · {a['data_agendamento']} {a['hora_inicio']}-{a['hora_fim']} "
        f"· {a['status']} · {cols}"
    )


def _venda_slimos_from_cart(cart: list, id_to: dict) -> list[dict]:
    """Monta linhas «slim» para `calcular_totais_venda` (paridade com o painel)."""
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
    return slim_all


def _venda_read_global_discount_from_state(fk: str) -> tuple[str | None, int | None]:
    g_opt = str(st.session_state.get(f"{fk}_gopt", "Nenhum") or "Nenhum")
    gtipo: str | None = None
    gval: int | None = None
    if g_opt == "Percentagem":
        g_pct = float(st.session_state.get(f"{fk}_gpct", 0.01) or 0.01)
        gtipo = "percent"
        gval = int(round(g_pct * 100))
    elif g_opt == "Valor (€)":
        g_eur = float(st.session_state.get(f"{fk}_geur", 0.01) or 0.01)
        gtipo = "fixed"
        ge = euros_para_centavos(g_eur)
        gval = ge if ge is not None else None
    return gtipo, gval


def _venda_collect_pag_rows_from_state(
    fk: str,
    n_lin: int,
    meios_opt: list[tuple[str, str]],
    meios_labels: list[str],
) -> tuple[list[tuple[str, int]], list[str]]:
    pag_rows: list[tuple[str, int]] = []
    obs_pay_notes: list[str] = []
    for j in range(n_lin):
        lbl_m = str(st.session_state.get(f"{fk}_pay_meio_{j}", meios_labels[0]) or meios_labels[0])
        try:
            meio_code = meios_opt[meios_labels.index(lbl_m)][0]
        except ValueError:
            meio_code = meios_opt[0][0]
        tipo_pg = str(st.session_state.get(f"{fk}_pay_tipo_{j}", "Integral") or "Integral")
        if tipo_pg == "Parcelado":
            nparc = int(st.session_state.get(f"{fk}_pay_nparc_{j}", 2) or 2)
        else:
            nparc = 1
        ve = float(st.session_state.get(f"{fk}_pay_val_{j}", 0.0) or 0.0)
        vc = euros_para_centavos(ve) or 0
        if vc > 0:
            pag_rows.append((meio_code, vc))
            if tipo_pg == "Parcelado" and nparc >= 2:
                obs_pay_notes.append(
                    f"[Pagamento] {lbl_m} em {nparc}× — total {_vnd_fmt_cent(euros_para_centavos(ve) or 0)}."
                )
    return pag_rows, obs_pay_notes


def _venda_finance_snapshot(
    fk: str,
    cart: list,
    id_to: dict,
    cli_id: int | None,
    meios_opt: list[tuple[str, str]],
    meios_labels: list[str],
) -> dict:
    """
    Totais e «A distribuir» a partir do carrinho e do estado dos widgets (rerun anterior).
    Usado no card de status superior e na secção de pagamento.
    """
    gtipo, gval = _venda_read_global_discount_from_state(fk)
    slim_all = _venda_slimos_from_cart(cart, id_to)
    ok_t = False
    tot_preview = None
    if slim_all:
        ok_t, _, tot_preview = calcular_totais_venda(
            slim_all,
            desconto_global_tipo=gtipo,
            desconto_global_valor=gval,
        )
    n_lin = max(1, min(10, int(st.session_state.get("venda_pay_n_linhas", 1))))
    pag_rows, _obs = _venda_collect_pag_rows_from_state(fk, n_lin, meios_opt, meios_labels)
    tf_cent = 0
    cab_m = 0
    liq_cent = 0
    if ok_t and tot_preview is not None:
        tf_cent = int(tot_preview["total_final_centavos"])
        abat_cred_eur = float(st.session_state.get(f"{fk}_abat_cred", 0.0) or 0.0)
        cab_try = euros_para_centavos(abat_cred_eur) or 0
        if cli_id:
            saldo_c2 = obter_saldo_credito_cliente(int(cli_id))
            cab_m = min(max(0, cab_try), max(0, saldo_c2), tf_cent)
        else:
            cab_m = 0
        liq_cent = max(0, tf_cent - cab_m)
    sp_cent = sum(v for _, v in pag_rows)
    a_distribuir_cent = liq_cent - sp_cent
    return {
        "ok_t": ok_t,
        "tot_preview": tot_preview,
        "tf_cent": tf_cent,
        "cab_m": cab_m,
        "liq_cent": liq_cent,
        "sp_cent": sp_cent,
        "a_distribuir_cent": a_distribuir_cent,
        "pedido_txt": _vnd_fmt_cent(liq_cent),
        "distrib_txt": _vnd_fmt_cent(sp_cent),
        "ad_txt": _vnd_fmt_cent(abs(a_distribuir_cent)),
        "pag_rows": pag_rows,
        "obs_pay_notes": _obs,
    }


_VENDA_MEIOS_OPT: list[tuple[str, str]] = [
    ("dinheiro", "Dinheiro"),
    ("mbway", "MBWay"),
    ("cartao_credito", "Cartão de crédito"),
    ("iban", "Transferência (IBAN)"),
]
_VENDA_MEIOS_LABELS = [x[1] for x in _VENDA_MEIOS_OPT]


def _html_comanda_item_minimal(*, nome_e: str, nat_e: str, val_e: str) -> str:
    """
    Card de linha só com nome, badge sálvia e valor bordeaux.
    Montagem por concatenação (evita f-strings que quebram `{` do CSS/HTML no Streamlit).
    """
    return (
        '<div class="bea-venda-comanda-item bea-comanda-min">'
        '<div class="bea-comanda-min-row">'
        "<div>"
        '<span class="bea-com-nome">'
        + nome_e
        + "</span><br/>"
        '<span class="bea-com-badge">'
        + nat_e
        + "</span>"
        "</div>"
        '<div class="bea-com-val-col">'
        '<div class="bea-com-val">'
        + val_e
        + "</div>"
        "</div>"
        "</div>"
        "</div>"
    )


def _render_venda_status_card_superior(snap: dict) -> None:
    """Card único de estado: totais compactos + A distribuir em destaque (bordeaux)."""
    ad = int(snap["a_distribuir_cent"])
    ad_val_cls = "bea-vs-sem-ad-val"
    ad_lbl_cls = "bea-vs-sem-ad-lbl"
    if ad > 0:
        ad_label = "A distribuir"
    elif ad < 0:
        ad_val_cls += " bea-ad-excesso"
        ad_lbl_cls += " bea-ad-lbl-warn"
        ad_label = "Excesso sobre o pedido"
    else:
        ad_val_cls += " bea-ad-zero"
        ad_label = "A distribuir"
    cab_m = int(snap["cab_m"])
    cab_html = ""
    if cab_m > 0:
        cab_e = html.escape(_vnd_fmt_cent(cab_m))
        cab_html = (
            f'<p class="bea-vs-sem-foot">Abatimento de crédito aplicado: <strong>{cab_e}</strong></p>'
        )
    ped_e = html.escape(str(snap["pedido_txt"]))
    reg_e = html.escape(str(snap["distrib_txt"]))
    adt_e = html.escape(str(snap["ad_txt"]))
    lbl_ad_e = html.escape(ad_label)
    inner = (
        '<div class="bea-cv-vnd-status-surface">'
        '<div class="bea-proto-scope">'
        '<div class="bea-venda-semaforo">'
        '<p class="bea-vs-sem-kicker">Estado da venda</p>'
        '<div class="bea-vs-sem-unified-row">'
        '<div class="bea-vs-sem-metrics-pair">'
        "<div>"
        '<span class="bea-vs-sem-lbl">Total pedido</span>'
        '<div class="bea-vs-sem-val-bdx">'
        + ped_e
        + "</div>"
        "</div>"
        "<div>"
        '<span class="bea-vs-sem-lbl">Total registado</span>'
        '<div class="bea-vs-sem-val-bdx">'
        + reg_e
        + "</div>"
        "</div>"
        "</div>"
        '<div class="bea-vs-sem-ad-wrap">'
        '<div class="'
        + ad_lbl_cls
        + '">'
        + lbl_ad_e
        + "</div>"
        '<div class="'
        + ad_val_cls
        + '">'
        + adt_e
        + "</div>"
        "</div>"
        "</div>"
        + cab_html
        + "</div>"
        "</div>"
        "</div>"
    )
    st.markdown(inner, unsafe_allow_html=True)


def _prime_cliente_form(prefix: str, d: dict) -> None:
    """Preenche widgets Streamlit a partir de ficha carregada."""
    st.session_state[f"{prefix}_nome"] = d["nome"]
    preencher_session_telefone_de_e164(f"{prefix}_tel", str(d.get("whatsapp") or ""))
    st.session_state[f"{prefix}_docintl"] = bool(d.get("identificacao_internacional"))
    st.session_state[f"{prefix}_nif"] = str(d.get("nif_ou_documento") or "")
    dn_t = d.get("data_nascimento")
    if dn_t and parse_data_iso(str(dn_t)[:10]):
        st.session_state[f"{prefix}_dnasc"] = datetime.strptime(str(dn_t)[:10], "%Y-%m-%d").date()
    else:
        st.session_state[f"{prefix}_dnasc"] = date(1990, 1, 1)
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
    for j, row in enumerate(filhos):
        fn, ida, sx = row[0], row[1], row[2]
        st.session_state[f"{prefix}_fn_{j}"] = fn
        st.session_state[f"{prefix}_fi_{j}"] = int(ida)
        st.session_state[f"{prefix}_fs_{j}"] = sx
        dn = row[3] if len(row) >= 4 else None
        if dn and parse_data_iso(str(dn)[:10]):
            st.session_state[f"{prefix}_fhas_{j}"] = True
            st.session_state[f"{prefix}_fdn_{j}"] = datetime.strptime(str(dn)[:10], "%Y-%m-%d").date()
        else:
            st.session_state[f"{prefix}_fhas_{j}"] = False
    em = d.get("contatos_emergencia") or []
    st.session_state[f"{prefix}_nem"] = max(1, len(em))
    for j, (en, et) in enumerate(em):
        st.session_state[f"{prefix}_em_n_{j}"] = en
        preencher_session_telefone_de_e164(f"{prefix}_emerg_{j}", str(et or ""))


def _vnd_tratar_sugestao_nome_clicada(cid: int, fk: str) -> None:
    d = obter_cliente_completo(int(cid))
    if not d:
        st.error("Cliente não encontrado.")
        return
    st.session_state.venda_cliente_id = int(cid)
    st.session_state._vnda_prime = {"prefix": f"{fk}_vc", "data": d}
    st.session_state["vnd_busca_nome"] = str(d.get("nome") or "")
    st.session_state["vnd_busca_nif"] = str(d.get("nif_ou_documento") or "")
    st.session_state["vnd_busca_email"] = str(d.get("email") or "")
    st.session_state["vnd_busca_tel_txt"] = str(d.get("whatsapp") or "").strip()
    st.session_state.pop("vnd_busca_cands", None)


def _collect_filhos(
    prefix: str, tem: bool, qtd: int
) -> list[tuple[str, int, str] | tuple[str, int, str, str]]:
    if not tem:
        return []
    out: list[tuple[str, int, str] | tuple[str, int, str, str]] = []
    for j in range(qtd):
        fn = st.session_state.get(f"{prefix}_fn_{j}", "")
        ida = int(st.session_state.get(f"{prefix}_fi_{j}", 0))
        sx = st.session_state.get(f"{prefix}_fs_{j}", SEXOS[0])
        if st.session_state.get(f"{prefix}_fhas_{j}", False):
            d_obj = st.session_state.get(f"{prefix}_fdn_{j}")
            if d_obj is not None and hasattr(d_obj, "isoformat"):
                out.append((str(fn), ida, str(sx), d_obj.isoformat()))
                continue
        out.append((str(fn), ida, str(sx)))
    return out


def _render_venda_novo_cliente_form(fk: str) -> None:
    """Cadastro completo de novo cliente no contexto da venda (expander)."""
    pn = f"{fk}_nv"
    st.text_input("Nome completo *", key=f"{pn}_nome")
    st.checkbox(
        "Documento de identificação **não** é NIF português",
        key=f"{pn}_docintl",
    )
    st.text_input("NIF ou documento *", key=f"{pn}_nif")
    st.date_input(
        "Data de nascimento *",
        min_value=CLIENTE_SEARCH_DATE_MIN,
        max_value=datetime.now().date(),
        format="DD/MM/YYYY",
        key=f"{pn}_dnasc",
    )
    render_grupo_telefone(st, prefix=f"{pn}_tel", label="Contacto principal *")
    st.text_input("Email *", key=f"{pn}_email")
    sxn = st.selectbox("Sexo *", SEXOS, key=f"{pn}_sexo")
    gn: bool | None = None
    dpn: str | None = None
    if sxn == "Feminino":
        gn = st.radio("Está grávida? *", ["Não", "Sim"], horizontal=True, key=f"{pn}_grav") == "Sim"
        if gn:
            dpn_d = st.date_input(
                "Estimativa DPP *",
                key=f"{pn}_parto",
                format="DD/MM/YYYY",
                min_value=CLIENTE_SEARCH_DATE_MIN,
            )
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
            fhn = st.checkbox(
                "Data nasc. (opcional)",
                key=f"{pn}_fhas_{j}",
            )
            if fhn:
                st.date_input(
                    f"Data nasc. filho {j + 1}",
                    max_value=datetime.now().date(),
                    min_value=CLIENTE_SEARCH_DATE_MIN,
                    format="DD/MM/YYYY",
                    key=f"{pn}_fdn_{j}",
                )
    nemn = int(st.number_input("Contactos emergência (0–10)", 0, 10, 0, key=f"{pn}_nem"))
    for j in range(nemn):
        st.text_input(f"Emerg. nome {j + 1}", key=f"{pn}_em_n_{j}")
        render_grupo_telefone(
            st,
            prefix=f"{pn}_emerg_{j}",
            label=f"Emerg. telefone {j + 1}",
        )
    st.text_area("Observações", key=f"{pn}_obs")
    if st.button("Cadastrar e usar este cliente", key=f"{pn}_cad"):
        ok_tn, tel_nv, err_nv = ler_e164_de_widgets(f"{pn}_tel")
        if not ok_tn:
            st.error(err_nv)
        else:
            ok_en, err_en, el = _collect_emerg_e164(pn, nemn)
            if not ok_en:
                st.error(err_en)
            else:
                fl = _collect_filhos(pn, temfn, qfn if temfn else 0)
                dno_n = st.session_state.get(f"{pn}_dnasc")
                dns_n = (
                    dno_n.isoformat()
                    if dno_n is not None and hasattr(dno_n, "isoformat")
                    else ""
                )
                ok_c, msg_c = cadastrar_cliente(
                    nome=str(st.session_state.get(f"{pn}_nome", "")),
                    numero_contato=tel_nv,
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
                    nif=str(st.session_state.get(f"{pn}_nif", "")),
                    documento_identificacao_internacional=bool(
                        st.session_state.get(f"{pn}_docintl")
                    ),
                    data_nascimento=dns_n,
                )
                if ok_c:
                    cid2 = buscar_cliente_por_whatsapp(tel_nv)
                    st.session_state.venda_cliente_id = cid2
                    st.session_state.venda_fv += 1
                    st.success(msg_c)
                    st.rerun()
                else:
                    st.error(msg_c)


def _render_venda_editar_cliente_form(cli_id: int, fk: str) -> None:
    """Formulário de edição de ficha dentro do expander na venda."""
    p = f"{fk}_vc"
    st.text_input("Nome completo *", key=f"{p}_nome")
    st.checkbox(
        "Documento de identificação **não** é NIF português",
        key=f"{p}_docintl",
    )
    st.text_input("NIF ou documento *", key=f"{p}_nif")
    st.date_input(
        "Data de nascimento *",
        min_value=CLIENTE_SEARCH_DATE_MIN,
        max_value=datetime.now().date(),
        format="DD/MM/YYYY",
        key=f"{p}_dnasc",
    )
    render_grupo_telefone(st, prefix=f"{p}_tel", label="Contacto principal *")
    st.text_input("Email *", key=f"{p}_email")
    sx = st.selectbox("Sexo *", SEXOS, key=f"{p}_sexo")
    gravida: bool | None = None
    data_parto: str | None = None
    if sx == "Feminino":
        g = st.radio("Está grávida? *", ["Não", "Sim"], horizontal=True, key=f"{p}_grav")
        gravida = g == "Sim"
        if gravida:
            dpp = st.date_input(
                "Estimativa de data de parto *",
                key=f"{p}_parto",
                format="DD/MM/YYYY",
                min_value=CLIENTE_SEARCH_DATE_MIN,
            )
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
        st.session_state.setdefault(f"{p}_qfil", 1)
        qfil = int(
            st.number_input(
                "Quantos filhos? *",
                min_value=1,
                max_value=20,
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
            fh = st.checkbox(
                "Data de nascimento (opcional)",
                key=f"{p}_fhas_{j}",
            )
            if fh:
                st.date_input(
                    "Data de nascimento",
                    max_value=datetime.now().date(),
                    min_value=CLIENTE_SEARCH_DATE_MIN,
                    format="DD/MM/YYYY",
                    key=f"{p}_fdn_{j}",
                )
    st.session_state.setdefault(f"{p}_nem", 1)
    nem = int(
        st.number_input(
            "Linhas de contacto de emergência (0–10)",
            min_value=0,
            max_value=10,
            key=f"{p}_nem",
        )
    )
    for j in range(nem):
        st.text_input(f"Nome emerg. {j + 1}", key=f"{p}_em_n_{j}")
        render_grupo_telefone(
            st,
            prefix=f"{p}_emerg_{j}",
            label=f"Telefone emerg. {j + 1}",
        )
    st.text_area("Observações", key=f"{p}_obs")
    if st.button("Guardar alterações na ficha", key=f"{p}_save"):
        ok_t, tel_e164, err_t = ler_e164_de_widgets(f"{p}_tel")
        if not ok_t:
            st.error(err_t)
        else:
            ok_em, err_em, em_l = _collect_emerg_e164(p, nem)
            if not ok_em:
                st.error(err_em)
            else:
                filhos_l = _collect_filhos(p, temf, qfil if temf else 0)
                dno = st.session_state.get(f"{p}_dnasc")
                dns = (
                    dno.isoformat()
                    if dno is not None and hasattr(dno, "isoformat")
                    else ""
                )
                ok_u, msg_u = atualizar_cliente(
                    int(cli_id),
                    nome=str(st.session_state.get(f"{p}_nome", "")),
                    numero_contato=tel_e164,
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
                    nif=str(st.session_state.get(f"{p}_nif", "")),
                    documento_identificacao_internacional=bool(
                        st.session_state.get(f"{p}_docintl")
                    ),
                    data_nascimento=dns,
                )
                if ok_u:
                    st.success(msg_u)
                else:
                    st.error(msg_u)


def _collect_emerg_e164(prefix: str, n: int) -> tuple[bool, str, list[tuple[str, str]]]:
    out: list[tuple[str, str]] = []
    for j in range(n):
        en = str(st.session_state.get(f"{prefix}_em_n_{j}", "") or "").strip()
        ok_t, e164, err = ler_e164_de_widgets(f"{prefix}_emerg_{j}")
        if not en and not ok_t:
            continue
        if not en or not ok_t:
            return False, err or "❌ Contacto de emergência incompleto.", []
        out.append((en, e164))
    return True, "", out


def render_page_vendas(
    *,
    render_back_and_breadcrumb,
) -> None:
    inject_constituicao_vnd_page()
    render_back_and_breadcrumb(["Home", "Vendas", "Registo"], back_key="bea_back_vendas")
    st.markdown(
        '<h1 class="bea-cv-cag-h1">Painel de Vendas</h1>',
        unsafe_allow_html=True,
    )

    if "venda_fv" not in st.session_state:
        st.session_state.venda_fv = 0
    fv = st.session_state.venda_fv
    fk = f"vnd_{fv}"

    if "venda_cliente_id" not in st.session_state:
        st.session_state.venda_cliente_id = None
    if "venda_cart" not in st.session_state:
        st.session_state.venda_cart = []
    if "venda_pay_n_linhas" not in st.session_state:
        st.session_state.venda_pay_n_linhas = 1
    if "venda_fechar_agendamento_id" not in st.session_state:
        st.session_state.venda_fechar_agendamento_id = None
    if "venda_agendamento_contexto_id" not in st.session_state:
        st.session_state.venda_agendamento_contexto_id = None

    sug_vnd = st.session_state.pop("vnd_busca_suggestion_apply_id", None)
    if sug_vnd is not None:
        _vnd_tratar_sugestao_nome_clicada(int(sug_vnd), fk)

    cat = listar_servicos_para_venda()
    id_to = {int(c["id"]): c for c in cat} if cat else {}

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

    snap_topo = _venda_finance_snapshot(
        fk,
        list(st.session_state.venda_cart),
        id_to,
        st.session_state.venda_cliente_id,
        _VENDA_MEIOS_OPT,
        _VENDA_MEIOS_LABELS,
    )
    _render_venda_status_card_superior(snap_topo)

    st.markdown(
        '<div class="bea-cv-cag-gap" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    st.markdown(_vnd_section_title_html("1. Pesquisa de clientes"), unsafe_allow_html=True)
    if st.session_state.pop("vnd_busca_clear_pending", False):
        st.session_state["vnd_busca_nome"] = ""
        st.session_state["vnd_busca_nome_sug_list"] = []
        st.session_state["vnd_busca_nif"] = ""
        st.session_state["vnd_busca_email"] = ""
        st.session_state["vnd_busca_tel_txt"] = ""
        st.session_state.pop("vnd_busca_docintl", None)

    vnd_busca_clicked = render_cliente_search_widget(
        key_prefix="vnd_busca",
        button_type="secondary",
        minimal=True,
        pesquisa_unificada=True,
    )

    if vnd_busca_clicked:
        nome_s = str(st.session_state.get("vnd_busca_nome", "") or "").strip()
        nif_s = str(st.session_state.get("vnd_busca_nif", "") or "").strip()
        em_s = str(st.session_state.get("vnd_busca_email", "") or "").strip()
        tel_raw = str(st.session_state.get("vnd_busca_tel_txt", "") or "").strip()
        use_tel = normalizar_telefone_legado_ou_e164(tel_raw) if tel_raw else ""

        msg_err: str | None = None
        if not nome_s and not nif_s and not em_s and not tel_raw:
            msg_err = "Indique nome, NIF, email ou telefone."
        elif em_s and not email_valido(em_s):
            msg_err = "❌ Email inválido para pesquisa."
        elif tel_raw and not use_tel:
            msg_err = "❌ Telefone inválido (ex.: +351912345678)."
        elif nif_s:
            ok_nf, msg_nf, _vx = normalizar_nif_armazenamento(
                nif_s, documento_identificacao_internacional=False
            )
            if not ok_nf:
                msg_err = msg_nf
        if msg_err:
            st.error(msg_err)
        else:
            merged: dict[int, str] = {}
            if nome_s:
                for cid, nm in buscar_clientes_por_prefixo_nome(nome_s, limit=80):
                    merged[int(cid)] = str(nm)
            for cid, nm in buscar_clientes_por_nif_email_telefone(
                nif=nif_s,
                email=em_s,
                telefone=use_tel,
                documento_internacional=False,
            ):
                merged[int(cid)] = str(nm)
            cands = sorted(merged.items(), key=lambda x: (x[1].lower(), x[0]))
            if len(cands) == 0:
                st.warning(
                    "Nenhum cliente encontrado. Abra **Novo cliente** no expander abaixo."
                )
                st.session_state.pop("vnd_busca_cands", None)
                st.session_state.venda_cliente_id = None
            elif len(cands) == 1:
                cid = cands[0][0]
                d = obter_cliente_completo(cid)
                if not d:
                    st.error("Cliente não encontrado.")
                else:
                    st.session_state.venda_cliente_id = cid
                    st.session_state._vnda_prime = {"prefix": f"{fk}_vc", "data": d}
                    st.session_state.pop("vnd_busca_cands", None)
                    st.session_state.vnd_busca_clear_pending = True
                    st.success(f"Cliente encontrado (#{cid}). Ficha carregada.")
                    st.rerun()
            else:
                st.session_state.vnd_busca_cands = cands
                st.info(f"**{len(cands)}** clientes encontrados — seleccione abaixo.")
                st.rerun()

    cands_v = st.session_state.get("vnd_busca_cands")
    if cands_v and len(cands_v) > 1:
        labels_v = [f"{nome} (#{cid})" for cid, nome in cands_v]
        pick_v = st.selectbox("Seleccione o cliente", labels_v, key="vnd_busca_pick_label")
        if st.button("Carregar cliente seleccionado", key="vnd_busca_apply_pick"):
            idx_v = labels_v.index(pick_v)
            cid_v = cands_v[idx_v][0]
            d_v = obter_cliente_completo(cid_v)
            if not d_v:
                st.error("Cliente não encontrado.")
            else:
                st.session_state.venda_cliente_id = cid_v
                st.session_state._vnda_prime = {"prefix": f"{fk}_vc", "data": d_v}
                st.session_state.pop("vnd_busca_cands", None)
                st.session_state.vnd_busca_clear_pending = True
                st.rerun()

    _c1, _c2 = st.columns([3, 1])
    with _c2:
        st.write("")
        if st.session_state.venda_cliente_id and st.button(
            "Limpar seleção", key=f"{fk}_clr_cli"
        ):
            st.session_state.venda_cliente_id = None
            st.session_state.pop("vnd_busca_cands", None)
            st.session_state.vnd_busca_clear_pending = True
            st.rerun()

    cli_id = st.session_state.venda_cliente_id

    if cli_id:
        saldo_loja = obter_saldo_credito_cliente(int(cli_id))
        st.info(
            f"**#{cli_id}** · crédito de loja: **{_vnd_fmt_cent(saldo_loja)}**."
        )
        with st.expander("Editar ficha do cliente", expanded=False):
            _render_venda_editar_cliente_form(int(cli_id), fk)
    else:
        with st.expander("Novo cliente — cadastro completo", expanded=False):
            _render_venda_novo_cliente_form(fk)

    st.markdown(
        '<div class="bea-cv-cag-gap" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    st.markdown(_vnd_section_title_html("2. Serviços requisitados"), unsafe_allow_html=True)
    if not cat:
        st.error("Sem serviços ativos. Abra o Catálogo.")
        return
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
        n_cart = len(cart)
        for row_start in range(0, n_cart, 3):
            grid_cols = st.columns(3)
            for col_i in range(3):
                idx = row_start + col_i
                if idx >= n_cart:
                    break
                it = cart[idx]
                with grid_cols[col_i]:
                    meta = id_to.get(int(it["servico_id"]), {})
                    nat = str(meta.get("natureza", ""))
                    nome_svc = str(meta.get("nome", "?"))
                    q0 = int(it.get("qty", 1))
                    evt_key0 = "adulto" if str(it.get("evt", "Adulto")) == "Adulto" else "crianca"
                    ok_hdr, _msg_hdr, snap_hdr = resolver_snapshot_venda(
                        int(it["servico_id"]),
                        evento_preco=evt_key0 if nat == "Evento" else None,
                        is_bonus=bool(it.get("bonus", False)),
                    )
                    if ok_hdr:
                        bruto_hdr = q0 * int(snap_hdr["preco_unitario_centavos"])
                        valor_card = _vnd_fmt_cent(bruto_hdr)
                    else:
                        valor_card = "—"
                    nome_e = html.escape(nome_svc)
                    nat_e = html.escape(nat) if nat else "—"
                    val_e = html.escape(valor_card)
                    row_html = _html_comanda_item_minimal(nome_e=nome_e, nat_e=nat_e, val_e=val_e)

                    h_left, h_x = st.columns([5, 1])
                    with h_left:
                        st.markdown(row_html, unsafe_allow_html=True)
                    with h_x:
                        st.caption("")
                        if st.button("✕", key=f"{fk}_rm_{idx}", help="Remover este item"):
                            to_remove = idx

                    with st.expander(f"⋯ Item {idx + 1}", expanded=False):
                        c_a, c_c = st.columns([1, 2])
                        with c_a:
                            st.caption("Quantidade")
                            it["qty"] = int(
                                st.number_input(
                                    "qty",
                                    min_value=1,
                                    max_value=999,
                                    value=int(it.get("qty", 1)),
                                    key=f"{fk}_q_{idx}",
                                    label_visibility="collapsed",
                                )
                            )
                        with c_c:
                            cc1, cc2 = st.columns(2)
                            with cc1:
                                st.session_state.setdefault(f"{fk}_bon_{idx}", bool(it.get("bonus")))
                                it["bonus"] = st.checkbox(
                                    "Bónus (preço 0)",
                                    key=f"{fk}_bon_{idx}",
                                )
                            with cc2:
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
                            (f"{nome} (#{cid})", int(cid))
                            for cid, nome in listar_colaboradores_resumo()
                        )
                        _sel_col = st.selectbox(
                            "Colaborador (opcional)",
                            options=_colab_opts,
                            format_func=lambda x: x[0],
                            key=f"{fk}_col_{idx}",
                        )
                        it["colab_id"] = _sel_col[1]
                        if cli_id and nat in ("Sessão", "Coworking", "Evento"):
                            if int(it.get("qty", 1)) != 1:
                                st.caption(
                                    "Para associar um agendamento a esta linha, use **quantidade 1**."
                                )
                            else:
                                ag_opts = listar_agendamentos_elegiveis_associacao_linha_venda(
                                    cliente_id=int(cli_id),
                                    servico_id=int(it["servico_id"]),
                                )
                                _vals = ["__none__"] + [str(int(a["id"])) for a in ag_opts]

                                def _fmt_ag_opt(v: str) -> str:
                                    if v == "__none__":
                                        return "Sem agendamento"
                                    for agx in ag_opts:
                                        if str(int(agx["id"])) == v:
                                            return _vnd_label_ag_para_combo(agx)
                                    return v

                                st.selectbox(
                                    "Agendamento a associar (opcional)",
                                    options=_vals,
                                    format_func=_fmt_ag_opt,
                                    key=f"{fk}_aglin_{idx}",
                                    help="Liga esta linha da venda a um compromisso em pré-venda do mesmo serviço.",
                                )
                        elif nat == "Produto":
                            st.caption("Produto: venda directa — sem associação a agendamento.")
                        elif nat == "Pacote":
                            st.caption(
                                "Pacote: consumos na agenda seguem a venda do pacote; "
                                "conclusão exige liquidação integral da venda (política restritiva)."
                            )
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
                            st.markdown(
                                f"**Cálculo:** {snap['unidade_medida']} × {q} → subtotal bruto "
                                f"**{_vnd_fmt_cent(bruto)}**"
                            )
                        else:
                            st.warning(msg_r)
        if to_remove is not None:
            st.session_state.venda_cart.pop(to_remove)
            st.rerun()

    st.markdown(
        '<div class="bea-cv-cag-gap" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    st.markdown(_vnd_section_title_html("3. Desconto sobre o total"), unsafe_allow_html=True)
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

    ok_t = False
    tot_preview = None
    if cart:
        slim_all = _venda_slimos_from_cart(cart, id_to)
        ok_t, msg_t, tot_preview = calcular_totais_venda(
            slim_all,
            desconto_global_tipo=gtipo,
            desconto_global_valor=gval,
        )
        if ok_t and tot_preview:
            st.success(
                f"**Subtotal (bruto):** {_vnd_fmt_cent(tot_preview['subtotal_bruto_centavos'])} · "
                f"**Após linhas:** {_vnd_fmt_cent(tot_preview['subtotal_apos_descontos_linha_centavos'])} · "
                f"**Desconto global:** {_vnd_fmt_cent(tot_preview['desconto_global_centavos_aplicado'])} · "
                f"**Total final:** {_vnd_fmt_cent(tot_preview['total_final_centavos'])}"
            )
        elif not ok_t:
            st.error(msg_t)

    st.markdown(
        '<div class="bea-cv-cag-gap" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    st.markdown(_vnd_section_title_html("4. Pagamento"), unsafe_allow_html=True)

    abat_cred_eur = 0.0
    if cli_id:
        saldo_ab = obter_saldo_credito_cliente(int(cli_id))
        abat_cred_eur = float(
            st.number_input(
                "Abatimento de crédito de loja (€)",
                min_value=0.0,
                value=0.0,
                step=0.01,
                key=f"{fk}_abat_cred",
                help=f"Máximo sugerido: saldo {_vnd_fmt_cent(saldo_ab)}.",
            )
        )

    meios_labels = _VENDA_MEIOS_LABELS

    n_lin = max(1, min(10, int(st.session_state.venda_pay_n_linhas)))

    for j in range(n_lin):
        r1, r2, r3, r4 = st.columns([1.55, 1.05, 0.95, 1.1])
        lv = "visible" if j == 0 else "collapsed"
        with r1:
            st.selectbox(
                "Forma de Pagamento",
                meios_labels,
                key=f"{fk}_pay_meio_{j}",
                label_visibility=lv,
            )
        with r2:
            tipo_pg = st.selectbox(
                "Modalidade de Pagamento",
                ["Integral", "Parcelado"],
                key=f"{fk}_pay_tipo_{j}",
                label_visibility=lv,
            )
        with r3:
            if tipo_pg == "Parcelado":
                nparc = int(
                    st.number_input(
                        "Qtd parcelas",
                        min_value=2,
                        max_value=60,
                        value=2,
                        step=1,
                        key=f"{fk}_pay_nparc_{j}",
                        label_visibility=lv,
                    )
                )
            else:
                nparc = 1
                st.caption("—")
        with r4:
            st.number_input(
                "Valor (€)",
                min_value=0.0,
                value=0.0,
                step=0.01,
                key=f"{fk}_pay_val_{j}",
                label_visibility=lv,
            )

    snap_fin = _venda_finance_snapshot(
        fk, cart, id_to, cli_id, _VENDA_MEIOS_OPT, _VENDA_MEIOS_LABELS
    )
    a_distribuir_cent = int(snap_fin["a_distribuir_cent"])
    pag_rows = snap_fin["pag_rows"]
    obs_pay_notes = snap_fin["obs_pay_notes"]

    if st.button(
        "➕ Adicionar outro meio de pagamento",
        type="secondary",
        key=f"{fk}_pay_add",
    ):
        st.session_state.venda_pay_n_linhas = min(10, n_lin + 1)
        st.rerun()

    if cli_id and int(snap_fin.get("cab_m", 0) or 0) > 0:
        st.caption(
            f"Total da venda (antes de abatimento): **{_vnd_fmt_cent(snap_fin['tf_cent'])}** · "
            f"Crédito abatido: **{_vnd_fmt_cent(int(snap_fin['cab_m']))}**"
        )

    if a_distribuir_cent < 0:
        st.warning(
            f"A soma dos meios excede o total a liquidar em **{_vnd_fmt_cent(-a_distribuir_cent)}**."
        )

    obs = st.text_area("Observações da venda", key=f"{fk}_obs_v")

    pode_finalizar = (
        bool(ok_t)
        and tot_preview is not None
        and bool(st.session_state.venda_cliente_id)
        and bool(cart)
        and a_distribuir_cent == 0
    )

    if st.button(
        "FINALIZAR VENDA",
        type="primary",
        key=f"{fk}_submit",
        disabled=not pode_finalizar,
    ):
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
        cab_reg = 0
        if (
            st.session_state.venda_cliente_id
            and ok_t
            and tot_preview is not None
        ):
            tfc = int(tot_preview["total_final_centavos"])
            cab_try_r = euros_para_centavos(float(abat_cred_eur)) or 0
            sd = obter_saldo_credito_cliente(int(st.session_state.venda_cliente_id))
            cab_reg = min(max(0, cab_try_r), max(0, sd), tfc)
        ox = "\n".join(obs_pay_notes).strip()
        obs_fin = (str(obs or "").strip() + ("\n" + ox if ox else "")).strip()
        ag_plan: list[int | None] = []
        for idx, it in enumerate(cart):
            meta_i = id_to.get(int(it["servico_id"]), {})
            nat_i = str(meta_i.get("natureza", ""))
            if (
                st.session_state.venda_cliente_id
                and nat_i in ("Sessão", "Coworking", "Evento")
                and int(it.get("qty", 1)) == 1
            ):
                sel_ag = str(st.session_state.get(f"{fk}_aglin_{idx}", "__none__") or "__none__")
                ag_plan.append(None if sel_ag == "__none__" else int(sel_ag))
            else:
                ag_plan.append(None)
        ok_f, msg_f, vid_new = registrar_venda(
            int(st.session_state.venda_cliente_id),
            "integral",
            linhas_b,
            gtipo,
            gval,
            pag_rows,
            [],
            obs_fin,
            agendamento_contexto_id=int(ctx_arg) if ctx_arg else None,
            credito_abatido_centavos=int(cab_reg),
        )
        if ok_f:
            if vid_new is not None and st.session_state.venda_cliente_id:
                msgs_pv = pos_venda_associar_agendamentos_por_linha(
                    venda_id=int(vid_new),
                    cliente_id=int(st.session_state.venda_cliente_id),
                    agendamento_ids_por_linha=ag_plan,
                )
                for ln in msgs_pv:
                    if not ln:
                        continue
                    if ln.startswith("❌"):
                        st.error(ln)
                    elif ln.startswith("⚠️") or ln.startswith("ℹ️"):
                        st.warning(ln)
                    else:
                        st.success(ln)
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
            st.session_state.venda_pay_n_linhas = 1
            st.session_state.venda_fv += 1
            st.session_state.venda_fechar_agendamento_id = None
            st.session_state.venda_agendamento_contexto_id = None
            st.success(msg_f)
            st.balloons()
            st.rerun()
        else:
            st.error(msg_f)
