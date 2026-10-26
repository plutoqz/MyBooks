# -*- coding: utf-8 -*-
"""第 1 章 疆域与位置 —— 四幅专题地图。

fig1-1 中国在全球的位置图（Natural Earth 110m）
fig1-2 领土四至点示意图（DataV 全国界线 + Albers 投影）
fig1-4 周边邻国图（Natural Earth 50m）
fig1-7 四大海域示意图（DataV 全国界线 + Albers 投影）

说明文字一律置于图幅下方（footer），不在地图主体内放置说明框。
"""
import os
import sys
import geopandas as gpd
from matplotlib.patches import Patch
from pyproj import Transformer
from shapely.geometry import LineString, Point

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from style import (ALBERS, C_CHINA, C_CHINA_FILL, C_EDGE, C_LAND, C_MARITIME,
                   C_NEIGHBOR, C_SEA, add_north_arrow, add_title, load_china,
                   load_world, new_map_axes, save_fig, setup)

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "figures")
os.makedirs(OUT, exist_ok=True)

_T = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True)


def to_albers(lon, lat):
    return _T.transform(lon, lat)


def set_extent_from(ax, gdf, pad_frac=0.04):
    """按要素范围设置图幅（含留白）。"""
    minx, miny, maxx, maxy = gdf.total_bounds
    dx, dy = (maxx - minx), (maxy - miny)
    ax.set_xlim(minx - dx * pad_frac, maxx + dx * pad_frac)
    ax.set_ylim(miny - dy * pad_frac, maxy + dy * pad_frac)
    return ax


# ---------------------------------------------------------------- fig 1-1
def fig1_global_position():
    world = load_world("110m")
    iso = world["ISO_A3"]
    china = world[iso == "CHN"]
    others = world[iso != "CHN"]

    fig, ax = new_map_axes((11.5, 7.0))
    others.plot(ax=ax, color=C_LAND, edgecolor=C_EDGE, linewidth=0.35)
    china.plot(ax=ax, color=C_CHINA, edgecolor="#8e2b20", linewidth=0.6)

    ax.set_facecolor(C_SEA)
    ax.set_xlim(-180, 180)
    ax.set_ylim(-62, 90)

    for lon in range(-150, 181, 30):
        ax.axvline(lon, color="#9fb6c9", lw=0.4, ls="--", zorder=1)
    for lat in range(-60, 81, 30):
        ax.axhline(lat, color="#9fb6c9", lw=0.4, ls="--", zorder=1)
    ax.axhline(0, color="#5d89a8", lw=0.9, zorder=2)
    ax.text(-178, 2.0, "赤道 0°", fontsize=8.5, color="#33607e")
    ax.axhline(23.44, color="#c08a3e", lw=0.7, ls=":", zorder=2)
    ax.text(-178, 25.2, "北回归线 23°26′N", fontsize=8, color="#8a6220")

    kw = dict(fontsize=11, color="#4a6274", style="italic", zorder=3)
    ax.text(74, 47, "亚　欧　大　陆", ha="center", fontsize=13, color="#4a6274", zorder=3)
    ax.text(-100, 46, "北美洲", ha="center", **kw)
    ax.text(20, 8, "非洲", ha="center", **kw)
    ax.text(133, -25, "大洋洲", ha="center", **kw)
    ax.text(-60, -20, "南美洲", ha="center", **kw)
    for x, y in [(-155, 8), (175, 5)]:
        ax.text(x, y, "太平洋", ha="center", fontsize=12, color="#33607e",
                style="italic", zorder=3)
    ax.text(78, -24, "印度洋", ha="center", fontsize=12, color="#33607e",
            style="italic", zorder=3)
    ax.text(-38, -30, "大西洋", ha="center", fontsize=12, color="#33607e",
            style="italic", zorder=3)

    add_title(ax, "中国在全球的位置", "全部位于东半球与北半球：亚欧大陆东部、太平洋西岸")
    save_fig(fig, ax, "fig1-1_全球位置图.png",
             footer="底图：Natural Earth 110m（公共领域）。示意地图，不作为权属划界依据。")


# ---------------------------------------------------------------- fig 1-2
def fig1_extreme_points():
    china = load_china().to_crs(ALBERS)

    pts = {  # 名称: (lon, lat, 说明)
        "北端点": (122.35, 53.55, "漠河以北黑龙江主航道中心线\n约 53°33′N，122°21′E"),
        "南端点": (112.28, 3.98, "南沙群岛曾母暗沙\n约 3°58′N，112°17′E"),
        "东端点": (135.09, 48.45, "黑龙江与乌苏里江主航道\n汇合处，约 135°05′E，48°27′N"),
        "西端点": (73.55, 39.20, "帕米尔高原（新疆）\n约 73°33′E，39°10′N"),
    }
    pts_g = gpd.GeoSeries(
        [Point(v[0], v[1]) for v in pts.values()], crs="EPSG:4326").to_crs(ALBERS)

    # 各端点处的十字参考线（短线）
    lines = []
    for name, (lon, lat, _) in pts.items():
        d = 2.2
        lines.append(LineString([(lon - d, lat), (lon + d, lat)]))
        lines.append(LineString([(lon, lat - d), (lon, lat + d)]))
    lines_g = gpd.GeoSeries(lines, crs="EPSG:4326").to_crs(ALBERS)

    fig, ax = new_map_axes((9.5, 10.5))
    china.plot(ax=ax, color=C_CHINA_FILL, edgecolor=C_CHINA, linewidth=0.7)
    lines_g.plot(ax=ax, color="#c0392b", lw=0.7, ls="--", alpha=0.7)
    ax.scatter(pts_g.x, pts_g.y, s=46, c="#8e2b20", edgecolors="white",
               linewidths=0.8, zorder=10)

    label_pos = {"北端点": (0.55, 0.905), "东端点": (0.90, 0.62),
                 "南端点": (0.30, 0.065), "西端点": (0.08, 0.74)}
    for (name, (lon, lat, text)), (lx, ly) in zip(pts.items(), label_pos.values()):
        x, y = to_albers(lon, lat)
        ax.annotate(f"{name}\n{text}", xy=(x, y), xytext=(lx, ly),
                    textcoords="axes fraction", fontsize=9.5, color="#7b241c",
                    ha="center", va="center", zorder=12,
                    arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1.0,
                                    shrinkA=2, shrinkB=3),
                    bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#c0392b",
                              lw=0.7, alpha=0.94))

    set_extent_from(ax, china)
    add_title(ax, "中国领土四至点", "最北约 53°33′N，最南约 3°58′N，最西约 73°33′E，最东约 135°05′E")
    add_north_arrow(ax, x=0.045)
    save_fig(fig, ax, "fig1-2_领土四至点图.png",
             footer="东西跨约 61°32′（≈5 200 km），南北跨约 49°35′（≈5 500 km），东西时差约 4 小时\n"
                    "界线：DataV.GeoAtlas areas_v3（2021.5，仅供学习交流）；投影：Albers 等积圆锥（105°E，25°/47°N）")


# ---------------------------------------------------------------- fig 1-4
LAND_NB = {  # 14 个陆上邻国：ISO3 -> (中文名, 边界长度, 标签锚点 lon, lat)
    "PRK": ("朝鲜", "约1 420 km", 128.8, 40.8),
    "RUS": ("俄罗斯", "约4 300 km", 116.0, 52.0),
    "MNG": ("蒙古", "约4 700 km", 102.5, 46.8),
    "KAZ": ("哈萨克斯坦", "约1 780 km", 81.0, 46.5),
    "KGZ": ("吉尔吉斯斯坦", "约1 100 km", 75.0, 40.8),
    "TJK": ("塔吉克斯坦", "约450 km", 70.5, 37.8),
    "AFG": ("阿富汗", "约92 km", 64.5, 33.0),
    "PAK": ("巴基斯坦", "约596 km", 68.5, 27.5),
    "IND": ("印度", "约2 000 km（未划定）", 78.5, 20.5),
    "NPL": ("尼泊尔", "约1 415 km", 85.5, 28.4),
    "BTN": ("不丹", "约470 km（未正式划定）", 92.0, 25.6),
    "MMR": ("缅甸", "约2 185 km", 96.5, 18.5),
    "LAO": ("老挝", "约505 km", 103.5, 16.5),
    "VNM": ("越南", "约1 450 km", 106.8, 19.6),
}
SEA_NB = {  # 6 个隔海相望国家
    "KOR": ("韩国", 131.0, 37.8),
    "JPN": ("日本", 140.0, 37.5),
    "PHL": ("菲律宾", 123.5, 14.5),
    "MYS": ("马来西亚", 101.0, 3.0),
    "BRN": ("文莱", 115.0, 5.2),
    "IDN": ("印度尼西亚", 111.0, -5.0),
}


def fig1_neighbors():
    world = load_world("50m")
    iso = world["ISO_A3"]
    land_codes, sea_codes = list(LAND_NB), list(SEA_NB)
    china = world[iso == "CHN"]
    land = world[iso.isin(land_codes)]
    sea = world[iso.isin(sea_codes)]
    others = world[~iso.isin(land_codes + sea_codes + ["CHN"])]

    fig, ax = new_map_axes((11.0, 10.0))
    others.plot(ax=ax, color="#eceff3", edgecolor=C_EDGE, linewidth=0.3)
    land.plot(ax=ax, color=C_NEIGHBOR, edgecolor="#b7950b", linewidth=0.5)
    sea.plot(ax=ax, color=C_MARITIME, edgecolor="#5d89a8", linewidth=0.5)
    china.plot(ax=ax, color=C_CHINA_FILL, edgecolor=C_CHINA, linewidth=0.9)
    ax.set_facecolor(C_SEA)
    ax.set_xlim(58, 150)
    ax.set_ylim(-13, 58)

    for iso3, (name, dist, lx, ly) in LAND_NB.items():
        ax.text(lx, ly, f"{name}\n{dist}", fontsize=8.8, color="#6e5a10",
                ha="center", va="center", zorder=12, linespacing=1.25,
                bbox=dict(boxstyle="round,pad=0.28", fc="white", ec="#b7950b",
                          lw=0.6, alpha=0.9))
    for iso3, (name, lx, ly) in SEA_NB.items():
        ax.text(lx, ly, name, fontsize=9.5, color="#1a5276", ha="center",
                va="center", zorder=12, style="italic",
                bbox=dict(boxstyle="round,pad=0.28", fc="white", ec="#5d89a8",
                          lw=0.6, alpha=0.9))

    legend_elems = [
        Patch(fc=C_CHINA_FILL, ec=C_CHINA, label="中国"),
        Patch(fc=C_NEIGHBOR, ec="#b7950b", label="14 个陆上邻国"),
        Patch(fc=C_MARITIME, ec="#5d89a8", label="6 个隔海相望国家"),
        Patch(fc="#eceff3", ec=C_EDGE, label="其他国家"),
    ]
    ax.legend(handles=legend_elems, loc="lower left", bbox_to_anchor=(0.005, 0.085),
              fontsize=9.5, framealpha=0.92, edgecolor="#cccccc")

    add_title(ax, "中国的陆上邻国与隔海相望国家",
              "陆上邻国 14 个（与俄罗斯并列世界最多），隔海相望国家 6 个；陆地国界线总长约 2.28 万 km")
    add_north_arrow(ax)
    save_fig(fig, ax, "fig1-4_周边邻国图.png",
             footer="底图：Natural Earth 50m（公共领域）；边界长度为约数。示意地图，不作为权属划界依据。")


# ---------------------------------------------------------------- fig 1-7
def fig1_seas():
    china = load_china().to_crs(ALBERS)

    fig, ax = new_map_axes((9.5, 10.5))
    china.plot(ax=ax, color=C_LAND, edgecolor="#4a6274", linewidth=0.6)
    ax.set_facecolor(C_SEA)

    # 四大海区界线（教材通行界线）
    sea_lines = [
        LineString([(121.24, 38.72), (120.73, 37.83)]),  # 渤海—黄海：老铁山角—蓬莱角
        LineString([(121.93, 31.70), (126.28, 33.22)]),  # 黄海—东海：长江口北角—济州岛西南
        LineString([(117.10, 23.43), (120.86, 21.90)]),  # 东海—南海：南澳岛—鹅銮鼻
    ]
    lines_g = gpd.GeoSeries(sea_lines, crs="EPSG:4326").to_crs(ALBERS)
    lines_g.plot(ax=ax, color="#1a5276", lw=0.9, ls="--")

    sea_labels = {"渤海": (119.4, 38.8), "黄海": (123.8, 35.6),
                  "东海": (124.6, 28.9), "南海": (113.0, 15.0)}
    for name, (lon, lat) in sea_labels.items():
        x, y = to_albers(lon, lat)
        ax.text(x, y, name, fontsize=13, color="#1a5276", ha="center",
                va="center", fontweight="bold", zorder=12)

    items = {
        "辽东半岛": (122.8, 40.5), "山东半岛": (120.8, 36.6),
        "雷州半岛": (110.7, 21.3), "琼州海峡（内海）": (107.2, 19.9),
        "台湾海峡": (119.6, 24.9), "台湾岛": (123.0, 22.9),
        "海南岛": (108.7, 18.3), "钓鱼岛\n及其附属岛屿": (126.0, 25.2),
    }
    for name, (lon, lat) in items.items():
        x, y = to_albers(lon, lat)
        ax.text(x, y, name, fontsize=8.8, color="#2c3e50", ha="center",
                va="center", zorder=12,
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))

    set_extent_from(ax, china)
    add_title(ax, "中国的四大海域与近海格局", "渤海—黄海—东海—南海自北而南依次排布；图中断续线为南海九段线")
    add_north_arrow(ax)
    save_fig(fig, ax, "fig1-7_四大海域图.png",
             footer="渤海、琼州海峡为中国内海；主张管辖海域约 300 万 km²，大陆海岸线约 1.8 万 km\n"
                    "界线：DataV.GeoAtlas areas_v3（2021.5，仅供学习交流）；海区界线为通行画法")


if __name__ == "__main__":
    setup()
    fig1_global_position()
    fig1_extreme_points()
    fig1_neighbors()
    fig1_seas()
    print("已生成：", sorted(f for f in os.listdir(OUT) if f.startswith("fig1-")))
