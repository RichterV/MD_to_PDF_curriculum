#!/usr/bin/env python3
"""
Gera PDFs de curriculo a partir de arquivos Markdown, otimizados para leitura
por ATS (Applicant Tracking System) e por triagem automatizada via IA.

Principios de ATS/IA aplicados:
  - Layout de coluna unica, sem tabelas, caixas de texto ou imagens.
  - Apenas fontes padrao do PDF (Helvetica), sempre com texto selecionavel
    (nunca convertido para curvas/imagem).
  - Titulos de secao em texto simples, ordem de leitura estritamente linear
    (topo -> base), igual a ordem do Markdown.
  - Metadados do PDF (titulo, autor, assunto, palavras-chave) preenchidos
    automaticamente a partir do conteudo, ajudando ferramentas de IA a
    identificar rapidamente do que se trata o documento.
  - Espacamento e tamanho de fonte se ajustam automaticamente (auto-shrink)
    para tentar manter o documento dentro do limite de paginas configurado
    conforme mais experiencias/habilidades sao adicionadas.

Estrutura esperada do Markdown (ver curriculo_base_PT.md / curriculo_base_EN.md):
  # Nome                              -> h1 (nome, obrigatorio, unico)
  Cargo/subtitulo                     -> texto solto logo apos o h1
  ## Contato                          -> PRIMEIRA secao "##" do arquivo:
    - Label: valor                       tratada como bloco de contato e
    - Label: valor                       renderizada em uma linha só, sem
                                          repetir o titulo da secao.
  ## Nome da secao                    -> demais secoes "##" (Experiencia,
                                          Formacao, Habilidades, Idiomas,
                                          Carta de Apresentacao, etc.)
  ### Cargo/Curso                     -> h3 dentro de uma secao (opcional)
  **Empresa** | Periodo               -> linha logo apos o h3 (empresa/datas)
  - bullet                            -> itens de lista
  Paragrafo solto                     -> paragrafo normal

Novas secoes "##", novos itens "###" e novos bullets sao suportados sem
qualquer alteracao no script: basta editar o Markdown.

Uso:
    python gerar_pdf.py
    python gerar_pdf.py curriculo_base_PT.md curriculo_base_EN.md
    python gerar_pdf.py meu_curriculo.md --out-dir dist --max-pages 1

Requisitos:
    pip install -r requirements.txt
"""

from __future__ import annotations

import argparse
import io
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
)

# --------------------------------------------------------------------------
# 1. Parsing do Markdown em blocos estruturados
# --------------------------------------------------------------------------

@dataclass
class Block:
    kind: str  # 'h1' | 'subtitle' | 'h2' | 'h3' | 'bullet' | 'paragraph'
    text: str


BULLET_RE = re.compile(r"^[-*]\s+(.*)$")


def parse_markdown(md_text: str) -> list[Block]:
    """Converte o texto Markdown em uma lista linear de blocos.

    O parser e propositalmente simples e posicional (nao usa uma lib de
    markdown generica) para que a estrutura do curriculo (h3 + linha de
    empresa/data + bullets) seja reconhecida de forma previsivel.
    """
    blocks: list[Block] = []
    seen_h1 = False
    before_first_h2 = True
    subtitle_captured = False

    for raw in md_text.splitlines():
        line = raw.strip()
        if not line:
            continue

        if line.startswith("# "):
            blocks.append(Block("h1", line[2:].strip()))
            seen_h1 = True
            continue

        if line.startswith("## "):
            blocks.append(Block("h2", line[3:].strip()))
            before_first_h2 = False
            continue

        if line.startswith("### "):
            blocks.append(Block("h3", line[4:].strip()))
            continue

        m = BULLET_RE.match(line)
        if m:
            blocks.append(Block("bullet", m.group(1).strip()))
            continue

        if seen_h1 and before_first_h2 and not subtitle_captured:
            blocks.append(Block("subtitle", line))
            subtitle_captured = True
            continue

        blocks.append(Block("paragraph", line))

    return blocks


# --------------------------------------------------------------------------
# 2. Conversao de markdown inline (negrito/italico/links) para markup do
#    ReportLab, com escape correto de caracteres especiais.
# --------------------------------------------------------------------------

LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
ITALIC_RE = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")


def escape_xml(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def md_inline(text: str) -> str:
    text = escape_xml(text)
    text = LINK_RE.sub(
        lambda m: f'<link href="{m.group(2)}" color="#1a4d7a"><u>{m.group(1)}</u></link>',
        text,
    )
    text = BOLD_RE.sub(lambda m: f"<b>{m.group(1)}</b>", text)
    text = ITALIC_RE.sub(lambda m: f"<i>{m.group(1)}</i>", text)
    return text


# --------------------------------------------------------------------------
# 3. Estilos com escala ajustavel (usados para o auto-encaixe de paginas)
# --------------------------------------------------------------------------

def build_styles(scale: float) -> dict:
    def px(base: float, minimum: float) -> float:
        return max(round(base * scale, 2), minimum)

    name_size = px(23, 17)
    subtitle_size = px(12.5, 10.5)
    contact_size = px(9.3, 8.3)
    h2_size = px(11.5, 10)
    h3_size = px(10.3, 9.2)
    dateline_size = px(9.3, 8.3)
    body_size = px(9.6, 8.6)

    styles: dict = {}

    styles["name"] = ParagraphStyle(
        "Name", fontName="Helvetica-Bold", fontSize=name_size,
        leading=name_size * 1.15, alignment=TA_CENTER,
        textColor=colors.HexColor("#111111"), spaceAfter=px(2, 1),
    )
    styles["subtitle"] = ParagraphStyle(
        "Subtitle", fontName="Helvetica", fontSize=subtitle_size,
        leading=subtitle_size * 1.3, alignment=TA_CENTER,
        textColor=colors.HexColor("#3d3d3d"), spaceAfter=px(7, 4),
    )
    styles["contact"] = ParagraphStyle(
        "Contact", fontName="Helvetica", fontSize=contact_size,
        leading=contact_size * 1.35, alignment=TA_CENTER,
        textColor=colors.HexColor("#202020"),
    )
    styles["h2"] = ParagraphStyle(
        "H2", fontName="Helvetica-Bold", fontSize=h2_size,
        leading=h2_size * 1.2, alignment=TA_LEFT,
        textColor=colors.HexColor("#12324f"), spaceBefore=0, spaceAfter=0,
    )
    styles["h3"] = ParagraphStyle(
        "H3", fontName="Helvetica-Bold", fontSize=h3_size,
        leading=h3_size * 1.25, alignment=TA_LEFT,
        textColor=colors.HexColor("#111111"),
        spaceBefore=px(7, 3), spaceAfter=0,
    )
    styles["dateline"] = ParagraphStyle(
        "Dateline", fontName="Helvetica-Oblique", fontSize=dateline_size,
        leading=dateline_size * 1.25, alignment=TA_LEFT,
        textColor=colors.HexColor("#525252"), spaceBefore=0, spaceAfter=px(3, 2),
    )
    styles["body"] = ParagraphStyle(
        "Body", fontName="Helvetica", fontSize=body_size,
        leading=body_size * 1.32, alignment=TA_LEFT,
        textColor=colors.HexColor("#1a1a1a"),
        spaceBefore=px(2, 1), spaceAfter=px(3, 2),
    )
    styles["bullet"] = ParagraphStyle(
        "BulletItem", parent=styles["body"], leftIndent=12, bulletIndent=0,
        spaceBefore=px(1.2, 0.8), spaceAfter=px(1.2, 0.8),
    )

    styles["h2_space_before"] = px(11, 6)
    styles["h2_rule_space_after"] = px(5, 3)
    styles["section_space_after"] = px(6, 3)
    styles["contact_space_after"] = px(8, 5)

    return styles


# --------------------------------------------------------------------------
# 4. Blocos estruturados -> Flowables do ReportLab
# --------------------------------------------------------------------------

def render_section_body(section_blocks: list[Block], styles: dict) -> list:
    flow: list = []
    bullet_buffer: list[str] = []

    def flush_bullets():
        for t in bullet_buffer:
            # "-" em vez de "•": o glifo unicode de bullet e mapeado pelo
            # ReportLab para o byte 0x7F (DEL, nao imprimivel) nas fontes
            # padrao Helvetica, o que quebra a extracao de texto por ATS e
            # pode deixar o marcador invisivel na renderizacao. Hifen e
            # ASCII puro, sem ambiguidade de codificacao em nenhuma fonte.
            flow.append(Paragraph(md_inline(t), styles["bullet"], bulletText="-"))
        bullet_buffer.clear()

    i = 0
    n = len(section_blocks)
    while i < n:
        b = section_blocks[i]

        if b.kind == "h3":
            flush_bullets()
            entry = [Paragraph(md_inline(b.text), styles["h3"])]
            i += 1
            # A linha logo apos o h3 (quando existir e nao for bullet) e a
            # linha de empresa/instituicao + periodo.
            if i < n and section_blocks[i].kind == "paragraph":
                entry.append(Paragraph(md_inline(section_blocks[i].text), styles["dateline"]))
                i += 1
            flow.append(KeepTogether(entry))
            continue

        if b.kind == "bullet":
            bullet_buffer.append(b.text)
            i += 1
            continue

        flush_bullets()
        flow.append(Paragraph(md_inline(b.text), styles["body"]))
        i += 1

    flush_bullets()
    flow.append(Spacer(1, styles["section_space_after"]))
    return flow


def build_flowables(blocks: list[Block], styles: dict) -> list:
    flow: list = []
    idx = 0
    n = len(blocks)

    if idx < n and blocks[idx].kind == "h1":
        flow.append(Paragraph(md_inline(blocks[idx].text), styles["name"]))
        idx += 1

    if idx < n and blocks[idx].kind == "subtitle":
        flow.append(Paragraph(md_inline(blocks[idx].text), styles["subtitle"]))
        idx += 1

    first_section = True
    while idx < n:
        block = blocks[idx]

        if block.kind != "h2":
            # Bloco solto fora de qualquer secao "##" (nao esperado nos
            # arquivos base, mas tratado por seguranca).
            flow.append(Paragraph(md_inline(block.text), styles["body"]))
            idx += 1
            continue

        heading_text = block.text
        idx += 1
        section_blocks: list[Block] = []
        while idx < n and blocks[idx].kind != "h2":
            section_blocks.append(blocks[idx])
            idx += 1

        if first_section:
            first_section = False
            contact_items = [b.text for b in section_blocks if b.kind == "bullet"]
            if contact_items:
                joined = "   |   ".join(md_inline(t) for t in contact_items)
                flow.append(Paragraph(joined, styles["contact"]))
                flow.append(Spacer(1, styles["contact_space_after"]))
            continue

        flow.append(Spacer(1, styles["h2_space_before"]))
        flow.append(Paragraph(md_inline(heading_text).upper(), styles["h2"]))
        flow.append(
            HRFlowable(
                width="100%", thickness=0.75, color=colors.HexColor("#999999"),
                spaceBefore=1, spaceAfter=styles["h2_rule_space_after"],
            )
        )
        flow.extend(render_section_body(section_blocks, styles))

    return flow


# --------------------------------------------------------------------------
# 5. Renderizacao em PDF com contagem de paginas e auto-encaixe de layout
# --------------------------------------------------------------------------

def render_to_buffer(flowables: list, page_size, margins: dict, metadata: dict, page_label: str):
    buf = io.BytesIO()
    page_count = {"n": 0}

    class _CountingCanvas(canvas.Canvas):
        def showPage(self):
            page_count["n"] += 1
            canvas.Canvas.showPage(self)

    left, right, top, bottom = margins["left"], margins["right"], margins["top"], margins["bottom"]
    frame = Frame(
        left, bottom, page_size[0] - left - right, page_size[1] - top - bottom,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id="main",
    )

    def on_page(c, _doc):
        c.saveState()
        c.setFont("Helvetica", 7.5)
        c.setFillColor(colors.HexColor("#8a8a8a"))
        c.drawCentredString(page_size[0] / 2, bottom * 0.45, f"{page_label} {c.getPageNumber()}")
        c.restoreState()

    doc = BaseDocTemplate(
        buf,
        pagesize=page_size,
        leftMargin=left, rightMargin=right, topMargin=top, bottomMargin=bottom,
        title=metadata.get("title", ""),
        author=metadata.get("author", ""),
        subject=metadata.get("subject", ""),
        keywords=metadata.get("keywords", ""),
        creator="gerar_pdf.py",
    )
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=on_page)])
    doc.build(flowables, canvasmaker=_CountingCanvas)

    return buf, page_count["n"]


# Fatores de escala testados em ordem, do layout "normal" ate o mais
# compacto, ate o conteudo caber no limite de paginas configurado.
# Os tamanhos de fonte tem piso minimo (ver build_styles) e param de encolher
# bem antes do fim desta lista; as escalas mais baixas continuam reduzindo
# apenas o espacamento vertical, o que permite encaixar mais conteudo sem
# tornar o texto ilegivel.
SCALE_STEPS = (1.0, 0.94, 0.88, 0.82, 0.76, 0.7, 0.64, 0.58, 0.52)


def render_pdf(md_path: Path, out_path: Path, max_pages: int, page_size, page_label: str) -> int:
    text = md_path.read_text(encoding="utf-8")
    blocks = parse_markdown(text)

    name = next((b.text for b in blocks if b.kind == "h1"), md_path.stem)
    subtitle = next((b.text for b in blocks if b.kind == "subtitle"), "")
    keywords = ", ".join(dict.fromkeys(b.text for b in blocks if b.kind == "bullet"))

    metadata = {
        "title": f"{name} - Curriculum Vitae",
        "author": name,
        "subject": subtitle or "Curriculum Vitae",
        "keywords": keywords[:2000],
    }
    margins = {"left": 2.0 * cm, "right": 2.0 * cm, "top": 1.7 * cm, "bottom": 1.7 * cm}

    best = None
    for scale in SCALE_STEPS:
        styles = build_styles(scale)
        flowables = build_flowables(blocks, styles)
        buf, pages = render_to_buffer(flowables, page_size, margins, metadata, page_label)
        if best is None or pages < best[1]:
            best = (buf, pages, scale)
        if pages <= max_pages:
            break

    buf, pages, scale = best
    out_path.write_bytes(buf.getvalue())

    if pages > max_pages:
        print(
            f"[aviso] {out_path.name}: ficou com {pages} pagina(s) mesmo no espacamento "
            f"mais compacto (escala {scale:.2f}). Considere reduzir o conteudo.",
            file=sys.stderr,
        )
    else:
        print(f"[ok] {out_path.name}: {pages} pagina(s), escala de layout {scale:.2f}")

    return pages


# --------------------------------------------------------------------------
# 6. CLI
# --------------------------------------------------------------------------

BASE_STEM_RE = re.compile(r"^curriculo_base", re.IGNORECASE)


def resolve_output_language(stem: str):
    """Detecta o idioma pelo token '_pt'/'_en' em qualquer posicao do nome,
    nao so no final — assim 'curriculo_base_PT_adapted' ainda e reconhecido
    como PT (ver instructions.md / secao "_adapted" no README).
    """
    tokens = re.split(r"[_\-]", stem.lower())
    if "en" in tokens:
        return LETTER, "Page"
    return A4, "Pagina"


def default_output_name(stem: str) -> str:
    """'curriculo_base_PT' -> 'Curriculo_PT.pdf'; 'curriculo_base_PT_adapted'
    -> 'Curriculo_PT_adapted.pdf' (mantendo o sufixo, para nao colidir com o
    PDF gerado a partir do arquivo base); qualquer outro nome e usado como
    esta.
    """
    if BASE_STEM_RE.match(stem):
        return BASE_STEM_RE.sub("Curriculo", stem) + ".pdf"
    return stem + ".pdf"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Gera PDFs de curriculo otimizados para ATS/IA a partir de Markdown.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemplos:\n"
            "  python gerar_pdf.py\n"
            "  python gerar_pdf.py curriculo_base_PT.md curriculo_base_EN.md\n"
            "  python gerar_pdf.py meu_curriculo.md --out-dir dist --max-pages 1\n"
        ),
    )
    parser.add_argument("arquivos", nargs="*", help="Arquivo(s) Markdown de entrada")
    parser.add_argument(
        "--out-dir", type=Path, default=None,
        help="Diretorio de saida (padrao: mesmo diretorio do .md)",
    )
    parser.add_argument(
        "--max-pages", type=int, default=2,
        help="Numero maximo de paginas antes de reduzir o espacamento (padrao: 2)",
    )
    args = parser.parse_args(argv)

    inputs = [Path(p) for p in args.arquivos]
    if not inputs:
        cwd = Path.cwd()
        defaults = [cwd / "curriculo_base_PT.md", cwd / "curriculo_base_EN.md"]
        inputs = [p for p in defaults if p.exists()]
        if not inputs:
            parser.error(
                "Nenhum arquivo informado e curriculo_base_PT.md / "
                "curriculo_base_EN.md nao foram encontrados no diretorio atual."
            )

    exit_code = 0
    for md_path in inputs:
        if not md_path.exists():
            print(f"[erro] arquivo nao encontrado: {md_path}", file=sys.stderr)
            exit_code = 1
            continue

        page_size, page_label = resolve_output_language(md_path.stem)
        out_dir = args.out_dir or md_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / default_output_name(md_path.stem)

        render_pdf(md_path, out_path, args.max_pages, page_size, page_label)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
