# -*- coding: utf-8 -*-
"""第 13 章 区域分论 —— 总论（13.1—13.4）图件。

图面规范：地图主体内不放置任何文字说明，仅保留编号标记；
全部名称与说明以编号列表置于图幅下方（图外）。

fig13-1 四大地理区域划分图          fig13-4 南方地区专题图
fig13-2 四大区域面积/人口/GDP占比   fig13-5 西北地区专题图
fig13-3 北方地区专题图              fig13-6 青藏地区专题图

底图：AWS Terrain 山体阴影（复用 ch03_terrain 缓存）；行政界线：DataV
GeoAtlas areas_v3；河流：Natural Earth 50m；气候界线坐标复用 ch04_climate。
"""
import os
import sys

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Polygon as MplPolygon

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import (ALBERS, C_SEA, C_TEXT, DATA, DPI, FIGURES, add_title,
                   new_map_axes, set_extent_from, setup)
from geo_features import (BASINS, CITIES, DESERTS, MOUNTAINS, PLAINS,
                          PLATEAUS, STAIR1)
from ch04_climate import PREC400, T1_0
from ch03_terrain import RES_A, load_cache, relief_rgba, to_albers

# ---------------------------------------------------------------- 四大区域（省级整体归组，教材口径）
REGION4 = {
    "北方": ["北京市", "天津市", "河北省", "山西省", "辽宁省", "吉林省",
             "黑龙江省", "山东省", "河南省", "陕西省"],
    "西北": ["内蒙古自治区", "甘肃省", "宁夏回族自治区", "新疆维吾尔自治区"],
    "青藏": ["青海省", "西藏自治区"],
    "南方": ["上海市", "江苏省", "浙江省", "安徽省", "福建省", "江西省",
             "湖北省", "湖南省", "广东省", "广西壮族自治区", "海南省",
             "重庆市", "四川省", "贵州省", "云南省", "香港特别行政区",
             "澳门特别行政区", "台湾省"],
}
R4_COLOR = {"北方": "#5d8aa8", "南方": "#6f9e6f", "西北": "#c8a45c",
            "青藏": "#9c6b7f"}

# 2023 年地区生产总值（亿元，附录 A 口径；港澳台按当地统计折算，约数）
GDP23 = {
    "北京市": 43760, "天津市": 16737, "河北省": 43944, "山西省": 25666,
    "内蒙古自治区": 24627, "辽宁省": 30209, "吉林省": 13532,
    "黑龙江省": 15884, "上海市": 47219, "江苏省": 128222, "浙江省": 82553,
    "安徽省": 47051, "福建省": 54355, "江西省": 32207, "山东省": 92069,
    "河南省": 59133, "湖北省": 55804, "湖南省": 50013, "广东省": 135673,
    "广西壮族自治区": 27202, "海南省": 7551, "重庆市": 30146,
    "四川省": 60133, "贵州省": 20865, "云南省": 30021, "西藏自治区": 2393,
    "陕西省": 33793, "甘肃省": 11864, "青海省": 3793, "宁夏回族自治区": 5315,
    "新疆维吾尔自治区": 19126, "香港特别行政区": 26900,
    "澳门特别行政区": 3300, "台湾省": 54000,
}

# 本脚本补充的地理要素坐标（暂不入共享库）
LOCAL_MTN = {
    "小兴安岭": [(126.6, 50.6), (128.6, 49.3), (129.6, 48.2)],
    "唐古拉山脉": [(91.0, 33.4), (94.0, 33.1), (97.0, 32.7)],
    "冈底斯山脉": [(81.0, 31.0), (85.0, 30.5), (89.0, 30.0)],
}
LOCAL_CITY = {
    "包头": (109.84, 40.66), "哈密": (93.51, 42.83), "敦煌": (94.66, 40.14),
    "日喀则": (88.88, 29.27), "二连浩特": (111.98, 43.65),
    "霍尔果斯": (80.40, 44.20),
}
FOOT_MAP = ("底图：AWS Terrain Tiles；行政界线：DataV.GeoAtlas areas_v3（2021.5，仅供学习交流）；投影：Albers 等积圆锥；"
            "示意地图，不作为权属划界依据")

# 编号标记：k=地形与山脉，r=河流，l=湖泊，c=城市，m=矿产，p=陆路口岸，h=海港
TAG_COLOR = {"k": "#a8432f", "r": "#1b4f72", "l": "#2471a3",
             "c": "#1a1a1a", "m": "#5d5d5d", "p": "#8a6d1f", "h": "#1f6f8b"}
KIND_NAME = {"k": "山脉与地形区", "r": "河流", "l": "湖泊", "c": "城市",
             "m": "主要矿产", "p": "陆路口岸", "h": "海港"}


# ---------------------------------------------------------------- 基础设施
def load_prov():
    gdf = gpd.read_file(os.path.join(DATA, "boundaries", "datav",
                                     "100000_full.json"))
    prov = gdf[gdf["name"].notna() & (gdf["name"].str.len() > 0)].to_crs(ALBERS)
    dash = gdf[gdf["name"].isna() | (gdf["name"].str.len() == 0)].to_crs(ALBERS)
    return prov, dash


def load_world_foreign():
    wld = gpd.read_file(os.path.join(DATA, "boundaries", "natural_earth",
                                     "ne_50m",
                                     "ne_50m_admin_0_countries.shp"))
    return wld[wld["ADMIN"] != "China"].to_crs(ALBERS)


def _dem_extent():
    dem, minx, maxy = load_cache()
    h, w = dem.shape
    return dem, (minx, minx + w * RES_A, maxy - h * RES_A, maxy)


def _dash_in_view(dash, ax):
    if not len(dash):
        return False
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    bx0, by0, bx1, by1 = dash.total_bounds
    return not (bx1 < x0 or bx0 > x1 or by1 < y0 or by0 > y1)


def draw_dash(ax, dash, z=4.8):
    if _dash_in_view(dash, ax):
        dash.plot(ax=ax, facecolor="none", edgecolor="#3b5872", linewidth=0.7,
                  ls="--", zorder=z)


def focus_base(ax, members, color, pad=0.05):
    """区域聚焦底图：境外与区外陆地平色淡出，区内保留晕渲并叠色。"""
    dem, extent = _dem_extent()
    ax.set_facecolor(C_SEA)
    ax.imshow(relief_rgba(dem), extent=extent, origin="upper",
              interpolation="bilinear", zorder=1)
    load_world_foreign().plot(ax=ax, color="#ecebe5", ec="none", zorder=2)
    prov, dash = load_prov()
    mem = prov[prov["name"].isin(members)]
    non = prov[~prov["name"].isin(members)]
    non.plot(ax=ax, color="#f3f1eb", ec="#b9b9b9", lw=0.25, zorder=2.6)
    mem.plot(ax=ax, fc=color, alpha=0.22, ec="none", zorder=4)
    mem.boundary.plot(ax=ax, color="#4a4a4a", lw=0.55, zorder=5)
    draw_dash(ax, dash)
    minx, miny, maxx, maxy = mem.total_bounds
    dx, dy = (maxx - minx), (maxy - miny)
    ax.set_xlim(minx - dx * pad, maxx + dx * pad)
    ax.set_ylim(miny - dy * pad, maxy + dy * pad)
    return prov, dash, mem


def _rivers(ax, mem):
    riv = gpd.read_file(os.path.join(DATA, "boundaries", "natural_earth",
                                     "ne_50m_rivers_lake_centerlines",
                                     "ne_50m_rivers_lake_centerlines.shp")
                        ).to_crs(ALBERS)
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    view = riv.cx[x0:x1, y0:y1]
    if not len(view):
        return
    joined = gpd.sjoin(view, mem[["geometry"]], predicate="intersects",
                       how="inner")
    sel = view.loc[sorted(set(joined.index))]
    lw = sel["scalerank"].map(lambda s: 1.15 if s <= 6 else 0.65)
    sel.plot(ax=ax, color="#3d6fa8", linewidth=lw, zorder=6)


def _mtn_line(ax, name, idx=0.5, lw=1.1):
    """山脉走向线（不带文字）。"""
    pts = LOCAL_MTN.get(name) or MOUNTAINS[name][1]
    xs, ys = zip(*[to_albers(lo, la) for lo, la in pts])
    ax.plot(xs, ys, color="#6b4f35", lw=lw, alpha=0.85, zorder=6.5)
    i = int(round(idx * (len(pts) - 1)))
    return pts[i]


def _terrain_poly(ax, name, poly, color, alpha=0.30):
    xs, ys = zip(*[to_albers(lo, la) for lo, la in poly])
    ax.add_patch(MplPolygon(list(zip(xs, ys)), closed=True, fc=color,
                            ec=color, lw=1.2, alpha=alpha, zorder=4.2))
    return float(np.mean([p[0] for p in poly])), float(np.mean([p[1] for p in poly]))


def _mark_dot(ax, lon, lat, star=False):
    x, y = to_albers(lon, lat)
    if star:
        ax.plot([x], [y], marker="*", ms=14, color="#b03a2e", mec="white",
                mew=0.6, zorder=9)
    else:
        ax.plot([x], [y], "o", ms=4.4, color="#1a1a1a", mec="white",
                mew=0.5, zorder=9)


def _mine_dot(ax, lon, lat):
    x, y = to_albers(lon, lat)
    ax.plot([x], [y], "s", ms=5.2, color="#5d5d5d", mec="white", mew=0.5,
            zorder=9)


def _port_dot(ax, lon, lat):
    x, y = to_albers(lon, lat)
    ax.plot([x], [y], "^", ms=6.5, color="#8a6d1f", mec="white", mew=0.5,
            zorder=9)


def _harbor_dot(ax, lon, lat):
    x, y = to_albers(lon, lat)
    ax.plot([x], [y], "^", ms=6.8, color="#1f6f8b", mec="white", mew=0.5,
            zorder=9)


def _lake_dot(ax, lon, lat):
    x, y = to_albers(lon, lat)
    ax.plot([x], [y], "o", ms=5.5, color="#3d6fa8", mec="white", mew=0.6,
            zorder=9)


class TagBoard:
    """收集编号标记，并在图下方生成两/三栏编号列表（图外说明）。"""

    def __init__(self):
        self.items = []

    def add(self, ax, kind, name, lon, lat, dot=None, dx=0.0, dy=0.0,
            leader=None):
        n = len(self.items) + 1
        if leader:
            tx, ty = to_albers(*leader)
            px, py = to_albers(lon, lat)
            ax.plot([px, tx], [py, ty], color="#666666", lw=0.6,
                    zorder=9.4)
            x, y = tx, ty
        else:
            x, y = to_albers(lon + dx, lat + dy)
        ax.plot([x], [y], "o", ms=10.5, mfc=TAG_COLOR[kind], mec="white",
                mew=0.8, zorder=9.6)
        ax.text(x, y, str(n), fontsize=6.8, color="white", ha="center",
                va="center", fontweight="bold", zorder=10)
        if dot == "star":
            _mark_dot(ax, lon, lat, star=True)
        elif dot == "mine":
            _mine_dot(ax, lon, lat)
        elif dot == "port":
            _port_dot(ax, lon, lat)
        elif dot == "harbor":
            _harbor_dot(ax, lon, lat)
        elif dot == "lake":
            _lake_dot(ax, lon, lat)
        elif dot == "city":
            _mark_dot(ax, lon, lat)
        self.items.append((kind, n, name))
        return n

    def render(self, fig, bottom=0.045, fs=9.2, cols=2, top=0.165, chunk=5):
        """在图下方绘制编号说明列表（组内不跨栏拆分）。

        bottom 是最下一行的下限（为图下脚注留位）：行为密度由
        (top - bottom) / 每栏行数 决定，避免行数多时压到脚注上。
        """
        groups = []  # 每组: [(text, bold)]
        for kind in ["k", "r", "l", "c", "m", "p", "h"]:
            gitems = [it for it in self.items if it[0] == kind]
            if not gitems:
                continue
            g = [(KIND_NAME[kind], True)]
            for i in range(0, len(gitems), chunk):
                part = gitems[i:i + chunk]
                g.append(("　".join(f"{n} {name}" for _, n, name in part),
                          False))
            groups.append(g)
        total = sum(len(g) for g in groups)
        per_col = (total + cols - 1) // cols
        columns, cur = [], []
        for g in groups:
            if cur and len(cur) + len(g) > per_col:
                columns.append(cur)
                cur = []
            cur.extend(g)
        if cur:
            columns.append(cur)
        # 列数超出预算时，反复合并相邻最小列，保证内容不丢
        while len(columns) > cols:
            sums = [len(columns[i]) + len(columns[i + 1])
                    for i in range(len(columns) - 1)]
            i = sums.index(min(sums))
            columns[i:i + 2] = [columns[i] + columns[i + 1]]
        lh = (top - bottom) / max(max(len(c) for c in columns), 1)
        for ci, part in enumerate(columns[:cols]):
            x = 0.02 + ci * (0.96 / cols)
            for j, (txt, bold) in enumerate(part):
                fig.text(x, top - j * lh, txt, fontsize=fs,
                         fontweight="bold" if bold else "normal",
                         color=C_TEXT if bold else "#444444",
                         ha="left", va="top")


def _save_with_legend(fig, fname, footer, rect_top=1.0, footer_y0=0.012):
    for a in fig.axes:
        a.set_xlabel("")
        a.set_ylabel("")
    lines = footer if isinstance(footer, (list, tuple)) else [footer]
    for i, t in enumerate(lines):
        fig.text(0.5, footer_y0 + (len(lines) - 1 - i) * 0.015, t,
                 ha="center", va="bottom", fontsize=8.0, color="#555555")
    fig.savefig(os.path.join(FIGURES, fname), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 13-1
def fig13_1_division():
    fig, ax = new_map_axes((10.5, 10.9))
    fig.subplots_adjust(bottom=0.245, top=0.99, left=0.01, right=0.99)
    dem, extent = _dem_extent()
    ax.set_facecolor(C_SEA)
    ax.imshow(relief_rgba(dem), extent=extent, origin="upper",
              interpolation="bilinear", zorder=1)
    load_world_foreign().plot(ax=ax, color="#ecebe5", ec="none", zorder=2)
    prov, dash = load_prov()
    for reg, names in REGION4.items():
        sub = prov[prov["name"].isin(names)]
        sub.plot(ax=ax, fc=R4_COLOR[reg], alpha=0.60, ec="white", lw=0.35,
                 zorder=4)
    draw_dash(ax, dash)

    styles = {"qhf": "-", "p400": (0, (5, 3)), "tp": (0, (4, 2, 1, 2))}
    for pts in [list(T1_0)]:
        xs, ys = zip(*[to_albers(lo, la) for lo, la in pts])
        ax.plot(xs, ys, color="#b03a2e", lw=2.1, ls=styles["qhf"], zorder=7)
    xs, ys = zip(*[to_albers(lo, la) for lo, la in PREC400[:8]])
    ax.plot(xs, ys, color="#b03a2e", lw=2.1, ls=styles["p400"], zorder=7)
    for pts in [STAIR1[:5], STAIR1[5:9], STAIR1[9:]]:
        xs, ys = zip(*[to_albers(lo, la) for lo, la in pts])
        ax.plot(xs, ys, color="#b03a2e", lw=2.1, ls=styles["tp"], zorder=7)

    set_extent_from(ax, prov, pad_frac=0.035)
    add_title(ax, "中国四大地理区域的划分",
              "北方 / 南方 / 西北 / 青藏——气候与地形两大主导因素交织的宏观分区")
    handles = [Patch(fc=R4_COLOR[r], alpha=0.8, ec="white", label=f"{r}地区")
               for r in ["北方", "南方", "西北", "青藏"]]
    handles += [
        Line2D([0], [0], color="#b03a2e", lw=2.1, ls=styles["qhf"],
               label="秦岭—淮河一线（北方/南方）"),
        Line2D([0], [0], color="#b03a2e", lw=2.1, ls=styles["p400"],
               label="400 mm 等降水量线（北方/西北）"),
        Line2D([0], [0], color="#b03a2e", lw=2.1, ls=styles["tp"],
               label="青藏高原边缘线（昆仑山—祁连山—横断山）"),
    ]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.02, 0.185),
               fontsize=9.2, frameon=False, ncol=2)
    _save_with_legend(fig, "fig13-1_四大地理区域划分图.png",
                      ["省级行政区按整体归组着色（北方 10、南方 18、西北 4、青藏 2）；界线为教材口径示意",
                       FOOT_MAP])


# ---------------------------------------------------------------- fig 13-2
def fig13_2_shares():
    df = pd.read_csv(os.path.join(DATA, "stats", "provinces.csv"))
    df["gdp"] = df["name"].map(GDP23)
    df["region4"] = df["name"].map({n: r for r, ns in REGION4.items()
                                    for n in ns})
    agg = df.groupby("region4").agg(area=("area_km2", "sum"),
                                    pop=("pop_2023w", "sum"),
                                    gdp=("gdp", "sum"))
    for c in ("area", "pop", "gdp"):
        agg[c + "_pct"] = agg[c] / agg[c].sum() * 100
    order = ["北方", "南方", "西北", "青藏"]
    print("== 四大区域合计（供正文引用） ==")
    for r in order:
        row = agg.loc[r]
        print(f"{r}: 面积 {row['area']/1e4:.0f} 万km² ({row['area_pct']:.1f}%) | "
              f"人口 {row['pop']:.0f} 万 ({row['pop_pct']:.1f}%) | "
              f"GDP {row['gdp']:.0f} 亿元 ({row['gdp_pct']:.1f}%)")

    metrics = [("area_pct", "陆地面积占比"), ("pop_pct", "常住人口占比"),
               ("gdp_pct", "GDP 占比（2023）")]
    fig, ax = plt.subplots(figsize=(9.6, 6.6))
    n = len(order)
    bh = 0.19
    for i, (col, lab) in enumerate(metrics):
        base = i
        for j, r in enumerate(order):
            v = agg.loc[r, col]
            y = base + (n - 1 - j) * bh - (n - 1) * bh / 2
            ax.barh(y, v, height=bh * 0.92, color=R4_COLOR[r],
                    edgecolor="white", lw=0.5, zorder=3)
            ax.text(v + 0.8, y, f"{v:.1f}%", va="center", ha="left",
                    fontsize=8.6, color=C_TEXT, zorder=4)
    ax.set_yticks(range(len(metrics)))
    ax.set_yticklabels([m[1] for m in metrics], fontsize=10.5)
    ax.set_xlim(0, max(agg["gdp_pct"].max(), agg["pop_pct"].max()) * 1.16)
    ax.set_ylim(-0.55, len(metrics) - 0.45)
    ax.grid(axis="x", color="#dde3e8", lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#999999")
    ax.tick_params(axis="x", labelsize=8.5, colors="#666666")
    ax.xaxis.set_major_formatter(
        plt.FuncFormatter(lambda v, p: f"{v:.0f}%"))
    handles = [Patch(fc=R4_COLOR[r], label=f"{r}地区") for r in order]
    ax.legend(handles=handles, loc="lower right", fontsize=9.2,
              framealpha=0.92, edgecolor="#cccccc")
    fig.text(0.02, 0.975, "四大区域的面积、人口与经济占比",
             fontsize=14.5, fontweight="bold", color=C_TEXT)
    fig.text(0.02, 0.945, "省级行政区整体归组口径；三组百分比分别以 34 个省级行政区合计为 100%",
             fontsize=9.2, color="#666666")
    fig.text(0.02, 0.02,
             "数据：人口为 2023 年末常住人口（《中国统计年鉴 2024》）；GDP 为 2023 年地区生产总值，港澳台按当地统计折算（约数）；面积按省级行政区划合计",
             fontsize=8, color="#555555")
    fig.tight_layout(rect=(0, 0.05, 1, 0.93))
    fig.savefig(os.path.join(FIGURES, "fig13-2_四大区域占比.png"), dpi=DPI)
    plt.close(fig)


# ---------------------------------------------------------------- fig 13-3
def fig13_3_north():
    fig, ax = new_map_axes((11.8, 10.4))
    fig.subplots_adjust(bottom=0.265, top=0.985, left=0.005, right=0.995)
    prov, dash, mem = focus_base(ax, REGION4["北方"], R4_COLOR["北方"],
                                 pad=0.06)
    _rivers(ax, mem)
    tb = TagBoard()

    _terrain_poly(ax, "东北平原", PLAINS["东北平原"], "#5d9b6c", 0.30)
    _terrain_poly(ax, "华北平原", PLAINS["华北平原"], "#5d9b6c", 0.30)
    _terrain_poly(ax, "黄土高原", PLATEAUS["黄土高原"], "#c08a58", 0.30)
    for name in ["大兴安岭", "小兴安岭", "长白山脉", "燕山", "太行山脉",
                 "吕梁山", "秦岭", "阴山山脉"]:
        _mtn_line(ax, name)
    tb.add(ax, "k", "大兴安岭", 123.3, 50.6)
    tb.add(ax, "k", "小兴安岭", 128.3, 49.4)
    tb.add(ax, "k", "长白山脉", 127.6, 42.8)
    tb.add(ax, "k", "燕山", 117.4, 40.7)
    tb.add(ax, "k", "太行山脉", 113.8, 37.2)
    tb.add(ax, "k", "吕梁山", 111.5, 37.6)
    tb.add(ax, "k", "秦岭", 107.4, 33.7)
    tb.add(ax, "k", "阴山山脉", 110.0, 41.0)
    tb.add(ax, "k", "辽东丘陵", 123.4, 40.9)
    tb.add(ax, "k", "山东丘陵", 120.5, 36.3)
    tb.add(ax, "k", "东北平原", 125.5, 46.0)
    tb.add(ax, "k", "华北平原", 116.2, 35.6)
    tb.add(ax, "k", "黄土高原", 108.2, 37.0)

    tb.add(ax, "r", "黑龙江", 127.4, 49.9)
    tb.add(ax, "r", "松花江", 128.8, 44.6)
    tb.add(ax, "r", "辽河", 122.3, 41.4)
    tb.add(ax, "r", "海河", 116.9, 38.9, dx=0.45, dy=0.25)
    tb.add(ax, "r", "黄河", 110.9, 40.2)
    tb.add(ax, "r", "淮河", 116.4, 32.6)

    tb.add(ax, "c", "北京（首都）", *CITIES["北京"], dot="star", dx=-0.55, dy=0.4)
    tb.add(ax, "c", "天津", *CITIES["天津"], dx=0.4, dy=-0.5)
    tb.add(ax, "c", "石家庄", *CITIES["石家庄"], dx=-0.35, dy=-0.3)
    tb.add(ax, "c", "太原", *CITIES["太原"])
    tb.add(ax, "c", "沈阳", *CITIES["沈阳"], dx=0.4, dy=0.3)
    tb.add(ax, "c", "长春", *CITIES["长春"])
    tb.add(ax, "c", "哈尔滨", *CITIES["哈尔滨"], dx=0.45, dy=0.25)
    tb.add(ax, "c", "济南", *CITIES["济南"], dx=0.3, dy=-0.4)
    tb.add(ax, "c", "郑州", *CITIES["郑州"])
    tb.add(ax, "c", "西安", *CITIES["西安"])

    tb.add(ax, "m", "大庆油田", 125.15, 46.6, dot="mine")
    tb.add(ax, "m", "大同煤矿", 113.0, 40.06, dot="mine")
    tb.add(ax, "m", "鞍山铁矿", 122.95, 41.1, dot="mine")
    tb.add(ax, "m", "胜利油田", 118.6, 37.42, dot="mine")

    add_title(ax, "北方地区",
              "东北平原、华北平原与黄土高原——温带季风气候下的黑土地与黄土地")
    tb.render(fig, bottom=0.265, fs=8.8, cols=3, top=0.255)
    _save_with_legend(fig, "fig13-3_北方地区专题图.png", FOOT_MAP)


# ---------------------------------------------------------------- fig 13-4
def fig13_4_south():
    fig, ax = new_map_axes((11.4, 11.2))
    fig.subplots_adjust(bottom=0.27, top=0.985, left=0.005, right=0.995)
    prov, dash, mem = focus_base(ax, REGION4["南方"], R4_COLOR["南方"],
                                 pad=0.06)
    _rivers(ax, mem)
    tb = TagBoard()

    _terrain_poly(ax, "长江中下游平原", PLAINS["长江中下游平原"], "#5d9b6c", 0.30)
    _terrain_poly(ax, "四川盆地", BASINS["四川盆地"], "#7fa8c9", 0.32)
    _terrain_poly(ax, "云贵高原", PLATEAUS["云贵高原"], "#c08a58", 0.30)
    for name in ["秦岭", "大巴山脉", "巫山", "雪峰山", "南岭", "武夷山脉",
                 "台湾山脉", "横断山脉"]:
        _mtn_line(ax, name)
    tb.add(ax, "k", "秦岭", 106.8, 33.8)
    tb.add(ax, "k", "大巴山脉", 108.3, 32.0)
    tb.add(ax, "k", "巫山", 110.0, 30.5)
    tb.add(ax, "k", "雪峰山", 110.9, 27.5)
    tb.add(ax, "k", "南岭", 112.9, 25.0)
    tb.add(ax, "k", "武夷山脉", 117.4, 26.8)
    tb.add(ax, "k", "台湾山脉", 121.0, 23.5)
    tb.add(ax, "k", "横断山脉", 99.3, 27.5)
    tb.add(ax, "k", "长江中下游平原", 117.6, 30.3)
    tb.add(ax, "k", "四川盆地", 105.6, 29.9)
    tb.add(ax, "k", "云贵高原", 104.3, 26.3)
    tb.add(ax, "k", "东南丘陵", 114.8, 26.6)

    tb.add(ax, "r", "长江", 115.2, 29.9)
    tb.add(ax, "r", "珠江", 112.0, 22.9)
    tb.add(ax, "r", "淮河", 116.6, 32.6)
    tb.add(ax, "l", "洞庭湖", 112.8, 29.3, dot="lake")
    tb.add(ax, "l", "鄱阳湖", 116.3, 29.15, dot="lake")
    tb.add(ax, "l", "太湖", 120.2, 31.25, dot="lake", dx=-0.5, dy=0.35)

    tb.add(ax, "c", "上海（最大城市）", *CITIES["上海"], dot="star", dx=0.5, dy=0.45)
    tb.add(ax, "c", "南京", *CITIES["南京"], dx=-0.4, dy=0.3)
    tb.add(ax, "c", "杭州", *CITIES["杭州"], dx=0.3, dy=-0.45)
    tb.add(ax, "c", "合肥", *CITIES["合肥"])
    tb.add(ax, "c", "武汉", *CITIES["武汉"])
    tb.add(ax, "c", "长沙", *CITIES["长沙"])
    tb.add(ax, "c", "南昌", *CITIES["南昌"])
    tb.add(ax, "c", "福州", *CITIES["福州"])
    tb.add(ax, "c", "广州", *CITIES["广州"], dx=0.35, dy=0.3)
    tb.add(ax, "c", "香港", *CITIES["香港"], dx=0.4, dy=-0.4)
    tb.add(ax, "c", "南宁", *CITIES["南宁"])
    tb.add(ax, "c", "海口", *CITIES["海口"])
    tb.add(ax, "c", "成都", *CITIES["成都"], dx=-0.4, dy=0.25)
    tb.add(ax, "c", "重庆", *CITIES["重庆"], dx=0.35, dy=0.3)
    tb.add(ax, "c", "贵阳", *CITIES["贵阳"])
    tb.add(ax, "c", "昆明", *CITIES["昆明"])

    add_title(ax, "南方地区",
              "水乡、丘陵、盆地与高原——亚热带季风气候下的鱼米之乡")
    tb.render(fig, bottom=0.27, fs=8.8, cols=3, top=0.26, chunk=4)
    _save_with_legend(fig, "fig13-4_南方地区专题图.png", FOOT_MAP)


# ---------------------------------------------------------------- fig 13-5
def fig13_5_northwest():
    fig, ax = new_map_axes((12.4, 9.6))
    fig.subplots_adjust(bottom=0.245, top=0.985, left=0.005, right=0.995)
    prov, dash, mem = focus_base(ax, REGION4["西北"], R4_COLOR["西北"],
                                 pad=0.05)
    _rivers(ax, mem)
    tb = TagBoard()

    _terrain_poly(ax, "内蒙古高原", PLATEAUS["内蒙古高原"], "#c08a58", 0.26)
    _terrain_poly(ax, "塔里木盆地", BASINS["塔里木盆地"], "#7fa8c9", 0.30)
    _terrain_poly(ax, "准噶尔盆地", BASINS["准噶尔盆地"], "#7fa8c9", 0.30)
    for name, poly in DESERTS.items():
        xs, ys = zip(*[to_albers(lo, la) for lo, la in poly])
        ax.add_patch(MplPolygon(list(zip(xs, ys)), closed=True, fc="#e3c98a",
                                ec="#b99a52", lw=0.8, ls="--", alpha=0.55,
                                zorder=4.4))
    for name in ["天山山脉", "阿尔泰山脉", "昆仑山脉", "阿尔金山脉",
                 "阴山山脉", "贺兰山", "祁连山脉"]:
        _mtn_line(ax, name)
    tb.add(ax, "k", "内蒙古高原", 116.0, 42.6)
    tb.add(ax, "k", "塔里木盆地", 84.5, 40.6)
    tb.add(ax, "k", "准噶尔盆地", 87.5, 44.9)
    tb.add(ax, "k", "塔克拉玛干沙漠", 83.0, 39.0)
    tb.add(ax, "k", "河西走廊", 98.5, 39.5)
    tb.add(ax, "k", "河套平原", 107.0, 40.5)
    tb.add(ax, "k", "天山山脉", 82.5, 42.8)
    tb.add(ax, "k", "阿尔泰山脉", 89.5, 48.4)
    tb.add(ax, "k", "昆仑山脉", 80.0, 36.0)
    tb.add(ax, "k", "阿尔金山脉", 88.5, 38.7)
    tb.add(ax, "k", "阴山山脉", 110.0, 41.0)
    tb.add(ax, "k", "贺兰山", 105.85, 39.3)
    tb.add(ax, "k", "祁连山脉", 99.5, 38.3)

    tb.add(ax, "r", "塔里木河", 82.0, 41.0)
    tb.add(ax, "r", "黄河", 105.0, 37.3)

    tb.add(ax, "c", "乌鲁木齐", *CITIES["乌鲁木齐"])
    tb.add(ax, "c", "兰州", *CITIES["兰州"])
    tb.add(ax, "c", "银川", *CITIES["银川"], dx=0.35, dy=0.3)
    tb.add(ax, "c", "呼和浩特", *CITIES["呼和浩特"])
    tb.add(ax, "c", "包头", *LOCAL_CITY["包头"])
    tb.add(ax, "c", "哈密", *LOCAL_CITY["哈密"])
    tb.add(ax, "c", "敦煌", *LOCAL_CITY["敦煌"])
    tb.add(ax, "c", "喀什", *CITIES["喀什"])

    tb.add(ax, "p", "满洲里", *CITIES["满洲里"], dot="port")
    tb.add(ax, "p", "二连浩特", *LOCAL_CITY["二连浩特"], dot="port")
    tb.add(ax, "p", "霍尔果斯", *LOCAL_CITY["霍尔果斯"], dot="port")

    tb.add(ax, "m", "克拉玛依油田", 84.9, 45.65, dot="mine")
    tb.add(ax, "m", "金昌镍矿", 102.19, 38.52, dot="mine")
    tb.add(ax, "m", "白云鄂博铁矿", 109.97, 41.77, dot="mine")

    add_title(ax, "西北地区",
              "深居内陆的干旱半干旱区——高原与盆地相间，绿洲与草原点缀")
    tb.render(fig, bottom=0.245, fs=8.8, cols=3, top=0.235, chunk=4)
    _save_with_legend(fig, "fig13-5_西北地区专题图.png", FOOT_MAP)


# ---------------------------------------------------------------- fig 13-6
def fig13_6_qingzang():
    fig, ax = new_map_axes((9.8, 10.4))
    fig.subplots_adjust(bottom=0.26, top=0.985, left=0.005, right=0.995)
    prov, dash, mem = focus_base(ax, REGION4["青藏"], R4_COLOR["青藏"],
                                 pad=0.06)
    _rivers(ax, mem)
    tb = TagBoard()

    _terrain_poly(ax, "柴达木盆地", BASINS["柴达木盆地"], "#7fa8c9", 0.30)
    for name in ["昆仑山脉", "喀喇昆仑山脉", "喜马拉雅山脉", "唐古拉山脉",
                 "冈底斯山脉", "祁连山脉", "横断山脉"]:
        _mtn_line(ax, name)
    tb.add(ax, "k", "昆仑山脉", 80.0, 36.0)
    tb.add(ax, "k", "喀喇昆仑山脉", 76.2, 35.9)
    tb.add(ax, "k", "喜马拉雅山脉", 83.5, 29.2)
    tb.add(ax, "k", "唐古拉山脉", 94.0, 33.1)
    tb.add(ax, "k", "冈底斯山脉", 85.0, 30.5)
    tb.add(ax, "k", "祁连山脉", 99.5, 38.3)
    tb.add(ax, "k", "横断山脉", 98.9, 30.0)
    tb.add(ax, "k", "柴达木盆地", 94.5, 37.2)
    tb.add(ax, "k", "三江源地区", 96.2, 34.2)
    tb.add(ax, "k", "湟水谷地", 103.0, 36.3, dx=0.3, dy=-0.2)
    tb.add(ax, "k", "雅鲁藏布江谷地", 92.0, 29.05)

    tb.add(ax, "r", "雅鲁藏布江", 95.2, 29.5)
    tb.add(ax, "l", "青海湖", 100.15, 36.95, dot="lake")
    tb.add(ax, "l", "纳木错", 90.65, 30.7, dot="lake")

    tb.add(ax, "c", "西宁", *CITIES["西宁"])
    tb.add(ax, "c", "格尔木", *CITIES["格尔木"])
    tb.add(ax, "c", "拉萨", *CITIES["拉萨"], dx=0.35, dy=0.3)
    tb.add(ax, "c", "日喀则", *LOCAL_CITY["日喀则"])

    # 青藏铁路（西宁—格尔木—拉萨）
    rail = [(101.78, 36.62), (97.37, 37.37), (94.90, 36.40), (94.05, 35.65),
            (92.44, 33.93), (91.68, 32.26), (92.05, 31.48), (91.14, 29.65)]
    xs, ys = zip(*[to_albers(lo, la) for lo, la in rail])
    ax.plot(xs, ys, color="#8e2a1e", lw=1.8, ls=(0, (5, 2)), zorder=7)

    add_title(ax, "青藏地区",
              "雪域高寒之地——世界屋脊、江河之源与河谷文明")
    tb.render(fig, bottom=0.26, fs=8.8, cols=2, top=0.25)
    _save_with_legend(fig, "fig13-6_青藏地区专题图.png",
                      ["红色虚线为青藏铁路（西宁—格尔木—拉萨）", FOOT_MAP])


if __name__ == "__main__":
    setup()
    fig13_1_division()
    fig13_2_shares()
    fig13_3_north()
    fig13_4_south()
    fig13_5_northwest()
    fig13_6_qingzang()
    print("ch13 regions done")
