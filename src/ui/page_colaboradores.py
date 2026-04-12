"""Gestão de colaboradores — UI Streamlit (vitrine em grelha + ficha em expander)."""

from __future__ import annotations

import html
import uuid
from datetime import date, datetime

import streamlit as st

from src.pages.theme import get_beaba_css  # noqa: F401 — BeaBa Sereno (CSS em app.main)
from src.modules.colaborador import (
    atualizar_colaborador,
    buscar_colaboradores_por_nif_email_telefone,
    cadastrar_colaborador,
    listar_colaboradores_vitrine,
    listar_servicos,
    obter_colaborador,
)
from src.modules.constants import SEXOS
from src.modules.nif import normalizar_nif_armazenamento
from src.modules.telefone import normalizar_telefone_legado_ou_e164
from src.modules.validators import email_valido, parse_data_iso
from src.ui.widgets.cliente_search import render_cliente_search_widget


def _html_colab_vitrine_card(*, nome_e: str, serv_e: str) -> str:
    """Card vitrine: nome bordeaux, badge sálvia, ícone de contacto discreto."""
    return (
        '<div class="bea-proto-scope">'
        '<div class="bea-venda-comanda-item bea-comanda-min">'
        '<p style="margin:0 0 6px 0;text-align:right;font-size:0.95rem;opacity:0.5;">✉</p>'
        '<span class="bea-com-nome">'
        + nome_e
        + "</span><br/>"
        '<span class="bea-com-badge">'
        + serv_e
        + "</span>"
        "</div></div>"
    )


def _carregar_colab_para_edicao(cid: int) -> None:
    data = obter_colaborador(cid)
    if not data or not data["linhas"]:
        st.error("Não foi possível carregar a ficha.")
        return
    st.session_state.col_edit_id = cid
    st.session_state.col_edit_nome = str(data["nome"])
    st.session_state.col_form_v += 1
    fv2 = st.session_state.col_form_v
    st.session_state.col_row_ids = [uuid.uuid4().hex[:12] for _ in data["linhas"]]
    st.session_state._col_prime = {"fk_target": f"col_{fv2}", "data": data}
    st.session_state.pop("col_busca_cands", None)


def render_page_colaboradores(*, render_back_and_breadcrumb) -> None:
    render_back_and_breadcrumb(["Home", "Colaboradores", "Cadastro"], back_key="bea_back_colaboradores")
    st.markdown(
        '<div class="bea-proto-scope"><div class="bea-pdv-titulo-wrap">'
        '<p class="bea-pdv-titulo">Gestão de Colaboradores</p></div></div>',
        unsafe_allow_html=True,
    )

    if "col_form_v" not in st.session_state:
        st.session_state.col_form_v = 0
    if "col_row_ids" not in st.session_state:
        st.session_state.col_row_ids = [uuid.uuid4().hex[:12]]
    if "col_edit_id" not in st.session_state:
        st.session_state.col_edit_id = None
    if "col_edit_nome" not in st.session_state:
        st.session_state.col_edit_nome = ""

    fv = st.session_state.col_form_v
    fk = f"col_{fv}"

    if "_col_prime" in st.session_state:
        prime = st.session_state.pop("_col_prime")
        if prime.get("fk_target") == fk:
            d = prime["data"]
            st.session_state.col_edit_nome = str(d.get("nome") or "")
            st.session_state[f"{fk}_nome"] = d["nome"]
            st.session_state[f"{fk}_sexo"] = d["sexo"]
            st.session_state[f"{fk}_dn"] = datetime.strptime(d["data_nascimento"][:10], "%Y-%m-%d").date()
            st.session_state[f"{fk}_email"] = d["email"]
            st.session_state[f"{fk}_docintl"] = bool(d.get("identificacao_internacional"))
            st.session_state[f"{fk}_nif"] = str(d.get("nif_ou_documento") or "")
            st.session_state[f"{fk}_num"] = d["whatsapp"]
            st.session_state[f"{fk}_rua"] = d["endereco_rua"]
            st.session_state[f"{fk}_numero"] = d["endereco_numero"]
            st.session_state[f"{fk}_comp"] = d["endereco_complemento"]
            st.session_state[f"{fk}_cp"] = d["codigo_postal"]
            st.session_state[f"{fk}_conc"] = d["concelho"]
            st.session_state[f"{fk}_freg"] = d["freguesia"]
            st.session_state[f"{fk}_dist"] = d["distrito"]
            st.session_state[f"{fk}_pais"] = d["pais"]
            st.session_state[f"{fk}_obs"] = d["observacoes"]
            for rid, ln in zip(st.session_state.col_row_ids, d["linhas"]):
                st.session_state[f"{fk}_svc_{rid}"] = ln["nome_servico"]
                st.session_state[f"{fk}_pct_{rid}"] = float(ln["percentual"])
                di = (ln.get("data_insercao_linha") or "")[:10]
                st.session_state[f"{fk}_dlin_{rid}"] = (
                    datetime.strptime(di, "%Y-%m-%d").date() if parse_data_iso(di) else datetime.now().date()
                )

    st.subheader("1. Pesquisa Colaborador")
    with st.container(border=True):
        col_busca_clicked = render_cliente_search_widget(
            key_prefix="col_busca",
            button_type="secondary",
            minimal=True,
        )

    if col_busca_clicked:
        nif_s = str(st.session_state.get("col_busca_nif", "") or "").strip()
        em_s = str(st.session_state.get("col_busca_email", "") or "").strip()
        tel_raw = str(st.session_state.get("col_busca_tel_txt", "") or "").strip()
        use_tel = normalizar_telefone_legado_ou_e164(tel_raw) if tel_raw else ""
        busca_doc_intl = bool(st.session_state.get("col_busca_docintl"))

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
            cands = buscar_colaboradores_por_nif_email_telefone(
                nif=nif_s,
                email=em_s,
                telefone=use_tel,
                documento_internacional=bool(busca_doc_intl),
            )
            if len(cands) == 0:
                st.warning("Nenhum colaborador encontrado com estes critérios.")
                st.session_state.pop("col_busca_cands", None)
            elif len(cands) == 1:
                cid = cands[0][0]
                _carregar_colab_para_edicao(cid)
                st.success(f"Colaborador encontrado (#{cid}).")
                st.rerun()
            else:
                st.session_state.col_busca_cands = cands
                st.rerun()

    cands_m = st.session_state.get("col_busca_cands")
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
                with cols[i]:
                    with st.container(border=True):
                        st.markdown(
                            _html_colab_vitrine_card(nome_e=nome_e, serv_e=html.escape(f"#{cid}")),
                            unsafe_allow_html=True,
                        )
                        if st.button("Carregar ficha", key=f"col_cand_load_{cid}", width="stretch"):
                            _carregar_colab_para_edicao(cid)
                            st.rerun()

    servicos_opts = listar_servicos()
    if not servicos_opts:
        st.error("Não há serviços ativos na base. Abra o Catálogo.")
        if st.button("Abrir Catálogo", key=f"{fk}_goto_cat_empty"):
            st.session_state.page = "catalogo"
        return

    nomes_servicos = [row[1] for row in servicos_opts]
    id_por_nome: dict[str, int] = {row[1]: row[0] for row in servicos_opts}

    vitrine = listar_colaboradores_vitrine()
    if vitrine:
        st.subheader("2. Equipa")
        if st.button("Novo cadastro limpo", key=f"{fk}_reset_new", type="secondary"):
            st.session_state.col_edit_id = None
            st.session_state.col_edit_nome = ""
            st.session_state.col_form_v += 1
            st.session_state.col_row_ids = [uuid.uuid4().hex[:12]]
            st.rerun()

        n_v = len(vitrine)
        for row_start in range(0, n_v, 3):
            cols = st.columns(3)
            for i in range(3):
                ix = row_start + i
                if ix >= n_v:
                    break
                cid, nome, serv_lbl = vitrine[ix]
                nome_e = html.escape(nome)
                serv_e = html.escape(serv_lbl)
                with cols[i]:
                    with st.container(border=True):
                        st.markdown(
                            _html_colab_vitrine_card(nome_e=nome_e, serv_e=serv_e),
                            unsafe_allow_html=True,
                        )
                        if st.button("Abrir ficha", key=f"colab_vit_load_{cid}", width="stretch"):
                            _carregar_colab_para_edicao(cid)
                            st.rerun()
    else:
        st.info("Ainda não há colaboradores. Utilize o formulário abaixo para o primeiro cadastro.")
        if st.button("Preparar novo cadastro", key=f"{fk}_prep_new"):
            st.session_state.col_edit_id = None
            st.session_state.col_edit_nome = ""
            st.session_state.col_form_v += 1
            st.session_state.col_row_ids = [uuid.uuid4().hex[:12]]
            st.rerun()

    exp_nome = st.session_state.col_edit_nome or "Novo colaborador"
    if st.session_state.col_edit_id is not None and not exp_nome:
        exp_nome = f"#{st.session_state.col_edit_id}"

    with st.container(border=True):
        with st.expander(f"⋯ Item: {exp_nome} — Detalhes", expanded=True):
            st.markdown("##### Dados pessoais")
            c_nome = st.text_input("Nome completo *", key=f"{fk}_nome")
            c_sexo = st.selectbox("Sexo *", SEXOS, key=f"{fk}_sexo")
            c_dn = st.date_input(
                "Data de nascimento *",
                key=f"{fk}_dn",
                format="DD/MM/YYYY",
                min_value=date(1900, 1, 1),
            )
            c_email = st.text_input("Email *", key=f"{fk}_email")
            c_docintl = st.checkbox("Documento de identificação internacional (opcional)", key=f"{fk}_docintl")
            ph_doc = "Documento internacional" if st.session_state.get(f"{fk}_docintl") else "NIF PT (opcional)"
            c_nif = st.text_input("NIF / documento (opcional)", key=f"{fk}_nif", placeholder=ph_doc)
            c_num = st.text_input("Número de contacto *", key=f"{fk}_num", placeholder="DDD + número (11 dígitos)")

            st.markdown("##### Morada")
            r1c1, r1c2 = st.columns(2)
            with r1c1:
                c_rua = st.text_input("Rua / logradouro *", key=f"{fk}_rua")
            with r1c2:
                c_numero = st.text_input("Número *", key=f"{fk}_numero")
            c_comp = st.text_input("Complemento (opcional)", key=f"{fk}_comp")
            r2c1, r2c2, r2c3 = st.columns(3)
            with r2c1:
                c_cp = st.text_input("Código postal *", key=f"{fk}_cp", placeholder="4800-123")
            with r2c2:
                c_conc = st.text_input("Concelho *", key=f"{fk}_conc")
            with r2c3:
                c_freg = st.text_input("Freguesia *", key=f"{fk}_freg")
            r3c1, r3c2 = st.columns(2)
            with r3c1:
                c_dist = st.text_input("Distrito (opcional)", key=f"{fk}_dist")
            with r3c2:
                _col_pais_k = f"{fk}_pais"
                if _col_pais_k not in st.session_state:
                    st.session_state[_col_pais_k] = "Portugal"
                c_pais = st.text_input("País *", key=_col_pais_k)

            st.markdown("##### Serviços habilitados e repasse")
            if st.button("Abrir Catálogo de Serviços", key=f"{fk}_goto_cat"):
                st.session_state.page = "catalogo"

            c_add, _ = st.columns([2, 3])
            with c_add:
                if st.button("➕ Adicionar item de serviço", key=f"{fk}_add_svc"):
                    st.session_state.col_row_ids.append(uuid.uuid4().hex[:12])

            repasse: list[tuple[int, float, str]] = []
            row_ids = list(st.session_state.col_row_ids)
            for pos, row_id in enumerate(row_ids):
                st.markdown(f"**Item {pos + 1}**")
                sc1, sc2, sc3 = st.columns([2, 1, 1])
                with sc1:
                    nome_svc = st.selectbox("Serviço *", nomes_servicos, key=f"{fk}_svc_{row_id}")
                    sid = id_por_nome[nome_svc]
                with sc2:
                    _pct_k = f"{fk}_pct_{row_id}"
                    if _pct_k not in st.session_state:
                        st.session_state[_pct_k] = 50.0
                    pct = float(
                        st.number_input(
                            "Repasse % *",
                            min_value=0.01,
                            max_value=100.0,
                            step=0.01,
                            key=_pct_k,
                        )
                    )
                with sc3:
                    dlin = st.date_input(
                        "Data de Ativação do serviço",
                        key=f"{fk}_dlin_{row_id}",
                        format="DD/MM/YYYY",
                        min_value=date(1900, 1, 1),
                    )
                rb1, rb2 = st.columns([1, 4])
                with rb1:
                    if len(row_ids) > 1 and st.button("Remover item", key=f"{fk}_rm_{row_id}"):
                        st.session_state.col_row_ids = [r for r in row_ids if r != row_id]
                        st.rerun()
                repasse.append((sid, pct, dlin.isoformat() if dlin else ""))

            st.markdown("##### Observações")
            c_obs = st.text_area(
                "Observações",
                key=f"{fk}_obs",
                height=100,
                placeholder="Texto livre (opcional).",
            )

            editing = st.session_state.col_edit_id is not None
            btn_label = "Guardar alterações" if editing else "Cadastrar colaborador"
            if st.button(btn_label, type="primary", key=f"{fk}_submit"):
                dn_iso = c_dn.isoformat() if c_dn else ""
                common = dict(
                    nome=c_nome,
                    sexo=c_sexo,
                    data_nascimento=dn_iso,
                    endereco_rua=c_rua,
                    endereco_numero=c_numero,
                    endereco_complemento=c_comp,
                    codigo_postal=c_cp,
                    concelho=c_conc,
                    freguesia=c_freg,
                    distrito=c_dist,
                    pais=c_pais,
                    email=c_email,
                    numero_contato=c_num,
                    observacoes=c_obs or "",
                    servicos_repasse=repasse,
                    nif_ou_documento=c_nif or "",
                    identificacao_internacional=bool(c_docintl),
                )
                if editing:
                    ok, msg = atualizar_colaborador(int(st.session_state.col_edit_id), **common)
                else:
                    ok, msg = cadastrar_colaborador(**common)
                if ok:
                    st.session_state.col_form_v += 1
                    st.session_state.col_edit_id = None
                    st.session_state.col_edit_nome = ""
                    st.session_state.col_row_ids = [uuid.uuid4().hex[:12]]
                    st.success(msg)
                else:
                    st.error(msg)
