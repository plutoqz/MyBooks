# -*- coding: utf-8 -*-
"""13.5.30 甘肃省 —— 省域地势图与分区统计图。

fig13-204 甘肃省地势图（z9 DEM，300 m/px；14 市州编号）
fig13-205 分市州常住人口（七普）与人口密度双联图
fig13-206 分市州地区生产总值（2025）条形图
"""
import os
import sys

import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import setup, C_TEXT, FIGURES, DPI
from ch13_prov_common import fig_relief, fig_pop

ADCODE = "620000"

POP7 = {  # 七普常住人口（万人，2020-11-01，甘肃省第七次全国人口普查公报第二号）
    "兰州市": 435.9, "嘉峪关市": 31.3, "金昌市": 43.8, "白银市": 151.2,
    "天水市": 298.5, "武威市": 146.5, "张掖市": 113.1, "平凉市": 184.9,
    "酒泉市": 105.6, "庆阳市": 218.0, "定西市": 252.4, "陇南市": 240.7,
    "临夏回族自治州": 211.0, "甘南藏族自治州": 69.2,
}

GDP25 = {  # 2025 年地区生产总值（亿元，各市州统计公报汇总）
    "兰州市": 3903.6, "庆阳市": 1235.3, "酒泉市": 1103.6, "天水市": 980.9,
    "武威市": 802.3, "定西市": 793.9, "白银市": 789.2, "平凉市": 754.9,
    "张掖市": 734.4, "陇南市": 716.0, "金昌市": 670.2, "临夏州": 546.6,
    "嘉峪关市": 391.0, "甘南州": 275.6,
}

GEO = [
    ("k", "祁连山", 98.8, 39.1),
    ("k", "北山", 97.2, 41.4),
    ("k", "河西走廊", 99.5, 39.9),
    ("k", "乌鞘岭", 102.9, 37.3),
    ("k", "西秦岭", 104.85, 34.05),
    ("k", "甘南高原", 102.3, 34.7),
    ("k", "陇中黄土高原", 105.0, 35.6),
    ("r", "黄河", 104.1, 36.35),
    ("r", "黑河", 99.9, 39.7),
    ("r", "疏勒河", 95.6, 40.7),
    ("r", "石羊河", 102.6, 38.3),
    ("r", "白龙江", 104.95, 32.95),
    ("l", "刘家峡水库", 103.15, 35.98, {"dot": "lake"}),
    ("l", "月牙泉", 94.68, 40.09, {"dot": "lake"}),
    ("m", "金川镍矿", 101.75, 38.95, {"dot": "mine"}),
    ("m", "玉门油田", 97.55, 40.3, {"dot": "mine"}),
]


def fig_gdp(fig_no, gdp, fname, title, subtitle, footer):
    """分市州地区生产总值条形图（2025）。"""
    d = sorted(gdp.items(), key=lambda kv: kv[1])
    names = [k for k, _ in d]
    vals = [v for _, v in d]
    fig, ax = plt.subplots(figsize=(10.8, 7.8))
    colors = ["#c8a45c" if n == "兰州市" else "#8fa8b8" for n in names]
    bars = ax.barh(names, vals, color=colors, edgecolor="white", lw=0.4,
                   height=0.62, zorder=3)
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
    fig.text(0.02, 0.965, title, fontsize=14.5, fontweight="bold", color=C_TEXT)
    fig.text(0.02, 0.938, subtitle, fontsize=9.0, color="#666666")
    fig.text(0.02, 0.02, footer, fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.045, 1, 0.92))
    fig.savefig(os.path.join(FIGURES, fname), dpi=DPI)
    plt.close(fig)
    print(f"fig13-{fig_no}: GDP sum = {sum(vals):,.1f}")


def run():
    areas = fig_relief(
        "204", ADCODE, "fig13-204_甘肃地势图.png",
        "甘肃省地势与14市州",
        "一柄西向的“玉如意”——河西走廊斜贯，三大高原在此交汇",
        geo_tags=GEO,
        footer_lines=[
            "河西走廊三大内陆河：石羊河、黑河、疏勒河，串起武威—张掖—酒泉—敦煌绿洲带",
            "界线：DataV.GeoAtlas（2021.5，仅供学习交流）；高程按 AWS Terrain z9（300 m）量算；"
            "示意地图，不作为权属划界依据；投影：Albers 等积圆锥",
        ],
        tag_top=0.335, cols=4, chunk=3, tag_fs=8.4, footer_y0=0.006,
        map_bottom=0.345)
    big = sorted(areas.items(), key=lambda kv: kv[1])
    print("市州面积最大/最小：", big[-1], big[0])

    fig_pop(
        "205", ADCODE, POP7, "fig13-205_甘肃分区人口.png",
        "甘肃省分市州人口格局",
        "数据：甘肃省第七次全国人口普查公报第二号（2021）；界线：DataV.GeoAtlas areas_v3（2021.5，仅供学习交流）",
        panel_titles=("分市州常住人口（2020 年七普）", "分市州人口密度（七普口径）"))

    fig_gdp(
        "206", GDP25, "fig13-206_甘肃市州GDP.png",
        "甘肃省分市州地区生产总值（2025 年）",
        "兰州一市占全省约 28.5%——“一城独大”格局仍在延续",
        "数据：各市州 2025 年国民经济和社会发展统计公报（汇总数，合计 13 697.5 亿元，与全省公报一致）")


if __name__ == "__main__":
    setup()
    run()
    print("gansu figures done")
