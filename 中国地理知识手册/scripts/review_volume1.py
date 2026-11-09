"""输出上册图件审阅页及成书页面检查结果。"""
import argparse
import json
from collections import Counter
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageFont

from audit_volume1 import contact_sheets

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "上册修订"
QA = OUT / "qa"


def figure_sheets():
    inventory = json.loads((QA / "inventory.json").read_text(encoding="utf-8"))
    items = [dict(item, path=str(OUT / "figures" / item["name"]))
             for item in inventory["figures"]]
    contact_sheets(items, QA, prefix="final")
    warnings = []
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 17)
    for item in items:
        report = json.loads((QA / f'{Path(item["name"]).stem}.collisions.json')
                            .read_text(encoding="utf-8"))
        pdf = OUT / "figures" / Path(item["name"]).with_suffix(".pdf")
        with pymupdf.open(pdf) as doc:
            page = doc[0]
            for finding in report["findings"]:
                rect = pymupdf.Rect(finding["text_bbox"])
                rect = pymupdf.Rect(rect.x0 - 20, rect.y0 - 18,
                                    rect.x1 + 20, rect.y1 + 18) & page.rect
                pix = page.get_pixmap(matrix=pymupdf.Matrix(2.5, 2.5), clip=rect)
                bitmap = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                warnings.append((item["name"], finding, bitmap))
    for offset in range(0, len(warnings), 12):
        sheet = Image.new("RGB", (2000, 1080), "white")
        draw = ImageDraw.Draw(sheet)
        for index, (name, finding, bitmap) in enumerate(warnings[offset:offset + 12]):
            col, row = index % 4, index // 4
            x, y = col * 500, row * 360
            bitmap.thumbnail((480, 280))
            sheet.paste(bitmap, (x + 10, y + 70))
            label = f"{offset + index + 1:02d} {name[:28]}\n"
            label += f'{finding["severity"]} {finding["kind"]} {finding["text"][:28]}'
            draw.text((x + 10, y + 7), label, fill="#222222", font=font)
        sheet.save(QA / f"warning_review_{offset // 12 + 1:02d}.jpg", quality=94)
    index = [dict(number=i + 1, name=name, finding=finding)
             for i, (name, finding, _) in enumerate(warnings)]
    (QA / "warning_review_index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Figure sheets: {len(items)} figures; {len(warnings)} finding crops.")


def book_pages():
    path = OUT / "中国地理知识手册_上册_修订版.pdf"
    pages, image_pages, blanks, clipped = [], [], [], []
    with pymupdf.open(path) as doc:
        for i, page in enumerate(doc):
            blocks = page.get_text("dict")["blocks"]
            images = page.get_image_info()
            body = [block for block in blocks if block["type"] == 0
                    and block["bbox"][3] < page.rect.height - 30]
            if not body and not images:
                blanks.append(i + 1)
            for block in blocks:
                if block["type"] != 0:
                    continue
                for line in block["lines"]:
                    for span in line["spans"]:
                        rect = pymupdf.Rect(span["bbox"])
                        if (rect.x0 < -1 or rect.y0 < -1
                                or rect.x1 > page.rect.width + 1
                                or rect.y1 > page.rect.height + 1):
                            clipped.append(dict(page=i + 1, text=span["text"],
                                                bbox=list(rect)))
            for image in images:
                rect = pymupdf.Rect(image["bbox"])
                if not page.rect.contains(rect):
                    clipped.append(dict(page=i + 1, image=True, bbox=list(rect)))
            if images:
                image_pages.append(i + 1)
            pages.append(dict(page=i + 1, width=round(page.rect.width, 2),
                              height=round(page.rect.height, 2), images=len(images),
                              text_characters=len(page.get_text().strip())))
        orientation = Counter("landscape" if p["width"] > p["height"] else "portrait"
                              for p in pages)
        preview = [1, 2, 6, 11, 31]
        preview += [p["page"] for p in pages if p["width"] > p["height"]][:3]
        preview += [p for p in image_pages if p > len(doc) * 0.65][:2]
        for n in sorted(set(preview)):
            page = doc[n - 1]
            page.get_pixmap(matrix=pymupdf.Matrix(1.3, 1.3)).save(
                QA / f"book_final_{n:03d}.png")
    layout = json.loads((QA / "book_figure_layout.json").read_text(encoding="utf-8"))
    report = dict(pages=len(pages), images=sum(p["images"] for p in pages),
                  orientations=dict(orientation), blank_pages=blanks,
                  clipped_objects=clipped,
                  minimum_figure_font_pt=min(p["minimum_printed_font_pt"] for p in layout),
                  figure_orientations=dict(Counter(p["orientation"] for p in layout)),
                  page_details=pages)
    (QA / "book_review.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "page_details"},
                     ensure_ascii=False, indent=2))
    if blanks or clipped or report["images"] != 204:
        raise ValueError("成书存在缺图、空白页或裁切")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--figures", action="store_true")
    parser.add_argument("--book", action="store_true")
    args = parser.parse_args()
    if args.figures:
        figure_sheets()
    if args.book:
        book_pages()
