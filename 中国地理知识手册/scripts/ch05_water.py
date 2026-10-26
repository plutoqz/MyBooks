# -*- coding: utf-8 -*-
"""第 5 章 河流与湖泊 —— 水系图与统计图。

fig5-1 全国主要水系图        fig5-5 长江与黄河干流纵剖面
fig5-2 主要河流长度对比      fig5-6 主要湖泊面积对比
fig5-3 长江流域水系图        fig5-7 南水北调三线示意
fig5-4 黄河流域水系图
底图：AWS Terrain 山体阴影（复用缓存）；河流：Natural Earth 50m。
"""
import os
import sys

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Polygon as MplPolygon
from shapely.geometry import Polygon as ShPolygon

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import (ALBERS, C_SEA, C_TEXT, DATA, DPI, FIGURES, add_title,
                   new_map_axes, save_fig, set_extent_from, setup)
from geo_features import YELLOW_BASIN, YANGTZE_BASIN
from ch03_terrain import RES_A, hillshade, load_cache, to_albers

WATER = "#2e86c1"
WATER_LT = "#aed6f1"
LAKE = "#2e86c1"


def _dem_base(ax):
    dem, minx, maxy = load_cache()
    h, w = dem.shape
    extent = (minx, minx + w * RES_A, maxy - h * RES_A, maxy)
    sh = hillshade(dem)
    rgba = np.zeros((h, w, 4))
    f = 0.55 + 0.45 * sh
    rgba[:, :, 0], rgba[:, :, 1], rgba[:, :, 2] = 0.93 * f, 0.91 * f, 0.87 * f
    rgba[:, :, 3] = np.where(np.isnan(dem), 0.0, 1.0)
    ax.imshow(rgba, extent=extent, origin="upper", interpolation="bilinear",
              zorder=1)


def _borders(ax, z=3):
    gdf = gpd.read_file(os.path.join(DATA, "boundaries", "datav",
                                     "100000_full.json"))
    prov = gdf[gdf["name"].notna() & (gdf["name"].str.len() > 0)].to_crs(ALBERS)
    dash = gdf[gdf["name"].isna() | (gdf["name"].str.len() == 0)].to_crs(ALBERS)
    prov.boundary.plot(ax=ax, color="#6a6a6a", linewidth=0.28, alpha=0.55, zorder=z)
    if len(dash):
        dash.plot(ax=ax, facecolor="none", edgecolor="#3b5872", linewidth=0.7,
                  ls="--", zorder=z + 1)
    return gdf, prov, dash


def _load_rivers():
    riv = gpd.read_file(os.path.join(DATA, "boundaries", "natural_earth",
                                     "ne_50m_rivers_lake_centerlines",
                                     "ne_50m_rivers_lake_centerlines.shp"))
    lak = gpd.read_file(os.path.join(DATA, "boundaries", "natural_earth",
                                     "ne_50m_lakes", "ne_50m_lakes.shp"))
    return riv.to_crs(ALBERS), lak.to_crs(ALBERS)


def _mark(ax, name, lon, lat, dx=0, dy=0.35, fs=8.2, color="#1a1a1a"):
    x, y = to_albers(lon, lat)
    ax.plot([x], [y], "o", ms=3.6, color="#8e2a1e", zorder=9)
    ax.text(x + dx, y + dy, name, fontsize=fs, color=color, ha="center",
            va="bottom", zorder=9)


def _river_label(ax, lon, lat, text, rot=0, fs=8.6, color="#1b4f72"):
    x, y = to_albers(lon, lat)
    ax.text(x, y, text, fontsize=fs, color=color, rotation=rot, ha="center",
            va="center", zorder=8,
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.78))


# ---------------------------------------------------------------- fig 5-1
def fig5_1_rivers():
    fig, ax = new_map_axes((10.5, 10.8))
    ax.set_facecolor(C_SEA)
    _dem_base(ax)
    gdf, prov, dash = _borders(ax)
    riv, lak = _load_rivers()
    bbox = prov.total_bounds
    view = riv.cx[bbox[0]:bbox[2], bbox[1]:bbox[3]]
    view.plot(ax=ax, color=WATER, linewidth=view["scalerank"].map(
        lambda s: 0.9 if s <= 6 else 0.55), zorder=6)
    lv = lak.cx[bbox[0]:bbox[2], bbox[1]:bbox[3]]
    lv.plot(ax=ax, color=LAKE, alpha=0.85, zorder=6)

    labels = [
        ("长江", 116.0, 30.6, -8), ("黄河", 110.5, 36.3, -12),
        ("黑龙江", 126.5, 50.3, -18), ("松花江", 128.5, 45.0, -12),
        ("珠江", 112.8, 23.1, -5), ("塔里木河", 84.0, 41.0, -3),
        ("雅鲁藏布江", 92.5, 29.4, 8), ("澜沧江", 100.0, 27.5, -70),
        ("怒江", 98.6, 27.0, -70), ("淮河", 117.5, 32.6, -5),
        ("海河", 116.8, 38.8, 0), ("辽河", 122.5, 42.3, -30),
        ("京杭运河", 116.5, 34.5, -88),
    ]
    for t, lo, la, rot in labels:
        _river_label(ax, lo, la, t, rot=rot)
    for t, lo, la in [("青海湖", 100.1, 36.9), ("鄱阳湖", 116.3, 29.2),
                      ("洞庭湖", 112.6, 29.2), ("太湖", 120.2, 31.3)]:
        _river_label(ax, lo, la, t, fs=7.6)
    set_extent_from(ax, prov)
    add_title(ax, "全国主要水系", "外流河与内流河并存；多数河流自西向东注入太平洋")
    save_fig(fig, ax, "fig5-1_全国主要水系图.png",
             footer="河流线划：Natural Earth 50m（公共领域），线宽按等级示意；底图：AWS Terrain Tiles\n"
                    "示意地图，不作为权属划界依据")


# ---------------------------------------------------------------- fig 5-2
def fig5_2_compare():
    rows = [("长江", 6300), ("黄河", 5464), ("黑龙江（全长）", 4440),
            ("珠江", 2320), ("塔里木河（最大内流河）", 2179),
            ("雅鲁藏布江（境内）", 2057), ("怒江（境内）", 2013),
            ("澜沧江（境内）", 2139), ("辽河", 1345), ("海河", 1090),
            ("淮河", 1000)]
    rows = sorted(rows, key=lambda r: r[1])
    fig, ax = plt.subplots(figsize=(9.4, 7.0))
    names = [r[0] for r in rows]; vals = [r[1] for r in rows]
    colors = ["#c0392b" if n in ("长江", "黄河") else "#7fa8c9" for n in names]
    bars = ax.barh(names, vals, color=colors, height=0.62, zorder=3)
    for b, v in zip(bars, vals):
        ax.text(b.get_width() + 60, b.get_y() + b.get_height() / 2,
                f"{v:,} km".replace(",", " "), va="center", fontsize=8.8,
                color=C_TEXT, zorder=4)
    ax.set_xlim(0, 7200)
    ax.grid(axis="x", color="#dde3e8", lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#999999")
    ax.tick_params(axis="y", length=0, labelsize=9.2)
    ax.tick_params(axis="x", labelsize=8.5, colors="#666666")
    ax.set_xlabel("河流长度（km）", fontsize=9, color="#666666")
    ax.legend(handles=[Patch(fc="#c0392b", label="中国两大母亲河"),
                       Patch(fc="#7fa8c9", label="其他主要河流")],
              loc="lower right", fontsize=8.8, framealpha=0.92,
              edgecolor="#cccccc")
    fig.text(0.02, 0.982, "中国主要河流长度对比", fontsize=14.5, fontweight="bold",
             color=C_TEXT, va="top")
    fig.text(0.02, 0.955, "以中国境内或通行口径为准；国际河流标注“全长”或“境内”",
             fontsize=9.3, color="#666666", va="top")
    fig.text(0.02, 0.012, "数据来源：水利部及通行教材口径（约数）", fontsize=8,
             color="#555555")
    fig.tight_layout(rect=(0, 0.045, 1, 0.935))
    fig.savefig(os.path.join(FIGURES, "fig5-2_主要河流长度对比.png"), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- 5-3 / 5-4
def basin_map(fname, title, subtitle, basin_poly, stem_names, marks, divs,
              trib_labels, footer, special=None):
    fig, ax = new_map_axes((11.8, 6.3))
    ax.set_facecolor(C_SEA)
    _dem_base(ax)
    gdf, prov, dash = _borders(ax)
    riv, lak = _load_rivers()
    poly = ShPolygon(basin_poly)
    basin_g = gpd.GeoSeries([poly], crs="EPSG:4326").to_crs(ALBERS)
    basin_g.plot(ax=ax, facecolor="#2471a3", alpha=0.10, edgecolor="#2471a3",
                 lw=1.4, zorder=4)
    sub = riv[riv.intersects(basin_g.union_all())]
    stem = sub[sub["name"].isin(stem_names) if stem_names else False]
    rest = sub[~sub.index.isin(stem.index)]
    rest.plot(ax=ax, color=WATER_LT, linewidth=0.5, zorder=5)
    stem.plot(ax=ax, color="#1b4f72", linewidth=1.7, zorder=6)
    lk = lak[lak.intersects(basin_g.union_all())]
    lk.plot(ax=ax, color=LAKE, alpha=0.85, zorder=5)
    for t, lo, la, rot in trib_labels:
        _river_label(ax, lo, la, t, rot=rot, fs=8.0)
    for t, lo, la, dx, dy in marks:
        _mark(ax, t, lo, la, dx=dx, dy=dy)
    for lo, la, t in divs:
        x, y = to_albers(lo, la)
        ax.axhline(y, color="#8e2a1e", lw=0, zorder=1)
        ax.plot([x], [y], "s", ms=5, color="#8e2a1e", zorder=9)
        ax.text(x, y + 130000, t, fontsize=8.2, color="#8e2a1e", ha="center",
                va="bottom", zorder=9,
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none",
                          alpha=0.8))
    if special:
        special(ax)
    set_extent_from(ax, basin_g)
    add_title(ax, title, subtitle)
    save_fig(fig, ax, fname, footer=footer)


def fig5_3_yangtze():
    marks = [("三峡工程", 111.00, 30.82, -0.35, 0.62), ("上海", 121.47, 31.23, 0.2, 0.3),
             ("重庆", 106.55, 29.56, 0.2, 0.3), ("武汉", 114.31, 30.59, 0.2, 0.3)]
    divs = [(111.29, 30.69, "宜昌（上游⇌中游）"), (116.26, 29.73, "湖口（中游⇌下游）")]
    trib = [("雅砻江", 101.8, 27.8, -75), ("岷江", 103.9, 29.3, -80),
            ("嘉陵江", 106.5, 30.4, -60), ("乌江", 107.2, 27.6, -80),
            ("汉江", 112.0, 32.3, -35), ("湘江", 112.8, 27.6, -80),
            ("赣江", 115.6, 27.9, -80), ("通天河", 94.5, 34.5, 5),
            ("金沙江", 100.5, 26.8, -65)]
    basin_map(
        "fig5-3_长江流域水系图.png", "长江流域水系",
        "干流全长约 6 300 km，流域面积约 180 万 km²；宜昌、湖口划分上、中、下游",
        YANGTZE_BASIN,
        ["Yangtze", "Chang Jiang", "Tongtian"],
        marks, divs, trib,
        "河流线划：Natural Earth 50m；流域范围为示意勾绘；底图：AWS Terrain Tiles\n"
        "示意地图，不作为权属划界依据")


def fig5_4_yellow():
    marks = [("小浪底", 112.45, 34.90, -0.55, 0.45), ("兰州", 103.83, 36.06, 0.2, 0.3),
             ("郑州", 113.63, 34.75, 0.55, -0.85)]
    divs = [(111.20, 40.28, "河口镇（上游⇌中游）"), (113.32, 34.92, "桃花峪（中游⇌下游）")]

    def special(ax):
        # “地上悬河”河段高亮
        seg = [(111.2, 35.2), (113.0, 34.9), (115.0, 35.4), (117.0, 36.2), (118.6, 37.2)]
        xs, ys = zip(*[to_albers(lo, la) for lo, la in seg])
        ax.plot(xs, ys, color="#c0392b", lw=3.0, alpha=0.75, zorder=7)
        ax.text(*to_albers(114.8, 35.9), "下游“地上悬河”", fontsize=8.5,
                color="#c0392b", rotation=20, ha="center", zorder=9,
                bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.85))

    trib = [("湟水", 101.7, 36.4, -20), ("洮河", 103.4, 35.2, -60),
            ("汾河", 112.2, 37.2, -85), ("渭河", 107.9, 34.75, -5),
            ("无定河", 109.5, 37.8, 5), ("宁夏平原灌区", 106.2, 38.4, 0)]
    basin_map(
        "fig5-4_黄河流域水系图.png", "黄河流域水系",
        "干流全长约 5 464 km，流域面积约 79.5 万 km²；河口镇、桃花峪划分上、中、下游",
        YELLOW_BASIN, ["Huang"],
        marks, divs, trib,
        "河流线划：Natural Earth 50m；流域范围为示意勾绘；底图：AWS Terrain Tiles\n"
        "示意地图，不作为权属划界依据", special=special)


# ---------------------------------------------------------------- fig 5-5
def fig5_5_profiles():
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.4))
    cz = [(0, 5400, "各拉丹冬"), (830, 4500, "沱沱河沿"), (2100, 3500, "玉树"),
          (2300, 1850, "石鼓"), (3460, 260, "宜宾"), (3900, 160, "重庆"),
          (4510, 44, "宜昌"), (5350, 18, "武汉"), (5800, 10, "湖口"),
          (6100, 5, "南京"), (6300, 0, "入海口")]
    hz = [(0, 4500, "约古宗列盆地"), (500, 4290, "玛多"), (2200, 1510, "兰州"),
          (3460, 834, "河口镇"), (4190, 387, "龙门"), (4470, 330, "潼关"),
          (4720, 92, "桃花峪"), (5450, 8, "利津"), (5464, 0, "入海口")]
    for ax, data, name, divs in [
            (axes[0], cz, "长江干流纵剖面（约 6 300 km）", [(4510, "宜昌")]),
            (axes[1], hz, "黄河干流纵剖面（约 5 464 km）", [(3460, "河口镇"), (4720, "桃花峪")])]:
        d = [p[0] for p in data]; e = [p[1] for p in data]
        ax.fill_between(d, e, 0, color="#d3a670", lw=0)
        ax.plot(d, e, color="#8a5a2a", lw=1.1, marker="o", ms=3)
        ax.set_facecolor("#eaf2f8")
        ax.set_ylim(0, 6200)
        ax.set_xlim(0, data[-1][0])
        ax.set_title(name, fontsize=11.5, color=C_TEXT, loc="left")
        ax.grid(axis="y", color="#dde3e8", lw=0.7)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.set_xlabel("距河源里程（km）", fontsize=9)
        for dd, lab in divs:
            ax.axvline(dd, color="#8e2a1e", lw=0.9, ls=":")
            ax.text(dd, 5900, lab, fontsize=8, ha="center", color="#8e2a1e")
        for dd, ee, lab in data:
            if lab in ("石鼓", "宜宾", "沱沱河沿", "兰州", "龙门", "潼关", "玛多", "湖口"):
                ax.annotate(lab, (dd, ee), textcoords="offset points",
                            xytext=(0, 8), fontsize=7.2, ha="center",
                            color="#555555")
    axes[0].set_ylabel("海拔（m）", fontsize=9)
    fig.text(0.02, 0.012,
             "示意剖面：按代表性水文/城市站点高程与里程勾绘，不按等比绘图",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(os.path.join(FIGURES, "fig5-5_长江黄河纵剖面.png"), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 5-6
def fig5_6_lakes():
    rows = [("青海湖（咸）", 4583), ("鄱阳湖", 3150), ("洞庭湖", 2625),
            ("色林错（咸）", 2391), ("呼伦湖（半咸）", 2339), ("太湖", 2338),
            ("纳木错（咸）", 2020), ("洪泽湖", 1576), ("巢湖", 780),
            ("南四湖", 1266)]
    rows = sorted(rows, key=lambda r: r[1])
    fig, ax = plt.subplots(figsize=(9.2, 6.4))
    names = [r[0] for r in rows]; vals = [r[1] for r in rows]
    colors = ["#8e7cc3" if ("咸" in n or "半咸" in n) else "#5dade2" for n in names]
    bars = ax.barh(names, vals, color=colors, height=0.6, zorder=3)
    for b, v in zip(bars, vals):
        ax.text(b.get_width() + 55, b.get_y() + b.get_height() / 2,
                f"{v:,} km²".replace(",", " "), va="center", fontsize=8.8,
                color=C_TEXT, zorder=4)
    ax.set_xlim(0, 5300)
    ax.grid(axis="x", color="#dde3e8", lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#999999")
    ax.tick_params(axis="y", length=0, labelsize=9.2)
    ax.tick_params(axis="x", labelsize=8.5, colors="#666666")
    ax.set_xlabel("湖泊面积（km²）", fontsize=9, color="#666666")
    ax.legend(handles=[Patch(fc="#5dade2", label="淡水湖（外流区）"),
                       Patch(fc="#8e7cc3", label="咸水湖 / 半咸水湖（内流区或高原）")],
              loc="lower right", fontsize=8.8, framealpha=0.92, edgecolor="#cccccc")
    fig.text(0.02, 0.982, "中国主要湖泊面积对比", fontsize=14.5, fontweight="bold",
             color=C_TEXT, va="top")
    fig.text(0.02, 0.955, "湖泊面积随水位波动，取常年参考值（约数）", fontsize=9.3,
             color="#666666", va="top")
    fig.text(0.02, 0.012, "数据来源：水利部、中国科学院南京地理与湖泊研究所公开数据（约数）",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.045, 1, 0.935))
    fig.savefig(os.path.join(FIGURES, "fig5-6_主要湖泊面积对比.png"), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 5-7
def fig5_7_snwd():
    fig, ax = new_map_axes((9.8, 10.4))
    ax.set_facecolor(C_SEA)
    _dem_base(ax)
    gdf, prov, dash = _borders(ax)
    lines = {
        "东线（2013 年全线通水）": ([(119.42, 32.39), (116.59, 35.41),
                                (116.36, 37.44), (117.20, 39.08)], "#1f618d", "-"),
        "中线（2014 年通水）": ([(111.51, 32.54), (113.63, 34.75),
                              (114.51, 38.04), (116.41, 39.90)], "#c0392b", "-"),
        "西线（规划）": ([(100.8, 30.0), (102.0, 31.5),
                      (102.5, 35.0)], "#7d6608", "--"),
    }
    for label, (pts, c, ls) in lines.items():
        xs, ys = zip(*[to_albers(lo, la) for lo, la in pts])
        ax.plot(xs, ys, color=c, lw=2.6, ls=ls, zorder=7,
                solid_capstyle="round")
        mid = pts[len(pts) // 2]
        x, y = to_albers(*mid)
        ax.annotate(label, xy=(x, y), xytext=(x - 700000, y - 260000),
                    fontsize=9, color=c, zorder=9,
                    arrowprops=dict(arrowstyle="-", color=c, lw=0.7),
                    bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=c,
                              lw=0.8, alpha=0.92))
    for t, lo, la in [("丹江口水库", 111.51, 32.54), ("江都枢纽", 119.42, 32.39)]:
        _mark(ax, t, lo, la)
    set_extent_from(ax, prov)
    add_title(ax, "南水北调工程三线示意", "东、中两线已通水，西线尚在论证；线路为示意勾绘")
    save_fig(fig, ax, "fig5-7_南水北调三线示意.png",
             footer="线路为示意勾绘；底图：AWS Terrain Tiles；投影：Albers 等积圆锥\n"
                    "示意地图，不作为权属划界依据")


if __name__ == "__main__":
    setup()
    fig5_1_rivers()
    fig5_2_compare()
    fig5_3_yangtze()
    fig5_4_yellow()
    fig5_5_profiles()
    fig5_6_lakes()
    fig5_7_snwd()
    print("ch05 water done")
