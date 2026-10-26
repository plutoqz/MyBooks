# -*- coding: utf-8 -*-
"""第 2 章 行政区划 —— 2.2 节图表。

fig2-3 全国省级行政区划图（Albers 投影，按七大区着色）
fig2-4 分省陆地面积排序（万 km²）
fig2-5 分省常住人口排序（2023 年末）
fig2-6 分省人口密度分级地图
"""
import os
import sys

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter
from pyproj import Transformer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import (ALBERS, C_CHINA, C_TEXT, DATA, DPI, FIGURES, add_title,
                   new_map_axes, save_fig, set_extent_from, setup)

OUT = FIGURES
os.makedirs(OUT, exist_ok=True)

_T = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True)


def to_albers(lon, lat):
    return _T.transform(lon, lat)


def load_provinces():
    """34 个省级行政区（投影到 Albers）+ 九段线要素。"""
    gdf = gpd.read_file(os.path.join(DATA, "boundaries", "datav", "100000_full.json"))
    dash = gdf[gdf["name"].isna() | (gdf["name"].str.len() == 0)]
    prov = gdf[~gdf.index.isin(dash.index)].copy()
    return prov.to_crs(ALBERS), dash.to_crs(ALBERS)


def load_stats():
    return pd.read_csv(os.path.join(DATA, "stats", "provinces.csv"))


REGION_COLORS = {
    "华北": "#c9d8ec", "东北": "#cfe3cd", "华东": "#f5e3c4", "华中": "#f2cfcf",
    "华南": "#d8d2e8", "西南": "#e8d9c0", "西北": "#cde0dd", "港澳台": "#ebebeb",
}
TYPE_COLORS = {"省": "#a9b8c4", "自治区": "#c2a878", "直辖市": "#8fa8bf",
               "特别行政区": "#c0392b"}

DISPLAY_NAME = {
    "内蒙古自治区": "内蒙古", "黑龙江省": "黑龙江", "广西壮族自治区": "广西",
    "西藏自治区": "西藏", "宁夏回族自治区": "宁夏", "新疆维吾尔自治区": "新疆",
    "香港特别行政区": "香港", "澳门特别行政区": "澳门",
}
LEADERS = {  # 小政区：标注名 -> (锚点lon, lat, 标签lon, lat)
    "北京市": ("北京", 116.40, 39.90, 112.8, 42.8),
    "天津市": ("天津", 117.35, 39.10, 121.6, 40.6),
    "上海市": ("上海", 121.47, 31.23, 125.8, 29.2),
    "宁夏回族自治区": ("宁夏", 106.20, 37.30, 100.8, 34.4),
    "香港特别行政区": ("香港", 114.17, 22.32, 111.4, 20.1),
    "澳门特别行政区": ("澳门", 113.55, 22.20, 108.6, 21.4),
}


def _strip(name):
    if name in DISPLAY_NAME:
        return DISPLAY_NAME[name]
    for suf in ("省", "市", "自治区"):
        if name.endswith(suf):
            return name[: -len(suf)]
    return name


# ---------------------------------------------------------------- fig 2-3
def fig2_3_admin_map():
    prov, dash = load_provinces()
    stats = load_stats().set_index("name")
    prov["region"] = prov["name"].map(stats["region"])

    fig, ax = new_map_axes((10.5, 10.8))
    ax.set_facecolor("#dfe8f0")
    prov.plot(ax=ax, color=prov["region"].map(REGION_COLORS),
              edgecolor="#7f7f7f", linewidth=0.45)
    if len(dash):
        dash.plot(ax=ax, facecolor="none", edgecolor="#4a6274", linewidth=0.7)

    for _, row in prov.iterrows():
        nm = row["name"]
        if nm in LEADERS:
            disp, lon0, lat0, lon1, lat1 = LEADERS[nm]
            x0, y0 = to_albers(lon0, lat0)
            x1, y1 = to_albers(lon1, lat1)
            ax.annotate(disp, xy=(x0, y0), xytext=(x1, y1), fontsize=8.2,
                        color="#2c3e50", ha="center", va="center", zorder=12,
                        arrowprops=dict(arrowstyle="-", color="#666666", lw=0.6,
                                        shrinkA=1, shrinkB=2))
        else:
            p = row.geometry.representative_point()
            ax.text(p.x, p.y, _strip(nm), fontsize=8.6, ha="center", va="center",
                    color="#2c3e50", zorder=11)

    legend_elems = [Patch(fc=c, ec="#7f7f7f", label=r)
                    for r, c in REGION_COLORS.items()]
    ax.legend(handles=legend_elems, loc="lower left", bbox_to_anchor=(0.005, 0.10),
              fontsize=9, framealpha=0.92, edgecolor="#cccccc", title="地理大区",
              title_fontsize=9.5)

    set_extent_from(ax, prov)
    add_title(ax, "全国省级行政区划", "34 个省级行政区，按七大地理分区着色；断续线为南海九段线")
    save_fig(fig, ax, "fig2-3_全国省级行政区划图.png",
             footer="行政界线：DataV.GeoAtlas areas_v3（2021.5，仅供学习交流）；投影：Albers 等积圆锥（105°E，25°/47°N）\n"
                    "示意地图，不作为权属划界依据")


# ---------------------------------------------------------------- 图表工具
def barh_local(filename, df, value_col, label_col, title, subtitle, xlabel,
               color_col, footer, figsize=(9.2, 10.0), nd=0, legend_elems=None):
    """横向条形图：颜色列随行排序，避免错位。"""
    d = df.sort_values(value_col, ascending=True)
    fig, ax = plt.subplots(figsize=figsize)
    bars = ax.barh(d[label_col], d[value_col], color=d[color_col], height=0.62,
                   edgecolor="white", linewidth=0.4, zorder=3)
    for b, v in zip(bars, d[value_col]):
        dec = 4 if 0 < v < 0.01 else nd
        txt = f"{v:,.{dec}f}".replace(",", " ")
        ax.text(b.get_width() + max(d[value_col]) * 0.012,
                b.get_y() + b.get_height() / 2, txt,
                va="center", ha="left", fontsize=8.6, color=C_TEXT, zorder=4)
    ax.set_xlim(0, max(d[value_col]) * 1.12)
    ax.grid(axis="x", color="#dde3e8", lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#999999")
    ax.tick_params(axis="y", length=0, labelsize=9.3)
    ax.tick_params(axis="x", labelsize=8.5, colors="#666666")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, p: f"{v:,.0f}".replace(",", " ")))
    ax.set_xlabel(xlabel, fontsize=9, color="#666666")

    if legend_elems:
        ax.legend(handles=legend_elems, loc="lower right", fontsize=8.8,
                  framealpha=0.92, edgecolor="#cccccc")

    fig.text(0.02, 0.982, title, fontsize=14.5, fontweight="bold", color=C_TEXT)
    fig.text(0.02, 0.958, subtitle, fontsize=9.3, color="#666666")
    fig.text(0.02, 0.008, footer, fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.045, 1, 0.945))
    fig.savefig(os.path.join(OUT, filename), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 2-4/2-5
def fig2_4_area():
    s = load_stats()
    s["label"] = s["name"].map(_strip)
    s["color"] = s["type"].map(TYPE_COLORS)
    s["value"] = s["area_km2"] / 10000  # 万 km²
    type_legend = [Patch(fc=c, ec="white", label=t) for t, c in TYPE_COLORS.items()]
    barh_local(
        "fig2-4_分省面积排序.png", s, "value", "label",
        "各省级行政区陆地面积排序", "单位：万 km²；最大（新疆）与最小（澳门）相差约 5 万倍",
        "万 km²", "color",
        "数据来源：各地官方公布的陆地面积（通行口径）；海南省面积不含南海诸岛水域。",
        figsize=(9.2, 10.0), nd=2, legend_elems=type_legend)


def fig2_5_pop():
    s = load_stats()
    s["label"] = s["name"].map(_strip)
    s["color"] = ["#c0392b" if v >= 10000 else "#a9b8c4" for v in s["pop_2023w"]]
    barh_local(
        "fig2-5_分省常住人口排序.png", s, "pop_2023w", "label",
        "各省级行政区常住人口排序（2023 年末）", "单位：万人；红色为人口过亿省份（广东、山东）",
        "万人", "color",
        "数据来源：《中国统计年鉴 2024》（2023 年末常住人口）；台湾省为台湾有关方面公布的 2023 年口径，港澳为 2023 年年中口径。",
        figsize=(9.2, 10.0), nd=0)


# ---------------------------------------------------------------- fig 2-6
def fig2_6_density():
    prov, dash = load_provinces()
    s = load_stats()
    s["density"] = s["pop_2023w"] * 10000 / s["area_km2"]
    sd = s.set_index("name")

    bins = [0, 50, 200, 400, 700, 4000, 1e9]
    labels = ["<50", "50–200", "200–400", "400–700", "700–4 000", "≥4 000"]
    fills = ["#f7f7f0", "#fde9c8", "#f9c08a", "#ef8f5e", "#d64541", "#8e1a1a"]
    prov["d"] = prov["name"].map(sd["density"])
    prov["cls"] = pd.cut(prov["d"], bins=bins, labels=labels)

    fig, ax = new_map_axes((10.5, 10.8))
    ax.set_facecolor("#dfe8f0")
    for lab, fc in zip(labels, fills):
        sub = prov[prov["cls"] == lab]
        if len(sub):
            sub.plot(ax=ax, color=fc, edgecolor="#8f8f8f", linewidth=0.45)
    if len(dash):
        dash.plot(ax=ax, facecolor="none", edgecolor="#4a6274", linewidth=0.7)

    legend_elems = [Patch(fc=fc, ec="#8f8f8f", label=f"{lab} 人/km²")
                    for lab, fc in zip(labels, fills)]
    ax.legend(handles=legend_elems, loc="lower left", bbox_to_anchor=(0.005, 0.085),
              fontsize=9, framealpha=0.92, edgecolor="#cccccc", title="人口密度",
              title_fontsize=9.5)

    set_extent_from(ax, prov)
    add_title(ax, "分省人口密度", "2023 年末常住人口与陆地面积之比；澳门（约 2.1 万人/km²）与香港（约 6 700 人/km²）居前两位")
    save_fig(fig, ax, "fig2-6_分省人口密度图.png",
             footer="数据来源：《中国统计年鉴 2024》；台湾省为台湾有关方面公布的 2023 年年末口径。行政界线：DataV.GeoAtlas areas_v3\n"
                    "（2021.5，仅供学习交流）；投影：Albers 等积圆锥。示意地图，不作为权属划界依据")


if __name__ == "__main__":
    setup()
    fig2_3_admin_map()
    fig2_4_area()
    fig2_5_pop()
    fig2_6_density()
    print("已生成：", sorted(f for f in os.listdir(OUT) if f.startswith("fig2-")))
