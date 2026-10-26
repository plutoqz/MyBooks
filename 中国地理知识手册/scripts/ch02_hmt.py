# -*- coding: utf-8 -*-
"""第 2 章 行政区划 —— 2.4 节图表。

fig2-10 港澳台位置图（全国主图 + 香港/澳门/台湾三幅放大插图）
fig2-11 港澳台陆地面积与人口对比
"""
import os
import sys

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter
from pyproj import Transformer
from shapely.geometry import box

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import (ALBERS, C_CHINA, C_CHINA_FILL, C_LAND, C_TEXT, DATA, DPI,
                   FIGURES, add_title, load_world, save_fig, set_extent_from,
                   setup)

OUT = FIGURES
os.makedirs(OUT, exist_ok=True)

SEA = "#dfe8f0"          # 与 fig2-3 一致的海面底色
HMT_FILL = "#c0392b"     # 港澳台高亮（红）
HMT_EDGE = "#7f2d1e"
_T = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True)


def to_albers(lon, lat):
    return _T.transform(lon, lat)


def load_hmt():
    gdf = gpd.read_file(os.path.join(DATA, "boundaries", "datav", "100000_full.json"))
    names = {"香港特别行政区", "澳门特别行政区", "台湾省"}
    hmt = gdf[gdf["name"].isin(names)]
    rest = gdf[~gdf["name"].isin(names) & gdf["name"].notna() & (gdf["name"].str.len() > 0)]
    dash = gdf[gdf["name"].isna() | (gdf["name"].str.len() == 0)]
    return hmt.to_crs(ALBERS), rest.to_crs(ALBERS), dash.to_crs(ALBERS)


def clip_land(ax, lon0, lat0, lon1, lat1):
    """Natural Earth 50m 陆地裁剪到插图范围，作为底图。"""
    ne = load_world("50m")
    ne_c = gpd.clip(ne, box(lon0, lat0, lon1, lat1))
    ne_c.plot(ax=ax, color=C_LAND, edgecolor="#b9b2a4", linewidth=0.4)


def dot_label(ax, lon, lat, text, dx=0.07, dy=0.02, fs=8.2, color=C_TEXT,
              weight="normal", dotsize=3.2):
    ax.plot([lon], [lat], "o", ms=dotsize, color="#1a1a1a", zorder=8)
    ax.text(lon + dx, lat + dy, text, fontsize=fs, color=color, va="center",
            ha="left", fontweight=weight, zorder=9)


def arrow_label(ax, xy, xytext, text, fs=8.0, color=C_TEXT, ha="left"):
    ax.annotate(text, xy=xy, xytext=xytext, fontsize=fs, color=color,
                ha=ha, va="center", zorder=9,
                arrowprops=dict(arrowstyle="-", color="#666666", lw=0.55,
                                shrinkA=1, shrinkB=1.5))


def inset_frame(ax, lon0, lat0, lon1, lat1, lat_aspect):
    ax.set_facecolor(SEA)
    ax.set_xlim(lon0, lon1)
    ax.set_ylim(lat0, lat1)
    ax.set_aspect(1 / np.cos(np.radians(lat_aspect)))
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(True)
        s.set_color("#999999")
        s.set_linewidth(0.7)


# ---------------------------------------------------------------- fig 2-10
def fig2_10_hmt_map():
    hmt, rest, dash = load_hmt()

    fig = plt.figure(figsize=(11.6, 8.8))
    gs = fig.add_gridspec(3, 3, width_ratios=[1.62, 1.0, 1.0],
                          height_ratios=[1.0, 1.0, 1.22],
                          left=0.015, right=0.985, top=0.965, bottom=0.075,
                          wspace=0.10, hspace=0.30)
    ax_main = fig.add_subplot(gs[:, 0])
    ax_hk = fig.add_subplot(gs[0, 1:])
    ax_mc = fig.add_subplot(gs[1, 1:])
    ax_tw = fig.add_subplot(gs[2, 1:])

    # ---- 主图：全国，港澳台红色高亮
    ax_main.set_facecolor(SEA)
    ax_main.set_aspect("equal")
    ax_main.set_xticks([])
    ax_main.set_yticks([])
    for s in ax_main.spines.values():
        s.set_visible(False)
    rest.plot(ax=ax_main, color=C_CHINA_FILL, edgecolor="#7f7f7f", linewidth=0.45)
    hmt.plot(ax=ax_main, color=HMT_FILL, edgecolor=HMT_EDGE, linewidth=0.5)
    if len(dash):
        dash.plot(ax=ax_main, facecolor="none", edgecolor="#4a6274",
                  linewidth=0.7, ls="--")

    p = hmt[hmt["name"] == "台湾省"].geometry.iloc[0].representative_point()
    tx, ty = to_albers(125.6, 22.7)
    ax_main.annotate("台湾省", xy=(p.x, p.y), xytext=(tx, ty), fontsize=9.5,
                     fontweight="bold", color=HMT_EDGE, ha="center",
                     va="center", zorder=12,
                     arrowprops=dict(arrowstyle="-", color=HMT_FILL,
                                     lw=0.7, shrinkA=1, shrinkB=2))
    for disp, lon0, lat0, lon1, lat1 in [
            ("香港", 114.17, 22.32, 111.6, 19.6),
            ("澳门", 113.55, 22.20, 106.8, 17.4)]:
        x0, y0 = to_albers(lon0, lat0)
        x1, y1 = to_albers(lon1, lat1)
        ax_main.annotate(disp, xy=(x0, y0), xytext=(x1, y1), fontsize=9.5,
                         fontweight="bold", color=HMT_FILL, ha="center",
                         va="center", zorder=12,
                         arrowprops=dict(arrowstyle="-", color=HMT_FILL,
                                         lw=0.7, shrinkA=1, shrinkB=2))
    set_extent_from(ax_main, rest)
    add_title(ax_main, "香港、澳门与台湾在全国的位置",
              "红色为香港特别行政区、澳门特别行政区与台湾省；断续线为南海九段线")
    ax_main.set_xlabel("")
    ax_main.set_ylabel("")

    # ---- 插图一：香港 18 区
    hk = gpd.read_file(os.path.join(DATA, "boundaries", "datav", "810000_full.json"))
    inset_frame(ax_hk, 113.80, 22.13, 114.44, 22.60, 22.4)
    clip_land(ax_hk, 113.6, 21.9, 114.7, 22.8)
    hk.plot(ax=ax_hk, color="#f5b28e", edgecolor="#8e4a2f", linewidth=0.5)
    ax_hk.text(114.08, 22.48, "新界", fontsize=8.4, color=C_TEXT, ha="center")
    arrow_label(ax_hk, (114.175, 22.335), (114.315, 22.385), "九龙")
    arrow_label(ax_hk, (114.195, 22.282), (114.315, 22.30), "香港岛")
    arrow_label(ax_hk, (113.935, 22.26), (113.905, 22.185), "大屿山")
    ax_hk.text(114.03, 22.565, "深圳", fontsize=7.6, color="#8a8a8a", ha="center")
    ax_hk.set_title("香港特别行政区（18 区）", fontsize=10.5, color=C_TEXT,
                    fontweight="bold", pad=4)

    # ---- 插图二：澳门
    mc = gpd.read_file(os.path.join(DATA, "boundaries", "datav", "820000_full.json"))
    inset_frame(ax_mc, 113.42, 22.065, 113.66, 22.25, 22.15)
    clip_land(ax_mc, 113.3, 21.95, 113.8, 22.35)
    mc.plot(ax=ax_mc, color="#f5b28e", edgecolor="#8e4a2f", linewidth=0.5)
    arrow_label(ax_mc, (113.545, 22.19), (113.472, 22.222), "澳门半岛")
    arrow_label(ax_mc, (113.575, 22.158), (113.63, 22.168), "氹仔")
    arrow_label(ax_mc, (113.585, 22.122), (113.63, 22.118), "路环")
    ax_mc.text(113.465, 22.105, "横琴（珠海）", fontsize=7.6, color="#8a8a8a",
               ha="center")
    ax_mc.set_title("澳门特别行政区（8 堂区）", fontsize=10.5, color=C_TEXT,
                    fontweight="bold", pad=4)

    # ---- 插图三：台湾省
    tw = gpd.read_file(os.path.join(DATA, "boundaries", "datav", "710000.json"))
    inset_frame(ax_tw, 119.15, 21.55, 124.85, 26.25, 23.8)
    clip_land(ax_tw, 118.4, 21.2, 125.6, 26.9)
    tw.plot(ax=ax_tw, color="#f5b28e", edgecolor="#8e4a2f", linewidth=0.6)
    ax_tw.plot([119.15, 124.85], [23.44, 23.44], ls="--", color=C_CHINA,
               linewidth=0.8, zorder=7)
    ax_tw.text(123.35, 23.50, "北回归线", fontsize=7.6, color=C_CHINA,
               ha="center")
    dot_label(ax_tw, 121.56, 25.03, "台北", dx=0.09, dy=0.03)
    dot_label(ax_tw, 121.60, 23.99, "花莲", dx=0.09, dy=0.03)
    dot_label(ax_tw, 120.67, 24.15, "台中", dx=0.09, dy=0.03)
    dot_label(ax_tw, 120.20, 23.00, "台南", dx=0.09, dy=0.03)
    dot_label(ax_tw, 120.31, 22.62, "高雄", dx=0.09, dy=0.03)
    ax_tw.plot([120.96], [23.47], "^", ms=5, color="#6b4f2a", zorder=8)
    arrow_label(ax_tw, (120.96, 23.47), (119.70, 23.88), "玉山 3 952 m")
    arrow_label(ax_tw, (123.85, 25.77), (122.75, 26.02), "钓鱼岛及其附属岛屿")
    ax_tw.set_title("台湾省（台湾本岛及附属岛屿）", fontsize=10.5, color=C_TEXT,
                    fontweight="bold", pad=4)

    for a in (ax_hk, ax_mc, ax_tw, ax_main):
        a.set_xlabel("")
        a.set_ylabel("")
    fig.text(0.5, 0.012,
             "行政界线：DataV.GeoAtlas areas_v3（2021.5，仅供学习交流）；插图底图：Natural Earth 50m（公共领域）\n"
             "示意地图，不作为权属划界依据",
             ha="center", va="bottom", fontsize=8.2, color="#555555")
    fig.savefig(os.path.join(OUT, "fig2-10_港澳台位置图.png"), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 2-11
def fig2_11_hmt_scale():
    rows = [("澳门", 33.3, 68.3), ("香港", 1114, 750.3), ("台湾省", 36000, 2342)]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.4, 3.5))

    for ax, col, xlabel, log in [
            (ax1, 1, "陆地面积（km²，对数刻度）", True),
            (ax2, 2, "人口（万人）", False)]:
        names = [r[0] for r in rows]
        vals = [r[col] for r in rows]
        bars = ax.barh(names, vals, color=C_CHINA_FILL, edgecolor="#b0572f",
                       linewidth=0.8, height=0.55, zorder=3)
        if log:
            ax.set_xscale("log")
            ax.set_xlim(10, 200000)
        else:
            ax.set_xlim(0, 2900)
        for b, v in zip(bars, vals):
            txt = f"{v:,.1f}".replace(",", " ").rstrip("0").rstrip(".")
            ax.text(b.get_width() * (1.25 if log else 1.015),
                    b.get_y() + b.get_height() / 2,
                    txt, va="center", ha="left", fontsize=9.2, color=C_TEXT,
                    zorder=4)
        ax.grid(axis="x", color="#dde3e8", lw=0.7, zorder=0)
        ax.set_axisbelow(True)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color("#999999")
        ax.tick_params(axis="y", length=0, labelsize=10.5)
        ax.tick_params(axis="x", labelsize=8.5, colors="#666666")
        ax.xaxis.set_major_formatter(
            FuncFormatter(lambda v, p: f"{v:,.0f}".replace(",", " ")))
        ax.set_xlabel(xlabel, fontsize=9, color="#666666")

    fig.text(0.02, 0.985, "港澳台规模对比", fontsize=14.5, fontweight="bold",
             color=C_TEXT, va="top")
    fig.text(0.02, 0.885, "三地合计约占全国陆地面积 0.4%、人口 2.2%", fontsize=9.3,
             color="#666666", va="top")
    fig.text(0.02, 0.012,
             "数据来源：香港特区政府统计处、澳门特区政府统计暨普查局，台湾有关方面公布之 2023 年统计",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.06, 1, 0.82))
    fig.savefig(os.path.join(OUT, "fig2-11_港澳台规模对比.png"), dpi=DPI)
    plt.close(fig)


if __name__ == "__main__":
    setup()
    fig2_10_hmt_map()
    fig2_11_hmt_scale()
    print("done")
