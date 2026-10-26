# -*- coding: utf-8 -*-
"""第 3 章 地形地貌 —— 地形区、山脉与特殊地貌图（3.2—3.5 节）。

fig3-4 四大高原分布图        fig3-6 主要山脉走向分布图
fig3-5 四大盆地与三大平原图  fig3-7 主要山脉及其最高峰海拔
                             fig3-8 特殊地貌类型分布示意图
底图：AWS Terrain 山体阴影（复用 ch03_terrain 缓存），境外灰化。
"""
import os
import sys

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Polygon as MplPolygon

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import (ALBERS, C_SEA, C_TEXT, DATA, DPI, FIGURES, add_title,
                   new_map_axes, save_fig, set_extent_from, setup)
from geo_features import (BASINS, DANXIA, DESERTS, GLACIER_ZONE, KARST,
                          MOUNTAINS, PLAINS, PLATEAUS, TREND_COLOR,
                          TREND_LABEL, VOLCANOES)
from ch03_terrain import RES_A, hillshade, load_cache, to_albers

C_HL = {"plateau": "#c08a58", "basin": "#7fa8c9", "plain": "#5d9b6c"}


def dem_base():
    dem, minx, maxy = load_cache()
    h, w = dem.shape
    extent = (minx, minx + w * RES_A, maxy - h * RES_A, maxy)
    sh = hillshade(dem)
    rgba = np.zeros((h, w, 4))
    gray = 0.86 + 0.14 * sh
    rgba[:, :, 0] = gray * 1.005
    rgba[:, :, 1] = gray
    rgba[:, :, 2] = gray * 0.975
    rgba[:, :, 3] = np.where(np.isnan(dem), 0.0, 1.0)
    land_gdf = gpd.read_file(os.path.join(DATA, "boundaries", "datav",
                                          "100000_full.json"))
    prov = land_gdf[land_gdf["name"].notna() &
                    (land_gdf["name"].str.len() > 0)].to_crs(ALBERS)
    dash = land_gdf[land_gdf["name"].isna() |
                    (land_gdf["name"].str.len() == 0)].to_crs(ALBERS)
    return dem, extent, prov, dash


def region_map(fname, title, subtitle, regions, footer, label_offsets=None,
               highlight=None):
    dem, extent, prov, dash = dem_base()
    fig, ax = new_map_axes((10.5, 10.8))
    ax.set_facecolor(C_SEA)
    ax.imshow(dem_base_rgba(dem), extent=extent, origin="upper",
              interpolation="bilinear", zorder=1)
    prov.boundary.plot(ax=ax, color="#6a6a6a", linewidth=0.3, alpha=0.5, zorder=3)
    if len(dash):
        dash.plot(ax=ax, facecolor="none", edgecolor="#3b5872", linewidth=0.7,
                  ls="--", zorder=4)

    seen_kinds = set()
    handles = []
    for i, (kind, name, poly) in enumerate(regions):
        c = C_HL[kind]
        xs, ys = zip(*[to_albers(lo, la) for lo, la in poly])
        alpha_f, alpha_e = (0.55, 1.0) if highlight == name else (0.30, 0.85)
        ax.add_patch(MplPolygon(list(zip(xs, ys)), closed=True, fc=c,
                                ec=c, lw=1.6, alpha=alpha_f, zorder=5))
        ax.plot(list(xs) + [xs[0]], list(ys) + [ys[0]], color=c, lw=1.6,
                alpha=alpha_e, zorder=6)
        if kind not in seen_kinds:
            seen_kinds.add(kind)
            handles.append(Patch(fc=c, alpha=0.45, ec=c,
                                 label={"plateau": "高原", "basin": "盆地",
                                        "plain": "平原"}[kind]))
        cx, cy = poly_center(poly)
        off = (label_offsets or {}).get(name, (0, 0))
        ax.text(*to_albers(cx + off[0], cy + off[1]), name, fontsize=10.5,
                fontweight="bold", color="white", ha="center", va="center",
                zorder=8, path_effects=None,
                bbox=dict(boxstyle="round,pad=0.28", fc=c, ec="white",
                          lw=0.8, alpha=0.92))
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.005, 0.10),
              fontsize=9.5, framealpha=0.92, edgecolor="#cccccc")
    set_extent_from(ax, prov)
    add_title(ax, title, subtitle)
    save_fig(fig, ax, fname, footer=footer)


def dem_base_rgba(dem):
    """山体阴影灰阶 + 中国境外减淡。"""
    from rasterio.features import rasterize
    from rasterio.transform import from_origin
    sh = hillshade(dem)
    h, w = dem.shape
    rgba = np.zeros((h, w, 4))
    f = 0.40 + 0.60 * sh
    rgba[:, :, 0], rgba[:, :, 1], rgba[:, :, 2] = 0.93 * f, 0.91 * f, 0.87 * f
    rgba[:, :, 3] = np.where(np.isnan(dem), 0.0, 1.0)
    return rgba


def poly_center(poly):
    lon = np.mean([p[0] for p in poly])
    lat = np.mean([p[1] for p in poly])
    return lon, lat


# ---------------------------------------------------------------- fig 3-4
def fig3_4_plateaus():
    regions = [("plateau", k, v) for k, v in PLATEAUS.items()]
    region_map(
        "fig3-4_四大高原分布图.png",
        "四大高原的分布",
        "海拔与成因各异的四块巨大隆起；底图为山体阴影",
        regions,
        "地形区范围为示意图，底图：AWS Terrain Tiles；投影：Albers 等积圆锥\n"
        "示意地图，不作为权属划界依据",
        label_offsets={"青藏高原": (1.5, 0), "内蒙古高原": (0, 0.3),
                       "黄土高原": (0, 0), "云贵高原": (0, 0)})


# ---------------------------------------------------------------- fig 3-5
def fig3_5_basins_plains():
    regions = ([("basin", k, v) for k, v in BASINS.items()] +
               [("plain", k, v) for k, v in PLAINS.items()])
    region_map(
        "fig3-5_四大盆地与三大平原分布图.png",
        "四大盆地与三大平原的分布",
        "第二级阶梯内的四大盆地与第三级阶梯上的三大平原；底图为山体阴影",
        regions,
        "地形区范围为示意图，底图：AWS Terrain Tiles；投影：Albers 等积圆锥\n"
        "示意地图，不作为权属划界依据",
        label_offsets={"塔里木盆地": (0, 0), "准噶尔盆地": (0, 0),
                       "柴达木盆地": (0, -0.2), "四川盆地": (0, 0),
                       "东北平原": (0.5, 0.5), "华北平原": (0.3, 0.5),
                       "长江中下游平原": (0, 0.6)})


# ---------------------------------------------------------------- fig 3-6
def fig3_6_mountains():
    dem, extent, prov, dash = dem_base()
    fig, ax = new_map_axes((10.5, 10.8))
    ax.set_facecolor(C_SEA)
    ax.imshow(dem_base_rgba(dem), extent=extent, origin="upper",
              interpolation="bilinear", zorder=1)
    prov.boundary.plot(ax=ax, color="#6a6a6a", linewidth=0.3, alpha=0.5, zorder=3)
    if len(dash):
        dash.plot(ax=ax, facecolor="none", edgecolor="#3b5872", linewidth=0.7,
                  ls="--", zorder=4)

    label_pos = {  # name -> (lon, lat, rotation)
        "喜马拉雅山脉": (82.5, 27.5, 13), "喀喇昆仑山脉": (75.4, 36.9, -28),
        "昆仑山脉": (88.5, 36.8, 2), "阿尔金山脉": (90.5, 39.5, 8),
        "祁连山脉": (99.5, 38.9, -20), "天山山脉": (83.0, 43.5, 6),
        "阿尔泰山脉": (89.2, 48.8, -22), "阴山山脉": (110.5, 41.6, -4),
        "秦岭": (106.8, 34.4, -3), "南岭": (112.8, 25.6, 4),
        "燕山": (117.8, 41.4, -3), "大兴安岭": (123.2, 50.0, -48),
        "太行山脉": (114.4, 37.6, -87), "吕梁山": (112.0, 37.6, -80),
        "巫山": (110.5, 30.7, -55), "雪峰山": (111.5, 27.4, -62),
        "长白山脉": (128.8, 43.4, -50), "武夷山脉": (118.4, 27.0, -78),
        "台湾山脉": (121.9, 23.7, -70), "大巴山脉": (108.0, 32.6, 5),
        "横断山脉": (100.6, 29.0, -80), "贺兰山": (106.7, 38.6, -80),
        "六盘山": (107.0, 34.9, -80), "岷山": (103.3, 32.9, -75),
        "乌蒙山脉": (104.2, 26.6, -55), "大娄山": (107.6, 28.9, -45),
    }
    for name, (trend, pts) in MOUNTAINS.items():
        xs, ys = zip(*[to_albers(lo, la) for lo, la in pts])
        ax.plot(xs, ys, color=TREND_COLOR[trend], lw=2.6, solid_capstyle="round",
                zorder=6)
        if name in label_pos:
            lo, la, rot = label_pos[name]
            x, y = to_albers(lo, la)
            ax.text(x, y, name, fontsize=8.2, color=TREND_COLOR[trend],
                    rotation=rot, ha="center", va="center", zorder=7,
                    bbox=dict(boxstyle="round,pad=0.16", fc="white", ec="none",
                              alpha=0.8))
    legend_elems = [Line2D([0], [0], color=c, lw=2.6, label=TREND_LABEL[t])
                    for t, c in TREND_COLOR.items()]
    # 珠穆朗玛峰
    px, py = to_albers(86.93, 27.99)
    ax.plot([px], [py], "^", ms=6, color="#1a1a1a", zorder=8)
    ax.annotate("珠穆朗玛峰 8 848.86 m", xy=(px, py), xytext=to_albers(79.0, 24.2),
                fontsize=8.5, color="#1a1a1a", ha="center", zorder=8,
                arrowprops=dict(arrowstyle="-", color="#666666", lw=0.6,
                                shrinkA=1, shrinkB=2))
    ax.legend(handles=legend_elems, loc="lower left", bbox_to_anchor=(0.005, 0.10),
              fontsize=9.5, framealpha=0.92, edgecolor="#cccccc",
              title="山脉走向", title_fontsize=10)
    set_extent_from(ax, prov)
    add_title(ax, "主要山脉的走向分布", "四组走向的山脉构成了中国地形的骨架")
    save_fig(fig, ax, "fig3-6_主要山脉走向分布图.png",
             footer="山脉走向线为示意勾绘；底图：AWS Terrain Tiles；投影：Albers 等积圆锥\n"
                    "示意地图，不作为权属划界依据")


# ---------------------------------------------------------------- fig 3-7
def fig3_7_peaks():
    rows = [
        ("喜马拉雅·珠穆朗玛峰", 8848.86), ("喀喇昆仑·乔戈里峰", 8611),
        ("昆仑·公格尔峰", 7649), ("横断·贡嘎山", 7556), ("天山·托木尔峰", 7443),
        ("祁连·团结峰", 5808), ("阿尔泰·友谊峰", 4374), ("台湾·玉山", 3952),
        ("秦岭·太白山", 3771), ("长白·白云峰", 2691), ("太行·小五台山", 2882),
        ("武夷·黄岗山", 2161), ("大兴安岭·黄岗梁", 2029),
    ]
    rows = sorted(rows, key=lambda r: r[1])
    names = [r[0] for r in rows]; vals = [r[1] for r in rows]
    colors = ["#c0392b" if v > 8000 else "#d3a670" if v > 5000 else "#7fa8c9"
              for v in vals]
    fig, ax = plt.subplots(figsize=(9.2, 7.2))
    bars = ax.barh(names, vals, color=colors, height=0.6, zorder=3)
    for b, v in zip(bars, vals):
        ax.text(b.get_width() + 90, b.get_y() + b.get_height() / 2,
                f"{v:,.2f} m".replace(",", " ") if isinstance(v, float) else f"{v:,} m".replace(",", " "),
                va="center", fontsize=8.8, color=C_TEXT, zorder=4)
    ax.set_xlim(0, 10300)
    ax.grid(axis="x", color="#dde3e8", lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#999999")
    ax.tick_params(axis="y", length=0, labelsize=9.2)
    ax.tick_params(axis="x", labelsize=8.5, colors="#666666")
    ax.set_xlabel("海拔（m）", fontsize=9, color="#666666")
    legend_elems = [Patch(fc="#c0392b", label="8 000 m 以上（世界级极高山）"),
                    Patch(fc="#d3a670", label="5 000—8 000 m（极高山、高山）"),
                    Patch(fc="#7fa8c9", label="5 000 m 以下（中高山）")]
    ax.legend(handles=legend_elems, loc="lower right", fontsize=8.8,
              framealpha=0.92, edgecolor="#cccccc")
    fig.text(0.02, 0.982, "主要山脉及其最高峰", fontsize=14.5, fontweight="bold",
             color=C_TEXT, va="top")
    fig.text(0.02, 0.955, "山脉呈条带状延展，图中取各山脉最高点", fontsize=9.3,
             color="#666666", va="top")
    fig.text(0.02, 0.012,
             "数据来源：2022 年珠峰高程 8 848.86 m（中尼联合公布）；其余为测绘部门公布值",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.045, 1, 0.935))
    fig.savefig(os.path.join(FIGURES, "fig3-7_主要山脉最高峰海拔.png"), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 3-8
def fig3_8_special():
    dem, extent, prov, dash = dem_base()
    fig, ax = new_map_axes((10.5, 10.8))
    ax.set_facecolor(C_SEA)
    ax.imshow(dem_base_rgba(dem), extent=extent, origin="upper",
              interpolation="bilinear", zorder=1)
    prov.boundary.plot(ax=ax, color="#6a6a6a", linewidth=0.3, alpha=0.5, zorder=3)
    if len(dash):
        dash.plot(ax=ax, facecolor="none", edgecolor="#3b5872", linewidth=0.7,
                  ls="--", zorder=4)

    # 喀斯特集中区
    xs, ys = zip(*[to_albers(lo, la) for lo, la in KARST])
    ax.add_patch(MplPolygon(list(zip(xs, ys)), closed=True, fc="#8e44ad",
                            alpha=0.35, ec="#8e44ad", lw=1.4, zorder=5))
    cx, cy = np.mean(xs), np.mean(ys)
    ax.text(cx, cy, "喀斯特地貌集中区\n（云贵高原）", fontsize=9, color="white",
            ha="center", va="center", zorder=8, linespacing=1.5,
            bbox=dict(boxstyle="round,pad=0.25", fc="#8e44ad", ec="white",
                      lw=0.7, alpha=0.9))
    # 黄土覆盖（复用黄土高原范围，标注塬梁峁）
    from geo_features import PLATEAUS
    xs, ys = zip(*[to_albers(lo, la) for lo, la in PLATEAUS["黄土高原"]])
    ax.add_patch(MplPolygon(list(zip(xs, ys)), closed=True, fc="#d4ac0d",
                            alpha=0.4, ec="#b7950b", lw=1.4, zorder=5))
    ax.text(*to_albers(108.3, 37.2), "黄土高原\n塬·梁·峁", fontsize=9, color="#4a3520",
            ha="center", va="center", zorder=8, linespacing=1.5,
            bbox=dict(boxstyle="round,pad=0.25", fc="#f9e79f", ec="#b7950b",
                      lw=0.7, alpha=0.92))
    # 沙漠
    for name, poly in DESERTS.items():
        xs, ys = zip(*[to_albers(lo, la) for lo, la in poly])
        ax.add_patch(MplPolygon(list(zip(xs, ys)), closed=True, fc="#e67e22",
                                alpha=0.5, ec="#ca6f1e", lw=1.0, zorder=5))
        if name in ("塔克拉玛干沙漠", "巴丹吉林沙漠", "古尔班通古特沙漠"):
            cx, cy = np.mean(xs), np.mean(ys)
            ax.text(cx, cy, name, fontsize=8.2, color="#7e3c06", ha="center",
                    va="center", zorder=8,
                    bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none",
                              alpha=0.85))
    # 冰川冻土区
    xs, ys = zip(*[to_albers(lo, la) for lo, la in GLACIER_ZONE])
    ax.plot(list(xs) + [xs[0]], list(ys) + [ys[0]], color="#2874a6", lw=1.4,
            ls="--", zorder=6)
    ax.text(*to_albers(90.5, 33.8), "冰川与冻土作用区", fontsize=9,
            color="#1a5276", ha="center", va="center", zorder=8,
            bbox=dict(boxstyle="round,pad=0.25", fc="#d6eaf8", ec="#2874a6",
                      lw=0.7, alpha=0.92))
    # 丹霞与火山点位
    for name, (lo, la) in DANXIA.items():
        x, y = to_albers(lo, la)
        ax.plot([x], [y], "s", ms=4.5, color="#b03a2e", zorder=7)
    for name, (lo, la) in VOLCANOES.items():
        x, y = to_albers(lo, la)
        ax.plot([x], [y], "^", ms=5.5, color="#1a1a1a", zorder=7)
    legend_elems = [
        Patch(fc="#8e44ad", alpha=0.45, label="喀斯特（云南、贵州、广西）"),
        Patch(fc="#d4ac0d", alpha=0.45, label="黄土地貌（塬、梁、峁）"),
        Patch(fc="#e67e22", alpha=0.5, label="风沙地貌（沙漠、沙地）"),
        Line2D([0], [0], color="#2874a6", lw=1.4, ls="--", label="冰川与冻土地貌"),
        Line2D([0], [0], marker="s", color="none", mfc="#b03a2e", ms=5,
               label="丹霞地貌（世界自然遗产点位）"),
        Line2D([0], [0], marker="^", color="none", mfc="#1a1a1a", ms=5.5,
               label="主要火山群"),
    ]
    ax.legend(handles=legend_elems, loc="lower left", bbox_to_anchor=(0.005, 0.06),
              fontsize=8.8, framealpha=0.92, edgecolor="#cccccc",
              title="地貌类型", title_fontsize=9.5)
    set_extent_from(ax, prov)
    add_title(ax, "特殊地貌类型分布示意", "以世界自然遗产与国家地质公园等典型点位标示；底图为山体阴影")
    save_fig(fig, ax, "fig3-8_特殊地貌分布示意图.png",
             footer="类型范围为示意勾绘，点位为代表性坐标；底图：AWS Terrain Tiles；投影：Albers 等积圆锥\n"
                    "示意地图，不作为权属划界依据")


if __name__ == "__main__":
    setup()
    fig3_4_plateaus()
    fig3_5_basins_plains()
    fig3_6_mountains()
    fig3_7_peaks()
    fig3_8_special()
    print("ch03 maps done")
