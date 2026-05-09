"""
Constituição Visual BeaBá Sereno — camada de shell (Horizonte + Sidebar Sálvia).

Documentação normativa: Template Master + `.cursorrules`. Injectar após
`inject_beaba_verde_sereno()` para predominar sobre tokens legados do mesmo rerun.
"""

from __future__ import annotations

import streamlit as st

# —— Template Master (valores literais canónicos) ——
CV_SALVIA = "#76947D"
CV_SALVIA_10 = "rgba(118, 148, 125, 0.1)"
CV_CREME = "#FAF8F5"
CV_BRANCO = "#FFFFFF"
CV_TITULO = "#2D332F"
CV_SOMBRA_1 = "0 12px 40px rgba(118, 148, 125, 0.12)"
CV_SOMBRA_2 = "0 2px 10px rgba(0, 0, 0, 0.05)"
CV_SOMBRA_COMPOSTA = f"{CV_SOMBRA_1}, {CV_SOMBRA_2}"

CV_SERIF = '"Lora", "Playfair Display", Georgia, "Times New Roman", serif'
CV_SANS = '"Montserrat", "Inter", system-ui, -apple-system, sans-serif'


def get_constituicao_shell_css() -> str:
    return f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,500;0,600;0,700;1,500&family=Montserrat:wght@400;500;600;700&family=Playfair+Display:wght@500;600&display=swap" rel="stylesheet">
<style>
    :root {{
        --cv-salvia: {CV_SALVIA};
        --cv-creme: {CV_CREME};
        --cv-branco: {CV_BRANCO};
        --cv-titulo: {CV_TITULO};
        --cv-sombra-composta: {CV_SOMBRA_COMPOSTA};
        --cv-serif: {CV_SERIF};
        --cv-sans: {CV_SANS};
        --cv-radius-isla: 20px;
        --cv-radius-sidebar-ativo: 12px;
    }}
    /* —— Horizonte: faixa 300px + creme (corte nítido); mobile 150px —— */
    html, html[data-theme="dark"], html[data-theme="light"] {{
        color-scheme: light !important;
    }}
    .stApp {{
        background-color: {CV_CREME} !important;
    }}
    section[data-testid="stMain"] > div {{
        background: linear-gradient(
            to bottom,
            {CV_SALVIA_10} 0,
            {CV_SALVIA_10} 300px,
            {CV_CREME} 300px,
            {CV_CREME} 100%
        ) !important;
    }}
    @media (max-width: 768px) {{
        section[data-testid="stMain"] > div {{
            background: linear-gradient(
                to bottom,
                {CV_SALVIA_10} 0,
                {CV_SALVIA_10} 150px,
                {CV_CREME} 150px,
                {CV_CREME} 100%
            ) !important;
        }}
    }}
    .main .block-container {{
        background: transparent !important;
        padding-top: 1rem !important;
        max-width: min(1120px, 100%) !important;
    }}
    /* —— Sidebar: Sálvia sólida, texto/ícones brancos, ativo 12px + 15% branco —— */
    header[data-testid="stHeader"] {{
        background-color: {CV_SALVIA} !important;
        background: {CV_SALVIA} !important;
        border: none !important;
        box-shadow: none !important;
    }}
    [data-testid="stExpandSidebarButton"] button,
    [data-testid="stExpandSidebarButton"] svg,
    [data-testid="stExpandSidebarButton"] path,
    [data-testid="stSidebarCollapseButton"] button,
    [data-testid="stSidebarCollapseButton"] svg,
    [data-testid="stSidebarCollapseButton"] path {{
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
    }}
    [data-testid="stSidebar"] {{
        background: {CV_SALVIA} !important;
        background-color: {CV_SALVIA} !important;
        border-right: none !important;
        box-shadow: none !important;
    }}
    /* Não usar `*` aqui: versões recentes do Streamlit envolvem botões/controlo em
       camadas extra; texto branco forçado + fundo branco do widget = navegação “vazia”. */
    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] small {{
        color: #FFFFFF !important;
    }}
    [data-testid="stSidebar"] .bea-sidebar-app-title,
    [data-testid="stSidebar"] .bea-sidebar-sector-title {{
        font-family: var(--cv-sans) !important;
        font-weight: 600 !important;
        color: #FFFFFF !important;
        opacity: 0.98 !important;
    }}
    [data-testid="stSidebar"] hr {{
        border-color: rgba(255, 255, 255, 0.22) !important;
    }}
    /* Itens não seleccionados: leve contraste sobre sálvia */
    [data-testid="stSidebar"] [data-testid="stButton"] button[kind="secondary"] {{
        background: rgba(255, 255, 255, 0.08) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255, 255, 255, 0.28) !important;
        border-radius: var(--cv-radius-sidebar-ativo) !important;
        min-height: 2.65rem !important;
        font-family: var(--cv-sans) !important;
        font-weight: 500 !important;
        box-shadow: none !important;
    }}
    [data-testid="stSidebar"] [data-testid="stButton"] button[kind="secondary"]:hover {{
        background: rgba(255, 255, 255, 0.18) !important;
        border-color: rgba(255, 255, 255, 0.45) !important;
    }}
    [data-testid="stSidebar"] [data-testid="stButton"] button[kind="secondary"] *,
    [data-testid="stSidebar"] [data-testid="stButton"] button[kind="secondary"] span {{
        color: #FFFFFF !important;
    }}
    /* Activo: só fundo branco ~15% + raio 12px — sem contorno nem barra lateral */
    [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] {{
        background: rgba(255, 255, 255, 0.15) !important;
        color: #FFFFFF !important;
        border: none !important;
        outline: none !important;
        border-radius: var(--cv-radius-sidebar-ativo) !important;
        min-height: 2.65rem !important;
        font-family: var(--cv-sans) !important;
        font-weight: 600 !important;
        box-shadow: none !important;
    }}
    [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"]:hover {{
        background: rgba(255, 255, 255, 0.24) !important;
    }}
    [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"]:focus {{
        outline: none !important;
        box-shadow: none !important;
    }}
    [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"]:focus-visible {{
        outline: 2px solid rgba(255, 255, 255, 0.45) !important;
        outline-offset: 2px !important;
    }}
    [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] *,
    [data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] span {{
        color: #FFFFFF !important;
    }}
</style>
"""


def get_constituicao_home_hub_css() -> str:
    """CSS só para o Hub (Início): ilhas em blocos horizontais de botões."""
    return f"""
<style>
    .bea-cv-hero {{
        min-height: 300px;
        box-sizing: border-box;
        padding: 2rem 1.5rem 1.5rem 1.5rem;
        margin: 0 0 1.25rem 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        background: transparent;
    }}
    @media (max-width: 768px) {{
        .bea-cv-hero {{ min-height: 150px; padding: 1.25rem 1rem; }}
    }}
    .bea-cv-hero h1 {{
        font-family: var(--cv-serif) !important;
        font-weight: 500 !important;
        color: {CV_TITULO} !important;
        font-size: clamp(1.75rem, 4vw, 2.35rem) !important;
        margin: 0 0 0.5rem 0 !important;
        letter-spacing: 0.02em !important;
    }}
    .bea-cv-hero .bea-cv-sub {{
        font-family: var(--cv-sans) !important;
        font-weight: 400 !important;
        color: {CV_TITULO} !important;
        opacity: 0.72 !important;
        font-size: 1rem !important;
        margin: 0 !important;
        max-width: 36rem;
    }}
    /* Ilha: métricas / resumo financeiro (padrão €) */
    .bea-cv-island-metricas {{
        background: {CV_BRANCO};
        border-radius: var(--cv-radius-isla);
        box-shadow: var(--cv-sombra-composta);
        padding: 28px 32px;
        margin: 0 0 20px 0;
        max-width: 920px;
        margin-left: auto;
        margin-right: auto;
    }}
    .bea-cv-island-metricas .bea-cv-island-titulo {{
        font-family: var(--cv-sans) !important;
        font-size: 0.72rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
        color: {CV_TITULO} !important;
        opacity: 0.55 !important;
        margin: 0 0 1rem 0 !important;
        font-weight: 600 !important;
    }}
    .bea-cv-metric-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 20px;
    }}
    .bea-cv-metric {{
        font-family: var(--cv-sans) !important;
    }}
    .bea-cv-metric .lbl {{
        display: block;
        font-size: 0.8rem;
        font-weight: 500;
        color: {CV_TITULO};
        opacity: 0.65;
        margin-bottom: 0.35rem;
    }}
    .bea-cv-metric .eur {{
        font-size: 1.35rem;
        font-weight: 600;
        color: {CV_TITULO};
        letter-spacing: 0.02em;
    }}
    /* Blocos horizontais do hub = ilhas */
    section[data-testid="stMain"] div[data-testid="stHorizontalBlock"] {{
        background: {CV_BRANCO} !important;
        border-radius: var(--cv-radius-isla) !important;
        box-shadow: var(--cv-sombra-composta) !important;
        padding: 24px 28px !important;
        margin-bottom: 20px !important;
        border: none !important;
        gap: 1rem !important;
    }}
    section[data-testid="stMain"] div[data-testid="stHorizontalBlock"] button {{
        border-radius: var(--cv-radius-isla) !important;
        min-height: 3.25rem !important;
        font-family: var(--cv-sans) !important;
        font-weight: 600 !important;
    }}
    section[data-testid="stMain"] div[data-testid="stHorizontalBlock"] button[kind="primary"] {{
        background-color: {CV_SALVIA} !important;
        border: 1px solid rgba(118, 148, 125, 0.45) !important;
        color: #FFFFFF !important;
        box-shadow: {CV_SOMBRA_2} !important;
    }}
    section[data-testid="stMain"] div[data-testid="stHorizontalBlock"] button[kind="primary"]:hover {{
        filter: brightness(1.06);
    }}
    section[data-testid="stMain"] div[data-testid="stHorizontalBlock"] button[kind="secondary"] {{
        background-color: {CV_CREME} !important;
        border: 1px solid rgba(118, 148, 125, 0.25) !important;
        color: {CV_TITULO} !important;
        box-shadow: none !important;
    }}
    section[data-testid="stMain"] div[data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {{
        background-color: #FFFFFF !important;
        border-color: {CV_SALVIA} !important;
    }}
    /* Ilha Mãe na Início: evitar segunda caixa branca nos blocos horizontais */
    section[data-testid="stMain"]:has(.bea-cv-home-slot) div[data-testid="stHorizontalBlock"] {{
        background: transparent !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin-bottom: 0.75rem !important;
    }}
</style>
"""


def inject_constituicao_shell() -> None:
    st.markdown(get_constituicao_shell_css(), unsafe_allow_html=True)


def inject_constituicao_home_hub() -> None:
    st.markdown(get_constituicao_home_hub_css(), unsafe_allow_html=True)


def get_constituicao_home_cockpit_extra_css() -> str:
    """Fase 3 — ilhas independentes (marcador .bea-cv-home-island-mark), Panorama, hero, agenda."""
    return f"""
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0" />
<style>
    .bea-cv-cockpit-active {{ display: none !important; }}
    /* Horizonte visível: não deixar bloqueios brancos sobre o gradiente da main */
    section[data-testid="stMain"]:has(.bea-cv-cockpit-active) [data-testid="stAppViewContainer"],
    section[data-testid="stMain"]:has(.bea-cv-cockpit-active) [data-testid="stAppViewContainer"] > .main,
    section[data-testid="stMain"]:has(.bea-cv-cockpit-active) .main .block-container {{
        background: transparent !important;
    }}
    /* Ilha Mãe única (.bea-cv-home-slot + mount): sem caixa branca/sombra nas colunas filhas do cockpit */
    section[data-testid="stMain"]:has(.bea-cv-home-slot):has(.bea-cv-cockpit-active)
        [data-testid="column"]:has(.bea-cv-home-island-mark) > div {{
        background-color: transparent !important;
        background: transparent !important;
        border-radius: 0 !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        margin-bottom: 0.85rem !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-home-slot):has(.bea-cv-cockpit-active)
        [data-testid="column"]:has(.bea-cv-home-island-mark)
        [data-testid="stVerticalBlockBorderWrapper"] {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }}
    .bea-cv-cockpit-hero {{
        position: relative;
        min-height: 300px;
        box-sizing: border-box;
        padding: 2rem 1.5rem 2.5rem 1.5rem;
        margin: 0 0 1.25rem 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        background: transparent;
    }}
    @media (max-width: 768px) {{
        .bea-cv-cockpit-hero {{ min-height: 150px; padding: 1.25rem 1rem 2rem 1rem; }}
    }}
    .bea-cv-cockpit-hero h1 {{
        font-family: var(--cv-serif) !important;
        font-weight: 500 !important;
        color: {CV_TITULO} !important;
        font-size: clamp(1.75rem, 4vw, 2.35rem) !important;
        margin: 0 0 0.35rem 0 !important;
        letter-spacing: 0.02em !important;
    }}
    .bea-cv-cockpit-hero .bea-cv-cockpit-greet-sub {{
        font-family: var(--cv-sans) !important;
        font-weight: 400 !important;
        color: {CV_TITULO} !important;
        opacity: 0.72 !important;
        font-size: 1rem !important;
        margin: 0 !important;
        max-width: 34rem;
    }}
    .bea-cv-cockpit-tier-title {{
        font-family: var(--cv-sans) !important;
        font-size: 0.72rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
        color: {CV_TITULO} !important;
        opacity: 0.55 !important;
        margin: 0 0 0.75rem 0 !important;
        font-weight: 600 !important;
    }}
    .bea-cv-donut-caption {{
        font-family: var(--cv-sans) !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        color: {CV_TITULO} !important;
        opacity: 0.78 !important;
        text-align: center !important;
        margin-top: 0.35rem !important;
    }}
    .bea-cv-pano-icon-wrap {{
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: rgba(118, 148, 125, 0.15);
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 14px;
    }}
    .bea-cv-pano-icon-wrap .material-symbols-outlined {{
        font-size: 26px;
        color: {CV_SALVIA};
        font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
    }}
    .bea-cv-pano-card-h {{
        font-family: var(--cv-serif) !important;
        font-weight: 500 !important;
        font-size: 0.95rem !important;
        line-height: 1.35 !important;
        color: {CV_TITULO} !important;
        margin: 0 0 10px 0 !important;
        letter-spacing: 0.01em !important;
    }}
    .bea-cv-home-block-h {{
        font-family: var(--cv-serif) !important;
        font-weight: 500 !important;
        font-size: 1.05rem !important;
        color: {CV_TITULO} !important;
        margin: 0 0 12px 0 !important;
    }}
    .bea-cv-panorama-card-val {{
        font-family: var(--cv-sans) !important;
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        color: {CV_TITULO} !important;
        letter-spacing: 0.02em !important;
    }}
    /* Panorama Global: mesma linha de base dos botões «Explorar» (títulos com alturas diferentes) */
    section[data-testid="stMain"]:has(.bea-cv-cockpit-active) div[data-testid="stHorizontalBlock"]:has(.bea-cv-pano-card) {{
        align-items: stretch !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-cockpit-active) div[data-testid="stHorizontalBlock"]:has(.bea-cv-pano-card) > div[data-testid="column"],
    section[data-testid="stMain"]:has(.bea-cv-cockpit-active) div[data-testid="stHorizontalBlock"]:has(.bea-cv-pano-card) > div[data-testid="stColumn"] {{
        display: flex !important;
        flex-direction: column !important;
        align-self: stretch !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-cockpit-active) div[data-testid="stHorizontalBlock"]:has(.bea-cv-pano-card) > div[data-testid="column"] > div,
    section[data-testid="stMain"]:has(.bea-cv-cockpit-active) div[data-testid="stHorizontalBlock"]:has(.bea-cv-pano-card) > div[data-testid="stColumn"] > div {{
        flex: 1 1 auto !important;
        display: flex !important;
        flex-direction: column !important;
        min-height: 0 !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-cockpit-active) div[data-testid="stHorizontalBlock"]:has(.bea-cv-pano-card) [data-testid="element-container"]:has([data-testid="stButton"]) {{
        margin-top: auto !important;
    }}
    /* Badges Master (mesmos tokens da CAG; Home não injecta CSS da Área Única) */
    .bea-cv-badge-verde {{
        display: inline-block;
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        font-family: var(--cv-sans);
        font-size: 0.78rem;
        font-weight: 600;
        background: #E8F0EA;
        color: #76947D;
        white-space: nowrap;
    }}
    .bea-cv-badge-terracota {{
        display: inline-block;
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        font-family: var(--cv-sans);
        font-size: 0.78rem;
        font-weight: 600;
        background: #FFF4E5;
        color: #D4A373;
        white-space: nowrap;
    }}
    .bea-cv-badge-neutro {{
        display: inline-block;
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        font-family: var(--cv-sans);
        font-size: 0.78rem;
        font-weight: 500;
        background: rgba(45, 51, 47, 0.06);
        color: {CV_TITULO};
        opacity: 0.85;
        white-space: nowrap;
    }}
    .bea-cv-agenda-table {{
        width: 100%;
        border-collapse: collapse;
        font-family: var(--cv-sans);
        font-size: 0.88rem;
    }}
    .bea-cv-agenda-table th {{
        text-align: left;
        padding: 0.5rem 0.4rem;
        border-bottom: 1px solid rgba(45, 51, 47, 0.12);
        color: {CV_TITULO};
        opacity: 0.65;
        font-weight: 600;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }}
    .bea-cv-agenda-table td {{
        padding: 0.55rem 0.4rem;
        border-bottom: 1px solid rgba(45, 51, 47, 0.06);
        color: {CV_TITULO};
        vertical-align: middle;
    }}
    .bea-cv-agenda-empty {{
        font-family: var(--cv-sans);
        font-size: 0.92rem;
        color: {CV_TITULO};
        opacity: 0.62;
        padding: 0.5rem 0;
    }}
    @keyframes bea-cv-pulse-sage {{
        0%, 100% {{ box-shadow: inset 0 0 0 0 rgba(118, 148, 125, 0.25); }}
        50% {{ box-shadow: inset 0 0 0 2px rgba(118, 148, 125, 0.35); }}
    }}
    .bea-cv-agenda-tr-proxima {{
        animation: bea-cv-pulse-sage 2.2s ease-in-out infinite;
        background: rgba(118, 148, 125, 0.09) !important;
    }}
    .bea-cv-evolucao {{
        font-family: var(--cv-sans);
        color: {CV_TITULO};
    }}
    .bea-cv-evolucao-linha {{
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: space-between;
        gap: 0.5rem;
        margin: 0 0 0.85rem 0;
        font-size: 0.9rem;
    }}
    .bea-cv-evolucao-k {{ opacity: 0.72; max-width: 62%; }}
    .bea-cv-evolucao-v {{
        font-weight: 700;
        font-size: 1.15rem;
    }}
    .bea-cv-evolucao-sage {{ color: {CV_SALVIA} !important; }}
    .bea-cv-evolucao-pill {{
        display: inline-block;
        padding: 0.2rem 0.65rem;
        border-radius: 999px;
        font-weight: 600;
        font-size: 0.88rem;
        background: #E8F0EA;
        color: #76947D;
    }}
    .bea-cv-evolucao-foot {{
        margin: 0.75rem 0 0 0;
        font-size: 0.78rem;
        opacity: 0.55;
    }}
    section[data-testid="stMain"]:has(.bea-cv-cockpit-active) .js-plotly-plot .plotly {{
        border-radius: 12px;
    }}
</style>
"""


def inject_constituicao_home_cockpit_extra() -> None:
    st.markdown(get_constituicao_home_cockpit_extra_css(), unsafe_allow_html=True)


# Badges Master §5 — Área Única (CAG)
CV_BADGE_TERRA_BG = "#FFF4E5"
CV_BADGE_TERRA_FG = "#D4A373"
CV_BADGE_VERDE_BG = "#E8F0EA"
CV_BADGE_VERDE_FG = "#76947D"


def cag_mother_mark_html() -> str:
    """Marcador DOM da Ilha Mãe CAG — um único cartão branco com todo o conteúdo operacional."""
    return '<p class="bea-cv-cag-mother-mark" aria-hidden="true"></p>'


def cag_island_mark_html() -> str:
    """Legado: redirecciona para a Ilha Mãe (evitar ilhas aninhadas tipo Panorama Home)."""
    return cag_mother_mark_html()


def get_constituicao_cag_page_css() -> str:
    """CAG: Horizonte 300px + creme, Ilha Mãe branca, cards métricas internos discretos, badges."""
    return f"""
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0" />
<style>
    /* Slot injectado em app.py (col_main) — class + data-testid preservam :has() fiável */
    .bea-cv-cag-slot {{
        display: none !important;
    }}
    .bea-cv-cag-gap {{
        min-height: 20px;
        height: 20px;
        margin: 0;
        padding: 0;
        pointer-events: none;
    }}
    /* Horizonte Sereno: sálvia 10% no topo + creme (stMain + filho directo — Streamlit 1.3x–1.6x) */
    section[data-testid="stMain"]:has(.bea-cv-cag-slot),
    section[data-testid="stMain"]:has(.bea-cv-cag-slot) > div,
    /* Fallback: :has() por vezes não bate com a árvore real; inject_area_unica_visual_mount() põe body.bea-cv-cag-page */
    body.bea-cv-cag-page .stApp,
    body.bea-cv-cag-page section[data-testid="stMain"],
    body.bea-cv-cag-page section[data-testid="stMain"] > div {{
        background: linear-gradient(
            to bottom,
            rgba(118, 148, 125, 0.1) 0,
            rgba(118, 148, 125, 0.1) 300px,
            {CV_CREME} 300px,
            {CV_CREME} 100%
        ) !important;
    }}
    @media (max-width: 768px) {{
        section[data-testid="stMain"]:has(.bea-cv-cag-slot),
        section[data-testid="stMain"]:has(.bea-cv-cag-slot) > div,
        body.bea-cv-cag-page .stApp,
        body.bea-cv-cag-page section[data-testid="stMain"],
        body.bea-cv-cag-page section[data-testid="stMain"] > div {{
            background: linear-gradient(
                to bottom,
                rgba(118, 148, 125, 0.1) 0,
                rgba(118, 148, 125, 0.1) 150px,
                {CV_CREME} 150px,
                {CV_CREME} 100%
            ) !important;
        }}
    }}
    section[data-testid="stMain"]:has(.bea-cv-cag-slot) [data-testid="stAppViewContainer"],
    section[data-testid="stMain"]:has(.bea-cv-cag-slot) [data-testid="stAppViewContainer"] > .main,
    section[data-testid="stMain"]:has(.bea-cv-cag-slot) .main .block-container,
    body.bea-cv-cag-page [data-testid="stAppViewContainer"],
    body.bea-cv-cag-page [data-testid="stAppViewContainer"] > .main,
    body.bea-cv-cag-page .main .block-container {{
        background: transparent !important;
    }}
    /*
     * Ilha Mãe: coluna central (0.88) que contém o slot injectado em app.py.
     * Estilo no próprio [data-testid="column"] — não depender do filho > div (varia por versão).
     * Inclui .bea-cv-cag-mother-island (classe aplicada por inject_cag_visual_mount).
     */
    section[data-testid="stMain"]:has(.bea-cv-cag-slot)
        [data-testid="column"]:has(.bea-cv-cag-slot),
    section[data-testid="stMain"]:has(.bea-cv-cag-slot)
        [data-testid="column"]:has([data-testid="bea-cag-slot"]),
    section[data-testid="stMain"]:has(.bea-cv-cag-slot) [data-testid="stColumn"]:has(.bea-cv-cag-slot),
    body.bea-cv-cag-page [data-testid="column"].bea-cv-cag-mother-island,
    body.bea-cv-cag-page [data-testid="stColumn"].bea-cv-cag-mother-island {{
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
        border-radius: 20px !important;
        border: none !important;
        box-shadow: {CV_SOMBRA_COMPOSTA} !important;
        padding: 32px !important;
        box-sizing: border-box !important;
        margin-top: 0.35rem !important;
        margin-bottom: 1.25rem !important;
    }}
    /* Facilitador de nome (pesquisa unificada): painel com sombra Master + borda #718355 suave */
    section[data-testid="stMain"]:has(.bea-cv-cag-slot)
        .main div[data-testid="stVerticalBlock"]:has(p[data-testid="bea-busca-nome-sug-panel"]),
    body.bea-cv-cag-page .main div[data-testid="stVerticalBlock"]:has(p[data-testid="bea-busca-nome-sug-panel"]) {{
        border-radius: 12px !important;
        background: {CV_BRANCO} !important;
        box-shadow: {CV_SOMBRA_COMPOSTA} !important;
        border: 1px solid rgba(113, 131, 85, 0.22) !important;
        padding: 8px 10px 10px 10px !important;
        margin: 4px 0 8px 0 !important;
    }}
    /* Cards métricas resumo (dentro da coluna CAG) */
    section[data-testid="stMain"]:has(.bea-cv-cag-slot)
        [data-testid="column"]:has(.bea-cv-cag-slot) .bea-cv-cag-metric-card,
    section[data-testid="stMain"]:has(.bea-cv-cag-slot)
        [data-testid="column"]:has([data-testid="bea-cag-slot"]) .bea-cv-cag-metric-card,
    section[data-testid="stMain"]:has(.bea-cv-cag-slot)
        [data-testid="stColumn"]:has(.bea-cv-cag-slot) .bea-cv-cag-metric-card,
    body.bea-cv-cag-page [data-testid="column"].bea-cv-cag-mother-island .bea-cv-cag-metric-card,
    body.bea-cv-cag-page [data-testid="stColumn"].bea-cv-cag-mother-island .bea-cv-cag-metric-card {{
        box-shadow: none !important;
        background: rgba(250, 248, 245, 0.72) !important;
        border: 1px solid rgba(118, 148, 125, 0.14) !important;
    }}
    .bea-cv-cag-h1 {{
        font-family: var(--cv-serif) !important;
        font-weight: 500 !important;
        color: {CV_TITULO} !important;
        font-size: clamp(1.45rem, 3.2vw, 1.85rem) !important;
        margin: 0 0 0.5rem 0 !important;
        letter-spacing: 0.02em !important;
        line-height: 1.25 !important;
    }}
    .bea-cv-cag-h2 {{
        font-family: var(--cv-serif) !important;
        font-weight: 500 !important;
        color: {CV_TITULO} !important;
        font-size: 1.2rem !important;
        margin: 0 0 0.5rem 0 !important;
        letter-spacing: 0.01em !important;
    }}
    .bea-cv-badge-terracota {{
        display: inline-block;
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        font-family: var(--cv-sans);
        font-size: 0.78rem;
        font-weight: 600;
        background: {CV_BADGE_TERRA_BG};
        color: {CV_BADGE_TERRA_FG};
        white-space: nowrap;
    }}
    .bea-cv-badge-verde {{
        display: inline-block;
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        font-family: var(--cv-sans);
        font-size: 0.78rem;
        font-weight: 600;
        background: {CV_BADGE_VERDE_BG};
        color: {CV_BADGE_VERDE_FG};
        white-space: nowrap;
    }}
    .bea-cv-badge-neutro {{
        display: inline-block;
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        font-family: var(--cv-sans);
        font-size: 0.78rem;
        font-weight: 500;
        background: rgba(45, 51, 47, 0.06);
        color: {CV_TITULO};
        opacity: 0.85;
        white-space: nowrap;
    }}
    /* Cards métricas (dentro da ilha Resumo) — Padrão BeaBá */
    .bea-cv-cag-metric-card {{
        background: {CV_BRANCO};
        border-radius: var(--cv-radius-isla);
        border: none;
        box-shadow: var(--cv-sombra-composta);
        padding: 16px 18px;
        min-height: 6.5rem;
        box-sizing: border-box;
    }}
    .bea-cv-cag-metric-icon {{
        width: 44px;
        height: 44px;
        border-radius: 50%;
        background: rgba(118, 148, 125, 0.15);
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 10px;
    }}
    .bea-cv-cag-metric-icon .material-symbols-outlined {{
        font-size: 24px;
        color: {CV_SALVIA};
        font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
    }}
    .bea-cv-cag-metric-title {{
        font-family: var(--cv-sans) !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
        line-height: 1.35 !important;
        color: {CV_TITULO} !important;
        margin: 0 0 8px 0 !important;
        opacity: 0.95;
    }}
    .bea-cv-cag-metric-body {{
        font-family: var(--cv-sans) !important;
        color: {CV_TITULO};
    }}
    .bea-cv-cag-metric-body .bea-cv-cag-metric-val {{
        margin: 0;
        font-size: 1.12rem;
        font-weight: 700;
        color: {CV_TITULO};
    }}
    /* Botões na área CAG (ilhas sem wrapper nativo) */
    section[data-testid="stMain"]:has(.bea-cv-cag-slot) .block-container [data-testid="stButton"] > button,
    body.bea-cv-cag-page section[data-testid="stMain"] .block-container [data-testid="stButton"] > button {{
        border-radius: 9999px !important;
        background: rgba(118, 148, 125, 0.15) !important;
        border: 1px solid rgba(118, 148, 125, 0.35) !important;
        color: {CV_TITULO} !important;
        font-family: var(--cv-sans) !important;
        font-weight: 500 !important;
        box-shadow: none !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-cag-slot) .block-container [data-testid="stButton"] > button:hover,
    body.bea-cv-cag-page section[data-testid="stMain"] .block-container [data-testid="stButton"] > button:hover {{
        background: rgba(118, 148, 125, 0.22) !important;
        border-color: rgba(118, 148, 125, 0.5) !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-cag-slot) .block-container [data-testid="stButton"] > button[kind="primary"],
    body.bea-cv-cag-page section[data-testid="stMain"] .block-container [data-testid="stButton"] > button[kind="primary"] {{
        background: rgba(118, 148, 125, 0.22) !important;
        border-color: {CV_SALVIA} !important;
        color: #FFFFFF !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-cag-slot) .block-container [data-testid="stButton"] > button[kind="primary"]:hover,
    body.bea-cv-cag-page section[data-testid="stMain"] .block-container [data-testid="stButton"] > button[kind="primary"]:hover {{
        filter: brightness(1.05);
    }}
</style>
"""


def inject_area_unica_visual_mount() -> None:
    """CAG, Vendas, Colaboradores, Catálogo ou Início: `body` + coluna Ilha Mãe conforme o slot no DOM."""
    st.iframe(
        """
<script>
(function () {
  function mount() {
    try {
      var doc = window.parent.document;
      doc.body.classList.remove("bea-cv-cag-page");
      doc.body.classList.remove("bea-cv-vnd-page");
      doc.body.classList.remove("bea-cv-col-page");
      doc.body.classList.remove("bea-cv-cat-page");
      doc.body.classList.remove("bea-cv-gov-page");
      doc.body.classList.remove("bea-cv-fin-page");
      doc.body.classList.remove("bea-cv-home-page");
      doc.querySelectorAll(".bea-cv-cag-mother-island").forEach(function (el) {
        el.classList.remove("bea-cv-cag-mother-island");
      });
      doc.querySelectorAll(".bea-cv-vnd-mother-island").forEach(function (el) {
        el.classList.remove("bea-cv-vnd-mother-island");
      });
      doc.querySelectorAll(".bea-cv-col-mother-island").forEach(function (el) {
        el.classList.remove("bea-cv-col-mother-island");
      });
      doc.querySelectorAll(".bea-cv-cat-mother-island").forEach(function (el) {
        el.classList.remove("bea-cv-cat-mother-island");
      });
      doc.querySelectorAll(".bea-cv-gov-mother-island").forEach(function (el) {
        el.classList.remove("bea-cv-gov-mother-island");
      });
      doc.querySelectorAll(".bea-cv-fin-mother-island").forEach(function (el) {
        el.classList.remove("bea-cv-fin-mother-island");
      });
      doc.querySelectorAll(".bea-cv-home-mother-island").forEach(function (el) {
        el.classList.remove("bea-cv-home-mother-island");
      });
      var slot = doc.querySelector(".bea-cv-cag-slot");
      var bodyCls = "bea-cv-cag-page";
      var colCls = "bea-cv-cag-mother-island";
      if (!slot) {
        slot = doc.querySelector(".bea-cv-vnd-slot");
        bodyCls = "bea-cv-vnd-page";
        colCls = "bea-cv-vnd-mother-island";
      }
      if (!slot) {
        slot = doc.querySelector(".bea-cv-col-slot");
        bodyCls = "bea-cv-col-page";
        colCls = "bea-cv-col-mother-island";
      }
      if (!slot) {
        slot = doc.querySelector(".bea-cv-cat-slot");
        bodyCls = "bea-cv-cat-page";
        colCls = "bea-cv-cat-mother-island";
      }
      if (!slot) {
        slot = doc.querySelector(".bea-cv-gov-slot");
        bodyCls = "bea-cv-gov-page";
        colCls = "bea-cv-gov-mother-island";
      }
      if (!slot) {
        slot = doc.querySelector(".bea-cv-fin-slot");
        bodyCls = "bea-cv-fin-page";
        colCls = "bea-cv-fin-mother-island";
      }
      if (!slot) {
        slot = doc.querySelector(".bea-cv-home-slot");
        bodyCls = "bea-cv-home-page";
        colCls = "bea-cv-home-mother-island";
      }
      if (!slot) return;
      doc.body.classList.add(bodyCls);
      var el = slot.parentElement;
      while (el && el !== doc.body) {
        var tid = el.getAttribute && el.getAttribute("data-testid");
        if (tid === "column" || tid === "stColumn") {
          el.classList.add(colCls);
          break;
        }
        el = el.parentElement;
      }
    } catch (e) {}
  }
  mount();
  setTimeout(mount, 30);
  setTimeout(mount, 120);
})();
</script>
        """,
        width=1,
        height=1,
    )


def inject_cag_visual_mount() -> None:
    """Compat: mesmo que `inject_area_unica_visual_mount()` (CAG/VND/COL/CAT/Governança/Financeiro/Início)."""
    inject_area_unica_visual_mount()


def inject_constituicao_cag_page() -> None:
    st.markdown(get_constituicao_cag_page_css(), unsafe_allow_html=True)


def get_constituicao_vnd_page_css() -> str:
    """Painel de Vendas: Horizonte + Ilha Mãe (paridade técnica com CAG, classes `vnd`)."""
    return f"""
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0" />
<style>
    .bea-cv-vnd-slot {{
        display: none !important;
    }}
    .bea-cv-cag-gap {{
        min-height: 20px;
        height: 20px;
        margin: 0;
        padding: 0;
        pointer-events: none;
    }}
    section[data-testid="stMain"]:has(.bea-cv-vnd-slot),
    section[data-testid="stMain"]:has(.bea-cv-vnd-slot) > div,
    body.bea-cv-vnd-page .stApp,
    body.bea-cv-vnd-page section[data-testid="stMain"],
    body.bea-cv-vnd-page section[data-testid="stMain"] > div {{
        background: linear-gradient(
            to bottom,
            rgba(118, 148, 125, 0.1) 0,
            rgba(118, 148, 125, 0.1) 300px,
            {CV_CREME} 300px,
            {CV_CREME} 100%
        ) !important;
    }}
    @media (max-width: 768px) {{
        section[data-testid="stMain"]:has(.bea-cv-vnd-slot),
        section[data-testid="stMain"]:has(.bea-cv-vnd-slot) > div,
        body.bea-cv-vnd-page .stApp,
        body.bea-cv-vnd-page section[data-testid="stMain"],
        body.bea-cv-vnd-page section[data-testid="stMain"] > div {{
            background: linear-gradient(
                to bottom,
                rgba(118, 148, 125, 0.1) 0,
                rgba(118, 148, 125, 0.1) 150px,
                {CV_CREME} 150px,
                {CV_CREME} 100%
            ) !important;
        }}
    }}
    section[data-testid="stMain"]:has(.bea-cv-vnd-slot) [data-testid="stAppViewContainer"],
    section[data-testid="stMain"]:has(.bea-cv-vnd-slot) [data-testid="stAppViewContainer"] > .main,
    section[data-testid="stMain"]:has(.bea-cv-vnd-slot) .main .block-container,
    body.bea-cv-vnd-page [data-testid="stAppViewContainer"],
    body.bea-cv-vnd-page [data-testid="stAppViewContainer"] > .main,
    body.bea-cv-vnd-page .main .block-container {{
        background: transparent !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-vnd-slot)
        [data-testid="column"]:has(.bea-cv-vnd-slot),
    section[data-testid="stMain"]:has(.bea-cv-vnd-slot)
        [data-testid="column"]:has([data-testid="bea-vnd-slot"]),
    section[data-testid="stMain"]:has(.bea-cv-vnd-slot) [data-testid="stColumn"]:has(.bea-cv-vnd-slot),
    body.bea-cv-vnd-page [data-testid="column"].bea-cv-vnd-mother-island,
    body.bea-cv-vnd-page [data-testid="stColumn"].bea-cv-vnd-mother-island {{
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
        border-radius: 20px !important;
        border: none !important;
        box-shadow: {CV_SOMBRA_COMPOSTA} !important;
        padding: 32px !important;
        box-sizing: border-box !important;
        margin-top: 0.35rem !important;
        margin-bottom: 1.25rem !important;
    }}
    /* Facilitador de nome (pesquisa unificada) — paridade Master com CAG */
    section[data-testid="stMain"]:has(.bea-cv-vnd-slot)
        .main div[data-testid="stVerticalBlock"]:has(p[data-testid="bea-busca-nome-sug-panel"]),
    body.bea-cv-vnd-page .main div[data-testid="stVerticalBlock"]:has(p[data-testid="bea-busca-nome-sug-panel"]) {{
        border-radius: 12px !important;
        background: {CV_BRANCO} !important;
        box-shadow: {CV_SOMBRA_COMPOSTA} !important;
        border: 1px solid rgba(113, 131, 85, 0.22) !important;
        padding: 8px 10px 10px 10px !important;
        margin: 4px 0 8px 0 !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-vnd-slot)
        [data-testid="column"]:has(.bea-cv-vnd-slot) .bea-cv-vnd-status-surface,
    section[data-testid="stMain"]:has(.bea-cv-vnd-slot)
        [data-testid="column"]:has([data-testid="bea-vnd-slot"]) .bea-cv-vnd-status-surface,
    body.bea-cv-vnd-page [data-testid="column"].bea-cv-vnd-mother-island .bea-cv-vnd-status-surface,
    body.bea-cv-vnd-page [data-testid="stColumn"].bea-cv-vnd-mother-island .bea-cv-vnd-status-surface {{
        box-shadow: none !important;
        background: rgba(250, 248, 245, 0.72) !important;
        border: 1px solid rgba(118, 148, 125, 0.14) !important;
        border-radius: var(--cv-radius-isla) !important;
        padding: 18px 20px !important;
        margin-bottom: 16px !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-vnd-slot)
        [data-testid="column"]:has(.bea-cv-vnd-slot) .bea-venda-comanda-item,
    body.bea-cv-vnd-page [data-testid="column"].bea-cv-vnd-mother-island .bea-venda-comanda-item {{
        box-shadow: none !important;
        background: rgba(250, 248, 245, 0.55) !important;
        border: 1px solid rgba(118, 148, 125, 0.12) !important;
        border-radius: 16px !important;
    }}
    /* Tag Natureza por tipo (linhas de serviço — PDV) */
    body.bea-cv-vnd-page .bea-venda-comanda-item .bea-com-badge.bea-com-badge--nature-sessao {{
        background: rgba(220, 38, 38, 0.22) !important;
        border: 1px solid rgba(185, 28, 28, 0.5) !important;
        color: #7f1d1d !important;
    }}
    body.bea-cv-vnd-page .bea-venda-comanda-item .bea-com-badge.bea-com-badge--nature-pacote {{
        background: rgba(22, 163, 74, 0.22) !important;
        border: 1px solid rgba(21, 128, 61, 0.45) !important;
        color: #14532d !important;
    }}
    body.bea-cv-vnd-page .bea-venda-comanda-item .bea-com-badge.bea-com-badge--nature-produto {{
        background: rgba(37, 99, 235, 0.2) !important;
        border: 1px solid rgba(29, 78, 216, 0.45) !important;
        color: #1e3a8a !important;
    }}
    body.bea-cv-vnd-page .bea-venda-comanda-item .bea-com-badge.bea-com-badge--nature-coworking {{
        background: rgba(124, 58, 237, 0.18) !important;
        border: 1px solid rgba(109, 40, 217, 0.4) !important;
        color: #5b21b6 !important;
    }}
    body.bea-cv-vnd-page .bea-venda-comanda-item .bea-com-badge.bea-com-badge--nature-evento {{
        background: rgba(234, 88, 12, 0.2) !important;
        border: 1px solid rgba(194, 65, 12, 0.45) !important;
        color: #9a3412 !important;
    }}
    body.bea-cv-vnd-page .bea-venda-comanda-item .bea-com-badge.bea-com-badge--nature-outros {{
        background: rgba(118, 148, 125, 0.22) !important;
        border: 1px solid rgba(118, 148, 125, 0.4) !important;
        color: #064e3b !important;
    }}
    .bea-cv-cag-h1 {{
        font-family: var(--cv-serif) !important;
        font-weight: 500 !important;
        color: {CV_TITULO} !important;
        font-size: clamp(1.45rem, 3.2vw, 1.85rem) !important;
        margin: 0 0 0.5rem 0 !important;
        letter-spacing: 0.02em !important;
        line-height: 1.25 !important;
    }}
    .bea-cv-cag-h2 {{
        font-family: var(--cv-serif) !important;
        font-weight: 500 !important;
        color: {CV_TITULO} !important;
        font-size: 1.2rem !important;
        margin: 0 0 0.5rem 0 !important;
        letter-spacing: 0.01em !important;
    }}
    .bea-cv-badge-terracota {{
        display: inline-block;
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        font-family: var(--cv-sans);
        font-size: 0.78rem;
        font-weight: 600;
        background: {CV_BADGE_TERRA_BG};
        color: {CV_BADGE_TERRA_FG};
        white-space: nowrap;
    }}
    .bea-cv-badge-verde {{
        display: inline-block;
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        font-family: var(--cv-sans);
        font-size: 0.78rem;
        font-weight: 600;
        background: {CV_BADGE_VERDE_BG};
        color: {CV_BADGE_VERDE_FG};
        white-space: nowrap;
    }}
    .bea-cv-badge-neutro {{
        display: inline-block;
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        font-family: var(--cv-sans);
        font-size: 0.78rem;
        font-weight: 500;
        background: rgba(45, 51, 47, 0.06);
        color: {CV_TITULO};
        opacity: 0.85;
        white-space: nowrap;
    }}
    section[data-testid="stMain"]:has(.bea-cv-vnd-slot) .block-container [data-testid="stButton"] > button,
    body.bea-cv-vnd-page section[data-testid="stMain"] .block-container [data-testid="stButton"] > button {{
        border-radius: 9999px !important;
        background: rgba(118, 148, 125, 0.15) !important;
        border: 1px solid rgba(118, 148, 125, 0.35) !important;
        color: {CV_TITULO} !important;
        font-family: var(--cv-sans) !important;
        font-weight: 500 !important;
        box-shadow: none !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-vnd-slot) .block-container [data-testid="stButton"] > button:hover,
    body.bea-cv-vnd-page section[data-testid="stMain"] .block-container [data-testid="stButton"] > button:hover {{
        background: rgba(118, 148, 125, 0.22) !important;
        border-color: rgba(118, 148, 125, 0.5) !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-vnd-slot) .block-container [data-testid="stButton"] > button[kind="primary"],
    body.bea-cv-vnd-page section[data-testid="stMain"] .block-container [data-testid="stButton"] > button[kind="primary"] {{
        background: rgba(118, 148, 125, 0.22) !important;
        border-color: {CV_SALVIA} !important;
        color: #FFFFFF !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-vnd-slot) .block-container [data-testid="stButton"] > button[kind="primary"]:hover,
    body.bea-cv-vnd-page section[data-testid="stMain"] .block-container [data-testid="stButton"] > button[kind="primary"]:hover {{
        filter: brightness(1.05);
    }}
    /* Item (expander): rótulo do bónus numa única linha, sem partir «gratuito)» */
    body.bea-cv-vnd-page div[class*="st-key-"][class*="_bon_"] [data-testid="stCheckbox"],
    section[data-testid="stMain"]:has(.bea-cv-vnd-slot) div[class*="st-key-"][class*="_bon_"] [data-testid="stCheckbox"] {{
        flex-wrap: nowrap !important;
    }}
    body.bea-cv-vnd-page div[class*="st-key-"][class*="_bon_"] [data-testid="stCheckbox"] label[data-testid="stWidgetLabel"],
    body.bea-cv-vnd-page div[class*="st-key-"][class*="_bon_"] [data-testid="stCheckbox"] label[data-testid="stWidgetLabel"] *,
    section[data-testid="stMain"]:has(.bea-cv-vnd-slot) div[class*="st-key-"][class*="_bon_"] [data-testid="stCheckbox"] label[data-testid="stWidgetLabel"],
    section[data-testid="stMain"]:has(.bea-cv-vnd-slot) div[class*="st-key-"][class*="_bon_"] [data-testid="stCheckbox"] label[data-testid="stWidgetLabel"] * {{
        white-space: nowrap !important;
        word-break: keep-all !important;
        overflow-wrap: normal !important;
        hyphens: manual !important;
        flex-shrink: 0 !important;
    }}
    /* Pagamento — Adicionar: largura ao conteúdo; «Remover» usa width em px no Python */
    body.bea-cv-vnd-page div[class*="st-key-"][class*="_pay_add"] [data-testid="stButton"] > button,
    section[data-testid="stMain"]:has(.bea-cv-vnd-slot) div[class*="st-key-"][class*="_pay_add"] [data-testid="stButton"] > button {{
        width: fit-content !important;
        max-width: 100% !important;
        min-width: unset !important;
        white-space: nowrap !important;
        box-sizing: border-box !important;
    }}
    body.bea-cv-vnd-page div[class*="st-key-"][class*="_pay_add"] [data-testid="stButton"],
    section[data-testid="stMain"]:has(.bea-cv-vnd-slot) div[class*="st-key-"][class*="_pay_add"] [data-testid="stButton"] {{
        width: fit-content !important;
        align-self: flex-start !important;
    }}
    body.bea-cv-vnd-page div[class*="st-key-"][class*="pay_remove_btn"] [data-testid="stButton"] > button,
    section[data-testid="stMain"]:has(.bea-cv-vnd-slot) div[class*="st-key-"][class*="pay_remove_btn"] [data-testid="stButton"] > button {{
        white-space: nowrap !important;
        box-sizing: border-box !important;
        justify-content: center !important;
    }}
    body.bea-cv-vnd-page div[class*="st-key-"][class*="pay_remove_btn"] [data-testid="stButton"],
    section[data-testid="stMain"]:has(.bea-cv-vnd-slot) div[class*="st-key-"][class*="pay_remove_btn"] [data-testid="stButton"] {{
        width: auto !important;
        max-width: none !important;
        align-self: flex-start !important;
    }}
    /* «−» vermelho antes de «Remover…» (paridade visual com o ➕ do Adicionar) */
    body.bea-cv-vnd-page div[class*="st-key-"][class*="pay_remove_btn"] [data-testid="stButton"] > button::before,
    section[data-testid="stMain"]:has(.bea-cv-vnd-slot) div[class*="st-key-"][class*="pay_remove_btn"] [data-testid="stButton"] > button::before {{
        content: "−";
        color: #b91c1c;
        font-weight: 700;
        font-size: 1.08em;
        line-height: 1;
        margin-right: 0.3em;
        display: inline-block;
        vertical-align: -0.06em;
    }}
</style>
"""


def inject_constituicao_vnd_page() -> None:
    st.markdown(get_constituicao_vnd_page_css(), unsafe_allow_html=True)


def get_constituicao_col_page_css() -> str:
    """Colaboradores: Horizonte + Ilha Mãe (paridade VND/CAG, classes `col`)."""
    return f"""
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0" />
<style>
    .bea-cv-col-slot {{
        display: none !important;
    }}
    .bea-cv-cag-gap {{
        min-height: 20px;
        height: 20px;
        margin: 0;
        padding: 0;
        pointer-events: none;
    }}
    section[data-testid="stMain"]:has(.bea-cv-col-slot),
    section[data-testid="stMain"]:has(.bea-cv-col-slot) > div,
    body.bea-cv-col-page .stApp,
    body.bea-cv-col-page section[data-testid="stMain"],
    body.bea-cv-col-page section[data-testid="stMain"] > div {{
        background: linear-gradient(
            to bottom,
            rgba(118, 148, 125, 0.1) 0,
            rgba(118, 148, 125, 0.1) 300px,
            {CV_CREME} 300px,
            {CV_CREME} 100%
        ) !important;
    }}
    @media (max-width: 768px) {{
        section[data-testid="stMain"]:has(.bea-cv-col-slot),
        section[data-testid="stMain"]:has(.bea-cv-col-slot) > div,
        body.bea-cv-col-page .stApp,
        body.bea-cv-col-page section[data-testid="stMain"],
        body.bea-cv-col-page section[data-testid="stMain"] > div {{
            background: linear-gradient(
                to bottom,
                rgba(118, 148, 125, 0.1) 0,
                rgba(118, 148, 125, 0.1) 150px,
                {CV_CREME} 150px,
                {CV_CREME} 100%
            ) !important;
        }}
    }}
    section[data-testid="stMain"]:has(.bea-cv-col-slot) [data-testid="stAppViewContainer"],
    section[data-testid="stMain"]:has(.bea-cv-col-slot) [data-testid="stAppViewContainer"] > .main,
    section[data-testid="stMain"]:has(.bea-cv-col-slot) .main .block-container,
    body.bea-cv-col-page [data-testid="stAppViewContainer"],
    body.bea-cv-col-page [data-testid="stAppViewContainer"] > .main,
    body.bea-cv-col-page .main .block-container {{
        background: transparent !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-col-slot)
        [data-testid="column"]:has(.bea-cv-col-slot),
    section[data-testid="stMain"]:has(.bea-cv-col-slot)
        [data-testid="column"]:has([data-testid="bea-col-slot"]),
    section[data-testid="stMain"]:has(.bea-cv-col-slot) [data-testid="stColumn"]:has(.bea-cv-col-slot),
    body.bea-cv-col-page [data-testid="column"].bea-cv-col-mother-island,
    body.bea-cv-col-page [data-testid="stColumn"].bea-cv-col-mother-island {{
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
        border-radius: 20px !important;
        border: none !important;
        box-shadow: {CV_SOMBRA_COMPOSTA} !important;
        padding: 32px !important;
        box-sizing: border-box !important;
        margin-top: 0.35rem !important;
        margin-bottom: 1.25rem !important;
    }}
    /* Facilitador pesquisa unificada (nome) — paridade CAG/VND */
    section[data-testid="stMain"]:has(.bea-cv-col-slot)
        .main div[data-testid="stVerticalBlock"]:has(p[data-testid="bea-busca-nome-sug-panel"]),
    body.bea-cv-col-page .main div[data-testid="stVerticalBlock"]:has(p[data-testid="bea-busca-nome-sug-panel"]) {{
        border-radius: 12px !important;
        background: {CV_BRANCO} !important;
        box-shadow: {CV_SOMBRA_COMPOSTA} !important;
        border: 1px solid rgba(113, 131, 85, 0.22) !important;
        padding: 8px 10px 10px 10px !important;
        margin: 4px 0 8px 0 !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-col-slot)
        [data-testid="column"]:has(.bea-cv-col-slot) .bea-venda-comanda-item,
    body.bea-cv-col-page [data-testid="column"].bea-cv-col-mother-island .bea-venda-comanda-item {{
        box-shadow: none !important;
        background: rgba(250, 248, 245, 0.55) !important;
        border: 1px solid rgba(118, 148, 125, 0.12) !important;
        border-radius: 16px !important;
    }}
    .bea-cv-cag-h1 {{
        font-family: var(--cv-serif) !important;
        font-weight: 500 !important;
        color: {CV_TITULO} !important;
        font-size: clamp(1.45rem, 3.2vw, 1.85rem) !important;
        margin: 0 0 0.5rem 0 !important;
        letter-spacing: 0.02em !important;
        line-height: 1.25 !important;
    }}
    .bea-cv-cag-h2 {{
        font-family: var(--cv-serif) !important;
        font-weight: 500 !important;
        color: {CV_TITULO} !important;
        font-size: 1.2rem !important;
        margin: 0 0 0.5rem 0 !important;
        letter-spacing: 0.01em !important;
    }}
    .bea-cv-badge-terracota {{
        display: inline-block;
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        font-family: var(--cv-sans);
        font-size: 0.78rem;
        font-weight: 600;
        background: {CV_BADGE_TERRA_BG};
        color: {CV_BADGE_TERRA_FG};
        white-space: nowrap;
    }}
    .bea-cv-badge-verde {{
        display: inline-block;
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        font-family: var(--cv-sans);
        font-size: 0.78rem;
        font-weight: 600;
        background: {CV_BADGE_VERDE_BG};
        color: {CV_BADGE_VERDE_FG};
        white-space: nowrap;
    }}
    .bea-cv-badge-neutro {{
        display: inline-block;
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        font-family: var(--cv-sans);
        font-size: 0.78rem;
        font-weight: 500;
        background: rgba(45, 51, 47, 0.06);
        color: {CV_TITULO};
        opacity: 0.85;
        white-space: nowrap;
    }}
    /* Mapa da Equipa — tabela + separador textual entre badges (Master Sereno) */
    .bea-col-mapa-sep {{
        color: rgba(45, 51, 47, 0.35);
        margin: 0 0.25rem;
        font-weight: 500;
    }}
    /* Ilha filha — Disponibilidade (coluna com marcador `bea-col-disp-flag`) */
    section[data-testid="stMain"]:has(.bea-cv-col-slot)
        [data-testid="column"]:has(p.bea-col-disp-flag),
    body.bea-cv-col-page [data-testid="column"]:has(p.bea-col-disp-flag),
    section[data-testid="stMain"]:has(.bea-cv-col-slot)
        [data-testid="stColumn"]:has(p.bea-col-disp-flag),
    body.bea-cv-col-page [data-testid="stColumn"]:has(p.bea-col-disp-flag) {{
        background-color: #FFFFFF !important;
        border-radius: 20px !important;
        box-shadow: {CV_SOMBRA_COMPOSTA} !important;
        padding: 24px 28px !important;
        margin: 20px 0 24px 0 !important;
        box-sizing: border-box !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-col-slot) .bea-col-mapa-wrap,
    body.bea-cv-col-page .bea-col-mapa-wrap {{
        width: 100%;
        margin: 10px 0 16px 0;
        padding: 0;
        border-top: 1px solid rgba(118, 148, 125, 0.15);
        padding-top: 8px;
    }}
    section[data-testid="stMain"]:has(.bea-cv-col-slot) .bea-col-mapa-wrap .bea-col-mapa-svc-cell,
    body.bea-cv-col-page .bea-col-mapa-wrap .bea-col-mapa-svc-cell {{
        flex: 1;
        min-width: 0;
        line-height: 1.5;
    }}
    section[data-testid="stMain"]:has(.bea-cv-col-slot) .bea-col-mapa-wrap .bea-col-mapa-th,
    body.bea-cv-col-page .bea-col-mapa-wrap .bea-col-mapa-th {{
        font-family: var(--cv-sans) !important;
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        color: #718355 !important;
        padding: 4px 2px 10px 2px !important;
        margin: 0 !important;
        border-bottom: 2px solid rgba(118, 148, 125, 0.28) !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-col-slot) .bea-col-mapa-wrap .bea-col-mapa-row-end,
    body.bea-cv-col-page .bea-col-mapa-wrap .bea-col-mapa-row-end {{
        height: 0;
        margin: 0;
        padding: 0;
        border: none;
        border-bottom: 1px solid rgba(118, 148, 125, 0.14);
        width: 100%;
    }}
    /* Nome na «tabela»: só existem botões de nome dentro do wrap — estilo célula (não pílula) */
    section[data-testid="stMain"]:has(.bea-cv-col-slot) .bea-col-mapa-wrap [data-testid="stButton"] > button,
    body.bea-cv-col-page .bea-col-mapa-wrap [data-testid="stButton"] > button {{
        border-radius: 6px !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: {CV_TITULO} !important;
        font-family: var(--cv-sans) !important;
        font-weight: 600 !important;
        justify-content: flex-start !important;
        text-align: left !important;
        padding: 6px 4px !important;
        width: auto !important;
        min-height: unset !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-col-slot) .bea-col-mapa-wrap [data-testid="stButton"] > button:hover,
    body.bea-cv-col-page .bea-col-mapa-wrap [data-testid="stButton"] > button:hover {{
        background: rgba(118, 148, 125, 0.08) !important;
        color: {CV_SALVIA} !important;
        border: none !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-col-slot) .block-container [data-testid="stButton"] > button,
    body.bea-cv-col-page section[data-testid="stMain"] .block-container [data-testid="stButton"] > button {{
        border-radius: 9999px !important;
        background: rgba(118, 148, 125, 0.15) !important;
        border: 1px solid rgba(118, 148, 125, 0.35) !important;
        color: {CV_TITULO} !important;
        font-family: var(--cv-sans) !important;
        font-weight: 500 !important;
        box-shadow: none !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-col-slot) .block-container [data-testid="stButton"] > button:hover,
    body.bea-cv-col-page section[data-testid="stMain"] .block-container [data-testid="stButton"] > button:hover {{
        background: rgba(118, 148, 125, 0.22) !important;
        border-color: rgba(118, 148, 125, 0.5) !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-col-slot) .block-container [data-testid="stButton"] > button[kind="primary"],
    body.bea-cv-col-page section[data-testid="stMain"] .block-container [data-testid="stButton"] > button[kind="primary"] {{
        background: rgba(118, 148, 125, 0.22) !important;
        border-color: {CV_SALVIA} !important;
        color: #FFFFFF !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-col-slot) .block-container [data-testid="stButton"] > button[kind="primary"]:hover,
    body.bea-cv-col-page section[data-testid="stMain"] .block-container [data-testid="stButton"] > button[kind="primary"]:hover {{
        filter: brightness(1.05);
    }}
</style>
"""


def inject_constituicao_col_page() -> None:
    st.markdown(get_constituicao_col_page_css(), unsafe_allow_html=True)


def get_constituicao_cat_page_css() -> str:
    """Catálogo de serviços: Horizonte + Ilha Mãe (paridade COL/VND, classes `cat`)."""
    return f"""
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0" />
<style>
    .bea-cv-cat-slot {{
        display: none !important;
    }}
    .bea-cv-cag-gap {{
        min-height: 20px;
        height: 20px;
        margin: 0;
        padding: 0;
        pointer-events: none;
    }}
    section[data-testid="stMain"]:has(.bea-cv-cat-slot),
    section[data-testid="stMain"]:has(.bea-cv-cat-slot) > div,
    body.bea-cv-cat-page .stApp,
    body.bea-cv-cat-page section[data-testid="stMain"],
    body.bea-cv-cat-page section[data-testid="stMain"] > div {{
        background: linear-gradient(
            to bottom,
            rgba(118, 148, 125, 0.1) 0,
            rgba(118, 148, 125, 0.1) 300px,
            {CV_CREME} 300px,
            {CV_CREME} 100%
        ) !important;
    }}
    @media (max-width: 768px) {{
        section[data-testid="stMain"]:has(.bea-cv-cat-slot),
        section[data-testid="stMain"]:has(.bea-cv-cat-slot) > div,
        body.bea-cv-cat-page .stApp,
        body.bea-cv-cat-page section[data-testid="stMain"],
        body.bea-cv-cat-page section[data-testid="stMain"] > div {{
            background: linear-gradient(
                to bottom,
                rgba(118, 148, 125, 0.1) 0,
                rgba(118, 148, 125, 0.1) 150px,
                {CV_CREME} 150px,
                {CV_CREME} 100%
            ) !important;
        }}
    }}
    section[data-testid="stMain"]:has(.bea-cv-cat-slot) [data-testid="stAppViewContainer"],
    section[data-testid="stMain"]:has(.bea-cv-cat-slot) [data-testid="stAppViewContainer"] > .main,
    section[data-testid="stMain"]:has(.bea-cv-cat-slot) .main .block-container,
    body.bea-cv-cat-page [data-testid="stAppViewContainer"],
    body.bea-cv-cat-page [data-testid="stAppViewContainer"] > .main,
    body.bea-cv-cat-page .main .block-container {{
        background: transparent !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-cat-slot)
        [data-testid="column"]:has(.bea-cv-cat-slot),
    section[data-testid="stMain"]:has(.bea-cv-cat-slot)
        [data-testid="column"]:has([data-testid="bea-cat-slot"]),
    section[data-testid="stMain"]:has(.bea-cv-cat-slot) [data-testid="stColumn"]:has(.bea-cv-cat-slot),
    body.bea-cv-cat-page [data-testid="column"].bea-cv-cat-mother-island,
    body.bea-cv-cat-page [data-testid="stColumn"].bea-cv-cat-mother-island {{
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
        border-radius: 20px !important;
        border: none !important;
        box-shadow: {CV_SOMBRA_COMPOSTA} !important;
        padding: 32px !important;
        box-sizing: border-box !important;
        margin-top: 0.35rem !important;
        margin-bottom: 1.25rem !important;
    }}
    .bea-cv-cag-h1 {{
        font-family: var(--cv-serif) !important;
        font-weight: 500 !important;
        color: {CV_TITULO} !important;
        font-size: clamp(1.45rem, 3.2vw, 1.85rem) !important;
        margin: 0 0 0.5rem 0 !important;
        letter-spacing: 0.02em !important;
        line-height: 1.25 !important;
    }}
    .bea-cv-cag-h2 {{
        font-family: var(--cv-serif) !important;
        font-weight: 500 !important;
        color: {CV_TITULO} !important;
        font-size: 1.2rem !important;
        margin: 0 0 0.5rem 0 !important;
        letter-spacing: 0.01em !important;
    }}
    .bea-cv-badge-terracota {{
        display: inline-block;
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        font-family: var(--cv-sans);
        font-size: 0.78rem;
        font-weight: 600;
        background: {CV_BADGE_TERRA_BG};
        color: {CV_BADGE_TERRA_FG};
        white-space: nowrap;
    }}
    .bea-cv-badge-verde {{
        display: inline-block;
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        font-family: var(--cv-sans);
        font-size: 0.78rem;
        font-weight: 600;
        background: {CV_BADGE_VERDE_BG};
        color: {CV_BADGE_VERDE_FG};
        white-space: nowrap;
    }}
    .bea-cv-badge-neutro {{
        display: inline-block;
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        font-family: var(--cv-sans);
        font-size: 0.78rem;
        font-weight: 500;
        background: rgba(45, 51, 47, 0.06);
        color: {CV_TITULO};
        opacity: 0.85;
        white-space: nowrap;
    }}
    section[data-testid="stMain"]:has(.bea-cv-cat-slot) .block-container [data-testid="stButton"] > button,
    body.bea-cv-cat-page section[data-testid="stMain"] .block-container [data-testid="stButton"] > button {{
        border-radius: 9999px !important;
        background: rgba(118, 148, 125, 0.15) !important;
        border: 1px solid rgba(118, 148, 125, 0.35) !important;
        color: {CV_TITULO} !important;
        font-family: var(--cv-sans) !important;
        font-weight: 500 !important;
        box-shadow: none !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-cat-slot) .block-container [data-testid="stButton"] > button:hover,
    body.bea-cv-cat-page section[data-testid="stMain"] .block-container [data-testid="stButton"] > button:hover {{
        background: rgba(118, 148, 125, 0.22) !important;
        border-color: rgba(118, 148, 125, 0.5) !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-cat-slot) .block-container [data-testid="stButton"] > button[kind="primary"],
    body.bea-cv-cat-page section[data-testid="stMain"] .block-container [data-testid="stButton"] > button[kind="primary"] {{
        background: rgba(118, 148, 125, 0.22) !important;
        border-color: {CV_SALVIA} !important;
        color: #FFFFFF !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-cat-slot) .block-container [data-testid="stButton"] > button[kind="primary"]:hover,
    body.bea-cv-cat-page section[data-testid="stMain"] .block-container [data-testid="stButton"] > button[kind="primary"]:hover {{
        filter: brightness(1.05);
    }}
</style>
"""


def inject_constituicao_cat_page() -> None:
    st.markdown(get_constituicao_cat_page_css(), unsafe_allow_html=True)


def get_constituicao_gov_page_css() -> str:
    """Governança prod (admin): Horizonte + Ilha Mãe Sereno — paridade técnica com Catálogo (classes ``gov``)."""
    css = get_constituicao_cat_page_css()
    return css.replace("bea-cv-cat-", "bea-cv-gov-").replace("bea-cat-slot", "bea-gov-slot")


def inject_constituicao_gov_page() -> None:
    st.markdown(get_constituicao_gov_page_css(), unsafe_allow_html=True)


def get_constituicao_usuarios_page_css() -> str:
    """Gestão de utilizadores (admin) — mesma geometria Horizonte + Ilha Mãe que Catálogo (classes ``usu``)."""
    css = get_constituicao_cat_page_css()
    return css.replace("bea-cv-cat-", "bea-cv-usu-").replace("bea-cat-slot", "bea-usu-slot")


def inject_constituicao_usuarios_page() -> None:
    st.markdown(get_constituicao_usuarios_page_css(), unsafe_allow_html=True)


def get_constituicao_fin_page_css() -> str:
    """Financeiro — Horizonte + Ilha Mãe (paridade CAT/COL/VND/CAG)."""
    return f"""
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0" />
<style>
    .bea-cv-fin-slot {{
        display: none !important;
    }}
    .bea-cv-cag-gap {{
        min-height: 20px;
        height: 20px;
        margin: 0;
        padding: 0;
        pointer-events: none;
    }}
    section[data-testid="stMain"]:has(.bea-cv-fin-slot),
    section[data-testid="stMain"]:has(.bea-cv-fin-slot) > div,
    body.bea-cv-fin-page .stApp,
    body.bea-cv-fin-page section[data-testid="stMain"],
    body.bea-cv-fin-page section[data-testid="stMain"] > div {{
        background: linear-gradient(
            to bottom,
            rgba(118, 148, 125, 0.1) 0,
            rgba(118, 148, 125, 0.1) 300px,
            {CV_CREME} 300px,
            {CV_CREME} 100%
        ) !important;
    }}
    @media (max-width: 768px) {{
        section[data-testid="stMain"]:has(.bea-cv-fin-slot),
        section[data-testid="stMain"]:has(.bea-cv-fin-slot) > div,
        body.bea-cv-fin-page .stApp,
        body.bea-cv-fin-page section[data-testid="stMain"],
        body.bea-cv-fin-page section[data-testid="stMain"] > div {{
            background: linear-gradient(
                to bottom,
                rgba(118, 148, 125, 0.1) 0,
                rgba(118, 148, 125, 0.1) 150px,
                {CV_CREME} 150px,
                {CV_CREME} 100%
            ) !important;
        }}
    }}
    section[data-testid="stMain"]:has(.bea-cv-fin-slot) [data-testid="stAppViewContainer"],
    section[data-testid="stMain"]:has(.bea-cv-fin-slot) [data-testid="stAppViewContainer"] > .main,
    section[data-testid="stMain"]:has(.bea-cv-fin-slot) .main .block-container,
    body.bea-cv-fin-page [data-testid="stAppViewContainer"],
    body.bea-cv-fin-page [data-testid="stAppViewContainer"] > .main,
    body.bea-cv-fin-page .main .block-container {{
        background: transparent !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-fin-slot)
        [data-testid="column"]:has(.bea-cv-fin-slot),
    section[data-testid="stMain"]:has(.bea-cv-fin-slot)
        [data-testid="column"]:has([data-testid="bea-fin-slot"]),
    section[data-testid="stMain"]:has(.bea-cv-fin-slot) [data-testid="stColumn"]:has(.bea-cv-fin-slot),
    body.bea-cv-fin-page [data-testid="column"].bea-cv-fin-mother-island,
    body.bea-cv-fin-page [data-testid="stColumn"].bea-cv-fin-mother-island {{
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
        border-radius: 20px !important;
        border: none !important;
        box-shadow: {CV_SOMBRA_COMPOSTA} !important;
        padding: 32px !important;
        box-sizing: border-box !important;
        margin-top: 0.35rem !important;
        margin-bottom: 1.25rem !important;
    }}
    .bea-cv-cag-h1 {{
        font-family: var(--cv-serif) !important;
        font-weight: 500 !important;
        color: {CV_TITULO} !important;
        font-size: clamp(1.45rem, 3.2vw, 1.85rem) !important;
        margin: 0 0 0.5rem 0 !important;
        letter-spacing: 0.02em !important;
        line-height: 1.25 !important;
    }}
    .bea-cv-cag-h2 {{
        font-family: var(--cv-serif) !important;
        font-weight: 500 !important;
        color: {CV_TITULO} !important;
        font-size: 1.2rem !important;
        margin: 0 0 0.5rem 0 !important;
        letter-spacing: 0.01em !important;
    }}
    .bea-cv-fin-gxc-banner {{
        font-family: var(--cv-sans) !important;
        margin: 0 0 0.75rem 0 !important;
    }}
    .bea-cv-fin-gxc-banner [data-testid="stAlert"] {{
        border-radius: 14px !important;
        box-shadow: {CV_SOMBRA_2} !important;
    }}
    .bea-cv-fin-gxc-banner-q {{
        font-family: var(--cv-sans) !important;
        font-weight: 600 !important;
        color: {CV_TITULO} !important;
        margin: 0 0 0.65rem 0 !important;
        font-size: 1rem !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-fin-slot) .block-container [data-testid="stButton"] > button,
    body.bea-cv-fin-page section[data-testid="stMain"] .block-container [data-testid="stButton"] > button {{
        border-radius: 9999px !important;
        background: rgba(118, 148, 125, 0.15) !important;
        border: 1px solid rgba(118, 148, 125, 0.35) !important;
        color: {CV_TITULO} !important;
        font-family: var(--cv-sans) !important;
        font-weight: 500 !important;
        box-shadow: none !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-fin-slot) .block-container [data-testid="stButton"] > button:hover,
    body.bea-cv-fin-page section[data-testid="stMain"] .block-container [data-testid="stButton"] > button:hover {{
        background: rgba(118, 148, 125, 0.22) !important;
        border-color: rgba(118, 148, 125, 0.5) !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-fin-slot) .block-container [data-testid="stButton"] > button[kind="primary"],
    body.bea-cv-fin-page section[data-testid="stMain"] .block-container [data-testid="stButton"] > button[kind="primary"] {{
        background: rgba(118, 148, 125, 0.22) !important;
        border-color: {CV_SALVIA} !important;
        color: #FFFFFF !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-fin-slot) .block-container [data-testid="stButton"] > button[kind="primary"]:hover,
    body.bea-cv-fin-page section[data-testid="stMain"] .block-container [data-testid="stButton"] > button[kind="primary"]:hover {{
        filter: brightness(1.05);
    }}
</style>
"""


def inject_constituicao_fin_page() -> None:
    st.markdown(get_constituicao_fin_page_css(), unsafe_allow_html=True)


def get_constituicao_home_page_css() -> str:
    """Início (cockpit): Horizonte + Ilha Mãe (paridade CAT/COL/VND/CAG, classes `home`)."""
    return f"""
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0" />
<style>
    .bea-cv-home-slot {{
        display: none !important;
    }}
    .bea-cv-cag-gap {{
        min-height: 20px;
        height: 20px;
        margin: 0;
        padding: 0;
        pointer-events: none;
    }}
    section[data-testid="stMain"]:has(.bea-cv-home-slot),
    section[data-testid="stMain"]:has(.bea-cv-home-slot) > div,
    body.bea-cv-home-page .stApp,
    body.bea-cv-home-page section[data-testid="stMain"],
    body.bea-cv-home-page section[data-testid="stMain"] > div {{
        background: linear-gradient(
            to bottom,
            rgba(118, 148, 125, 0.1) 0,
            rgba(118, 148, 125, 0.1) 300px,
            {CV_CREME} 300px,
            {CV_CREME} 100%
        ) !important;
    }}
    @media (max-width: 768px) {{
        section[data-testid="stMain"]:has(.bea-cv-home-slot),
        section[data-testid="stMain"]:has(.bea-cv-home-slot) > div,
        body.bea-cv-home-page .stApp,
        body.bea-cv-home-page section[data-testid="stMain"],
        body.bea-cv-home-page section[data-testid="stMain"] > div {{
            background: linear-gradient(
                to bottom,
                rgba(118, 148, 125, 0.1) 0,
                rgba(118, 148, 125, 0.1) 150px,
                {CV_CREME} 150px,
                {CV_CREME} 100%
            ) !important;
        }}
    }}
    section[data-testid="stMain"]:has(.bea-cv-home-slot) [data-testid="stAppViewContainer"],
    section[data-testid="stMain"]:has(.bea-cv-home-slot) [data-testid="stAppViewContainer"] > .main,
    section[data-testid="stMain"]:has(.bea-cv-home-slot) .main .block-container,
    body.bea-cv-home-page [data-testid="stAppViewContainer"],
    body.bea-cv-home-page [data-testid="stAppViewContainer"] > .main,
    body.bea-cv-home-page .main .block-container {{
        background: transparent !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-home-slot)
        [data-testid="column"]:has(.bea-cv-home-slot),
    section[data-testid="stMain"]:has(.bea-cv-home-slot)
        [data-testid="column"]:has([data-testid="bea-home-slot"]),
    section[data-testid="stMain"]:has(.bea-cv-home-slot) [data-testid="stColumn"]:has(.bea-cv-home-slot),
    body.bea-cv-home-page [data-testid="column"].bea-cv-home-mother-island,
    body.bea-cv-home-page [data-testid="stColumn"].bea-cv-home-mother-island {{
        background-color: #FFFFFF !important;
        background: #FFFFFF !important;
        border-radius: 20px !important;
        border: none !important;
        box-shadow: {CV_SOMBRA_COMPOSTA} !important;
        padding: 32px !important;
        box-sizing: border-box !important;
        margin-top: 0.35rem !important;
        margin-bottom: 1.25rem !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-home-slot) .block-container [data-testid="stButton"] > button,
    body.bea-cv-home-page section[data-testid="stMain"] .block-container [data-testid="stButton"] > button {{
        border-radius: 9999px !important;
        background: rgba(118, 148, 125, 0.15) !important;
        border: 1px solid rgba(118, 148, 125, 0.35) !important;
        color: {CV_TITULO} !important;
        font-family: var(--cv-sans) !important;
        font-weight: 500 !important;
        box-shadow: none !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-home-slot) .block-container [data-testid="stButton"] > button:hover,
    body.bea-cv-home-page section[data-testid="stMain"] .block-container [data-testid="stButton"] > button:hover {{
        background: rgba(118, 148, 125, 0.22) !important;
        border-color: rgba(118, 148, 125, 0.5) !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-home-slot) .block-container [data-testid="stButton"] > button[kind="primary"],
    body.bea-cv-home-page section[data-testid="stMain"] .block-container [data-testid="stButton"] > button[kind="primary"] {{
        background: rgba(118, 148, 125, 0.22) !important;
        border-color: {CV_SALVIA} !important;
        color: #FFFFFF !important;
    }}
    section[data-testid="stMain"]:has(.bea-cv-home-slot) .block-container [data-testid="stButton"] > button[kind="primary"]:hover,
    body.bea-cv-home-page section[data-testid="stMain"] .block-container [data-testid="stButton"] > button[kind="primary"]:hover {{
        filter: brightness(1.05);
    }}
</style>
"""


def inject_constituicao_home_page() -> None:
    st.markdown(get_constituicao_home_page_css(), unsafe_allow_html=True)
