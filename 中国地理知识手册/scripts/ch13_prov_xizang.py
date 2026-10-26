# -*- coding: utf-8 -*-
"""13.5.34 西藏自治区 —— 省域地势图与分区统计图。

fig13-216 西藏自治区地势图（z9 DEM，300 m/px；7 地市编号）
fig13-217 分地市常住人口（七普）与人口密度双联图
fig13-218 西藏与尼泊尔：经济与人口对比双联图
"""
import os
import sys

import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import setup, C_TEXT, FIGURES, DPI
from ch13_prov_common import fig_relief, fig_pop

ADCODE = "540000"

POP7 = {  # 七普常住人口（万人，2020-11-01，西藏第七次全国人口普查主要数据公报）
    "拉萨市": 86.8, "日喀则市": 79.8, "昌都市": 76.1, "林芝市": 23.9,
    "山南市": 35.4, "那曲市": 50.5, "阿里地区": 12.3,
}

GEO = [
    ("k", "喜马拉雅山", 84.5, 28.35),
    ("k", "冈底斯山", 83.8, 31.1),
    ("k", "昆仑山", 85.5, 36.0),
    ("k", "念青唐古拉山", 92.3, 30.6),
    ("k", "横断山", 97.5, 30.3),
    ("k", "羌塘高原", 87.5, 33.8),
    ("k", "雅鲁藏布大峡谷", 95.3, 29.55),
    ("r", "雅鲁藏布江", 88.5, 29.4),
    ("r", "拉萨河", 90.2, 30.2),
    ("r", "怒江", 97.2, 31.2),
    ("r", "狮泉河", 80.0, 32.5),
    ("l", "纳木错", 90.6, 30.7, {"dot": "lake"}),
    ("l", "色林错", 88.6, 31.9, {"dot": "lake"}),
    ("l", "玛旁雍错", 81.5, 30.7, {"dot": "lake"}),
    ("m", "玉龙铜矿", 98.1, 31.3, {"dot": "mine"}),
    ("m", "扎布耶锂盐湖", 84.5, 31.6, {"dot": "mine"}),
    ("p", "吉隆口岸", 85.32, 28.35, {"dot": "port"}),
]


def fig_nepal_compare(fname):
    """西藏与尼泊尔：经济与人口对比双联图（世界视角）。"""
    labels = ["西藏", "尼泊尔"]
    gdp_usd = [427, 429]      # 亿美元：西藏 2025（3 031.89 亿元/7.1）；尼泊尔 2024（世界银行）
    pop_wan = [374, 2970]     # 万人：西藏 2025 年末；尼泊尔约（联合国口径）
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.8))

    def panel(ax, vals, title, xlabel, fmt):
        bars = ax.barh(labels[::-1], vals[::-1],
                       color=["#9c6b7f", "#8fa8b8"][::-1],
                       edgecolor="white", lw=0.4, height=0.5, zorder=3)
        for b, v in zip(bars, vals[::-1]):
            ax.text(b.get_width() + max(vals) * 0.02,
                    b.get_y() + b.get_height() / 2, fmt.format(v),
                    va="center", ha="left", fontsize=10, color=C_TEXT,
                    zorder=4)
        ax.set_xlim(0, max(vals) * 1.2)
        ax.grid(axis="x", color="#dde3e8", lw=0.7, zorder=0)
        ax.set_axisbelow(True)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color("#999999")
        ax.tick_params(axis="y", length=0, labelsize=11)
        ax.tick_params(axis="x", labelsize=8.5, colors="#666666")
        ax.set_xlabel(xlabel, fontsize=9, color="#666666")
        ax.set_title(title, fontsize=11.5, color=C_TEXT, pad=10)

    panel(axes[0], gdp_usd, "地区生产总值（现价美元）", "亿美元", "{:,.0f}")
    panel(axes[1], pop_wan, "人口", "万人", "{:,.0f}")
    fig.text(0.02, 0.95, "西藏与邻国尼泊尔：经济体量相当，人口约为其 1/8",
             fontsize=14.5, fontweight="bold", color=C_TEXT)
    fig.text(0.02, 0.885,
             "西藏 GDP 按 2025 年人民币计值折算（1 美元≈7.1 元）；尼泊尔为 2024 年现价美元",
             fontsize=9.0, color="#666666")
    fig.text(0.02, 0.02,
             "数据：西藏自治区 2025 年国民经济和社会发展统计公报；尼泊尔 GDP 为世界银行口径（2024，"
             "约 429 亿美元），人口为联合国口径（约 2 970 万）",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.055, 1, 0.86))
    fig.savefig(os.path.join(FIGURES, fname), dpi=DPI)
    plt.close(fig)
    print("nepal compare done")


def run():
    areas = fig_relief(
        "216", ADCODE, "fig13-216_西藏地势图.png",
        "西藏自治区地势与7地市",
        "世界屋脊——喜马拉雅与冈底斯、念青唐古拉之间，雅鲁藏布江顺谷东流",
        geo_tags=GEO,
        footer_lines=[
            "珠穆朗玛峰（8 848.86 m）为世界最高峰；雅鲁藏布大峡谷为世界最深峡谷；"
            "狮泉河为印度河上源，怒江、澜沧江与长江均流经或发源于此",
            "界线：DataV.GeoAtlas（2021.5，仅供学习交流）；高程按 AWS Terrain z9（300 m）量算；"
            "示意地图，不作为权属划界依据；投影：Albers 等积圆锥",
        ],
        tag_top=0.29, cols=4, chunk=3, tag_fs=8.4, footer_y0=0.006)
    big = sorted(areas.items(), key=lambda kv: kv[1])
    print("地市面积最大/最小：", big[-1], big[0])

    fig_pop(
        "217", ADCODE, POP7, "fig13-217_西藏分区人口.png",
        "西藏自治区分地市人口格局",
        "数据：西藏自治区第七次全国人口普查主要数据公报（2021）；界线：DataV.GeoAtlas areas_v3（2021.5，仅供学习交流）",
        panel_titles=("分地市常住人口（2020 年七普）", "分地市人口密度（七普口径）"))

    fig_nepal_compare("fig13-218_西藏尼泊尔对比.png")


if __name__ == "__main__":
    setup()
    run()
    print("xizang figures done")
