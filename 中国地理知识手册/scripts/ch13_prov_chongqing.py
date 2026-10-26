# -*- coding: utf-8 -*-
"""13.5.22 重庆市 —— 省域地势图与功能板块统计图。

fig13-133 重庆市地势图（z9 DEM，300 m/px；38 区县界线 + 地理要素标注）
fig13-134 三大功能板块人口与人口密度（七普，公报分组口径）
fig13-135 重庆市地区生产总值（1997—2024）
"""
import os
import sys

import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import C_TEXT, DPI, FIGURES, setup
from ch01_charts import barv_chart
from ch13_prov_south import fig_relief

ADCODE = "500000"

# 七普三大功能板块分组（重庆市第七次全国人口普查公报（第二号），精确到人）
BOARDS = {  # 名称: (人口万人, 面积万km²)
    "中心城区": (1034.35, 0.5467),
    "主城新区": (1077.89, 2.3233),
    "渝东北三峡库区城镇群": (806.46, 3.3942),
    "渝东南武陵山区城镇群": (286.72, 1.9803),
}

GDP = {  # 重庆市地区生产总值（亿元），历年统计公报
    "1997": 1525, "2010": 7926, "2020": 25003, "2024": 32193,
}

GEO = [
    ("k", "大巴山", 108.80, 31.60),
    ("k", "三峡库区", 108.30, 30.90),
    ("k", "武陵山", 108.60, 29.30),
    ("k", "金佛山", 107.20, 29.10),
    ("r", "长江", 107.80, 30.30),
    ("r", "嘉陵江", 106.55, 29.85),
    ("r", "乌江", 107.60, 29.35),
    ("c", "中心城区", 106.55, 29.56, {"dot": "star"}),
]


def fig134_boards():
    names = list(BOARDS.keys())
    pops = [BOARDS[n][0] for n in names]
    dens = [BOARDS[n][0] * 1e4 / (BOARDS[n][1] * 1e4) for n in names]
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.4))

    def panel(ax, vals, title, xlabel, fmt):
        order = list(range(len(names)))
        dd = sorted(order, key=lambda i: vals[i])
        bars = ax.barh([names[i] for i in dd], [vals[i] for i in dd],
                       color="#6f9e6f", edgecolor="white", lw=0.4,
                       height=0.6, zorder=3)
        for b, i in zip(bars, dd):
            ax.text(b.get_width() + max(vals) * 0.02,
                    b.get_y() + b.get_height() / 2, fmt.format(vals[i]),
                    va="center", ha="left", fontsize=9, color=C_TEXT, zorder=4)
        ax.set_xlim(0, max(vals) * 1.16)
        ax.grid(axis="x", color="#dde3e8", lw=0.7, zorder=0)
        ax.set_axisbelow(True)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color("#999999")
        ax.tick_params(axis="y", length=0, labelsize=9.5)
        ax.tick_params(axis="x", labelsize=8.2, colors="#666666")
        ax.set_xlabel(xlabel, fontsize=9, color="#666666")
        ax.set_title(title, fontsize=11.5, color=C_TEXT, pad=10)

    panel(axes[0], pops, "功能板块常住人口（2020 年七普）", "万人", "{:,.1f}")
    panel(axes[1], dens, "功能板块人口密度（七普口径）", "人/km²", "{:,.0f}")
    fig.text(0.02, 0.955, "重庆市功能板块人口格局", fontsize=14.5,
             fontweight="bold", color=C_TEXT)
    fig.text(0.02, 0.90,
             "板块分组为重庆市第七次全国人口普查公报（第二号）口径；主城都市区"
             "含中心城区与主城新区；面积按《重庆市国土空间总体规划》口径",
             fontsize=8.6, color="#666666")
    fig.text(0.02, 0.02,
             "数据：重庆市第七次全国人口普查公报（第二号，2021）；"
             "中心城区 10 343 462 人、主城新区 10 778 908 人、渝东北 8 064 628 人、渝东南 2 867 161 人",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.06, 1, 0.88))
    fig.savefig(os.path.join(FIGURES, "fig13-134_重庆功能板块人口.png"), dpi=DPI)
    plt.close(fig)


def run():
    areas = fig_relief(
        133, ADCODE, "fig13-133_重庆市地势图.png",
        "重庆市地势与功能板块",
        "山城江城——大巴山、巫山与武陵山之间的直辖市",
        geo_tags=GEO,
        footer_lines=[
            "38 个区县界线如图所示，功能板块分区见正文与图 13-134；"
            "最高峰阴条岭 2 797 米（巫溪县，大巴山脉）",
            "界线：DataV.GeoAtlas（2021.5，仅供学习交流）；高程按 AWS Terrain z9（300 m）量算；"
            "示意地图，不作为权属划界依据；投影：Albers 等积圆锥",
        ],
        tag_top=0.28, cols=2, chunk=5, number_cities=False)
    print("重庆区县面积（km²）：", areas)

    fig134_boards()

    barv_chart(
        "fig13-135_重庆GDP.png",
        list(GDP.keys()), list(GDP.values()),
        "重庆市地区生产总值（1997—2024）",
        "直辖当年 1 525 亿元，2024 年达 3.22 万亿元——中西部首个 3 万亿城市",
        "亿元",
        highlight_labels=("2024",),
        footer="数据：重庆市历年国民经济和社会发展统计公报（初步核算口径）",
        nd=0)


if __name__ == "__main__":
    setup()
    run()
    print("chongqing figures done")
