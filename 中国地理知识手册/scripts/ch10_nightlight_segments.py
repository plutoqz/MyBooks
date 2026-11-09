"""省级夜光分段序列与重叠年份比较。"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import openpyxl
import pandas as pd

import volume1_layout
from style import setup
from volume1_layout import save_volume_figure

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "上册修订"


def main():
    setup()
    source = next((ROOT / "中国省市数据" / "夜间灯光数据-省、市、县（1986-2024年）"
                   ).glob("*省份*.xlsx"))
    workbook = openpyxl.load_workbook(source, read_only=True, data_only=True)
    tables = []
    for sheet in workbook:
        rows = list(sheet.iter_rows(values_only=True))
        frame = pd.DataFrame(rows[1:], columns=rows[0])
        frame = frame.loc[:, frame.columns.notna()]
        frame["series"] = sheet.title
        tables.append(frame)
    early, modern = tables
    overlap = early[early["年份"].isin([2012, 2013])].merge(
        modern[modern["年份"].isin([2012, 2013])],
        on=["年份", "省份代码"], suffixes=("_early", "_modern"),
        validate="one_to_one",
    )
    overlap["sum_ratio"] = overlap["sum_modern"] / overlap["sum_early"]
    overlap.to_csv(OUT / "qa" / "夜光重叠年份比较.csv", index=False, encoding="utf-8-sig")
    names = ["广东省", "江苏省", "四川省", "黑龙江省"]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True)
    changes = []
    for ax, name in zip(axes.flat, names):
        for frame, color, label in [(early, "#296a9a", "1986—2013 汇编序列"),
                                    (modern, "#b0443a", "2012—2024 NPP-VIIRS 表")]:
            values = frame[frame["省份"] == name].sort_values("年份")
            ax.plot(values["年份"], values["sum"] / 1e6, color=color,
                    label=label, marker="o", markersize=2.3, linewidth=1.4)
        ax.axvspan(2012, 2013, color="#e4e7e8", zorder=0)
        ax.set_title(name, loc="left", fontsize=12, weight="bold")
        ax.set_ylabel("汇编 sum（百万单位）", fontsize=9)
        ax.set_xlabel("年份", fontsize=9)
        ax.set_xticks([1986, 1995, 2005, 2013, 2024])
        values = modern[modern["省份"] == name].set_index("年份")
        changes.append(dict(
            province=name, sum_2012=float(values.loc[2012, "sum"]),
            sum_2024=float(values.loc[2024, "sum"]),
            change_percent=float((values.loc[2024, "sum"] / values.loc[2012, "sum"] - 1) * 100),
            pixel_counts=sorted(values["count"].unique().astype(int).tolist()),
        ))
    fig.suptitle("省级夜间灯光的两组分段序列", x=0.07, ha="left",
                 fontsize=17, weight="bold")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", bbox_to_anchor=(0.97, 0.97),
               ncol=2, frameon=False, fontsize=9)
    fig.text(0.07, 0.015, "数据：本地省级夜间灯光汇编表。灰带为 2012—2013 年重叠期；两组曲线独立绘制。",
             fontsize=8.5, color="#555555")
    fig.tight_layout(rect=(0.01, 0.05, 0.99, 0.91), h_pad=2.0, w_pad=3.0)
    volume1_layout.OUTPUT_DIR = OUT / "figures"
    volume1_layout.AUDIT_DIR = OUT / "qa"
    save_volume_figure(fig, "fig10-12_夜光分段时间序列.png")
    plt.close(fig)
    report = dict(
        overlap_records=len(overlap),
        ratio_min=float(overlap["sum_ratio"].min()),
        ratio_median=float(overlap["sum_ratio"].median()),
        ratio_max=float(overlap["sum_ratio"].max()),
        all_overlap_counts_equal=bool((overlap["count_early"] == overlap["count_modern"]).all()),
        province_changes=changes,
    )
    (OUT / "qa" / "夜光分段专题结果.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.concat(tables, ignore_index=True).to_csv(
        OUT / "qa" / "省级夜光分段数据.csv", index=False, encoding="utf-8-sig")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
