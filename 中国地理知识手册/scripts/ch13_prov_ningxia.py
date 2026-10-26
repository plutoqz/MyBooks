# -*- coding: utf-8 -*-
"""13.5.31 宁夏回族自治区 —— 省域地势图与分区统计图。

fig13-207 宁夏回族自治区地势图（z9 DEM，300 m/px；5 市编号）
fig13-208 分市常住人口（七普）与人口密度双联图
fig13-209 分市地区生产总值（2025）条形图
"""
import os
import sys

import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import setup, C_TEXT, FIGURES, DPI
from ch13_prov_common import fig_relief, fig_pop

ADCODE = "640000"

POP7 = {  # 七普常住人口（万人，2020-11-01，宁夏第七次全国人口普查公报）
    "银川市": 285.9, "石嘴山市": 75.1, "吴忠市": 138.3, "固原市": 114.2,
    "中卫市": 106.7,
}

GDP25 = {  # 2025 年地区生产总值（亿元，各市统计公报汇总）
    "银川市": 3033.5, "吴忠市": 961.7, "中卫市": 633.4, "石嘴山市": 579.8,
    "固原市": 488.1,
}

GEO = [
    ("k", "贺兰山", 106.0, 39.05),
    ("k", "六盘山", 106.2, 35.42),
    ("k", "宁夏平原", 106.25, 38.35),
    ("r", "黄河", 106.35, 38.55),
    ("r", "清水河", 105.7, 37.2),
    ("r", "泾河", 106.45, 35.5),
    ("l", "沙湖", 106.4, 38.8, {"dot": "lake"}),
    ("l", "青铜峡水库", 106.0, 37.95, {"dot": "lake"}),
    ("m", "宁东能源化工基地", 106.55, 38.2, {"dot": "mine"}),
]


def fig_gdp(fig_no, gdp, fname, title, subtitle, footer):
    """分市地区生产总值条形图（2025）。"""
    d = sorted(gdp.items(), key=lambda kv: kv[1])
    names = [k for k, _ in d]
    vals = [v for _, v in d]
    fig, ax = plt.subplots(figsize=(10.8, 5.6))
    colors = ["#c8a45c" if n == "银川市" else "#8fa8b8" for n in names]
    bars = ax.barh(names, vals, color=colors, edgecolor="white", lw=0.4,
                   height=0.58, zorder=3)
    for b, v in zip(bars, vals):
        ax.text(b.get_width() + max(vals) * 0.012,
                b.get_y() + b.get_height() / 2, f"{v:,.0f}",
                va="center", ha="left", fontsize=9.5, color=C_TEXT, zorder=4)
    ax.set_xlim(0, max(vals) * 1.13)
    ax.grid(axis="x", color="#dde3e8", lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#999999")
    ax.tick_params(axis="y", length=0, labelsize=10)
    ax.tick_params(axis="x", labelsize=8.5, colors="#666666")
    ax.set_xlabel("地区生产总值（亿元）", fontsize=9, color="#666666")
    fig.text(0.02, 0.955, title, fontsize=14.5, fontweight="bold", color=C_TEXT)
    fig.text(0.02, 0.925, subtitle, fontsize=9.0, color="#666666")
    fig.text(0.02, 0.02, footer, fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.045, 1, 0.90))
    fig.savefig(os.path.join(FIGURES, fname), dpi=DPI)
    plt.close(fig)
    print(f"fig13-{fig_no}: GDP sum = {sum(vals):,.1f}")


def run():
    areas = fig_relief(
        "207", ADCODE, "fig13-207_宁夏地势图.png",
        "宁夏回族自治区地势与5市",
        "“塞上江南”——贺兰山护佑的黄河平原与南部的黄土丘陵、六盘山地",
        geo_tags=GEO,
        footer_lines=[
            "黄河自中卫入境、经青铜峡至石嘴山出境，两岸引黄灌区即“塞上江南”",
            "界线：DataV.GeoAtlas（2021.5，仅供学习交流）；高程按 AWS Terrain z9（300 m）量算；"
            "示意地图，不作为权属划界依据；投影：Albers 等积圆锥",
        ],
        tag_top=0.29, cols=4, chunk=3, tag_fs=8.4, footer_y0=0.006)
    big = sorted(areas.items(), key=lambda kv: kv[1])
    print("市面积最大/最小：", big[-1], big[0])

    fig_pop(
        "208", ADCODE, POP7, "fig13-208_宁夏分区人口.png",
        "宁夏回族自治区分市人口格局",
        "数据：宁夏回族自治区第七次全国人口普查公报（2021）；界线：DataV.GeoAtlas areas_v3（2021.5，仅供学习交流）",
        panel_titles=("分市常住人口（2020 年七普）", "分市人口密度（七普口径）"))

    fig_gdp(
        "209", GDP25, "fig13-209_宁夏各市GDP.png",
        "宁夏回族自治区分市地区生产总值（2025 年）",
        "银川一市占全区约 53%——首府集聚度居全国省区前列",
        "数据：各市 2025 年国民经济和社会发展统计公报（汇总数，合计 5 696.49 亿元，与全区公报一致）")


if __name__ == "__main__":
    setup()
    run()
    print("ningxia figures done")
