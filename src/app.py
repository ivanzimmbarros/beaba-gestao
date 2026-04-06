"""
Aplicação Streamlit BeaBa Gestão — shell V11.0 (tema + dashboard de 4 blocos).
Referência: docs/CADERNO_MESTRE.md
"""

from __future__ import annotations

import streamlit as st

from src.database.connection import create_tables
from src.modules.cliente import SEXOS, cadastrar_cliente
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
        if st.button("Gestão de Colaboradoras", use_container_width=True, type="secondary"):
            st.session_state.page = "colaboradoras"

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    row2 = st.columns(2)
    with row2[0]:
        if st.button("Catálogo de Serviços", use_container_width=True, type="primary"):
            st.session_state.page = "catalogo"
    with row2[1]:
        if st.button("Painel de Vendas", use_container_width=True, type="secondary"):
            st.session_state.page = "vendas"

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
    morada = st.text_area("Morada *", key=f"{fk}_morada", height=88)
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

    st.subheader("Filhos")
    tem_filhos = st.radio("Possui filhos? *", ["Não", "Sim"], horizontal=True, key=f"{fk}_temf") == "Sim"
    filhos: list[tuple[int, str]] = []
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
            c1, c2 = st.columns(2)
            with c1:
                idade = int(
                    st.number_input(
                        f"Idade (anos completos) — filho {j + 1} *",
                        min_value=0,
                        max_value=120,
                        value=0,
                        key=f"{fk}_f_id_{j}",
                    )
                )
            with c2:
                sx = st.selectbox(f"Sexo — filho {j + 1} *", SEXOS, key=f"{fk}_f_sx_{j}")
            filhos.append((idade, sx))

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
            morada=morada,
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


def _page_placeholder(title: str, trail: list[str], blurb: str, *, back_key: str) -> None:
    _render_back_and_breadcrumb(trail, back_key=back_key)
    st.markdown(f"### {title}")
    st.info(blurb)


def main() -> None:
    page = st.session_state.page
    if page == "home":
        _page_home()
    elif page == "clientes":
        _page_clientes()
    elif page == "colaboradoras":
        _page_placeholder(
            "Colaboradoras",
            ["Home", "Colaboradoras"],
            "Módulo em construção: cadastro, percentual de repasse e vínculos.",
            back_key="bea_back_colaboradoras",
        )
    elif page == "catalogo":
        _page_placeholder(
            "Catálogo de serviços",
            ["Home", "Catálogo"],
            "Módulo em construção: Sessão, Tempo, Pacote e Produto (4 naturezas).",
            back_key="bea_back_catalogo",
        )
    elif page == "vendas":
        _page_placeholder(
            "Painel de vendas",
            ["Home", "Vendas"],
            "Módulo em construção: exceções financeiras e centavos.",
            back_key="bea_back_vendas",
        )
    else:
        st.session_state.page = "home"
        _page_home()


main()
