# -*- coding: utf-8 -*-
"""第 10—12 章 —— 城市、经济、交通图表。

fig10-1 城市规模金字塔      fig11-4 粮食产量（1949—2024）
fig10-2 超大特大城市分布    fig11-5 三大粮食作物优势区（示意）
fig10-3 主要城市群示意      fig11-6 能源消费结构演变
fig10-4 五大城市群对比      fig11-7 重大区域战略示意
fig11-1 GDP 总量与人均      fig12-1 铁路与公路里程增长
fig11-2 分省 GDP 排序       fig12-2 货运量结构
fig11-3 四大板块构成        fig12-3 “八纵八横”高铁网示意
                            fig12-4 沿海港口货物吞吐量
"""
from volume1_layout import save_volume_figure
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Patch, Polygon as MplPolygon

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matplotlib.patheffects as pe

from style import (ALBERS, C_CHINA, C_SEA, C_TEXT, DATA, DPI, FIGURES,
                   add_title, china_borders, draw_borders, new_map_axes,
                   plot_china_frame, save_fig, set_extent_from, setup)
from mapkit import LabelPlacer, reserve_axes_boxes
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


def _dem_base():
    """全国 DEM 晕渲底图数据（复用 ch03_terrain 的缓存，不重复下载）。"""
    import geopandas as gpd
    dem, minx, maxy = load_cache()
    h, w = dem.shape
    extent = (minx, minx + w * RES_A, maxy - h * RES_A, maxy)
    gdf = gpd.read_file(os.path.join(DATA, "boundaries", "datav",
                                     "100000_full.json"))
    prov, dash = china_borders(gdf.to_crs(ALBERS))
    return dem, extent, prov, dash


def _relief(dem):
    """淡灰晕渲：只提供地形骨架，不抢线路的颜色。"""
    h, w = dem.shape
    sh = hillshade(dem)
    rgba = np.zeros((h, w, 4))
    gray = 0.88 + 0.12 * sh
    rgba[:, :, 0] = gray * 1.005
    rgba[:, :, 1] = gray
    rgba[:, :, 2] = gray * 0.972
    rgba[:, :, 3] = np.where(np.isnan(dem), 0.0, 1.0)
    return rgba


def _prov_frame(ax, fill=None):
    """中国地图骨架：国界（深）+ 省界（浅）+ 南海断续线（实线）。

    旧实现只画 prov.boundary（0.28pt 灰）且把断续线当成面用 ls="--" 描边，
    结果全国图没有国界、南海断续线碎成十余段小弧。统一走 style.plot_china_frame。
    """
    import geopandas as gpd
    gdf = gpd.read_file(os.path.join(DATA, "boundaries", "datav",
                                     "100000_full.json")).to_crs(ALBERS)
    prov, _ = plot_china_frame(ax, gdf, z=3,
                               facecolor=fill if fill else None)
    return prov


CITY_XY = {
    "湛江": (110.40, 21.19), "连云港": (119.22, 34.60),
    "绥芬河": (131.15, 44.41), "满洲里": (117.48, 49.59),
    "上海": (121.47, 31.23), "北京": (116.41, 39.90), "深圳": (114.06, 22.55),
    "重庆": (106.55, 29.56), "广州": (113.26, 23.13), "成都": (104.07, 30.57),
    "天津": (117.20, 39.08), "武汉": (114.31, 30.59), "东莞": (113.75, 23.02),
    "西安": (108.94, 34.34), "杭州": (120.15, 30.27), "佛山": (113.12, 23.02),
    "南京": (118.80, 32.06), "沈阳": (123.43, 41.80), "青岛": (120.38, 36.07),
    "济南": (117.12, 36.65), "长沙": (112.94, 28.23), "哈尔滨": (126.53, 45.80),
    "郑州": (113.63, 34.75), "昆明": (102.83, 24.88), "大连": (121.61, 38.91),
    "苏州": (120.58, 31.30), "合肥": (117.28, 31.86), "宁波": (121.55, 29.87),
    "厦门": (118.09, 24.48), "福州": (119.30, 26.08), "无锡": (120.31, 31.49),
    "石家庄": (114.51, 38.04), "南昌": (115.86, 28.68), "贵阳": (106.63, 26.65),
    "南宁": (108.37, 22.82), "长春": (125.32, 43.90), "太原": (112.55, 37.87),
    "乌鲁木齐": (87.62, 43.79), "兰州": (103.83, 36.06), "呼和浩特": (111.75, 40.84),
    "西宁": (101.78, 36.62), "银川": (106.28, 38.47), "拉萨": (91.14, 29.65),
    "海口": (110.20, 20.04), "香港": (114.17, 22.32), "澳门": (113.55, 22.20),
    "台北": (121.56, 25.03),
}


def _city(ax, name, r_deg=None, ms=None, label=True, fs=7.8, color="#8e2a1e",
          dx=0.0, dy=0.0):
    lo, la = CITY_XY[name]
    x, y = to_albers(lo, la)
    if r_deg:
        ax.add_patch(Circle((x, y), r_deg * 111000, fc=color, ec="white",
                            lw=0.6, alpha=0.75, zorder=6))
    elif ms:
        ax.plot([x], [y], "o", ms=ms, color=color, zorder=6)
    if label:
        ax.text(x + dx, y + dy, name, fontsize=fs, color="#1a1a1a", ha="center",
                va="center", zorder=8,
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none",
                          alpha=0.8))


# ---------------------------------------------------------------- fig 10-1
from volume1_topics import city_sizes as fig10_1_pyramid


# ---------------------------------------------------------------- fig 10-2
def fig10_2_megacities():
    from volume1_layout import NumberedMapIndex
    from ch13_regions import _save_with_legend
    fig, ax = new_map_axes((10.5, 10.8))
    fig.subplots_adjust(bottom=0.18, top=0.91)
    _map_base(ax)
    prov = _prov_frame(ax)
    mega = ["上海", "北京", "深圳", "重庆", "广州", "成都", "天津"]
    huge = ["武汉", "东莞", "西安", "杭州", "佛山", "南京", "沈阳", "青岛",
            "济南", "长沙", "哈尔滨", "郑州", "昆明", "大连"]
    set_extent_from(ax, prov)
    index = NumberedMapIndex()
    for c in mega:
        index.add(ax, "mega", c, *CITY_XY[c])
    for c in huge:
        index.add(ax, "huge", c, *CITY_XY[c])
    add_title(ax, "超大城市与特大城市的分布",
              "7 座超大城市与 14 座特大城市全部位于胡焕庸线东南侧")
    index.render(fig)
    _save_with_legend(
        fig, "fig10-2_超大特大城市分布.png",
        ["超大城市：城区常住人口超过 1 000 万；特大城市：500 万—1 000 万。",
         "底图：DataV.GeoAtlas 与 AWS Terrain Tiles；示意地图，不作为权属划界依据。"])


# ---------------------------------------------------------------- fig 10-3
CLUSTERS = {
    "京津冀": (116.8, 39.2, 2.1), "长三角": (120.5, 31.2, 2.6),
    "粤港澳大湾区": (113.4, 22.7, 1.9), "成渝": (105.3, 30.2, 2.0),
    "长江中游": (113.0, 29.3, 2.3), "山东半岛": (118.8, 36.6, 1.5),
    "中原": (113.5, 34.5, 1.3), "粤闽浙沿海": (117.8, 25.6, 1.3),
    "关中": (108.9, 34.4, 1.1), "北部湾": (108.9, 22.0, 1.0),
    "辽中南": (122.6, 41.0, 1.2), "哈长": (126.4, 44.6, 1.2),
    "山西中部": (112.5, 37.7, 0.9), "呼包鄂榆": (110.0, 40.0, 1.0),
    "黔中": (106.6, 26.6, 0.9), "滇中": (102.8, 24.9, 0.9),
    "宁夏沿黄": (106.1, 38.3, 0.8), "天山北坡": (87.0, 44.0, 0.9),
    "兰西": (103.0, 36.4, 0.8),
}


def fig10_3_clusters():
    from volume1_layout import NumberedMapIndex
    from ch13_regions import _save_with_legend
    fig, ax = new_map_axes((10.5, 10.8))
    fig.subplots_adjust(bottom=0.18, top=0.91)
    _map_base(ax)
    prov = _prov_frame(ax)
    set_extent_from(ax, prov)
    index = NumberedMapIndex()
    for name, (lo, la, r) in CLUSTERS.items():
        x, y = to_albers(lo, la)
        index.add(ax, "cluster", name, lo, la)
    add_title(ax, "全国主要城市群的分布",
              "19 个城市群示意中心；圆圈表示概略位置")
    index.render(fig)
    _save_with_legend(
        fig, "fig10-4_主要城市群分布.png",
        ["依据《“十四五”规划纲要》城市群布局示意勾绘；底图：AWS Terrain Tiles。",
         "示意地图，不作为权属划界依据。"])


# ---------------------------------------------------------------- fig 10-4
def fig10_4_cluster_compare():
    rows = [("长三角（沪苏浙皖）", 33.0, 23800), ("粤港澳大湾区（含港澳）", 14.2, 8700),
            ("长江中游（鄂湘赣）", 13.8, 21000), ("京津冀", 10.5, 11000),
            ("成渝（川渝）", 9.0, 9800)]
    rows = sorted(rows, key=lambda r: r[1], reverse=True)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.0, 4.6))
    names = [r[0] for r in rows]
    y = np.arange(len(rows))[::-1]
    ax1.barh(y, [r[1] for r in rows], color="#c0392b", height=0.55, zorder=3)
    for i, r in enumerate(rows):
        ax1.text(r[1] + 0.5, y[i], f"{r[1]:.1f}", va="center", fontsize=9.2,
                 color=C_TEXT, zorder=4)
    ax1.set_yticks(y, names, fontsize=9)
    ax1.set_xlim(0, 38)
    ax1.set_title("GDP（万亿元，2023 年）", fontsize=10.5, color=C_TEXT)
    ax2.barh(y, [r[2] / 10000 for r in rows], color="#2e86c1", height=0.55,
             zorder=3)
    for i, r in enumerate(rows):
        ax2.text(r[2] / 10000 + 0.03, y[i], f"{r[2] / 10000:.2f}", va="center",
                 fontsize=9.2, color=C_TEXT, zorder=4)
    ax2.set_yticks(y, ["" for _ in rows])
    ax2.set_xlim(0, 2.9)
    ax2.set_title("常住人口（亿人）", fontsize=10.5, color=C_TEXT)
    for ax in (ax1, ax2):
        ax.grid(axis="x", color="#dde3e8", lw=0.7, zorder=0)
        ax.set_axisbelow(True)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color("#999999")
        ax.tick_params(axis="x", labelsize=8.5, colors="#666666")
    fig.text(0.02, 0.982, "五大国家级城市群的体量对比", fontsize=14.5,
             fontweight="bold", color=C_TEXT, va="top")
    fig.text(0.02, 0.952, "长三角以约 3.4% 的国土贡献了全国约四分之一的经济总量",
             fontsize=9.3, color="#666666", va="top")
    fig.text(0.02, 0.012,
             "数据来源：各地 2023 年统计公报汇总；粤港澳大湾区含港澳（当地口径折算，约数）",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 0.93))
    save_volume_figure(fig, os.path.join(OUT, "fig10-5_五大城市群对比.png"), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 11-1
def fig11_1_gdp():
    pairs = [(1952, 679), (1978, 3679), (1990, 18873), (2000, 100280),
             (2010, 412119), (2020, 1015986), (2023, 1260582), (2025, 1400000)]
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.2, 4.4),
                                   gridspec_kw={"width_ratios": [1.5, 1]})
    ax1.plot(xs, ys, color="#c0392b", lw=2.2, marker="o", ms=4.5, zorder=3)
    ax1.set_yscale("log")
    ax1.set_yticks([1000, 10000, 100000, 1000000],
                   ["1 000", "1 万", "10 万", "100 万"])
    for x, y in pairs:
        if x in (1952, 1978, 2000, 2025):
            ax1.annotate(f"{y:,}".replace(",", " "), (x, y),
                         textcoords="offset points", xytext=(0, 9),
                         fontsize=8.2, ha="center", color="#8e2a1e")
    ax1.set_xlim(1948, 2028)
    ax1.set_ylim(300, 3000000)
    ax1.grid(axis="y", color="#dde3e8", lw=0.7, zorder=0)
    ax1.set_axisbelow(True)
    for s in ("top", "right"):
        ax1.spines[s].set_visible(False)
    ax1.spines["bottom"].set_color("#999999")
    ax1.set_title("GDP 总量（亿元，对数轴）", fontsize=10.5, color=C_TEXT)
    pop = [(1952, 119), (1978, 385), (2000, 7942), (2010, 30876),
           (2020, 72000), (2025, 99500)]
    ax2.plot([p[0] for p in pop], [p[1] for p in pop], color="#2e86c1", lw=2.2,
             marker="o", ms=4.5, zorder=3)
    for x, y in pop:
        if x in (1952, 1978, 2025):
            ax2.annotate(f"{y:,}".replace(",", " "), (x, y),
                         textcoords="offset points", xytext=(0, 9),
                         fontsize=8.2, ha="center", color="#1b4f72")
    ax2.set_xlim(1948, 2028)
    ax2.grid(axis="y", color="#dde3e8", lw=0.7, zorder=0)
    ax2.set_axisbelow(True)
    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)
    ax2.spines["bottom"].set_color("#999999")
    ax2.set_title("人均 GDP（元）", fontsize=10.5, color=C_TEXT)
    fig.text(0.02, 0.982, "中国经济总量与人均（1952—2025）", fontsize=14.5,
             fontweight="bold", color=C_TEXT, va="top")
    fig.text(0.02, 0.952, "2025 年 GDP 首破 140 万亿元；人均约 10 万元，接近高收入国家门槛",
             fontsize=9.3, color="#666666", va="top")
    fig.text(0.02, 0.012,
             "数据来源：国家统计局历年统计公报（现价，2025 年为初步核算约数）；人均 GDP 按当年价",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 0.93))
    save_volume_figure(fig, os.path.join(OUT, "fig11-1_经济总量与人均.png"), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 11-2
def fig11_2_prov_gdp():
    rows = [("广东", 135673), ("江苏", 128222), ("山东", 92069), ("浙江", 82553),
            ("四川", 60133), ("河南", 59133), ("湖北", 55804), ("福建", 54355),
            ("湖南", 50013), ("上海", 47219), ("安徽", 47051), ("河北", 43944),
            ("北京", 43761), ("陕西", 33793), ("江西", 32207)]
    rows = sorted(rows, key=lambda r: r[1])
    fig, ax = plt.subplots(figsize=(9.4, 7.0))
    names = [r[0] for r in rows]
    vals = [r[1] for r in rows]
    colors = ["#c0392b" if n in ("广东", "江苏") else "#7fa8c9" for n in names]
    bars = ax.barh(names, vals, color=colors, height=0.62, zorder=3)
    for b, v in zip(bars, vals):
        ax.text(b.get_width() + 1600, b.get_y() + b.get_height() / 2,
                f"{v:,}".replace(",", " "), va="center", fontsize=8.6,
                color=C_TEXT, zorder=4)
    ax.set_xlim(0, 152000)
    ax.grid(axis="x", color="#dde3e8", lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#999999")
    ax.tick_params(axis="y", length=0, labelsize=9.2)
    ax.tick_params(axis="x", labelsize=8.5, colors="#666666")
    ax.set_xlabel("地区生产总值（亿元，2023 年）", fontsize=9, color="#666666")
    fig.text(0.02, 0.982, "分省 GDP 排序（前 15 位）", fontsize=14.5,
             fontweight="bold", color=C_TEXT, va="top")
    fig.text(0.02, 0.952, "粤苏双雄合计约 26 万亿元，超过印度的经济总量",
             fontsize=9.3, color="#666666", va="top")
    fig.text(0.02, 0.012,
             "数据来源：各省 2023 年国民经济和社会发展统计公报", fontsize=8,
             color="#555555")
    fig.tight_layout(rect=(0, 0.045, 1, 0.935))
    save_volume_figure(fig, os.path.join(OUT, "fig11-2_分省GDP排序.png"), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 11-3
def fig11_3_boards():
    labels = ["东部（10 省）", "中部（6 省）", "西部（12 省）", "东北（3 省）"]
    vals = [52, 22, 21, 5]
    colors = ["#c0392b", "#2e86c1", "#b9770e", "#7d3c98"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.0, 4.2),
                                   gridspec_kw={"width_ratios": [1, 1.2]})
    w, _ = ax1.pie(vals, colors=colors, startangle=90, counterclock=False,
                   wedgeprops=dict(width=0.42, edgecolor="white"))
    ax1.legend(w, [f"{l}  {v}%" for l, v in zip(labels, vals)], loc="center",
               fontsize=9, frameon=False)
    ax1.set_title("GDP 构成（2023 年）", fontsize=10.5, color=C_TEXT)
    area = [9.5, 10.2, 68.8, 11.5]
    pop = [40, 25, 27, 7]
    x = np.arange(4)
    ax2.bar(x - 0.19, area, 0.36, label="国土面积占比（%）", color="#a9cce3",
            zorder=3)
    ax2.bar(x + 0.19, pop, 0.36, label="人口占比（%）", color="#e59866", zorder=3)
    ax2.set_xticks(x, ["东部", "中部", "西部", "东北"], fontsize=9.5)
    ax2.grid(axis="y", color="#dde3e8", lw=0.7, zorder=0)
    ax2.set_axisbelow(True)
    for s in ("top", "right"):
        ax2.spines[s].set_visible(False)
    ax2.spines["bottom"].set_color("#999999")
    ax2.legend(fontsize=8.8, framealpha=0.92, edgecolor="#cccccc")
    ax2.set_title("面积与人口的不对称分布", fontsize=10.5, color=C_TEXT)
    fig.text(0.02, 0.982, "四大板块：经济与人口、国土的错位", fontsize=14.5,
             fontweight="bold", color=C_TEXT, va="top")
    fig.text(0.02, 0.952, "东部以约 9.5% 的国土承载 40% 的人口、创造 52% 的 GDP",
             fontsize=9.3, color="#666666", va="top")
    fig.text(0.02, 0.012,
             "数据来源：国家统计局分省数据汇总（2023 年，约数）", fontsize=8,
             color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 0.93))
    save_volume_figure(fig, os.path.join(OUT, "fig11-3_四大板块.png"), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 11-4
def fig11_4_grain():
    pairs = [(1949, 1.13), (1978, 3.05), (1984, 4.07), (1998, 5.12),
             (2003, 4.31), (2015, 6.21), (2020, 6.70), (2024, 7.06)]
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    fig, ax = plt.subplots(figsize=(9.8, 5.0))
    ax.plot(xs, ys, color="#1e8449", lw=2.2, marker="o", ms=4.5, zorder=3)
    ax.fill_between(xs, ys, 0, color="#a9dfbf", alpha=0.5, zorder=2)
    ax.annotate("2024 年首破 1.4 万亿斤", xy=(2024, 7.06), xytext=(1992, 7.3),
                fontsize=9, color="#1e8449",
                arrowprops=dict(arrowstyle="->", color="#1e8449", lw=0.9))
    ax.annotate("2003 年低谷（退耕与种粮比较效益低）", xy=(2003, 4.31),
                xytext=(1975, 5.6), fontsize=8.6, color="#555555",
                arrowprops=dict(arrowstyle="->", color="#888888", lw=0.9))
    ax.set_xlim(1946, 2028)
    ax.set_ylim(0, 8.2)
    ax.grid(axis="y", color="#dde3e8", lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#999999")
    ax.spines["left"].set_color("#999999")
    ax.set_ylabel("粮食产量（亿吨）", fontsize=9, color="#666666")
    fig.text(0.02, 0.982, "全国粮食产量（1949—2024）", fontsize=14.5,
             fontweight="bold", color=C_TEXT, va="top")
    fig.text(0.02, 0.952, "75 年增长 5.2 倍；人均约 500 kg，高于国际公认的 400 kg 安全线",
             fontsize=9.3, color="#666666", va="top")
    fig.text(0.02, 0.012,
             "数据来源：国家统计局历年统计公报（谷物与豆类薯类合计口径）", fontsize=8,
             color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 0.94))
    save_volume_figure(fig, os.path.join(OUT, "fig11-4_粮食产量.png"), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 11-5
CROP_ZONES = [
    ("水稻优势区", "#1e8449", [(102.5, 29.5), (108.0, 27.0), (114.0, 27.5), (120.0, 29.5), (122.0, 32.0), (117.0, 33.5), (110.0, 33.0), (104.0, 32.0)]),
    ("东北粳稻区", "#2e86c1", [(123.0, 47.5), (130.0, 46.5), (132.0, 43.5), (127.0, 41.5), (123.0, 43.5)]),
    ("小麦优势区", "#b9770e", [(110.5, 39.5), (117.5, 39.5), (121.0, 35.5), (118.0, 32.5), (112.0, 32.5), (108.0, 34.5), (106.0, 36.5)]),
    ("玉米优势区", "#c0392b", [(122.0, 48.5), (131.0, 47.5), (131.0, 43.5), (125.5, 41.0), (119.0, 40.5), (115.5, 38.5), (114.5, 34.5), (117.5, 33.0), (119.0, 35.5), (120.5, 39.5), (118.0, 44.0), (119.5, 47.5)]),
]


def fig11_5_crops():
    fig, ax = new_map_axes((10.5, 10.8))
    _map_base(ax)
    _prov_frame(ax)
    for name, color, poly in CROP_ZONES:
        xs, ys = zip(*[to_albers(lo, la) for lo, la in poly])
        ax.add_patch(MplPolygon(list(zip(xs, ys)), closed=True, fc=color,
                                alpha=0.35, ec=color, lw=1.3, zorder=5))
    handles = [Patch(fc=c, alpha=0.45, label=n) for n, c, _ in CROP_ZONES]
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.005, 0.08),
              fontsize=9, framealpha=0.92, edgecolor="#cccccc",
              title="作物优势区", title_fontsize=9.5)
    set_extent_from(ax, _prov_frame(ax) if False else
                    __import__("geopandas").read_file(
                        os.path.join(DATA, "boundaries", "datav",
                                     "100000_full.json")).to_crs(ALBERS))
    add_title(ax, "三大粮食作物优势区（示意）",
              "“南稻北麦”的传统格局与东北玉米、粳稻的崛起")
    save_fig(fig, ax, "fig11-5_粮食作物优势区.png",
             footer="优势区为示意勾绘，依据农业农村部《全国优势农产品区域布局规划》；底图：AWS Terrain Tiles\n"
                    "示意地图，不作为权属划界依据")


# ---------------------------------------------------------------- fig 11-6
def fig11_6_energy():
    years = [1978, 2000, 2010, 2020, 2024]
    coal = [70.7, 68.5, 69.2, 56.8, 53.2]
    clean = [3.4, 7.3, 9.4, 15.9, 19.8]
    fig, ax = plt.subplots(figsize=(9.6, 5.0))
    ax.plot(years, coal, color="#616a6b", lw=2.2, marker="o", ms=5,
            label="煤炭占比", zorder=3)
    ax.plot(years, clean, color="#1e8449", lw=2.2, marker="s", ms=5,
            label="非化石能源占比", zorder=3)
    for x, y in zip(years, coal):
        ax.annotate(f"{y:.1f}", (x, y), textcoords="offset points",
                    xytext=(0, -16), fontsize=8.4, ha="center", color="#616a6b")
    for x, y in zip(years, clean):
        ax.annotate(f"{y:.1f}", (x, y), textcoords="offset points",
                    xytext=(0, 9), fontsize=8.4, ha="center", color="#1e8449")
    ax.set_xlim(1972, 2030)
    ax.set_ylim(0, 80)
    ax.grid(axis="y", color="#dde3e8", lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#999999")
    ax.spines["left"].set_color("#999999")
    ax.set_ylabel("占一次能源消费比重（%）", fontsize=9, color="#666666")
    ax.legend(loc="upper right", fontsize=9.2, framealpha=0.92,
              edgecolor="#cccccc")
    fig.text(0.02, 0.982, "能源消费结构：煤炭退场与非化石能源登场", fontsize=14.5,
             fontweight="bold", color=C_TEXT, va="top")
    fig.text(0.02, 0.952, "煤炭占比近十五年下降约 16 个百分点；2024 年非化石能源接近 20%",
             fontsize=9.3, color="#666666", va="top")
    fig.text(0.02, 0.012,
             "数据来源：国家统计局、国家能源局公开数据（约数）；2030 年非化石能源目标 25%",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 0.94))
    save_volume_figure(fig, os.path.join(OUT, "fig11-6_能源消费结构.png"), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 11-7
STRATEGY_LINES = {
    "长江经济带": ("#1f618d", [(91.0, 29.6), (100.0, 28.5), (106.5, 29.6), (111.3, 30.6), (114.3, 30.6), (118.8, 32.1), (121.5, 31.4)]),
    "黄河流域": ("#b9770e", [(101.0, 36.0), (103.8, 36.1), (106.3, 38.5), (110.2, 40.3), (111.2, 40.3), (110.5, 37.0), (110.6, 35.0), (113.6, 34.8), (117.0, 36.2), (119.0, 37.7)]),
    "京津冀协同": ("#c0392b", [(116.4, 39.9), (117.2, 39.1), (119.6, 39.0)]),
    "长三角一体化": ("#8e44ad", [(118.8, 32.1), (120.5, 31.2), (121.5, 30.0), (120.2, 30.3)]),
    "粤港澳大湾区": ("#1e8449", [(113.3, 23.1), (114.1, 22.6), (113.6, 22.2)]),
    "成渝双城": ("#6c3483", [(104.1, 30.6), (106.6, 29.6)]),
}


def fig11_7_strategy():
    fig, ax = new_map_axes((10.5, 10.8))
    _map_base(ax)
    _prov_frame(ax)
    for name, (c, pts) in STRATEGY_LINES.items():
        xs, ys = zip(*[to_albers(lo, la) for lo, la in pts])
        ax.plot(xs, ys, color=c, lw=3.4, alpha=0.7, solid_capstyle="round",
                zorder=6)
        label_xy = pts[len(pts) // 2]
        x, y = to_albers(*label_xy)
        ax.text(x, y + 60000, name, fontsize=8.6, color=c, ha="center",
                zorder=8,
                bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none",
                          alpha=0.85))
    set_extent_from(ax, _prov_frame(ax) if False else
                    __import__("geopandas").read_file(
                        os.path.join(DATA, "boundaries", "datav",
                                     "100000_full.json")).to_crs(ALBERS))
    add_title(ax, "重大区域发展战略的空间布局",
              "“四板块 + 五战略”：西部大开发、东北振兴、中部崛起、东部率先，叠加五大跨区域战略")
    save_fig(fig, ax, "fig11-8_重大区域战略.png",
             footer="战略覆盖范围为示意勾绘；底图：AWS Terrain Tiles；投影：Albers 等积圆锥\n"
                    "示意地图，不作为权属划界依据")


# ---------------------------------------------------------------- fig 12-1
def fig12_1_network():
    rail = [(1949, 2.18), (1978, 5.17), (2000, 6.87), (2010, 9.12),
            (2020, 14.63), (2024, 16.20)]
    hsr = [(2008, 0.07), (2015, 1.98), (2020, 3.79), (2024, 4.80)]
    road = [(1949, 8.07), (1978, 89.0), (2000, 140.3), (2010, 400.8),
            (2024, 549.0)]
    expr = [(1988, 0.01), (2000, 1.63), (2010, 7.41), (2024, 19.07)]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.2, 4.4))
    ax1.plot([p[0] for p in rail], [p[1] for p in rail], color="#c0392b", lw=2.2,
             marker="o", ms=4.5, label="铁路营业里程")
    ax1.plot([p[0] for p in hsr], [p[1] for p in hsr], color="#8e44ad", lw=2.2,
             marker="s", ms=4.5, label="其中：高铁")
    ax1.annotate("2024：16.2 万 km\n（高铁 4.8 万 km，世界第一）",
                 xy=(2024, 16.2), xytext=(1978, 13.5), fontsize=8.6,
                 color="#8e2a1e",
                 arrowprops=dict(arrowstyle="->", color="#888888", lw=0.9))
    ax1.set_xlim(1946, 2028)
    ax1.set_ylim(0, 20)
    ax1.legend(loc="upper left", fontsize=8.8, framealpha=0.92,
               edgecolor="#cccccc")
    ax1.set_title("铁路（万 km）", fontsize=10.5, color=C_TEXT)
    ax2.plot([p[0] for p in road], [p[1] for p in road], color="#2e86c1", lw=2.2,
             marker="o", ms=4.5, label="公路总里程")
    ax2.plot([p[0] for p in expr], [p[1] for p in expr], color="#b9770e", lw=2.2,
             marker="s", ms=4.5, label="其中：高速公路")
    ax2.annotate("2024：549 万 km\n（高速公路 19.1 万 km，世界第一）",
                 xy=(2024, 549), xytext=(1988, 430), fontsize=8.6,
                 color="#1b4f72",
                 arrowprops=dict(arrowstyle="->", color="#888888", lw=0.9))
    ax2.set_xlim(1946, 2028)
    ax2.set_ylim(0, 620)
    ax2.legend(loc="upper left", fontsize=8.8, framealpha=0.92,
               edgecolor="#cccccc")
    ax2.set_title("公路（万 km）", fontsize=10.5, color=C_TEXT)
    for ax in (ax1, ax2):
        ax.grid(axis="y", color="#dde3e8", lw=0.7, zorder=0)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color("#999999")
    fig.text(0.02, 0.982, "中国交通网络的世纪增长", fontsize=14.5,
             fontweight="bold", color=C_TEXT, va="top")
    fig.text(0.02, 0.952, "高铁与高速公路营业里程均居世界第一", fontsize=9.3,
             color="#666666", va="top")
    fig.text(0.02, 0.012,
             "数据来源：交通运输部《交通运输行业发展统计公报》（2024 年）", fontsize=8,
             color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 0.93))
    save_volume_figure(fig, os.path.join(OUT, "fig12-1_交通网络增长.png"), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 12-2
def fig12_2_freight():
    labels = ["公路", "水运", "铁路", "管道", "民航"]
    vals = [72.9, 16.7, 9.2, 1.2, 0.01]
    colors = ["#e59866", "#2e86c1", "#c0392b", "#7d3c98", "#bdc3c7"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.0, 5.5),
                                   gridspec_kw={"width_ratios": [1, 1.2]})
    w, _ = ax1.pie(vals, colors=colors, startangle=90, counterclock=False,
                   wedgeprops=dict(width=0.42, edgecolor="white"))
    ax1.legend(w, [f"{l}  {v}%" for l, v in zip(labels, vals)], loc="center",
               fontsize=9, frameon=False)
    ax1.set_title("货运量结构（2024 年）", fontsize=10.5,
                  color=C_TEXT)
    ports = [("宁波舟山", 13.24), ("唐山", 8.42), ("上海", 7.76), ("青岛", 7.06),
             ("广州", 6.75), ("苏州", 5.93), ("日照", 5.93), ("天津", 5.60)]
    ports = sorted(ports, key=lambda p: p[1])
    ax2.barh([p[0] for p in ports], [p[1] for p in ports], color="#2e86c1",
             height=0.6, zorder=3)
    for i, (n, v) in enumerate(ports):
        ax2.text(v + 0.15, i, f"{v:.2f}", va="center", fontsize=8.8,
                 color=C_TEXT, zorder=4)
    ax2.set_xlim(0, 15.5)
    ax2.set_title("沿海港口货物吞吐量前八（亿吨，2023 年）", fontsize=10.5,
                  color=C_TEXT)
    ax2.grid(axis="x", color="#dde3e8", lw=0.7, zorder=0)
    ax2.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax2.spines[s].set_visible(False)
    ax2.spines["bottom"].set_color("#999999")
    ax2.tick_params(axis="y", length=0, labelsize=9.2)
    fig.text(0.02, 0.982, "货运结构与世界级港口", fontsize=14.5,
             fontweight="bold", color=C_TEXT, va="top")
    fig.text(0.02, 0.952, "公路承担七成货运量；全球货物吞吐量前十的港口中国占八席",
             fontsize=9.3, color="#666666", va="top")
    fig.text(0.02, 0.012,
             "数据来源：交通运输部《2024 年交通运输行业发展统计公报》、各港务集团公开数据（约数）",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 0.93))
    save_volume_figure(fig, os.path.join(OUT, "fig12-2_货运结构与港口.png"), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 12-3
# 干线走向用「枢纽 + 沿线重要节点」的经纬度序列描述。
# 旧实现只连枢纽城市（北京—济南—南京—上海），在图面上就是几根笔直的长线，
# 与真实高铁走向（经德州、徐州、蚌埠，绕太湖东侧）差别明显，看起来像直尺画出来的。
# 这里补入沿线真实车站所在城镇，并对折线做 Catmull-Rom 平滑。
_WP = {  # 沿线节点：名称 -> (经度, 纬度)
    "沧州": (116.84, 38.30), "德州": (116.36, 37.44), "曲阜": (116.99, 35.58),
    "徐州": (117.19, 34.26), "宿州": (116.96, 33.65), "蚌埠": (117.39, 32.92),
    "滁州": (118.32, 32.30), "镇江": (119.45, 32.20), "常州": (119.95, 31.81),
    "苏州": (120.58, 31.30), "盐城": (120.16, 33.35), "南通": (120.86, 31.98),
    "日照": (119.53, 35.42), "临沂": (118.36, 35.10), "潍坊": (119.16, 36.71),
    "淄博": (118.05, 36.81), "秦皇岛": (119.60, 39.94), "唐山": (118.18, 39.63),
    "锦州": (121.13, 41.10), "丹东": (124.38, 40.13), "温州": (120.70, 28.00),
    "台州": (121.42, 28.66), "宁德": (119.55, 26.67), "泉州": (118.68, 24.87),
    "汕头": (116.68, 23.35), "汕尾": (115.36, 22.79), "惠州": (114.41, 23.11),
    "茂名": (110.93, 21.66), "北海": (109.12, 21.48),
    "保定": (115.46, 38.87), "邢台": (114.51, 37.07), "邯郸": (114.54, 36.63),
    "安阳": (114.39, 36.10), "新乡": (113.93, 35.30), "许昌": (113.85, 34.04),
    "漯河": (114.03, 33.58), "驻马店": (114.02, 33.01), "信阳": (114.09, 32.15),
    "岳阳": (113.13, 29.36), "衡阳": (112.57, 26.89), "郴州": (113.03, 25.78),
    "韶关": (113.60, 24.81),
    "大同": (113.30, 40.08), "包头": (109.84, 40.66), "张家口": (114.88, 40.82),
    "中卫": (105.19, 37.51), "天水": (105.72, 34.58), "张掖": (100.45, 38.93),
    "酒泉": (98.49, 39.73), "哈密": (93.51, 42.83), "吐鲁番": (89.19, 42.95),
    "洛阳": (112.45, 34.62), "宝鸡": (107.24, 34.36),
    "宜昌": (111.29, 30.69), "万州": (108.41, 30.81), "恩施": (109.49, 30.27),
    "九江": (116.00, 29.71), "上饶": (117.97, 28.45), "金华": (119.65, 29.08),
    "杭州东": (120.21, 30.29), "怀化": (110.00, 27.55), "凯里": (107.98, 26.58),
    "曲靖": (103.80, 25.49), "六盘水": (104.85, 26.59),
    "赣州": (114.93, 25.83), "吉安": (114.99, 27.11), "龙岩": (117.02, 25.08),
    "常德": (111.70, 29.03), "黔江": (108.77, 29.53),
    "阜阳": (115.81, 32.89), "商丘": (115.65, 34.44), "衡水": (115.67, 37.74),
    "桂林": (110.29, 25.27), "柳州": (109.41, 24.33), "梧州": (111.30, 23.48),
    "百色": (106.62, 23.90), "兴义": (104.90, 25.09), "钦州": (108.65, 21.98),
    "牡丹江": (129.63, 44.55), "齐齐哈尔": (123.92, 47.35),
    "海拉尔": (119.74, 49.22), "松原": (124.83, 45.14), "赤峰": (118.89, 42.26),
    "通辽": (122.24, 43.65), "汉中": (107.03, 33.07), "广元": (105.84, 32.44),
    "绵阳": (104.68, 31.47), "西昌": (102.27, 27.90), "攀枝花": (101.72, 26.58),
    "安康": (109.03, 32.68), "延安": (109.49, 36.59), "邵阳": (111.47, 27.24),
    "永州": (111.61, 26.42), "益阳": (112.36, 28.55), "焦作": (113.24, 35.22),
    "长治": (113.12, 36.20), "襄阳": (112.14, 32.04),
    "平顶山": (113.19, 33.77), "安庆": (117.05, 30.53),
}


def _pt(name):
    """节点坐标：优先取全书统一城市表，其次取沿线补充表。"""
    if name in CITY_XY:
        return CITY_XY[name]
    return _WP[name]


def _smooth(pts, n=14):
    """Catmull-Rom 样条加密，去掉折线的「直尺」感。

    pts 为投影后的坐标序列；端点重复一次以确定切向。
    """
    if len(pts) < 3:
        return [p[0] for p in pts], [p[1] for p in pts]
    P = [pts[0]] + list(pts) + [pts[-1]]
    xs, ys = [], []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            for a, b, c, d, out in ((p0[0], p1[0], p2[0], p3[0], xs),
                                    (p0[1], p1[1], p2[1], p3[1], ys)):
                out.append(0.5 * ((2 * b) + (-a + c) * t
                                  + (2 * a - 5 * b + 4 * c - d) * t2
                                  + (-a + 3 * b - 3 * c + d) * t3))
    xs.append(P[-2][0])
    ys.append(P[-2][1])
    return xs, ys


RAIL_LINES = {  # 通道 -> (颜色, 沿线节点序列)
    "京沪通道": ("#c0392b", ["北京", "天津", "沧州", "德州", "济南", "曲阜",
                          "徐州", "蚌埠", "滁州", "南京", "镇江", "常州",
                          "无锡", "苏州", "上海"]),
    "京哈—京港澳通道": ("#1f618d", ["哈尔滨", "长春", "沈阳", "锦州", "秦皇岛",
                                 "唐山", "北京", "保定", "石家庄", "邢台",
                                 "邯郸", "安阳", "新乡", "郑州", "许昌",
                                 "漯河", "驻马店", "信阳", "武汉", "岳阳",
                                 "长沙", "衡阳", "郴州", "韶关", "广州",
                                 "深圳", "香港"]),
    "京港（台）通道": ("#7d3c98", ["北京", "衡水", "商丘", "阜阳", "合肥",
                                "九江", "南昌", "吉安", "赣州", "惠州",
                                "深圳", "香港"]),
    "京昆通道": ("#6c3483", ["北京", "保定", "石家庄", "太原", "西安",
                          "汉中", "广元", "绵阳", "成都", "西昌",
                          "攀枝花", "昆明"]),
    "呼南通道": ("#b03a2e", ["呼和浩特", "大同", "太原", "长治", "焦作",
                          "郑州", "襄阳", "常德", "益阳", "邵阳",
                          "永州", "桂林", "柳州", "南宁"]),
    "包（银）海通道": ("#af601a", ["包头", "延安", "西安", "安康", "重庆",
                                "贵阳", "南宁", "钦州", "湛江", "海口"]),
    "兰（西）广通道": ("#b9770e", ["西宁", "兰州", "广元", "重庆", "贵阳",
                                "桂林", "梧州", "广州"]),
    "沿海通道": ("#1e8449", ["丹东", "大连", "秦皇岛", "天津", "潍坊",
                          "青岛", "日照", "连云港", "盐城", "南通",
                          "上海", "宁波", "台州", "温州", "宁德",
                          "福州", "泉州", "厦门", "汕头", "汕尾",
                          "深圳", "茂名", "湛江", "北海"]),
    "绥满通道": ("#5d6d7e", ["绥芬河", "牡丹江", "哈尔滨", "齐齐哈尔",
                          "海拉尔", "满洲里"]),
    "京兰通道": ("#117a65", ["北京", "张家口", "呼和浩特", "包头", "银川",
                          "中卫", "兰州"]),
    "青银通道": ("#148f77", ["青岛", "潍坊", "淄博", "济南", "石家庄",
                          "太原", "银川"]),
    "陆桥通道": ("#8e44ad", ["连云港", "徐州", "商丘", "郑州", "洛阳",
                          "西安", "宝鸡", "天水", "兰州", "西宁",
                          "张掖", "酒泉", "哈密", "吐鲁番", "乌鲁木齐"]),
    "沿江通道": ("#2e86c1", ["上海", "南京", "合肥", "武汉", "宜昌",
                          "恩施", "万州", "重庆", "成都"]),
    "沪昆通道": ("#c0392b", ["上海", "杭州东", "金华", "上饶", "南昌",
                          "长沙", "怀化", "凯里", "贵阳", "六盘水",
                          "曲靖", "昆明"]),
    "厦渝通道": ("#7d8f3f", ["厦门", "龙岩", "赣州", "长沙", "常德",
                          "黔江", "重庆"]),
    "广昆通道": ("#a04000", ["广州", "梧州", "南宁", "百色", "兴义",
                          "昆明"]),
}

# 通道名标注锚点（用节点名，标在该节点南侧 1.1°）
RAIL_LABEL_AT = {
    "京沪通道": "德州", "京哈—京港澳通道": "郑州", "京港（台）通道": "赣州",
    "京昆通道": "广元", "呼南通道": "常德", "包（银）海通道": "贵阳",
    "兰（西）广通道": "桂林", "沿海通道": "温州", "绥满通道": "齐齐哈尔",
    "京兰通道": "包头", "青银通道": "太原", "陆桥通道": "酒泉",
    "沿江通道": "恩施", "沪昆通道": "怀化", "厦渝通道": "常德",
    "广昆通道": "百色",
}


def _hsr_legend(ax, loc=(0.015, 0.015)):
    """通道图例。

    16 条通道若都写成图内文字，在郑州—武汉—长沙这种枢纽密集区必然叠成一团
    （实测 8 个通道名互相压字）。改为两列图例放在图幅左下空白处，
    图内只保留线路与城市名，可读性最好，也避免文字盖住线位。
    """
    from matplotlib.lines import Line2D
    handles = [Line2D([0], [0], color=c, lw=2.4, label=n)
               for n, (c, _) in RAIL_LINES.items()]
    leg = ax.legend(handles=handles, loc="lower left", bbox_to_anchor=loc,
                    ncol=2, fontsize=7.4, framealpha=0.94,
                    edgecolor="#cccccc", title="“八纵八横”通道", title_fontsize=8.2,
                    handlelength=2.0, columnspacing=0.9, labelspacing=0.42,
                    borderpad=0.6)
    leg.set_zorder(30)
    return leg


RAIL_HUBS_MAJOR = ["北京", "上海", "广州", "武汉", "西安", "成都",
                   "重庆", "郑州", "兰州", "乌鲁木齐"]
RAIL_HUBS_MID = ["哈尔滨", "沈阳", "南京", "杭州", "长沙", "昆明", "贵阳",
                 "南宁", "福州", "厦门", "青岛", "济南", "太原", "合肥",
                 "南昌", "石家庄", "呼和浩特", "银川", "西宁", "海口",
                 "深圳", "长春"]


def fig12_3_hsr():
    dem, extent, prov, dash = _dem_base()
    # 按数据范围定画幅比例：set_aspect("equal") 下画幅与数据比例不一致，
    # axes 内会留出大片纯色空边（看起来像"海面漫到陆地上方"）。
    minx, miny, maxx, maxy = prov.total_bounds
    ax_ratio = (maxx - minx) / (maxy - miny)
    figsize = (10.6 * ax_ratio, 10.6)
    fig, ax = new_map_axes(figsize)
    ax.set_facecolor(C_SEA)
    ax.imshow(_relief(dem), extent=extent, origin="upper",
              interpolation="bilinear", zorder=1)
    draw_borders(ax, prov, dash, z=3)

    for name, (c, nodes) in RAIL_LINES.items():
        pts = [to_albers(*_pt(n)) for n in nodes]
        xs, ys = _smooth(pts)
        ax.plot(xs, ys, color=c, lw=1.9, alpha=0.92, solid_capstyle="round",
                solid_joinstyle="round", zorder=6)

    placer = LabelPlacer(ax, fig)
    for ct in RAIL_HUBS_MAJOR + RAIL_HUBS_MID:
        if ct not in CITY_XY:
            continue
        x, y = to_albers(*CITY_XY[ct])
        major = ct in RAIL_HUBS_MAJOR
        ax.plot([x], [y], "o", ms=3.8 if major else 3.0, mfc="white",
                mec="#2c3e50", mew=0.95, zorder=9)
        placer.add(x, y, ct, color="#1a1a1a", fs=8.6 if major else 7.8,
                   priority=0 if major else 1,
                   weight="bold" if major else "normal",
                   leader=False, max_radius=2.45, zorder=14)

    set_extent_from(ax, prov)
    reserve_axes_boxes(placer, ax, [(0.00, 0.00, 0.30, 0.26)])
    placer.flush()

    _hsr_legend(ax)
    add_title(ax, "“八纵八横”高速铁路网",
              "干线经沿线主要节点城市；2024 年高铁营业里程 4.8 万 km，居世界第一")
    save_fig(fig, ax, "fig12-3_八纵八横高铁网.png",
             footer="线路按《中长期铁路网规划》通道走向、经沿线节点城市描绘，为走向示意而非精确线位；"
                    "底图：AWS Terrain Tiles；投影：Albers 等积圆锥\n"
                    "示意地图，不作为权属划界依据")


if __name__ == "__main__":
    setup()
    fig10_1_pyramid()
    fig10_2_megacities()
    fig10_3_clusters()
    fig10_4_cluster_compare()
    fig11_1_gdp()
    fig11_2_prov_gdp()
    fig11_3_boards()
    fig11_4_grain()
    fig11_5_crops()
    fig11_6_energy()
    fig11_7_strategy()
    fig12_1_network()
    fig12_2_freight()
    fig12_3_hsr()
    print("ch10-12 done")
