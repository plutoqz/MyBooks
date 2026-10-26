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
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Patch, Polygon as MplPolygon

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import (ALBERS, C_CHINA, C_SEA, C_TEXT, DATA, DPI, FIGURES,
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


def _prov_frame(ax, fill=None):
    import geopandas as gpd
    gdf = gpd.read_file(os.path.join(DATA, "boundaries", "datav",
                                     "100000_full.json"))
    prov = gdf[gdf["name"].notna() & (gdf["name"].str.len() > 0)].to_crs(ALBERS)
    dash = gdf[gdf["name"].isna() | (gdf["name"].str.len() == 0)].to_crs(ALBERS)
    prov.plot(ax=ax, color=fill, edgecolor="#7f7f7f", linewidth=0.4, zorder=3) \
        if fill else prov.boundary.plot(ax=ax, color="#5a5a5a", linewidth=0.28,
                                        alpha=0.5, zorder=3)
    if len(dash):
        dash.plot(ax=ax, facecolor="none", edgecolor="#3b5872", linewidth=0.7,
                  ls="--", zorder=4)
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
def fig10_1_pyramid():
    tiers = [("超大城市\n（>1 000 万）", 7), ("特大城市\n（500—1 000 万）", 14),
             ("Ⅰ型大城市\n（300—500 万）", 14), ("Ⅱ型大城市\n（100—300 万）", 71),
             ("中等城市\n（50—100 万）", 116), ("Ⅰ型小城市\n（<50 万）", 139)]
    fig, ax = plt.subplots(figsize=(9.4, 5.6))
    total = sum(t[1] for t in tiers)
    left = (total - tiers[0][1]) / 2
    colors = ["#c0392b", "#e67e22", "#f1c40f", "#7dcea0", "#5dade2", "#a9cce3"]
    for i, (name, n) in enumerate(tiers):
        width = n
        ax.add_patch(MplPolygon([(left, i), (left + width, i),
                                 (left + width + 0, i + 1),
                                 (left, i + 1)],
                                closed=True, fc=colors[i], ec="white", lw=1.2,
                                zorder=3))
        ax.text(left + width / 2, i + 0.5, f"{name}\n{n} 个", ha="center",
                va="center", fontsize=9.2, color="#1a1a1a" if i > 1 else "white",
                zorder=4, linespacing=1.4)
        left += 0
        left = (total - width) / 2 if False else left
        left = (total - width) / 2
    ax.set_xlim(0, total)
    ax.set_ylim(0, len(tiers))
    ax.axis("off")
    fig.text(0.02, 0.982, "中国城市规模金字塔（七普城区人口口径）", fontsize=14.5,
             fontweight="bold", color=C_TEXT, va="top")
    fig.text(0.02, 0.945, "城市规模按城区常住人口划分（国务院 2014 年标准）；底座小城市数量最多",
             fontsize=9.3, color="#666666", va="top")
    fig.text(0.02, 0.012,
             "数据来源：住房和城乡建设部《2020 年城市建设统计年鉴》与第七次人口普查（约数）",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 0.93))
    fig.savefig(os.path.join(OUT, "fig10-1_城市规模金字塔.png"), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 10-2
def fig10_2_megacities():
    fig, ax = new_map_axes((10.5, 10.8))
    _map_base(ax)
    _prov_frame(ax)
    mega = ["上海", "北京", "深圳", "重庆", "广州", "成都", "天津"]
    huge = ["武汉", "东莞", "西安", "杭州", "佛山", "南京", "沈阳", "青岛",
            "济南", "长沙", "哈尔滨", "郑州", "昆明", "大连"]
    for c in mega:
        _city(ax, c, r_deg=1.35, fs=8.8)
    for c in huge:
        _city(ax, c, r_deg=0.85, fs=7.6, color="#e67e22")
    legend_elems = [Circle((0, 0), 1, fc="#8e2a1e", alpha=0.75,
                           label="超大城市（城区人口 >1 000 万，7 个）"),
                    Circle((0, 0), 1, fc="#e67e22", alpha=0.75,
                           label="特大城市（500 万—1 000 万，14 个）")]
    ax.legend(handles=legend_elems, loc="lower left", bbox_to_anchor=(0.005, 0.08),
              fontsize=8.8, framealpha=0.92, edgecolor="#cccccc")
    set_extent_from(ax, _prov_frame(ax) if False else
                    __import__("geopandas").read_file(
                        os.path.join(DATA, "boundaries", "datav",
                                     "100000_full.json")).to_crs(ALBERS))
    add_title(ax, "超大城市与特大城市的分布",
              "7 座超大城市与 14 座特大城市全部位于胡焕庸线东南侧")
    save_fig(fig, ax, "fig10-2_超大特大城市分布.png",
             footer="底图：DataV.GeoAtlas 与 AWS Terrain Tiles；圆面积示意人口规模\n"
                    "示意地图，不作为权属划界依据")


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
    fig, ax = new_map_axes((10.5, 10.8))
    _map_base(ax)
    _prov_frame(ax)
    for name, (lo, la, r) in CLUSTERS.items():
        x, y = to_albers(lo, la)
        ax.add_patch(Circle((x, y), r * 111000 * 0.55, fc="#2e86c1", ec="#1b4f72",
                            lw=1.0, alpha=0.35, zorder=6))
        ax.text(x, y, name, fontsize=7.8, color="#1b4f72", ha="center",
                va="center", zorder=8)
    set_extent_from(ax, _prov_frame(ax) if False else
                    __import__("geopandas").read_file(
                        os.path.join(DATA, "boundaries", "datav",
                                     "100000_full.json")).to_crs(ALBERS))
    add_title(ax, "全国主要城市群的分布",
              "“19+2”城市群格局；圆圈为示意范围，五大国家级城市群承担国家战略")
    save_fig(fig, ax, "fig10-3_主要城市群分布.png",
             footer="依据《“十四五”规划纲要》城市群布局示意勾绘；底图：AWS Terrain Tiles\n"
                    "示意地图，不作为权属划界依据")


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
    fig.savefig(os.path.join(OUT, "fig10-4_五大城市群对比.png"), dpi=DPI)
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
    fig.savefig(os.path.join(OUT, "fig11-1_经济总量与人均.png"), dpi=DPI)
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
    fig.savefig(os.path.join(OUT, "fig11-2_分省GDP排序.png"), dpi=DPI)
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
    fig.savefig(os.path.join(OUT, "fig11-3_四大板块.png"), dpi=DPI)
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
    fig.savefig(os.path.join(OUT, "fig11-4_粮食产量.png"), dpi=DPI)
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
    fig.savefig(os.path.join(OUT, "fig11-6_能源消费结构.png"), dpi=DPI)
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
    save_fig(fig, ax, "fig11-7_重大区域战略.png",
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
    fig.savefig(os.path.join(OUT, "fig12-1_交通网络增长.png"), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 12-2
def fig12_2_freight():
    labels = ["公路", "水运", "铁路", "管道", "民航"]
    vals = [72.9, 16.7, 9.2, 1.2, 0.01]
    colors = ["#e59866", "#2e86c1", "#c0392b", "#7d3c98", "#bdc3c7"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.0, 4.2),
                                   gridspec_kw={"width_ratios": [1, 1.2]})
    w, _ = ax1.pie(vals, colors=colors, startangle=90, counterclock=False,
                   wedgeprops=dict(width=0.42, edgecolor="white"))
    ax1.legend(w, [f"{l}  {v}%" for l, v in zip(labels, vals)], loc="center",
               fontsize=9, frameon=False)
    ax1.set_title("货运量结构（2024 年，占全社会货运量）", fontsize=10.5,
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
    fig.savefig(os.path.join(OUT, "fig12-2_货运结构与港口.png"), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 12-3
RAIL_LINES = {
    "京沪通道": ("#c0392b", ["北京", "济南", "南京", "上海"]),
    "京哈—京港澳通道": ("#1f618d", ["哈尔滨", "沈阳", "北京", "郑州", "武汉", "广州", "香港"]),
    "京昆通道": ("#6c3483", ["北京", "石家庄", "太原", "西安", "成都", "昆明"]),
    "兰（西）广通道": ("#b9770e", ["西宁", "兰州", "成都", "贵阳", "广州"]),
    "沿海通道": ("#1e8449", ["哈尔滨", "大连", "青岛", "上海", "福州", "深圳", "湛江"]),
    "陆桥通道": ("#8e44ad", ["连云港", "郑州", "西安", "兰州", "乌鲁木齐"]),
    "沪昆通道": ("#c0392b", ["上海", "南昌", "长沙", "贵阳", "昆明"]),
    "沿江通道": ("#2e86c1", ["上海", "南京", "合肥", "武汉", "重庆", "成都"]),
    "青银通道": ("#117a65", ["青岛", "济南", "石家庄", "太原", "银川"]),
    "厦渝通道": ("#7d8f3f", ["厦门", "长沙", "重庆"]),
    "广昆通道": ("#a04000", ["广州", "南宁", "昆明"]),
    "绥满通道": ("#5d6d7e", ["绥芬河", "哈尔滨", "满洲里"]),
}


def fig12_3_hsr():
    fig, ax = new_map_axes((10.5, 10.8))
    _map_base(ax)
    _prov_frame(ax)
    for name, (c, cities) in RAIL_LINES.items():
        xs, ys = zip(*[to_albers(*CITY_XY[ct]) for ct in cities])
        ax.plot(xs, ys, color=c, lw=2.0, alpha=0.85, solid_capstyle="round",
                zorder=6)
        override = {"京昆通道": "西安", "兰（西）广通道": "贵阳",
                    "沿江通道": "武汉", "青银通道": "太原",
                    "京哈—京港澳通道": "郑州"}
        mid = override.get(name, cities[len(cities) // 2])
        lo, la = CITY_XY[mid]
        ax.text(*to_albers(lo, la - 1.1), name, fontsize=7.6, color=c,
                ha="center", zorder=8,
                bbox=dict(boxstyle="round,pad=0.14", fc="white", ec="none",
                          alpha=0.85))
    for ct, (lo, la) in CITY_XY.items():
        if ct in ("绥芬河", "满洲里"):
            continue
    set_extent_from(ax, _prov_frame(ax) if False else
                    __import__("geopandas").read_file(
                        os.path.join(DATA, "boundaries", "datav",
                                     "100000_full.json")).to_crs(ALBERS))
    add_title(ax, "“八纵八横”高速铁路网（简化示意）",
              "以中心城市为节点的干线通道；2024 年高铁营业里程 4.8 万 km，居世界第一")
    save_fig(fig, ax, "fig12-3_八纵八横高铁网.png",
             footer="线路为简化示意（直线连接枢纽城市），依据《中长期铁路网规划》；底图：AWS Terrain Tiles\n"
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
