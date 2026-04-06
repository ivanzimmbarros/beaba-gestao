"""
Aplicação Streamlit BeaBa Gestão — shell V11.0 (tema + dashboard de 4 blocos).
Referência: docs/CADERNO_MESTRE.md
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

import streamlit as st

from src.database.connection import create_tables
from src.modules.catalogo import (
    cadastrar_evento,
    cadastrar_pacote,
    cadastrar_servico_fase1,
    listar_itens_catalogo,
    listar_servicos_produto_para_pacote,
    listar_servicos_sessao_para_pacote,
    repasse_medio_ponderado_pacote,
)
from src.modules.cliente import cadastrar_cliente
from src.ui.page_agendamentos import render_page_agendamentos
from src.ui.page_dashboards import render_page_dashboards
from src.ui.page_fluxo_gestao import render_page_fluxo_gestao
from src.ui.page_vendas import render_page_vendas
from src.modules.colaborador import (
    atualizar_colaborador,
    cadastrar_colaborador,
    listar_colaboradores_resumo,
    listar_servicos,
    obter_colaborador,
)
from src.modules.constants import NATUREZAS_CATALOGO_FASE3, SEXOS
from src.modules.validators import parse_data_iso
from src.ui.theme import inject_bea_theme

st.set_page_config(
    page_title="BeaBa Gestão",
    page_icon="⚜️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

create_tables()
inject_bea_theme()

if "page" not in st.session_state:
    st.session_state.page = "home"


def _nav_home() -> None:
    st.session_state.page = "home"


def _render_back_and_breadcrumb(trail: list[str], *, back_key: str) -> None:
    """100% das vistas internas: retorno + breadcrumbs (CADERNO V11.0)."""
    c_back, _ = st.columns([1, 4])
    with c_back:
        if st.button("← Voltar ao Início", key=back_key):
            _nav_home()
    st.markdown(
        '<p class="bea-breadcrumb">' + " › ".join(trail) + "</p>",
        unsafe_allow_html=True,
    )


def _page_home() -> None:
    st.markdown(
        '<h1 class="bea-title" style="text-align:center;margin-bottom:0.25rem;">BeaBa Gestão</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="text-align:center;font-family:Montserrat,sans-serif;color:#545454;opacity:0.85;">'
        "Centro terapêutico — painel operacional</p>",
        unsafe_allow_html=True,
    )
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        """
        <style>
        .bea-dash-wrap { max-width: 920px; margin: 0 auto; }
        </style>
        <div class="bea-dash-wrap">
        """,
        unsafe_allow_html=True,
    )

    row1 = st.columns(2)
    with row1[0]:
        if st.button("Gestão de Clientes", use_container_width=True, type="primary"):
            st.session_state.page = "clientes"
    with row1[1]:
        if st.button("Gestão de Colaboradores", use_container_width=True, type="secondary"):
            st.session_state.page = "colaboradores"

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    row2 = st.columns(2)
    with row2[0]:
        if st.button("Catálogo de Serviços", use_container_width=True, type="primary"):
            st.session_state.page = "catalogo"
    with row2[1]:
        if st.button("Painel de Vendas", use_container_width=True, type="secondary"):
            st.session_state.page = "vendas"

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    row3 = st.columns(2)
    with row3[0]:
        if st.button("Agendamentos", use_container_width=True, type="primary"):
            st.session_state.page = "agendamentos"
    with row3[1]:
        if st.button("Dashboards e Relatórios", use_container_width=True, type="secondary"):
            st.session_state.page = "dashboards"

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    if st.button(
        "Fluxo e governança (status da demanda)",
        use_container_width=True,
        type="secondary",
    ):
        st.session_state.page = "fluxo_gestao"

    st.markdown("</div>", unsafe_allow_html=True)


def _page_clientes() -> None:
    _render_back_and_breadcrumb(["Home", "Clientes", "Cadastro"], back_key="bea_back_clientes")
    st.markdown("### Cadastro de clientes")
    st.caption(
        "Campos obrigatórios, exceto contactos de emergência. "
        "Número de contacto principal: 11 dígitos (DDD + número), único na base."
    )

    if "cli_form_v" not in st.session_state:
        st.session_state.cli_form_v = 0
    if "cli_n_emergency" not in st.session_state:
        st.session_state.cli_n_emergency = 1

    fv = st.session_state.cli_form_v
    fk = f"cli_{fv}"

    st.subheader("Dados pessoais")
    nome = st.text_input("Nome completo *", key=f"{fk}_nome")
    numero = st.text_input("Número de contacto *", key=f"{fk}_num", placeholder="DDD + número (11 dígitos)")
    email = st.text_input("Email *", key=f"{fk}_email")
    sexo = st.selectbox("Sexo *", SEXOS, key=f"{fk}_sexo")

    gravida: bool | None = None
    data_parto: str | None = None
    if sexo == "Feminino":
        g_label = st.radio("Está grávida? *", ["Não", "Sim"], horizontal=True, key=f"{fk}_gravida")
        gravida = g_label == "Sim"
        if gravida:
            d = st.date_input("Estimativa de data de parto *", key=f"{fk}_parto")
            data_parto = d.isoformat() if d else None
    else:
        gravida = None
        data_parto = None

    st.subheader("Morada (estruturada)")
    st.caption("Campos separados para pesquisas e relatórios futuros. Código postal: formato XXXX-XXX.")
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
        end_pais = st.text_input("País *", key=f"{fk}_pais", value="Portugal")

    st.subheader("Filhos")
    tem_filhos = st.radio("Possui filhos? *", ["Não", "Sim"], horizontal=True, key=f"{fk}_temf") == "Sim"
    filhos: list[tuple[str, int, str]] = []
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
                fn = st.text_input(f"Nome *", key=f"{fk}_f_nom_{j}")
            with cf2:
                idade = int(
                    st.number_input(
                        f"Idade (anos) *",
                        min_value=0,
                        max_value=120,
                        value=0,
                        key=f"{fk}_f_id_{j}",
                    )
                )
            with cf3:
                sx = st.selectbox(f"Sexo *", SEXOS, key=f"{fk}_f_sx_{j}")
            filhos.append((fn, idade, sx))

    st.subheader("Contactos de emergência (opcional)")
    st.caption("Pode adicionar vários. Cada linha válida exige nome e número (11 dígitos).")
    c_add, _ = st.columns([2, 3])
    with c_add:
        if st.button("➕ Adicionar contacto de emergência", key=f"{fk}_add_em"):
            st.session_state.cli_n_emergency = min(st.session_state.cli_n_emergency + 1, 10)

    emerg: list[tuple[str, str]] = []
    for i in range(st.session_state.cli_n_emergency):
        ec1, ec2 = st.columns(2)
        with ec1:
            en = st.text_input(f"Nome (emergência {i + 1})", key=f"{fk}_em_n_{i}")
        with ec2:
            et = st.text_input(f"Número de contacto (emergência {i + 1})", key=f"{fk}_em_t_{i}")
        emerg.append((en or "", et or ""))

    st.subheader("Observações")
    observacoes = st.text_area(
        "Observações",
        key=f"{fk}_obs",
        height=100,
        placeholder="Detalhes especiais sobre a pessoa (opcional).",
    )

    if st.button("Cadastrar cliente", type="primary", key=f"{fk}_submit"):
        ok, msg = cadastrar_cliente(
            nome=nome,
            numero_contato=numero,
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
            contatos_emergencia=emerg,
        )
        if ok:
            st.session_state.cli_form_v += 1
            st.session_state.cli_n_emergency = 1
            st.success(msg)
        else:
            st.error(msg)


def _page_colaboradores() -> None:
    _render_back_and_breadcrumb(["Home", "Colaboradores", "Cadastro"], back_key="bea_back_colaboradores")
    st.markdown("### Gestão de colaboradores")
    st.caption(
        "Contacto exclusivo (11 dígitos). Pelo menos uma linha de serviço ativa: repasse 0,01%–100,00% e "
        "data de inserção da linha (não confundir com a data de cadastro do colaborador)."
    )

    if "col_form_v" not in st.session_state:
        st.session_state.col_form_v = 0
    if "col_row_ids" not in st.session_state:
        st.session_state.col_row_ids = [uuid.uuid4().hex[:12]]
    if "col_edit_id" not in st.session_state:
        st.session_state.col_edit_id = None

    fv = st.session_state.col_form_v
    fk = f"col_{fv}"

    if "_col_prime" in st.session_state:
        prime = st.session_state.pop("_col_prime")
        if prime.get("fk_target") == fk:
            d = prime["data"]
            st.session_state[f"{fk}_nome"] = d["nome"]
            st.session_state[f"{fk}_sexo"] = d["sexo"]
            st.session_state[f"{fk}_dn"] = datetime.strptime(d["data_nascimento"][:10], "%Y-%m-%d").date()
            st.session_state[f"{fk}_email"] = d["email"]
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
                    datetime.strptime(di, "%Y-%m-%d").date() if parse_data_iso(di) else date.today()
                )

    servicos_opts = listar_servicos()
    if not servicos_opts:
        st.error(
            "Não há serviços ativos na base. Utilize o Catálogo de Serviços para criar itens ativos ou contacte o administrador."
        )
        if st.button("Abrir Catálogo de Serviços", key=f"{fk}_goto_cat_empty"):
            st.session_state.page = "catalogo"
        return

    nomes_servicos = [row[1] for row in servicos_opts]
    id_por_nome: dict[str, int] = {row[1]: row[0] for row in servicos_opts}

    colab_resumo = listar_colaboradores_resumo()
    if colab_resumo:
        st.subheader("Edição de ficha")
        labels = [f"{nome} (#{cid})" for cid, nome in colab_resumo]
        ec1, ec2, ec3 = st.columns([2, 1, 1])
        with ec1:
            pick = st.selectbox("Colaborador", ["— Novo cadastro —"] + labels, key=f"{fk}_pick_colab")
        with ec2:
            st.write("")
            if st.button("Carregar para edição", key=f"{fk}_load_colab"):
                if pick == "— Novo cadastro —":
                    st.warning("Selecione um colaborador na lista.")
                else:
                    idx = labels.index(pick)
                    cid = colab_resumo[idx][0]
                    data = obter_colaborador(cid)
                    if not data or not data["linhas"]:
                        st.error("Não foi possível carregar a ficha.")
                    else:
                        st.session_state.col_edit_id = cid
                        st.session_state.col_form_v += 1
                        fv2 = st.session_state.col_form_v
                        st.session_state.col_row_ids = [uuid.uuid4().hex[:12] for _ in data["linhas"]]
                        st.session_state._col_prime = {"fk_target": f"col_{fv2}", "data": data}
                        st.rerun()
        with ec3:
            st.write("")
            if st.button("Novo cadastro limpo", key=f"{fk}_reset_new"):
                st.session_state.col_edit_id = None
                st.session_state.col_form_v += 1
                st.session_state.col_row_ids = [uuid.uuid4().hex[:12]]
                st.rerun()
        if st.session_state.col_edit_id is not None:
            st.caption(f"A editar colaborador **#{st.session_state.col_edit_id}** — guarde com **Guardar alterações**.")

    st.subheader("Dados pessoais")
    c_nome = st.text_input("Nome completo *", key=f"{fk}_nome")
    c_sexo = st.selectbox("Sexo *", SEXOS, key=f"{fk}_sexo")
    c_dn = st.date_input("Data de nascimento *", key=f"{fk}_dn")
    c_email = st.text_input("Email *", key=f"{fk}_email")
    c_num = st.text_input("Número de contacto *", key=f"{fk}_num", placeholder="11 dígitos, exclusivo")

    st.subheader("Morada (estruturada)")
    st.caption("Mesma estrutura que o cadastro de clientes. Código postal: XXXX-XXX.")
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
        c_pais = st.text_input("País *", key=f"{fk}_pais", value="Portugal")

    st.subheader("Serviços habilitados e repasse")
    st.caption("Serviços ativos do catálogo. Cada linha tem data de **inserção da habilitação** (relatórios de desempenho).")
    if st.button("Abrir área Catálogo de Serviços", key=f"{fk}_goto_cat"):
        st.session_state.page = "catalogo"

    c_add, _ = st.columns([2, 3])
    with c_add:
        if st.button("➕ Adicionar linha de serviço", key=f"{fk}_add_svc"):
            st.session_state.col_row_ids.append(uuid.uuid4().hex[:12])

    repasse: list[tuple[int, float, str]] = []
    row_ids = list(st.session_state.col_row_ids)
    for pos, row_id in enumerate(row_ids):
        st.markdown(f"**Serviço {pos + 1}**")
        sc1, sc2, sc3 = st.columns([2, 1, 1])
        with sc1:
            nome_svc = st.selectbox("Serviço *", nomes_servicos, key=f"{fk}_svc_{row_id}")
            sid = id_por_nome[nome_svc]
        with sc2:
            pct = float(
                st.number_input(
                    "Repasse % *",
                    min_value=0.01,
                    max_value=100.0,
                    value=50.0,
                    step=0.01,
                    key=f"{fk}_pct_{row_id}",
                )
            )
        with sc3:
            dlin = st.date_input(
                "Inserção da linha *",
                key=f"{fk}_dlin_{row_id}",
            )
        rb1, rb2 = st.columns([1, 4])
        with rb1:
            if len(row_ids) > 1 and st.button("Remover linha", key=f"{fk}_rm_{row_id}"):
                st.session_state.col_row_ids = [r for r in row_ids if r != row_id]
                st.rerun()
        repasse.append((sid, pct, dlin.isoformat() if dlin else ""))

    st.subheader("Observações")
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
        )
        if editing:
            ok, msg = atualizar_colaborador(int(st.session_state.col_edit_id), **common)
        else:
            ok, msg = cadastrar_colaborador(**common)
        if ok:
            st.session_state.col_form_v += 1
            st.session_state.col_edit_id = None
            st.session_state.col_row_ids = [uuid.uuid4().hex[:12]]
            st.success(msg)
        else:
            st.error(msg)


def _page_catalogo() -> None:
    _render_back_and_breadcrumb(["Home", "Catálogo"], back_key="bea_back_catalogo")
    st.markdown("### Catálogo de serviços")
    st.caption(
        "**E06:** Sessão, Produto, Coworking, **Pacote** e **Evento** — cadastro no catálogo; itens **Pacote** e **Evento** não aparecem nas habilitações de colaboradores."
    )

    fk = "cat_form"

    with st.expander("Cadastrar novo item", expanded=True):
        natureza = st.selectbox("Natureza *", NATUREZAS_CATALOGO_FASE3, key=f"{fk}_nat")
        nome = st.text_input("Nome *", key=f"{fk}_nome")
        descritivo = st.text_area(
            "Descritivo do serviço / produto *",
            key=f"{fk}_desc",
            height=88,
            placeholder="Texto para identificação e relatórios.",
        )
        ativo = st.checkbox("Item ativo (disponível para habilitações e vendas futuras)", value=True, key=f"{fk}_ativo")

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
            sessao_dh = float(
                st.number_input("Duração (horas) *", min_value=0.25, max_value=24.0, value=1.0, step=0.25, key=f"{fk}_sdh")
            )
            sessao_ve = float(st.number_input("Valor por sessão (€) *", min_value=0.01, value=45.0, step=0.5, key=f"{fk}_sve"))
        elif natureza == "Produto":
            ptipo = st.text_input("Tipo do produto *", key=f"{fk}_ptipo", placeholder="Ex.: cosmética, suplemento")
            pdesc = st.text_area("Descrição do produto", key=f"{fk}_pdesc", height=70)
            pve = float(st.number_input("Valor de venda (€) *", min_value=0.01, value=10.0, step=0.5, key=f"{fk}_pve"))
            porig_l = st.radio("Origem *", ["Estoque próprio", "Repasse / consignado"], horizontal=True, key=f"{fk}_porig")
            porig = "proprio" if porig_l == "Estoque próprio" else "repasse"
            if porig == "repasse":
                modo_rep = st.radio("Acordo com o proprietário *", ["Percentual", "Valor fixo"], horizontal=True, key=f"{fk}_pmod")
                if modo_rep == "Percentual":
                    pr_pct = float(
                        st.number_input("Percentual de repasse (%) *", min_value=0.01, max_value=100.0, value=30.0, step=0.01, key=f"{fk}_prpct")
                    )
                else:
                    pr_ve = float(st.number_input("Valor de repasse (€) *", min_value=0.01, value=5.0, step=0.5, key=f"{fk}_prve"))
        elif natureza == "Coworking":
            cws = st.text_input("Nome da sala *", key=f"{fk}_cws")
            cwc_l = st.radio("Cobrança *", ["Por hora", "Por dia"], horizontal=True, key=f"{fk}_cwc")
            cwc = "hora" if cwc_l == "Por hora" else "dia"
            cwv = float(st.number_input("Valor (€) *", min_value=0.01, value=8.0, step=0.5, key=f"{fk}_cwv"))
        elif natureza == "Pacote":
            opts_sess = listar_servicos_sessao_para_pacote()
            if not opts_sess:
                st.warning("Cadastre pelo menos uma **Sessão** completa no catálogo antes de montar um pacote.")
            else:
                nomes_sess = [x[1] for x in opts_sess]
                id_por_nome_sess = {x[1]: x[0] for x in opts_sess}
                if "cat_pac_row_ids" not in st.session_state:
                    st.session_state.cat_pac_row_ids = [uuid.uuid4().hex[:12]]

                st.subheader("Composição: tipos e quantidades de sessões")
                st.caption("Duração `0` = usar a duração definida no catálogo para essa sessão (deve estar preenchida).")
                p_row_ids = list(st.session_state.cat_pac_row_ids)
                for pos, prid in enumerate(p_row_ids):
                    st.markdown(f"**Linha {pos + 1}**")
                    pc1, pc2, pc3 = st.columns([2, 1, 1])
                    with pc1:
                        sn = st.selectbox("Tipo de sessão *", nomes_sess, key=f"{fk}_ps_{prid}")
                    with pc2:
                        pq = int(st.number_input("Quantidade *", min_value=1, max_value=999, value=1, step=1, key=f"{fk}_pq_{prid}"))
                    with pc3:
                        pdh = float(
                            st.number_input(
                                "Duração (h) 0=catálogo",
                                min_value=0.0,
                                max_value=24.0,
                                value=0.0,
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
                    st.number_input("Valor de venda do pacote (€) *", min_value=0.01, value=100.0, step=1.0, key=f"{fk}_pval")
                )

                st.subheader("Produto opcional no pacote")
                prod_opts = listar_servicos_produto_para_pacote()
                incluir_p = st.checkbox("Incluir produto do catálogo no pacote", key=f"{fk}_pinc_prod")
                if incluir_p and prod_opts:
                    nomes_p = [x[1] for x in prod_opts]
                    id_por_nome_p = {x[1]: x[0] for x in prod_opts}
                    pc4, pc5 = st.columns(2)
                    with pc4:
                        pn = st.selectbox("Produto *", nomes_p, key=f"{fk}_pnp")
                    with pc5:
                        pqn = int(st.number_input("Quantidade *", min_value=1, max_value=999, value=1, step=1, key=f"{fk}_pqn"))
                    prod_opt_ui = (id_por_nome_p[pn], pqn)
                elif incluir_p and not prod_opts:
                    st.info("Não há produtos ativos no catálogo. Crie um item **Produto** primeiro.")

        elif natureza == "Evento":
            st.subheader("Dados do evento")
            ed = st.date_input("Data do evento *", key=f"{fk}_edt")
            evt_data_iso = ed.isoformat() if ed else ""
            evt_local = st.text_input("Local de realização *", key=f"{fk}_eloc", placeholder="Morada ou espaço")
            evt_obs = st.text_area("Observações", key=f"{fk}_eobs", height=70, placeholder="Opcional.")
            esc_l = st.radio(
                "Âmbito *",
                ["Interno (membros e colaboradores BeaBa)", "Com convidado (parcerias)"],
                horizontal=True,
                key=f"{fk}_eesc",
            )
            evt_escopo = "interno" if esc_l.startswith("Interno") else "convidado"

            ec1, ec2, ec3 = st.columns(3)
            with ec1:
                evt_pc = float(st.number_input("Preço venda — criança (€) *", min_value=0.01, value=10.0, step=0.5, key=f"{fk}_epc"))
            with ec2:
                evt_pa = float(st.number_input("Preço venda — adulto (€) *", min_value=0.01, value=15.0, step=0.5, key=f"{fk}_epa"))
            with ec3:
                evt_pdf = float(
                    st.number_input(
                        "Desconto por filho adicional (€)",
                        min_value=0.0,
                        value=0.0,
                        step=0.5,
                        key=f"{fk}_epdf",
                    )
                )

            st.subheader("Participantes e repasse")
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
                st.markdown(f"**Participante {pos + 1}**")
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
                        lb = st.selectbox("Colaborador *", labels_c, key=f"{fk}_ecol_{erid}")
                        cid_e = id_por_label_c[lb]
                    else:
                        st.caption("— cadastre um colaborador para selecionar.")
                else:
                    pn_e = st.text_input("Nome do parceiro *", key=f"{fk}_epn_{erid}", placeholder="Entidade ou pessoa")

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
                    pct_e = float(
                        st.number_input(
                            "Repasse (%) *",
                            min_value=0.01,
                            max_value=100.0,
                            value=25.0,
                            step=0.01,
                            key=f"{fk}_epct_{erid}",
                        )
                    )
                else:
                    ve_e = float(st.number_input("Repasse (€) *", min_value=0.01, value=50.0, step=0.5, key=f"{fk}_eval_{erid}"))

                evt_el.append((tipo, cid_e, pn_e, modo, pct_e, ve_e))

                er1, _ = st.columns([1, 4])
                with er1:
                    if len(erow_ids) > 1 and st.button("Remover linha", key=f"{fk}_ermv_{erid}"):
                        st.session_state.cat_evt_row_ids = [x for x in erow_ids if x != erid]
                        st.rerun()

            if st.button("➕ Adicionar participante", key=f"{fk}_eadd"):
                st.session_state.cat_evt_row_ids.append(uuid.uuid4().hex[:12])
                st.rerun()

        if st.button("Registar no catálogo", type="primary", key=f"{fk}_submit"):
            if natureza == "Pacote":
                if not pac_el:
                    st.error("Defina a composição do pacote (sessões).")
                else:
                    linhas_db = [(sid, q, (dh if dh > 0 else None)) for sid, q, dh in pac_el]
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
                        st.success(msg)
                        st.session_state.cat_pac_row_ids = [uuid.uuid4().hex[:12]]
                        for k in list(st.session_state.keys()):
                            if k.startswith(f"{fk}_") and k not in (f"{fk}_nat", f"{fk}_ativo"):
                                try:
                                    del st.session_state[k]
                                except Exception:
                                    pass
                    else:
                        st.error(msg)
            elif natureza == "Evento":
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
                    st.success(msg)
                    st.session_state.cat_evt_row_ids = [uuid.uuid4().hex[:12]]
                    for k in list(st.session_state.keys()):
                        if k.startswith(f"{fk}_") and k not in (f"{fk}_nat", f"{fk}_ativo"):
                            try:
                                del st.session_state[k]
                            except Exception:
                                pass
                else:
                    st.error(msg)
            else:
                ok, msg = cadastrar_servico_fase1(
                    natureza,
                    nome,
                    descritivo,
                    ativo,
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
                if ok:
                    st.success(msg)
                    for k in list(st.session_state.keys()):
                        if k.startswith(f"{fk}_") and k not in (f"{fk}_nat", f"{fk}_ativo"):
                            try:
                                del st.session_state[k]
                            except Exception:
                                pass
                else:
                    st.error(msg)

    st.subheader("Itens registados")
    itens = listar_itens_catalogo()
    if not itens:
        st.info("Sem registos na tabela `servicos`.")
    else:
        st.table(
            {
                "ID": [r["id"] for r in itens],
                "Nome": [r["nome"] for r in itens],
                "Natureza": [r["natureza"] for r in itens],
                "Ativo": [r["ativo"] for r in itens],
                "Descritivo": [r["descritivo"] for r in itens],
                "Detalhes": [r["detalhes"] for r in itens],
            }
        )


def _page_placeholder(title: str, trail: list[str], blurb: str, *, back_key: str) -> None:
    _render_back_and_breadcrumb(trail, back_key=back_key)
    st.markdown(f"### {title}")
    st.info(blurb)


def main() -> None:
    page = st.session_state.page
    try:
        if page == "home":
            _page_home()
        elif page == "clientes":
            _page_clientes()
        elif page in ("colaboradores", "colaboradoras"):
            if page == "colaboradoras":
                st.session_state.page = "colaboradores"
            _page_colaboradores()
        elif page == "catalogo":
            _page_catalogo()
        elif page == "vendas":
            render_page_vendas(render_back_and_breadcrumb=_render_back_and_breadcrumb)
        elif page == "dashboards":
            render_page_dashboards(render_back_and_breadcrumb=_render_back_and_breadcrumb)
        elif page == "agendamentos":
            render_page_agendamentos(render_back_and_breadcrumb=_render_back_and_breadcrumb)
        elif page == "fluxo_gestao":
            render_page_fluxo_gestao(render_back_and_breadcrumb=_render_back_and_breadcrumb)
        else:
            st.session_state.page = "home"
            _page_home()
    except Exception as err:
        st.error("Ocorreu um erro ao renderizar esta página. Detalhes abaixo.")
        st.exception(err)


main()
