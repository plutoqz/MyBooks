"""下册单位、坐标和示意表的正文排版。"""
import json
import re
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "下册修订"
SUPERSCRIPT = str.maketrans("0123456789+-=()in", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁱⁿ")
SYMBOLS = {"circ": "°", "times": "×", "sim": "～", "pm": "±",
           "rightarrow": "→", "ge": "≥", "cdot": "·", "Omega": "Ω", "mu": "μ"}


def plain_math(text):
    text = text.replace("\text{", r"\text{").replace("\times", r"\times")
    text = re.sub(r"\\text\s*\{\{([^{}]*)\}\}", r"\1", text)
    text = re.sub(r"\\text\s*\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\^\s*\\circ", "°", text)
    for name, symbol in SYMBOLS.items():
        text = re.sub(r"\\" + name + r"(?![a-zA-Z])", lambda _: symbol, text)
    text = text.replace(r"\mum", "μm").replace("\\ ", " ")
    text = text.replace(r"\cdotd", "·d")
    text = text.replace(r"\%", "%")
    text = re.sub(r"\^\{([0-9+\-=()in]+)\}",
                  lambda m: m[1].translate(SUPERSCRIPT), text)
    text = re.sub(r"\^([0-9])", lambda m: m[1].translate(SUPERSCRIPT), text)
    text = text.replace("$", "")
    return text


def diagram_table(match):
    block = match[0]
    lines = block.splitlines()[1:-1]
    rows, notes = [], []
    separate_boxes = len(re.findall(r"┌[─]+┐", block)) > 1
    for line in lines:
        line = re.sub(r"^\s*>\s?", "", line).strip()
        if "│" in line:
            parts = line.split("│")
            cells = ([parts[i].strip() for i in range(1, len(parts), 2)]
                     if separate_boxes else [v.strip() for v in parts[1:-1]])
            if separate_boxes:
                transitions = [re.sub(r"[─>←→\s]+", "", value)
                               for value in parts[2:-1:2]]
                transitions = [value for value in transitions if re.search(r"[\u4e00-\u9fff]", value)]
                if transitions:
                    notes.append("过渡关系：" + "；".join(transitions))
            cells = [re.sub(r"^[─>←→\s]+|[─>←→\s]+$", "", v) for v in cells]
            cells = [v for v in cells if v]
            if cells:
                rows.append(cells)
        elif re.search(r"[\u4e00-\u9fff]", line):
            line = re.sub(r"[─━┌┐└┘├┤┬┴┼]+", " ", line)
            line = re.sub(r"\s{2,}", " · ", line).strip().replace(">", "→")
            if line:
                notes.append(line)
    if not rows:
        title, *entries = notes
        entries = [re.sub(r"^[└├─\s]+", "", entry) for entry in entries]
        return "\n**" + title + "**\n\n" + "\n".join(
            "- " + entry for entry in entries) + "\n"
    columns = max(map(len, rows))
    rows = [row + [""] * (columns - len(row)) for row in rows]
    heading = notes[0].strip("【】").replace("示意图", "示意表") if notes else "地理格局"
    table = [f"\n**{heading}**\n"]
    if len(rows[0]) == columns and all(rows[0]):
        header = rows.pop(0)
    else:
        header = [f"区域 {i + 1}" for i in range(columns)]
    if separate_boxes and rows:
        rows = [["；".join(row[column] for row in rows if row[column])
                 for column in range(columns)]]
    table += ["| " + " | ".join(header) + " |",
              "| " + " | ".join(["---"] * columns) + " |"]
    table += ["| " + " | ".join(row) + " |" for row in rows]
    if len(notes) > 1:
        table += ["", "；".join(notes[1:])]
    return "\n".join(table) + "\n"


def repair_text(text):
    diagrams = len(re.findall(r"(?m)^\s*>?\s*```", text)) // 2
    text = re.sub(r"(?m)^\s*>?\s*```[^\n]*\n.*?^\s*>?\s*```\s*$",
                  diagram_table, text, flags=re.S | re.M)
    text = plain_math(text)
    text = text.replace(r"\n", "\n")
    text = re.sub(r"(?m)^((?!(?:[-*+] |\d+\. ))\S[^\n]*)\n(?=(?:[-*+] |\d+\. ))",
                  r"\1\n\n", text)
    return text.lstrip("\r\n"), diagrams


def nightlight_text(text, chapter):
    if chapter in {"26", "27", "28"}:
        return text, []
    removed = []
    lines = []
    for line in text.splitlines():
        if line.startswith("!["):
            lines.append(line)
            continue
        if re.search(r"nW/cm|夜光积分值.*\bDN\b", line):
            removed.append(line)
            if "空间特征表现为：" in line:
                year = re.search(r"(19|20)\d{2}", line)
                detail = line.split("空间特征表现为：", 1)[1]
                line = f"- **{year[0]} 年空间发展说明**：{detail}" if year else detail
            elif line.startswith("- "):
                continue
        if line.startswith("- ") and "空间总辐射量约" in line:
            removed.append(line)
            line = re.sub(r"（空间总辐射量约 [\d,.\s]+DN）", "", line)
        if "夜光" in line or "夜间灯光" in line:
            if not line.startswith("**图"):
                line = re.sub(r"1986\s*[—–-]\s*2024", "1986—2013", line)
            line = line.replace("卫星遥感夜间灯光时序数据", "本地汇编夜光指标序列")
            line = line.replace("能够真实、连续地刻画出", "用于观察")
            line = line.replace("总辐射强度", "指标总量")
            line = line.replace("夜间灯光总辐射", "夜光指标总量")
            line = line.replace("夜光总辐射", "夜光指标总量")
            line = line.replace("长达 38 年的长时序卫星校准夜间灯光遥感数据（DMSP-OLS 与 NPP-VIIRS）",
                                "本地汇编的 1986—2013 年夜光指标")
            line = line.replace("NOAA/DMSP-OLS & VIIRS-DNB 1986—2013 年长时序夜间灯光遥感校验数据集",
                                "本地夜光指标汇编表（1986—2013 年）")
        lines.append(line)
    return "\n".join(lines) + "\n", removed


def tianjin_nightlight(text):
    import pandas as pd
    source = pd.read_csv(ROOT / "data" / "tianjin_nightlight_clean.csv")
    yearly = source.groupby("year")[["sum", "count"]].sum()
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if "全市灯光总和 (DN Sum)" in line:
            lines[i] = "| 年份节点 | 汇编夜光指标总量（sum） | 像元加权均值（sum/count） | 空间集聚特征 |"
        if re.match(r"\| \*\*(1986|1995|2005|2013|2024) 年\*\*", line):
            cells = line.split("|")
            year = int(re.search(r"\d{4}", cells[1])[0])
            if year in yearly.index:
                row = yearly.loc[year]
                cells[2] = f" {row['sum']:,.2f} "
                cells[3] = f" {row['sum'] / row['count']:.4f} "
            else:
                cells[2] = " — "
                cells[3] = " — "
            lines[i] = "|".join(cells)
    text = "\n".join(lines) + "\n"
    text = re.sub(
        r"而和平区平均夜光亮度高达 \*\*62\.22\*\*，已逼近光学传感器 63\.0 的理论物理上限，"
        r"生动印证了金融中心与核心都市圈的极致繁荣密度。",
        "2013 年和平区的原表 mean 为 62.22；各区均值与全市加权均值采用不同的汇总尺度。",
        text)
    text = text.replace("遥感数据显示，**滨海新区", "2013 年汇编表显示，**滨海新区")
    core_names = ["和平区", "河东区", "河西区", "南开区", "河北区", "红桥区"]
    earliest = source[source["year"] == 1986]
    share = earliest[earliest["district_name"].isin(core_names)]["sum"].sum() / earliest["sum"].sum() * 100
    text = re.sub(
        r"六个核心区面积不足全域 1\.5%，但贡献了全域超 60% 的夜光辐射总量。",
        f"1986 年六个核心区的汇编夜光指标总量占全市 {share:.2f}%。", text)
    text = text.replace("2007 年至今（", "2007—2013 年（")
    text = text.replace("全域饱和与双城辉映", "空间集聚与双城发展")
    text = text.replace("核心区亮度接近卫星传感器极限饱和值",
                        "核心六区的原表均值高于多数外围区")
    return text


def main():
    records = []
    point_descriptions = {}
    for name in ["taiwan_configs.py", "hongkong_configs.py", "macao_configs.py"]:
        namespace = runpy.run_path(str(ROOT / "scripts" / name))
        for value in namespace.values():
            if not isinstance(value, dict):
                continue
            for config in value.values():
                if not isinstance(config, dict) or "sec_id" not in config:
                    continue
                point_descriptions[config["sec_id"]] = config.get("special_labels", [])
    for source in sorted((ROOT / "sections_vol2").glob("*.md")):
        before = source.read_text(encoding="utf-8-sig")
        after, diagrams = repair_text(before)
        after, removed = nightlight_text(after, source.name[:2])
        if source.name.startswith("02-00_"):
            after = tianjin_nightlight(after)
        after = after.replace("传统传统", "传统")
        for point in point_descriptions.get(source.name.split("_", 1)[0], []):
            if len(point) > 3 and isinstance(point[3], str):
                pattern = (r"(\*\*" + re.escape(point[0]) + r"\*\*[^\n]*?：)\s*"
                           + re.escape(str(point[2])) + r"\s*；")
                after = re.sub(pattern, lambda match: match[1] + point[3] + "；", after)
        source.write_text(after, encoding="utf-8")
        records.append(dict(section=source.name, changed=before != after,
                            diagrams=diagrams,
                            replaced_nightlight_statements=removed,
                            remaining_commands=re.findall(r"\\[a-zA-Z]+", after),
                            remaining_math=after.count("$")))
    report_path = OUT / "qa" / "text_revision.json"
    if not report_path.exists() or any(item["changed"] for item in records):
        report_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print("changed", sum(item["changed"] for item in records),
          "diagrams", sum(item["diagrams"] for item in records))
    print("nightlight statements", sum(len(r["replaced_nightlight_statements"]) for r in records))
    print("residuals", [r["section"] for r in records if r["remaining_commands"] or r["remaining_math"]])


if __name__ == "__main__":
    main()
