"""组装上册修订版 HTML 与 A4 PDF。"""
import argparse
import base64
import html
import json
import os
import re
import shutil
from pathlib import Path
from xml.etree import ElementTree as ET

import markdown
from PIL import Image as PILImage

from build_book import CHAPTERS, CSS, demote
from book_pdf_assets import (
    VectorFigure, embed_figures, figure_numbers, figure_parts, prepared_text,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "上册修订"
FIGURES = OUT / "figures"
NUMBERING = None

EXTRA_CSS = """
body { background:white; }
.book { max-width:1000px; box-shadow:none; }
img { border:0; box-shadow:none; height:auto; }
table { table-layout:auto; overflow-wrap:anywhere; }
pre { white-space:pre-wrap; overflow-wrap:anywhere; }
h1,h2,h3,h4 { break-after:avoid; }
@media (max-width:700px) {
  .book { padding:24px 18px; }
  table { font-size:12px; }
}
@media print {
  @page { size:A4; margin:16mm 13mm; }
  img { max-height:240mm; object-fit:contain; break-inside:avoid; }
  tr { break-inside:avoid; }
  thead { display:table-header-group; }
}
"""


def chapters():
    files = sorted(p for p in (ROOT / "sections").glob("*.md")
                   if "推进登记" not in p.name)
    for title, prefixes in CHAPTERS:
        selected = [p for p in files if any(p.name.startswith(x) for x in prefixes)]
        if selected:
            yield title, selected


def section_html(path):
    global NUMBERING
    if NUMBERING is None:
        NUMBERING = figure_numbers(chapters())
    text = prepared_text(path, NUMBERING)
    prefix = Path(os.path.relpath(FIGURES, OUT)).as_posix()
    text = re.sub(r"\.\./figures/([^)\s]+)", lambda m: f"{prefix}/{m[1]}", text)
    return markdown.markdown(text, extensions=["tables", "sane_lists", "fenced_code"])


def build_html(filename="中国地理知识手册_上册_修订版.html"):
    toc, body = [], []
    count = 0
    figure_count = 0
    for i, (title, files) in enumerate(chapters(), 1):
        toc.append(f'<li><a href="#chapter-{i}">{html.escape(title)}</a><ul>')
        part = [f'<section class="chapter" id="chapter-{i}"><h1>{title}</h1>']
        for path in files:
            ident = path.stem if path.name.startswith("99_") else path.stem.split("_", 1)[0]
            heading = path.read_text(encoding="utf-8-sig").splitlines()[0].lstrip("# ")
            toc.append(f'<li><a href="#s-{ident}">{html.escape(heading)}</a></li>')
            rendered = section_html(path)
            figure_count += len(re.findall(r"<img\b", rendered))
            part.append(f'<div id="s-{ident}">{demote(rendered)}</div>')
            count += 1
        toc.append("</ul></li>")
        part.append("</section>")
        body.append("\n".join(part))
    document = (
        '<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>中国地理知识手册·上册</title><style>' + CSS + EXTRA_CSS + '</style>'
        '<div class="book"><div class="cover"><h1>中国地理知识手册</h1>'
        '<div class="sub">上册 · 全国自然与人文地理总论及省级行政区速览</div>'
        f'<div class="meta">2026 年 11 月修订<br>{count} 节 · {figure_count} 幅图</div></div>'
        '<nav class="toc"><h2>目录</h2><ul>' + "\n".join(toc) +
        "</ul></nav>" + "\n".join(body) + "</div></html>"
    )
    path = OUT / filename
    path.write_text(document, encoding="utf-8")
    return path


def build_pdf():
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A3, A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        BaseDocTemplate, Frame, Image, PageBreak, PageTemplate,
        NextPageTemplate, Paragraph, Spacer, Table, TableStyle,
    )
    from reportlab.platypus.tableofcontents import TableOfContents

    pdfmetrics.registerFont(TTFont("BookSong", "C:/Windows/Fonts/simsun.ttc",
                                  subfontIndex=0))
    pdfmetrics.registerFont(TTFont("BookHei", "C:/Windows/Fonts/simhei.ttf"))
    pdfmetrics.registerFont(TTFont("BookUnit", "C:/Windows/Fonts/msyh.ttc",
                                  subfontIndex=0))
    pdfmetrics.registerFontFamily("BookUnit", normal="BookUnit", bold="BookUnit",
                                 italic="BookUnit", boldItalic="BookUnit")
    pdfmetrics.registerFontFamily("BookSong", normal="BookSong", bold="BookHei",
                                 italic="BookSong", boldItalic="BookHei")
    styles = {
        "body": ParagraphStyle("body", fontName="BookSong", fontSize=10.2,
                               leading=17, spaceAfter=7, wordWrap="CJK"),
        "cell": ParagraphStyle("cell", fontName="BookSong", fontSize=8.2,
                               leading=12.8, wordWrap="CJK"),
        "caption": ParagraphStyle("caption", fontName="BookSong", fontSize=9,
                                  leading=14, spaceAfter=10, wordWrap="CJK"),
    }
    for level, size in [(1, 19), (2, 15), (3, 12), (4, 11), (5, 10.5)]:
        styles[f"h{level}"] = ParagraphStyle(
            f"h{level}", parent=styles["body"], fontName="BookHei", fontSize=size,
            leading=size * 1.5, spaceBefore=12, spaceAfter=8, keepWithNext=True,
        )
    width = A4[0] - 76
    records = []

    class BookDoc(BaseDocTemplate):
        def beforeDocument(self):
            self.heading_serial = 0
            self.figure_placements = []
            records.clear()

        def afterFlowable(self, flowable):
            if isinstance(flowable, Paragraph) and flowable.style.name in {"h1", "h2"}:
                level = 0 if flowable.style.name == "h1" else 1
                title = flowable.getPlainText()
                if self.page <= 1 or title == "目录":
                    return
                key = f"section-{self.heading_serial}"
                self.heading_serial += 1
                records.append((title, self.page))
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(title, key, level=level, closed=False)
                self.notify("TOCEntry", (level, title, self.page, key))

    def footer(canvas, doc):
        canvas.setFont("BookSong", 8)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(38, 24, "中国地理知识手册 · 上册")
        canvas.drawRightString(canvas._pagesize[0] - 38, 24, str(doc.page))

    layout_path = OUT / "中国地理知识手册_上册_版面.pdf"
    final_path = OUT / "中国地理知识手册_上册_修订压缩版.pdf"
    doc = BookDoc(str(layout_path), pagesize=A4,
                  leftMargin=38, rightMargin=38, topMargin=40, bottomMargin=40,
                  title="中国地理知识手册·上册", author="")
    doc.addPageTemplates(PageTemplate(
        id="book", pagesize=A4, frames=[Frame(38, 40, width, A4[1] - 80,
                                leftPadding=0, rightPadding=0,
                                topPadding=0, bottomPadding=0)], onPage=footer))
    for ident, paper in [("wide", landscape(A4)), ("foldout", landscape(A3)),
                         ("tall", A3)]:
        doc.addPageTemplates(PageTemplate(
            id=ident, pagesize=paper,
            frames=[Frame(38, 40, paper[0] - 76, paper[1] - 80,
                          leftPadding=0, rightPadding=0,
                          topPadding=0, bottomPadding=0)], onPage=footer))
    story = [Spacer(1, 120),
             Paragraph("中国地理知识手册", ParagraphStyle(
                 "cover", fontName="BookHei", fontSize=28, leading=45,
                 alignment=TA_CENTER)),
             Spacer(1, 25),
             Paragraph("上册", ParagraphStyle("volume", parent=styles["h2"],
                                             alignment=TA_CENTER)),
             Paragraph("全国自然与人文地理总论<br/>省级行政区速览",
                       ParagraphStyle("sub", parent=styles["body"], alignment=TA_CENTER)),
             Spacer(1, 50),
             Paragraph("2026 年 11 月修订", ParagraphStyle(
                 "date", parent=styles["body"], alignment=TA_CENTER)), PageBreak(),
             Paragraph("目录", styles["h1"])]
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle("toc0", parent=styles["body"], fontName="BookHei",
                       spaceBefore=8, leading=15),
        ParagraphStyle("toc1", parent=styles["body"], leftIndent=14, fontSize=9,
                       leading=14, spaceAfter=3),
    ]
    story += [toc]

    def inline(node):
        def escaped(value):
            return re.sub("[²³⁴⁸]", lambda match:
                          f'<font name="BookUnit">{match[0]}</font>', html.escape(value))
        text = escaped(node.text or "")
        for child in node:
            tag = {"strong": "b", "em": "i"}.get(child.tag, child.tag)
            inner = inline(child)
            if tag in {"b", "i", "sub", "sup"}:
                text += f"<{tag}>{inner}</{tag}>"
            elif tag == "br":
                text += "<br/>"
            elif tag == "a" and child.get("href", "").startswith(("http:", "https:")):
                text += f'<link href="{html.escape(child.get("href"), quote=True)}">{inner}</link>'
            else:
                text += inner
            text += escaped(child.tail or "")
        return text

    wide_open = False
    figure_layout = []

    def close_wide():
        nonlocal wide_open
        if wide_open:
            story.extend([NextPageTemplate("book"), PageBreak()])
            wide_open = False

    def flow(node, demotion=1):
        nonlocal wide_open
        if wide_open:
            if node.tag == "p" and inline(node).startswith("<b>图"):
                story.append(Paragraph(inline(node), styles["caption"]))
                close_wide()
                return
            close_wide()
        if re.fullmatch("h[1-6]", node.tag):
            level = min(int(node.tag[1]) + demotion, 5)
            story.append(Paragraph(inline(node), styles[f"h{level}"]))
        elif node.tag == "p":
            image = node.find("img")
            if image is not None:
                path = OUT / image.get("src")
                for part in figure_parts(path.with_suffix(".pdf")):
                    orientation = part["orientation"]
                    ident = "book" if orientation == "portrait" else orientation
                    if story and isinstance(story[-1], PageBreak):
                        story.insert(len(story) - 1, NextPageTemplate(ident))
                    else:
                        story.extend([NextPageTemplate(ident), PageBreak()])
                    if part["part"] == "index":
                        story.append(Paragraph("地点与要素索引（与前页主图编号对应）",
                                               styles["caption"]))
                    figure_layout.append(dict(name=path.name, **part))
                    story.append(VectorFigure(path.with_suffix(".pdf"), part["clip"],
                                              part["width"], part["height"]))
                    story.append(Spacer(1, 7))
                    wide_open = True
            else:
                content = inline(node)
                style = "caption" if content.startswith("<b>图") else "body"
                story.append(Paragraph(content, styles[style]))
        elif node.tag == "table":
            rows = node.findall(".//tr")
            data = [[Paragraph(inline(cell), styles["cell"]) for cell in row]
                    for row in rows]
            if data:
                columns = len(data[0])
                table = Table(data, colWidths=[width / columns] * columns,
                              repeatRows=1, hAlign="LEFT")
                table.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E7EDEF")),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C5CDD0")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]))
                story.extend([table, Spacer(1, 9)])
        elif node.tag in {"ul", "ol"}:
            for i, item in enumerate(node.findall("li"), 1):
                prefix = f"{i}. " if node.tag == "ol" else "· "
                story.append(Paragraph(prefix + inline(item), styles["body"]))
        elif node.tag in {"blockquote", "div"}:
            for child in node:
                flow(child, demotion)
        elif node.tag == "pre":
            story.append(Paragraph(html.escape("".join(node.itertext())).replace(
                "\n", "<br/>"), styles["body"]))

    for title, files in chapters():
        close_wide()
        if not isinstance(story[-1], PageBreak):
            story.append(PageBreak())
        story.append(Paragraph(html.escape(title), styles["h1"]))
        for path in files:
            content = re.sub(r"<br\s*>", "<br/>", section_html(path))
            content = content.replace("&nbsp;", "&#160;")
            tree = ET.fromstring("<root>" + content + "</root>")
            for node in tree:
                flow(node)
    doc.multiBuild(story)
    embed_figures(layout_path, final_path, doc.figure_placements,
                  OUT / "qa" / "pdf_compression.json")
    (OUT / "qa" / "book_figure_layout.json").write_text(
        json.dumps(figure_layout, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "qa" / "book_pages.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print("PDF written", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--html-only", action="store_true")
    parser.add_argument("--html-name", default="中国地理知识手册_上册_修订版.html")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    global OUT
    if args.output_dir:
        OUT = args.output_dir.resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "qa").mkdir(exist_ok=True)
    figures = FIGURES
    figures.mkdir(parents=True, exist_ok=True)
    sections = list((ROOT / "sections").glob("*.md"))
    for section in sections:
        if "推进登记" in section.name:
            continue
        for name in re.findall(r"!\[[^\]]*\]\(\.\./figures/([^)]+)\)",
                               section.read_text(encoding="utf-8-sig")):
            if not (figures / name).exists():
                if name != "fig4-2_柯本气候分类图.png":
                    raise FileNotFoundError(f"上册修订图件未生成：{name}")
                shutil.copy2(ROOT / "figures" / name, figures / name)
    print(build_html(args.html_name), flush=True)
    (OUT / "qa" / "figure_numbers.json").write_text(
        json.dumps(NUMBERING, ensure_ascii=False, indent=2), encoding="utf-8")
    if not args.html_only:
        build_pdf()


if __name__ == "__main__":
    main()
