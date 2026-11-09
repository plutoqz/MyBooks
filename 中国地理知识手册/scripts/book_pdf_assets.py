"""成书矢量图嵌入、底图压缩与图号编排。"""

import io
import json
import re
from pathlib import Path

import pymupdf
import numpy as np
from PIL import Image
from reportlab.lib.pagesizes import A3, A4, landscape
from reportlab.platypus import Flowable


def figure_numbers(chapter_groups):
    mapping = {}
    for title, files in chapter_groups:
        serial = 0
        for path in files:
            text = path.read_text(encoding="utf-8-sig")
            chapter = int(re.match(r"\d+", path.name)[0])
            for name in re.findall(r"!\[[^\]]*\]\(\.\./figures/([^)]+)\)", text):
                old = re.match(r"fig([\d-]+)_", name)[1]
                if old not in mapping:
                    serial += 1
                    mapping[old] = f"{chapter}-{serial}"
    return mapping


def number_text(text, mapping):
    return re.sub(
        r"图\s*(\d+(?:-\d+){1,2})(?![\d-])",
        lambda match: "图 " + mapping.get(match[1], match[1]),
        text,
    )


def prepared_text(path, mapping):
    text = path.read_text(encoding="utf-8-sig")
    # 图件文件名是稳定资源编号，显示图号单独按阅读顺序编排。
    text = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        lambda match: f"![{number_text(match[1], mapping)}]({match[2]})",
        text,
    )
    lines = text.splitlines()
    result = []
    for index, line in enumerate(lines):
        if line.startswith("!["):
            result.append(line)
            name = re.search(r"/(fig[\d-]+_[^)]+)\)", line)[1]
            old = re.match(r"fig([\d-]+)_", name)[1]
            following = next((s for s in lines[index + 1:] if s.strip()), "")
            if not following.startswith("**图"):
                label = re.search(r"!\[([^\]]*)\]", line)[1]
                label = re.sub(r"^图\s*[\d-]+\s*", "", label)
                result.extend(["", f"**图 {mapping[old]} {label}**"])
        else:
            result.append(number_text(line, mapping))
    return "\n".join(result) + "\n"


class VectorFigure(Flowable):
    def __init__(self, source, clip, width, height):
        super().__init__()
        self.source = str(source)
        self.clip = list(clip)
        self.width, self.height = width, height
        self.hAlign = "CENTER"

    def draw(self):
        x, y = self.canv.absolutePosition(0, 0)
        self.canv._doctemplate.figure_placements.append(dict(
            page=self.canv.getPageNumber(), source=self.source, clip=self.clip,
            x=x, y=y, width=self.width, height=self.height,
        ))


def figure_parts(source, minimum_font=6.5):
    with pymupdf.open(source) as document:
        page = document[0]
        spans = [span for block in page.get_text(
            "dict", flags=pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES
        )["blocks"] if block["type"] == 0 for line in block["lines"]
                 for span in line["spans"] if span["text"].strip()]
        rect = page.rect
        indices = [span for span in spans if "地点与要素索引" in span["text"]]
        clips = [rect]
        if indices:
            boundary = min(span["bbox"][1] for span in indices) - 8
            clips = [pymupdf.Rect(0, 0, rect.width, boundary),
                     pymupdf.Rect(0, boundary, rect.width, rect.height)]
        parts = []
        papers = [("portrait", A4), ("wide", landscape(A4)),
                  ("foldout", landscape(A3)), ("tall", A3)]
        for part, clip in enumerate(clips):
            sizes = [span["size"] for span in spans
                     if pymupdf.Rect(span["bbox"]).intersects(clip)]
            font = min(sizes, default=8)
            for orientation, paper in papers:
                scale = min((paper[0] - 76) / clip.width,
                            (paper[1] - 150) / clip.height, 1.5)
                if font * scale >= minimum_font:
                    break
            else:
                raise ValueError(f"图件字号不足 {minimum_font} pt：{source}")
            parts.append(dict(
                clip=list(clip), width=clip.width * scale,
                height=clip.height * scale, orientation=orientation,
                minimum_printed_font_pt=round(font * scale, 2),
                part="index" if part else "main",
            ))
        return parts


def compress_rasters(document, output_scale, dpi=180):
    page = document[0]
    replaced, saved = 0, 0
    for item in page.get_images(full=True):
        xref, mask, width, height = item[:4]
        original_size = len(document.xref_stream_raw(xref))
        if mask:
            original_size += len(document.xref_stream_raw(mask))
        if original_size < 60_000:
            continue
        rectangles = page.get_image_rects(xref)
        if not rectangles:
            continue
        target_width = max(round(r.width * output_scale * dpi / 72)
                           for r in rectangles)
        target_height = max(round(r.height * output_scale * dpi / 72)
                            for r in rectangles)
        pixmap = pymupdf.Pixmap(document, xref)
        if pixmap.colorspace.n != 3:
            pixmap = pymupdf.Pixmap(pymupdf.csRGB, pixmap)
        if mask:
            pixmap = pymupdf.Pixmap(pixmap, pymupdf.Pixmap(document, mask))
        bitmap = Image.frombytes("RGBA" if mask else "RGB",
                                 (pixmap.width, pixmap.height), pixmap.samples)
        bitmap.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
        stream = io.BytesIO()
        if mask:
            bitmap.save(stream, format="PNG", optimize=True)
        else:
            bitmap.save(stream, format="JPEG", quality=88, subsampling=0, optimize=True)
        encoded = stream.getvalue()
        with pymupdf.open() as probe:
            replacement = probe.new_page()
            reference = replacement.insert_image(replacement.rect, stream=encoded)
            if mask:
                probe.update_stream(reference, probe.xref_stream(reference), compress=True)
            replacement_size = len(probe.xref_stream_raw(reference))
            replacement_mask = probe.xref_get_key(reference, "SMask")[1]
            if replacement_mask.endswith(" R"):
                mask_reference = int(replacement_mask.split()[0])
                probe.update_stream(mask_reference, probe.xref_stream(mask_reference), compress=True)
                replacement_size += len(probe.xref_stream_raw(mask_reference))
        if replacement_size < original_size:
            page.replace_image(xref, stream=encoded)
            replaced += 1
            saved += original_size - replacement_size
    return replaced, saved


def share_figure_fonts(book):
    from fontTools import subset
    from fontTools.ttLib import TTFont
    import matplotlib

    font_paths = {
        "MicrosoftYaHei": Path("C:/Windows/Fonts/msyh.ttc"),
        "MicrosoftYaHei-Bold": Path("C:/Windows/Fonts/msyhbd.ttc"),
        "SimHei": Path("C:/Windows/Fonts/simhei.ttf"),
        "DejaVuSans": Path(matplotlib.get_data_path()) / "fonts/ttf/DejaVuSans.ttf",
    }
    fonts = {row[0] for page in book for row in page.get_fonts(full=True)}
    families = {}
    for reference in fonts:
        if book.xref_get_key(reference, "Subtype")[1] != "/Type0":
            continue
        if book.xref_get_key(reference, "Encoding")[1] != "/Identity-H":
            continue
        name = book.xref_get_key(reference, "BaseFont")[1].lstrip("/").split("+")[-1]
        if name not in font_paths:
            continue
        descendants = re.findall(r"(\d+) 0 R",
                                 book.xref_get_key(reference, "DescendantFonts")[1])
        if len(descendants) != 1:
            continue
        cidfont = int(descendants[0])
        descriptor = book.xref_get_key(cidfont, "FontDescriptor")[1]
        mapping = book.xref_get_key(cidfont, "CIDToGIDMap")[1]
        if not descriptor.endswith(" R") or not mapping.endswith(" R"):
            continue
        descriptor = int(descriptor.split()[0])
        mapping = int(mapping.split()[0])
        unicode_reference = book.xref_get_key(reference, "ToUnicode")[1]
        if not unicode_reference.endswith(" R"):
            continue
        unicode_map = book.xref_stream(int(unicode_reference.split()[0])).decode("ascii")
        codes = {}
        single_characters = True
        for first, last, values in re.findall(
            r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\[([^\]]*)\]",
            unicode_map,
        ):
            first, last = int(first, 16), int(last, 16)
            values = [bytes.fromhex(v).decode("utf-16-be")
                      for v in re.findall(r"<([0-9A-Fa-f]+)>", values)]
            single_characters &= len(values) == last - first + 1 and all(
                len(value) == 1 for value in values)
            if single_characters:
                codes.update({first + i: ord(value) for i, value in enumerate(values)})
        if not codes or not single_characters:
            continue
        family = families.setdefault(name, dict(codes=set(), fonts=[]))
        family["codes"].update(codes.values())
        family["fonts"].append((cidfont, descriptor, codes))
    report = []
    for name, family in families.items():
        path = font_paths[name]
        font = TTFont(path, fontNumber=0, recalcTimestamp=False)
        cmap = font.getBestCmap()
        if not family["codes"].issubset(cmap):
            font.close()
            continue
        options = subset.Options(glyph_names=True, recommended_glyphs=True)
        options.drop_tables += ["FFTM"]
        selector = subset.Subsetter(options=options)
        selector.populate(unicodes=family["codes"])
        selector.subset(font)
        stream = io.BytesIO()
        font.save(stream)
        font_bytes = stream.getvalue()
        cmap = font.getBestCmap()
        file_reference = book.get_new_xref()
        book.update_object(file_reference, f"<< /Length1 {len(font_bytes)} >>")
        book.update_stream(file_reference, font_bytes, compress=True)
        for cidfont, descriptor, codes in family["fonts"]:
            mapping = np.zeros(max(codes) + 1, dtype=">u2")
            for code, unicode_value in codes.items():
                mapping[code] = font.getGlyphID(cmap[unicode_value])
            map_reference = book.get_new_xref()
            book.update_object(map_reference, "<< >>")
            book.update_stream(map_reference, mapping.tobytes(), compress=True)
            book.xref_set_key(descriptor, "FontFile2", f"{file_reference} 0 R")
            book.xref_set_key(cidfont, "CIDToGIDMap", f"{map_reference} 0 R")
        font.close()
        report.append(dict(font=name, shared_subsets=len(family["fonts"]),
                           glyphs=len(family["codes"]), shared_font_bytes=len(font_bytes)))
    return report


def embed_figures(layout_path, final_path, placements, report_path):
    Path(report_path).with_name("figure_placements.json").write_text(
        json.dumps(placements, ensure_ascii=False, indent=2), encoding="utf-8")
    groups = {}
    for placement in placements:
        groups.setdefault(placement["source"], []).append(placement)
    report = dict(figure_files=len(groups), placements=len(placements),
                  compressed_rasters=0, raster_bytes_saved=0)
    with pymupdf.open(layout_path) as book:
        for serial, (source, entries) in enumerate(groups.items(), 1):
            with pymupdf.open(stream=Path(source).read_bytes(), filetype="pdf") as figure:
                scale = max(item["width"] / pymupdf.Rect(item["clip"]).width
                            for item in entries)
                compressed, saved = compress_rasters(figure, scale)
                report["compressed_rasters"] += compressed
                report["raster_bytes_saved"] += saved
                for item in entries:
                    page = book[item["page"] - 1]
                    y = page.rect.height - item["y"] - item["height"]
                    target = pymupdf.Rect(item["x"], y,
                                          item["x"] + item["width"],
                                          y + item["height"])
                    page.show_pdf_page(target, figure, 0, clip=item["clip"])
            if serial % 100 == 0:
                print(f"Vector figures: {serial}/{len(groups)}", flush=True)
        report["shared_fonts"] = share_figure_fonts(book)
        book.save(final_path, garbage=4, deflate=True, use_objstms=1)
        report["pages"] = len(book)
    report["pdf_bytes"] = Path(final_path).stat().st_size
    Path(report_path).write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False), flush=True)
