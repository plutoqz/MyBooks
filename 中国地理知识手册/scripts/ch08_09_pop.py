# -*- coding: utf-8 -*-
"""第 8、9 章 —— 海洋与人口的图表。

fig8-1 主要岛屿与群岛分布      fig9-1 全国人口总量（1949—2025）
fig8-2 海洋生产总值历年变化    fig9-2 历次普查年龄结构
                               fig9-3 胡焕庸线与人口分布
                               fig9-4 七普民族人口
                               fig9-5 城镇化率（1949—2025）
"""
import os
import sys

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import (ALBERS, C_CHINA_FILL, C_SEA, C_TEXT, DATA, DPI, FIGURES,
                   add_title, new_map_axes, save_fig, set_extent_from, setup)
from ch03_terrain import RES_A, hillshade, load_cache, to_albers

OUT = FIGURES


def _map_base(ax, sea="#dfe8f0"):
    ax.set_facecolor(sea)
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


def _full_gdf():
    gdf = gpd.read_file(os.path.join(DATA, "boundaries", "datav",
                                     "100000_full.json"))
    prov = gdf[gdf["name"].notna() & (gdf["name"].str.len() > 0)].to_crs(ALBERS)
    dash = gdf[gdf["name"].isna() | (gdf["name"].str.len() == 0)].to_crs(ALBERS)
    return gdf, prov, dash


def _island(ax, lon, lat, name, dx=0, dy=0.45, fs=8.6):
    x, y = to_albers(lon, lat)
    ax.plot([x], [y], "o", ms=3.6, color="#8e2a1e", zorder=9)
    ax.text(x + dx, y + dy, name, fontsize=fs, color="#1a1a1a", ha="center",
            zorder=9,
            bbox=dict(boxstyle="round,pad=0.16", fc="white", ec="none",
                      alpha=0.85))


# ---------------------------------------------------------------- fig 8-1
def fig8_1_islands():
    fig, ax = new_map_axes((10.5, 10.8))
    _map_base(ax)
    gdf, prov, dash = _full_gdf()
    prov.boundary.plot(ax=ax, color="#5a5a5a", linewidth=0.28, alpha=0.5,
                       zorder=3)
    if len(dash):
        dash.plot(ax=ax, facecolor="none", edgecolor="#3b5872", linewidth=0.7,
                  ls="--", zorder=4)
    items = [
        ("长山群岛", 122.6, 39.2, 0, 0.5), ("庙岛群岛", 120.7, 38.0, 0.9, 0.2),
        ("崇明岛", 121.6, 31.7, -1.6, 0.5), ("舟山群岛", 122.2, 30.1, 1.2, 0.1),
        ("台湾岛（3.6万km²）", 121.0, 23.8, 2.4, 0),
        ("海南岛（3.4万km²）", 109.8, 19.2, 0, -0.9),
        ("东沙群岛", 116.7, 20.7, 0, 0.5), ("西沙群岛", 112.3, 16.8, 0, 0.5),
        ("中沙群岛", 114.5, 15.8, 1.0, 0), ("南沙群岛", 114.0, 10.5, 0, 0.55),
        ("钓鱼岛及其附属岛屿", 123.8, 25.8, 0, 0.5),
        ("澎湖列岛", 119.6, 23.5, -1.6, 0.2),
    ]
    for name, lo, la, dx, dy in items:
        _island(ax, lo, la, name, dx, dy,
                fs=9.0 if "万" in name else 8.2)
    set_extent_from(ax, prov)
    add_title(ax, "主要岛屿与群岛的分布",
              "面积 500 m² 以上海岛 7 300 余个；三大岛与四大群岛构成海岛地理的骨架")
    save_fig(fig, ax, "fig8-1_主要岛屿与群岛分布.png",
             footer="底图：DataV.GeoAtlas 与 AWS Terrain Tiles；点位为代表性坐标\n"
                    "示意地图，不作为权属划界依据")


# ---------------------------------------------------------------- fig 8-2
def fig8_2_oceangdp():
    years = ["2019", "2020", "2021", "2022", "2023", "2024"]
    vals = [8.94, 8.00, 9.04, 9.46, 9.91, 10.54]
    fig, ax = plt.subplots(figsize=(9.2, 4.8))
    bars = ax.bar(years, vals, color="#2e86c1", width=0.55, zorder=3)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.12, f"{v:.2f}",
                ha="center", fontsize=9.4, color=C_TEXT, zorder=4)
    ax.axhline(10, color="#c0392b", lw=1.1, ls="--")
    ax.text(5.42, 10.12, "突破 10 万亿", fontsize=8.6, color="#c0392b",
            ha="right")
    ax.set_ylim(0, 12.2)
    ax.grid(axis="y", color="#dde3e8", lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#999999")
    ax.spines["left"].set_color("#999999")
    ax.tick_params(labelsize=9)
    ax.set_ylabel("海洋生产总值（万亿元）", fontsize=9, color="#666666")
    fig.text(0.02, 0.982, "全国海洋生产总值（2019—2024）", fontsize=14.5,
             fontweight="bold", color=C_TEXT, va="top")
    fig.text(0.02, 0.952, "2024 年突破 10 万亿元，约占 GDP 的 7.8%", fontsize=9.3,
             color="#666666", va="top")
    fig.text(0.02, 0.012,
             "数据来源：自然资源部《中国海洋经济统计公报》（2020—2025 年发布）",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 0.94))
    fig.savefig(os.path.join(OUT, "fig8-2_海洋生产总值.png"), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 9-1
def fig9_1_population():
    pairs = [(1949, 5.42), (1954, 6.03), (1959, 6.72), (1964, 6.98),
             (1969, 8.07), (1974, 9.09), (1979, 9.75), (1984, 10.44),
             (1989, 11.27), (1994, 11.99), (1999, 12.58), (2004, 13.00),
             (2009, 13.35), (2014, 13.68), (2019, 14.10), (2021, 14.13),
             (2023, 14.10), (2024, 14.08), (2025, 14.05)]
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    fig, ax = plt.subplots(figsize=(10.0, 5.2))
    ax.plot(xs, ys, color="#c0392b", lw=2.2, marker="o", ms=4, zorder=3)
    ax.fill_between(xs, ys, 0, color="#f5c6aa", alpha=0.55, zorder=2)
    ax.annotate("2021 年 14.13 亿：峰值", xy=(2021, 14.13), xytext=(1985, 14.6),
                fontsize=9, color="#8e2a1e",
                arrowprops=dict(arrowstyle="->", color="#8e2a1e", lw=0.9))
    ax.annotate("2022 年起连续负增长", xy=(2024, 14.08), xytext=(1996, 12.3),
                fontsize=9, color="#555555",
                arrowprops=dict(arrowstyle="->", color="#888888", lw=0.9))
    ax.set_xlim(1946, 2028)
    ax.set_ylim(0, 15.5)
    ax.grid(axis="y", color="#dde3e8", lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#999999")
    ax.spines["left"].set_color("#999999")
    ax.set_ylabel("年末总人口（亿人）", fontsize=9, color="#666666")
    fig.text(0.02, 0.982, "中国人口总量（1949—2025）", fontsize=14.5,
             fontweight="bold", color=C_TEXT, va="top")
    fig.text(0.02, 0.952, "从 5.4 亿到 14.05 亿；2025 年末 140 489 万人，比上年减少 339 万",
             fontsize=9.3, color="#666666", va="top")
    fig.text(0.02, 0.012,
             "数据来源：国家统计局历年国民经济和社会发展统计公报（逢 0/5 年为普查修正值口径）",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 0.94))
    fig.savefig(os.path.join(OUT, "fig9-1_人口总量变化.png"), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 9-2
def fig9_2_age():
    censuses = ["1982 二普后", "1990 四普", "2000 五普", "2010 六普", "2020 七普"]
    young = [33.59, 27.69, 22.89, 16.60, 17.95]
    work = [61.50, 66.74, 70.15, 74.53, 68.55]
    old = [4.91, 5.57, 6.96, 8.87, 13.50]
    fig, ax = plt.subplots(figsize=(9.6, 5.0))
    x = np.arange(len(censuses))
    ax.bar(x, young, 0.55, label="0—14 岁", color="#5dade2", zorder=3)
    ax.bar(x, work, 0.55, bottom=young, label="15—64 岁", color="#a9dfbf",
           zorder=3)
    ax.bar(x, old, 0.55, bottom=np.array(young) + np.array(work), label="65 岁及以上",
           color="#c0392b", zorder=3)
    for i in range(len(censuses)):
        ax.text(i, young[i] + work[i] + old[i] + 1.5,
                f"老龄化 {old[i]:.1f}%", ha="center", fontsize=8.6,
                color="#8e2a1e")
    ax.set_xticks(x, censuses, fontsize=9)
    ax.set_ylim(0, 112)
    ax.set_ylabel("占总人口比重（%）", fontsize=9, color="#666666")
    ax.grid(axis="y", color="#dde3e8", lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#999999")
    ax.spines["left"].set_color("#999999")
    ax.legend(loc="upper right", fontsize=8.8, framealpha=0.92,
              edgecolor="#cccccc", ncol=3)
    fig.text(0.02, 0.982, "历次人口普查的年龄结构", fontsize=14.5,
             fontweight="bold", color=C_TEXT, va="top")
    fig.text(0.02, 0.952, "少子化与老龄化同步加深：七普 65 岁及以上人口占 13.5%",
             fontsize=9.3, color="#666666", va="top")
    fig.text(0.02, 0.012, "数据来源：国家统计局历次全国人口普查公报", fontsize=8,
             color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 0.94))
    fig.savefig(os.path.join(OUT, "fig9-2_年龄结构演变.png"), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 9-3
def fig9_3_hu():
    fig, ax = new_map_axes((10.5, 10.8))
    _map_base(ax)
    gdf, prov, dash = _full_gdf()
    prov.plot(ax=ax, color=C_CHINA_FILL, edgecolor="#7f7f7f", linewidth=0.4,
              zorder=3)
    if len(dash):
        dash.plot(ax=ax, facecolor="none", edgecolor="#4a6274", linewidth=0.7,
                  ls="--", zorder=4)
    xs, ys = zip(*[to_albers(127.53, 50.24), to_albers(110.0, 41.2),
                   to_albers(104.0, 34.5), to_albers(98.50, 25.02)])
    ax.plot(xs, ys, color="#1a1a1a", lw=2.4, ls=(0, (7, 4)), zorder=6)
    x, y = to_albers(116.0, 47.6)
    ax.text(x, y, "胡焕庸线\n（黑河—腾冲）", fontsize=10, fontweight="bold",
            color="#1a1a1a", ha="center", va="center", zorder=8, linespacing=1.5,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#999999",
                      alpha=0.9))
    x, y = to_albers(117.5, 30.0)
    ax.text(x, y, "东南侧\n约 43% 国土\n约 94% 人口", fontsize=10.5,
            fontweight="bold", color="#8e2a1e", ha="center", va="center",
            zorder=8, linespacing=1.6,
            bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#c0392b",
                      alpha=0.92))
    x, y = to_albers(90.5, 38.0)
    ax.text(x, y, "西北侧\n约 57% 国土\n约 6% 人口", fontsize=10.5,
            fontweight="bold", color="#1d5a7a", ha="center", va="center",
            zorder=8, linespacing=1.6,
            bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#1d6b8a",
                      alpha=0.92))
    for t, lo, la in [("黑河", 127.53, 50.9), ("腾冲", 98.50, 24.2)]:
        x, y = to_albers(lo, la)
        ax.plot(*to_albers(t == "腾冲" and 98.50 or 127.53, t == "腾冲" and 25.02 or 50.24),
                "o", ms=4.5, color="#1a1a1a", zorder=9)
        ax.text(x, y, t, fontsize=9.2, color="#1a1a1a", ha="center", zorder=9)
    set_extent_from(ax, prov)
    add_title(ax, "胡焕庸线与人口分布",
              "1935 年地理学家胡焕庸划出的这条线，87 年后依然有效")
    save_fig(fig, ax, "fig9-3_胡焕庸线.png",
             footer="底图：DataV.GeoAtlas 与 AWS Terrain Tiles；比例按近年人口数据更新\n"
                    "示意地图，不作为权属划界依据")


# ---------------------------------------------------------------- fig 9-4
def fig9_4_ethnic():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.0, 5.2),
                                   gridspec_kw={"width_ratios": [1, 1.7]})
    b = ax1.bar(["汉族", "少数民族\n合计"], [128631, 12547], color=["#c0392b", "#2e86c1"],
                width=0.5, zorder=3)
    for bb, v, pct in zip(b, [128631, 12547], ["91.11%", "8.89%"]):
        ax1.text(bb.get_x() + bb.get_width() / 2, v + 2500,
                 f"{v:,} 万人\n（{pct}）".replace(",", " "), ha="center",
                 fontsize=9.4, color=C_TEXT, zorder=4)
    ax1.set_ylim(0, 155000)
    ax1.grid(axis="y", color="#dde3e8", lw=0.7, zorder=0)
    ax1.set_axisbelow(True)
    for s in ("top", "right"):
        ax1.spines[s].set_visible(False)
    ax1.spines["bottom"].set_color("#999999")
    ax1.spines["left"].set_color("#999999")
    ax1.tick_params(labelsize=9.2)
    ax1.set_ylabel("人口（万人）", fontsize=9, color="#666666")
    ax1.set_title("汉族与少数民族", fontsize=11, color=C_TEXT)

    rows = [("壮族", 19569), ("维吾尔族", 11775), ("回族", 11378),
            ("苗族", 11068), ("满族", 10423), ("彝族", 9830),
            ("土家族", 9588), ("藏族", 7061), ("蒙古族", 6290), ("侗族", 3496)]
    rows = sorted(rows, key=lambda r: r[1])
    ax2.barh([r[0] for r in rows], [r[1] for r in rows], color="#2e86c1",
             height=0.6, zorder=3)
    for i, (n, v) in enumerate(rows):
        ax2.text(v + 220, i, f"{v:,}".replace(",", " "), va="center",
                 fontsize=8.8, color=C_TEXT, zorder=4)
    ax2.set_xlim(0, 22500)
    ax2.grid(axis="x", color="#dde3e8", lw=0.7, zorder=0)
    ax2.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax2.spines[s].set_visible(False)
    ax2.spines["bottom"].set_color("#999999")
    ax2.tick_params(axis="y", length=0, labelsize=9.2)
    ax2.tick_params(axis="x", labelsize=8.5, colors="#666666")
    ax2.set_title("人口最多的 10 个少数民族", fontsize=11, color=C_TEXT)

    fig.text(0.02, 0.982, "第七次人口普查的民族构成（2020）", fontsize=14.5,
             fontweight="bold", color=C_TEXT, va="top")
    fig.text(0.02, 0.952, "55 个少数民族合计 12 547 万人，占 8.89%", fontsize=9.3,
             color="#666666", va="top")
    fig.text(0.02, 0.012, "数据来源：国家统计局《第七次全国人口普查公报》（2021 年 5 月）",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 0.93))
    fig.savefig(os.path.join(OUT, "fig9-4_民族构成.png"), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 9-5
def fig9_5_urban():
    pairs = [(1949, 10.6), (1960, 19.8), (1978, 17.9), (1990, 26.4),
             (2000, 36.2), (2010, 49.9), (2020, 63.9), (2024, 67.0),
             (2025, 67.9)]
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    fig, ax = plt.subplots(figsize=(9.8, 5.0))
    ax.plot(xs, ys, color="#7d3c98", lw=2.2, marker="o", ms=4.5, zorder=3)
    ax.fill_between(xs, ys, 0, color="#d7bde2", alpha=0.5, zorder=2)
    ax.annotate("1978 年改革开放起点：17.9%", xy=(1978, 17.9),
                xytext=(1952, 33), fontsize=9, color="#555555",
                arrowprops=dict(arrowstyle="->", color="#888888", lw=0.9))
    ax.annotate("2011 年城镇人口首次过半", xy=(2010, 49.9), xytext=(1966, 55),
                fontsize=9, color="#555555",
                arrowprops=dict(arrowstyle="->", color="#888888", lw=0.9))
    ax.set_xlim(1946, 2028)
    ax.set_ylim(0, 78)
    ax.grid(axis="y", color="#dde3e8", lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#999999")
    ax.spines["left"].set_color("#999999")
    ax.set_ylabel("常住人口城镇化率（%）", fontsize=9, color="#666666")
    fig.text(0.02, 0.982, "中国城镇化率（1949—2025）", fontsize=14.5,
             fontweight="bold", color=C_TEXT, va="top")
    fig.text(0.02, 0.952, "2025 年末城镇化率 67.89%，城镇常住人口 95 380 万",
             fontsize=9.3, color="#666666", va="top")
    fig.text(0.02, 0.012,
             "数据来源：国家统计局历年统计公报与人口普查（逢普查年取普查口径）",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 0.94))
    fig.savefig(os.path.join(OUT, "fig9-5_城镇化率.png"), dpi=DPI)
    plt.close(fig)


if __name__ == "__main__":
    setup()
    fig8_1_islands()
    fig8_2_oceangdp()
    fig9_1_population()
    fig9_2_age()
    fig9_3_hu()
    fig9_4_ethnic()
    fig9_5_urban()
    print("ch08-09 done")
