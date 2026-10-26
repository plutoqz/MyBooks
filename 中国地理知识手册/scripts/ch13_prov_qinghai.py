# -*- coding: utf-8 -*-
"""13.5.33 青海省 —— 省域地势图与分区统计图。

fig13-213 青海省地势图（z9 DEM，300 m/px；8 市州编号）
fig13-214 分市州常住人口（七普）与人口密度双联图
fig13-215 分市州地区生产总值（2025）条形图
"""
import os
import sys

import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import setup, C_TEXT, FIGURES, DPI
from ch13_prov_common import fig_relief, fig_pop

ADCODE = "630000"

POP7 = {  # 七普常住人口（万人，2020-11-01，青海省第七次全国人口普查公报）
    "西宁市": 246.8, "海东市": 135.8, "海北藏族自治州": 26.5,
    "黄南藏族自治州": 27.6, "海南藏族自治州": 44.7,
    "果洛藏族自治州": 21.6, "玉树藏族自治州": 42.5,
    "海西蒙古族藏族自治州": 46.8,
}

GDP25 = {  # 2025 年地区生产总值（亿元，各市州统计公报汇总）
    "西宁市": 1914.8, "海西州": 917.3, "海东市": 615.8, "海南州": 246.3,
    "黄南州": 124.2, "海北州": 122.5, "玉树州": 97.4, "果洛州": 73.2,
}

GEO = [
    ("k", "祁连山", 99.0, 38.35),
    ("k", "昆仑山", 93.5, 36.2),
    ("k", "唐古拉山", 92.0, 33.3),
    ("k", "河湟谷地", 101.15, 36.9),
    ("k", "三江源", 95.5, 33.5),
    ("k", "巴颜喀拉山", 96.3, 34.6),
    ("k", "柴达木盆地", 94.3, 37.3),
    ("k", "阿尼玛卿雪山", 99.4, 34.8),
    ("r", "黄河", 101.4, 36.05),
    ("r", "长江源·通天河", 97.3, 33.6),
    ("r", "澜沧江源", 94.2, 32.6),
    ("r", "湟水", 102.75, 36.3),
    ("l", "青海湖", 100.2, 36.9, {"dot": "lake"}),
    ("l", "龙羊峡水库", 100.9, 36.1, {"dot": "lake"}),
    ("m", "察尔汗钾盐", 95.3, 36.75, {"dot": "mine"}),
    ("m", "冷湖油田", 93.4, 38.8, {"dot": "mine"}),
]

RENAME = {  # 图下编号列表用简称（仅影响图例显示）
    "海北藏族自治州": "海北州", "黄南藏族自治州": "黄南州",
    "海南藏族自治州": "海南州", "果洛藏族自治州": "果洛州",
    "玉树藏族自治州": "玉树州", "海西蒙古族藏族自治州": "海西州",
}


def fig_gdp(fig_no, gdp, fname, title, subtitle, footer):
    """分市州地区生产总值条形图（2025）。"""
    d = sorted(gdp.items(), key=lambda kv: kv[1])
    names = [k for k, _ in d]
    vals = [v for _, v in d]
    fig, ax = plt.subplots(figsize=(10.8, 5.8))
    colors = ["#c8a45c" if n == "西宁市" else "#8fa8b8" for n in names]
    bars = ax.barh(names, vals, color=colors, edgecolor="white", lw=0.4,
                   height=0.6, zorder=3)
    for b, v in zip(bars, vals):
        ax.text(b.get_width() + max(vals) * 0.012,
                b.get_y() + b.get_height() / 2, f"{v:,.0f}",
                va="center", ha="left", fontsize=9, color=C_TEXT, zorder=4)
    ax.set_xlim(0, max(vals) * 1.13)
    ax.grid(axis="x", color="#dde3e8", lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#999999")
    ax.tick_params(axis="y", length=0, labelsize=9.5)
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
        "213", ADCODE, "fig13-213_青海地势图.png",
        "青海省地势与8市州",
        "“中华水塔”——三江之源、昆仑之巅，柴达木盆地嵌于高原东北",
        geo_tags=GEO,
        footer_lines=[
            "长江、黄河、澜沧江均发源于此；青海湖（4 650 km²）为我国最大内陆咸水湖",
            "界线：DataV.GeoAtlas（2021.5，仅供学习交流）；高程按 AWS Terrain z9（300 m）量算；"
            "示意地图，不作为权属划界依据；投影：Albers 等积圆锥",
        ],
        tag_top=0.29, cols=4, chunk=3, tag_fs=8.4, footer_y0=0.006,
        rename_map=RENAME)
    big = sorted(areas.items(), key=lambda kv: kv[1])
    print("市州面积最大/最小：", big[-1], big[0])

    fig_pop(
        "214", ADCODE, POP7, "fig13-214_青海分区人口.png",
        "青海省分市州人口格局",
        "数据：青海省第七次全国人口普查公报（2021）；界线：DataV.GeoAtlas areas_v3（2021.5，仅供学习交流）",
        panel_titles=("分市州常住人口（2020 年七普）", "分市州人口密度（七普口径）"))

    fig_gdp(
        "215", GDP25, "fig13-215_青海市州GDP.png",
        "青海省分市州地区生产总值（2025 年）",
        "西宁一市占全省约 46%——河湟谷地集聚了全省近三分之二的人口",
        "数据：各市州 2025 年国民经济和社会发展统计公报（汇总数）；全省 4 121.84 亿元（2025 年统计公报）")


if __name__ == "__main__":
    setup()
    run()
    print("qinghai figures done")
