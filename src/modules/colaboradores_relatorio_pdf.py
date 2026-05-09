"""PDF landscape (fpdf2): relatório E24 repasse com texto íntegro (quebra linha sem truncar)."""

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


def _epw_safe(pdf: FPDF) -> float:
    return float(pdf.w - pdf.l_margin - pdf.r_margin)


def _bloco_esquerda(
    pdf: FPDF,
    *,
    epub: float,
    linhas_texto: list[str],
    tamanho: float,
    interline_mm: float,
) -> None:
    """Empilha parágrafos alinhados à esquerda, largura = área imprimível (sem texto cortado na margem)."""
    pdf.set_x(pdf.l_margin)
    pdf.set_font("bea_rep_pdf", size=tamanho)
    for par in linhas_texto:
        texto = str(par or "").replace("\r", "")
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(
            epub,
            interline_mm,
            texto if texto.strip() else " ",
            align="L",
            new_x="LMARGIN",
            new_y="NEXT",
        )


def _linhas_celulas_dry_run(
    pdf: FPDF, *, largura_interna_mm: float, altura_linha_mm: float, texto: object
) -> list[str]:
    """Quebra texto à largura da célula (sem desenhar)."""
    txt = str(texto if texto is not None else "").replace("\r", "").replace("\n", " ").strip()
    if not txt:
        return [""]
    if largura_interna_mm <= 3:
        largura_interna_mm = 3.0
    out = pdf.multi_cell(
        largura_interna_mm,
        altura_linha_mm,
        txt,
        align="L",
        dry_run=True,
        output="LINES",
    )
    lines = list(out) if out else []
    return lines if lines else [txt]


def _tabela_linhas_com_wrap(
    pdf: FPDF,
    grid: list[list[str]],
    *,
    width_template: tuple[float, ...],
) -> None:
    """Tabela cabeça + dados: todas as colunas podem ocupar várias linhas; nada cortado com reticências."""
    CELL_PAD_X = 0.9
    CELL_PAD_Y = 0.55
    LH_HEAD = 3.95
    LH_BODY = 3.72
    DISP = _epw_safe(pdf)
    soma = sum(width_template)
    fator = DISP / soma if soma > 0 else 1.0
    widths_mm: tuple[float, ...] = tuple(round(w * fator, 3) for w in width_template)

    for idx, row_raw in enumerate(grid):
        padded = list(row_raw) + [""] * max(0, len(widths_mm) - len(row_raw))
        cells = padded[: len(widths_mm)]

        eh_cabeca = idx == 0
        zebra_ok = idx > 0 and idx % 2 == 1

        lh = LH_HEAD if eh_cabeca else LH_BODY
        tam_fonte = 8.65 if eh_cabeca else 7.95
        pdf.set_font("bea_rep_pdf", size=tam_fonte)

        # número de linhas de texto por célula
        conta_linhas_por_col: list[int] = []
        linhas_explodidas: list[list[str]] = []
        inner_w_each: list[float] = []
        for col_i, dado in enumerate(cells):
            wcol = widths_mm[col_i]
            inner = max(4.5, float(wcol) - 2.0 * CELL_PAD_X)
            inner_w_each.append(inner)
            lis = _linhas_celulas_dry_run(pdf, largura_interna_mm=inner, altura_linha_mm=lh, texto=dado)
            lista_norm = lis if lis else [""]
            linhas_explodidas.append(lista_norm)
            conta_linhas_por_col.append(len(lista_norm))

        n_linhas_row = max(conta_linhas_por_col) if conta_linhas_por_col else 1
        row_h_mm = CELL_PAD_Y * 2 + n_linhas_row * lh

        y_page_bottom = pdf.h - pdf.b_margin
        pdf.set_x(pdf.l_margin)
        if pdf.get_y() + row_h_mm > y_page_bottom:
            pdf.add_page()
            pdf.set_font("bea_rep_pdf", size=tam_fonte)

        y0 = float(pdf.get_y())
        x_ini = float(pdf.l_margin)

        if eh_cabeca:
            pdf.set_fill_color(224, 234, 224)
            pdf.set_draw_color(118, 148, 125)
            pdf.set_text_color(32, 40, 35)
        else:
            pdf.set_draw_color(200, 200, 200)
            pdf.set_text_color(35, 40, 36)
            if zebra_ok:
                pdf.set_fill_color(248, 250, 248)
            else:
                pdf.set_fill_color(255, 255, 255)

        x_abs = x_ini
        for col_i in range(len(cells)):
            wcol = widths_mm[col_i]
            pdf.rect(x_abs, y0, wcol, row_h_mm, style="FD")
            inner = inner_w_each[col_i]
            conteudo = "\n".join(linhas_explodidas[col_i]) if linhas_explodidas[col_i] else ""
            pdf.set_xy(x_abs + CELL_PAD_X, y0 + CELL_PAD_Y)
            pdf.multi_cell(
                inner,
                lh,
                conteudo.strip() if conteudo.strip() else " ",
                align="L",
                border=0,
                fill=False,
            )
            x_abs += wcol

        pdf.set_y(y0 + row_h_mm)


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
    epub = _epw_safe(pdf)

    meta_doc: list[str] = ["Gerado em: " + datetime.now().strftime("%d/%m/%Y %H:%M")]

    pdf.set_xy(pdf.l_margin, pdf.get_y())
    _bloco_esquerda(
        pdf,
        epub=epub,
        linhas_texto=[str(titulo).strip()],
        tamanho=12,
        interline_mm=6.8,
    )
    _bloco_esquerda(pdf, epub=epub, linhas_texto=meta_doc, tamanho=8.5, interline_mm=5.2)
    pdf.ln(1.5)

    pdf.set_xy(pdf.l_margin, pdf.get_y())
    _bloco_esquerda(pdf, epub=epub, linhas_texto=["Filtros Aplicados"], tamanho=10.8, interline_mm=5.8)
    _bloco_esquerda(
        pdf,
        epub=epub,
        linhas_texto=[_str_nl(x) for x in meta_filtros_texto],
        tamanho=9,
        interline_mm=5.1,
    )
    pdf.ln(2)

    _bloco_esquerda(pdf, epub=epub, linhas_texto=["– Resumo executivo –"], tamanho=10.8, interline_mm=5.8)
    _bloco_esquerda(
        pdf,
        epub=epub,
        linhas_texto=[_str_nl(x) for x in resumo_texto],
        tamanho=9,
        interline_mm=5.1,
    )
    pdf.ln(3)

    _bloco_esquerda(
        pdf,
        epub=epub,
        linhas_texto=["– Detalhe linha-a-linha –"],
        tamanho=10.8,
        interline_mm=6.6,
    )
    pdf.ln(1)

    if not linhas_tabela:
        _bloco_esquerda(
            pdf,
            epub=epub,
            linhas_texto=["(Sem linhas para o período e filtros indicados.)"],
            tamanho=9,
            interline_mm=5.8,
        )
    else:
        width_template = (
            34.5,
            38.8,
            30.8,
            33.8,
            38.8,
            24.9,
            22.9,
            22.9,
            21.5,
        )
        _tabela_linhas_com_wrap(pdf, linhas_tabela, width_template=width_template)

    out = pdf.output()
    return bytes(out)


def _str_nl(x: object) -> str:
    return str(x or "").strip()
