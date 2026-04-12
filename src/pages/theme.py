"""
Tema global «BeaBa Sereno» — ponto de entrada em `src/pages/` (Épico redesign).

A injeção do CSS (`inject_beaba_verde_sereno`) deve ocorrer no arranque da app,
após `st.set_page_config`, tipicamente em `src.app.main`.
"""

from __future__ import annotations

from src.ui.styles_theme import get_beaba_css, inject_beaba_verde_sereno

__all__ = ["get_beaba_css", "inject_beaba_verde_sereno"]
