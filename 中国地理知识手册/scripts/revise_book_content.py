"""按本地年鉴原表口径统一地市统计及夜光叙述。"""

import argparse
import ast
import csv
import io
import json
import re
import zipfile
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "output" / "修订20261105" / "qa"
SERIES_QA = ROOT / "output" / "下册修订" / "qa"
SOURCE = "《中国城市统计年鉴 2025》表 2-1、2-6、2-7（2024 年，全市）"


def number(value, decimals=2):
    if not isinstance(value, (int, float)):
        return "—"
    return f"{value:,.{decimals}f}".rstrip("0").rstrip(".") if decimals else f"{value:,.0f}"


def data_sources():
    folder = ROOT / "中国省市数据"
    archive = next((folder / "005.【出版年份】2025").glob("*excel*zip"))
    with zipfile.ZipFile(archive) as package:
        name = next(n for n in package.namelist() if "地级市" in n)
        workbook = openpyxl.load_workbook(io.BytesIO(package.read(name)),
                                          read_only=True, data_only=True)
        records = {}
        for row_number, row in enumerate(workbook.active.iter_rows(values_only=True), 1):
            if row_number < 7 or not row[0]:
                continue
            city = str(row[0]).strip()
            if not city.endswith("市") or not any(isinstance(row[i], (int, float))
                                                  for i in (2, 17)):
                continue
            if city in records:
                raise ValueError(f"年鉴城市名称重复：{city}")
            composition = [row[i] for i in (23, 25, 27)]
            structure = (" : ".join(number(v) for v in composition)
                         if all(isinstance(v, (int, float)) for v in composition) else None)
            records[city] = dict(
                pop_wan=row[2], urban_rate=row[4], gdp_2024=row[17],
                per_gdp_yuan=row[19], structure=structure, yearbook_row=row_number,
            )
        workbook.close()
    panel = openpyxl.load_workbook(
        folder / "中国城市数据面板数据（2000-2024年）.xlsx",
        read_only=True, data_only=True,
    )
    histories = {}
    for row in panel["原始数据"].iter_rows(min_row=2, values_only=True):
        year, city = row[0], row[2]
        if city not in records:
            continue
        if isinstance(row[6], (int, float)) and row[6] > 0:
            histories.setdefault(city, {})[int(year)] = round(row[6] / 10000, 1)
        if year == 2024:
            records[city]["adcode"] = int(row[4])
    panel.close()
    for city, values in records.items():
        if isinstance(values["gdp_2024"], (int, float)):
            histories.setdefault(city, {})[2024] = values["gdp_2024"]
    return records, histories


def source_note():
    return (f"2024 年统计来源：{SOURCE}。其他年份 GDP 据本地城市面板"
            "“原始数据”表，单位为亿元、当年价格。\n")


def fact_paragraph(city, values, intro):
    prefix = re.split(r"全境|全域|总面积|截至\s*2024|2024\s*年", intro, 1)[0].strip()
    if len(prefix) > 260 or not prefix:
        prefix = city + "。"
    prefix = prefix.rstrip("，；。") + "。"
    fields = []
    if isinstance(values["pop_wan"], (int, float)):
        fields.append(f"2024 年常住人口 **{number(values['pop_wan'])} 万人**")
    if isinstance(values["urban_rate"], (int, float)):
        fields.append(f"常住人口城镇化率 **{number(values['urban_rate'])}%**")
    if isinstance(values["gdp_2024"], (int, float)):
        fields.append(f"地区生产总值 **{number(values['gdp_2024'], 0)} 亿元**（当年价格）")
    if isinstance(values["per_gdp_yuan"], (int, float)):
        fields.append(f"人均地区生产总值 **{number(values['per_gdp_yuan'], 0)} 元**")
    if values["structure"]:
        fields.append(f"三次产业构成为 **{values['structure']}**")
    return prefix + "，".join(fields) + "。"


def update_gdp_tables(text, history):
    lines = text.splitlines()
    i, changed = 0, False
    while i < len(lines):
        if not lines[i].startswith("|"):
            i += 1
            continue
        end = i
        while end < len(lines) and lines[end].startswith("|"):
            end += 1
        block = lines[i:end]
        header = block[0]
        if not ("年份" in header and ("GDP" in header or "生产总值" in header)):
            i = end
            continue
        years = [int(m[0]) for line in block[2:]
                 if (m := re.search(r"(?:19|20)\d{2}", line.split("|")[1]))]
        if years:
            table = ["| 年份 | 地区生产总值（亿元，当年价格） |", "|:---|---:|"]
            table += [f"| {year} 年 | {number(history.get(year), 1)} |" for year in years]
            lines[i:end] = table
            i += len(table)
            changed = True
        else:
            i = end
    return "\n".join(lines) + "\n", changed


def economic_prose(text, records, own_city):
    lines = text.splitlines()
    first_prose = next((i for i, line in enumerate(lines[1:], 1)
                        if line.strip() and not line.startswith(("#", "![", "|", "---"))), -1)
    for i, line in enumerate(lines):
        if i == first_prose or line.startswith(("#", "|", "![", "**图")):
            continue
        if "2024" not in line or not re.search(r"GDP|地区生产总值", line):
            continue
        cities = ([own_city] if own_city else
                  [c for c in records if c in line and isinstance(records[c]["gdp_2024"], (int, float))])
        if not cities or (not own_city and not line.startswith("-")):
            continue
        prefix = "- " if line.startswith("-") else ""
        lines[i] = prefix + "2024 年" + "，".join(
            f"{city}全市地区生产总值为 {number(records[city]['gdp_2024'], 0)} 亿元"
            for city in cities if records[city]["gdp_2024"] is not None) + "（当年价格）。"
    return "\n".join(lines) + "\n"


def table_metric(label):
    label = re.sub(r"\*|`|\s", "", label)
    if "人均" in label and ("GDP" in label.upper() or "生产总值" in label):
        return "per_gdp_yuan"
    if "GDP" in label.upper() or "地区生产总值" in label:
        if not any(s in label for s in ("增长", "占比", "份额", "增速")):
            return "gdp_2024"
    if "城镇化率" in label:
        return "urban_rate"
    if "常住人口" in label or label.startswith("人口(") or label.startswith("人口（"):
        return "pop_wan"
    if any(s in label for s in ("三产结构", "三次产业", "产业结构比")):
        return "structure"
    return None


def metric_cell(key, values):
    value = values[key]
    if key == "structure":
        return value or "—"
    return number(value, 0 if key in {"gdp_2024", "per_gdp_yuan"} else 2)


def update_stat_tables(text, records, own_city):
    lines = text.splitlines()
    headers = None
    edited_rows = 0
    for i, line in enumerate(lines):
        if not line.startswith("|"):
            headers = None
            continue
        cells = [s.strip() for s in line.strip().strip("|").split("|")]
        if headers is None:
            headers = cells
            continue
        if all(re.fullmatch(r"[:\s-]+", s) for s in cells):
            continue
        city_cell = re.sub(r"\*|`", "", cells[0])
        city = next((c for c in records if city_cell == c
                     or re.fullmatch(r"[\d.\-\s]+" + re.escape(c), city_cell)), None)
        changed = False
        if city and len(headers) == len(cells):
            for column, heading in enumerate(headers):
                key = table_metric(heading)
                if key:
                    cells[column] = metric_cell(key, records[city])
                    changed = True
        elif own_city and len(cells) >= 2 and (key := table_metric(cells[0])):
            # 行式指标矩阵的第三列解释与更新后的统计口径保持一致。
            suffix = {"pop_wan": " 万人", "urban_rate": "%", "gdp_2024": " 亿元",
                      "per_gdp_yuan": " 元/人", "structure": ""}[key]
            cells[1] = metric_cell(key, records[own_city]) + suffix
            if len(cells) >= 3:
                cells[2] = "2024 年，全市；年鉴公布口径"
            changed = True
        if changed:
            lines[i] = "| " + " | ".join(cells) + " |"
            edited_rows += 1
    return "\n".join(lines) + "\n", edited_rows


def revise_nightlight(text, years):
    if not years:
        return text, 0
    start, end = min(years), max(years)
    lines = text.splitlines()
    output, removed = [], 0
    context, level, omit_events, note_added = False, 0, False, False
    for line in lines:
        heading = re.match(r"^(#{2,6})\s*(.*)", line)
        if heading:
            current_level, title = len(heading[1]), heading[2]
            if context and current_level <= level:
                context, omit_events, note_added = False, False, False
            if re.search(r"夜光|夜间灯光|灯光演|时序演进", title):
                context, level, omit_events = True, current_level, False
                title = re.sub(r"1986\s*[—–至-]\s*2024", f"{start}—{end}", title)
                title = title.replace("跃迁", "变化").replace("跃升", "变化")
                output.append(heading[1] + " " + title)
                if not note_added:
                    output.extend(["", f"本节夜光图的观测年份为 {start}—{end} 年，"
                                   "指标为行政区汇总值（原表 sum）。", ""])
                    note_added = True
                continue
            if context and re.search(r"突变|跃升节点|空间集聚|重构动力|辐射演进", title):
                omit_events = True
                removed += 1
                continue
            if context:
                omit_events = False
        if not context:
            output.append(line)
            continue
        if line.startswith(("![", "**图", "|", "#")):
            output.append(line)
            continue
        if omit_events and line.strip():
            removed += 1
            continue
        if line.startswith("**") and re.search(r"突变|跃升|演进特征", line):
            omit_events = True
            removed += 1
            continue
        if re.search(r"夜光|灯光", line) and re.search(r"跃升节点|突变节点|三个.*节点", line):
            omit_events = True
            removed += 1
            continue
        if re.search(r"夜光|灯光|辐射|发光|指数级|几何跃升", line):
            if "来源" not in line and "数据源" not in line:
                removed += 1
                continue
        output.append(line)
    result = re.sub(r"\n{3,}", "\n\n", "\n".join(output))
    return result.rstrip() + "\n", removed


def unsupported_regional_stats(text, path):
    if path.name[:2] not in {"26", "27", "28"} or path.name[3:5] == "00":
        return text, []
    removed_figures = []
    text = re.sub(
        r"(?ms)^##\s+[^\n]*(?:城市空间演化|夜间灯光|经济跃迁)[^\n]*\n.*?(?=^##\s|\Z)",
        "", text,
    )
    lines = text.splitlines()
    output = []
    in_gdp_table = False
    drop_events = False
    for line in lines:
        if line.startswith("#"):
            if re.search(r"夜间灯光|GDP|经济跃迁", line):
                drop_events = True
                continue
            drop_events = False
        if line.startswith("![") and re.search(r"夜间灯光|夜光演变", line):
            removed_figures.extend(re.findall(r"/([^/)]+\.png)", line))
            continue
        if line.startswith("|"):
            if re.search(r"地区生产总值|GDP|三产结构|人均.*GDP", line):
                in_gdp_table = "年份" in line or "基准" in line
                if in_gdp_table:
                    continue
                cells = line.split("|")
                # 省级横向矩阵在后续整表中去除无来源的分区经济列。
                if len(cells) <= 5:
                    continue
            if in_gdp_table:
                continue
            output.append(line)
            continue
        in_gdp_table = False
        if drop_events:
            continue
        if re.search(r"GDP|地区生产总值|三次产业结构比", line):
            continue
        if not line.startswith("|") and re.search(r"常住人口|城镇化率", line):
            line = re.split(r"截至\s*2024|2024\s*年", line, 1)[0].rstrip()
            if not line:
                continue
        if re.search(r"夜光|夜间灯光", line) and not line.startswith("!["):
            continue
        output.append(line)
    text = "\n".join(output) + "\n"
    # 分区汇总矩阵按表头删列，保留地名、面积与地理要素。
    blocks = re.split(r"(\n(?:\|[^\n]*\n)+)", text)
    for i, block in enumerate(blocks):
        rows = [s for s in block.splitlines() if s.startswith("|")]
        if not rows:
            continue
        header = [s.strip() for s in rows[0].strip("|").split("|")]
        drop = [j for j, s in enumerate(header)
                if re.search(r"GDP|生产总值|产业结构|三产结构|人口|城镇化", s)]
        if not drop:
            continue
        revised = []
        for row in rows:
            cells = row.strip("|").split("|")
            revised.append("|" + "|".join(s for j, s in enumerate(cells)
                                          if j not in drop) + "|")
        blocks[i] = "\n" + "\n".join(revised) + "\n"
    text = "".join(blocks)
    note = ("本节按地理功能划分分析板块，板块不作为独立的地区生产总值统计单元。")
    lines = text.splitlines()
    lines[1:1] = ["", note]
    return "\n".join(lines).rstrip() + "\n", removed_figures


def configuration_updates(records, histories, apply):
    files, changed_values = [], 0
    for path in (ROOT / "scripts").glob("*configs.py"):
        raw = path.read_bytes()
        tree = ast.parse(raw, filename=str(path))
        lines = raw.splitlines(keepends=True)
        offsets = [0]
        for line in lines:
            offsets.append(offsets[-1] + len(line))
        edits = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            entries = {key.value: value for key, value in zip(node.keys, node.values)
                       if isinstance(key, ast.Constant) and isinstance(key.value, str)}
            name_node = entries.get("name")
            if not isinstance(name_node, ast.Constant) or name_node.value not in records:
                continue
            city = name_node.value
            for key in ("pop_wan", "urban_rate", "gdp_2024", "per_gdp_yuan",
                        "structure", "gdp_series"):
                target = entries.get(key)
                if target is None:
                    continue
                if key == "gdp_series" and isinstance(target, ast.Dict):
                    old = ast.literal_eval(target)
                    value = {year: histories[city].get(year, old[year]) for year in old}
                else:
                    value = records[city].get(key)
                    if value is None:
                        continue
                if ast.literal_eval(target) == value:
                    continue
                begin = offsets[target.lineno - 1] + target.col_offset
                end = offsets[target.end_lineno - 1] + target.end_col_offset
                edits.append((begin, end, repr(value).encode("utf-8")))
        if edits:
            for begin, end, value in sorted(edits, reverse=True):
                raw = raw[:begin] + value + raw[end:]
            if apply:
                path.write_bytes(raw)
            files.append(path.name)
            changed_values += len(edits)
    return dict(files=files, fields=changed_values)


def chart_updates(records, histories, city_sections, apply):
    changed = []
    years_by_section = {}
    for path in sorted(SERIES_QA.glob("*.data.json")):
        original = path.read_text(encoding="utf-8")
        data = json.loads(original)
        code = re.match(r"fig(\d\d-\d\d)-", path.name)[1]
        city = city_sections.get(code)
        nightlight_years = []
        for panel in data["panels"]:
            if panel["lines"] and re.search(r"夜光|灯光|辐射", panel["title"] + panel["ylabel"]):
                xs = [int(x) for line in panel["lines"] for x in line["x"]]
                if xs:
                    low, high = min(xs), max(xs)
                    nightlight_years.extend(xs)
                    panel["title"] = re.sub(r"1986\s*[—–-]\s*2024",
                                             f"{low}—{high}", panel["title"])
                    panel["title"] = panel["title"].replace("跃迁", "变化")
                    panel["xlabel"] = "年份"
                    panel["ylabel"] = "汇编夜光指标总量（原表 sum）"
                    for line in panel["lines"]:
                        if re.search(r"DN|nW|辐射", line.get("label", "")):
                            line["label"] = "夜光汇总指标"
            if city and re.search(r"GDP|生产总值", panel["title"] + panel["ylabel"]):
                history = histories.get(city, {})
                for bar in panel["bars"]:
                    for index, point in enumerate(bar["points"]):
                        year = (int(round(point[0])) if 1900 <= point[0] <= 2100 else
                                int(re.search(r"(?:19|20)\d{2}", bar["ticks"][index])[0])
                                if len(bar["ticks"]) == len(bar["points"]) and
                                re.search(r"(?:19|20)\d{2}", bar["ticks"][index]) else None)
                        if year in history:
                            point[1] = history[year]
                    if all(1900 <= point[0] <= 2100 for point in bar["points"]):
                        bar["ticks"] = [str(round(point[0])) for point in bar["points"]]
                for line in panel["lines"]:
                    line["y"] = [history.get(int(round(x)), y)
                                 for x, y in zip(line["x"], line["y"])]
                panel["ylabel"] = "GDP（亿元，当年价格）"
            elif re.search(r"GDP|生产总值", panel["title"] + panel["ylabel"]):
                for bar in panel["bars"]:
                    if len(bar["ticks"]) != len(bar["points"]):
                        continue
                    for index, label in enumerate(bar["ticks"]):
                        names = [c for c in records if c in label or label.strip() == c[:-1]]
                        if len(names) == 1 and records[names[0]]["gdp_2024"] is not None:
                            bar["points"][index][1] = records[names[0]]["gdp_2024"]
        if nightlight_years:
            years_by_section[code] = sorted(set(nightlight_years))
            data["events"] = []
            data["qualitative_notes"] = []
            footers = [f for f in data.get("footers", [])
                       if not re.search(r"遥感|夜光|夜间灯光|DMSP|VIIRS|光学", f)]
            footers.append("夜光：本地分区统计汇编；观测范围以面板年份为准。")
            if city:
                footers.append("GDP：本地城市面板原始数据表；2024 年据《中国城市统计年鉴 2025》表 2-6。")
            data["footers"] = list(dict.fromkeys(footers))
        revised = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        if json.loads(original) != data:
            changed.append(path.name)
            if apply:
                path.write_text(revised, encoding="utf-8")
    return changed, years_by_section


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    QA.mkdir(parents=True, exist_ok=True)
    records, histories = data_sources()
    sections = sorted((ROOT / "sections_vol2").glob("*.md"))
    city_sections = {p.stem.split("_", 1)[0]: p.stem.split("_", 1)[1]
                     for p in sections if p.stem.split("_", 1)[1] in records}
    charts, years_by_section = chart_updates(records, histories, city_sections, args.apply)
    results, removed_figures = [], []
    for path in sections:
        text = original = path.read_text(encoding="utf-8-sig")
        code, title = path.stem.split("_", 1)
        city = title if title in records else None
        text = economic_prose(text, records, city)
        if city:
            lines = text.splitlines()
            for i, line in enumerate(lines[1:], 1):
                if line.strip() and not line.startswith(("#", "![", "|", "---")):
                    if re.search(r"人口|GDP|生产总值", line):
                        lines[i] = fact_paragraph(city, records[city], line)
                    break
            text = "\n".join(lines) + "\n"
            text, _ = update_gdp_tables(text, histories.get(city, {}))
            text = re.sub(r"(?m)^统计来源：《中国城市统计年鉴 2025》[^\n]*\n?", "", text)
        text, table_rows = update_stat_tables(text, records, city)
        text, nightlight = revise_nightlight(text, years_by_section.get(code, []))
        text, excluded = unsupported_regional_stats(text, path)
        removed_figures.extend(excluded)
        text = text.replace("冷水冷水", "冷水").replace("世纪世纪", "世纪")
        if city:
            text = text.rstrip() + "\n\n" + source_note()
        elif table_rows:
            text = text.rstrip() + f"\n\n地市统计来源：{SOURCE}。\n"
        if args.apply and text != original:
            path.write_text(text, encoding="utf-8")
        results.append(dict(section=path.name, city=city, changed=text != original,
                            updated_table_rows=table_rows, removed_nightlight_lines=nightlight))
    config = configuration_updates(records, histories, args.apply)
    report = dict(yearbook_cities=len(records), city_sections=len(city_sections),
                  changed_sections=sum(r["changed"] for r in results),
                  changed_chart_data=len(charts), chart_data=charts,
                  removed_unsupported_figures=removed_figures,
                  configurations=config, sections=results,
                  statistics_source=SOURCE,
                  history_source="中国城市数据面板数据（2000-2024年）/原始数据",
                  source_verification="按本地汇编表统一；未将汇编表视为独立地方公报复核。")
    if args.apply:
        (QA / "content_revision.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        with (QA / "2024地市采用值.csv").open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["city", *next(iter(records.values()))])
            writer.writeheader()
            for city, values in records.items():
                writer.writerow(dict(city=city, **values))
    print(json.dumps({k: v for k, v in report.items()
                      if k not in {"sections", "chart_data"}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
