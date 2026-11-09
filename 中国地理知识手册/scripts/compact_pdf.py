"""对已生成合订 PDF 的栅格流做二次压缩。"""

import argparse
import io
import json
from pathlib import Path

import pymupdf
from PIL import Image


def compact(source, target, dpi=120, quality=78):
    source = Path(source)
    target = Path(target)
    document = pymupdf.open(source)
    seen = set()
    report = dict(source_bytes=source.stat().st_size, images=0,
                  replaced=0, original_bytes=0, replacement_bytes=0)
    for page in document:
        for item in page.get_images(full=True):
            xref, mask = item[0], item[1]
            if xref in seen:
                continue
            seen.add(xref)
            original = len(document.xref_stream_raw(xref) or b"")
            if mask:
                original += len(document.xref_stream_raw(mask) or b"")
            report["images"] += 1
            if original < 60_000:
                continue
            rectangles = page.get_image_rects(xref)
            if not rectangles:
                continue
            width = max(rect.width for rect in rectangles)
            height = max(rect.height for rect in rectangles)
            target_size = (max(32, round(width * dpi / 72)),
                           max(32, round(height * dpi / 72)))
            try:
                pixmap = pymupdf.Pixmap(document, xref)
                if pixmap.colorspace is None or pixmap.colorspace.n != 3:
                    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pixmap)
                if mask:
                    alpha = pymupdf.Pixmap(document, mask)
                    pixmap = pymupdf.Pixmap(pixmap, alpha)
                bitmap = Image.frombytes(
                    "RGBA" if pixmap.alpha else "RGB",
                    (pixmap.width, pixmap.height), pixmap.samples)
                bitmap.thumbnail(target_size, Image.Resampling.LANCZOS)
                stream = io.BytesIO()
                if pixmap.alpha:
                    bitmap.save(stream, format="PNG", optimize=True)
                else:
                    bitmap.save(stream, format="JPEG", quality=quality,
                               subsampling=0, optimize=True)
                encoded = stream.getvalue()
                if len(encoded) >= original:
                    continue
                page.replace_image(xref, stream=encoded)
                report["replaced"] += 1
                report["original_bytes"] += original
                report["replacement_bytes"] += len(encoded)
            except Exception as error:
                report.setdefault("skipped", []).append(
                    dict(xref=xref, error=str(error)))
    document.save(target, garbage=4, deflate=True, use_objstms=1)
    report["target_bytes"] = target.stat().st_size
    report["byte_reduction"] = report["source_bytes"] - report["target_bytes"]
    target.with_suffix(".compression.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--dpi", type=int, default=120)
    parser.add_argument("--quality", type=int, default=78)
    args = parser.parse_args()
    compact(args.source, args.target, args.dpi, args.quality)


if __name__ == "__main__":
    main()
