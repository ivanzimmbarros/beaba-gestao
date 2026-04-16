"""
Tema visual «BeaBa Sereno» — engine central de CSS e tokens.

Paleta global: fundo menta pálido, sidebar sálvia suave, destaque floresta nos itens
activos, títulos bordeaux, acção primária cereja.
"""

from __future__ import annotations

import streamlit as st

# —— Paleta pública (Épico Redesign Sereno) ——
BEABA_BG_SOFT = "#F0FDF4"
BEABA_SIDEBAR_SOFT = "#D1FAE5"
BEABA_SIDEBAR_HIGHLIGHT = "#166534"
BEABA_TITLE = "#723E4B"
BEABA_PRIMARY = "#C43048"

# Tokens internos (compatível com código existente)
BEABA_VS = {
    "bg_soft": BEABA_BG_SOFT,
    "sidebar_soft": BEABA_SIDEBAR_SOFT,
    "sidebar_highlight": BEABA_SIDEBAR_HIGHLIGHT,
    "titulo_bordeaux": BEABA_TITLE,
    "botao_primario_cereja": BEABA_PRIMARY,
    "botao_secundario_salvia": "#A7F3D0",
    "sidebar_floresta": BEABA_SIDEBAR_HIGHLIGHT,
    "card_branco": "#FFFFFF",
    "texto_base": "#1F2937",
}


def get_beaba_css() -> str:
    """
    CSS global «BeaBa Sereno»: fundo menta, sidebar sálvia suave, cards/inputs 20px,
    sombra leve, Lora nos títulos, Inter/Roboto no corpo.
    """
    bg = BEABA_VS["bg_soft"]
    sidebar_soft = BEABA_VS["sidebar_soft"]
    highlight = BEABA_VS["sidebar_highlight"]
    bordeaux = BEABA_VS["titulo_bordeaux"]
    sage = BEABA_VS["botao_secundario_salvia"]
    cherry = BEABA_VS["botao_primario_cereja"]
    r = "20px"
    sh = "0 4px 6px rgba(0, 0, 0, 0.05)"
    sans = '"Inter", "Roboto", system-ui, -apple-system, sans-serif'
    serif_t = '"Lora", "Georgia", "Times New Roman", serif'

    return f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Roboto:wght@400;500;700&family=Lora:ital,wght@0,500;0,600;0,700;1,500&display=swap" rel="stylesheet">
<style>
    /* Barra superior alinhada à sidebar suave; seta em floresta */
    header[data-testid="stHeader"] {{
        visibility: visible !important;
        height: auto !important;
        min-height: 0 !important;
        max-height: none !important;
        overflow: visible !important;
        position: relative !important;
        pointer-events: auto !important;
        background: {sidebar_soft} !important;
        background-color: {sidebar_soft} !important;
        border: none !important;
        box-shadow: none !important;
    }}
    div[data-testid="stToolbar"] {{
        visibility: visible !important;
        height: auto !important;
        min-height: 0 !important;
        max-height: none !important;
        overflow: visible !important;
        position: relative !important;
        pointer-events: auto !important;
        background: transparent !important;
        border: none !important;
    }}
    /* Deploy, ⋮ definições Streamlit — mantém-se o stExpandSidebarButton à esquerda */
    div[data-testid="stToolbarActions"] {{
        display: none !important;
    }}
    /* Setas menu: floresta sobre fundo sálvia suave */
    [data-testid="stExpandSidebarButton"] button,
    [data-testid="stExpandSidebarButton"] svg,
    [data-testid="stExpandSidebarButton"] path {{
        color: {highlight} !important;
        fill: {highlight} !important;
    }}
    [data-testid="stSidebarCollapseButton"] button,
    [data-testid="stSidebarCollapseButton"] svg,
    [data-testid="stSidebarCollapseButton"] path {{
        color: {highlight} !important;
        fill: {highlight} !important;
    }}
    div[data-testid="stDecoration"],
    #MainMenu {{
        display: none !important;
    }}
    footer {{
        visibility: hidden !important;
        height: 0 !important;
        min-height: 0 !important;
        overflow: hidden !important;
    }}
    [data-testid="stAppViewContainer"] {{
        padding-top: 0 !important;
    }}
    section[data-testid="stMain"] > div {{
        padding-top: 0 !important;
    }}
    /* v3: anula regra legada do theme.py que força cinza em todo o Markdown (semáforo «invisível») */
    [data-testid="stMarkdownContainer"] .bea-proto-scope,
    [data-testid="stMarkdownContainer"] .bea-proto-scope * {{
        font-family: var(--bea-vs-sans) !important;
    }}
    [data-testid="stMarkdownContainer"] .bea-proto-scope p {{
        color: inherit !important;
    }}
    /* theme legado força span cinza — badges e rótulos do protótipo */
    [data-testid="stMarkdownContainer"] .bea-proto-scope span.bea-com-badge {{
        color: #064E3B !important;
    }}
    [data-testid="stMarkdownContainer"] .bea-proto-scope span.bea-vs-sem-lbl {{
        color: #374151 !important;
    }}
    :root {{
        --bea-vs-bg: {bg};
        --bea-vs-bordeaux: {bordeaux};
        --bea-vs-sidebar-soft: {sidebar_soft};
        --bea-vs-highlight: {highlight};
        --bea-vs-sage: {sage};
        --bea-vs-cherry: {cherry};
        --bea-vs-radius: {r};
        --bea-vs-shadow: {sh};
        --bea-vs-sans: {sans};
        --bea-vs-serif-t: {serif_t};
    }}
    html, html[data-theme="dark"], html[data-theme="light"] {{
        color-scheme: light !important;
    }}
    .stApp {{
        background-color: var(--bea-vs-bg) !important;
        font-family: var(--bea-vs-sans) !important;
        color: {BEABA_VS["texto_base"]} !important;
        margin-top: 0 !important;
        padding-top: 0 !important;
    }}
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] > div,
    section[data-testid="stMain"],
    section[data-testid="stMain"] > div,
    /* Área principal sem «moldura branca» gigante — só cards explícitos levam sombra */
    .main .block-container {{
        background-color: transparent !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        padding-top: 0rem !important;
        padding-bottom: 1.25rem !important;
        max-width: 100% !important;
    }}
    h1, h2, h3, h4, h5, h6 {{
        font-family: var(--bea-vs-serif-t) !important;
        color: var(--bea-vs-bordeaux) !important;
    }}
    .bea-title, .bea-breadcrumb {{
        font-family: var(--bea-vs-serif-t) !important;
        color: var(--bea-vs-bordeaux) !important;
    }}
    [data-testid="stSidebar"] {{
        background: {sidebar_soft} !important;
        top: 0 !important;
        min-height: 100vh !important;
        border-right: 1px solid rgba(22, 101, 52, 0.12) !important;
        box-shadow: none !important;
    }}
    [data-testid="stSidebar"] > div:first-child {{
        padding-top: 0.75rem !important;
    }}
    [data-testid="stSidebar"] hr {{
        border-color: rgba(22, 101, 52, 0.18) !important;
        margin: 0.85rem 0 !important;
    }}
    /* Texto corpo na sidebar: floresta suave (sem `*`: quebra controlos nativos app/theme). */
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] small {{
        color: {highlight} !important;
    }}
    [data-testid="stSidebar"] .bea-sidebar-app-title {{
        font-family: var(--bea-vs-sans) !important;
        font-size: 1.02rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.015em !important;
        color: #166534 !important;
        margin: 0 0 0.85rem 0 !important;
        line-height: 1.35 !important;
        max-width: 100% !important;
    }}
    [data-testid="stSidebar"] .bea-sidebar-sector-title {{
        font-family: var(--bea-vs-sans) !important;
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.02em !important;
        color: #166534 !important;
        margin: 0 0 0.5rem 0 !important;
        line-height: 1.35 !important;
    }}
    /* Itens em repouso: cartão branco suave (descendente: DOM do botão pode ter wrappers) */
    [data-testid="stSidebar"] [data-testid="stButton"] button {{
        background: rgba(255, 255, 255, 0.92) !important;
        color: {highlight} !important;
        border: 1px solid rgba(22, 101, 52, 0.14) !important;
        border-radius: 20px !important;
        min-height: 2.75rem !important;
        padding: 0.65rem 1.15rem !important;
        font-weight: 600 !important;
        font-family: var(--bea-vs-sans) !important;
        box-shadow: {sh} !important;
    }}
    [data-testid="stSidebar"] [data-testid="stButton"] button:hover {{
        background: #FFFFFF !important;
        border-color: rgba(22, 101, 52, 0.28) !important;
    }}
    /* Seleccionado: Sálvia Suave + texto/ícone Floresta Escuro (contraste legível) */
    [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] {{
        background: #A7F3D0 !important;
        color: #064E3B !important;
        border: 1px solid rgba(6, 78, 59, 0.35) !important;
        border-radius: 20px !important;
        padding: 0.7rem 1.25rem !important;
        font-weight: 700 !important;
        font-family: var(--bea-vs-sans) !important;
        box-shadow: {sh} !important;
    }}
    [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] *,
    [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] span,
    [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] svg,
    [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] path {{
        color: #064E3B !important;
        fill: #064E3B !important;
    }}
    [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"]:hover {{
        background: #6EE7B7 !important;
        color: #022C22 !important;
        border-color: rgba(6, 78, 59, 0.45) !important;
    }}
    [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"]:hover *,
    [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"]:hover svg,
    [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"]:hover path {{
        color: #022C22 !important;
        fill: #022C22 !important;
    }}
    [data-testid="stSidebar"] .stMarkdown a {{
        color: {highlight} !important;
    }}
    div[data-testid="stExpander"] {{
        border-radius: var(--bea-vs-radius) !important;
        box-shadow: var(--bea-vs-shadow) !important;
        background-color: {BEABA_VS["card_branco"]} !important;
        border: 1px solid rgba(22, 101, 52, 0.12) !important;
    }}
    div[data-testid="element-container"] > div[data-testid="stVerticalBlock"] > div {{
        border-radius: var(--bea-vs-radius);
    }}
    button[kind="primary"], .stButton > button[kind="primary"] {{
        background-color: var(--bea-vs-cherry) !important;
        border-color: var(--bea-vs-cherry) !important;
        color: #FFFFFF !important;
        border-radius: 20px !important;
        font-family: var(--bea-vs-sans) !important;
        box-shadow: var(--bea-vs-shadow) !important;
    }}
    button[kind="secondary"], .stButton > button[kind="secondary"] {{
        background-color: var(--bea-vs-sage) !important;
        border-color: rgba(22, 101, 52, 0.25) !important;
        color: #064E3B !important;
        border-radius: 20px !important;
        font-family: var(--bea-vs-sans) !important;
        box-shadow: var(--bea-vs-shadow) !important;
    }}
    [data-testid="stMetric"] {{
        background-color: {BEABA_VS["card_branco"]};
        border-radius: var(--bea-vs-radius);
        padding: 0.75rem 1rem;
        box-shadow: var(--bea-vs-shadow);
    }}
    /* v3 — «app», não planilha: blocos e widgets mais card-like */
    div[data-testid="stVerticalBlock"] > div[data-testid="element-container"] {{
        border-radius: var(--bea-vs-radius);
    }}
    .stTextInput input,
    .stTextArea textarea,
    div[data-testid="stNumberInput"] input,
    div[data-baseweb="input"] input,
    div[data-baseweb="textarea"] textarea {{
        background-color: #FFFFFF !important;
        border-radius: 20px !important;
        box-shadow: var(--bea-vs-shadow) !important;
        border: 1px solid rgba(22, 101, 52, 0.1) !important;
    }}
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {{
        background-color: #FFFFFF !important;
        border-radius: 20px !important;
        box-shadow: var(--bea-vs-shadow) !important;
        border: 1px solid rgba(22, 101, 52, 0.1) !important;
    }}
    div[data-testid="stDateInput"] input {{
        background-color: #FFFFFF !important;
        border-radius: 20px !important;
        box-shadow: var(--bea-vs-shadow) !important;
    }}
    div[data-testid="stMultiSelect"] div[data-baseweb="select"] > div {{
        background-color: #FFFFFF !important;
        border-radius: 20px !important;
    }}
    div[data-testid="stExpander"] {{
        border-radius: var(--bea-vs-radius) !important;
        box-shadow: var(--bea-vs-shadow) !important;
    }}
    /* PDV — Card único de estado (Total pedido + Total registado + A distribuir) */
    .bea-sem-float-wrap {{
        max-width: min(98vw, 960px) !important;
        width: 100% !important;
        margin-left: auto !important;
        margin-right: auto !important;
        margin-bottom: 1rem !important;
    }}
    .bea-venda-semaforo {{
        background: {BEABA_VS["card_branco"]} !important;
        border-radius: 20px !important;
        box-shadow: {sh} !important;
        padding: 1.25rem 1.5rem !important;
        margin-bottom: 0 !important;
        border: 1px solid rgba(114, 62, 75, 0.1) !important;
    }}
    .bea-venda-semaforo .bea-vs-sem-kicker {{
        margin: 0 0 0.85rem 0 !important;
        font-size: 0.75rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.09em !important;
        color: #64748B !important;
        font-weight: 700 !important;
    }}
    .bea-venda-semaforo .bea-vs-sem-unified-row {{
        display: flex !important;
        flex-wrap: wrap !important;
        align-items: flex-end !important;
        justify-content: space-between !important;
        gap: 1.25rem 2rem !important;
    }}
    .bea-venda-semaforo .bea-vs-sem-metrics-pair {{
        display: flex !important;
        flex-wrap: wrap !important;
        gap: 1.5rem 2.25rem !important;
        flex: 1 1 auto !important;
        min-width: min(100%, 280px) !important;
    }}
    .bea-venda-semaforo .bea-vs-sem-lbl {{
        display: block !important;
        font-size: 0.78rem !important;
        color: #64748B !important;
        font-weight: 600 !important;
        margin-bottom: 0.25rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
    }}
    .bea-venda-semaforo .bea-vs-sem-val-bdx {{
        font-size: 1.35rem !important;
        font-weight: 800 !important;
        line-height: 1.15 !important;
        color: {bordeaux} !important;
        font-family: var(--bea-vs-sans) !important;
    }}
    .bea-venda-semaforo .bea-vs-sem-ad-wrap {{
        flex: 0 1 auto !important;
        min-width: 180px !important;
        text-align: right !important;
    }}
    .bea-venda-semaforo .bea-vs-sem-ad-lbl {{
        font-size: 0.8rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.05em !important;
        margin-bottom: 0.2rem !important;
        color: #64748B !important;
        text-transform: uppercase !important;
    }}
    .bea-venda-semaforo .bea-vs-sem-ad-lbl.bea-ad-lbl-warn {{
        color: #C2410C !important;
    }}
    .bea-venda-semaforo .bea-vs-sem-ad-val {{
        font-size: 2.85rem !important;
        font-weight: 800 !important;
        line-height: 1 !important;
        font-family: var(--bea-vs-sans) !important;
        color: {bordeaux} !important;
    }}
    .bea-venda-semaforo .bea-vs-sem-ad-val.bea-ad-zero {{
        color: {highlight} !important;
    }}
    .bea-venda-semaforo .bea-vs-sem-ad-val.bea-ad-excesso {{
        color: #C2410C !important;
    }}
    .bea-venda-semaforo .bea-vs-sem-foot {{
        margin: 0.5rem 0 0 0 !important;
        font-size: 0.82rem !important;
        color: #64748B !important;
    }}
    /* Comanda — card item (spa) */
    .bea-venda-comanda-item {{
        background: transparent !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin-bottom: 0 !important;
        border: none !important;
    }}
    .bea-venda-comanda-item .bea-com-item-k {{
        font-family: var(--bea-vs-serif-t) !important;
        font-size: 1.05rem !important;
        font-weight: 700 !important;
        color: {bordeaux} !important;
        margin: 0 0 0.35rem 0 !important;
    }}
    .bea-venda-comanda-item .bea-com-nome {{
        font-size: 1.08rem !important;
        font-weight: 600 !important;
        color: {BEABA_VS["texto_base"]} !important;
        margin: 0 0 0.4rem 0 !important;
    }}
    .bea-venda-comanda-item .bea-com-desc {{
        font-size: 0.88rem !important;
        color: #64748B !important;
        margin: 0 0 0.5rem 0 !important;
        line-height: 1.35 !important;
    }}
    .bea-venda-comanda-item .bea-com-badge {{
        display: inline-block !important;
        background: {sage} !important;
        color: #064E3B !important;
        padding: 0.22rem 0.65rem !important;
        border-radius: 999px !important;
        font-size: 0.74rem !important;
        font-weight: 700 !important;
        margin-right: 0.35rem !important;
        margin-bottom: 0.25rem !important;
    }}
    .bea-venda-comanda-item .bea-com-meta {{
        font-size: 0.8rem !important;
        color: #475569 !important;
        margin: 0.15rem 0 !important;
    }}
    .bea-venda-comanda-item .bea-com-val-lbl {{
        font-size: 0.72rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        color: #64748B !important;
        font-weight: 600 !important;
    }}
    .bea-venda-comanda-item .bea-com-val {{
        font-size: 1.5rem !important;
        font-weight: 800 !important;
        color: {bordeaux} !important;
        line-height: 1.15 !important;
        font-family: var(--bea-vs-sans) !important;
    }}
    /* Título PDV (sem st.title) */
    .bea-pdv-titulo-wrap {{
        margin: 0 0 0.35rem 0 !important;
        padding: 0 !important;
    }}
    .bea-pdv-titulo {{
        margin: 0 !important;
        font-family: var(--bea-vs-serif-t) !important;
        font-size: 1.65rem !important;
        font-weight: 700 !important;
        color: {bordeaux} !important;
        letter-spacing: 0.02em !important;
    }}
    .bea-pdv-sub {{
        margin: 0.15rem 0 0 0 !important;
        font-size: 0.88rem !important;
        color: #64748B !important;
        font-weight: 500 !important;
    }}
    /* Comanda mínima (sem lixo HTML): uma linha nome + badge | valor */
    .bea-comanda-min .bea-comanda-min-row {{
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        gap: 1rem !important;
        flex-wrap: wrap !important;
    }}
    .bea-comanda-min .bea-com-nome {{
        display: block !important;
        font-size: 1.08rem !important;
        font-weight: 700 !important;
        color: {bordeaux} !important;
        font-family: var(--bea-vs-serif-t) !important;
        margin: 0 0 0.35rem 0 !important;
    }}
    .bea-comanda-min .bea-com-val-col {{
        text-align: right !important;
        min-width: 100px !important;
    }}
    /* Cartão secção (Streamlit container com borda) — cantos alinhados ao protótipo */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        border-radius: 20px !important;
        box-shadow: {sh} !important;
        background: {BEABA_VS["card_branco"]} !important;
        border: 1px solid rgba(22, 101, 52, 0.08) !important;
        padding: 0.5rem 0.85rem 0.85rem 0.85rem !important;
    }}
</style>
"""


def inject_beaba_verde_sereno() -> None:
    """Injeta o tema «BeaBa Sereno» (chamar uma vez por rerun, após set_page_config)."""
    st.markdown(get_beaba_css(), unsafe_allow_html=True)
