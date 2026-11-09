"""最终 PDF 结构、文字和代表页面检查。"""

import json
import re
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "修订20261105"


def verify(volume, pdf_name, source_pdf=None):
    folder = OUT / volume
    pdf = folder / pdf_name
    document = pymupdf.open(pdf)
    blank, clipped, glyphs, pages_with_images = [], [], [], []
    text_lengths = []
    for page_number, page in enumerate(document, 1):
        text = page.get_text()
        text_lengths.append(len(text))
        blocks = page.get_text(
            "dict", flags=pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES
        )["blocks"]
        images = page.get_images(full=True)
        if images:
            pages_with_images.append(page_number)
        has_text = any(block["type"] == 0 and any(
            line["spans"] for line in block["lines"]) for block in blocks)
        if not has_text and not images:
            blank.append(page_number)
        for block in blocks:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    box = pymupdf.Rect(span["bbox"])
                    if (box.x0 < -1 or box.y0 < -1
                            or box.x1 > page.rect.width + 1
                            or box.y1 > page.rect.height + 1):
                        clipped.append(dict(page=page_number, text=span["text"]))
                    if "\ufffd" in span["text"]:
                        glyphs.append(dict(page=page_number, text=span["text"]))
    source_mismatch = []
    if source_pdf:
        source = pymupdf.open(source_pdf)
        if len(source) != len(document):
            source_mismatch.append(dict(kind="page_count",
                                        source=len(source), final=len(document)))
        else:
            for i, page in enumerate(document):
                if page.get_text() != source[i].get_text():
                    source_mismatch.append(dict(kind="text", page=i + 1))
        source.close()
    bookmarks = document.get_toc()
    render_dir = folder / "qa" / "final_render"
    render_dir.mkdir(parents=True, exist_ok=True)
    selected = sorted({1, 2, len(document), *[row[2] for row in bookmarks[:6]]})
    selected += [p for p in pages_with_images[:3]]
    selected = sorted({p for p in selected if 1 <= p <= len(document)})
    for p in selected:
        document[p - 1].get_pixmap(matrix=pymupdf.Matrix(1.1, 1.1)).save(
            render_dir / f"page_{p:05d}.png")
    report = dict(
        volume=volume, pdf=str(pdf), bytes=pdf.stat().st_size,
        pages=len(document), bookmarks=len(bookmarks),
        blank_pages=blank, clipped_objects=clipped, missing_glyphs=glyphs,
        pages_with_images=len(pages_with_images), selected_render_pages=selected,
        source_mismatch=source_mismatch,
        text_min=min(text_lengths), text_max=max(text_lengths),
    )
    (folder / "qa" / "final_pdf_validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items()
                      if k not in {"text_min", "text_max"}}, ensure_ascii=False))
    if blank or clipped or glyphs or source_mismatch:
        raise ValueError(f"{volume} final PDF validation failed")


def main():
    verify("上册", "中国地理知识手册_上册_修订压缩版.pdf",
           OUT / "上册" / "中国地理知识手册_上册_修订压缩版.pdf")
    verify("下册", "中国地理知识手册_下册_最终压缩版.pdf",
           OUT / "下册" / "中国地理知识手册_下册_修订压缩版.pdf")


if __name__ == "__main__":
    main()
