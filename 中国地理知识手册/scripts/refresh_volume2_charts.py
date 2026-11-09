"""从保留的观测值重排下册统计图。"""
import argparse
import json
import re
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pymupdf

from volume2_layout import OUT, QA, SAVE, render_chart_data, space_chart_values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("patterns", nargs="*", default=["*.data.json"])
    parser.add_argument("--revision-report", type=Path)
    parser.add_argument("--chapters", nargs=2, type=int)
    args = parser.parse_args()
    mpl.rcParams.update({"font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
                         "pdf.fonttype": 42, "svg.fonttype": "none",
                         "axes.unicode_minus": False})
    tools = Path.home() / ".codex" / "skills" / "nature-figure" / "scripts"
    sys.path.insert(0, str(tools))
    from audit_panel_alignment import require_matplotlib_panel_alignment
    if args.revision_report:
        report = json.loads(args.revision_report.read_text(encoding="utf-8"))
        paths = sorted(QA / name for name in report["chart_data"])
    else:
        paths = sorted({p for pattern in args.patterns for p in QA.glob(pattern)})
    if args.chapters:
        paths = [p for p in paths
                 if args.chapters[0] <= int(p.name[3:5]) <= args.chapters[1]]
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        data.setdefault("name", path.name.replace(".data.json", ".png"))
        target = OUT / "figures" / data["name"]
        if not data.get("footers") and target.with_suffix(".pdf").exists():
            with pymupdf.open(target.with_suffix(".pdf")) as pdf:
                data["footers"] = [line.strip() for line in pdf[0].get_text().splitlines()
                                   if re.search(r"数据来源|数据源|底图数据", line)]
        for panel in data["panels"]:
            if "xlabel" not in panel:
                if path.name.startswith("fig12-00-5") and any(
                        bar["horizontal"] for bar in panel["bars"]):
                    panel["xlabel"] = "夜光指标总量（2013年，千单位）"
                else:
                    panel["xlabel"] = ""
        fig = render_chart_data(data)
        space_chart_values(fig)
        require_matplotlib_panel_alignment(
            fig, json_out=str(QA / f"{target.stem}.alignment.json"),
            tolerance_pt=1.5, strict=True)
        for suffix in [".png", ".pdf", ".svg"]:
            SAVE(fig, target.with_suffix(suffix), dpi=300,
                 bbox_inches="tight", pad_inches=0.15)
        plt.close(fig)
        print(target.name, flush=True)
    print(f"Updated chart figures: {len(paths)}", flush=True)


if __name__ == "__main__":
    main()
