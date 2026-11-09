"""Compare labelled 2024 city GDP in the book with the local yearbook extract."""

import csv
import io
import re
import zipfile
from pathlib import Path

import openpyxl


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = (
    ROOT
    / "中国省市数据"
    / "005.【出版年份】2025"
    / "中国城市统计年鉴2025（excel）【截面数据】.zip"
)
PATTERNS = [
    re.compile(
        r"2024\s*年[^。\n]{0,45}?(?:GDP|地区生产总值)[^。\n]{0,30}?"
        r"(?:约|达|为|突破)?\s*\*\*([\d,]+(?:\.\d+)?)\*\*\s*亿元"
    ),
    re.compile(
        r"2024\s*年[^。\n]{0,35}?地区生产总值[^。\n]{0,40}?"
        r"\*\*([\d,]+(?:\.\d+)?)\*\*\s*亿元"
    ),
]


def main():
    with zipfile.ZipFile(ARCHIVE) as archive:
        name = next(name for name in archive.namelist() if "地级市" in name)
        workbook = openpyxl.load_workbook(
            io.BytesIO(archive.read(name)), read_only=True, data_only=True
        )
        rows = list(workbook.active.iter_rows(values_only=True))
    yearbook = {
        str(row[0]).strip(): (index, row[17])
        for index, row in enumerate(rows[6:], 7)
        if row[0] and isinstance(row[17], (int, float))
    }
    records = []
    for path in sorted((ROOT / "sections_vol2").glob("*.md")):
        city = path.stem.split("_", 1)[-1]
        if city not in yearbook:
            continue
        text = path.read_text(encoding="utf-8-sig")
        match = next((m for pattern in PATTERNS if (m := pattern.search(text))), None)
        if not match:
            continue
        book = float(match.group(1).replace(",", ""))
        row, reference = yearbook[city]
        delta = (book / reference - 1) * 100
        records.append(
            {
                "城市": city,
                "正文文件": path.name,
                "正文行号": text[: match.start()].count("\n") + 1,
                "正文2024GDP_亿元": book,
                "年鉴2024GDP_亿元": reference,
                "年鉴表行号": row,
                "差异百分比": round(delta, 2),
                "超过3%且超过5亿元": "是"
                if abs(book - reference) > max(5, reference * 0.03)
                else "否",
            }
        )
    target = Path(__file__).with_name("2024地市GDP可匹配差异.csv")
    with target.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(sorted(records, key=lambda row: abs(row["差异百分比"]), reverse=True))
    print(f"matched={len(records)} flagged={sum(r['超过3%且超过5亿元'] == '是' for r in records)}")


if __name__ == "__main__":
    main()
