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
    python gerar_pdf.py --config outro_config.yml

Margens, escalas de auto-encaixe, cores e tamanhos de fonte vem de
"config.yml" (ao lado deste script, por padrao) e podem ser sobrescritos
sem editar o codigo. Ver config.yml para a lista completa de opcoes.

Requisitos:
    pip install -r requirements.txt
"""

from __future__ import annotations

import argparse
import io
import re
import sys
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

import yaml
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
# 0. Configuracao (config.yml, com fallback embutido)
# --------------------------------------------------------------------------

DEFAULT_CONFIG = {
    "max_pages": 2,
    "out_dir": None,
    "margins_cm": {"left": 2.0, "right": 2.0, "top": 1.7, "bottom": 1.7},
    "scale_steps": [1.0, 0.94, 0.88, 0.82, 0.76, 0.7, 0.64, 0.58, 0.52],
    "languages": {
        "pt": {"page_size": "A4", "page_label": "Pagina"},
        "en": {"page_size": "LETTER", "page_label": "Page"},
        "default": {"page_size": "A4", "page_label": "Pagina"},
    },
    "colors": {
        "rule": "#999999",
        "page_number": "#8a8a8a",
        "link": "#1a4d7a",
    },
    "styles": {
        "name": {"font_size": 23, "font_size_min": 17, "color": "#111111"},
        "subtitle": {"font_size": 12.5, "font_size_min": 10.5, "color": "#3d3d3d"},
        "contact": {"font_size": 9.3, "font_size_min": 8.3, "color": "#202020"},
        "h2": {"font_size": 11.5, "font_size_min": 10, "color": "#12324f"},
        "h3": {"font_size": 10.3, "font_size_min": 9.2, "color": "#111111"},
        "dateline": {"font_size": 9.3, "font_size_min": 8.3, "color": "#525252"},
        "body": {"font_size": 9.6, "font_size_min": 8.6, "color": "#1a1a1a"},
    },
}

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config.yml"

PAGE_SIZES = {"A4": A4, "LETTER": LETTER}


def deep_merge(base: dict, override: dict) -> dict:
    """Mescla `override` sobre `base`, recursivamente para chaves que sao
    dicts nos dois lados. Permite que o config.yml do usuario sobrescreva
    so as chaves que quiser, mantendo o resto do padrao embutido.
    """
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(config_path: Path | None) -> dict:
    path = config_path or DEFAULT_CONFIG_PATH
    config = deepcopy(DEFAULT_CONFIG)
    if not path.exists():
        return config
    with path.open(encoding="utf-8") as f:
        user_config = yaml.safe_load(f) or {}
    return deep_merge(config, user_config)


# Populado por load_config() em main(); os valores padrao aqui garantem que
# as funcoes abaixo continuem funcionando mesmo se chamadas sem passar por
# main() (ex: em um script/teste que importa este modulo).
CFG = deepcopy(DEFAULT_CONFIG)


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
    link_color = CFG["colors"]["link"]
    text = LINK_RE.sub(
        lambda m: f'<link href="{m.group(2)}" color="{link_color}"><u>{m.group(1)}</u></link>',
        text,
    )
    text = BOLD_RE.sub(lambda m: f"<b>{m.group(1)}</b>", text)
    text = ITALIC_RE.sub(lambda m: f"<i>{m.group(1)}</i>", text)
    return text


# --------------------------------------------------------------------------
# 3. Estilos com escala ajustavel (usados para o auto-encaixe de paginas)
# --------------------------------------------------------------------------

def build_styles(scale: float) -> dict:
    s = CFG["styles"]

    def px(base: float, minimum: float) -> float:
        return max(round(base * scale, 2), minimum)

    name_size = px(s["name"]["font_size"], s["name"]["font_size_min"])
    subtitle_size = px(s["subtitle"]["font_size"], s["subtitle"]["font_size_min"])
    contact_size = px(s["contact"]["font_size"], s["contact"]["font_size_min"])
    h2_size = px(s["h2"]["font_size"], s["h2"]["font_size_min"])
    h3_size = px(s["h3"]["font_size"], s["h3"]["font_size_min"])
    dateline_size = px(s["dateline"]["font_size"], s["dateline"]["font_size_min"])
    body_size = px(s["body"]["font_size"], s["body"]["font_size_min"])

    styles: dict = {}

    styles["name"] = ParagraphStyle(
        "Name", fontName="Helvetica-Bold", fontSize=name_size,
        leading=name_size * 1.15, alignment=TA_CENTER,
        textColor=colors.HexColor(s["name"]["color"]), spaceAfter=px(2, 1),
    )
    styles["subtitle"] = ParagraphStyle(
        "Subtitle", fontName="Helvetica", fontSize=subtitle_size,
        leading=subtitle_size * 1.3, alignment=TA_CENTER,
        textColor=colors.HexColor(s["subtitle"]["color"]), spaceAfter=px(7, 4),
    )
    styles["contact"] = ParagraphStyle(
        "Contact", fontName="Helvetica", fontSize=contact_size,
        leading=contact_size * 1.35, alignment=TA_CENTER,
        textColor=colors.HexColor(s["contact"]["color"]),
    )
    styles["h2"] = ParagraphStyle(
        "H2", fontName="Helvetica-Bold", fontSize=h2_size,
        leading=h2_size * 1.2, alignment=TA_LEFT,
        textColor=colors.HexColor(s["h2"]["color"]), spaceBefore=0, spaceAfter=0,
    )
    styles["h3"] = ParagraphStyle(
        "H3", fontName="Helvetica-Bold", fontSize=h3_size,
        leading=h3_size * 1.25, alignment=TA_LEFT,
        textColor=colors.HexColor(s["h3"]["color"]),
        spaceBefore=px(7, 3), spaceAfter=0,
    )
    styles["dateline"] = ParagraphStyle(
        "Dateline", fontName="Helvetica-Oblique", fontSize=dateline_size,
        leading=dateline_size * 1.25, alignment=TA_LEFT,
        textColor=colors.HexColor(s["dateline"]["color"]), spaceBefore=0, spaceAfter=px(3, 2),
    )
    styles["body"] = ParagraphStyle(
        "Body", fontName="Helvetica", fontSize=body_size,
        leading=body_size * 1.32, alignment=TA_LEFT,
        textColor=colors.HexColor(s["body"]["color"]),
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
    styles["rule_color"] = colors.HexColor(CFG["colors"]["rule"])

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
                width="100%", thickness=0.75, color=styles["rule_color"],
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
        c.setFillColor(colors.HexColor(CFG["colors"]["page_number"]))
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
    m = CFG["margins_cm"]
    margins = {
        "left": m["left"] * cm, "right": m["right"] * cm,
        "top": m["top"] * cm, "bottom": m["bottom"] * cm,
    }

    best = None
    for scale in CFG["scale_steps"]:
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
    """Detecta o idioma pelo token de "languages" em config.yml (ex: 'pt',
    'en') em qualquer posicao do nome separada por '_'/'-', nao so no final:
    assim 'curriculo_base_PT_adapted' ainda e reconhecido como PT. Cai em
    "languages.default" quando nenhum token bate.
    """
    tokens = re.split(r"[_\-]", stem.lower())
    languages = CFG["languages"]
    for token, lang_cfg in languages.items():
        if token != "default" and token in tokens:
            return PAGE_SIZES[lang_cfg["page_size"]], lang_cfg["page_label"]
    default_cfg = languages.get("default", DEFAULT_CONFIG["languages"]["default"])
    return PAGE_SIZES[default_cfg["page_size"]], default_cfg["page_label"]


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
            "  python gerar_pdf.py --config outro_config.yml\n"
        ),
    )
    parser.add_argument("arquivos", nargs="*", help="Arquivo(s) Markdown de entrada")
    parser.add_argument(
        "--out-dir", type=Path, default=None,
        help="Diretorio de saida (padrao: 'out_dir' em config.yml, ou o "
             "mesmo diretorio do .md se 'out_dir' nao estiver definido)",
    )
    parser.add_argument(
        "--max-pages", type=int, default=None,
        help="Numero maximo de paginas antes de reduzir o espacamento "
             "(padrao: valor de 'max_pages' em config.yml, normalmente 2)",
    )
    parser.add_argument(
        "--config", type=Path, default=None,
        help="Caminho para um config.yml alternativo (padrao: config.yml "
             "ao lado deste script)",
    )
    args = parser.parse_args(argv)

    global CFG
    CFG = load_config(args.config)
    max_pages = args.max_pages if args.max_pages is not None else CFG["max_pages"]

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
        config_out_dir = Path(CFG["out_dir"]) if CFG["out_dir"] else None
        out_dir = args.out_dir or config_out_dir or md_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / default_output_name(md_path.stem)

        render_pdf(md_path, out_path, max_pages, page_size, page_label)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
