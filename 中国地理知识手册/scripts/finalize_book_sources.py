"""整理修订正文并核对 GDP 与夜光图表的实际观测范围。"""

import csv
import json
import re
from pathlib import Path

from book_pdf_assets import figure_numbers
from sync_volume2_captions import gdp_table

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "output" / "修订20261105" / "qa"


def main():
    with (QA / "2024地市采用值.csv").open(encoding="utf-8-sig") as stream:
        records = {r["city"]: r for r in csv.DictReader(stream)}
    cleaned = []
    for p in (ROOT / "sections_vol2").glob("*.md"):
        text = p.read_text(encoding="utf-8-sig")
        original = text
        city = p.stem.split("_", 1)[1]
        if city in records and "2024 年常住人口 **" not in text:
            values = records[city]
            facts = []
            for key, label, unit in [
                ("pop_wan", "常住人口", "万人"),
                ("urban_rate", "常住人口城镇化率", "%"),
                ("gdp_2024", "地区生产总值", "亿元"),
                ("per_gdp_yuan", "人均地区生产总值", "元"),
            ]:
                if values[key]:
                    value = float(values[key])
                    facts.append(f"{label} {value:,.2f}".rstrip("0").rstrip(".") + f" {unit}")
            if values["structure"]:
                facts.append("三次产业构成 " + values["structure"])
            paragraph = "2024 年全市统计：" + "，".join(facts) + "。"
            lines = text.splitlines()
            position = next((i for i, line in enumerate(lines) if line.startswith("![")), 2)
            lines[position:position] = [paragraph, ""]
            text = "\n".join(lines) + "\n"
        lines = text.splitlines()
        remove = []
        for i, line in enumerate(lines):
            heading = re.match(r"^(#+)\s", line)
            if not heading:
                continue
            j = i + 1
            while j < len(lines) and (not lines[j].strip() or lines[j].strip() == "---"):
                j += 1
            following = re.match(r"^(#+)\s", lines[j]) if j < len(lines) else None
            if j == len(lines) or (following and len(following[1]) <= len(heading[1])):
                remove.append(i)
        text = "\n".join(line for i, line in enumerate(lines) if i not in remove)
        text = text.replace("南三环知春路", "知春路")
        if city == "绥化市":
            text = text.replace("三江平原松嫩平原过渡带", "松嫩平原与小兴安岭过渡地带")
        text = re.sub(r"\n{3,}", "\n\n", text).rstrip() + "\n"
        if text != original:
            p.write_text(text, encoding="utf-8")
            cleaned.append(p.name)

    conflicts = []
    comparisons = 0
    scope_conflicts = []
    used_assets = {}
    figures = ROOT / "output" / "下册修订" / "figures"
    for source in (ROOT / "sections_vol2").glob("*.md"):
        text = source.read_text(encoding="utf-8")
        observations = gdp_table(text)
        for name in re.findall(r"!\[[^\]]*\]\(\.\./figures/([^)]+)\)", text):
            used_assets[name] = source.name
            data_path = figures.parent / "qa" / (Path(name).stem + ".data.json")
            if not data_path.exists():
                continue
            data = json.loads(data_path.read_text(encoding="utf-8"))
            for panel in data["panels"]:
                if re.search(r"夜光|夜间灯光|辐射", panel["title"]) and panel["lines"]:
                    xs = [x for line in panel["lines"] for x in line["x"]]
                    if "2024" in panel["title"] and max(xs) < 2024:
                        scope_conflicts.append(dict(source=source.name, figure=name))
                if not re.search(r"GDP|生产总值", panel["title"]):
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
                        if year not in observations:
                            continue
                        comparisons += 1
                        expected, decimals = observations[year]
                        if abs(expected - value) > 0.5 * 10 ** -decimals + 1e-6:
                            conflicts.append(dict(source=source.name, figure=name,
                                                   year=year, table=expected, chart=value))
        city = source.stem.split("_", 1)[1]
        if city in records and 2024 in observations and records[city]["gdp_2024"]:
            comparisons += 1
            expected = float(records[city]["gdp_2024"])
            if abs(observations[2024][0] - expected) > 0.51:
                conflicts.append(dict(source=source.name, year=2024,
                                       table=observations[2024][0], yearbook=expected))
    missing = [name for name in used_assets
               if not (figures / name).is_file()
               or not (figures / name).with_suffix(".pdf").is_file()]
    report = dict(cleaned_sections=cleaned, gdp_comparisons=comparisons,
                  gdp_conflicts=conflicts, nightlight_scope_conflicts=scope_conflicts,
                  lower_figure_references=len(used_assets), missing_assets=missing)
    (QA / "source_validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "cleaned_sections"},
                     ensure_ascii=False, indent=2))
    if conflicts or scope_conflicts or missing:
        raise ValueError("正文与图表或采用值存在冲突")


if __name__ == "__main__":
    main()
