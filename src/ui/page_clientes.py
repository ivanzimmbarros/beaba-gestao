"""Gestão de clientes — UI Streamlit (ficha digital em cards + grelha de resultados)."""

from __future__ import annotations

import html
from datetime import date, datetime

import streamlit as st

from src.pages.theme import get_beaba_css  # noqa: F401 — BeaBa Sereno (CSS em app.main)
from src.modules.catalogo import centavos_para_texto_euros
from src.modules.cliente import (
    atualizar_cliente,
    buscar_clientes_por_nif_email_telefone,
    cadastrar_cliente,
    listar_clientes_resumo_com_credito,
    listar_vendas_resumo_cliente,
    obter_cliente_completo,
)
from src.modules.credito_ledger import obter_saldo_credito_cliente
from src.modules.constants import SEXOS
from src.modules.nif import normalizar_nif_armazenamento
from src.modules.telefone import normalizar_telefone_legado_ou_e164
from src.modules.validators import email_valido, parse_data_iso
from src.ui.telefone_widgets import (
    ler_e164_de_widgets,
    preencher_session_telefone_de_e164,
    render_grupo_telefone,
)
from src.ui.widgets.cliente_search import CLIENTE_SEARCH_DATE_MIN, render_cliente_search_widget


def _html_cli_result_card(*, nome_e: str, sub_e: str) -> str:
    return (
        '<div class="bea-proto-scope">'
        '<div class="bea-venda-comanda-item bea-comanda-min">'
        '<p style="margin:0 0 6px 0;text-align:right;font-size:0.95rem;opacity:0.5;">👤</p>'
        '<span class="bea-com-nome">'
        + nome_e
        + "</span><br/>"
        '<span class="bea-com-badge">'
        + sub_e
        + "</span>"
        "</div></div>"
    )


def _carregar_ficha_em_formulario(fk: str, d: dict) -> None:
    st.session_state[f"{fk}_nome"] = d["nome"]
    st.session_state[f"{fk}_docintl"] = bool(d.get("identificacao_internacional"))
    st.session_state[f"{fk}_nif"] = str(d.get("nif_ou_documento") or "")
    preencher_session_telefone_de_e164(f"{fk}_tel_pri", str(d.get("whatsapp") or ""))
    st.session_state[f"{fk}_email"] = d["email"]
    st.session_state[f"{fk}_sexo"] = d["sexo"]
    st.session_state[f"{fk}_rua"] = d["endereco_rua"]
    st.session_state[f"{fk}_numero"] = d["endereco_numero"]
    st.session_state[f"{fk}_comp"] = d["endereco_complemento"]
    st.session_state[f"{fk}_cp"] = d["codigo_postal"]
    st.session_state[f"{fk}_conc"] = d["concelho"]
    st.session_state[f"{fk}_freg"] = d["freguesia"]
    st.session_state[f"{fk}_dist"] = d["distrito"]
    st.session_state[f"{fk}_pais"] = d.get("pais") or "Portugal"
    dn = d.get("data_nascimento")
    if dn and parse_data_iso(str(dn)[:10]):
        st.session_state[f"{fk}_dnasc"] = datetime.strptime(str(dn)[:10], "%Y-%m-%d").date()
    else:
        st.session_state[f"{fk}_dnasc"] = date(1990, 1, 1)
    if d["sexo"] == "Feminino":
        st.session_state[f"{fk}_gravida"] = "Sim" if d.get("gravida") else "Não"
        dp = d.get("data_parto_prevista")
        if dp and parse_data_iso(str(dp)[:10]):
            st.session_state[f"{fk}_parto"] = datetime.strptime(str(dp)[:10], "%Y-%m-%d").date()
    st.session_state[f"{fk}_temf"] = "Sim" if d["tem_filhos"] else "Não"
    if d["tem_filhos"]:
        filhos = d.get("filhos") or []
        st.session_state[f"{fk}_qtd"] = max(1, len(filhos))
        for j, row in enumerate(filhos):
            fn, ida, sx = row[0], row[1], row[2]
            st.session_state[f"{fk}_f_nom_{j}"] = fn
            st.session_state[f"{fk}_f_id_{j}"] = int(ida)
            st.session_state[f"{fk}_f_sx_{j}"] = sx
            dn_f = row[3] if len(row) >= 4 else None
            if dn_f and parse_data_iso(str(dn_f)[:10]):
                st.session_state[f"{fk}_f_hasdn_{j}"] = True
                st.session_state[f"{fk}_f_dn_{j}"] = datetime.strptime(str(dn_f)[:10], "%Y-%m-%d").date()
            else:
                st.session_state[f"{fk}_f_hasdn_{j}"] = False
    em = d.get("contatos_emergencia") or []
    if em:
        st.session_state[f"{fk}_tem_emerg"] = "Sim"
        st.session_state.cli_n_emergency = max(1, min(10, len(em)))
        for j, (en, et) in enumerate(em):
            st.session_state[f"{fk}_em_n_{j}"] = en
            preencher_session_telefone_de_e164(f"{fk}_emerg_{j}", str(et or ""))
    else:
        st.session_state[f"{fk}_tem_emerg"] = "Não"
        st.session_state.cli_n_emergency = 1
    st.session_state[f"{fk}_obs"] = d.get("observacoes") or ""


def render_page_clientes(*, render_back_and_breadcrumb) -> None:
    render_back_and_breadcrumb(["Home", "Clientes", "Cadastro"], back_key="bea_back_clientes")
    st.markdown(
        '<div class="bea-proto-scope"><div class="bea-pdv-titulo-wrap">'
        '<p class="bea-pdv-titulo">Cadastro de Clientes</p></div></div>',
        unsafe_allow_html=True,
    )

    if "cli_form_v" not in st.session_state:
        st.session_state.cli_form_v = 0
    if "cli_n_emergency" not in st.session_state:
        st.session_state.cli_n_emergency = 1
    if "cli_edit_id" not in st.session_state:
        st.session_state.cli_edit_id = None

    fv = st.session_state.cli_form_v
    fk = f"cli_{fv}"

    if "_cli_prime" in st.session_state:
        prime = st.session_state.pop("_cli_prime")
        if prime.get("fk_target") == fk:
            _carregar_ficha_em_formulario(fk, prime["data"])

    st.subheader("1. Pesquisa Cliente")
    with st.container(border=True):
        cli_busca_clicked = render_cliente_search_widget(
            key_prefix="cli_busca",
            button_type="secondary",
            minimal=True,
        )

    if cli_busca_clicked:
        nif_s = str(st.session_state.get("cli_busca_nif", "") or "").strip()
        em_s = str(st.session_state.get("cli_busca_email", "") or "").strip()
        tel_raw = str(st.session_state.get("cli_busca_tel_txt", "") or "").strip()
        use_tel = normalizar_telefone_legado_ou_e164(tel_raw) if tel_raw else ""
        busca_doc_intl = bool(st.session_state.get("cli_busca_docintl"))

        msg_err: str | None = None
        if not nif_s and not em_s and not tel_raw:
            msg_err = "Indique NIF, email ou telefone."
        elif em_s and not email_valido(em_s):
            msg_err = "❌ Email inválido para pesquisa."
        elif tel_raw and not use_tel:
            msg_err = "❌ Telefone inválido (ex.: +351912345678)."
        elif nif_s:
            ok_nf, msg_nf, _vx = normalizar_nif_armazenamento(
                nif_s, documento_identificacao_internacional=bool(busca_doc_intl)
            )
            if not ok_nf:
                msg_err = msg_nf
        if msg_err:
            st.error(msg_err)
        else:
            cands = buscar_clientes_por_nif_email_telefone(
                nif=nif_s,
                email=em_s,
                telefone=use_tel,
                documento_internacional=bool(busca_doc_intl),
            )
            if len(cands) == 0:
                st.warning("Nenhum cliente encontrado com estes critérios.")
                st.session_state.pop("cli_busca_cands", None)
            elif len(cands) == 1:
                cid = cands[0][0]
                data = obter_cliente_completo(cid)
                if not data:
                    st.error("Cliente não encontrado.")
                else:
                    st.session_state.cli_edit_id = cid
                    st.session_state.cli_form_v += 1
                    fk2 = f"cli_{st.session_state.cli_form_v}"
                    st.session_state._cli_prime = {"fk_target": fk2, "data": data}
                    st.session_state.pop("cli_busca_cands", None)
                    st.success(f"Cliente encontrado (#{cid}). Ficha carregada para edição.")
                    st.rerun()
            else:
                st.session_state.cli_busca_cands = cands
                st.rerun()

    cands_m = st.session_state.get("cli_busca_cands")
    if cands_m and len(cands_m) > 1:
        st.subheader("Resultados")
        n_c = len(cands_m)
        for row_start in range(0, n_c, 3):
            cols = st.columns(3)
            for i in range(3):
                ix = row_start + i
                if ix >= n_c:
                    break
                cid, nome = cands_m[ix]
                nome_e = html.escape(str(nome))
                sub_e = html.escape(f"#{cid}")
                with cols[i]:
                    with st.container(border=True):
                        st.markdown(
                            _html_cli_result_card(nome_e=nome_e, sub_e=sub_e),
                            unsafe_allow_html=True,
                        )
                        if st.button("Carregar ficha", key=f"cli_cand_load_{cid}", width="stretch"):
                            data = obter_cliente_completo(cid)
                            if not data:
                                st.error("Cliente não encontrado.")
                            else:
                                st.session_state.cli_edit_id = cid
                                st.session_state.cli_form_v += 1
                                fk2 = f"cli_{st.session_state.cli_form_v}"
                                st.session_state._cli_prime = {"fk_target": fk2, "data": data}
                                st.session_state.pop("cli_busca_cands", None)
                                st.rerun()

    r_new, _ = st.columns([1, 3])
    with r_new:
        if st.button("Nova ficha", key=f"{fk}_btn_new", type="secondary"):
            st.session_state.cli_edit_id = None
            st.session_state.cli_form_v += 1
            st.session_state.cli_n_emergency = 1
            st.session_state.pop("cli_busca_cands", None)
            st.rerun()

    if st.button("Consultar saldo de crédito na loja", key=f"{fk}_btn_toggle_saldo"):
        st.session_state[f"{fk}_saldo_aberto"] = not st.session_state.get(f"{fk}_saldo_aberto", False)
    if st.session_state.get(f"{fk}_saldo_aberto"):
        st.subheader("Consulta de saldo de crédito")
        eid_s = st.session_state.cli_edit_id
        if eid_s is not None:
            sc = obter_saldo_credito_cliente(int(eid_s))
            st.metric("Saldo do cliente em edição", centavos_para_texto_euros(sc))
        filtro_saldo = st.radio(
            "Filtrar lista por saldo",
            ["todos", "com_saldo", "sem_saldo"],
            horizontal=True,
            format_func=lambda x: {
                "todos": "Todos",
                "com_saldo": "Com saldo (> 0)",
                "sem_saldo": "Sem saldo",
            }[x],
            key=f"{fk}_cli_filtro_cred",
        )
        rows_cc = listar_clientes_resumo_com_credito(filtro_saldo=filtro_saldo)
        if rows_cc:
            n_cc = len(rows_cc)
            for row_start in range(0, n_cc, 3):
                cols = st.columns(3)
                for i in range(3):
                    ix = row_start + i
                    if ix >= n_cc:
                        break
                    r = rows_cc[ix]
                    with cols[i]:
                        with st.container(border=True):
                            st.markdown(
                                f'<div class="bea-proto-scope"><p class="bea-com-nome">'
                                f"{html.escape(str(r[1]))}</p>"
                                f'<span class="bea-com-badge">#{r[0]}</span></div>',
                                unsafe_allow_html=True,
                            )
                            st.markdown(f"**Saldo:** {centavos_para_texto_euros(r[2])}")
        else:
            st.info("Nenhum cliente neste filtro.")

    st.subheader("2. Ficha")
    with st.container(border=True):
        st.markdown("##### Dados pessoais")
        nome = st.text_input("Nome completo *", key=f"{fk}_nome")
        doc_intl = st.checkbox(
            "Documento de identificação **não** é NIF português",
            key=f"{fk}_docintl",
        )
        ph_doc = "Documento internacional (3–40 caracteres)" if doc_intl else "9 dígitos (NIF PT)"
        nif_val = st.text_input(
            "NIF ou documento de identificação *",
            key=f"{fk}_nif",
            placeholder=ph_doc,
        )
        st.date_input(
            "Data de nascimento *",
            min_value=CLIENTE_SEARCH_DATE_MIN,
            max_value=date.today(),
            format="DD/MM/YYYY",
            key=f"{fk}_dnasc",
        )
        render_grupo_telefone(st, prefix=f"{fk}_tel_pri", label="Contacto principal *")
        email = st.text_input("Email *", key=f"{fk}_email")
        sexo = st.selectbox("Sexo *", SEXOS, key=f"{fk}_sexo")

        gravida: bool | None = None
        data_parto: str | None = None
        if sexo == "Feminino":
            g_label = st.radio("Está grávida? *", ["Não", "Sim"], horizontal=True, key=f"{fk}_gravida")
            gravida = g_label == "Sim"
            if gravida:
                d = st.date_input(
                    "Estimativa de data de parto *",
                    key=f"{fk}_parto",
                    format="DD/MM/YYYY",
                    min_value=CLIENTE_SEARCH_DATE_MIN,
                )
                data_parto = d.isoformat() if d else None
        else:
            gravida = None
            data_parto = None

        st.markdown("##### Morada")
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            end_rua = st.text_input("Rua / logradouro *", key=f"{fk}_rua")
        with r1c2:
            end_num = st.text_input("Número *", key=f"{fk}_numero")
        end_comp = st.text_input("Complemento (opcional)", key=f"{fk}_comp", placeholder="Andar, fração, etc.")
        r2c1, r2c2, r2c3 = st.columns(3)
        with r2c1:
            end_cp = st.text_input("Código postal *", key=f"{fk}_cp", placeholder="4800-123")
        with r2c2:
            end_conc = st.text_input("Concelho *", key=f"{fk}_conc")
        with r2c3:
            end_freg = st.text_input("Freguesia *", key=f"{fk}_freg")
        r3c1, r3c2 = st.columns(2)
        with r3c1:
            end_dist = st.text_input("Distrito (opcional)", key=f"{fk}_dist")
        with r3c2:
            _cli_pais_k = f"{fk}_pais"
            if _cli_pais_k not in st.session_state:
                st.session_state[_cli_pais_k] = "Portugal"
            end_pais = st.text_input("País *", key=_cli_pais_k)

        st.markdown("##### Filhos")
        tem_filhos = st.radio("Possui filhos? *", ["Não", "Sim"], horizontal=True, key=f"{fk}_temf") == "Sim"
        filhos: list[tuple[str, int, str] | tuple[str, int, str, str]] = []
        if tem_filhos:
            qtd = int(
                st.number_input(
                    "Quantos filhos? *",
                    min_value=1,
                    max_value=20,
                    value=1,
                    step=1,
                    key=f"{fk}_qtd",
                )
            )
            for j in range(qtd):
                st.markdown(f"**Filho {j + 1}**")
                cf1, cf2, cf3 = st.columns(3)
                with cf1:
                    fn = st.text_input("Nome *", key=f"{fk}_f_nom_{j}")
                with cf2:
                    idade = int(
                        st.number_input(
                            "Idade (anos) *",
                            min_value=0,
                            max_value=120,
                            value=0,
                            key=f"{fk}_f_id_{j}",
                        )
                    )
                with cf3:
                    sx = st.selectbox("Sexo *", SEXOS, key=f"{fk}_f_sx_{j}")
                has_dn = st.checkbox(
                    "Indicar data de nascimento (opcional)",
                    key=f"{fk}_f_hasdn_{j}",
                )
                dn_iso: str | None = None
                if has_dn:
                    d_birth = st.date_input(
                        "Data de nascimento",
                        max_value=date.today(),
                        format="DD/MM/YYYY",
                        min_value=CLIENTE_SEARCH_DATE_MIN,
                        key=f"{fk}_f_dn_{j}",
                    )
                    dn_iso = d_birth.isoformat() if d_birth else None
                if dn_iso:
                    filhos.append((fn, idade, sx, dn_iso))
                else:
                    filhos.append((fn, idade, sx))

        tem_emerg = st.radio(
            "Possui contacto de emergência? *",
            ["Não", "Sim"],
            horizontal=True,
            key=f"{fk}_tem_emerg",
        ) == "Sim"
        if tem_emerg:
            st.markdown("##### Contactos de emergência")
            c_add, _ = st.columns([2, 3])
            with c_add:
                if st.button("➕ Adicionar contacto de emergência", key=f"{fk}_add_em"):
                    st.session_state.cli_n_emergency = min(st.session_state.cli_n_emergency + 1, 10)

            for i in range(st.session_state.cli_n_emergency):
                st.text_input(f"Nome (emergência {i + 1})", key=f"{fk}_em_n_{i}")
                render_grupo_telefone(
                    st,
                    prefix=f"{fk}_emerg_{i}",
                    label=f"Telefone (emergência {i + 1})",
                )

    eid_hist = st.session_state.cli_edit_id
    if eid_hist is not None:
        with st.container(border=True):
            st.markdown("##### Histórico de Compras")
            vendas = listar_vendas_resumo_cliente(int(eid_hist))
            if vendas:
                nv = len(vendas)
                for row_start in range(0, nv, 3):
                    cols = st.columns(3)
                    for i in range(3):
                        ix = row_start + i
                        if ix >= nv:
                            break
                        vid, dr, tot_cent, est = vendas[ix]
                        with cols[i]:
                            with st.container(border=True):
                                st.markdown(
                                    f'<div class="bea-proto-scope"><span class="bea-com-badge">'
                                    f"Venda #{vid}</span>"
                                    f'<p class="bea-com-nome" style="font-size:1rem;margin:0.35rem 0 0 0;">'
                                    f"{html.escape(centavos_para_texto_euros(tot_cent))}</p>"
                                    f"<p style='margin:0;font-size:0.8rem;color:#64748B;'>{html.escape(dr)} · "
                                    f"{html.escape(est)}</p></div>",
                                    unsafe_allow_html=True,
                                )
            else:
                st.caption("Sem vendas registadas para este cliente.")

    with st.container(border=True):
        st.markdown("##### Observações")
        observacoes = st.text_area(
            "Observações",
            key=f"{fk}_obs",
            height=100,
            placeholder="Detalhes especiais sobre a pessoa (opcional).",
        )

    d_nasc_o = st.session_state.get(f"{fk}_dnasc")
    data_nasc_iso = (
        d_nasc_o.isoformat()
        if d_nasc_o is not None and hasattr(d_nasc_o, "isoformat")
        else ""
    )

    eid = st.session_state.cli_edit_id
    if eid and st.button("Guardar alterações", type="primary", key=f"{fk}_submit_edit"):
        ok_t, tel_e164, err_t = ler_e164_de_widgets(f"{fk}_tel_pri")
        if not ok_t:
            st.error(err_t)
        else:
            emerg_l: list[tuple[str, str]] = []
            em_err = False
            if tem_emerg:
                for i in range(st.session_state.cli_n_emergency):
                    en = str(st.session_state.get(f"{fk}_em_n_{i}", "") or "").strip()
                    ok_e, e164_e, err_e = ler_e164_de_widgets(f"{fk}_emerg_{i}")
                    if not en and not ok_e:
                        continue
                    if not en or not ok_e:
                        st.error(err_e or "❌ Contacto de emergência incompleto.")
                        em_err = True
                        break
                    emerg_l.append((en, e164_e))
            if not em_err:
                ok, msg = atualizar_cliente(
                    int(eid),
                    nome=nome,
                    numero_contato=tel_e164,
                    endereco_rua=end_rua,
                    endereco_numero=end_num,
                    endereco_complemento=end_comp,
                    codigo_postal=end_cp,
                    concelho=end_conc,
                    freguesia=end_freg,
                    distrito=end_dist,
                    pais=end_pais,
                    email=email,
                    sexo=sexo,
                    tem_filhos=tem_filhos,
                    filhos=filhos,
                    gravida=gravida,
                    data_parto_prevista=data_parto,
                    observacoes=observacoes or "",
                    contatos_emergencia=emerg_l,
                    nif=nif_val,
                    documento_identificacao_internacional=bool(doc_intl),
                    data_nascimento=data_nasc_iso,
                )
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

    if not eid and st.button("Cadastrar cliente", type="primary", key=f"{fk}_submit"):
        ok_t, tel_e164, err_t = ler_e164_de_widgets(f"{fk}_tel_pri")
        if not ok_t:
            st.error(err_t)
        else:
            emerg_l: list[tuple[str, str]] = []
            em_err = False
            if tem_emerg:
                for i in range(st.session_state.cli_n_emergency):
                    en = str(st.session_state.get(f"{fk}_em_n_{i}", "") or "").strip()
                    ok_e, e164_e, err_e = ler_e164_de_widgets(f"{fk}_emerg_{i}")
                    if not en and not ok_e:
                        continue
                    if not en or not ok_e:
                        st.error(err_e or "❌ Contacto de emergência incompleto.")
                        em_err = True
                        break
                    emerg_l.append((en, e164_e))
            if not em_err:
                ok, msg = cadastrar_cliente(
                    nome=nome,
                    numero_contato=tel_e164,
                    endereco_rua=end_rua,
                    endereco_numero=end_num,
                    endereco_complemento=end_comp,
                    codigo_postal=end_cp,
                    concelho=end_conc,
                    freguesia=end_freg,
                    distrito=end_dist,
                    pais=end_pais,
                    email=email,
                    sexo=sexo,
                    tem_filhos=tem_filhos,
                    filhos=filhos,
                    gravida=gravida,
                    data_parto_prevista=data_parto,
                    observacoes=observacoes or "",
                    contatos_emergencia=emerg_l,
                    nif=nif_val,
                    documento_identificacao_internacional=bool(doc_intl),
                    data_nascimento=data_nasc_iso,
                )
                if ok:
                    st.session_state.cli_form_v += 1
                    st.session_state.cli_n_emergency = 1
                    st.session_state.cli_edit_id = None
                    st.success(msg)
                else:
                    st.error(msg)
