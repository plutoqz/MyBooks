# -*- coding: utf-8 -*-
"""13.5.5 内蒙古自治区 —— 省域地势图与分区统计图。

fig201 内蒙古自治区地势图（z9 DEM，300 m/px；12 盟市编号）
fig202 分盟市常住人口（七普）与人口密度双联图
fig203 分盟市地区生产总值（2025）条形图
"""
import os
import sys

import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import setup, C_TEXT, FIGURES, DPI
from ch13_prov_common import fig_relief, fig_pop

ADCODE = "150000"

POP7 = {  # 七普常住人口（万人，2020-11-01，内蒙古自治区第七次全国人口普查公报）
    "呼和浩特市": 344.6, "包头市": 271.0, "乌海市": 55.7, "赤峰市": 403.6,
    "通辽市": 287.3, "鄂尔多斯市": 215.4, "呼伦贝尔市": 224.3,
    "巴彦淖尔市": 153.9, "乌兰察布市": 170.6, "兴安盟": 141.7,
    "锡林郭勒盟": 110.8, "阿拉善盟": 26.2,
}

GDP25 = {  # 2025 年地区生产总值（亿元，各盟市统计公报初步核算）
    "鄂尔多斯市": 6122.2, "包头市": 4711.9, "呼和浩特市": 4278.3,
    "赤峰市": 2407.1, "呼伦贝尔市": 1749.7, "通辽市": 1737.7,
    "锡林郭勒盟": 1289.8, "巴彦淖尔市": 1277.6, "乌兰察布市": 1260.3,
    "兴安盟": 850.1, "乌海市": 540.8, "阿拉善盟": 418.8,
}

GEO = [
    ("k", "大兴安岭", 121.5, 50.6),
    ("k", "阴山", 111.4, 41.0),
    ("k", "贺兰山", 106.0, 39.3),
    ("k", "河套平原", 107.5, 40.9),
    ("k", "科尔沁沙地", 122.7, 43.1),
    ("k", "锡林郭勒草原", 116.3, 43.9),
    ("k", "巴丹吉林沙漠", 102.3, 39.9),
    ("r", "黄河", 110.4, 40.6),
    ("r", "额尔古纳河", 119.6, 50.4),
    ("r", "西辽河", 123.1, 43.5),
    ("r", "黑河下游", 100.9, 41.3),
    ("l", "呼伦湖", 117.35, 49.05, {"dot": "lake"}),
    ("l", "乌梁素海", 108.9, 40.95, {"dot": "lake"}),
    ("l", "居延海", 101.15, 42.32, {"dot": "lake"}),
    ("m", "白云鄂博稀土矿", 110.0, 41.8, {"dot": "mine"}),
    ("m", "东胜煤田", 110.5, 39.5, {"dot": "mine"}),
    ("p", "满洲里口岸", 117.47, 49.6, {"dot": "port"}),
    ("p", "二连浩特口岸", 111.98, 43.65, {"dot": "port"}),
]


def fig_gdp(fig_no, gdp, fname, title, subtitle, footer):
    """分盟市地区生产总值条形图（2025）。"""
    d = sorted(gdp.items(), key=lambda kv: kv[1])
    names = [k for k, _ in d]
    vals = [v for _, v in d]
    fig, ax = plt.subplots(figsize=(10.8, 7.2))
    colors = ["#c8a45c" if n == "鄂尔多斯市" else "#8fa8b8" for n in names]
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
        "201", ADCODE, "fig13-201_内蒙古地势图.png",
        "内蒙古自治区地势与12盟市",
        "东西横贯2 400余公里的草原带——高原为主体，大兴安岭、阴山、贺兰山构成外缘山框",
        geo_tags=GEO,
        footer_lines=[
            "黄河环绕鄂尔多斯高原构成“几”字弯；呼伦湖（约 2 339 km²）为内蒙古第一大湖",
            "界线：DataV.GeoAtlas（2021.5，仅供学习交流）；高程按 AWS Terrain z9（300 m）量算；"
            "示意地图，不作为权属划界依据；投影：Albers 等积圆锥",
        ],
        tag_top=0.29, cols=4, chunk=3, tag_fs=8.4, footer_y0=0.006)
    big = sorted(areas.items(), key=lambda kv: kv[1])
    print("盟市面积最大/最小：", big[-1], big[0])

    fig_pop(
        "202", ADCODE, POP7, "fig13-202_内蒙古分区人口.png",
        "内蒙古自治区分盟市人口格局",
        "数据：内蒙古自治区第七次全国人口普查公报（2021）；界线：DataV.GeoAtlas areas_v3（2021.5，仅供学习交流）",
        panel_titles=("分盟市常住人口（2020 年七普）", "分盟市人口密度（七普口径）"))

    fig_gdp(
        "203", GDP25, "fig13-203_内蒙古盟市GDP.png",
        "内蒙古自治区分盟市地区生产总值（2025 年）",
        "呼包鄂三市合计占全区约 57%——能源与首府经济构成第一方阵",
        "数据：各盟市 2025 年国民经济和社会发展统计公报（初步核算数，合计约 26 644 亿元）；"
        "全区 26 710.3 亿元（自治区 2025 年统计公报）")


if __name__ == "__main__":
    setup()
    run()
    print("neimenggu figures done")
