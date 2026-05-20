"""Catálogo de serviços — UI Streamlit (E21 Fase 2: filtros, tabela, carregar ficha)."""

from __future__ import annotations

import html
import uuid
from datetime import date, datetime

import pandas as pd
import streamlit as st

from src.pages.theme import get_beaba_css  # noqa: F401 — BeaBa Sereno (CSS em app.main)
from src.modules.catalogo import (
    CAT_MSG_SUCESSO,
    MSG_REGISTRO_DUPLICADO,
    atualizar_evento_existente,
    atualizar_pacote_existente,
    atualizar_servico_fase1_existente,
    cadastrar_evento,
    cadastrar_pacote,
    cadastrar_servico_fase1,
    listar_especialidades_por_natureza,
    listar_itens_catalogo,
    listar_naturezas_catalogo,
    listar_servicos_produto_para_pacote,
    listar_servicos_sessao_para_pacote,
    obter_servico_para_formulario,
    repasse_medio_ponderado_pacote,
    salvar_especialidade_catalogo,
    salvar_natureza_catalogo,
)
from src.modules.colaborador import listar_colaboradores_resumo
from src.modules.constants import (
    NATUREZA_PACK,
    NATUREZAS_CATALOGO_FASE1,
    canon_natureza_catalogo,
)
from src.modules.validators import parse_data_iso
from src.ui.constituicao_visual_shell import inject_constituicao_cat_page

_CAT_PICK_NONE = "— Seleccione um item para carregar na ficha —"
_CAT_MODE_NAT = "Natureza"
_CAT_MODE_ESP = "Especialidade"
_CAT_MODE_SRV = "Serviço / Produto"
_CAT_FILT_TODAS_ESP = "Todas as especialidades"
_CAT_FILT_TODOS_NOMES = "Todos os serviços ou produtos"
_CAT_FLASH_KEY = "cat_save_flash"
_CAT_FOCUS_KEY = "cat_focus_widget_key"


def _cat_actor_email() -> str:
    return str(st.session_state.get("auth_user_email") or "").strip()


def _cat_naturezas_ui() -> list[str]:
    rows = listar_naturezas_catalogo()
    return [str(r["nome"]) for r in rows if str(r.get("nome") or "").strip()]


def _cat_row_label_listagem(r: dict) -> str:
    """Rótulo na listagem / filtros (apenas nome)."""
    return str(r["nome"])


def _cat_set_save_flash(kind: str, msg: str, *, focus_key: str | None = None) -> None:
    st.session_state[_CAT_FLASH_KEY] = (kind, msg, focus_key or "")


def _cat_render_pending_flash(fk: str) -> None:
    raw = st.session_state.pop(_CAT_FLASH_KEY, None)
    if not raw:
        focus_pending = st.session_state.pop(_CAT_FOCUS_KEY, None)
        if focus_pending:
            st.session_state[focus_pending] = st.session_state.get(focus_pending, "")
        return
    kind = str(raw[0])
    msg = str(raw[1])
    focus_key = str(raw[2]) if len(raw) > 2 else ""
    if kind == "success":
        st.success(msg)
    elif kind == "error_dup":
        st.error(msg)
        if st.button("Confirmar", key="cat_dup_confirm_btn"):
            if focus_key:
                st.session_state[_CAT_FOCUS_KEY] = focus_key
            st.rerun()
    else:
        st.error(msg)


def _cat_finish_save(ok: bool, msg: str, fk: str, focus_key: str) -> None:
    if ok:
        _cat_set_save_flash("success", CAT_MSG_SUCESSO)
        st.session_state.cat_edit_id = None
        st.session_state._cat_prev_sid = None
        st.session_state.cat_form_v = st.session_state.get("cat_form_v", 0) + 1
        for k in list(st.session_state.keys()):
            if k.startswith(f"{fk}_wiz") or k == f"{fk}_wiz_locked":
                try:
                    del st.session_state[k]
                except Exception:
                    pass
        st.rerun()
    if msg == MSG_REGISTRO_DUPLICADO:
        _cat_set_save_flash("error_dup", msg, focus_key=focus_key)
        st.rerun()
    st.error(msg)


def _cat_format_duration_hm_h(hours_dec: float) -> str:
    """Apresentação «H:MMh» a partir de horas decimais (valor interno do catálogo)."""
    h = float(hours_dec)
    if h < 0:
        h = 0.0
    total_min = int(round(h * 60))
    total_min = max(0, min(total_min, 24 * 60))
    hp, mp = divmod(total_min, 60)
    return f"{int(hp)}:{int(mp):02d}h"


def _cat_parse_duration_hm_h(text: str) -> tuple[bool, float, str]:
    """
    Aceita «H:MMh» ou «H:MM» (ex.: 1:30h, 0:15).
    Devolve (ok, horas_decimais, mensagem_erro). Mínimo 0:15h; máximo 24:00h.
    """
    raw = (text or "").strip().replace(" ", "")
    low = raw.lower()
    if low.endswith("h"):
        low = low[:-1]
    if not low or ":" not in low:
        return (
            False,
            0.0,
            "Indique a duração no formato horas:minutos terminado em «h» (ex.: 1:30h).",
        )
    parts = low.split(":", 1)
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        return False, 0.0, "Formato inválido. Exemplo: 1:30h."
    try:
        hp = int(parts[0].strip())
        mp = int(parts[1].strip())
    except ValueError:
        return False, 0.0, "Horas e minutos devem ser números inteiros (ex.: 1:30h)."
    if mp < 0 or mp > 59:
        return False, 0.0, "Os minutos devem estar entre 0 e 59."
    if hp < 0 or hp > 24 or (hp == 24 and mp > 0):
        return False, 0.0, "A duração máxima é 24:00h."
    total_min = hp * 60 + mp
    if total_min < 15:
        return False, 0.0, "A duração mínima é 0:15h (15 minutos)."
    if total_min > 24 * 60:
        return False, 0.0, "A duração máxima é 24:00h."
    return True, total_min / 60.0, ""


def _cat_section_title_html(title: str) -> str:
    t = html.escape(title)
    return f'<div class="bea-cv-cag-h2">{t}</div>'


def _cat_ficha_subsec_html(title: str) -> str:
    t = html.escape(title)
    return (
        f'<div class="bea-cv-cag-h2" style="font-size:1.05rem;margin:0.75rem 0 0.3rem 0;">{t}</div>'
    )


def _cat_linha_lbl_html(n: int) -> str:
    return (
        '<p style="font-family:var(--cv-sans);font-weight:600;color:#2D332F;margin:0.6rem 0 0.25rem 0;">'
        f"Linha {int(n)}</p>"
    )


def _cat_participante_lbl_html(n: int) -> str:
    return (
        '<p style="font-family:var(--cv-sans);font-weight:600;color:#2D332F;margin:0.6rem 0 0.25rem 0;">'
        f"Participante {int(n)}</p>"
    )


def _dataframe_selected_rows(ev: object | None, session_key: str) -> list[int]:
    """Lê índices de linha do retorno de `st.dataframe(..., on_select='rerun')` ou de `session_state[key]`."""
    rows: list[int] = []

    def _rows_from_selection(sel: object | None) -> list[int]:
        if sel is None:
            return []
        r = getattr(sel, "rows", None)
        if r is None and isinstance(sel, dict):
            r = sel.get("rows")
        if not r:
            return []
        return [int(x) for x in r]

    if ev is not None:
        sel = getattr(ev, "selection", None)
        if sel is None and isinstance(ev, dict):
            sel = ev.get("selection")
        rows = _rows_from_selection(sel)
    if rows:
        return rows
    raw = st.session_state.get(session_key)
    if raw is None:
        return []
    sel2 = getattr(raw, "selection", None)
    if sel2 is None and isinstance(raw, dict):
        sel2 = raw.get("selection")
    return _rows_from_selection(sel2)


def _prime_cat_form(fk: str, d: dict) -> None:
    """Preenche `st.session_state` para as chaves `fk_*` antes de renderizar o expander."""
    nat = d["natureza"]
    st.session_state[f"{fk}_nat"] = nat
    if str(nat) in NATUREZAS_CATALOGO_FASE1 and d.get("especialidade_id") is not None:
        st.session_state[f"{fk}_esp_{nat}"] = int(d["especialidade_id"])
    st.session_state[f"{fk}_nome"] = d["nome"]
    st.session_state[f"{fk}_desc"] = d["descritivo"]
    st.session_state[f"{fk}_ativo"] = bool(d.get("ativo", True))

    if nat == "Sessão":
        st.session_state[f"{fk}_sdh_disp"] = _cat_format_duration_hm_h(float(d.get("sessao_duracao_horas", 1.0)))
        st.session_state[f"{fk}_sve"] = float(d.get("sessao_valor_euros", 45.0))
    elif nat == "Produto":
        st.session_state[f"{fk}_ptipo"] = d.get("produto_tipo", "")
        st.session_state[f"{fk}_pdesc"] = d.get("produto_descricao", "")
        st.session_state[f"{fk}_pve"] = float(d.get("produto_valor_euros", 10.0))
        po = d.get("produto_origem", "proprio")
        st.session_state[f"{fk}_porig"] = "Estoque próprio" if po == "proprio" else "Repasse / consignado"
        if po == "repasse":
            modo = d.get("produto_repasse_modo", "percentual")
            if modo == "valor":
                st.session_state[f"{fk}_pmod"] = "Valor fixo"
                st.session_state[f"{fk}_prve"] = float(d.get("produto_repasse_valor_euros", 5.0))
            else:
                st.session_state[f"{fk}_pmod"] = "Percentual"
                st.session_state[f"{fk}_prpct"] = float(d.get("produto_repasse_pct", 30.0))
    elif nat == "Coworking":
        st.session_state[f"{fk}_cws"] = d.get("cowork_sala_nome", "")
        cwc = d.get("cowork_cobranca", "hora")
        st.session_state[f"{fk}_cwc"] = "Por hora" if cwc == "hora" else "Por dia"
        st.session_state[f"{fk}_cwv"] = float(d.get("cowork_valor_euros", 8.0))
    elif canon_natureza_catalogo(nat) == NATUREZA_PACK:
        linhas = d.get("pacote_linhas") or []
        st.session_state.cat_pac_row_ids = [uuid.uuid4().hex[:12] for _ in linhas]
        for prid, ln in zip(st.session_state.cat_pac_row_ids, linhas):
            st.session_state[f"{fk}_ps_{prid}"] = ln["sessao_nome"]
            st.session_state[f"{fk}_pq_{prid}"] = int(ln["quantidade"])
            st.session_state[f"{fk}_pdh_{prid}"] = float(ln.get("duracao_horas", 0.0))
        st.session_state[f"{fk}_pref"] = float(d.get("pacote_repasse_ref_pct", 50.0))
        st.session_state[f"{fk}_pval"] = float(d.get("pacote_valor_euros", 100.0))
        pop = d.get("pacote_produto_opcional")
        if pop:
            st.session_state[f"{fk}_pinc_prod"] = True
            st.session_state[f"{fk}_pnp"] = pop["nome"]
            st.session_state[f"{fk}_pqn"] = int(pop["quantidade"])
        else:
            st.session_state[f"{fk}_pinc_prod"] = False
    elif nat == "Evento":
        ds = (d.get("evento_data_iso") or "")[:10]
        if parse_data_iso(ds):
            st.session_state[f"{fk}_edt"] = datetime.strptime(ds, "%Y-%m-%d").date()
        esc = d.get("evento_escopo", "interno")
        st.session_state[f"{fk}_eesc"] = (
            "Interno (membros e colaboradores internos)"
            if esc == "interno"
            else "Com convidado (parcerias externas)"
        )
        st.session_state[f"{fk}_eloc"] = d.get("evento_local", "")
        st.session_state[f"{fk}_eobs"] = d.get("evento_observacoes", "")
        st.session_state[f"{fk}_epc"] = float(d.get("evento_preco_crianca_euros", 10.0))
        st.session_state[f"{fk}_epa"] = float(d.get("evento_preco_adulto_euros", 15.0))
        st.session_state[f"{fk}_epdf"] = float(d.get("evento_desconto_filho_euros", 0.0))
        parts = d.get("evento_participantes") or []
        colab_opts = listar_colaboradores_resumo()
        id_to_label = {i: f"{n} (#{i})" for i, n in colab_opts}
        st.session_state.cat_evt_row_ids = [uuid.uuid4().hex[:12] for _ in parts]
        for erid, row in zip(st.session_state.cat_evt_row_ids, parts):
            tipo, cid, pn, modo, pct, veur = row
            if tipo == "colaborador":
                st.session_state[f"{fk}_ept_{erid}"] = "Colaborador"
                if cid is not None and int(cid) in id_to_label:
                    st.session_state[f"{fk}_ecol_{erid}"] = id_to_label[int(cid)]
            else:
                st.session_state[f"{fk}_ept_{erid}"] = "Parceiro externo"
                st.session_state[f"{fk}_epn_{erid}"] = pn or ""
            st.session_state[f"{fk}_erm_{erid}"] = "Percentual (%)" if modo == "percentual" else "Valor fixo (€)"
            if modo == "percentual" and pct is not None:
                st.session_state[f"{fk}_epct_{erid}"] = float(pct)
            elif modo == "valor" and veur is not None:
                st.session_state[f"{fk}_eval_{erid}"] = float(veur)


def _ensure_cat_form_widget_defaults(fk: str, natureza: str) -> None:
    """Preenche defaults no session_state para widgets com `key` sem usar `value=` (evita conflito com prime)."""
    st.session_state.setdefault(f"{fk}_ativo", True)
    if natureza == "Sessão":
        st.session_state.setdefault(f"{fk}_sdh_disp", "1:00h")
        st.session_state.setdefault(f"{fk}_sve", 45.0)
    elif natureza == "Produto":
        st.session_state.setdefault(f"{fk}_pve", 10.0)
        st.session_state.setdefault(f"{fk}_porig", "Estoque próprio")
        st.session_state.setdefault(f"{fk}_pmod", "Percentual")
        st.session_state.setdefault(f"{fk}_prpct", 30.0)
        st.session_state.setdefault(f"{fk}_prve", 5.0)
    elif natureza == "Coworking":
        st.session_state.setdefault(f"{fk}_cwc", "Por hora")
        st.session_state.setdefault(f"{fk}_cwv", 8.0)
    elif natureza == NATUREZA_PACK:
        st.session_state.setdefault(f"{fk}_pval", 100.0)
        st.session_state.setdefault(f"{fk}_pinc_prod", False)
        st.session_state.setdefault(f"{fk}_pqn", 1)
    elif natureza == "Evento":
        st.session_state.setdefault(f"{fk}_edt", date.today())
        st.session_state.setdefault(f"{fk}_eesc", "Interno (membros e colaboradores internos)")
        st.session_state.setdefault(f"{fk}_epc", 10.0)
        st.session_state.setdefault(f"{fk}_epa", 15.0)
        st.session_state.setdefault(f"{fk}_epdf", 0.0)


def _render_cat_modo_natureza(fk: str) -> None:
    rows = listar_naturezas_catalogo()
    labels = ["— Nova natureza —"] + [str(r["nome"]) for r in rows]
    ids = [None] + [int(r["id"]) for r in rows]
    sel_ix = st.selectbox(
        "Naturezas cadastradas",
        range(len(labels)),
        format_func=lambda i, lb=labels: lb[int(i)],
        key=f"{fk}_nat_sel_ix",
    )
    sel_id = ids[int(sel_ix)] if int(sel_ix) > 0 else None
    preset = labels[int(sel_ix)] if int(sel_ix) > 0 else ""
    nome_key = f"{fk}_nat_nome_txt"
    if sel_id and not st.session_state.get(nome_key):
        st.session_state[nome_key] = preset
    nome_nat = st.text_input(
        "Nome da natureza *",
        key=nome_key,
        placeholder="Ex.: Sessão, Pack, Evento",
    )
    if st.button("Actualizar Catálogo", type="primary", key=f"{fk}_nat_submit"):
        ok, msg = salvar_natureza_catalogo(nome_nat, natureza_id=sel_id)
        _cat_finish_save(ok, msg, fk, nome_key)


def _render_cat_modo_especialidade(fk: str) -> None:
    nat_opts = _cat_naturezas_ui()
    if not nat_opts:
        st.warning("Cadastre pelo menos uma natureza antes de criar especialidades.")
        return
    nat_esp = st.selectbox("Natureza *", nat_opts, key=f"{fk}_esp_nat")
    rows = listar_especialidades_por_natureza(nat_esp)
    labels = ["— Nova especialidade —"] + [str(r["nome"]) for r in rows]
    ids = [None] + [int(r["id"]) for r in rows]
    sel_ix = st.selectbox(
        "Especialidades",
        range(len(labels)),
        format_func=lambda i, lb=labels: lb[int(i)],
        key=f"{fk}_esp_sel_ix",
    )
    sel_id = ids[int(sel_ix)] if int(sel_ix) > 0 else None
    preset = labels[int(sel_ix)] if int(sel_ix) > 0 else ""
    nome_key = f"{fk}_esp_nome_txt"
    if sel_id and nome_key not in st.session_state:
        st.session_state[nome_key] = preset
    nome_esp = st.text_input("Nome da especialidade *", key=nome_key, placeholder="Ex.: Massagem pré-natal")
    if st.button("Actualizar Catálogo", type="primary", key=f"{fk}_esp_submit"):
        ok, msg = salvar_especialidade_catalogo(
            nat_esp, nome_esp, especialidade_id=sel_id, descritivo=""
        )
        _cat_finish_save(ok, msg, fk, nome_key)


def _render_cat_expander_cadastro(fk: str) -> None:
    """Cadastro / edição no expander por tipo: Natureza, Especialidade ou Serviço / Produto."""
    _cat_render_pending_flash(fk)
    if st.session_state.get("cat_edit_id") is not None:
        st.session_state.setdefault(f"{fk}_cad_mode", _CAT_MODE_SRV)
    mode = st.radio(
        "O que pretende cadastrar ou editar?",
        (_CAT_MODE_NAT, _CAT_MODE_ESP, _CAT_MODE_SRV),
        horizontal=True,
        key=f"{fk}_cad_mode",
    )
    if mode == _CAT_MODE_NAT:
        _render_cat_modo_natureza(fk)
        return
    if mode == _CAT_MODE_ESP:
        _render_cat_modo_especialidade(fk)
        return

    col_nat, col_esp = st.columns(2)
    with col_nat:
        natureza = st.selectbox("1. Natureza *", _cat_naturezas_ui(), key=f"{fk}_nat")
        _ensure_cat_form_widget_defaults(fk, natureza)

    esp_id_ui: int | None = None
    rows_esp: list = []
    if natureza in NATUREZAS_CATALOGO_FASE1:
        rows_esp = listar_especialidades_por_natureza(natureza)
    with col_esp:
        if natureza in NATUREZAS_CATALOGO_FASE1 and rows_esp:
            id_to_label = {int(r["id"]): str(r["nome"]) for r in rows_esp}
            ids_esp = [int(r["id"]) for r in rows_esp]
            pref = st.session_state.get(f"{fk}_esp_{natureza}")
            default_ix = 0
            if pref in ids_esp:
                default_ix = ids_esp.index(int(pref))
            esp_id_ui = int(
                st.selectbox(
                    "2. Especialidade *",
                    ids_esp,
                    index=default_ix,
                    format_func=lambda x, _m=id_to_label: _m.get(int(x), str(x)),
                    key=f"{fk}_esp_{natureza}",
                    help="Ligação Natureza → Especialidade → Serviço.",
                )
            )
    if natureza in NATUREZAS_CATALOGO_FASE1 and not rows_esp:
        st.warning("Sem especialidades para esta natureza — execute a migração ou contacte o suporte.")

    nome = st.text_input("3. Nome do Serviço ou Produto *", key=f"{fk}_nome")
    descritivo = st.text_area(
        "Descritivo do serviço / produto *",
        key=f"{fk}_desc",
        height=88,
        placeholder="Texto para identificação e relatórios.",
    )
    ativo = st.checkbox("Serviço Disponível (serviço apto para venda)", key=f"{fk}_ativo")

    sessao_dh = 1.0
    sessao_ve = 0.0
    ptipo = ""
    pdesc = ""
    pve = 0.0
    porig = "proprio"
    pr_pct = 0.0
    pr_ve = 0.0
    cws = ""
    cwc = "hora"
    cwv = 0.0

    pac_el: list[tuple[int, int, float]] = []
    pref_pac = 50.0
    valor_pac_eur = 100.0
    prod_opt_ui: tuple[int, int] | None = None

    evt_el: list[tuple[str, int | None, str, str, float | None, float | None]] = []
    evt_data_iso = ""
    evt_local = ""
    evt_obs = ""
    evt_escopo = "interno"
    evt_pc = 10.0
    evt_pa = 15.0
    evt_pdf = 0.0

    if natureza == "Sessão":
        st.text_input(
            "Duração (HH:MM) *",
            key=f"{fk}_sdh_disp",
            placeholder="Ex.: 1:30h",
        )
        sessao_ve = float(st.number_input("Valor por sessão (€) *", min_value=0.01, step=0.5, key=f"{fk}_sve"))
    elif natureza == "Produto":
        ptipo = st.text_input("Tipo do produto *", key=f"{fk}_ptipo", placeholder="Ex.: cosmética, suplemento")
        pdesc = st.text_area("Descrição do produto", key=f"{fk}_pdesc", height=70)
        pve = float(st.number_input("Valor de venda (€) *", min_value=0.01, step=0.5, key=f"{fk}_pve"))
        porig_l = st.radio("Origem *", ["Estoque próprio", "Repasse / consignado"], horizontal=True, key=f"{fk}_porig")
        porig = "proprio" if porig_l == "Estoque próprio" else "repasse"
        if porig == "repasse":
            modo_rep = st.radio("Acordo com o proprietário *", ["Percentual", "Valor fixo"], horizontal=True, key=f"{fk}_pmod")
            if modo_rep == "Percentual":
                pr_pct = float(
                    st.number_input("Percentual de repasse (%) *", min_value=0.01, max_value=100.0, step=0.01, key=f"{fk}_prpct")
                )
            else:
                pr_ve = float(st.number_input("Valor de repasse (€) *", min_value=0.01, step=0.5, key=f"{fk}_prve"))
    elif natureza == "Coworking":
        cws = st.text_input("Nome da sala *", key=f"{fk}_cws")
        cwc_l = st.radio("Cobrança *", ["Por hora", "Por dia"], horizontal=True, key=f"{fk}_cwc")
        cwc = "hora" if cwc_l == "Por hora" else "dia"
        cwv = float(st.number_input("Valor (€) *", min_value=0.01, step=0.5, key=f"{fk}_cwv"))
    elif natureza == NATUREZA_PACK:
        opts_sess = listar_servicos_sessao_para_pacote()
        if not opts_sess:
            st.warning("Cadastre pelo menos uma **Sessão** completa no catálogo antes de montar um pacote.")
        else:
            nomes_sess = [x[1] for x in opts_sess]
            id_por_nome_sess = {x[1]: x[0] for x in opts_sess}
            if "cat_pac_row_ids" not in st.session_state:
                st.session_state.cat_pac_row_ids = [uuid.uuid4().hex[:12]]

            st.markdown(
                _cat_section_title_html("Validade do pacote — composição e valores"),
                unsafe_allow_html=True,
            )
            st.caption("Sessões incluídas, repasse de referência e preço de venda do pacote.")
            st.markdown(
                _cat_ficha_subsec_html("Composição: tipos e quantidades de sessões"),
                unsafe_allow_html=True,
            )
            st.caption("Duração `0` = usar a duração definida no catálogo para essa sessão (deve estar preenchida).")
            p_row_ids = list(st.session_state.cat_pac_row_ids)
            for pos, prid in enumerate(p_row_ids):
                st.markdown(_cat_linha_lbl_html(pos + 1), unsafe_allow_html=True)
                pc1, pc2, pc3 = st.columns([2, 1, 1])
                with pc1:
                    _psk = f"{fk}_ps_{prid}"
                    if _psk not in st.session_state and nomes_sess:
                        st.session_state[_psk] = nomes_sess[0]
                    sn = st.selectbox("Tipo de sessão *", nomes_sess, key=_psk)
                with pc2:
                    st.session_state.setdefault(f"{fk}_pq_{prid}", 1)
                    pq = int(st.number_input("Quantidade *", min_value=1, max_value=999, step=1, key=f"{fk}_pq_{prid}"))
                with pc3:
                    st.session_state.setdefault(f"{fk}_pdh_{prid}", 0.0)
                    pdh = float(
                        st.number_input(
                            "Duração (h)",
                            min_value=0.0,
                            max_value=24.0,
                            step=0.25,
                            key=f"{fk}_pdh_{prid}",
                        )
                    )
                sid_v = id_por_nome_sess[sn]
                pac_el.append((sid_v, pq, pdh))
                rc1, _ = st.columns([1, 4])
                with rc1:
                    if len(p_row_ids) > 1 and st.button("Remover linha", key=f"{fk}_prm_{prid}"):
                        st.session_state.cat_pac_row_ids = [x for x in p_row_ids if x != prid]
                        st.rerun()
            if st.button("➕ Adicionar tipo de sessão ao pacote", key=f"{fk}_padd"):
                st.session_state.cat_pac_row_ids.append(uuid.uuid4().hex[:12])
                st.rerun()

            linhas_repasse = [(a, b) for a, b, _ in pac_el]
            sug = repasse_medio_ponderado_pacote(linhas_repasse) if linhas_repasse else None
            if sug is not None:
                st.caption(
                    f"Sugestão automática (média dos repasses dos colaboradores habilitados, ponderada por quantidade): **{sug:.2f} %**"
                )
            else:
                st.caption(
                    "Sem média calculável (nenhuma sessão selecionada tem colaboradores habilitados com repasse). "
                    "Preencha o referencial manualmente."
                )
            ac1, ac2 = st.columns(2)
            with ac1:
                if st.button("Aplicar sugestão ao referencial", key=f"{fk}_apply_sug"):
                    st.session_state[f"{fk}_pref"] = round(float(sug), 2) if sug is not None else 50.0
                    st.rerun()
            with ac2:
                pass
            if f"{fk}_pref" not in st.session_state:
                st.session_state[f"{fk}_pref"] = round(float(sug), 2) if sug is not None else 50.0
            pref_pac = float(
                st.number_input(
                    "Repasse médio de referência (%) *",
                    min_value=0.01,
                    max_value=100.0,
                    step=0.01,
                    key=f"{fk}_pref",
                )
            )
            valor_pac_eur = float(
                st.number_input("Valor de venda do pacote (€) *", min_value=0.01, step=1.0, key=f"{fk}_pval")
            )

            st.markdown(
                _cat_section_title_html("Produto opcional no pacote"),
                unsafe_allow_html=True,
            )
            prod_opts = listar_servicos_produto_para_pacote()
            incluir_p = st.checkbox("Incluir produto do catálogo no pacote", key=f"{fk}_pinc_prod")
            if incluir_p and prod_opts:
                nomes_p = [x[1] for x in prod_opts]
                id_por_nome_p = {x[1]: x[0] for x in prod_opts}
                pc4, pc5 = st.columns(2)
                with pc4:
                    _pnk = f"{fk}_pnp"
                    if _pnk not in st.session_state and nomes_p:
                        st.session_state[_pnk] = nomes_p[0]
                    pn = st.selectbox("Produto *", nomes_p, key=_pnk)
                with pc5:
                    st.session_state.setdefault(f"{fk}_pqn", 1)
                    pqn = int(st.number_input("Quantidade *", min_value=1, max_value=999, step=1, key=f"{fk}_pqn"))
                prod_opt_ui = (id_por_nome_p[pn], pqn)
            elif incluir_p and not prod_opts:
                st.info("Não há produtos ativos no catálogo. Crie um item **Produto** primeiro.")

    elif natureza == "Evento":
        st.markdown(_cat_section_title_html("Dados do evento"), unsafe_allow_html=True)
        ed = st.date_input(
            "Data do evento *",
            key=f"{fk}_edt",
            format="DD/MM/YYYY",
            min_value=date(1900, 1, 1),
        )
        evt_data_iso = ed.isoformat() if ed else ""
        evt_local = st.text_input("Local de realização *", key=f"{fk}_eloc", placeholder="Morada ou espaço")
        evt_obs = st.text_area("Observações", key=f"{fk}_eobs", height=70, placeholder="Opcional.")
        esc_l = st.radio(
            "Âmbito *",
            ["Interno (membros e colaboradores internos)", "Com convidado (parcerias externas)"],
            horizontal=True,
            key=f"{fk}_eesc",
        )
        evt_escopo = "interno" if esc_l.startswith("Interno") else "convidado"

        ec1, ec2, ec3 = st.columns(3)
        with ec1:
            evt_pc = float(st.number_input("Preço venda — criança (€) *", min_value=0.01, step=0.5, key=f"{fk}_epc"))
        with ec2:
            evt_pa = float(st.number_input("Preço venda — adulto (€) *", min_value=0.01, step=0.5, key=f"{fk}_epa"))
        with ec3:
            evt_pdf = float(
                st.number_input(
                    "Desconto por filho adicional (€)",
                    min_value=0.0,
                    step=0.5,
                    key=f"{fk}_epdf",
                )
            )

        st.markdown(_cat_section_title_html("Participantes e repasse"), unsafe_allow_html=True)
        st.caption("Uma linha por colaborador ou parceiro externo; indique **percentual** ou **valor** de repasse acordado.")
        colab_opts = listar_colaboradores_resumo()
        if not colab_opts:
            st.warning("Não há colaboradores na base — adicione colaboradores para usar linhas do tipo **Colaborador**.")
        labels_c = [f"{n} (#{i})" for i, n in colab_opts]
        id_por_label_c = {f"{n} (#{i})": i for i, n in colab_opts}

        if "cat_evt_row_ids" not in st.session_state:
            st.session_state.cat_evt_row_ids = [uuid.uuid4().hex[:12]]

        erow_ids = list(st.session_state.cat_evt_row_ids)
        for pos, erid in enumerate(erow_ids):
            st.markdown(_cat_participante_lbl_html(pos + 1), unsafe_allow_html=True)
            st.session_state.setdefault(f"{fk}_ept_{erid}", "Colaborador")
            tipo_l = st.radio(
                "Tipo *",
                ["Colaborador", "Parceiro externo"],
                horizontal=True,
                key=f"{fk}_ept_{erid}",
            )
            tipo = "colaborador" if tipo_l == "Colaborador" else "parceiro"
            cid_e: int | None = None
            pn_e = ""
            if tipo == "colaborador":
                if colab_opts:
                    _eck = f"{fk}_ecol_{erid}"
                    st.session_state.setdefault(_eck, labels_c[0])
                    lb = st.selectbox("Colaborador *", labels_c, key=_eck)
                    cid_e = id_por_label_c[lb]
                else:
                    st.caption("— cadastre um colaborador para selecionar.")
            else:
                pn_e = st.text_input("Nome do parceiro *", key=f"{fk}_epn_{erid}", placeholder="Entidade ou pessoa")

            st.session_state.setdefault(f"{fk}_erm_{erid}", "Percentual (%)")
            modo_l = st.radio(
                "Repasse acordado *",
                ["Percentual (%)", "Valor fixo (€)"],
                horizontal=True,
                key=f"{fk}_erm_{erid}",
            )
            modo = "percentual" if modo_l.startswith("Percentual") else "valor"
            pct_e: float | None = None
            ve_e: float | None = None
            if modo == "percentual":
                st.session_state.setdefault(f"{fk}_epct_{erid}", 25.0)
                pct_e = float(
                    st.number_input(
                        "Repasse (%) *",
                        min_value=0.01,
                        max_value=100.0,
                        step=0.01,
                        key=f"{fk}_epct_{erid}",
                    )
                )
            else:
                st.session_state.setdefault(f"{fk}_eval_{erid}", 50.0)
                ve_e = float(st.number_input("Repasse (€) *", min_value=0.01, step=0.5, key=f"{fk}_eval_{erid}"))

            evt_el.append((tipo, cid_e, pn_e, modo, pct_e, ve_e))

            er1, _ = st.columns([1, 4])
            with er1:
                if len(erow_ids) > 1 and st.button("Remover linha", key=f"{fk}_ermv_{erid}"):
                    st.session_state.cat_evt_row_ids = [x for x in erow_ids if x != erid]
                    st.rerun()

        if st.button("➕ Adicionar participante", key=f"{fk}_eadd"):
            st.session_state.cat_evt_row_ids.append(uuid.uuid4().hex[:12])
            st.rerun()

    edit_id_submit = st.session_state.get("cat_edit_id")
    actor = _cat_actor_email()
    if st.button("Actualizar Catálogo", type="primary", key=f"{fk}_submit"):
        skip_submit = False
        if natureza == "Sessão":
            raw_sdh = str(st.session_state.get(f"{fk}_sdh_disp", "") or "").strip()
            ok_sdh, sdh_val, err_sdh = _cat_parse_duration_hm_h(raw_sdh)
            if not ok_sdh:
                st.error(err_sdh)
                skip_submit = True
            else:
                sessao_dh = sdh_val
        if skip_submit:
            pass
        elif natureza == NATUREZA_PACK:
            if not pac_el:
                st.error("Defina a composição do pacote (sessões).")
            else:
                linhas_db = [(sid, q, (dh if dh > 0 else None)) for sid, q, dh in pac_el]
                if edit_id_submit:
                    ok, msg = atualizar_pacote_existente(
                        int(edit_id_submit),
                        nome,
                        descritivo,
                        ativo,
                        linhas_db,
                        prod_opt_ui,
                        pref_pac,
                        valor_pac_eur,
                    )
                else:
                    ok, msg = cadastrar_pacote(
                        nome,
                        descritivo,
                        ativo,
                        linhas_db,
                        prod_opt_ui,
                        pref_pac,
                        valor_pac_eur,
                    )
                if ok:
                    st.session_state.cat_pac_row_ids = [uuid.uuid4().hex[:12]]
                _cat_finish_save(ok, msg, fk, f"{fk}_nome")
        elif natureza == "Evento":
            if edit_id_submit:
                ok, msg = atualizar_evento_existente(
                    int(edit_id_submit),
                    nome,
                    descritivo,
                    ativo,
                    evt_data_iso,
                    evt_local,
                    evt_obs,
                    evt_escopo,
                    evt_pc,
                    evt_pa,
                    evt_pdf,
                    evt_el,
                )
            else:
                ok, msg = cadastrar_evento(
                    nome,
                    descritivo,
                    ativo,
                    evt_data_iso,
                    evt_local,
                    evt_obs,
                    evt_escopo,
                    evt_pc,
                    evt_pa,
                    evt_pdf,
                    evt_el,
                )
            if ok:
                st.session_state.cat_evt_row_ids = [uuid.uuid4().hex[:12]]
            _cat_finish_save(ok, msg, fk, f"{fk}_nome")
        else:
            if edit_id_submit:
                ok, msg = atualizar_servico_fase1_existente(
                    int(edit_id_submit),
                    natureza,
                    nome,
                    descritivo,
                    ativo,
                    alterado_por=actor,
                    especialidade_id=esp_id_ui if natureza in NATUREZAS_CATALOGO_FASE1 else None,
                    sessao_duracao_horas=sessao_dh if natureza == "Sessão" else None,
                    sessao_valor_euros=sessao_ve if natureza == "Sessão" else None,
                    produto_tipo=ptipo if natureza == "Produto" else "",
                    produto_descricao=pdesc if natureza == "Produto" else "",
                    produto_valor_euros=pve if natureza == "Produto" else None,
                    produto_origem=porig if natureza == "Produto" else "",
                    produto_repasse_pct=pr_pct if natureza == "Produto" and porig == "repasse" and pr_pct > 0 else None,
                    produto_repasse_valor_euros=pr_ve if natureza == "Produto" and porig == "repasse" and pr_ve > 0 else None,
                    cowork_sala_nome=cws if natureza == "Coworking" else "",
                    cowork_cobranca=cwc if natureza == "Coworking" else "",
                    cowork_valor_euros=cwv if natureza == "Coworking" else None,
                )
            else:
                ok, msg = cadastrar_servico_fase1(
                    natureza,
                    nome,
                    descritivo,
                    ativo,
                    cadastrado_por=actor,
                    especialidade_id=esp_id_ui if natureza in NATUREZAS_CATALOGO_FASE1 else None,
                    sessao_duracao_horas=sessao_dh if natureza == "Sessão" else None,
                    sessao_valor_euros=sessao_ve if natureza == "Sessão" else None,
                    produto_tipo=ptipo if natureza == "Produto" else "",
                    produto_descricao=pdesc if natureza == "Produto" else "",
                    produto_valor_euros=pve if natureza == "Produto" else None,
                    produto_origem=porig if natureza == "Produto" else "",
                    produto_repasse_pct=pr_pct if natureza == "Produto" and porig == "repasse" and pr_pct > 0 else None,
                    produto_repasse_valor_euros=pr_ve if natureza == "Produto" and porig == "repasse" and pr_ve > 0 else None,
                    cowork_sala_nome=cws if natureza == "Coworking" else "",
                    cowork_cobranca=cwc if natureza == "Coworking" else "",
                    cowork_valor_euros=cwv if natureza == "Coworking" else None,
                )
            _cat_finish_save(ok, msg, fk, f"{fk}_nome")


def render_page_catalogo(*, render_back_and_breadcrumb) -> None:
    inject_constituicao_cat_page()
    render_back_and_breadcrumb(["Home", "Catálogo"], back_key="bea_back_catalogo")
    st.markdown(
        '<h1 class="bea-cv-cag-h1">Catálogo de serviços</h1>',
        unsafe_allow_html=True,
    )
    st.caption("Controle de todos os serviços prestados e disponíveis para oferta")
    st.markdown(
        '<div class="bea-cv-cag-gap" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )

    if "cat_form_v" not in st.session_state:
        st.session_state.cat_form_v = 0
    if "cat_edit_id" not in st.session_state:
        st.session_state.cat_edit_id = None

    fv = st.session_state.cat_form_v
    fk = f"cat_form_{fv}"

    if "_cat_prime_catalog" in st.session_state:
        prime = st.session_state.pop("_cat_prime_catalog")
        if prime.get("fk_target") == fk:
            _prime_cat_form(fk, prime["data"])

    with st.expander("Cadastrar ou editar item", expanded=True):
        _render_cat_expander_cadastro(fk)

    itens_all = listar_itens_catalogo()
    st.markdown(
        '<div class="bea-cv-cag-gap" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    st.markdown(_cat_section_title_html("Itens registados"), unsafe_allow_html=True)
    c_nat, c_esp, c_nom, c_stat = st.columns([1.15, 1.15, 2.0, 0.9])
    with c_nat:
        _nat_filt = _cat_naturezas_ui()
        sel_nat = st.multiselect(
            "Natureza",
            _nat_filt,
            default=_nat_filt,
            key="cat_ui_filt_nat",
        )
    por_natureza = [r for r in itens_all if (not sel_nat or r["natureza"] in sel_nat)]
    esp_opts = [_CAT_FILT_TODAS_ESP] + sorted(
        {str(r.get("especialidade") or "").strip() or "—" for r in por_natureza},
        key=lambda s: (s == "—", s.lower()),
    )
    if st.session_state.get("cat_ui_filt_esp") not in esp_opts:
        st.session_state["cat_ui_filt_esp"] = esp_opts[0]
    with c_esp:
        sel_esp = st.selectbox(
            "Especialidades",
            esp_opts,
            key="cat_ui_filt_esp",
            help="Opções conforme as naturezas seleccionadas à esquerda.",
        )
    por_esp = por_natureza
    if sel_esp != _CAT_FILT_TODAS_ESP:
        por_esp = [r for r in por_natureza if str(r.get("especialidade") or "—") == sel_esp]
    nom_opts = [_CAT_FILT_TODOS_NOMES] + [
        _cat_row_label_listagem(r) for r in sorted(por_esp, key=lambda x: (str(x["nome"]).lower(), int(x["id"])))
    ]
    if st.session_state.get("cat_ui_filt_nome_sel") not in nom_opts:
        st.session_state["cat_ui_filt_nome_sel"] = nom_opts[0]
    with c_nom:
        sel_nom_lbl = st.selectbox(
            "Nome do Serviço ou Produto",
            nom_opts,
            key="cat_ui_filt_nome_sel",
            help="Itens conforme naturezas e especialidade seleccionadas.",
        )
    with c_stat:
        st_f = st.selectbox("Status", ["Todos", "Ativo", "Inativo"], key="cat_ui_filt_stat")

    def _keep(r: dict) -> bool:
        if sel_nat and r["natureza"] not in sel_nat:
            return False
        if sel_esp != _CAT_FILT_TODAS_ESP and str(r.get("especialidade") or "—") != sel_esp:
            return False
        if sel_nom_lbl != _CAT_FILT_TODOS_NOMES and _cat_row_label_listagem(r) != sel_nom_lbl:
            return False
        if st_f == "Ativo" and r["ativo"] != "Sim":
            return False
        if st_f == "Inativo" and r["ativo"] != "Não":
            return False
        return True

    itens = [r for r in itens_all if _keep(r)]

    if not itens:
        st.info("Nenhum item com os filtros actuais.")
        lab_to_id: dict[str, int] = {}
        opts_pick = [_CAT_PICK_NONE]
    else:
        lab_to_id = {str(r["nome"]): int(r["id"]) for r in itens}
        opts_pick = [_CAT_PICK_NONE] + list(lab_to_id.keys())

    # Não alterar `cat_pick_item` depois do selectbox (StreamlitAPIException). Sincronizar só aqui.
    if "_cat_pending_pick_item" in st.session_state:
        st.session_state["cat_pick_item"] = st.session_state.pop("_cat_pending_pick_item")

    c_pick, c_clr = st.columns([3, 1])
    with c_pick:
        sel_item = st.selectbox("Selecionar item para edição", opts_pick, key="cat_pick_item")
    with c_clr:
        st.write("")
        if st.button("Limpar edição", key="cat_btn_clear_edit"):
            st.session_state.cat_edit_id = None
            st.session_state._cat_prev_sid = None
            st.session_state["_cat_pending_pick_item"] = _CAT_PICK_NONE
            st.session_state.cat_form_v = st.session_state.get("cat_form_v", 0) + 1
            st.rerun()

    if sel_item != _CAT_PICK_NONE and sel_item in lab_to_id:
        sid_sb = lab_to_id[sel_item]
        if st.session_state.get("_cat_prev_sid") != sid_sb:
            data = obter_servico_para_formulario(sid_sb)
            if data:
                st.session_state.cat_form_v = st.session_state.get("cat_form_v", 0) + 1
                nfk = f"cat_form_{st.session_state.cat_form_v}"
                st.session_state._cat_prime_catalog = {"fk_target": nfk, "data": data}
                st.session_state.cat_edit_id = sid_sb
                st.session_state._cat_prev_sid = sid_sb
                st.rerun()

    if itens:
        df = pd.DataFrame(
            {
                "id": [r["id"] for r in itens],
                "Nome": [r["nome"] for r in itens],
                "Valor de Venda": [r.get("valor_venda") or "—" for r in itens],
                "Natureza": [r["natureza"] for r in itens],
                "Especialidade": [r.get("especialidade", "—") for r in itens],
                "Ativo": [r["ativo"] for r in itens],
                "Cadastrado por": [r.get("cadastrado_por", "—") for r in itens],
                "Última alteração": [r.get("ultima_alteracao", "—") for r in itens],
                "Descritivo": [r["descritivo"] for r in itens],
                "Detalhes": [r["detalhes"] for r in itens],
            }
        )
        ev = st.dataframe(
            df,
            width="stretch",
            on_select="rerun",
            selection_mode="single-row",
            key="cat_tbl_df",
            hide_index=True,
        )
        rows_sel = _dataframe_selected_rows(ev, "cat_tbl_df")
        if rows_sel:
            idx = int(rows_sel[0])
            if 0 <= idx < len(df):
                sid_df = int(df.iloc[idx]["id"])
                pick_lbl = str(df.iloc[idx]["Nome"])
                if st.session_state.get("_cat_prev_sid") != sid_df:
                    data = obter_servico_para_formulario(sid_df)
                    if data:
                        st.session_state.cat_form_v = st.session_state.get("cat_form_v", 0) + 1
                        nfk = f"cat_form_{st.session_state.cat_form_v}"
                        st.session_state._cat_prime_catalog = {"fk_target": nfk, "data": data}
                        st.session_state.cat_edit_id = sid_df
                        st.session_state._cat_prev_sid = sid_df
                        if pick_lbl in lab_to_id:
                            st.session_state["_cat_pending_pick_item"] = pick_lbl
                        st.rerun()
