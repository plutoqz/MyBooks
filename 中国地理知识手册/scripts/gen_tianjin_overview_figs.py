# -*- coding: utf-8 -*-
"""天津市地理统揽专题地图生成引擎（02-00）
包含 5 幅全市域权威地图与分析图表（精细调优排版、真实GIS水系水体、径向外展排版、杜绝压盖）：
1. fig02-00-1_天津市地形地貌与海陆水系格局图.png （九山顶燕山余脉、真实海河干支与于桥/北大港/团泊大水体）
2. fig02-00-2_天津市行政区划与空间骨架图.png （“津城—滨城”双城格局、中心六区径向引线无重叠排版）
3. fig02-00-3_天津市综合立体交通网与海陆空枢纽图.png （京津城际、京沪高铁、天津港核心区、滨海国际机场）
4. fig02-00-4_天津市产业经济与先进制造研发走廊图.png （天开高教科创园、海河智造轴、TEDA经开区、南港石化）
5. fig02-00-5_天津市生态屏障与历史文化空间分布图.png （津沽绿屏736km²、黄崖关长城、五大道、大沽口炮台）
"""
import os
import sys
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Rectangle, Patch, PathPatch, Polygon
from matplotlib.path import Path
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap, Normalize
from rasterio.transform import from_origin
from rasterio.features import rasterize
from pyproj import Transformer

sys.path.insert(0, r"D:\code\Ideas\MyBooks\中国地理知识手册\scripts")
from style import ALBERS, C_TEXT, DATA, DPI, FIGURES, setup
from prov_pipeline import prov_dem
import mapkit

setup()
OUT_DIR = FIGURES
os.makedirs(OUT_DIR, exist_ok=True)
_T = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True)

def to_alb(lon, lat):
    return _T.transform(lon, lat)

def get_mpl_clip_patch(poly_geom):
    if poly_geom.geom_type == 'Polygon':
        geoms = [poly_geom]
    else:
        geoms = list(poly_geom.geoms)
    all_verts = []
    all_codes = []
    for g in geoms:
        ext = np.array(g.exterior.coords)
        verts = list(ext)
        codes = [Path.MOVETO] + [Path.LINETO] * (len(verts) - 2) + [Path.CLOSEPOLY]
        all_verts.extend(verts)
        all_codes.extend(codes)
        for interior in g.interiors:
            intr = np.array(interior.coords)
            verts = list(intr)
            codes = [Path.MOVETO] + [Path.LINETO] * (len(verts) - 2) + [Path.CLOSEPOLY]
            all_verts.extend(verts)
            all_codes.extend(codes)
    mpl_path = Path(all_verts, all_codes)
    return PathPatch(mpl_path, facecolor='none', edgecolor='none')

def calc_hillshade(dem, res, az=315.0, alt=45.0):
    az_rad = np.radians(az)
    alt_rad = np.radians(alt)
    gy, gx = np.gradient(dem, res)
    slope = np.arctan(np.sqrt(gx * gx + gy * gy))
    aspect = np.arctan2(-gx, gy)
    shaded = np.sin(alt_rad) * np.cos(slope) + np.cos(alt_rad) * np.sin(slope) * np.cos(az_rad - aspect)
    return np.clip(shaded, 0.0, 1.0)

def add_scalebar(ax, x0, y0, length_km=30):
    """统一走 mapkit 版本，按像素宽度自适应是否画中点刻度。"""
    import mapkit
    mapkit.add_scalebar(ax, x0, y0, length_km=length_km)

def add_compass(ax, x=0.94, y=0.92):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.055), transform=ax.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=1.8, headwidth=5.5, headlength=6.5),
                ha="center", va="center", fontsize=8.8, fontweight="bold", color="#2c3e50", zorder=30)

print("Loading Tianjin municipal data...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
tj_districts = gpd.read_file(os.path.join(DATA_DIR, "boundaries", "datav", "120000_full.json")).to_crs(ALBERS)
tj_union = tj_districts.union_all()
bb = tj_districts.total_bounds

# 视口与中心
cx = (bb[0] + bb[2]) / 2.0
cy = (bb[1] + bb[3]) / 2.0
span_x = bb[2] - bb[0]
span_y = bb[3] - bb[1]
max_span = max(span_x, span_y)

half_span_x = max_span * 0.55
half_span_y = max_span * 0.60
ax_xlim = (cx - half_span_x, cx + half_span_x)
ax_ylim = (cy - half_span_y * 0.96, cy + half_span_y * 1.08)

sb_x0 = cx + half_span_x * 0.32
sb_y0 = cy - half_span_y * 0.88

dem_tj, dem_minx, dem_maxy, dem_res = prov_dem("120000", zoom=9, res=300.0)

# 加载真实水系与水体面图层（彻底替代圆形占位符）
print("Loading authentic GIS hydrology for Tianjin...")
water_a_file = os.path.join(DATA_DIR, "transport", "hebei", "gis_osm_water_a_free_1.shp")
waterways_file = os.path.join(DATA_DIR, "transport", "hebei", "gis_osm_waterways_free_1.shp")

all_water_a = gpd.read_file(water_a_file).to_crs(ALBERS)
tj_water_a = all_water_a.cx[bb[0]:bb[2], bb[1]:bb[3]]
tj_water_a = gpd.clip(tj_water_a, tj_union)

all_waterways = gpd.read_file(waterways_file).to_crs(ALBERS)
tj_waterways = all_waterways.cx[bb[0]:bb[2], bb[1]:bb[3]]
tj_waterways = gpd.clip(tj_waterways, tj_union)

# 筛选大水体与主河流
main_tj_lakes = tj_water_a[tj_water_a['fclass'].isin(['water', 'reservoir', 'wetland'])]
main_tj_rivers = tj_waterways[tj_waterways['fclass'].isin(['river', 'canal'])]

print("Tianjin spatial base layers ready.")

# --- 真实路网与铁路（市域综合交通图用）------------------------------------
# 原 fig02-00-3 的"铁路/高速"是硬编码的 4~6 个经纬度点连成的折线，
# 画出来就是用户点名的"只有直来直去的线"。这里改用 OSM 实际矢量。
print("Loading authentic OSM roads & railways for Tianjin...")
_tjdir = os.path.join(DATA_DIR, "transport", "tianjin")
_roads_all = gpd.read_file(os.path.join(_tjdir, "gis_osm_roads_free_1.shp"))
_rails_all = gpd.read_file(os.path.join(_tjdir, "gis_osm_railways_free_1.shp"))

# 省级/市域尺度只保留骨架：高速 + 国道干线 + 省市干路，支路会糊成一片
_EXPRESS = ["motorway", "motorway_link", "trunk", "trunk_link"]
_TRUNK = ["primary", "primary_link", "secondary", "secondary_link"]
tj_express = gpd.clip(
    _roads_all[_roads_all["fclass"].isin(_EXPRESS)].to_crs(ALBERS), tj_union)
tj_trunk = gpd.clip(
    _roads_all[_roads_all["fclass"].isin(_TRUNK)].to_crs(ALBERS), tj_union)
tj_rail_main = gpd.clip(
    _rails_all[_rails_all["fclass"].isin(["rail", "narrow_gauge"])].to_crs(ALBERS),
    tj_union)
print(f"  express={len(tj_express)} trunk={len(tj_trunk)} rail={len(tj_rail_main)}")

# =============================================================================
# 图 1：天津市地形地貌与海陆水系格局图 (fig02-00-1)
# =============================================================================
def make_fig1():
    print("Generating fig02-00-1: 地形地貌与海陆水系格局图...")
    fig, ax = plt.subplots(figsize=(10.0, 10.2), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.set_axis_off()

    c0 = max(0, int((ax_xlim[0] - dem_minx) / dem_res))
    c1 = min(dem_tj.shape[1], int((ax_xlim[1] - dem_minx) / dem_res) + 1)
    r0 = max(0, int((dem_maxy - ax_ylim[1]) / dem_res))
    r1 = min(dem_tj.shape[0], int((dem_maxy - ax_ylim[0]) / dem_res) + 1)

    sub_dem = dem_tj[r0:r1, c0:c1].copy()
    sub_minx = dem_minx + c0 * dem_res
    sub_maxy = dem_maxy - r0 * dem_res
    sub_extent = (sub_minx, sub_minx + sub_dem.shape[1] * dem_res,
                  sub_maxy - sub_dem.shape[0] * dem_res, sub_maxy)

    tf = from_origin(sub_minx, sub_maxy, dem_res, dem_res)
    inside_mask = rasterize([(tj_union, 1)], out_shape=(sub_dem.shape[0], sub_dem.shape[1]), transform=tf, fill=0, dtype="uint8")

    sub_dem_clean = sub_dem.copy()
    sub_dem_clean[np.isnan(sub_dem_clean)] = -10.0
    sub_dem_clean = np.clip(sub_dem_clean, -5.0, 1100.0)

    shade = calc_hillshade(sub_dem_clean, dem_res, az=315.0, alt=45.0)

    colors_terrain = [
        (0.00, "#a8d8b9"),
        (0.03, "#c8e6c9"),
        (0.08, "#dce775"),
        (0.18, "#ffd54f"),
        (0.40, "#ff8a65"),
        (0.70, "#a1887f"),
        (1.00, "#4e342e")
    ]
    cmap_relief = LinearSegmentedColormap.from_list("tj_relief", colors_terrain)
    norm = Normalize(vmin=0, vmax=1100)
    rgba = cmap_relief(norm(sub_dem_clean))

    for c in range(3):
        rgba[:, :, c] = rgba[:, :, c] * (0.45 + 0.55 * shade)
    rgba[:, :, 3] = np.where(inside_mask == 1, 1.0, 0.0)

    clip_patch = get_mpl_clip_patch(tj_union)
    ax.add_patch(clip_patch)
    im = ax.imshow(rgba, extent=sub_extent, origin="upper", zorder=3)
    im.set_clip_path(clip_patch)

    tj_districts.plot(ax=ax, facecolor="none", edgecolor="#5d6d7e", lw=0.5, linestyle="--", zorder=5)
    gpd.GeoSeries([tj_union], crs=ALBERS).plot(ax=ax, facecolor="none", edgecolor="#1a5276", lw=1.6, zorder=6)

    # 绘制真实 GIS 水系水体（全真多边形，彻底告别圆圈占位符）
    main_tj_lakes.plot(ax=ax, facecolor="#85c1e9", edgecolor="#2471a3", lw=0.4, alpha=0.95, zorder=7)
    main_tj_rivers.plot(ax=ax, color="#1b4f72", lw=0.9, alpha=0.9, zorder=8)

    # 渤海湾
    bx, by = to_alb(117.95, 38.82)
    ax.text(bx, by, "渤 海 湾\n(BOHAI BAY)",
            fontsize=8.5, fontweight="bold", color="#2980b9", ha="center", va="center", zorder=7,
            path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])

    # 骨干江河注记
    river_labels = [
        ("海河干流", 117.38, 39.04),
        ("子牙河", 117.05, 39.08),
        ("南运河", 117.02, 38.88),
        ("北运河", 117.08, 39.30),
        ("永定新河", 117.45, 39.20),
        ("潮白新河", 117.48, 39.45),
        ("蓟运河", 117.70, 39.30),
        ("独流减河", 117.25, 38.86)
    ]
    for rname, rlon, rlat in river_labels:
        rx, ry = to_alb(rlon, rlat)
        ax.text(rx, ry, rname, fontsize=6.5, fontweight="bold", color="#154360",
                ha="center", va="center", zorder=10,
                path_effects=[pe.withStroke(linewidth=2.0, foreground="white")])

    # 湖泊水库与天然湿地注记
    lakes_annotations = [
        ("于桥水库 (翠屏湖·引滦入津入城枢纽)", 117.52, 40.04, 2500, 2500, "left"),
        ("七里海古海岸湿地 (国家级自然保护区)", 117.58, 39.30, 2500, 1800, "left"),
        ("团泊水库 (华北重要蓄滞洪湖泊)", 117.17, 38.92, -2500, 1800, "right"),
        ("北大港水库 (亚洲东部候鸟停歇关键地)", 117.42, 38.74, 2500, -1800, "left"),
        ("大黄堡湿地自然保护区", 117.26, 39.45, -2500, 1800, "right")
    ]
    for lname, llon, llat, ox, oy, ha in lakes_annotations:
        lx, ly = to_alb(llon, llat)
        ax.annotate(lname, xy=(lx, ly), xytext=(lx + ox, ly + oy),
                    arrowprops=dict(arrowstyle="->", color="#1b4f72", lw=0.6),
                    fontsize=6.8, fontweight="bold", color="#1b4f72", ha=ha, va="center", zorder=12,
                    path_effects=[pe.withStroke(linewidth=2.0, foreground="white")])

    # 蓟州北部山峰与地质点（错落分布，杜绝文字挤压）
    peaks = [
        ("九山顶 1078.5m\n(天津最高峰)", 117.48, 40.23, 2500, 2800, "left"),
        ("盘山 挂月峰 864.4m", 117.26, 40.08, -2500, -1200, "right"),
        ("黄崖关 380m", 117.44, 40.24, -2800, 1500, "right"),
        ("八仙山 1052m", 117.55, 40.18, 2500, -2200, "left")
    ]
    for pname, plon, plat, ox, oy, ha in peaks:
        px, py = to_alb(plon, plat)
        ax.plot(px, py, marker="^", color="#c0392b", markersize=5.5, markeredgecolor="white", markeredgewidth=0.8, zorder=12)
        ax.annotate(pname, xy=(px, py), xytext=(px + ox, py + oy),
                    arrowprops=dict(arrowstyle="->", color="#c0392b", lw=0.6),
                    fontsize=6.5, fontweight="bold", color="#641e16", ha=ha, va="center", zorder=13,
                    path_effects=[pe.withStroke(linewidth=2.0, foreground="white")])

    # 标题置于最顶部安全区
    ax.text(cx, cy + half_span_y * 1.05, "天津市地势地貌与海陆水系格局图", fontsize=12.0, fontweight="bold",
            ha="center", va="top", color="#1a252f", zorder=30)
    ax.text(cx, cy + half_span_y * 1.01, "Topography, Water Systems and Maritime Coastline of Tianjin", fontsize=7.2,
            style="italic", ha="center", va="top", color="#566573", zorder=30)

    # 图例框置于西南角
    leg_x = cx - half_span_x * 0.95
    leg_y = cy - half_span_y * 0.90
    leg_w = half_span_x * 0.46
    leg_h = half_span_y * 0.32
    ax.add_patch(Rectangle((leg_x, leg_y), leg_w, leg_h, facecolor="white", edgecolor="#bdc3c7", lw=0.8, alpha=0.92, zorder=24))
    ax.text(leg_x + leg_w * 0.5, leg_y + leg_h * 0.88, "图 例 (Legend)", fontsize=7.2, fontweight="bold", ha="center", va="center", color="#2c3e50", zorder=25)

    items = [
        (Line2D([0], [0], marker='^', color='w', markerfacecolor='#c0392b', markersize=5.5), "燕山主要山峰/山口"),
        (Line2D([0], [0], color='#1b4f72', lw=1.6), "骨干江河水系 (海河干流及支流)"),
        (Patch(facecolor='#85c1e9', edgecolor='#2471a3', lw=0.8), "真实水库与天然湿地水面"),
        (Patch(facecolor='#a8d8b9', edgecolor='none'), "平原低地 (海拔 0~30m)"),
        (Patch(facecolor='#ff8a65', edgecolor='none'), "低山丘陵 (海拔 200~500m)"),
        (Patch(facecolor='#4e342e', edgecolor='none'), "中山山峰 (海拔 800~1078m)")
    ]
    for idx, (handle, label) in enumerate(items):
        iy = leg_y + leg_h * (0.72 - idx * 0.12)
        if isinstance(handle, Line2D):
            if handle.get_marker() != 'None':
                ax.plot(leg_x + leg_w * 0.14, iy, marker='^', color='#c0392b', markersize=5, zorder=25)
            else:
                ax.plot([leg_x + leg_w * 0.08, leg_x + leg_w * 0.20], [iy, iy], color=handle.get_color(), lw=handle.get_linewidth(), zorder=25)
        elif isinstance(handle, Patch):
            ax.add_patch(Rectangle((leg_x + leg_w * 0.08, iy - leg_h * 0.035), leg_w * 0.12, leg_h * 0.07,
                                   facecolor=handle.get_facecolor(), edgecolor=handle.get_edgecolor(), lw=0.5, zorder=25))
        ax.text(leg_x + leg_w * 0.26, iy, label, fontsize=5.8, va="center", color="#2c3e50", zorder=25)

    add_scalebar(ax, sb_x0, sb_y0, 30)
    add_compass(ax)

    out_path = os.path.join(OUT_DIR, "fig02-00-1_天津市地形地貌与海陆水系格局图.png")
    plt.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_path}")

# =============================================================================
# 图 2：天津市行政区划与“津城-滨城”双城空间骨架图 (fig02-00-2)
# =============================================================================
def make_fig2():
    print("Generating fig02-00-2: 行政区划与双城格局图（中心六区径向引出）...")
    fig, ax = plt.subplots(figsize=(10.0, 10.2), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.set_axis_off()

    color_map = {
        120101: "#f9ebea", 120102: "#f9ebea", 120103: "#f9ebea",
        120104: "#f9ebea", 120105: "#f9ebea", 120106: "#f9ebea",
        120116: "#d4e6f1",
        120110: "#d1f2eb", 120111: "#d1f2eb", 120112: "#d1f2eb", 120113: "#d1f2eb",
        120114: "#fef5e7", 120115: "#fef5e7", 120117: "#fef5e7", 120118: "#fef5e7", 120119: "#eaeded"
    }

    for _, row in tj_districts.iterrows():
        adc = int(row["adcode"])
        c = color_map.get(adc, "#f2f4f4")
        gpd.GeoSeries([row.geometry], crs=ALBERS).plot(ax=ax, facecolor=c, edgecolor="#7f8c8d", lw=0.6, zorder=4)

    gpd.GeoSeries([tj_union], crs=ALBERS).plot(ax=ax, facecolor="none", edgecolor="#1a5276", lw=1.6, zorder=6)

    # 津沽绿色生态屏障
    green_barrier_coords = [
        to_alb(117.28, 39.02), to_alb(117.48, 39.08), to_alb(117.58, 38.98),
        to_alb(117.45, 38.88), to_alb(117.25, 38.92)
    ]
    ax.add_patch(plt.Polygon(green_barrier_coords, facecolor="#27ae60", edgecolor="#196f3d", lw=1.0, linestyle="--", alpha=0.35, zorder=7))
    gb_cx, gb_cy = to_alb(117.42, 38.95)
    ax.text(gb_cx, gb_cy, "津沽绿色生态屏障\n(736 km² 双城绿廊)", fontsize=6.8, fontweight="bold", color="#145a32",
            ha="center", va="center", zorder=15, path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])

    # 津城主核
    jc_x, jc_y = to_alb(117.18, 39.12)
    ax.add_patch(plt.Circle((jc_x, jc_y), 8500, facecolor="none", edgecolor="#c0392b", lw=1.8, linestyle=":", zorder=10))
    ax.text(jc_x - 12000, jc_y + 12000, "【津城】核心区", fontsize=7.6, fontweight="bold", color="#922b21",
            ha="right", va="center", zorder=15, path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])

    # 滨城极核
    bc_x, bc_y = to_alb(117.65, 39.02)
    ax.add_patch(plt.Circle((bc_x, bc_y), 13500, facecolor="none", edgecolor="#2980b9", lw=1.8, linestyle=":", zorder=10))
    ax.text(bc_x, bc_y + 14200, "【滨城】极核区", fontsize=7.6, fontweight="bold", color="#1f618d",
            ha="center", va="bottom", zorder=15, path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])

    # 发展轴向走廊
    ax.annotate("", xy=(bc_x - 13500, bc_y), xytext=(jc_x + 8500, jc_y),
                arrowprops=dict(arrowstyle="<->", color="#8e44ad", lw=1.8, linestyle="-"), zorder=12)
    mid_ax = (jc_x + bc_x) / 2.0
    mid_ay = (jc_y + bc_y) / 2.0 + 9500
    ax.text(mid_ax, mid_ay, "海河高质量发展轴", fontsize=6.8, fontweight="bold", color="#6c3483",
            ha="center", va="bottom", zorder=15, path_effects=[pe.withStroke(linewidth=2.0, foreground="white")])

    # 16 个区行政中心与区名标注（核心6区大跨度径向引出，彻底根除叠压）
    district_labels = [
        # 核心6区：径向辐射引出
        ("和平区", 117.200, 39.115, -16000, -8000, "right", True),
        ("河东区", 117.240, 39.125, 18000, 16000, "left", True),
        ("河西区", 117.210, 39.085, 14000, -18000, "left", True),
        ("南开区", 117.150, 39.120, -20000, 2000, "right", True),
        ("河北区", 117.200, 39.160, 0, 18000, "center", True),
        ("红桥区", 117.140, 39.175, -18000, 14000, "right", True),
        # 环城与外围各区
        ("东丽区", 117.40, 39.18, 0, 0, "center", False),
        ("西青区", 116.98, 38.98, 0, 0, "center", False),
        ("津南区", 117.38, 38.86, 0, 0, "center", False),
        ("北辰区", 117.13, 39.25, 0, 0, "center", False),
        ("武清区", 117.06, 39.38, 0, 0, "center", False),
        ("宝坻区", 117.31, 39.72, 0, 0, "center", False),
        ("滨海新区", 117.65, 39.03, 0, 0, "center", False),
        ("宁河区", 117.83, 39.33, 0, 0, "center", False),
        ("静海区", 116.92, 38.94, 0, 0, "center", False),
        ("蓟州区", 117.41, 40.05, 0, 0, "center", False)
    ]
    for dname, dlon, dlat, ox, oy, ha, has_arrow in district_labels:
        dx, dy = to_alb(dlon, dlat)
        fsize = 6.8 if dname in ["和平区", "河东区", "河西区", "南开区", "河北区", "红桥区"] else 7.2
        col = "#922b21" if dname in ["和平区", "河东区", "河西区", "南开区", "河北区", "红桥区"] else "#1a252f"
        ax.plot(dx, dy, marker="*", color="#c0392b" if "和平" in dname else "#2980b9", markersize=5.0, zorder=16)
        if has_arrow:
            ax.annotate(dname, xy=(dx, dy), xytext=(dx + ox, dy + oy),
                        arrowprops=dict(arrowstyle="->", color="#922b21", lw=0.7),
                        fontsize=fsize, fontweight="bold", color=col, ha=ha, va="center", zorder=18,
                        path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])
        else:
            ax.text(dx + ox, dy + oy, dname, fontsize=fsize, fontweight="bold", color=col, ha=ha, va="center", zorder=18,
                    path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])

    ax.text(cx, cy + half_span_y * 1.05, "天津市行政区划与“津城—滨城”双城空间骨架图", fontsize=12.0, fontweight="bold",
            ha="center", va="top", color="#1a252f", zorder=30)
    ax.text(cx, cy + half_span_y * 1.01, "Administrative Divisions & 'Twin-City' Spatial Framework of Tianjin", fontsize=7.2,
            style="italic", ha="center", va="top", color="#566573", zorder=30)

    # 图例框
    leg_x = cx - half_span_x * 0.95
    leg_y = cy - half_span_y * 0.90
    leg_w = half_span_x * 0.46
    leg_h = half_span_y * 0.32
    ax.add_patch(Rectangle((leg_x, leg_y), leg_w, leg_h, facecolor="white", edgecolor="#bdc3c7", lw=0.8, alpha=0.92, zorder=24))
    ax.text(leg_x + leg_w * 0.5, leg_y + leg_h * 0.88, "功能板块图例 (Legend)", fontsize=7.2, fontweight="bold", ha="center", va="center", color="#2c3e50", zorder=25)

    items = [
        (Patch(facecolor='#f9ebea', edgecolor='#c0392b', lw=0.7), "中心城区（津城核心·现代服务）"),
        (Patch(facecolor='#d4e6f1', edgecolor='#2980b9', lw=0.7), "滨海新区（滨城极核·先进智造航运）"),
        (Patch(facecolor='#d1f2eb', edgecolor='#16a085', lw=0.7), "环城四区（协同拓展·先进制造）"),
        (Patch(facecolor='#fef5e7', edgecolor='#d35400', lw=0.7), "外围平原区（京津走廊与生态田园）"),
        (Patch(facecolor='#eaeded', edgecolor='#7f8c8d', lw=0.7), "蓟州区（燕山生态涵养与名胜区）"),
        (Patch(facecolor='#27ae60', edgecolor='#196f3d', lw=1.0, linestyle='--'), "津沽绿色生态屏障 (736 km²)")
    ]
    for idx, (handle, label) in enumerate(items):
        iy = leg_y + leg_h * (0.74 - idx * 0.11)
        ax.add_patch(Rectangle((leg_x + leg_w * 0.08, iy - leg_h * 0.035), leg_w * 0.12, leg_h * 0.065,
                               facecolor=handle.get_facecolor(), edgecolor=handle.get_edgecolor(),
                               lw=handle.get_linewidth(), linestyle=handle.get_linestyle(), zorder=25))
        ax.text(leg_x + leg_w * 0.25, iy, label, fontsize=5.6, va="center", color="#2c3e50", zorder=25)

    add_scalebar(ax, sb_x0, sb_y0, 30)
    add_compass(ax)

    out_path = os.path.join(OUT_DIR, "fig02-00-2_天津市行政区划与空间骨架图.png")
    plt.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_path}")

# =============================================================================
# 图 3：天津市综合立体交通网与海陆空枢纽图 (fig02-00-3)
# =============================================================================
def make_fig3():
    print("Generating fig02-00-3: 综合立体交通网与枢纽图...")
    fig, ax = plt.subplots(figsize=(10.0, 10.2), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.set_axis_off()

    tj_districts.plot(ax=ax, facecolor="#f8f9f9", edgecolor="#d5dbdb", lw=0.5, zorder=3)
    gpd.GeoSeries([tj_union]).boundary.plot(ax=ax, color="#2c3e50", lw=1.6, zorder=7)

    # 真实路网：国道/省市干路作淡色衬底，高速压在上面
    if len(tj_trunk) > 0:
        tj_trunk.plot(ax=ax, color="#e0b34a", lw=0.45, alpha=0.85, zorder=8)
    if len(tj_express) > 0:
        tj_express.plot(ax=ax, color="#e67e22", lw=0.85, alpha=0.95, zorder=9)
    if len(tj_rail_main) > 0:
        tj_rail_main.plot(ax=ax, color="#2c3e50", lw=1.05, zorder=10)

    # 图面零文字：所有要素只画「符号 + 编号」，名称与含义统一进图外图例。
    # 旧版把完整名称压在图上（「天津滨海国际机场（4E 级双跑道国家枢纽）」
    # 一行约 230 px），而滨海三站相距不足 30 px，任何避让算法都排不开。
    sl = mapkit.SymbolLabels(ax, fig)
    sl.reserve([(0.00, 0.00, 0.42, 0.30),    # 图例
                (0.62, 0.00, 1.00, 0.10),    # 比例尺
                (0.88, 0.83, 1.00, 1.00)])   # 指北针

    # 铁路廊道：符号统一为红叉，走向由底图真实铁路线表达
    corridors = [
        ("京津城际铁路", 117.13, 39.26, "350 km/h · 京津主轴"),
        ("京沪高铁", 117.02, 39.22, "350 km/h · 南下主通道"),
        ("津秦客专", 117.82, 39.24, "350 km/h · 东北向"),
        ("津保铁路", 116.84, 39.10, "200 km/h · 西向联络"),
        ("京唐城际", 117.42, 39.71, "350 km/h · 京东通道"),
        ("京滨城际", 117.34, 39.52, "350 km/h · 宝坻—滨海"),
        ("津兴城际", 116.88, 39.34, "350 km/h · 大兴机场向"),
    ]
    for cname, clon, clat, note in corridors:
        cx_c, cy_c = to_alb(clon, clat)
        sl.add(cx_c, cy_c, cname, "corridor", note=note)

    # 枢纽：类型决定符号颜色与形状，编号按下列顺序自增
    hubs = [
        ("天津站", 117.21, 39.14, "rail_hub", "三线交汇特等站"),
        ("天津西站", 117.16, 39.16, "rail_hub", "京沪高铁客运枢纽"),
        ("天津南站", 117.06, 39.06, "rail_hub", "京沪客运干线站"),
        ("滨海站", 117.67, 39.01, "rail_mid", "于家堡高铁枢纽"),
        ("滨海西站", 117.62, 39.07, "rail_mid", "津秦客专枢纽"),
        ("武清站", 117.06, 39.38, "rail_mid", "京津城际首站"),
        ("宝坻站", 117.32, 39.72, "rail_mid", "三城际交汇枢纽"),
        ("天津滨海国际机场", 117.35, 39.12, "airport", "TSN · 4E 级双跑道国家枢纽"),
        ("天津港", 117.75, 38.99, "port", "北方国际航运核心区 · 年吞吐超 5.5 亿吨"),
        ("北疆港区", 117.72, 39.02, "port_zone", "集装箱"),
        ("东疆港区", 117.78, 39.05, "port_zone", "冷链 / 保税"),
        ("南疆港区", 117.74, 38.94, "port_zone", "散货 / 原油"),
        ("大沽口港区", 117.70, 38.90, "port_zone", "临港工业"),
    ]
    for hname, hlon, hlat, htype, hnote in hubs:
        hx, hy = to_alb(hlon, hlat)
        sl.add(hx, hy, hname, htype, note=hnote)
    sym_type_h, sym_idx_h = sl.flush()

    ax.text(cx, cy + half_span_y * 1.05, "天津市综合立体交通网与海陆空枢纽图", fontsize=12.0, fontweight="bold",
            ha="center", va="top", color="#1a252f", zorder=30)
    ax.text(cx, cy + half_span_y * 1.01, "Comprehensive Transportation Network & Strategic Hubs of Tianjin", fontsize=7.2,
            style="italic", ha="center", va="top", color="#566573", zorder=30)

    add_scalebar(ax, sb_x0, sb_y0, 30)
    add_compass(ax)

    # 图例分两组堆叠到图幅下方：① 线型与符号含义 ② 图上编号对照
    road_h = [
        Line2D([0], [0], color="#e67e22", lw=1.4, label="国家高速公路"),
        Line2D([0], [0], color="#e0b34a", lw=1.2, label="国道 / 省市干路"),
        Line2D([0], [0], color="#2c3e50", lw=1.4, label="国铁干线"),
        Patch(facecolor="none", edgecolor="#2c3e50", linewidth=1.6, label="天津市辖区边界"),
    ]
    last = mapkit.stacked_legends(ax, [
        dict(handles=road_h + sym_type_h, title="线型与符号含义", ncol=4,
             fontsize=6.6, title_fontsize=7.2),
        dict(handles=sym_idx_h, title="图上编号对照（编号标注于符号旁）", ncol=3,
             fontsize=6.6, title_fontsize=7.2),
    ], top=-0.010, gap=0.013)
    mapkit.footer_below_legend(
        ax, last, "数据源：OpenStreetMap (2026) · 中国国家铁路集团 · 天津港集团 · 制作：《中国地理知识手册》")

    out_path = os.path.join(OUT_DIR, "fig02-00-3_天津市综合立体交通网与海陆空枢纽图.png")
    plt.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_path}")

# =============================================================================
# 图 4：天津市产业经济与先进制造研发走廊图 (fig02-00-4)
# =============================================================================
def make_fig4():
    print("Generating fig02-00-4: 产业经济与先进制造研发走廊图...")
    fig, ax = plt.subplots(figsize=(10.0, 10.2), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.set_axis_off()

    tj_districts.plot(ax=ax, facecolor="#fdfefe", edgecolor="#bdc3c7", lw=0.6, zorder=3)
    gpd.GeoSeries([tj_union], crs=ALBERS).plot(ax=ax, facecolor="none", edgecolor="#1a5276", lw=1.6, zorder=4)

    # 1. 京津冀科创走廊
    p1 = [to_alb(117.02, 39.45), to_alb(117.08, 39.35), to_alb(117.15, 39.22), to_alb(117.18, 39.12)]
    xs, ys = mapkit.smooth_line(p1)
    ax.plot(xs, ys, color="#9b59b6", lw=4.0, alpha=0.30, zorder=5)
    ax.plot(xs, ys, color="#8e44ad", lw=1.5, linestyle="--", zorder=6)
    ax.text(xs[1] - 1200, ys[1] - 2500, "京津科创走廊", fontsize=6.2, fontweight="bold", color="#6c3483",
            ha="right", va="center", zorder=12, path_effects=[pe.withStroke(linewidth=1.8, foreground="white")])

    # 2. 海河高端制造主轴
    p2 = [to_alb(117.18, 39.12), to_alb(117.38, 39.06), to_alb(117.65, 39.02)]
    xs, ys = mapkit.smooth_line(p2)
    ax.plot(xs, ys, color="#3498db", lw=5.0, alpha=0.30, zorder=5)
    ax.plot(xs, ys, color="#2980b9", lw=1.8, zorder=6)
    ax.text(xs[1], ys[1] - 4200, "海河高端智造创新轴", fontsize=6.5, fontweight="bold", color="#1b4f72",
            ha="center", va="top", zorder=12, path_effects=[pe.withStroke(linewidth=1.8, foreground="white")])

    # 3. 沿海重工与石化产业带
    p3 = [to_alb(117.72, 39.05), to_alb(117.68, 38.92), to_alb(117.55, 38.72)]
    xs, ys = mapkit.smooth_line(p3)
    ax.plot(xs, ys, color="#e67e22", lw=4.5, alpha=0.30, zorder=5)
    ax.plot(xs, ys, color="#d35400", lw=1.6, zorder=6)
    ax.text(xs[1] + 2500, ys[1], "沿海先进石化重工带", fontsize=6.2, fontweight="bold", color="#ba4a00",
            ha="left", va="center", zorder=12, path_effects=[pe.withStroke(linewidth=1.8, foreground="white")])

    # 产业园区点位（精细错落，杜绝叠压）
    parks = [
        ("天开高教科创园 (核心区)\n(南开/天大智力策源)", 117.16, 39.11, "tech", -2500, 3200, "right"),
        ("天开西青拓展区\n(智能制造转化)", 117.05, 39.10, "tech", -2200, -500, "right"),
        ("天开津南拓展区 (海教园)\n(产教融合集聚地)", 117.36, 38.98, "tech", 2200, -1600, "left"),
        ("天津经开区 (TEDA)\n(汽车/医药/电子信息)", 117.68, 39.03, "eda", 0, -3200, "center"),
        ("滨海高新技术产业区\n(国家级·信创谷)", 117.58, 39.08, "tech", 0, 2000, "center"),
        ("临空经济区 (航空航天城)\n(空客A320/A350总装)", 117.38, 39.12, "aero", 0, 4200, "center"),
        ("中新天津生态城\n(绿色智慧城市示范)", 117.75, 39.15, "eco", 2000, 0, "left"),
        ("东疆综合保税区\n(全球融资租赁高地)", 117.78, 39.02, "finance", 2000, 800, "left"),
        ("南港工业区 (世界级石化基地)\n(百万吨级乙烯一体化)", 117.55, 38.72, "chemi", 2000, -800, "left"),
        ("武清京津产业新城\n(智能装备与电商)", 117.06, 39.38, "eda", 1800, 0, "left"),
        ("宝坻中关村科技城\n(新一代信息技术)", 117.35, 39.75, "tech", 1800, 0, "left"),
        ("西青微电子工业区\n(集成电路封装基地)", 117.18, 39.04, "tech", -2500, -3200, "right"),
        ("北辰京津医药谷\n(现代中药与生物医药)", 117.15, 39.26, "med", -1800, 0, "right"),
        ("静海子牙循环经济区\n(国家循环经济示范)", 116.85, 38.85, "eco", 1800, 1200, "left")
    ]

    marker_dict = {
        "tech": ("D", "#8e44ad"),
        "eda": ("s", "#c0392b"),
        "aero": ("^", "#2980b9"),
        "eco": ("o", "#27ae60"),
        "finance": ("p", "#f39c12"),
        "chemi": ("v", "#d35400"),
        "med": ("h", "#16a085")
    }

    for pname, plon, plat, ptype, ox, oy, ha in parks:
        px, py = to_alb(plon, plat)
        m, col = marker_dict.get(ptype, ("o", "#2c3e50"))
        ax.plot(px, py, marker=m, color=col, markersize=5.5, markeredgecolor="white", markeredgewidth=0.7, zorder=15)
        ax.annotate(pname, xy=(px, py), xytext=(px + ox, py + oy),
                    arrowprops=dict(arrowstyle="->", color="#7f8c8d", lw=0.5),
                    fontsize=5.8, fontweight="bold", color="#1a252f", ha=ha, va="center", zorder=18,
                    path_effects=[pe.withStroke(linewidth=2.0, foreground="white")])

    ax.text(cx, cy + half_span_y * 1.05, "天津市产业经济与先进制造研发走廊图", fontsize=12.0, fontweight="bold",
            ha="center", va="top", color="#1a252f", zorder=30)
    ax.text(cx, cy + half_span_y * 1.01, "Industrial Corridors & Advanced Manufacturing Hubs of Tianjin", fontsize=7.2,
            style="italic", ha="center", va="top", color="#566573", zorder=30)

    # 图例框置于西南角
    leg_x = cx - half_span_x * 0.95
    leg_y = cy - half_span_y * 0.90
    leg_w = half_span_x * 0.46
    leg_h = half_span_y * 0.32
    ax.add_patch(Rectangle((leg_x, leg_y), leg_w, leg_h, facecolor="white", edgecolor="#bdc3c7", lw=0.8, alpha=0.92, zorder=24))
    ax.text(leg_x + leg_w * 0.5, leg_y + leg_h * 0.88, "产业功能图例 (Legend)", fontsize=7.2, fontweight="bold", ha="center", va="center", color="#2c3e50", zorder=25)

    items = [
        (Line2D([0], [0], marker='D', color='w', markerfacecolor='#8e44ad', markersize=5), "天开高教/高新区/硬科技集聚区"),
        (Line2D([0], [0], marker='s', color='w', markerfacecolor='#c0392b', markersize=5), "国家级经开区 / 重点智造新城"),
        (Line2D([0], [0], marker='^', color='w', markerfacecolor='#2980b9', markersize=5), "空客总装 / 航空航天产业基地"),
        (Line2D([0], [0], marker='p', color='w', markerfacecolor='#f39c12', markersize=5), "东疆融资租赁 / 现代航运金融"),
        (Line2D([0], [0], marker='v', color='w', markerfacecolor='#d35400', markersize=5), "南港世界级绿色石化产业基地"),
        (Line2D([0], [0], marker='o', color='w', markerfacecolor='#27ae60', markersize=5), "绿色生态城 / 循环经济产业区")
    ]
    for idx, (handle, label) in enumerate(items):
        iy = leg_y + leg_h * (0.74 - idx * 0.11)
        ax.plot(leg_x + leg_w * 0.14, iy, marker=handle.get_marker(), color=handle.get_markerfacecolor(), markersize=handle.get_markersize(), zorder=25)
        ax.text(leg_x + leg_w * 0.25, iy, label, fontsize=5.6, va="center", color="#2c3e50", zorder=25)

    add_scalebar(ax, sb_x0, sb_y0, 30)
    add_compass(ax)

    out_path = os.path.join(OUT_DIR, "fig02-00-4_天津市产业经济与先进制造研发走廊图.png")
    plt.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_path}")

# =============================================================================
# 图 5：天津市生态屏障与历史文化空间分布图 (fig02-00-5)
# =============================================================================
def make_fig5():
    print("Generating fig02-00-5: 生态屏障与历史文化空间分布图...")
    fig, ax = plt.subplots(figsize=(10.0, 10.2), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.set_axis_off()

    tj_districts.plot(ax=ax, facecolor="#fbfcfc", edgecolor="#bdc3c7", lw=0.6, zorder=3)
    gpd.GeoSeries([tj_union], crs=ALBERS).plot(ax=ax, facecolor="none", edgecolor="#1a5276", lw=1.6, zorder=4)

    # 1. 北部山地生态屏障
    north_mtn_coords = [
        to_alb(117.20, 40.10), to_alb(117.40, 40.25), to_alb(117.65, 40.22),
        to_alb(117.60, 40.05), to_alb(117.30, 40.00)
    ]
    ax.add_patch(plt.Polygon(north_mtn_coords, facecolor="#52be80", edgecolor="#1e8449", lw=1.0, linestyle="--", alpha=0.35, zorder=5))
    nm_x, nm_y = to_alb(117.48, 40.08)
    ax.text(nm_x, nm_y, "蓟北燕山生态屏障\n(国家地质公园·森林水源)", fontsize=6.0, fontweight="bold", color="#145a32",
            ha="center", va="center", zorder=12, path_effects=[pe.withStroke(linewidth=2.0, foreground="white")])

    # 2. 中部津沽绿色生态屏障
    green_barrier_coords = [
        to_alb(117.28, 39.02), to_alb(117.48, 39.08), to_alb(117.58, 38.98),
        to_alb(117.45, 38.88), to_alb(117.25, 38.92)
    ]
    ax.add_patch(plt.Polygon(green_barrier_coords, facecolor="#27ae60", edgecolor="#196f3d", lw=1.0, linestyle="-", alpha=0.35, zorder=5))
    gb_cx, gb_cy = to_alb(117.42, 38.96)
    ax.text(gb_cx, gb_cy, "津沽绿色生态屏障 (736 km²)\n“一轴两廊两带多组团”", fontsize=6.8, fontweight="bold", color="#145a32",
            ha="center", va="center", zorder=12, path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])

    # 3. 真实水系底色（自然保护区水体）
    main_tj_lakes.plot(ax=ax, facecolor="#76d7c4", edgecolor="#117864", lw=0.4, alpha=0.6, zorder=6)

    # 四大湿地注记
    wetland_notes = [
        ("七里海湿地\n(国家级自然保护区)", 117.58, 39.30, 2000, 1800, "left"),
        ("大黄堡湿地自然保护区", 117.26, 39.45, -2000, 1800, "right"),
        ("团泊湿地自然保护区", 117.17, 38.92, -2000, 1500, "right"),
        ("北大港湿地自然保护区", 117.42, 38.74, 2000, -1800, "left")
    ]
    for wname, wlon, wlat, ox, oy, ha in wetland_notes:
        wx, wy = to_alb(wlon, wlat)
        ax.annotate(wname, xy=(wx, wy), xytext=(wx + ox, wy + oy),
                    arrowprops=dict(arrowstyle="->", color="#117864", lw=0.5),
                    fontsize=6.2, fontweight="bold", color="#0e6251", ha=ha, va="center", zorder=14,
                    path_effects=[pe.withStroke(linewidth=1.8, foreground="white")])

    # 4. 历史文化核心空间与名胜遗产（错开偏移）
    heritage = [
        ("黄崖关长城\n(世界文化遗产·明长城)", 117.44, 40.24, "unesco", -2000, 1800, "right"),
        ("盘山国家重点名胜区\n(“早知有盘山，何必下江南”)", 117.26, 40.08, "scenic", -2200, 0, "right"),
        ("独乐寺 (辽代古建大木作)", 117.40, 40.04, "history", 1800, -1400, "left"),
        ("中上元古界地层剖面", 117.45, 40.16, "geology", 1800, 1200, "left"),
        ("五大道历史街区 (小洋楼建筑群)", 117.20, 39.11, "history", -2200, -2200, "right"),
        ("意式风情区 (百年意租界)", 117.20, 39.14, "history", 1800, 2600, "left"),
        ("古文化街 (津门故里·天后宫)", 117.18, 39.14, "history", -1800, 2600, "right"),
        ("杨柳青千年古镇 (石家大院)", 117.00, 39.14, "history", -2200, 1600, "right"),
        ("大沽口炮台遗址 (近代海防要塞)", 117.70, 38.98, "history", 2200, -1200, "left"),
        ("大直沽天后宫 (津沽发祥地)", 117.24, 39.11, "history", 2200, -1800, "left")
    ]

    h_markers = {
        "unesco": ("*", "#c0392b", 7.5),
        "scenic": ("^", "#d35400", 5.5),
        "history": ("s", "#8e44ad", 5.0),
        "geology": ("D", "#2980b9", 5.0)
    }

    for hname, hlon, hlat, htype, ox, oy, ha in heritage:
        hx, hy = to_alb(hlon, hlat)
        m, col, ms = h_markers.get(htype, ("o", "#2c3e50", 5.0))
        ax.plot(hx, hy, marker=m, color=col, markersize=ms, markeredgecolor="white", markeredgewidth=0.7, zorder=16)
        ax.annotate(hname, xy=(hx, hy), xytext=(hx + ox, hy + oy),
                    arrowprops=dict(arrowstyle="->", color="#7f8c8d", lw=0.5),
                    fontsize=5.8, fontweight="bold", color="#1a252f", ha=ha, va="center", zorder=18,
                    path_effects=[pe.withStroke(linewidth=2.0, foreground="white")])

    ax.text(cx, cy + half_span_y * 1.05, "天津市生态屏障与历史文化空间分布图", fontsize=12.0, fontweight="bold",
            ha="center", va="top", color="#1a252f", zorder=30)
    ax.text(cx, cy + half_span_y * 1.01, "Ecological Barriers & Historical Cultural Heritage of Tianjin", fontsize=7.2,
            style="italic", ha="center", va="top", color="#566573", zorder=30)

    # 图例框置于西南角
    leg_x = cx - half_span_x * 0.95
    leg_y = cy - half_span_y * 0.90
    leg_w = half_span_x * 0.46
    leg_h = half_span_y * 0.32
    ax.add_patch(Rectangle((leg_x, leg_y), leg_w, leg_h, facecolor="white", edgecolor="#bdc3c7", lw=0.8, alpha=0.92, zorder=24))
    ax.text(leg_x + leg_w * 0.5, leg_y + leg_h * 0.88, "生态文化图例 (Legend)", fontsize=7.2, fontweight="bold", ha="center", va="center", color="#2c3e50", zorder=25)

    items = [
        (Line2D([0], [0], marker='*', color='w', markerfacecolor='#c0392b', markersize=7), "世界文化遗产 (黄崖关长城)"),
        (Line2D([0], [0], marker='s', color='w', markerfacecolor='#8e44ad', markersize=5), "全国重点文保/历史文化名城街区"),
        (Line2D([0], [0], marker='^', color='w', markerfacecolor='#d35400', markersize=5), "国家级重点风景名胜区 (盘山)"),
        (Line2D([0], [0], marker='D', color='w', markerfacecolor='#2980b9', markersize=5), "国家级地质公园 / 地质地层剖面"),
        (Patch(facecolor='#27ae60', edgecolor='#196f3d', lw=1.0), "津沽绿色生态屏障 (736 km²)"),
        (Patch(facecolor='#76d7c4', edgecolor='#117864', lw=1.0), "四大湿地自然保护区水体 (七里海等)")
    ]
    for idx, (handle, label) in enumerate(items):
        iy = leg_y + leg_h * (0.74 - idx * 0.11)
        if isinstance(handle, Line2D):
            ax.plot(leg_x + leg_w * 0.14, iy, marker=handle.get_marker(), color=handle.get_markerfacecolor(), markersize=handle.get_markersize(), zorder=25)
        elif isinstance(handle, Patch):
            ax.add_patch(Rectangle((leg_x + leg_w * 0.08, iy - leg_h * 0.035), leg_w * 0.12, leg_h * 0.065,
                                   facecolor=handle.get_facecolor(), edgecolor=handle.get_edgecolor(),
                                   lw=handle.get_linewidth(), zorder=25))
        ax.text(leg_x + leg_w * 0.25, iy, label, fontsize=5.6, va="center", color="#2c3e50", zorder=25)

    add_scalebar(ax, sb_x0, sb_y0, 30)
    add_compass(ax)

    out_path = os.path.join(OUT_DIR, "fig02-00-5_天津市生态屏障与历史文化空间分布图.png")
    plt.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_path}")

if __name__ == "__main__":
    make_fig1()
    make_fig2()
    make_fig3()
    make_fig4()
    make_fig5()
    print("\nAll 5 Tianjin municipal overview maps generated successfully!")
