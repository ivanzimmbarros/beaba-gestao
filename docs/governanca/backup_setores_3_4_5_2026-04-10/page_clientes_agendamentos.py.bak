"""Consolidação Clientes + Agendamentos — Setor 1 (pesquisa), 2 e 4 conforme Proposta; Setor 3 limpar."""

from __future__ import annotations

import html
from datetime import date, datetime

import streamlit as st

from src.pages.theme import get_beaba_css  # noqa: F401 — BeaBa Sereno (CSS em app.main)
from src.modules.agendamento import obter_resumo_agendamentos_cliente_setor2_proposta
from src.modules.catalogo import centavos_para_texto_euros
from src.modules.cliente import (
    atualizar_cliente,
    buscar_clientes_por_nif_email_telefone,
    obter_cliente_completo,
)
from src.modules.constants import SEXOS
from src.modules.nif import normalizar_nif_armazenamento
from src.modules.telefone import normalizar_telefone_legado_ou_e164
from src.modules.validators import email_valido, parse_data_iso
from src.ui.telefone_widgets import ler_e164_de_widgets, preencher_session_telefone_de_e164, render_grupo_telefone
from src.ui.widgets.cliente_search import CLIENTE_SEARCH_DATE_MIN, render_cliente_search_widget

_CAG_PREFIX = "cag_"

_SUB_LORA = (
    "font-family: var(--bea-vs-serif-t), Lora, Georgia, serif; "
    "color: var(--bea-vs-bordeaux, #3b1c2f); font-weight: 700; margin: 0 0 0.4rem 0;"
)

_CAG_CHERRY_BTN_CSS = """
<style>
/* Setor 4 — único botão primário desta página: Salvar Alterações */
div[data-testid="stAppViewContainer"] button[kind="primary"] {
    background-color: #C43048 !important;
    color: #ffffff !important;
    border: 1px solid #9b2438 !important;
}
</style>
"""


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


def cag_valores_setor2_identificacao_basica(cli: dict | None) -> tuple[str, str, str]:
    """Nome completo, NIF/documento, telefone (E.164) — alinhado a B.1.1; para testes."""
    if cli is None:
        return ("-", "-", "-")
    return (
        str(cli.get("nome") or "-"),
        str(cli.get("nif_ou_documento") or "-"),
        str(cli.get("whatsapp") or "-"),
    )


def _cag_valor_moeda_centavos(c: int) -> str:
    return centavos_para_texto_euros(int(c)).replace(".", ",")


def _cag_carregar_ficha(fk: str, d: dict) -> None:
    """Igual a `page_clientes._carregar_ficha_em_formulario`, com `cag_n_emergency`."""
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
        st.session_state.cag_n_emergency = max(1, min(10, len(em)))
        for j, (en, et) in enumerate(em):
            st.session_state[f"{fk}_em_n_{j}"] = en
            preencher_session_telefone_de_e164(f"{fk}_emerg_{j}", str(et or ""))
    else:
        st.session_state[f"{fk}_tem_emerg"] = "Não"
        st.session_state.cag_n_emergency = 1
    st.session_state[f"{fk}_obs"] = d.get("observacoes") or ""


def _reset_cag_page_state() -> None:
    for k in list(st.session_state.keys()):
        if k.startswith(_CAG_PREFIX) or k == "_cag_prime":
            del st.session_state[k]
    for k in (
        "cag_ficha_loaded_sig",
        "cag_lib_edit",
        "_cag_lib_edit_prev",
        "cag_n_emergency",
        "cag_skip_uncheck_reload",
    ):
        st.session_state.pop(k, None)
    st.session_state.cag_form_v = 0
    st.session_state.cag_edit_id = None


def _card_shell(*, label: str, body_html: str) -> str:
    lab_e = html.escape(label)
    return (
        '<div style="background:linear-gradient(165deg,#F0FDF4 0%,#ECFDF5 50%,#D1FAE5 100%);'
        "border:1px solid rgba(22,101,52,0.12);border-radius:18px;padding:0.65rem 0.8rem;"
        'min-height:5.5rem;box-shadow:0 1px 3px rgba(15,118,110,0.06);">'
        f'<p style="margin:0 0 8px 0;font-size:0.72rem;color:#64748B;font-family:Montserrat,sans-serif;line-height:1.25;">{lab_e}</p>'
        f"{body_html}</div>"
    )


def _html_linhas_natureza(rows: list[tuple[str, int]]) -> str:
    if not rows:
        return '<p style="margin:0;color:#64748B;font-size:0.88rem;">—</p>'
    parts: list[str] = []
    for nat, q in rows:
        parts.append(
            "<p style='margin:3px 0;font-size:0.9rem;'>"
            f"<span style='font-weight:600;color:var(--bea-vs-bordeaux,#3b1c2f);'>"
            f"{html.escape(nat)}</span>: {int(q)}</p>"
        )
    return "".join(parts)


def _render_cag_setor2_dados_pessoais(*, cli: dict | None) -> None:
    st.markdown(
        f'<div class="bea-proto-scope"><p style="{_SUB_LORA} font-size:1.05rem;">Dados Pessoais</p></div>',
        unsafe_allow_html=True,
    )
    nome, doc, tel = cag_valores_setor2_identificacao_basica(cli)
    key_suf = str(cli.get("id")) if cli else "none"
    lbl = ("Nome Completo", "NIF ou Documento de Identificação", "Telefone")
    vals = (nome, doc, tel)
    keys_k = ("nome", "ndoc", "tel")
    cols = st.columns(3)
    for c, label, val, kpart in zip(cols, lbl, vals, keys_k):
        with c:
            st.caption(label)
            st.text_input(
                label,
                value=val,
                key=f"cag_s2_dp_{key_suf}_{kpart}",
                disabled=True,
                label_visibility="collapsed",
            )
    st.divider()


def _render_cag_setor2_resumo_agendamentos(*, resumo: dict) -> None:
    st.markdown(
        f'<div class="bea-proto-scope"><p style="{_SUB_LORA} font-size:1.05rem;">'
        "Resumo Geral: Agendamentos</p></div>",
        unsafe_allow_html=True,
    )
    c30 = resumo.get("previstos_30d_por_natureza") or []
    c10 = resumo.get("previstos_10d_por_natureza") or []
    pend_n = resumo.get("pendente_pgto_por_natureza") or []
    pend_v = int(resumo.get("pendente_pgto_valor_total_centavos") or 0)
    n_can = int(resumo.get("cancelados_60d_total") or 0)

    r1 = st.columns(5)
    labels = (
        "Total de Agendamentos previstos para os próximos 30 dias",
        "Total de Agendamentos previstos para os próximos 10 dias",
        "Qtde Total de Serviços com Pendência de Pagamento",
        "Valor Total Acumulado de Serviços com Pendencia de Pagamento",
        "Histórico de Cancelamento do Cliente",
    )
    bodies = (
        _html_linhas_natureza(list(c30)),
        _html_linhas_natureza(list(c10)),
        _html_linhas_natureza(list(pend_n)),
        f'<p style="margin:0;font-size:1.15rem;font-weight:700;color:var(--bea-vs-bordeaux,#3b1c2f);">'
        f"{html.escape(_cag_valor_moeda_centavos(pend_v))}</p>",
        f'<p style="margin:0;font-size:1.15rem;font-weight:700;color:var(--bea-vs-bordeaux,#3b1c2f);">'
        f"{html.escape(str(n_can))}</p>",
    )
    for col, lab, body in zip(r1, labels, bodies):
        with col:
            st.markdown(_card_shell(label=lab, body_html=body), unsafe_allow_html=True)


def _render_cag_setor4_ficha(*, eid: int, fk: str) -> None:
    st.markdown(_CAG_CHERRY_BTN_CSS, unsafe_allow_html=True)
    st.markdown(
        f'<div class="bea-proto-scope"><p style="font-size:1.2rem;letter-spacing:0.01em;{_SUB_LORA}">'
        "4. Ficha do Cliente</p></div>",
        unsafe_allow_html=True,
    )

    lib = st.checkbox(
        "Liberar edição do Cadastro do Cliente Selecionado",
        key="cag_lib_edit",
    )
    prev = st.session_state.get("_cag_lib_edit_prev", False)
    if prev and not lib and not st.session_state.pop("cag_skip_uncheck_reload", False):
        d0 = obter_cliente_completo(int(eid))
        if d0:
            _cag_carregar_ficha(fk, d0)
    st.session_state._cag_lib_edit_prev = lib

    dis = not lib

    with st.container(border=True):
        st.markdown("##### Dados pessoais")
        st.text_input("Nome completo *", key=f"{fk}_nome", disabled=dis)
        st.checkbox(
            "Documento de identificação **não** é NIF português",
            key=f"{fk}_docintl",
            disabled=dis,
        )
        doc_intl = bool(st.session_state.get(f"{fk}_docintl"))
        ph_doc = "Documento internacional (3–40 caracteres)" if doc_intl else "9 dígitos (NIF PT)"
        st.text_input(
            "NIF ou documento de identificação *",
            key=f"{fk}_nif",
            placeholder=ph_doc,
            disabled=dis,
        )
        st.date_input(
            "Data de nascimento *",
            min_value=CLIENTE_SEARCH_DATE_MIN,
            max_value=date.today(),
            format="DD/MM/YYYY",
            key=f"{fk}_dnasc",
            disabled=dis,
        )
        render_grupo_telefone(st, prefix=f"{fk}_tel_pri", label="Contacto principal *", disabled=dis)
        st.text_input("Email *", key=f"{fk}_email", disabled=dis)
        sexo = st.selectbox("Sexo *", SEXOS, key=f"{fk}_sexo", disabled=dis)

        gravida: bool | None = None
        data_parto: str | None = None
        if sexo == "Feminino":
            g_label = st.radio(
                "Está grávida? *",
                ["Não", "Sim"],
                horizontal=True,
                key=f"{fk}_gravida",
                disabled=dis,
            )
            gravida = g_label == "Sim"
            if gravida:
                d = st.date_input(
                    "Estimativa de data de parto *",
                    key=f"{fk}_parto",
                    format="DD/MM/YYYY",
                    min_value=CLIENTE_SEARCH_DATE_MIN,
                    disabled=dis,
                )
                data_parto = d.isoformat() if d else None
        else:
            gravida = None
            data_parto = None

        st.markdown("##### Morada")
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            end_rua = st.text_input("Rua / logradouro *", key=f"{fk}_rua", disabled=dis)
        with r1c2:
            end_num = st.text_input("Número *", key=f"{fk}_numero", disabled=dis)
        end_comp = st.text_input(
            "Complemento (opcional)",
            key=f"{fk}_comp",
            placeholder="Andar, fração, etc.",
            disabled=dis,
        )
        r2c1, r2c2, r2c3 = st.columns(3)
        with r2c1:
            end_cp = st.text_input("Código postal *", key=f"{fk}_cp", placeholder="4800-123", disabled=dis)
        with r2c2:
            end_conc = st.text_input("Concelho *", key=f"{fk}_conc", disabled=dis)
        with r2c3:
            end_freg = st.text_input("Freguesia *", key=f"{fk}_freg", disabled=dis)
        r3c1, r3c2 = st.columns(2)
        with r3c1:
            end_dist = st.text_input("Distrito (opcional)", key=f"{fk}_dist", disabled=dis)
        with r3c2:
            _pais_k = f"{fk}_pais"
            if _pais_k not in st.session_state:
                st.session_state[_pais_k] = "Portugal"
            end_pais = st.text_input("País *", key=_pais_k, disabled=dis)

        st.markdown("##### Filhos")
        tem_filhos = (
            st.radio("Possui filhos? *", ["Não", "Sim"], horizontal=True, key=f"{fk}_temf", disabled=dis)
            == "Sim"
        )
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
                    disabled=dis,
                )
            )
            for j in range(qtd):
                st.markdown(f"**Filho {j + 1}**")
                cf1, cf2, cf3 = st.columns(3)
                with cf1:
                    fn = st.text_input("Nome *", key=f"{fk}_f_nom_{j}", disabled=dis)
                with cf2:
                    idade = int(
                        st.number_input(
                            "Idade (anos) *",
                            min_value=0,
                            max_value=120,
                            value=0,
                            key=f"{fk}_f_id_{j}",
                            disabled=dis,
                        )
                    )
                with cf3:
                    sx = st.selectbox("Sexo *", SEXOS, key=f"{fk}_f_sx_{j}", disabled=dis)
                has_dn = st.checkbox(
                    "Indicar data de nascimento (opcional)",
                    key=f"{fk}_f_hasdn_{j}",
                    disabled=dis,
                )
                dn_iso: str | None = None
                if has_dn:
                    d_birth = st.date_input(
                        "Data de nascimento",
                        max_value=date.today(),
                        format="DD/MM/YYYY",
                        min_value=CLIENTE_SEARCH_DATE_MIN,
                        key=f"{fk}_f_dn_{j}",
                        disabled=dis,
                    )
                    dn_iso = d_birth.isoformat() if d_birth else None
                if dn_iso:
                    filhos.append((fn, idade, sx, dn_iso))
                else:
                    filhos.append((fn, idade, sx))

        tem_emerg = (
            st.radio(
                "Possui contacto de emergência? *",
                ["Não", "Sim"],
                horizontal=True,
                key=f"{fk}_tem_emerg",
                disabled=dis,
            )
            == "Sim"
        )
        if tem_emerg:
            st.markdown("##### Contactos de emergência")
            c_add, _ = st.columns([2, 3])
            with c_add:
                if st.button("➕ Adicionar contacto de emergência", key=f"{fk}_add_em", disabled=dis):
                    st.session_state.cag_n_emergency = min(st.session_state.cag_n_emergency + 1, 10)
                    st.rerun()

            for i in range(st.session_state.cag_n_emergency):
                st.text_input(f"Nome (emergência {i + 1})", key=f"{fk}_em_n_{i}", disabled=dis)
                render_grupo_telefone(
                    st,
                    prefix=f"{fk}_emerg_{i}",
                    label=f"Telefone (emergência {i + 1})",
                    disabled=dis,
                )

    with st.container(border=True):
        st.markdown("##### Observações")
        observacoes = st.text_area(
            "Observações",
            key=f"{fk}_obs",
            height=100,
            placeholder="Detalhes especiais sobre a pessoa (opcional).",
            disabled=dis,
        )

    d_nasc_o = st.session_state.get(f"{fk}_dnasc")
    data_nasc_iso = (
        d_nasc_o.isoformat()
        if d_nasc_o is not None and hasattr(d_nasc_o, "isoformat")
        else ""
    )

    nome = str(st.session_state.get(f"{fk}_nome", "") or "")
    nif_val = str(st.session_state.get(f"{fk}_nif", "") or "")
    end_rua = str(st.session_state.get(f"{fk}_rua", "") or "")
    end_num = str(st.session_state.get(f"{fk}_numero", "") or "")
    end_comp = str(st.session_state.get(f"{fk}_comp", "") or "")
    end_cp = str(st.session_state.get(f"{fk}_cp", "") or "")
    end_conc = str(st.session_state.get(f"{fk}_conc", "") or "")
    end_freg = str(st.session_state.get(f"{fk}_freg", "") or "")
    end_dist = str(st.session_state.get(f"{fk}_dist", "") or "")
    end_pais = str(st.session_state.get(f"{fk}_pais", "") or "Portugal")

    if st.button("Salvar Alterações", type="primary", key="cag_salvar_alt"):
        ok_t, tel_e164, err_t = ler_e164_de_widgets(f"{fk}_tel_pri")
        if not ok_t:
            st.error(err_t)
        else:
            emerg_l: list[tuple[str, str]] = []
            em_err = False
            if tem_emerg:
                for i in range(st.session_state.cag_n_emergency):
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
                    email=str(st.session_state.get(f"{fk}_email", "") or ""),
                    sexo=sexo,
                    tem_filhos=tem_filhos,
                    filhos=filhos,
                    gravida=gravida,
                    data_parto_prevista=data_parto,
                    observacoes=observacoes or "",
                    contatos_emergencia=emerg_l,
                    nif=nif_val,
                    documento_identificacao_internacional=bool(st.session_state.get(f"{fk}_docintl")),
                    data_nascimento=data_nasc_iso,
                )
                if ok:
                    st.session_state.cag_skip_uncheck_reload = True
                    st.session_state.cag_lib_edit = False
                    st.session_state._cag_lib_edit_prev = False
                    d2 = obter_cliente_completo(int(eid))
                    if d2:
                        _cag_carregar_ficha(fk, d2)
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)


def render_page_clientes_agendamentos(*, render_back_and_breadcrumb) -> None:
    render_back_and_breadcrumb(
        ["Home", "Clientes e Agendamentos", "Cadastro"],
        back_key="bea_back_clientes_agendamentos",
    )
    st.markdown(
        '<div class="bea-proto-scope"><div class="bea-pdv-titulo-wrap">'
        '<p class="bea-pdv-titulo">Cadastro de Clientes e Gestão de Agendamentos</p></div></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div style="height:6px;background:linear-gradient(90deg,#F0FDF4,#D1FAE5,#A7F3D0);'
        "border-radius:8px;margin:0 0 0.85rem 0;opacity:0.95;\"></div>",
        unsafe_allow_html=True,
    )

    if "cag_form_v" not in st.session_state:
        st.session_state.cag_form_v = 0
    if "cag_edit_id" not in st.session_state:
        st.session_state.cag_edit_id = None
    st.session_state.setdefault("cag_n_emergency", 1)

    st.markdown(
        '<div class="bea-proto-scope"><p class="bea-pdv-titulo" '
        'style="font-size:1.2rem;margin:0 0 0.5rem 0;letter-spacing:0.01em;">'
        "1. Pesquisa de Clientes</p></div>",
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        cag_busca_clicked = render_cliente_search_widget(
            key_prefix="cag_busca",
            button_type="secondary",
            minimal=True,
        )

    if cag_busca_clicked:
        nif_s = str(st.session_state.get("cag_busca_nif", "") or "").strip()
        em_s = str(st.session_state.get("cag_busca_email", "") or "").strip()
        tel_raw = str(st.session_state.get("cag_busca_tel_txt", "") or "").strip()
        use_tel = normalizar_telefone_legado_ou_e164(tel_raw) if tel_raw else ""
        busca_doc_intl = bool(st.session_state.get("cag_busca_docintl"))

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
                st.session_state.pop("cag_busca_cands", None)
            elif len(cands) == 1:
                cid = cands[0][0]
                data = obter_cliente_completo(cid)
                if not data:
                    st.error("Cliente não encontrado.")
                else:
                    st.session_state.cag_edit_id = cid
                    st.session_state.cag_form_v += 1
                    st.session_state.pop("cag_busca_cands", None)
                    st.session_state.cag_busca_nif = ""
                    st.session_state.cag_busca_email = ""
                    st.session_state.cag_busca_tel_txt = ""
                    st.session_state.cag_busca_docintl = False
                    st.success(f"Cliente encontrado (#{cid}). Pesquisa limpa para nova consulta.")
                    st.rerun()
            else:
                st.session_state.cag_busca_cands = cands
                st.rerun()

    cands_m = st.session_state.get("cag_busca_cands")
    if cands_m and len(cands_m) > 1:
        st.markdown(
            '<div class="bea-proto-scope"><p class="bea-pdv-titulo" '
            'style="font-size:1.05rem;margin:0.6rem 0 0.35rem 0;">Resultados</p></div>',
            unsafe_allow_html=True,
        )
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
                        if st.button("Carregar ficha", key=f"cag_cand_load_{cid}", width="stretch"):
                            data = obter_cliente_completo(cid)
                            if not data:
                                st.error("Cliente não encontrado.")
                            else:
                                st.session_state.cag_edit_id = cid
                                st.session_state.cag_form_v += 1
                                st.session_state.pop("cag_busca_cands", None)
                                st.session_state.cag_busca_nif = ""
                                st.session_state.cag_busca_email = ""
                                st.session_state.cag_busca_tel_txt = ""
                                st.session_state.cag_busca_docintl = False
                                st.success(f"Cliente #{cid} selecionado. Pesquisa limpa.")
                                st.rerun()

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    st.markdown(
        f'<div class="bea-proto-scope"><p style="font-size:1.2rem;letter-spacing:0.01em;{_SUB_LORA}">'
        "2. Resumo do Cliente</p></div>",
        unsafe_allow_html=True,
    )

    eid = st.session_state.cag_edit_id
    cli_data: dict | None = None
    if eid is not None:
        cli_data = obter_cliente_completo(int(eid))
        if cli_data is None:
            st.warning("Cliente seleccionado já não existe na base. Limpe o ecrã e pesquise novamente.")

    resumo_ag = (
        obter_resumo_agendamentos_cliente_setor2_proposta(int(eid))
        if eid is not None
        else obter_resumo_agendamentos_cliente_setor2_proposta(0)
    )

    _render_cag_setor2_dados_pessoais(cli=cli_data)
    _render_cag_setor2_resumo_agendamentos(resumo=resumo_ag)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div class="bea-proto-scope"><p class="bea-pdv-titulo" '
        'style="font-size:1.2rem;margin:0.5rem 0 0.35rem 0;letter-spacing:0.01em;">'
        "3. Limpar informações na página</p></div>",
        unsafe_allow_html=True,
    )
    if st.button("Limpar Informações Apresentadas", key="cag_btn_limpar_tela", type="secondary"):
        _reset_cag_page_state()
        st.rerun()

    if eid is not None and cli_data is not None:
        fv = st.session_state.cag_form_v
        fk = f"cag_{fv}"
        sig = (int(eid), fv)
        if st.session_state.get("cag_ficha_loaded_sig") != sig:
            _cag_carregar_ficha(fk, cli_data)
            st.session_state.cag_ficha_loaded_sig = sig
            st.session_state.cag_lib_edit = False
            st.session_state._cag_lib_edit_prev = False
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        _render_cag_setor4_ficha(eid=int(eid), fk=fk)
