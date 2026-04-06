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
            .stApp {{
                background-color: var(--bea-bg) !important;
                color: var(--bea-text) !important;
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
        </style>
        """,
        unsafe_allow_html=True,
    )
