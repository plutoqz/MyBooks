# -*- coding: utf-8 -*-
"""13.5.28 澳门特别行政区 —— 珠江口区位图与经济/旅客双联图。

fig13-149 澳门在珠江口的位置（粤港澳大湾区局部；港珠澳大桥示意）
fig13-150 澳门本地生产总值与入境旅客（2019—2024）
"""
import os
import sys

import geopandas as gpd
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import (ALBERS, C_CHINA, C_SEA, C_TEXT, DATA, DPI, FIGURES,
                   add_title, new_map_axes, setup)
from pyproj import Transformer

_T = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True)

YEARS = ["2019", "2020", "2021", "2022", "2023", "2024"]
GDP = [4667, 2044, 2413, 1873, 3795, 4033]        # 亿澳门元，当年价格
VISITORS = [3940, 590, 770, 571, 2823, 3493]       # 万人次，入境旅客

CITY = {  # 城市标注（经纬度）
    "广州": (113.26, 23.13), "东莞": (113.75, 23.02), "深圳": (114.06, 22.55),
    "中山": (113.39, 22.52), "珠海": (113.58, 22.27), "香港": (114.17, 22.30),
    "澳门": (113.55, 22.20), "江门": (113.08, 22.58),
}

BRIDGE = [(113.555, 22.215), (113.74, 22.26), (113.92, 22.29), (114.05, 22.31)]


def fig149_locator():
    prov = gpd.read_file(os.path.join(
        DATA, "boundaries", "datav", "100000_full.json")).to_crs(ALBERS)
    gd = prov[prov["name"] == "广东省"]
    hk = prov[prov["name"] == "香港特别行政区"]
    mo = prov[prov["name"] == "澳门特别行政区"]
    riv = gpd.read_file(os.path.join(
        DATA, "boundaries", "natural_earth", "ne_50m_rivers_lake_centerlines",
        "ne_50m_rivers_lake_centerlines.shp")).to_crs(ALBERS)

    fig, ax = new_map_axes((9.8, 8.6))
    fig.subplots_adjust(bottom=0.10, top=0.985, left=0.01, right=0.99)
    ax.set_facecolor(C_SEA)

    gd.plot(ax=ax, color="#f2efe9", edgecolor="#b9b2a4", linewidth=0.5, zorder=2)
    hk.plot(ax=ax, color="#f5c6aa", edgecolor="#8e4a2f", linewidth=0.7, zorder=3)
    mo.plot(ax=ax, color=C_CHINA, edgecolor="#7f2d1e", linewidth=0.9, zorder=4)

    x0, x1 = _T.transform(112.75, 22.02)
    x2, y1 = _T.transform(114.32, 23.34)
    ax.set_xlim(min(x0, x2), max(x0, x2))
    ax.set_ylim(min(x1, y1), max(x1, y1))

    vx0, vx1 = ax.get_xlim()
    vy0, vy1 = ax.get_ylim()
    view = riv.cx[vx0:vx1, vy0:vy1]
    if len(view):
        view.plot(ax=ax, color="#3d6fa8", lw=0.9, zorder=2.5)

    # 港珠澳大桥
    xs, ys = zip(*[_T.transform(*p) for p in BRIDGE])
    ax.plot(xs, ys, color="#b03a2e", lw=2.0, ls=(0, (6, 2)), zorder=6)
    bx, by = _T.transform(113.85, 22.30)
    ax.annotate("港珠澳大桥（2018 年通车，55 km）", xy=(bx, by - 2000),
                xytext=(bx - 26000, by + 14000), fontsize=8.6, color="#b03a2e",
                arrowprops=dict(arrowstyle="-", color="#b03a2e", lw=0.7),
                zorder=8)

    for name, (lon, lat) in CITY.items():
        x, y = _T.transform(lon, lat)
        if name == "澳门":
            ax.plot([x], [y], marker="*", ms=15, color="#b03a2e",
                    mec="white", mew=0.8, zorder=9)
            ax.text(x - 7600, y + 1200, name, fontsize=10.5, color="#7f2d1e",
                    fontweight="bold", zorder=9)
        else:
            ax.plot([x], [y], "o", ms=4.6, color="#1a1a1a", mec="white",
                    mew=0.5, zorder=9)
            ax.text(x + 1800, y + 1500, name, fontsize=8.8, color=C_TEXT,
                    zorder=9)

    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.text(0.5, 0.06, "南海", fontsize=10, color="#3d6fa8", ha="center",
            transform=ax.transAxes)
    add_title(ax, "澳门在珠江口的位置",
              "粤港澳大湾区局部：珠江西岸的澳门与东岸的香港隔伶仃洋相望")
    fig.text(0.5, 0.012,
             "界线：DataV.GeoAtlas areas_v3（2021.5，仅供学习交流）；河流：Natural Earth 50m；"
             "示意地图，不作为权属划界依据；投影：Albers 等积圆锥",
             ha="center", va="bottom", fontsize=8, color="#555555")
    fig.savefig(os.path.join(FIGURES, "fig13-149_澳门区位图.png"), dpi=DPI)
    plt.close(fig)


def fig150_gdp_visitors():
    fig, axes = plt.subplots(1, 2, figsize=(12.2, 5.0))

    def panel(ax, vals, title, unit, color, fmt):
        bars = ax.bar(YEARS, vals, width=0.56, color=color, edgecolor="white",
                      linewidth=0.6, zorder=3)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() * 1.02,
                    fmt.format(v), ha="center", va="bottom", fontsize=9,
                    color=C_TEXT, zorder=4)
        ax.set_ylim(0, max(vals) * 1.18)
        ax.set_title(title, fontsize=12, color=C_TEXT, pad=10)
        ax.set_ylabel(unit, fontsize=9.5, color="#666666")
        ax.grid(axis="y", color="#dde3e8", lw=0.7, zorder=0)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.spines["left"].set_color("#999999")
        ax.spines["bottom"].set_color("#999999")
        ax.tick_params(axis="x", length=0, labelsize=10)
        ax.tick_params(axis="y", labelsize=8.4, colors="#666666")

    panel(axes[0], GDP, "本地生产总值（2019—2024）", "亿澳门元", C_CHINA, "{:,.0f}")
    panel(axes[1], VISITORS, "入境旅客（2019—2024）", "万人次", "#a9b8c4", "{:,.0f}")

    fig.text(0.02, 0.965, "澳门的 V 形曲线：疫情冲击与博彩旅游的复苏",
             fontsize=14.5, fontweight="bold", color=C_TEXT, va="top")
    fig.text(0.02, 0.925,
             "2020 年 GDP 较 2019 年腰斩，2024 年恢复至 2019 年的 86.4%；"
             "入境旅客 2024 年 3 492.6 万人次，约为 2019 年的 88.6%",
             fontsize=9, color="#666666", va="top")
    fig.text(0.02, 0.012,
             "数据：澳门特别行政区政府统计暨普查局《本地生产总值》《入境旅客》历年统计",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.04, 1, 0.88))
    fig.savefig(os.path.join(FIGURES, "fig13-150_澳门GDP与旅客.png"), dpi=DPI)
    plt.close(fig)


if __name__ == "__main__":
    setup()
    fig149_locator()
    fig150_gdp_visitors()
    print("macau figures done")



