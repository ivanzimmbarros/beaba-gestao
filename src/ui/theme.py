"""Tokens visuais BeaBa V11.0 — alinhados a beabamaterno.com."""

from __future__ import annotations

import streamlit as st

COLORS = {
    "primary": "#97C9C5",
    "bg": "#FFFFFF",
    "card": "#F7F7F7",
    "text": "#545454",
    "highlight": "#E2F1F0",
}

FONTS = {
    "serif": '"Playfair Display", "Lora", Georgia, "Times New Roman", serif',
    "sans": '"Montserrat", "Open Sans", system-ui, -apple-system, sans-serif',
}

RADIUS = "20px"
SHADOW_CARD = "0 4px 24px rgba(0, 0, 0, 0.05)"

# Gráficos (E08) — tons suaves, boa distinção entre séries, sem cores agressivas
ANALYTICS_COLORS: list[str] = [
    "#97C9C5",
    "#7BA7A3",
    "#A8C4CE",
    "#C5B8A5",
    "#B5C99E",
    "#9EB8D9",
    "#B8A9C9",
    "#8BA892",
    "#D4C4B0",
    "#A3C4BC",
]

# Agenda (E09) — fundo + borda por estado; ícones por tipo de ocorrência
AGENDA_STATUS_STYLES: dict[str, dict[str, str]] = {
    "AGENDADO": {"bg": "#E8F4F3", "border": "#97C9C5", "label": "Agendado"},
    "CONFIRMADO": {"bg": "#D4EDDA", "border": "#5CB85C", "label": "Confirmado"},
    "CONCLUIDO": {"bg": "#E2E3E5", "border": "#6C757D", "label": "Concluído"},
    "CANCELADO": {"bg": "#FCE8E8", "border": "#DC3545", "label": "Cancelado"},
}

AGENDA_TIPO_ORIGEM_ICONS: dict[str, str] = {
    "sessao_avulsa": "◇",
    "pacote": "📦",
    "coworking": "⌂",
    "evento": "📅",
}


def agenda_status_style(status: str) -> dict[str, str]:
    return AGENDA_STATUS_STYLES.get(
        status,
        {"bg": "#F7F7F7", "border": "#CCCCCC", "label": status},
    )


def agenda_tipo_icon(tipo_origem: str) -> str:
    return AGENDA_TIPO_ORIGEM_ICONS.get(tipo_origem, "•")


def inject_bea_theme() -> None:
    """Injeta fontes (Google Fonts), variáveis CSS e overrides Streamlit."""
    primary = COLORS["primary"]
    bg = COLORS["bg"]
    card = COLORS["card"]
    text = COLORS["text"]
    highlight = COLORS["highlight"]
    serif = FONTS["serif"]
    sans = FONTS["sans"]

    st.markdown(
        f"""
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600&family=Playfair+Display:wght@500;600;700&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bea-primary: {primary};
                --bea-bg: {bg};
                --bea-card: {card};
                --bea-text: {text};
                --bea-highlight: {highlight};
                --bea-serif: {serif};
                --bea-sans: {sans};
                --bea-radius: {RADIUS};
                --bea-shadow: {SHADOW_CARD};
            }}
            /* Força modo claro no viewport (evita área principal preta com tema escuro OS/Streamlit) */
            html, html[data-theme="dark"], html[data-theme="light"] {{
                color-scheme: light !important;
            }}
            .stApp {{
                background-color: var(--bea-bg) !important;
                color: var(--bea-text) !important;
            }}
            [data-testid="stAppViewContainer"],
            [data-testid="stAppViewContainer"] > div,
            section[data-testid="stMain"],
            section[data-testid="stMain"] > div,
            .main .block-container {{
                background-color: var(--bea-bg) !important;
                color: var(--bea-text) !important;
            }}
            [data-testid="stHeader"] {{
                background-color: var(--bea-bg) !important;
            }}
            .stApp, .stApp [data-testid="stMarkdownContainer"], .stTextInput label, .stTextInput input {{
                font-family: var(--bea-sans) !important;
                color: var(--bea-text) !important;
            }}
            h1, h2, h3, h4, .bea-title {{
                font-family: var(--bea-serif) !important;
                color: var(--bea-text) !important;
                font-weight: 600 !important;
            }}
            div[data-testid="stButton"] > button[kind="primary"] {{
                background-color: var(--bea-primary) !important;
                color: var(--bea-text) !important;
                border: none !important;
                border-radius: var(--bea-radius) !important;
                box-shadow: var(--bea-shadow) !important;
                font-family: var(--bea-sans) !important;
                font-weight: 600 !important;
                min-height: 5.5rem;
                transition: background-color 0.2s ease, box-shadow 0.2s ease;
            }}
            div[data-testid="stButton"] > button[kind="primary"]:hover {{
                background-color: var(--bea-highlight) !important;
                box-shadow: 0 6px 28px rgba(0, 0, 0, 0.07) !important;
            }}
            div[data-testid="stButton"] > button[kind="secondary"] {{
                background-color: var(--bea-card) !important;
                color: var(--bea-text) !important;
                border: 1px solid rgba(84, 84, 84, 0.12) !important;
                border-radius: var(--bea-radius) !important;
                box-shadow: var(--bea-shadow) !important;
                font-family: var(--bea-sans) !important;
                font-weight: 600 !important;
                min-height: 5.5rem;
            }}
            div[data-testid="stButton"] > button[kind="secondary"]:hover {{
                background-color: var(--bea-highlight) !important;
            }}
            .bea-breadcrumb {{
                font-family: var(--bea-sans);
                font-size: 0.85rem;
                color: rgba(84, 84, 84, 0.75);
                margin-bottom: 0.75rem;
            }}
            .bea-back-note {{
                font-family: var(--bea-sans);
                font-size: 0.9rem;
            }}
            /* Inputs claros (#F7F7F7): contraste suave com fundo branco, sem “dark theme” */
            .stTextInput input,
            .stTextArea textarea,
            div[data-testid="stNumberInput"] input,
            div[data-baseweb="input"] input,
            div[data-baseweb="textarea"] textarea {{
                background-color: var(--bea-card) !important;
                color: var(--bea-text) !important;
                border: 1px solid rgba(84, 84, 84, 0.12) !important;
                border-radius: var(--bea-radius) !important;
                caret-color: var(--bea-text) !important;
            }}
            div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
            div[data-baseweb="select"] > div {{
                background-color: var(--bea-card) !important;
                border: 1px solid rgba(84, 84, 84, 0.12) !important;
                border-radius: var(--bea-radius) !important;
                color: var(--bea-text) !important;
            }}
            div[data-testid="stDateInput"] input {{
                background-color: var(--bea-card) !important;
                color: var(--bea-text) !important;
                border: 1px solid rgba(84, 84, 84, 0.12) !important;
                border-radius: var(--bea-radius) !important;
            }}
            .stRadio label, .stCheckbox label, .stMultiSelect label {{
                color: var(--bea-text) !important;
                font-family: var(--bea-sans) !important;
            }}
            [data-testid="stWidgetLabel"],
            label[data-testid="stWidgetLabel"] {{
                color: var(--bea-text) !important;
            }}
            [data-testid="stCaption"],
            .stCaption {{
                color: rgba(84, 84, 84, 0.85) !important;
            }}
            [data-testid="stMarkdownContainer"] p,
            [data-testid="stMarkdownContainer"] li,
            [data-testid="stMarkdownContainer"] span {{
                color: var(--bea-text) !important;
            }}
            div[data-testid="stAlert"] {{
                color: var(--bea-text) !important;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )
