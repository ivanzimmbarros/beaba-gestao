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
    buscar_colaboradores_por_prefixo_nome,
    cadastrar_colaborador,
    listar_colaboradores_mapa_equipa,
    listar_colaboradores_resumo,
    listar_naturezas_servicos_mapa_equipa,
    listar_servicos,
    listar_servicos_para_mapa_equipa,
    obter_colaborador,
    resolver_conjunto_servicos_mapa_equipa,
)
from src.modules.constants import SEXOS
from src.modules.nif import normalizar_nif_armazenamento
from src.modules.telefone import normalizar_telefone_legado_ou_e164
from src.modules.validators import email_valido, parse_data_iso
from src.ui.constituicao_visual_shell import inject_constituicao_col_page
from src.ui.widgets.cliente_search import render_cliente_search_widget


def _col_section_title_html(title: str) -> str:
    t = html.escape(title)
    return f'<div class="bea-cv-cag-h2">{t}</div>'


def _col_ficha_subsec_html(title: str) -> str:
    t = html.escape(title)
    return (
        f'<div class="bea-cv-cag-h2" style="font-size:1.05rem;margin:0.85rem 0 0.35rem 0;">{t}</div>'
    )


def _html_colab_vitrine_card(*, nome_e: str, serv_e: str) -> str:
    """Card vitrine — estilo comanda dentro da Ilha Mãe (sem proto-scope duplicado)."""
    return (
        '<div class="bea-venda-comanda-item bea-comanda-min">'
        '<p style="margin:0 0 6px 0;text-align:right;font-size:0.95rem;opacity:0.5;">✉</p>'
        '<span class="bea-com-nome">'
        + nome_e
        + "</span><br/>"
        '<span class="bea-com-badge">'
        + serv_e
        + "</span>"
        "</div>"
    )


_LBL_FILTRO_COL_MAPA = (
    '<p style="margin:0 0 4px 0;font-size:0.8rem;color:#718355;font-weight:600;'
    'min-height:1.35rem;line-height:1.35rem;">{}</p>'
)

_COL_MAPA_COL_W = [1.08, 1.08, 0.36]
_COL_MAPA_TBL_W = [0.38, 0.62]


def _col_badge_cls_natureza_servico(natureza: str) -> str:
    n = (natureza or "").strip()
    if n == "Sessão":
        return "bea-cv-badge-verde"
    if n in ("Produto", "Coworking"):
        return "bea-cv-badge-terracota"
    return "bea-cv-badge-neutro"


def _html_col_mapa_cell_servicos(servicos: list[tuple[str, str]]) -> str:
    parts: list[str] = []
    for sn, nat in servicos:
        cls = _col_badge_cls_natureza_servico(nat)
        parts.append(f'<span class="{cls}">{html.escape(sn)}</span>')
    sep = ' <span class="bea-col-mapa-sep">;</span> '
    return sep.join(parts)


def _carregar_colab_para_edicao(cid: int, *, limpar_barra_busca: bool = True) -> None:
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
    if limpar_barra_busca:
        st.session_state.col_busca_clear_pending = True
    else:
        st.session_state["col_busca_nome"] = str(data.get("nome") or "")
        st.session_state["col_busca_nif"] = str(data.get("nif_ou_documento") or "")
        st.session_state["col_busca_email"] = str(data.get("email") or "")
        st.session_state["col_busca_tel_txt"] = str(data.get("whatsapp") or "").strip()


def render_page_colaboradores(*, render_back_and_breadcrumb) -> None:
    inject_constituicao_col_page()
    render_back_and_breadcrumb(["Home", "Colaboradores", "Cadastro"], back_key="bea_back_colaboradores")
    st.markdown(
        '<h1 class="bea-cv-cag-h1">Gestão de Colaboradores</h1>',
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

    # Carregar ficha + barra de busca ANTES de qualquer widget `col_busca_*` (regra Streamlit).
    _col_load_id = st.session_state.pop("col_mapa_open_id", None)
    if _col_load_id is None:
        _col_load_id = st.session_state.pop("col_busca_suggestion_apply_id", None)
    if _col_load_id is not None:
        _carregar_colab_para_edicao(int(_col_load_id), limpar_barra_busca=False)

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

    st.markdown(
        '<div class="bea-cv-cag-gap" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    st.markdown(_col_section_title_html("1. Pesquisa de colaboradores"), unsafe_allow_html=True)
    if st.session_state.pop("col_busca_clear_pending", False):
        st.session_state["col_busca_nome"] = ""
        st.session_state["col_busca_nome_sug_list"] = []
        st.session_state["col_busca_nif"] = ""
        st.session_state["col_busca_email"] = ""
        st.session_state["col_busca_tel_txt"] = ""
        st.session_state.pop("col_busca_docintl", None)

    col_busca_clicked = render_cliente_search_widget(
        key_prefix="col_busca",
        button_type="secondary",
        minimal=True,
        pesquisa_unificada=True,
        nome_placeholder="Nome do colaborador",
        entidade_nome="colaborador",
    )

    if col_busca_clicked:
        nome_s = str(st.session_state.get("col_busca_nome", "") or "").strip()
        nif_s = str(st.session_state.get("col_busca_nif", "") or "").strip()
        em_s = str(st.session_state.get("col_busca_email", "") or "").strip()
        tel_raw = str(st.session_state.get("col_busca_tel_txt", "") or "").strip()
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
                for cid, nm in buscar_colaboradores_por_prefixo_nome(nome_s, limit=80):
                    merged[int(cid)] = str(nm)
            for cid, nm in buscar_colaboradores_por_nif_email_telefone(
                nif=nif_s,
                email=em_s,
                telefone=use_tel,
                documento_internacional=False,
            ):
                merged[int(cid)] = str(nm)
            cands = sorted(merged.items(), key=lambda x: (x[1].lower(), x[0]))
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
        st.markdown(
            '<div class="bea-cv-cag-gap" aria-hidden="true"></div>',
            unsafe_allow_html=True,
        )
        st.markdown(_col_section_title_html("Resultados"), unsafe_allow_html=True)
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

    st.markdown(
        '<div class="bea-cv-cag-gap" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    st.markdown(_col_section_title_html("2. Equipa"), unsafe_allow_html=True)
    if st.button("Novo cadastro limpo", key=f"{fk}_reset_new", type="secondary"):
        st.session_state.col_edit_id = None
        st.session_state.col_edit_nome = ""
        st.session_state.col_form_v += 1
        st.session_state.col_row_ids = [uuid.uuid4().hex[:12]]
        st.session_state.pop("col_mapa_resultado", None)
        st.rerun()

    st.markdown(_col_ficha_subsec_html("Mapa da Equipa"), unsafe_allow_html=True)
    _gap_m = "small"
    r1m = st.columns(_COL_MAPA_COL_W, gap=_gap_m, vertical_alignment="top")
    with r1m[0]:
        st.markdown(_LBL_FILTRO_COL_MAPA.format("Tipos de Serviço"), unsafe_allow_html=True)
    with r1m[1]:
        st.markdown(_LBL_FILTRO_COL_MAPA.format("Serviços Registados"), unsafe_allow_html=True)
    with r1m[2]:
        st.markdown(
            '<div style="height:calc(1.35rem + 4px);margin:0;padding:0;" aria-hidden="true"></div>',
            unsafe_allow_html=True,
        )

    nat_opts = listar_naturezas_servicos_mapa_equipa()
    r2m = st.columns(_COL_MAPA_COL_W, gap=_gap_m, vertical_alignment="center")
    with r2m[0]:
        nat_sel = st.multiselect(
            "Tipos de Serviço",
            options=nat_opts,
            key="col_mapa_nat",
            label_visibility="collapsed",
            placeholder="Naturezas…",
        )
    svc_rows = listar_servicos_para_mapa_equipa(nat_sel if nat_sel else None)
    avail_ids = [r[0] for r in svc_rows]
    if "col_mapa_svc" in st.session_state:
        st.session_state["col_mapa_svc"] = [
            x for x in st.session_state.get("col_mapa_svc", []) if x in set(avail_ids)
        ]

    def _fmt_svc_mapa(sid: int) -> str:
        for a, b, c in svc_rows:
            if int(a) == int(sid):
                return f"{b} ({c})"
        return str(sid)

    with r2m[1]:
        svc_sel = st.multiselect(
            "Serviços Registados",
            options=avail_ids,
            key="col_mapa_svc",
            format_func=_fmt_svc_mapa,
            label_visibility="collapsed",
            placeholder="Serviços…",
        )
    with r2m[2]:
        can_mapa_search = bool(nat_sel or svc_sel)
        if st.button(
            "Pesquisar",
            key="col_mapa_pesquisar",
            type="secondary",
            disabled=not can_mapa_search,
            width="stretch",
        ):
            cj = resolver_conjunto_servicos_mapa_equipa(
                naturezas_seleccionadas=list(nat_sel),
                servico_ids_seleccionados=list(svc_sel),
            )
            st.session_state.col_mapa_resultado = listar_colaboradores_mapa_equipa(cj)

    res_mapa = st.session_state.get("col_mapa_resultado")
    if res_mapa is None:
        st.caption(
            "Seleccione **Tipos de Serviço** e/ou **Serviços Registados** (pelo menos um) e clique "
            "**Pesquisar** — a tabela com *Nome completo* e *Serviços habilitados* aparece abaixo."
        )
    elif len(res_mapa) == 0:
        st.info("Nenhum colaborador encontrado para esta combinação.")
    else:
        st.markdown(
            '<div class="bea-col-mapa-wrap" data-testid="bea-col-mapa-wrap">',
            unsafe_allow_html=True,
        )
        th0, th1 = st.columns(_COL_MAPA_TBL_W, gap="small")
        with th0:
            st.markdown(
                '<div class="bea-col-mapa-th" data-testid="bea-col-mapa-th-nome">Nome completo</div>',
                unsafe_allow_html=True,
            )
        with th1:
            st.markdown(
                '<div class="bea-col-mapa-th" data-testid="bea-col-mapa-th-svc">Serviços habilitados</div>',
                unsafe_allow_html=True,
            )
        for row in res_mapa:
            cid_m = int(row["id"])
            nome_m = str(row["nome"])
            sv_tuples = list(row["servicos"])
            cell_html = _html_col_mapa_cell_servicos(sv_tuples)
            cnm, csv = st.columns(_COL_MAPA_TBL_W, gap="small", vertical_alignment="center")
            with cnm:
                if st.button(
                    nome_m,
                    key=f"col_mapa_open_{cid_m}",
                    type="tertiary",
                    help="Abrir ficha no expander abaixo",
                ):
                    st.session_state.col_mapa_open_id = int(cid_m)
                    st.rerun()
            with csv:
                st.markdown(
                    f'<div class="bea-col-mapa-svc-cell">{cell_html}</div>',
                    unsafe_allow_html=True,
                )
            st.markdown(
                '<div class="bea-col-mapa-row-end" aria-hidden="true"></div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    _resumo_col = listar_colaboradores_resumo()
    if not _resumo_col:
        st.info("Ainda não há colaboradores. Utilize o formulário abaixo para o primeiro cadastro.")
        if st.button("Preparar novo cadastro", key=f"{fk}_prep_new"):
            st.session_state.col_edit_id = None
            st.session_state.col_edit_nome = ""
            st.session_state.col_form_v += 1
            st.session_state.col_row_ids = [uuid.uuid4().hex[:12]]
            st.session_state.pop("col_mapa_resultado", None)
            st.rerun()

    exp_nome = st.session_state.col_edit_nome or "Novo colaborador"
    if st.session_state.col_edit_id is not None and not exp_nome:
        exp_nome = f"#{st.session_state.col_edit_id}"

    st.markdown(
        '<div class="bea-cv-cag-gap" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    with st.expander(f"⋯ Item: {exp_nome} — Detalhes", expanded=True):
        st.markdown(_col_ficha_subsec_html("Dados pessoais"), unsafe_allow_html=True)
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

        st.markdown(_col_ficha_subsec_html("Morada"), unsafe_allow_html=True)
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

        st.markdown(_col_ficha_subsec_html("Serviços habilitados e repasse"), unsafe_allow_html=True)
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

        st.markdown(_col_ficha_subsec_html("Observações"), unsafe_allow_html=True)
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
