"""下册图件审阅页与成书完整性检查。"""
import argparse
import json
import re
import shutil
from collections import Counter
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageFont

from audit_volume1 import contact_sheets

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "下册修订"
QA = OUT / "qa"


def sample():
    import build_volume2 as build
    destination = QA / "sample"
    (destination / "figures").mkdir(parents=True, exist_ok=True)
    (destination / "qa").mkdir(exist_ok=True)
    sections = [next((ROOT / "sections_vol2").glob("02-00_*.md")),
                next((ROOT / "sections_vol2").glob("02-17_*.md"))]
    for section in sections:
        for name in re.findall(r"!\[[^\]]*\]\(\.\./figures/([^)]+)\)",
                               section.read_text(encoding="utf-8")):
            for suffix in [".png", ".pdf"]:
                source = (OUT / "figures" / name).with_suffix(suffix)
                shutil.copy2(source, destination / "figures" / source.name)
    build.OUT = destination
    build.chapters = lambda: [("第 2 章　天津市", sections)]
    build.build_pdf()
    pdf = destination / "中国地理知识手册_下册_修订版.pdf"
    with pymupdf.open(pdf) as document:
        for page_number in [0, 1, 3, 5, len(document) - 4, len(document) - 2]:
            document[page_number].get_pixmap(
                matrix=pymupdf.Matrix(1.2, 1.2)).save(
                    destination / f"page_{page_number + 1:03d}.png")
    print("Sample PDF:", pdf)


def figure_sheets():
    manifest = json.loads((QA / "inventory.json").read_text(encoding="utf-8"))
    for chapter in range(1, 35):
        items = [dict(item, path=str(OUT / "figures" / item["name"]))
                 for item in manifest["figures"]
                 if item["name"].startswith(f"fig{chapter:02d}-")]
        contact_sheets(items, QA / "sheets", f"chapter_{chapter:02d}")
    finding_sheets()
    print("Figures:", len(manifest["figures"]))


def finding_sheets():
    findings = []
    for report_file in sorted(QA.glob("*.collisions.json")):
        report = json.loads(report_file.read_text(encoding="utf-8"))
        with pymupdf.open(report["pdf"]) as document:
            page = document[0]
            for finding in report["findings"]:
                clip = pymupdf.Rect(finding["text_bbox"]) + (-15, -15, 15, 15)
                clip &= page.rect
                pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=clip)
                bitmap = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                findings.append((report_file.stem, finding, bitmap))
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 16)
    for start in range(0, len(findings), 20):
        sheet = Image.new("RGB", (2000, 1350), "white")
        draw = ImageDraw.Draw(sheet)
        for slot, (name, finding, bitmap) in enumerate(findings[start:start + 20]):
            x, y = slot % 4 * 500, slot // 4 * 270
            bitmap.thumbnail((475, 190))
            sheet.paste(bitmap, (x + 10, y + 65))
            label = f"{start + slot + 1} {name[:28]}\n{finding['kind']} {finding['text'][:25]}"
            draw.text((x + 10, y + 3), label, font=font, fill="#28383F")
        sheet.save(QA / f"finding_review_{start // 20 + 1:03d}.jpg", quality=94)
    index = [dict(number=i + 1, figure=name, finding=finding)
             for i, (name, finding, _) in enumerate(findings)]
    (QA / "finding_review_index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Finding crops:", len(findings))


def book_pages():
    pdf = OUT / "中国地理知识手册_下册_修订版.pdf"
    pages, blank, clipped, glyphs = [], [], [], []
    layout = json.loads((QA / "book_figure_layout.json").read_text(encoding="utf-8"))
    figure_pages, figure_index = [], 0
    sample_figures = {
        "fig01-06-4", "fig02-00-5", "fig12-00-5", "fig16-00-1",
        "fig20-00-1", "fig21-00-5", "fig27-00-5", "fig32-06-2",
    }
    units_preview = False
    with pymupdf.open(pdf) as document:
        bookmarks = document.get_toc()
        previews = {1, 2, 3}
        previews.update(row[2] for row in bookmarks if row[0] == 1)
        previews.update(row[2] + 1 for row in bookmarks
                        if "天津" in row[1] and "矩阵" in row[1])
        for page_number, page in enumerate(document, 1):
            blocks = page.get_text("dict", flags=pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES)["blocks"]
            images = page.get_image_info()
            for image in images:
                name = layout[figure_index]["name"]
                figure_pages.append(dict(name=name, page=page_number))
                if name.split("_", 1)[0] in sample_figures:
                    previews.add(page_number)
                figure_index += 1
            body = [block for block in blocks if block["type"] == 0
                    and block["bbox"][3] < page.rect.height - 30]
            if not body and not images:
                blank.append(page_number)
            for block in blocks:
                if block["type"] != 0:
                    continue
                for line in block["lines"]:
                    for span in line["spans"]:
                        bounds = pymupdf.Rect(span["bbox"])
                        if (bounds.x0 < -1 or bounds.y0 < -1
                                or bounds.x1 > page.rect.width + 1
                                or bounds.y1 > page.rect.height + 1):
                            clipped.append(dict(page=page_number, text=span["text"]))
                        if "\ufffd" in span["text"] or "\x00" in span["text"]:
                            glyphs.append(dict(page=page_number, text=span["text"]))
                        if not units_preview and "²" in span["text"]:
                            previews.add(page_number)
                            units_preview = True
            for image in images:
                if not page.rect.contains(pymupdf.Rect(image["bbox"])):
                    clipped.append(dict(page=page_number, image=True))
            pages.append(dict(page=page_number, images=len(images),
                              width=page.rect.width, height=page.rect.height))
            if page_number in previews:
                page.get_pixmap(matrix=pymupdf.Matrix(1.1, 1.1)).save(
                    QA / f"book_page_{page_number:04d}.png")
        actual_titles = {row[1].replace(" ", "") for row in bookmarks}
        missing_headings = []
        for source in (ROOT / "sections_vol2").glob("*.md"):
            title = source.read_text(encoding="utf-8-sig").splitlines()[0].lstrip("# ").replace(" ", "")
            if title not in actual_titles:
                missing_headings.append(source.name)
    report = dict(pages=len(pages), images=sum(row["images"] for row in pages),
                  bookmark_entries=len(bookmarks), missing_headings=missing_headings,
                  blank_pages=blank, clipped_objects=clipped, missing_glyphs=glyphs,
                  minimum_figure_font_pt=min(item["minimum_printed_font_pt"] for item in layout),
                  figure_orientations=dict(Counter(item["orientation"] for item in layout)),
                  page_details=pages)
    (QA / "figure_pages.json").write_text(
        json.dumps(figure_pages, ensure_ascii=False, indent=2), encoding="utf-8")
    (QA / "book_review.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "page_details"},
                     ensure_ascii=False, indent=2))
    if blank or clipped or glyphs or missing_headings or report["images"] != 2400:
        raise ValueError("下册存在缺图、章节遗漏、空白页、文字缺字或裁切")


def sample_book():
    topics = {
        "fig01-06-4": "密集地图与分类符号",
        "fig02-00-5": "地图图例与地点索引",
        "fig12-00-5": "夜光指标与横向柱图",
        "fig16-00-1": "地形图与独立高程色带",
        "fig20-00-1": "主图与南海诸岛附图",
        "fig21-00-5": "区县比较与缺失值说明",
        "fig27-00-5": "不同单位指标分别比较",
        "fig32-06-2": "水系地形与地图编号",
    }
    figure_pages = json.loads((QA / "figure_pages.json").read_text(encoding="utf-8"))
    selected = {2: "数据口径与已知问题"}
    for item in figure_pages:
        code = item["name"].split("_", 1)[0]
        if code in topics:
            selected[item["page"]] = topics[code]
    source = OUT / "中国地理知识手册_下册_修订版.pdf"
    target = OUT / "下册修订样页.pdf"
    with pymupdf.open(source) as document, pymupdf.open() as sample:
        headings = document.get_toc()
        selected[next(row[2] for row in headings
                      if "北京市地理统揽" in row[1])] = "单位字形与正文表格"
        table_page = next(row[2] for row in headings
                          if "天津" in row[1] and "矩阵" in row[1])
        selected[table_page] = "宽表分组"
        selected[table_page + 1] = "跨页重复表头"
        diagram_start = next(row[2] for row in headings
                             if "辽宁省地理统揽" in row[1])
        diagram_page = next(page + 1 for page in range(diagram_start - 1, diagram_start + 10)
                            if "宏观构造与地貌剖面示意表" in document[page].get_text())
        selected[diagram_page] = "地貌剖面表格"
        contents, records = [], []
        for index, (page_number, topic) in enumerate(sorted(selected.items()), 1):
            sample.insert_pdf(document, from_page=page_number - 1, to_page=page_number - 1)
            contents.append([1, f"{topic}（原页 {page_number}）", index])
            records.append(dict(page=index, source_page=page_number, topic=topic))
        sample.set_toc(contents)
        sample.set_metadata(dict(title="中国地理知识手册·下册修订样页", author=""))
        sample.save(target, garbage=3, deflate=True)
    previews = QA / "sample_book"
    previews.mkdir(exist_ok=True)
    with pymupdf.open(source) as document, pymupdf.open(target) as sample:
        for item in records:
            page = sample[item["page"] - 1]
            original = document[item["source_page"] - 1]
            if (page.get_text() != original.get_text()
                    or len(page.get_image_info()) != len(original.get_image_info())
                    or page.rect != original.rect):
                raise ValueError(f"样页内容不一致：{item['page']}")
            page.get_pixmap(matrix=pymupdf.Matrix(1.1, 1.1)).save(
                previews / f"page_{item['page']:02d}.png")
    (QA / "sample_book.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Sample pages:", len(records), target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--figures", action="store_true")
    parser.add_argument("--findings", action="store_true")
    parser.add_argument("--book", action="store_true")
    parser.add_argument("--sample-book", action="store_true")
    args = parser.parse_args()
    if args.sample:
        sample()
    if args.figures:
        figure_sheets()
    elif args.findings:
        finding_sheets()
    if args.book:
        book_pages()
    if args.sample_book:
        sample_book()
