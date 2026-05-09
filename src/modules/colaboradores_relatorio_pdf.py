"""PDF landscape (fpdf2): relatório E24 repasse, paridade com consulta SQLite."""

from __future__ import annotations

import os
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from fpdf import FPDF


@lru_cache(maxsize=1)
def _fonte_ttf_unicode() -> Path:
    cands: list[Path] = []
    if os.name == "nt":
        wd = Path(os.environ.get("WINDIR", r"C:\Windows"))
        cands.extend([wd / "Fonts" / "arial.ttf", wd / "Fonts" / "Arial.ttf"])
    cands.extend(
        [
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
            Path("/Library/Fonts/Arial.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        ]
    )
    for p in cands:
        if p.is_file():
            return p
    raise RuntimeError(
        "Fonte Unicode TTF não encontrada no SO (arial.ttf / DejaVuSans.ttf). "
        "Instale DejaVu ou confirme o directório de fontes Windows."
    )


def _encaixar(txt: object, n: int) -> str:
    s = str(txt or "").replace("\n", " ").replace("\r", "").strip()
    return s if len(s) <= n else s[: max(4, n - 1)] + "…"


def montar_pdf_relatorio_repasse_landscape(
    *,
    titulo: str,
    meta_filtros_texto: list[str],
    resumo_texto: list[str],
    linhas_tabela: list[list[str]],
) -> bytes:
    fname = _fonte_ttf_unicode()
    pdf = FPDF(orientation="LANDSCAPE", unit="mm", format="A4")
    pdf.set_author("BeaBa Gestao")
    pdf.set_title(str(titulo)[:118])
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.set_margins(14.0, 14.0, 14.0)
    pdf.add_font("bea_rep_pdf", fname=str(fname))

    pdf.add_page()
    epub = float(pdf.epw)
    pdf.set_font("bea_rep_pdf", size=12)
    pdf.multi_cell(epub, 6.5, str(titulo))
    pdf.set_font("bea_rep_pdf", size=8.5)
    pdf.ln(0.6)
    pdf.multi_cell(epub, 5, "Uso interno / tratamento RGPD-compatible (minimização de dados pessoais).")
    stamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    pdf.multi_cell(epub, 5, f"Gerado em: {stamp} (perspectiva calendário / horário: Europe/Lisbon)")
    pdf.ln(1.8)

    pdf.set_font("bea_rep_pdf", size=10.5)
    pdf.multi_cell(epub, 7, "- Resumo dos filtros -")
    pdf.set_font("bea_rep_pdf", size=9)
    for ln in meta_filtros_texto:
        pdf.multi_cell(epub, 5.2, str(ln))
    pdf.ln(1)

    pdf.set_font("bea_rep_pdf", size=10.5)
    pdf.multi_cell(epub, 7, "- Resumo executivo -")
    pdf.set_font("bea_rep_pdf", size=9)
    for ln in resumo_texto:
        pdf.multi_cell(epub, 5.2, str(ln))
    pdf.ln(3)

    pdf.set_font("bea_rep_pdf", size=10.5)
    pdf.multi_cell(epub, 7, "- Detalhe linha-a-linha -")
    pdf.ln(0.6)

    if not linhas_tabela:
        pdf.set_font("bea_rep_pdf", size=9)
        pdf.multi_cell(epub, 6, "(Sem linhas para o período e filtros indicados.)")
    else:
        _tabela_alveolar(pdf, linhas_tabela)

    out = pdf.output()
    return bytes(out)


_COL_MAX = (38, 40, 32, 36, 40, 26, 20, 20, 16)


def _tabela_alveolar(pdf: FPDF, grid: list[list[str]]) -> None:
    width_template = (
        33.5,
        40.0,
        31.8,
        34.8,
        38.9,
        25.9,
        22.9,
        22.9,
        21.9,
    )
    disponivel = pdf.w - pdf.l_margin - pdf.r_margin
    soma = sum(width_template)
    fator = disponivel / soma if soma > 0 else 1.0
    widths_mm = tuple(round(w * fator, 3) for w in width_template)

    row_h_base = 5.95
    for idx, row_raw in enumerate(grid):
        padded = list(row_raw) + [""] * max(0, len(widths_mm) - len(row_raw))
        cells = padded[: len(widths_mm)]
        header = idx == 0
        zebra = idx > 0 and idx % 2 == 1
        if pdf.get_y() + row_h_base > pdf.h - pdf.b_margin:
            pdf.add_page()
        # Fonte externa TTF: evitar `style="B"` sem ficheiro `-bold` registado.
        pdf.set_font("bea_rep_pdf", size=8.75 if header else 8.05)
        if header:
            pdf.set_fill_color(224, 234, 224)
            pdf.set_draw_color(118, 148, 125)
            pdf.set_text_color(32, 40, 35)
        else:
            pdf.set_draw_color(200, 200, 200)
            pdf.set_text_color(40, 40, 40)
            if zebra:
                pdf.set_fill_color(248, 250, 248)
            else:
                pdf.set_fill_color(255, 255, 255)

        pdf.set_x(pdf.l_margin)
        last_ix = len(cells) - 1
        for col_i, datum in enumerate(cells):
            w = widths_mm[col_i]
            cap = _COL_MAX[col_i] if col_i < len(_COL_MAX) else 28
            txt = _encaixar(datum, cap) if datum or header else ""
            ln = col_i == last_ix
            pdf.cell(
                w,
                row_h_base,
                text=(txt if txt else " "),
                border=1,
                fill=True,
                align="L",
                ln=int(ln),
            )
