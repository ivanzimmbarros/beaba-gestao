"""Gestão de colaboradores — UI Streamlit (vitrine em grelha + ficha em expander)."""

from __future__ import annotations

import html
import uuid
from datetime import date, datetime

import streamlit as st

from src.pages.theme import get_beaba_css  # noqa: F401 — BeaBa Sereno (CSS em app.main)
from src.modules.catalogo import obter_servico_para_formulario
from src.modules.colaborador import (
    MAPA_EQUI_ESP_SEM_LABEL,
    atualizar_colaborador,
    buscar_colaboradores_por_nif_email_telefone,
    buscar_colaboradores_por_prefixo_nome,
    cadastrar_colaborador,
    listar_colaboradores_mapa_equipa,
    listar_colaboradores_resumo,
    listar_naturezas_servicos_mapa_equipa,
    listar_servicos_para_mapa_equipa,
    obter_colaborador,
    resolver_conjunto_servicos_mapa_equipa,
)
from src.modules.constants import SEXOS
from src.modules.nif import normalizar_nif_armazenamento
from src.modules.telefone import normalizar_telefone_legado_ou_e164
from src.modules.validators import email_valido, parse_data_iso
from src.ui.colaboradores_disponibilidade_ui import render_colaboradores_disponibilidade_setor
from src.ui.colaboradores_repasse_setor_ui import render_setor4_relatorio_repasse_admin
from src.ui.constituicao_visual_shell import inject_constituicao_col_page
from src.ui.telefone_widgets import ler_e164_de_widgets, preencher_session_telefone_de_e164, render_grupo_telefone
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

_COL_MAPA_NAT_PH = "— Escolher natureza —"
_COL_MAPA_ESP_PH = "— Escolher especialidade —"
_COL_MAPA_SVC_PH = "— Escolher serviço —"
_COL_SIM_NAO = ("Sim", "Não")
_COL_PAR_3W = [0.24, 0.38, 0.38]
_COL_BTN_ROW_HALF = [0.25, 0.25, 0.5]
# Placeholder interno para multiselect «Serviço» quando ainda não há ids reais (Streamlit exige opções).
_COL_MAPA_SVC_SENTINEL = -9_000_000
_COL_MAPA_FILT_W = [0.95, 0.95, 1.15]
_COL_MAPA_COL_W = _COL_MAPA_FILT_W
_COL_MAPA_TBL_W = [0.26, 0.16, 0.16, 0.42]


def _col_badge_cls_natureza_servico(natureza: str) -> str:
    n = (natureza or "").strip()
    if n == "Sessão":
        return "bea-cv-badge-verde"
    if n in ("Produto", "Coworking"):
        return "bea-cv-badge-terracota"
    return "bea-cv-badge-neutro"


def _col_mapa_especialidades_opts(
    rows: list[tuple[int, str, str, str]],
    *,
    natureza: str | None = None,
) -> list[str]:
    from src.modules.catalogo import listar_especialidades_por_natureza

    nomes: set[str] = set()
    nat = str(natureza or "").strip()
    if nat:
        for r in listar_especialidades_por_natureza(nat):
            nm = str(r.get("nome") or "").strip()
            if nm:
                nomes.add(nm)
    for r in rows:
        ep = str(r[3]).strip()
        if ep:
            nomes.add(ep)
    out = sorted(nomes, key=str.casefold)
    if any(not str(r[3]).strip() for r in rows):
        if MAPA_EQUI_ESP_SEM_LABEL not in out:
            out.append(MAPA_EQUI_ESP_SEM_LABEL)
    return out


def _col_mapa_filtra_rows_por_especialidades(
    rows: list[tuple[int, str, str, str]], esp_sel: list[str]
) -> list[tuple[int, str, str, str]]:
    """Filtra por uma ou mais especialidades; `esp_sel` vazio → nenhuma linha (não «todos»)."""
    if not esp_sel:
        return []
    eset = set(str(x) for x in esp_sel)
    sem = MAPA_EQUI_ESP_SEM_LABEL in eset
    reals = [e for e in eset if e != MAPA_EQUI_ESP_SEM_LABEL]
    out: list[tuple[int, str, str, str]] = []
    for r in rows:
        ep = str(r[3] or "").strip()
        ok = False
        if sem and not ep:
            ok = True
        if ep and ep in reals:
            ok = True
        if ok:
            out.append(r)
    return out


def _col_mapa_agg_natureza_especialidade(sv: list[tuple[str, str, str]]) -> tuple[str, str]:
    nats = sorted({t[1].strip() for t in sv if t[1].strip()})
    esp_parts: list[str] = []
    seen: set[str] = set()
    for _nome, _nat, ep in sv:
        e = str(ep or "").strip()
        if not e:
            k = MAPA_EQUI_ESP_SEM_LABEL
        else:
            k = e
        if k not in seen:
            seen.add(k)
            esp_parts.append(k)
    esp_parts.sort(key=lambda x: (x != MAPA_EQUI_ESP_SEM_LABEL, x.casefold()))
    return ", ".join(nats) or "—", ", ".join(esp_parts) or "—"


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


def _col_iniciar_novo_cadastro(*, limpar_busca: bool = True) -> None:
    st.session_state.col_edit_id = None
    st.session_state.col_edit_nome = ""
    st.session_state.col_form_v += 1
    st.session_state.col_row_ids = [uuid.uuid4().hex[:12]]
    st.session_state.pop("col_mapa_resultado", None)
    if limpar_busca:
        st.session_state.col_busca_clear_pending = True


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
            st.session_state[f"{fk}_doc_par"] = str(d.get("documento_passaporte_residencia_cc") or "")
            st.session_state[f"{fk}_ae_sel"] = "Sim" if d.get("atividade_economica_aberta") else "Não"
            st.session_state[f"{fk}_ae_cod"] = str(d.get("atividade_economica_codigo") or "")
            st.session_state[f"{fk}_ae_desc"] = str(d.get("atividade_economica_descricao") or "")
            st.session_state[f"{fk}_ctr_sel"] = "Sim" if d.get("contrato_prestacao_assinado") else "Não"
            dctr = (d.get("contrato_prestacao_data_assinatura") or "")[:10]
            st.session_state[f"{fk}_ctr_dt"] = (
                datetime.strptime(dctr, "%Y-%m-%d").date() if parse_data_iso(dctr) else date.today()
            )
            st.session_state[f"{fk}_iban"] = str(d.get("iban_dados_bancarios") or "")
            preencher_session_telefone_de_e164(f"{fk}_tel_pri", str(d.get("whatsapp") or ""))
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
                sf = obter_servico_para_formulario(int(ln["servico_id"]))
                if sf:
                    st.session_state[f"{fk}_lnat_{rid}"] = str(sf.get("natureza") or "Sessão")
                    en = str(sf.get("especialidade_nome") or "").strip()
                    st.session_state[f"{fk}_lesp_{rid}"] = en if en else MAPA_EQUI_ESP_SEM_LABEL
                else:
                    st.session_state[f"{fk}_lnat_{rid}"] = _COL_MAPA_NAT_PH
                    st.session_state[f"{fk}_lesp_{rid}"] = _COL_MAPA_ESP_PH
                st.session_state[f"{fk}_lsvc_{rid}"] = f'{int(ln["servico_id"])}|{ln["nome_servico"]}'
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

    render_cliente_search_widget(
        key_prefix="col_busca",
        button_type="secondary",
        minimal=True,
        pesquisa_unificada=True,
        nome_placeholder="Nome do colaborador",
        entidade_nome="colaborador",
        search_button_placement="below",
    )
    b_proc, b_novo, _ = st.columns(_COL_BTN_ROW_HALF, gap="small")
    with b_proc:
        col_busca_clicked = st.button(
            "Procurar",
            type="secondary",
            key="col_busca_go",
            width="stretch",
        )
    with b_novo:
        if st.button("Novo Colaborador", key=f"{fk}_reset_new", type="secondary", width="stretch"):
            _col_iniciar_novo_cadastro()
            st.rerun()

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

    all_sv_detail = listar_servicos_para_mapa_equipa(None)
    if not all_sv_detail:
        st.error("Não há serviços ativos na base. Abra o Catálogo.")
        if st.button("Abrir Catálogo", key=f"{fk}_goto_cat_empty"):
            st.session_state.page = "catalogo"
        return

    st.markdown(
        '<div class="bea-cv-cag-gap" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    st.markdown(_col_section_title_html("2. Equipa"), unsafe_allow_html=True)

    st.markdown(_col_ficha_subsec_html("Mapa da Equipa"), unsafe_allow_html=True)
    _gap_m = "small"
    r1m = st.columns(_COL_MAPA_COL_W, gap=_gap_m, vertical_alignment="top")
    with r1m[0]:
        st.markdown(_LBL_FILTRO_COL_MAPA.format("Natureza"), unsafe_allow_html=True)
    with r1m[1]:
        st.markdown(_LBL_FILTRO_COL_MAPA.format("Especialidades"), unsafe_allow_html=True)
    with r1m[2]:
        st.markdown(_LBL_FILTRO_COL_MAPA.format("Serviço ou Produto"), unsafe_allow_html=True)

    nat_opts = listar_naturezas_servicos_mapa_equipa()
    nat_labels_ui = [_COL_MAPA_NAT_PH] + list(nat_opts)
    _raw_nat_m = st.session_state.get("col_mapa_natureza")
    if _raw_nat_m is not None and str(_raw_nat_m) not in nat_labels_ui:
        st.session_state.pop("col_mapa_natureza", None)

    r2m = st.columns(_COL_MAPA_COL_W, gap=_gap_m, vertical_alignment="center")
    with r2m[0]:
        st.selectbox(
            "Natureza",
            options=nat_labels_ui,
            key="col_mapa_natureza",
            label_visibility="collapsed",
        )
    nat_lbl = str(st.session_state.get("col_mapa_natureza") or _COL_MAPA_NAT_PH)
    _nat_sig = st.session_state.get("_col_mapa_nat_sig", "__unset__")
    if _nat_sig == "__unset__":
        st.session_state._col_mapa_nat_sig = nat_lbl
    elif str(_nat_sig) != nat_lbl:
        st.session_state._col_mapa_nat_sig = nat_lbl
        st.session_state.pop("col_mapa_especialidade", None)
        st.session_state.pop("col_mapa_svc", None)
    nat_for_q = None if nat_lbl == _COL_MAPA_NAT_PH else [nat_lbl]
    svc_rows_nat = listar_servicos_para_mapa_equipa(nat_for_q)
    esp_labels_ui = [_COL_MAPA_ESP_PH] + _col_mapa_especialidades_opts(
        svc_rows_nat,
        natureza=nat_lbl if nat_lbl != _COL_MAPA_NAT_PH else None,
    )
    _raw_esp_m = st.session_state.get("col_mapa_especialidade")
    if _raw_esp_m is not None and str(_raw_esp_m) not in esp_labels_ui:
        st.session_state.pop("col_mapa_especialidade", None)
    with r2m[1]:
        st.selectbox(
            "Especialidades",
            options=esp_labels_ui,
            key="col_mapa_especialidade",
            label_visibility="collapsed",
        )
    esp_lbl = str(st.session_state.get("col_mapa_especialidade") or _COL_MAPA_ESP_PH)
    _esp_sig = st.session_state.get("_col_mapa_esp_sig", "__unset__")
    if _esp_sig == "__unset__":
        st.session_state._col_mapa_esp_sig = esp_lbl
    elif str(_esp_sig) != esp_lbl:
        st.session_state._col_mapa_esp_sig = esp_lbl
        st.session_state.pop("col_mapa_svc", None)
    if esp_lbl == _COL_MAPA_ESP_PH:
        rows_esp: list[tuple[int, str, str, str]] = []
        avail_ids: list[int] = []
        st.session_state.pop("col_mapa_svc", None)
    else:
        rows_esp = _col_mapa_filtra_rows_por_especialidades(svc_rows_nat, [esp_lbl])
        avail_ids = [int(r[0]) for r in rows_esp]
        if "col_mapa_svc" in st.session_state:
            st.session_state["col_mapa_svc"] = [
                int(x)
                for x in st.session_state.get("col_mapa_svc", [])
                if int(x) in set(avail_ids)
            ]

    opts_m = avail_ids if avail_ids else [_COL_MAPA_SVC_SENTINEL]

    def _fmt_svc_mapa(sid: int) -> str:
        if int(sid) == _COL_MAPA_SVC_SENTINEL:
            if esp_lbl == _COL_MAPA_ESP_PH:
                return "— Escolher especialidade —"
            return "— Sem serviços para esta especialidade —"
        for a, b, c, _d in rows_esp:
            if int(a) == int(sid):
                return f"{b} ({c})"
        return str(sid)

    with r2m[2]:
        svc_sel = st.multiselect(
            "Serviço ou Produto",
            options=opts_m,
            key="col_mapa_svc",
            format_func=_fmt_svc_mapa,
            label_visibility="collapsed",
            placeholder="Serviços ou produtos…",
            disabled=esp_lbl == _COL_MAPA_ESP_PH,
        )
    svc_ids_pesquisa = [int(x) for x in svc_sel if int(x) != _COL_MAPA_SVC_SENTINEL]

    r3m = st.columns(_COL_BTN_ROW_HALF, gap="small")
    with r3m[0]:
        can_mapa_search = (
            nat_lbl != _COL_MAPA_NAT_PH
            or esp_lbl != _COL_MAPA_ESP_PH
            or bool(svc_ids_pesquisa)
        )
        if st.button(
            "Pesquisar",
            key="col_mapa_pesquisar",
            type="secondary",
            disabled=not can_mapa_search,
            width="stretch",
        ):
            nats_q = [nat_lbl] if nat_lbl != _COL_MAPA_NAT_PH else []
            esps_q = [esp_lbl] if esp_lbl != _COL_MAPA_ESP_PH else None
            cj = resolver_conjunto_servicos_mapa_equipa(
                naturezas_seleccionadas=nats_q,
                especialidades_seleccionadas=esps_q,
                servico_ids_seleccionados=svc_ids_pesquisa,
            )
            st.session_state.col_mapa_resultado = listar_colaboradores_mapa_equipa(cj)

    res_mapa = st.session_state.get("col_mapa_resultado")
    if res_mapa is None:
        pass
    elif len(res_mapa) == 0:
        st.info("Nenhum colaborador encontrado para esta combinação.")
    else:
        st.markdown(
            '<div class="bea-col-mapa-wrap" data-testid="bea-col-mapa-wrap">',
            unsafe_allow_html=True,
        )
        th0, th1, th2, th3 = st.columns(_COL_MAPA_TBL_W, gap="small")
        with th0:
            st.markdown(
                '<div class="bea-col-mapa-th" data-testid="bea-col-mapa-th-nome">Nome completo</div>',
                unsafe_allow_html=True,
            )
        with th1:
            st.markdown(
                '<div class="bea-col-mapa-th" data-testid="bea-col-mapa-th-nat">Natureza</div>',
                unsafe_allow_html=True,
            )
        with th2:
            st.markdown(
                '<div class="bea-col-mapa-th" data-testid="bea-col-mapa-th-esp">Especialidade</div>',
                unsafe_allow_html=True,
            )
        with th3:
            st.markdown(
                '<div class="bea-col-mapa-th" data-testid="bea-col-mapa-th-svc">Serviços habilitados</div>',
                unsafe_allow_html=True,
            )
        for row in res_mapa:
            cid_m = int(row["id"])
            nome_m = str(row["nome"])
            sv_tuples = list(row["servicos"])
            cell_html = _html_col_mapa_cell_servicos([(t[0], t[1]) for t in sv_tuples])
            nat_cell, esp_cell = _col_mapa_agg_natureza_especialidade(sv_tuples)
            nat_e = html.escape(nat_cell)
            esp_e = html.escape(esp_cell)
            cnm, ctn, cte, csv = st.columns(_COL_MAPA_TBL_W, gap="small", vertical_alignment="center")
            with cnm:
                if st.button(
                    nome_m,
                    key=f"col_mapa_open_{cid_m}",
                    type="tertiary",
                    help="Abrir ficha no expander abaixo",
                ):
                    st.session_state.col_mapa_open_id = int(cid_m)
                    st.rerun()
            with ctn:
                st.markdown(
                    f'<div class="bea-col-mapa-svc-cell">{nat_e}</div>',
                    unsafe_allow_html=True,
                )
            with cte:
                st.markdown(
                    f'<div class="bea-col-mapa-svc-cell">{esp_e}</div>',
                    unsafe_allow_html=True,
                )
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

    exp_nome = st.session_state.col_edit_nome or "Novo colaborador"
    if st.session_state.col_edit_id is not None and not exp_nome:
        exp_nome = f"#{st.session_state.col_edit_id}"

    st.markdown(
        '<div class="bea-cv-cag-gap" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        _col_section_title_html("3. Cadastro de novo colaborador"),
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
        ph_doc = (
            "Documento internacional (3–40 caracteres)"
            if bool(st.session_state.get(f"{fk}_docintl"))
            else "9 dígitos (NIF PT)"
        )
        nif_col, docp_col = st.columns(2, gap="small", vertical_alignment="bottom")
        with nif_col:
            c_nif = st.text_input("NIF ou documento de identificação *", key=f"{fk}_nif", placeholder=ph_doc)
        with docp_col:
            st.text_input(
                "Passaporte, Título de Residência ou Cartão Cidadão",
                key=f"{fk}_doc_par",
                placeholder="Opcional",
            )
        render_grupo_telefone(st, prefix=f"{fk}_tel_pri", label="Contacto principal *", disabled=False)

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
            c_freg = st.text_input("Freguesia (opcional)", key=f"{fk}_freg")
        r3c1, r3c2 = st.columns(2)
        with r3c1:
            c_dist = st.text_input("Distrito (opcional)", key=f"{fk}_dist")
        with r3c2:
            _col_pais_k = f"{fk}_pais"
            if _col_pais_k not in st.session_state:
                st.session_state[_col_pais_k] = "Portugal"
            c_pais = st.text_input("País *", key=_col_pais_k)

        st.markdown(_col_ficha_subsec_html("Dados da Parceria"), unsafe_allow_html=True)
        for _pk, _pd in (
            (f"{fk}_ae_sel", "Não"),
            (f"{fk}_ctr_sel", "Não"),
        ):
            if _pk not in st.session_state:
                st.session_state[_pk] = _pd
        if f"{fk}_ctr_dt" not in st.session_state:
            st.session_state[f"{fk}_ctr_dt"] = date.today()

        r_par_1 = st.columns(_COL_PAR_3W, gap="small", vertical_alignment="bottom")
        with r_par_1[0]:
            st.selectbox("Atividade Econômica Aberta? *", options=_COL_SIM_NAO, key=f"{fk}_ae_sel")
        ae_sim = str(st.session_state.get(f"{fk}_ae_sel") or "Não") == "Sim"
        with r_par_1[1]:
            st.text_input("Código da Atividade", key=f"{fk}_ae_cod", disabled=not ae_sim)
        with r_par_1[2]:
            st.text_input("Descrição da Atividade Econômica", key=f"{fk}_ae_desc", disabled=not ae_sim)

        r_par_2 = st.columns(_COL_PAR_3W, gap="small", vertical_alignment="bottom")
        with r_par_2[0]:
            st.selectbox(
                "Contrato de Prestação de Serviço assinado? *",
                options=_COL_SIM_NAO,
                key=f"{fk}_ctr_sel",
            )
        ctr_sim = str(st.session_state.get(f"{fk}_ctr_sel") or "Não") == "Sim"
        with r_par_2[1]:
            st.date_input(
                "Data de Assinatura (DD/MM/AAAA)",
                key=f"{fk}_ctr_dt",
                format="DD/MM/YYYY",
                disabled=not ctr_sim,
                min_value=date(1900, 1, 1),
            )
        with r_par_2[2]:
            st.text_input("Dados Bancários — IBAN *", key=f"{fk}_iban", placeholder="PT50 …")

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
            nat_labels_r = [_COL_MAPA_NAT_PH] + listar_naturezas_servicos_mapa_equipa()
            rnk = f"{fk}_lnat_{row_id}"
            rek = f"{fk}_lesp_{row_id}"
            rsk = f"{fk}_lsvc_{row_id}"
            if st.session_state.get(rnk) not in nat_labels_r:
                st.session_state.pop(rnk, None)
            rep_c0, rep_c1, rep_c2, rep_c3, rep_c4 = st.columns([0.95, 0.95, 1.15, 0.78, 1.0], gap="small")
            with rep_c0:
                st.selectbox("Natureza *", nat_labels_r, key=rnk)
            nat_v = str(st.session_state.get(rnk) or _COL_MAPA_NAT_PH)
            _pn = st.session_state.get(f"{fk}_lch_nat_{row_id}", "__unset__")
            if _pn == "__unset__":
                st.session_state[f"{fk}_lch_nat_{row_id}"] = nat_v
            elif str(_pn) != nat_v:
                st.session_state[f"{fk}_lch_nat_{row_id}"] = nat_v
                st.session_state.pop(rek, None)
                st.session_state.pop(rsk, None)
            rows_nat = (
                list(all_sv_detail)
                if nat_v == _COL_MAPA_NAT_PH
                else [r for r in all_sv_detail if str(r[2]).strip() == nat_v.strip()]
            )
            esp_lbls_r = [_COL_MAPA_ESP_PH] + _col_mapa_especialidades_opts(
                rows_nat,
                natureza=nat_v if nat_v != _COL_MAPA_NAT_PH else None,
            )
            if st.session_state.get(rek) not in esp_lbls_r:
                st.session_state.pop(rek, None)
            with rep_c1:
                st.selectbox("Especialidades *", esp_lbls_r, key=rek)
            esp_v = str(st.session_state.get(rek) or _COL_MAPA_ESP_PH)
            _pe = st.session_state.get(f"{fk}_lch_esp_{row_id}", "__unset__")
            if _pe == "__unset__":
                st.session_state[f"{fk}_lch_esp_{row_id}"] = esp_v
            elif str(_pe) != esp_v:
                st.session_state[f"{fk}_lch_esp_{row_id}"] = esp_v
                st.session_state.pop(rsk, None)
            if esp_v == _COL_MAPA_ESP_PH:
                rows_fin: list[tuple[int, str, str, str]] = []
                svc_choices = [_COL_MAPA_SVC_PH]
            else:
                rows_fin = _col_mapa_filtra_rows_por_especialidades(rows_nat, [esp_v])
                svc_choices = [_COL_MAPA_SVC_PH] + [f"{int(a)}|{b}" for a, b, _c, _d in rows_fin]
            if st.session_state.get(rsk) not in svc_choices:
                st.session_state.pop(rsk, None)
            with rep_c2:
                st.selectbox("Serviço ou Produto *", svc_choices, key=rsk)
            raw_svc = str(st.session_state.get(rsk) or _COL_MAPA_SVC_PH)
            if raw_svc == _COL_MAPA_SVC_PH or "|" not in raw_svc:
                sid = 0
            else:
                try:
                    sid = int(raw_svc.split("|", 1)[0])
                except ValueError:
                    sid = 0
            with rep_c3:
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
            with rep_c4:
                dlin = st.date_input(
                    "Data de Habilitação",
                    key=f"{fk}_dlin_{row_id}",
                    format="DD/MM/YYYY",
                    min_value=date(1900, 1, 1),
                )
            rb1, rb2 = st.columns([1, 4])
            with rb1:
                if len(row_ids) > 1 and st.button("Remover item", key=f"{fk}_rm_{row_id}"):
                    st.session_state.col_row_ids = [r for r in row_ids if r != row_id]
                    st.rerun()
            if sid > 0:
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
            ok_t, tel_e164, err_t = ler_e164_de_widgets(f"{fk}_tel_pri")
            if len(repasse) != len(row_ids):
                st.error("Em cada item, seleccione **Natureza**, **Especialidade** e **Serviço ou Produto** válidos.")
            elif not ok_t:
                st.error(str(err_t or "❌ Contacto inválido."))
            else:
                dn_iso = c_dn.isoformat() if c_dn else ""
                ae_aberta = str(st.session_state.get(f"{fk}_ae_sel") or "Não") == "Sim"
                ctr_ass = str(st.session_state.get(f"{fk}_ctr_sel") or "Não") == "Sim"
                d_ctr = st.session_state.get(f"{fk}_ctr_dt")
                ctr_dt_iso = d_ctr.isoformat() if ctr_ass and isinstance(d_ctr, date) else ""
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
                    numero_contato=tel_e164,
                    observacoes=c_obs or "",
                    servicos_repasse=repasse,
                    nif_ou_documento=c_nif or "",
                    identificacao_internacional=bool(c_docintl),
                    documento_passaporte_residencia_cc=str(st.session_state.get(f"{fk}_doc_par") or ""),
                    atividade_economica_aberta=ae_aberta,
                    atividade_economica_codigo=str(st.session_state.get(f"{fk}_ae_cod") or ""),
                    atividade_economica_descricao=str(st.session_state.get(f"{fk}_ae_desc") or ""),
                    contrato_prestacao_assinado=ctr_ass,
                    contrato_prestacao_data_assinatura=ctr_dt_iso,
                    iban_dados_bancarios=str(st.session_state.get(f"{fk}_iban") or ""),
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

    render_colaboradores_disponibilidade_setor()

    render_setor4_relatorio_repasse_admin(fk=fk)
