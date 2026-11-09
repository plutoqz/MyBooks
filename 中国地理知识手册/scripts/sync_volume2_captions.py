"""同步下册图题、图注与绘图数据的文字口径。"""
import json
import re
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "下册修订"
QA = OUT / "qa"


def gdp_table(text):
    active = False
    observations = {}
    for line in text.splitlines():
        if not line.startswith("|"):
            active = False
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if "年份" in cells[0]:
            active = any("GDP" in cell or "地区生产总值" in cell for cell in cells[1:])
            continue
        if not active or len(cells) < 2:
            continue
        year = re.search(r"(?:19|20)\d{2}", cells[0])
        value = re.fullmatch(r"[\s*约超]*([\d,\s]+(?:\.\d+)?)[\s*]*", cells[1])
        if year and value:
            number = value[1].replace(",", "").replace(" ", "")
            decimals = len(number.split(".")[1]) if "." in number else 0
            observations[int(year[0])] = (float(number), decimals)
    return observations


def main():
    manifest = json.loads((QA / "inventory.json").read_text(encoding="utf-8"))
    figures = {}
    for item in manifest["figures"]:
        path = OUT / "figures" / Path(item["name"]).with_suffix(".pdf")
        with pymupdf.open(path) as document:
            blocks = document[0].get_text(
                "dict", flags=pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES)["blocks"]
            lines = []
            for block in blocks:
                if block["type"] != 0:
                    continue
                for line in block["lines"]:
                    spans = [span["text"] for span in line["spans"]
                             if span["size"] >= 13.8 and span["bbox"][1] < 65]
                    if spans:
                        lines.append("".join(spans))
            title = "".join(lines).strip()
        if not title:
            raise ValueError(f"图题未识别：{path.name}")
        number = re.match(r"fig([\d-]+)_", item["name"])[1]
        data_path = QA / f"{path.stem}.data.json"
        data = json.loads(data_path.read_text(encoding="utf-8")) if data_path.exists() else None
        figures[item["name"]] = dict(number=number, title=title, data=data)
    differences, revised, compared_sections = [], [], set()
    comparisons = 0
    for source in sorted((ROOT / "sections_vol2").glob("*.md")):
        text = source.read_text(encoding="utf-8")
        observations = gdp_table(text)
        used = [figures[name] for name in re.findall(r"!\[[^\]]*\]\(\.\./figures/([^)]+)\)", text)]
        for figure in used:
            number, title, data = figure["number"], figure["title"], figure["data"]
            title = title.replace("\n", " ")
            text = re.sub(
                r"!\[[^\]]*\]\((\.\./figures/fig" + re.escape(number) + r"_[^)]+)\)",
                lambda match: f"![{title}]({match[1]})", text)
            description = "图上编号与地点、要素索引对应。"
            if data:
                description = "各面板按标注的观测年份、指标和单位列示。"
                if any("GDP" in panel["title"] or "生产总值" in panel["title"]
                       for panel in data["panels"]):
                    for panel in data["panels"]:
                        if "GDP" not in panel["title"] and "生产总值" not in panel["title"]:
                            continue
                        for bar in panel["bars"]:
                            for i, (position, value) in enumerate(bar["points"]):
                                if value is None:
                                    continue
                                if 1900 <= position <= 2100:
                                    year = round(position)
                                elif len(bar["ticks"]) == len(bar["points"]):
                                    match = re.fullmatch(r"(?:19|20)\d{2}", bar["ticks"][i])
                                    if not match:
                                        continue
                                    year = int(match[0])
                                else:
                                    continue
                                if year in observations:
                                    comparisons += 1
                                    compared_sections.add(source.name)
                                    body_value, decimals = observations[year]
                                    if abs(body_value - value) > 0.5 * 10 ** -decimals + 1e-6:
                                        differences.append(dict(
                                            section=source.name, figure=number, year=year,
                                            table_value=body_value, figure_value=value))
            pattern = r"(?m)^\*\*图\s*" + re.escape(number) + r"\b[^\n]*"
            text = re.sub(pattern, f"**图 {number} {title}**：{description}", text)
        source.write_text(text, encoding="utf-8")
        revised.append(source.name)
    (QA / "gdp_consistency.json").write_text(
        json.dumps(dict(compared_observations=comparisons,
                        compared_sections=len(compared_sections), conflicts=differences),
                   ensure_ascii=False, indent=2), encoding="utf-8")
    print("Caption sections:", len(revised), "GDP observations:", comparisons,
          "GDP differences:", len(differences))
    if differences:
        print(json.dumps(differences, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
