# -*- coding: utf-8 -*-
"""第 6、7 章 —— 统计图表。

fig6-1 三调地类构成          fig7-1 中国主要自然带分布（示意）
fig6-2 耕地面积变化          fig7-2 森林覆盖率变化（1949—2023）
fig6-3 分省森林覆盖率前十二  fig7-3 主要地震带与代表性强震
fig6-4 主要矿产品产量世界占比
"""
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Polygon as MplPolygon

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import C_SEA, C_TEXT, DATA, DPI, FIGURES, add_title, new_map_axes, \
    save_fig, set_extent_from, setup

OUT = FIGURES


def barh_generic(fname, title, subtitle, rows, xlabel, footer, colors,
                 figsize=(9.6, 6.4), fmt="{:,.0f}", legend=None):
    rows = sorted(rows, key=lambda r: r[1])
    fig, ax = plt.subplots(figsize=figsize)
    names = [r[0] for r in rows]
    vals = [r[1] for r in rows]
    bars = ax.barh(names, vals, color=colors(rows) if callable(colors) else colors,
                   height=0.62, zorder=3)
    for b, v in zip(bars, vals):
        ax.text(b.get_width() + max(vals) * 0.012, b.get_y() + b.get_height() / 2,
                fmt.format(v).replace(",", " "), va="center", fontsize=8.8,
                color=C_TEXT, zorder=4)
    ax.set_xlim(0, max(vals) * 1.14)
    ax.grid(axis="x", color="#dde3e8", lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#999999")
    ax.tick_params(axis="y", length=0, labelsize=9.2)
    ax.tick_params(axis="x", labelsize=8.5, colors="#666666")
    ax.set_xlabel(xlabel, fontsize=9, color="#666666")
    if legend:
        ax.legend(handles=legend, loc="lower right", fontsize=8.8,
                  framealpha=0.92, edgecolor="#cccccc")
    fig.text(0.02, 0.982, title, fontsize=14.5, fontweight="bold", color=C_TEXT,
             va="top")
    fig.text(0.02, 0.952, subtitle, fontsize=9.3, color="#666666", va="top")
    fig.text(0.02, 0.012, footer, fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.045, 1, 0.935))
    fig.savefig(os.path.join(OUT, fname), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 6-1
def fig6_1_land():
    rows = [("耕地", 12786), ("园地", 2020), ("林地", 28413), ("草地", 26457),
            ("湿地", 2346), ("城镇村及工矿用地", 3531), ("交通运输用地", 981),
            ("水域及水利设施用地", 3629)]
    palette = {"耕地": "#c0392b", "园地": "#e59866", "林地": "#1e8449",
               "草地": "#a9dfbf", "湿地": "#5dade2", "城镇村及工矿用地": "#7f8c8d",
               "交通运输用地": "#b2babb", "水域及水利设施用地": "#2e86c1"}

    def colors(rs):
        return [palette[r[0]] for r in rs]
    barh_generic(
        "fig6-1_三调地类构成.png", "第三次全国国土调查：主要地类面积",
        "2019 年末口径；8 类主要地类合计约 80 亿亩，其余为未利用地等",
        rows, "面积（万公顷）",
        "数据来源：自然资源部《第三次全国国土调查主要数据公报》（2021 年发布）",
        colors, figsize=(9.8, 6.6))


# ---------------------------------------------------------------- fig 6-2b
def fig6_2_cropland():
    rows = [("二调（2009 年末）", 20.31), ("三调（2019 年末）", 19.18),
            ("2023 年度变更调查", 19.29)]
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    names = [r[0] for r in rows]
    vals = [r[1] for r in rows]
    colors = ["#8fa8bf", "#c0392b", "#1e8449"]
    bars = ax.bar(names, vals, color=colors, width=0.52, zorder=3)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.06, f"{v:.2f}",
                ha="center", fontsize=10, color=C_TEXT, zorder=4)
    ax.axhline(18, color="#c0392b", lw=1.2, ls="--")
    ax.text(2.38, 18.08, "18 亿亩红线", fontsize=8.6, color="#c0392b",
            ha="right")
    ax.set_ylim(17.5, 21)
    ax.grid(axis="y", color="#dde3e8", lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#999999")
    ax.spines["left"].set_color("#999999")
    ax.tick_params(labelsize=9)
    ax.set_ylabel("全国耕地面积（亿亩）", fontsize=9, color="#666666")
    fig.text(0.02, 0.982, "全国耕地面积：两次调查与最新变更", fontsize=14.5,
             fontweight="bold", color=C_TEXT, va="top")
    fig.text(0.02, 0.952, "2010 年代耕地净减少约 1.1 亿亩；2021 年起连续三年净增加",
             fontsize=9.3, color="#666666", va="top")
    fig.text(0.02, 0.012,
             "数据来源：第二次、第三次全国国土调查主要数据公报，自然资源部 2023 年度全国国土变更调查",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 0.94))
    fig.savefig(os.path.join(OUT, "fig6-2_耕地面积变化.png"), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 6-3
def fig6_3_forest():
    rows = [("福建", 66.8), ("江西", 63.1), ("广西", 62.5), ("浙江", 61.2),
            ("海南", 62.1), ("广东", 58.7), ("湖南", 59.0), ("云南", 55.3),
            ("贵州", 63.3), ("黑龙江", 47.3), ("全国平均", 24.0), ("内蒙古", 23.0),
            ("新疆", 5.0), ("青海", 7.5)]
    rows = sorted(rows, key=lambda r: r[1])
    fig, ax = plt.subplots(figsize=(9.4, 6.6))
    names = [r[0] for r in rows]
    vals = [r[1] for r in rows]
    colors = ["#c0392b" if n == "全国平均" else "#1e8449" for n in names]
    bars = ax.barh(names, vals, color=colors, height=0.62, zorder=3)
    for b, v in zip(bars, vals):
        ax.text(b.get_width() + 0.8, b.get_y() + b.get_height() / 2,
                f"{v:.1f}%", va="center", fontsize=8.8, color=C_TEXT, zorder=4)
    ax.set_xlim(0, 78)
    ax.grid(axis="x", color="#dde3e8", lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#999999")
    ax.tick_params(axis="y", length=0, labelsize=9.2)
    ax.tick_params(axis="x", labelsize=8.5, colors="#666666")
    ax.set_xlabel("森林覆盖率（%）", fontsize=9, color="#666666")
    ax.legend(handles=[Patch(fc="#1e8449", label="省级行政区"),
                       Patch(fc="#c0392b", label="全国平均（24.02%）")],
              loc="lower right", fontsize=8.8, framealpha=0.92,
              edgecolor="#cccccc")
    fig.text(0.02, 0.982, "分省森林覆盖率对比", fontsize=14.5, fontweight="bold",
             color=C_TEXT, va="top")
    fig.text(0.02, 0.952, "南方集体林区包揽前列；西北干旱区受水分条件制约",
             fontsize=9.3, color="#666666", va="top")
    fig.text(0.02, 0.012,
             "数据来源：国家林业和草原局（第九次全国森林资源清查及各省公布值，约数）",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.045, 1, 0.935))
    fig.savefig(os.path.join(OUT, "fig6-3_分省森林覆盖率.png"), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 6-3
def fig6_4_minerals():
    rows = [("稀土", 69), ("电解铝", 59), ("粗钢", 54), ("煤炭", 52),
            ("水泥", 50), ("黄金", 10)]
    rows = sorted(rows, key=lambda r: r[1])
    fig, ax = plt.subplots(figsize=(9.2, 5.0))
    names = [r[0] for r in rows]
    vals = [r[1] for r in rows]
    bars = ax.barh(names, vals, color="#b9770e", height=0.58, zorder=3)
    for b, v in zip(bars, vals):
        ax.text(b.get_width() + 1, b.get_y() + b.get_height() / 2,
                f"{v}%", va="center", fontsize=9.2, color=C_TEXT, zorder=4)
    ax.axvline(50, color="#999999", lw=0.8, ls=":")
    ax.text(50.5, -0.45, "全球一半", fontsize=8, color="#777777")
    ax.set_xlim(0, 82)
    ax.grid(axis="x", color="#dde3e8", lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#999999")
    ax.tick_params(axis="y", length=0, labelsize=9.6)
    ax.tick_params(axis="x", labelsize=8.5, colors="#666666")
    ax.set_xlabel("中国产量占世界比重（%）", fontsize=9, color="#666666")
    fig.text(0.02, 0.982, "主要矿产品产量：中国占世界的比重", fontsize=14.5,
             fontweight="bold", color=C_TEXT, va="top")
    fig.text(0.02, 0.952, "2023 年前后口径；稀土、粗钢、电解铝均为全球第一",
             fontsize=9.3, color="#666666", va="top")
    fig.text(0.02, 0.012,
             "数据来源：USGS《矿产品摘要》、国家统计局、中国钢铁工业协会等（约数）",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.045, 1, 0.935))
    fig.savefig(os.path.join(OUT, "fig6-4_主要矿产品产量世界占比.png"), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 7-1
NATURAL_ZONES = [
    ("寒温带针叶林", "#1a5276", [(121.0, 53.5), (126.0, 52.0), (127.5, 50.0), (124.0, 49.5), (121.0, 51.0)]),
    ("中温带针阔混交林与森林草原", "#2874a6", [(126.0, 48.0), (130.5, 46.0), (131.0, 43.0), (128.0, 41.0), (125.0, 42.5), (125.5, 45.5)]),
    ("温带草原", "#7d8f3f", [(112.0, 47.0), (120.0, 46.0), (121.0, 43.0), (118.0, 41.0), (114.0, 40.5), (110.0, 41.0), (107.0, 42.0), (107.0, 44.5)]),
    ("温带荒漠", "#c9a66b", [(76.0, 44.0), (90.0, 47.0), (100.0, 46.0), (106.0, 42.0), (105.0, 38.0), (96.0, 37.0), (86.0, 37.0), (78.0, 38.0)]),
    ("暖温带落叶阔叶林", "#b7791f", [(114.0, 40.5), (120.0, 40.5), (122.0, 37.5), (121.0, 34.0), (118.0, 33.0), (112.0, 33.5), (110.0, 35.0), (111.0, 38.0)]),
    ("亚热带常绿阔叶林", "#1e8449", [(104.0, 31.5), (112.0, 33.0), (120.0, 32.0), (122.5, 28.0), (120.0, 24.5), (116.0, 23.5), (111.0, 24.0), (106.0, 25.0), (103.0, 27.0), (102.0, 29.5)]),
    ("热带季雨林与雨林", "#117a65", [(100.0, 22.0), (104.5, 22.6), (106.5, 21.6), (110.0, 21.5), (114.0, 22.0), (112.0, 19.5), (109.0, 18.5), (106.0, 20.0), (101.5, 21.0)]),
]


def fig7_1_vegetation():
    import geopandas as gpd
    from ch03_terrain import RES_A, hillshade, load_cache, to_albers
    fig, ax = new_map_axes((10.5, 10.8))
    ax.set_facecolor(C_SEA)
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
    for name, color, poly in NATURAL_ZONES:
        xs, ys = zip(*[to_albers(lo, la) for lo, la in poly])
        ax.add_patch(MplPolygon(list(zip(xs, ys)), closed=True, fc=color,
                                alpha=0.42, ec=color, lw=1.4, zorder=5))
    from geo_features import PLATEAUS
    xs, ys = zip(*[to_albers(lo, la) for lo, la in PLATEAUS["青藏高原"]])
    ax.add_patch(MplPolygon(list(zip(xs, ys)), closed=True, fc="#8e7cc3",
                            alpha=0.42, ec="#8e7cc3", lw=1.4, zorder=5))
    handles = [Patch(fc=c, alpha=0.45, label=n) for n, c, _ in NATURAL_ZONES]
    handles.append(Patch(fc="#8e7cc3", alpha=0.45, label="青藏高寒植被区"))
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.005, 0.04),
              fontsize=8.4, framealpha=0.92, edgecolor="#cccccc",
              title="自然带（水平地带性）", title_fontsize=9.2)
    gdf = gpd.read_file(os.path.join(DATA, "boundaries", "datav",
                                     "100000_full.json"))
    from style import ALBERS
    prov = gdf[gdf["name"].notna() & (gdf["name"].str.len() > 0)].to_crs(ALBERS)
    dash = gdf[gdf["name"].isna() | (gdf["name"].str.len() == 0)].to_crs(ALBERS)
    prov.boundary.plot(ax=ax, color="#5a5a5a", linewidth=0.28, alpha=0.5, zorder=6)
    if len(dash):
        dash.plot(ax=ax, facecolor="none", edgecolor="#3b5872", linewidth=0.7,
                  ls="--", zorder=7)
    set_extent_from(ax, prov)
    add_title(ax, "中国主要自然带分布（示意）",
              "森林—草原—荒漠的东西向更替与纬向温度带的叠加；青藏高寒区自成体系")
    save_fig(fig, ax, "fig7-1_自然带分布示意图.png",
             footer="自然带范围为示意勾绘，底图：AWS Terrain Tiles；投影：Albers 等积圆锥\n"
                    "示意地图，不作为权属划界依据")


# ---------------------------------------------------------------- fig 7-2
def fig7_2_forest_curve():
    years = [1949, 1976, 1988, 1993, 1998, 2003, 2008, 2013, 2018, 2023]
    rate = [8.6, 12.7, 12.98, 13.92, 16.55, 18.21, 20.36, 21.63, 22.96, 24.02]
    fig, ax = plt.subplots(figsize=(9.6, 5.2))
    ax.plot(years, rate, color="#1e8449", lw=2.2, marker="o", ms=5, zorder=3)
    ax.fill_between(years, rate, 0, color="#a9dfbf", alpha=0.5, zorder=2)
    for x, y in zip(years, rate):
        ax.annotate(f"{y:.1f}", (x, y), textcoords="offset points",
                    xytext=(0, 8), fontsize=8.2, ha="center", color="#1e8449")
    ax.set_xlim(1946, 2026)
    ax.set_ylim(0, 28)
    ax.grid(axis="y", color="#dde3e8", lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#999999")
    ax.spines["left"].set_color("#999999")
    ax.set_ylabel("森林覆盖率（%）", fontsize=9, color="#666666")
    ax.set_xlabel("年份（历次全国森林资源清查口径）", fontsize=9, color="#666666")
    fig.text(0.02, 0.982, "中国森林覆盖率的变化（1949—2023）", fontsize=14.5,
             fontweight="bold", color=C_TEXT, va="top")
    fig.text(0.02, 0.952, "三北防护林（1978 年启动）与退耕还林（1999 年启动）是两次跃升的主因",
             fontsize=9.3, color="#666666", va="top")
    fig.text(0.02, 0.012,
             "数据来源：国家林业和草原局历次全国森林资源清查、2023 年林草公报", fontsize=8,
             color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 0.94))
    fig.savefig(os.path.join(OUT, "fig7-2_森林覆盖率变化.png"), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 7-3
EARTHQUAKE_BELTS = [
    ("南北地震带", "#8e2a1e", [(104.2, 25.5), (103.5, 29.0), (103.8, 32.5), (104.8, 35.5), (105.8, 38.5), (106.2, 40.5)]),
    ("华北地震带", "#b9770e", [(115.5, 32.0), (116.5, 35.5), (117.5, 38.5), (119.5, 40.5), (121.5, 41.5)]),
    ("东南沿海地震带", "#1f618d", [(113.5, 22.5), (116.5, 23.8), (119.5, 25.0), (121.5, 24.5)]),
    ("天山地震带", "#6c3483", [(76.0, 40.5), (81.0, 42.5), (86.0, 43.5), (91.0, 43.8)]),
    ("青藏高原周缘地震带", "#1e8449", [(84.0, 31.0), (88.5, 29.5), (93.0, 28.8), (97.5, 30.5), (100.0, 33.0), (96.0, 36.5), (90.0, 37.5), (84.0, 36.8)]),
]
QUAKES = [
    ("海原 1920 · 8.5", 105.4, 36.5), ("古浪 1927 · 8.0", 102.7, 37.4),
    ("唐山 1976 · 7.8", 118.2, 39.6), ("通海 1970 · 7.8", 102.7, 24.1),
    ("汶川 2008 · 8.0", 103.4, 31.0), ("玉树 2010 · 7.1", 97.0, 33.2),
    ("芦山 2013 · 7.0", 103.0, 30.3), ("九寨沟 2017 · 7.0", 103.8, 33.2),
    ("集集 1999 · 7.3", 120.9, 23.9), ("积石山 2023 · 6.2", 102.8, 35.8),
]


def fig7_3_quakes():
    import geopandas as gpd
    from ch03_terrain import RES_A, hillshade, load_cache, to_albers
    from style import ALBERS
    fig, ax = new_map_axes((10.5, 10.8))
    ax.set_facecolor(C_SEA)
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
    gdf = gpd.read_file(os.path.join(DATA, "boundaries", "datav",
                                     "100000_full.json"))
    prov = gdf[gdf["name"].notna() & (gdf["name"].str.len() > 0)].to_crs(ALBERS)
    dash = gdf[gdf["name"].isna() | (gdf["name"].str.len() == 0)].to_crs(ALBERS)
    prov.boundary.plot(ax=ax, color="#6a6a6a", linewidth=0.28, alpha=0.5, zorder=3)
    if len(dash):
        dash.plot(ax=ax, facecolor="none", edgecolor="#3b5872", linewidth=0.7,
                  ls="--", zorder=4)
    label_pos = {"南北地震带": (103.9, 27.0, -80), "华北地震带": (121.9, 42.1, -35),
                 "东南沿海地震带": (116.0, 22.6, 12), "天山地震带": (82.0, 42.0, 8),
                 "青藏高原周缘地震带": (88.0, 33.5, 0)}
    for name, color, pts in EARTHQUAKE_BELTS:
        xs, ys = zip(*[to_albers(lo, la) for lo, la in pts])
        ax.plot(xs, ys, color=color, lw=3.2, alpha=0.55,
                solid_capstyle="round", zorder=5)
        lo, la, rot = label_pos[name]
        x, y = to_albers(lo, la)
        ax.text(x, y, name, fontsize=8.6, color=color, rotation=rot,
                ha="center", va="center", zorder=8,
                bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none",
                          alpha=0.85))
    for name, lo, la in QUAKES:
        x, y = to_albers(lo, la)
        ax.plot([x], [y], "*", ms=10, color="#1a1a1a", zorder=9)
        dx = 0.45 if lo < 118 else -1.9
        ax.text(*to_albers(lo + dx, la - 0.35), name, fontsize=7.4,
                color="#1a1a1a", zorder=9,
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none",
                          alpha=0.8))
    set_extent_from(ax, prov)
    add_title(ax, "主要地震带与代表性强震（★）",
              "中国地处环太平洋地震带与欧亚地震带之间，震源浅、分布广")
    save_fig(fig, ax, "fig7-3_地震带与强震分布.png",
             footer="地震带为示意勾绘，震级为面波震级或矩震级通行口径；底图：AWS Terrain Tiles\n"
                    "示意地图，不作为权属划界依据")


if __name__ == "__main__":
    setup()
    fig6_1_land()
    fig6_2_cropland()
    fig6_3_forest()
    fig6_4_minerals()
    fig7_1_vegetation()
    fig7_2_forest_curve()
    fig7_3_quakes()
    print("ch06-07 done")
