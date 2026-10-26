# -*- coding: utf-8 -*-
"""13.5.27 香港特别行政区 —— 18 区地势图与深港对照图。

fig13-147 香港特别行政区地势图（z11 DEM，约 75 m/px；18 区编号标记）
fig13-148 香港与深圳的四项指标对照（面积、人口、GDP、集装箱吞吐量）
"""
import os
import sys

import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import C_CHINA, C_TEXT, DPI, FIGURES, setup
from ch13_prov_south import fig_relief

ADCODE = "810000"

GEO = [
    ("h", "维多利亚港", 114.17, 22.29),
    ("k", "大帽山", 114.12, 22.41),
    ("k", "太平山", 114.15, 22.27),
    ("k", "狮子山", 114.17, 22.35),
    ("k", "大屿山", 113.95, 22.27),
    ("r", "深圳河", 114.08, 22.52),
]

# 2024 年四项指标：香港（特区政府统计处、海运港口局）与深圳（统计公报）
COMPARE = [
    ("陆地面积", "km²", 1_114, 1_997, "{:,.0f}"),
    ("常住人口", "万人", 753.4, 1_778.9, "{:,.1f}"),
    ("地区生产总值", "亿元（人民币）", 28_900, 36_802, "{:,.0f}"),
    ("港口集装箱吞吐量", "万标准箱", 1_369, 3_339, "{:,.0f}"),
]


def fig148_hk_sz():
    fig, axes = plt.subplots(2, 2, figsize=(10.6, 6.6))
    for ax, (name, unit, hk, sz, fmt) in zip(axes.ravel(), COMPARE):
        bars = ax.bar(["香港", "深圳"], [hk, sz], width=0.52,
                      color=["#c0392b", "#a9b8c4"], edgecolor="white",
                      linewidth=0.6, zorder=3)
        for b, v in zip(bars, [hk, sz]):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() * 1.02,
                    fmt.format(v), ha="center", va="bottom", fontsize=10.5,
                    color=C_TEXT, zorder=4)
        ax.set_ylim(0, max(hk, sz) * 1.20)
        ratio = sz / hk
        ax.set_title(f"{name}（{unit}）　深圳/香港 = {ratio:.2f}", fontsize=11,
                     color=C_TEXT, pad=8)
        ax.grid(axis="y", color="#dde3e8", lw=0.7, zorder=0)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.spines["left"].set_color("#999999")
        ax.spines["bottom"].set_color("#999999")
        ax.tick_params(axis="x", length=0, labelsize=10.5)
        ax.tick_params(axis="y", labelsize=8.2, colors="#666666")

    fig.text(0.02, 0.975, "一河两岸：香港与深圳的四项指标对照（2024 年）",
             fontsize=14.5, fontweight="bold", color=C_TEXT, va="top")
    fig.text(0.02, 0.935,
             "香港 GDP 31 770 亿港元，按当年平均汇率折约 2.89 万亿元人民币；"
             "1980 年深圳 GDP 不足香港的百分之一，2018 年起超过香港",
             fontsize=9, color="#666666", va="top")
    fig.text(0.02, 0.012,
             "数据：香港特区政府统计处、香港海运港口局；深圳市 2024 年国民经济和社会发展统计公报",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.04, 1, 0.90))
    fig.savefig(os.path.join(FIGURES, "fig13-148_香港与深圳对比.png"), dpi=DPI)
    plt.close(fig)


def run():
    areas = fig_relief(
        147, ADCODE, "fig13-147_香港特别行政区地势图.png",
        "香港特别行政区地势与18区",
        "山海之间的高密度城市——从大帽山到维多利亚港",
        geo_tags=GEO,
        footer_lines=[
            "最高峰大帽山 957 米；建成区仅占土地约四分之一，约 6% 的土地由填海而来",
            "界线：DataV.GeoAtlas（2021.5，仅供学习交流）；高程按 AWS Terrain z11（约 75 m）量算；"
            "示意地图，不作为权属划界依据；投影：Albers 等积圆锥",
        ],
        tag_top=0.26, cols=2, chunk=6, zoom=11)
    print("香港 18 区量算面积（km²）：", areas)

    fig148_hk_sz()


if __name__ == "__main__":
    setup()
    run()
    print("hongkong figures done")


