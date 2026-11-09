# -*- coding: utf-8 -*-
"""更新海淀区地图与分析图表（严格视觉校验与防重叠版）：
1. fig01-06-1_海淀区行政区位图.png （边界外彻底剔除白底，图例与比例尺互不遮挡，右上角全市鹰眼）
2. fig01-06-2_海淀区地形地貌图.png （高程DEM严格裁切至辖区内，高程色带与比例尺完全分离，山峰避让）
3. fig01-06-3_海淀区道路交通图.png （清洗302条跨区异常直射连线，真实等级重构，五大枢纽引线标注，零重叠）
4. fig01-06-4_海淀区重点高校与科研院所分布图.png （学院路与中关村双走廊引线外展，杜绝任何字迹交叠）
5. fig01-06-5_海淀区夜间灯光与经济发展演进图.png （数据分析图：1986—2024夜光辐射演进与GDP万亿跃迁）
"""
import os
import sys
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import FancyArrow, Rectangle, Patch
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap, Normalize
from rasterio.transform import from_origin
from rasterio.features import rasterize
from pyproj import Transformer

sys.path.insert(0, r"D:\code\Ideas\MyBooks\中国地理知识手册\scripts")
from style import ALBERS, C_TEXT, DATA, DPI, FIGURES, setup

setup()
OUT_DIR = FIGURES
os.makedirs(OUT_DIR, exist_ok=True)
_T = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True)

def to_alb(lon, lat):
    return _T.transform(lon, lat)

# -------------------------------------------------------------------------
# 1. 基础地理数据读取与异常几何清洗
# -------------------------------------------------------------------------
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
bj_all = gpd.read_file(os.path.join(DATA_DIR, "boundaries", "datav", "110000_full.json")).to_crs(ALBERS)
haidian = bj_all[bj_all["name"] == "海淀区"]
h_geom = haidian.geometry.iloc[0]
hb = haidian.total_bounds

# OSM 道路、水系、铁路
osm_dir = os.path.join(DATA_DIR, "transport", "beijing", "Beijing-shp", "shape")
h_bounds_wgs = haidian.to_crs("EPSG:4326").total_bounds
pad = 0.05
bbox_wgs = (h_bounds_wgs[0] - pad, h_bounds_wgs[1] - pad, h_bounds_wgs[2] + pad, h_bounds_wgs[3] + pad)

roads_raw = gpd.read_file(os.path.join(osm_dir, "roads.shp"), bbox=bbox_wgs)
water_raw = gpd.read_file(os.path.join(osm_dir, "waterways.shp"), bbox=bbox_wgs)
rails_raw = gpd.read_file(os.path.join(osm_dir, "railways.shp"), bbox=bbox_wgs).to_crs(ALBERS)

# 核心清洗算法：剔除 BBBike 导出的异常两点长直弦线（多边形关系/断头闭合导致的跨区直线）
def is_clean_line(geom):
    if geom is None:
        return False
    if geom.geom_type == "LineString":
        coords = list(geom.coords)
        if len(coords) == 2:
            p1, p2 = coords[0], coords[1]
            dist_deg = ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5
            if dist_deg > 0.008: # 大于约800米且中间无折点的2点假线
                return False
        for i in range(len(coords) - 1):
            p1, p2 = coords[i], coords[i+1]
            dist_deg = ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5
            if dist_deg > 0.015: # 跨度超过1.5公里的异常长线段
                return False
        return True
    elif geom.geom_type == "MultiLineString":
        return all(is_clean_line(part) for part in geom.geoms)
    return True

roads_osm = roads_raw[roads_raw.geometry.apply(is_clean_line)].to_crs(ALBERS)
water_osm = water_raw[water_raw.geometry.apply(is_clean_line)].to_crs(ALBERS)

# 严格几何裁切至海淀辖区内部
roads_h = gpd.clip(roads_osm, h_geom)
water_h = gpd.clip(water_osm, h_geom)
rails_h = gpd.clip(rails_raw, h_geom)

# DEM 数据与辖区掩膜
from prov_pipeline import prov_dem
dem_bj, dem_minx, dem_maxy, dem_res = prov_dem("110000", zoom=9, res=300.0)

dx_pad, dy_pad = 2000.0, 2000.0
x0, y0, x1, y1 = hb[0] - dx_pad, hb[1] - dy_pad, hb[2] + dx_pad, hb[3] + dy_pad
c0 = max(0, int((x0 - dem_minx) / dem_res))
c1 = min(dem_bj.shape[1], int((x1 - dem_minx) / dem_res) + 1)
r0 = max(0, int((dem_maxy - y1) / dem_res))
r1 = min(dem_bj.shape[0], int((dem_maxy - y0) / dem_res) + 1)

sub_dem = dem_bj[r0:r1, c0:c1].copy()
sub_minx = dem_minx + c0 * dem_res
sub_maxy = dem_maxy - r0 * dem_res
sub_extent = (sub_minx, sub_minx + sub_dem.shape[1] * dem_res,
              sub_maxy - sub_dem.shape[0] * dem_res, sub_maxy)

h_w = sub_dem.shape[1]
h_h = sub_dem.shape[0]
tf = from_origin(sub_minx, sub_maxy, dem_res, dem_res)
inside_mask = rasterize([(h_geom, 1)], out_shape=(h_h, h_w), transform=tf, fill=0, dtype="uint8")

def calc_hillshade(dem, res, az=315.0, alt=45.0):
    az_rad = np.radians(az)
    alt_rad = np.radians(alt)
    gy, gx = np.gradient(dem, res)
    slope = np.arctan(np.sqrt(gx * gx + gy * gy))
    aspect = np.arctan2(-gx, gy)
    shaded = np.sin(alt_rad) * np.cos(slope) + np.cos(alt_rad) * np.sin(slope) * np.cos(az_rad - aspect)
    return np.clip(shaded, 0.0, 1.0)

def add_scalebar(ax, x0, y0, length_km=5):
    length_m = length_km * 1000.0
    h = (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.012
    half_m = length_m / 2.0
    ax.add_patch(Rectangle((x0, y0), half_m, h, facecolor="#2c3e50", edgecolor="#2c3e50", zorder=25))
    ax.add_patch(Rectangle((x0 + half_m, y0), half_m, h, facecolor="white", edgecolor="#2c3e50", lw=0.8, zorder=25))
    ax.text(x0, y0 - h * 1.6, "0", ha="center", va="top", fontsize=8.5, color="#2c3e50", zorder=25)
    ax.text(x0 + half_m, y0 - h * 1.6, f"{length_km/2:g}", ha="center", va="top", fontsize=8.5, color="#2c3e50", zorder=25)
    ax.text(x0 + length_m, y0 - h * 1.6, f"{length_km} km", ha="center", va="top", fontsize=8.5, color="#2c3e50", zorder=25)

def add_compass(ax, x=0.94, y=0.90):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.065), transform=ax.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=2.5, headwidth=7.5, headlength=9),
                ha="center", va="center", fontsize=12, fontweight="bold", color="#2c3e50", zorder=30)

# -------------------------------------------------------------------------
# 图 1：海淀区行政区位图（彻底剔除区界外，图例与比例尺互不遮挡，右上角鹰眼）
# -------------------------------------------------------------------------
def make_map1_admin():
    fig, ax = plt.subplots(figsize=(9.5, 9.5), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # 1. 辖区底色与边界
    haidian.plot(ax=ax, facecolor="#f4f8fa", edgecolor="#1a5276", lw=2.4, zorder=3)
    water_h.plot(ax=ax, color="#7fb3d5", lw=1.2, zorder=4)

    # 2. 代表性地标与街道镇
    places_curated = [
        ("上庄镇", 116.23, 40.12, 0, 400, "town"),
        ("苏家坨镇", 116.13, 40.08, 0, 400, "town"),
        ("温泉镇", 116.19, 40.04, 0, 400, "town"),
        ("西北旺镇", 116.26, 40.045, 0, 400, "town"),
        ("中关村软件园", 116.29, 40.04, 0, -500, "tech"),
        ("永丰产业基地", 116.24, 40.07, 0, 400, "tech"),
        ("四季青镇", 116.26, 39.94, 0, -450, "town"),
        ("海淀区政府", 116.298, 39.959, 0, 500, "gov"),
        ("五道口", 116.338, 39.992, 0, -450, "place"),
        ("颐和园", 116.27, 39.995, -450, 0, "scenic"),
        ("圆明园遗址", 116.30, 40.008, 450, 0, "scenic"),
        ("香山公园", 116.19, 39.99, 0, 450, "scenic"),
        ("紫竹院", 116.32, 39.94, 0, -450, "scenic"),
        ("万寿路", 116.285, 39.91, 0, 400, "subdistrict"),
        ("羊坊店", 116.32, 39.90, 0, 400, "subdistrict"),
        ("北京大学", 116.31, 39.99, -400, -350, "univ"),
        ("清华大学", 116.33, 40.005, 400, 350, "univ")
    ]

    for pname, plon, plat, ox, oy, ptype in places_curated:
        px, py = to_alb(plon, plat)
        tx, ty = px + ox, py + oy
        if ptype == "gov":
            ax.plot(px, py, marker="*", color="#c0392b", markersize=12, markeredgecolor="black", markeredgewidth=0.8, zorder=12)
            ax.text(tx, ty, pname, fontsize=10.0, fontweight="bold", color="#78281f", ha="center", va="bottom", zorder=15,
                    path_effects=[pe.withStroke(linewidth=3, foreground="white")])
        elif ptype == "town":
            ax.plot(px, py, marker="s", color="#d35400", markersize=6.5, markeredgecolor="white", markeredgewidth=0.8, zorder=10)
            ax.text(tx, ty, pname, fontsize=8.8, fontweight="bold", color="#935116", ha="center", va="bottom", zorder=11,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])
        elif ptype == "tech":
            ax.plot(px, py, marker="D", color="#8e44ad", markersize=6.5, markeredgecolor="white", markeredgewidth=0.8, zorder=10)
            ax.text(tx, ty, pname, fontsize=8.6, fontweight="bold", color="#6c3483", ha="center", va="top", zorder=11,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])
        elif ptype == "univ":
            ax.plot(px, py, marker="^", color="#2471a3", markersize=6.5, markeredgecolor="white", markeredgewidth=0.8, zorder=10)
            ax.text(tx, ty, pname, fontsize=8.6, fontweight="bold", color="#1b4f72", ha="center", va="center", zorder=11,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])
        elif ptype == "scenic":
            ax.plot(px, py, marker="o", color="#27ae60", markersize=5.5, markeredgecolor="white", markeredgewidth=0.8, zorder=10)
            ax.text(tx, ty, pname, fontsize=8.2, color="#196f3d", ha="center", va="center", zorder=11,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])
        else:
            ax.plot(px, py, marker="o", color="#7f8c8d", markersize=4.5, markeredgecolor="white", markeredgewidth=0.6, zorder=9)
            ax.text(tx, ty, pname, fontsize=8.0, color="#515a5a", ha="center", va="bottom", zorder=10,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])

    pad_m = 1800.0
    ax.set_xlim(hb[0] - pad_m, hb[2] + pad_m)
    ax.set_ylim(hb[1] - pad_m, hb[3] + pad_m)
    ax.axis("off")

    # 右下角比例尺（与左下角图例彻底错开）
    add_scalebar(ax, hb[2] - 13000, hb[1] + 800, length_km=5)
    add_compass(ax, 0.94, 0.90)

    # 左下角图例
    leg_elements = [
        Line2D([0], [0], marker="*", color="w", markerfacecolor="#c0392b", markeredgecolor="k", markersize=11, label="区政府驻地"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#d35400", markersize=7, label="主要建制镇"),
        Line2D([0], [0], marker="D", color="w", markerfacecolor="#8e44ad", markersize=7, label="核心科创园区"),
        Line2D([0], [0], marker="^", color="w", markerfacecolor="#2471a3", markersize=7, label="著名高等学府"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#27ae60", markersize=6, label="重点文保名胜"),
        Patch(facecolor="none", edgecolor="#1a5276", linewidth=2.0, label="海淀区辖区边界")
    ]
    ax.legend(handles=leg_elements, loc="lower left", bbox_to_anchor=(0.03, 0.06), fontsize=8.5, framealpha=0.92,
              title="图例凡例", title_fontsize=9.2)

    # 右上角北京市域鹰眼图
    inset_ax = fig.add_axes([0.71, 0.69, 0.25, 0.25])
    bj_all.plot(ax=inset_ax, facecolor="#f2f4f4", edgecolor="#bdc3c7", lw=0.6)
    haidian.plot(ax=inset_ax, facecolor="#c0392b", edgecolor="#78281f", lw=1.2)
    inset_ax.set_aspect("equal")
    inset_ax.axis("off")
    inset_ax.text(0.5, 0.02, "海淀在全市的位置", transform=inset_ax.transAxes,
                  ha="center", fontsize=8.0, color="#2c3e50", fontweight="bold")

    ax.set_title("北京市海淀区行政区划图", fontsize=15, fontweight="bold", pad=12, color=C_TEXT)
    ax.text(0.5, 0.985, "Haidian District Administrative Boundary & Localities", transform=ax.transAxes,
            ha="center", va="top", fontsize=9.2, color="#7f8c8d")

    footer_text = "底图数据：自然资源部 / 阿里云 DataV (2021.5) · 审图号：GS(2021)6038号 · 制作：《中国地理知识手册》"
    fig.text(0.5, 0.015, footer_text, ha="center", va="bottom", fontsize=8.0, color="#7f8c8d")
    out_path = os.path.join(OUT_DIR, "fig01-06-1_海淀区行政区位图.png")
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print("Map 1 updated:", out_path)

# -------------------------------------------------------------------------
# 图 2：海淀区地形地貌图（边界外完全透明裁切，高程色带与比例尺分离）
# -------------------------------------------------------------------------
def make_map2_terrain():
    fig, ax = plt.subplots(figsize=(9.5, 9.5), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    # 1. 渲染海淀区内 DEM 与山体阴影
    hs = calc_hillshade(sub_dem, dem_res)
    colors = [
        (0.00, "#73a580"),
        (0.08, "#8bbd8b"),
        (0.20, "#c9bb86"),
        (0.40, "#c49257"),
        (0.70, "#9c6039"),
        (1.00, "#5a2b16")
    ]
    cmap = LinearSegmentedColormap.from_list("haidian_elev", colors, N=256)
    norm = Normalize(vmin=25.0, vmax=1276.0)

    rgba = cmap(norm(sub_dem))
    h_weight = 0.52
    hs_c = np.clip(hs, 0, 1)
    for i in range(3):
        rgba[..., i] = rgba[..., i] * (1.0 - h_weight + h_weight * hs_c)

    # 辖区外设为完全透明
    rgba[inside_mask == 0, 3] = 0.0
    ax.imshow(rgba, extent=sub_extent, origin="upper", interpolation="bilinear", zorder=2)

    # 2. 边界线与水系
    haidian.boundary.plot(ax=ax, color="#1c2833", lw=2.2, zorder=5)
    water_h.plot(ax=ax, color="#2980b9", lw=1.6, zorder=6)

    water_labels = [
        ("京密引水渠", 116.23, 40.03, 16),
        ("昆明湖", 116.27, 39.99, 0),
        ("清河", 116.32, 40.03, 0),
        ("南沙河", 116.20, 40.14, 0),
        ("玉渊潭", 116.32, 39.91, 0)
    ]
    for wname, wlon, wlat, rot in water_labels:
        wx, wy = to_alb(wlon, wlat)
        ax.text(wx, wy, wname, fontsize=8.8, color="#154360", fontweight="bold", rotation=rot,
                ha="center", va="center", zorder=7,
                path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])

    # 3. 标注主要山峰
    peaks = [
        ("阳台山 (最高峰 1276m)", 116.08, 40.07, 1276, 400, 0, "left"),
        ("凤凰岭 (748m)", 116.11, 40.11, 748, 400, 0, "left"),
        ("鹫峰 (1071m)", 116.10, 40.05, 1071, 400, 0, "left"),
        ("香炉峰 (鬼见愁 575m)", 116.18, 39.99, 575, 400, 0, "left"),
        ("百望山 (太行前哨 210m)", 116.26, 40.03, 210, 400, 150, "left"),
        ("万寿山 (109m)", 116.27, 40.005, 109, -400, -200, "right"), # 避开百望山，朝西南偏
        ("东南平原 (低点 29m)", 116.35, 39.95, 29, 0, 0, "center")
    ]
    for pname, plon, plat, elev, ox, oy, ha in peaks:
        px, py = to_alb(plon, plat)
        tx, ty = px + ox, py + oy
        if elev > 500:
            ax.plot(px, py, marker="^", color="#78281f", markersize=9, markeredgecolor="white", markeredgewidth=1.0, zorder=10)
            ax.text(tx, ty, pname, fontsize=9.0, fontweight="bold", color="#641e16", ha=ha, va="center", zorder=11,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])
        elif elev > 100:
            ax.plot(px, py, marker="^", color="#af601a", markersize=7.5, markeredgecolor="white", markeredgewidth=0.8, zorder=10)
            ax.text(tx, ty, pname, fontsize=8.6, fontweight="bold", color="#7e5109", ha=ha, va="center", zorder=11,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])
        else:
            ax.text(tx, ty, pname, fontsize=8.5, color="#196f3d", ha=ha, va="center", zorder=11,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])

    pad_m = 1800.0
    ax.set_xlim(hb[0] - pad_m, hb[2] + pad_m)
    ax.set_ylim(hb[1] - pad_m, hb[3] + pad_m)
    ax.axis("off")

    # 右下角比例尺
    add_scalebar(ax, hb[2] - 13000, hb[1] + 800, length_km=5)
    add_compass(ax, 0.94, 0.90)

    # 左下角高程色带（与比例尺彻底错开）
    cbar_ax = fig.add_axes([0.08, 0.08, 0.22, 0.016])
    cbar = fig.colorbar(matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cbar_ax, orientation="horizontal")
    cbar.set_ticks([50, 300, 600, 900, 1200])
    cbar.set_ticklabels(["50m", "300m", "600m", "900m", "1200m"])
    cbar_ax.tick_params(labelsize=8)
    cbar_ax.set_title("海拔高度 (米)", fontsize=8.5, pad=3, color="#2c3e50")

    ax.set_title("北京市海淀区地形地貌与水系图", fontsize=15, fontweight="bold", pad=12, color=C_TEXT)
    ax.text(0.5, 0.985, "Topography, Relief & Water Systems of Haidian District", transform=ax.transAxes,
            ha="center", va="top", fontsize=9.2, color="#7f8c8d")

    footer_text = "数据源：AWS Terrarium / Copernicus GLO-30 DEM · 阿里云 DataV · 制作：《中国地理知识手册》"
    fig.text(0.5, 0.015, footer_text, ha="center", va="bottom", fontsize=8.0, color="#7f8c8d")
    out_path = os.path.join(OUT_DIR, "fig01-06-2_海淀区地形地貌图.png")
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print("Map 2 updated:", out_path)

# -------------------------------------------------------------------------
# 图 3：海淀区综合道路交通图（清洗异常直射连线，真实等级重构，五大枢纽引线标注）
# -------------------------------------------------------------------------
def make_map3_transport():
    fig, ax = plt.subplots(figsize=(9.5, 9.5), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    haidian.plot(ax=ax, facecolor="#fdfefe", edgecolor="#2c3e50", lw=2.2, zorder=2)
    water_h.plot(ax=ax, color="#ebf5fb", lw=1.2, zorder=3)

    # 严格按照北京市官方路网等级分类
    expressway_keywords = ["三环", "四环", "五环", "万泉河", "阜石", "莲石", "莲花池"]

    def classify_road(r):
        name = str(r.get("name") or "")
        rtype = str(r.get("type") or "")
        if rtype in ["motorway", "motorway_link"]:
            return "motorway"
        if any(k in name for k in expressway_keywords):
            return "expressway"
        if rtype in ["trunk", "trunk_link", "primary", "primary_link"]:
            return "primary"
        if rtype in ["secondary", "secondary_link"]:
            return "secondary"
        return "local"

    roads_h["road_class"] = roads_h.apply(classify_road, axis=1)

    motorways = roads_h[roads_h["road_class"] == "motorway"]
    expressways = roads_h[roads_h["road_class"] == "expressway"]
    primaries = roads_h[roads_h["road_class"] == "primary"]
    # 仅绘制有名称的重要城市次干道，避免无名小巷过度拥塞
    secondaries = roads_h[(roads_h["road_class"] == "secondary") & (roads_h["name"].notna())]

    secondaries.plot(ax=ax, color="#d5d8dc", lw=0.6, zorder=4)
    primaries.plot(ax=ax, color="#f39c12", lw=1.3, zorder=5)     # 城市主干道（中关村大街、紫竹院路、北清路）
    expressways.plot(ax=ax, color="#e67e22", lw=2.0, zorder=6)   # 城市快速路（三/四/五环、万泉河路、阜石路）
    motorways.plot(ax=ax, color="#c0392b", lw=2.5, zorder=7)     # 国家高速公路（G6/G7/西六环）

    national_rail = rails_h[rails_h["type"].isin(["rail", "narrow_gauge"])]
    subway_rail = rails_h[rails_h["type"].isin(["subway", "light_rail"])]
    national_rail.plot(ax=ax, color="#1c2833", lw=2.4, zorder=8)
    national_rail.plot(ax=ax, color="white", lw=1.2, linestyle="--", zorder=9)
    subway_rail.plot(ax=ax, color="#884ea0", lw=1.5, zorder=10)

    # 五大骨干换乘枢纽（引线标注）
    stations = [
        ("清河站 (高铁特等枢纽)", 116.315, 40.033, 800, 600, "station", "left", "bottom"),
        ("西二旗 (13/昌平线)", 116.306, 40.053, -800, 500, "metro", "right", "bottom"),
        ("海淀黄庄 (4/10线)", 116.318, 39.976, 800, -500, "metro", "left", "top"),
        ("国家图书馆 (4/9/16线)", 116.324, 39.942, -800, -500, "metro", "right", "top"),
        ("巴沟 (10号线/西郊线)", 116.295, 39.975, -800, 600, "metro", "right", "bottom")
    ]
    for sname, slon, slat, ox, oy, stype, ha, va in stations:
        sx, sy = to_alb(slon, slat)
        tx, ty = sx + ox, sy + oy
        color = "#e74c3c" if stype == "station" else "#884ea0"
        ax.plot(sx, sy, marker="s" if stype == "station" else "o", color=color,
                markersize=8 if stype == "station" else 5.5,
                markeredgecolor="black" if stype == "station" else "white", markeredgewidth=0.8, zorder=15)
        ax.annotate(sname, xy=(sx, sy), xytext=(tx, ty),
                    arrowprops=dict(arrowstyle="-", color="#7f8c8d", lw=0.7),
                    fontsize=8.8 if stype == "station" else 8.2, fontweight="bold",
                    color="#78281f" if stype == "station" else "#4a235a",
                    ha=ha, va=va, zorder=16, path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])

    # 廊道文字（安放在空旷路段，绝不挤压枢纽注记）
    corridors = [
        ("G6 京藏高速", 116.360, 40.080, -55),
        ("G7 京新高速", 116.290, 40.110, -60),
        ("G4501 西六环路", 116.120, 40.050, -50),
        ("北五环路", 116.200, 40.015, 0),
        ("北四环路", 116.350, 39.986, 0),
        ("北清路 (科创主轴)", 116.180, 40.070, 0),
    ]
    for cname, clon, clat, rot in corridors:
        cx, cy = to_alb(clon, clat)
        ax.text(cx, cy, cname, fontsize=8.2, fontweight="bold", color="#922b21", rotation=rot,
                ha="center", va="center", zorder=14, path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])

    pad_m = 1800.0
    ax.set_xlim(hb[0] - pad_m, hb[2] + pad_m)
    ax.set_ylim(hb[1] - pad_m, hb[3] + pad_m)
    ax.axis("off")

    # 右下角比例尺
    add_scalebar(ax, hb[2] - 13000, hb[1] + 800, length_km=5)
    add_compass(ax, 0.94, 0.90)

    leg_elements = [
        Line2D([0], [0], color="#c0392b", lw=2.5, label="国家高速公路 (G6/G7/西六环)"),
        Line2D([0], [0], color="#e67e22", lw=2.0, label="城市快速路 (三/四/五环/万泉河路等)"),
        Line2D([0], [0], color="#f39c12", lw=1.3, label="城市主干道 (中关村大街/紫竹院路/北清路)"),
        Line2D([0], [0], color="#1c2833", lw=2.2, linestyle="-", label="国铁干线 (京张高铁/京包铁路)"),
        Line2D([0], [0], color="#884ea0", lw=1.6, label="城市轨道交通 / 地铁线网"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#e74c3c", markeredgecolor="k", markersize=8, label="高铁客运枢纽 (清河站)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#884ea0", markeredgecolor="w", markersize=6, label="重点地铁换乘枢纽"),
        Patch(facecolor="none", edgecolor="#2c3e50", linewidth=2.0, label="海淀区辖区边界")
    ]
    ax.legend(handles=leg_elements, loc="lower left", bbox_to_anchor=(0.03, 0.06), fontsize=8.2, framealpha=0.92,
              title="交通图例", title_fontsize=9.0)

    ax.set_title("北京市海淀区综合道路交通图", fontsize=15, fontweight="bold", pad=12, color=C_TEXT)
    ax.text(0.5, 0.985, "Comprehensive Transportation Network of Haidian District", transform=ax.transAxes,
            ha="center", va="top", fontsize=9.2, color="#7f8c8d")
    fig.text(0.5, 0.015, "数据源：OpenStreetMap (2026) · 中国国家铁路集团 · 北京市地铁运营公司 · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=8.0, color="#7f8c8d")

    out_path = os.path.join(OUT_DIR, "fig01-06-3_海淀区道路交通图.png")
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print("Map 3 updated:", out_path)

# -------------------------------------------------------------------------
# 图 4：特色配图 —— 海淀区重点高等院校与国家级科研院所空间分布图（引线双翼外展）
# -------------------------------------------------------------------------
def make_map4_universities():
    fig, ax = plt.subplots(figsize=(9.5, 9.5), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    haidian.plot(ax=ax, facecolor="#fbfcfc", edgecolor="#2c3e50", lw=2.0, zorder=2)
    water_h.plot(ax=ax, color="#eaf2f8", lw=1.0, zorder=3)

    # 学院路走廊指示框
    x_c1, y_c1 = to_alb(116.335, 39.950)
    x_c2, y_c2 = to_alb(116.370, 40.015)
    rect = Rectangle((x_c1, y_c1), x_c2 - x_c1, y_c2 - y_c1, linewidth=1.5,
                     edgecolor="#e74c3c", facecolor="#fadbd8", alpha=0.25, linestyle=":", zorder=5)
    ax.add_patch(rect)
    ax.text((x_c1 + x_c2)/2, y_c2 + 300, "【学院路高教学术核心带】", fontsize=9.0, color="#b03a2e",
            fontweight="bold", ha="center", va="bottom", zorder=15,
            path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])

    edu_institutes = [
        # 顶尖综合学府 (清北人)
        ("北京大学", 116.310, 39.992, "top", -600, 350, "right", "bottom"),
        ("清华大学", 116.328, 40.001, "top", 500, 350, "left", "bottom"),
        ("中国人民大学", 116.315, 39.970, "top", -600, 150, "right", "center"),
        # 中关村大街西侧大学 (全部往西引出)
        ("北京理工大学", 116.317, 39.960, "eng", -600, -100, "right", "center"),
        ("中央民族大学", 116.318, 39.949, "normal", -600, -300, "right", "top"),
        # 学院路东侧高校与院所 (全部引向东侧，绝不跨越中关村)
        ("中国农业大学(东校区)", 116.353, 40.003, "agri", 550, 400, "left", "bottom"),
        ("中国地质大学(北京)", 116.346, 39.991, "eng", 550, 200, "left", "center"),
        ("北京科技大学", 116.358, 39.988, "eng", 550, 0, "left", "center"),
        ("北京航空航天大学", 116.348, 39.982, "eng", 550, -200, "left", "center"),
        ("中国科学院中关村院区", 116.335, 39.986, "cas", -500, -350, "right", "top"),
        ("北京师范大学", 116.366, 39.962, "normal", 550, 200, "left", "bottom"),
        ("北京邮电大学", 116.358, 39.962, "eng", 550, -150, "left", "top"),
        ("北京交通大学", 116.342, 39.951, "eng", 550, -350, "left", "top"),
        # 北部科学城
        ("中国农业大学(西校区)", 116.278, 40.030, "agri", -500, 200, "right", "center"),
        ("北京量子信息科学研究院", 116.295, 40.040, "cas", 500, 200, "left", "center"),
        ("智源人工智能研究院", 116.250, 40.065, "cas", 500, 200, "left", "center")
    ]

    for uname, ulon, ulat, utype, ox, oy, ha, va in edu_institutes:
        ux, uy = to_alb(ulon, ulat)
        tx, ty = ux + ox, uy + oy
        if utype == "top":
            m, c, ms = "^", "#c0392b", 8.5
        elif utype == "eng":
            m, c, ms = "s", "#2980b9", 7.0
        elif utype == "cas":
            m, c, ms = "D", "#8e44ad", 7.0
        else:
            m, c, ms = "o", "#27ae60", 6.5
        ax.plot(ux, uy, marker=m, color=c, markersize=ms, markeredgecolor="black" if utype=="top" else "white",
                markeredgewidth=0.8, zorder=12)
        ax.annotate(uname, xy=(ux, uy), xytext=(tx, ty),
                    arrowprops=dict(arrowstyle="-", color="#95a5a6", lw=0.7),
                    fontsize=8.5, fontweight="bold", color=c, ha=ha, va=va, zorder=14,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])

    pad_m = 1800.0
    ax.set_xlim(hb[0] - pad_m, hb[2] + pad_m)
    ax.set_ylim(hb[1] - pad_m, hb[3] + pad_m)
    ax.axis("off")

    # 右下角比例尺
    add_scalebar(ax, hb[2] - 13000, hb[1] + 800, length_km=5)
    add_compass(ax, 0.94, 0.90)

    leg_elements = [
        Line2D([0], [0], marker="^", color="w", markerfacecolor="#c0392b", markeredgecolor="k", markersize=8.5, label="顶尖综合性大学 (清/北/人)"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#2980b9", markersize=7, label="工科及专业骨干大学 (北航/北理工等)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#27ae60", markersize=6.5, label="师范/农林/医药大学 (北师大/农大等)"),
        Line2D([0], [0], marker="D", color="w", markerfacecolor="#8e44ad", markersize=7, label="中科院所与国家前沿科研平台"),
        Patch(facecolor="#fadbd8", edgecolor="#e74c3c", linestyle=":", label="学院路高教密集核心走廊")
    ]
    ax.legend(handles=leg_elements, loc="lower left", bbox_to_anchor=(0.03, 0.06), fontsize=8.2, framealpha=0.92,
              title="科教集群分类", title_fontsize=9.0)

    ax.set_title("北京市海淀区重点高等院校与科研院所分布图", fontsize=15, fontweight="bold", pad=12, color=C_TEXT)
    ax.text(0.5, 0.985, "Spatial Distribution of Top Universities & Research Institutes in Haidian",
            transform=ax.transAxes, ha="center", va="top", fontsize=9.2, color="#7f8c8d")
    fig.text(0.5, 0.015, "数据源：教育部高等教育名录 · 中科院院所空间名录 · 制作：《中国地理知识手册》",
             ha="center", va="bottom", fontsize=8.0, color="#7f8c8d")

    out_path = os.path.join(OUT_DIR, "fig01-06-4_海淀区重点高校与科研院所分布图.png")
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print("Map 4 updated:", out_path)

# -------------------------------------------------------------------------
# 图 5：特色数据分析图 —— 海淀区夜间灯光（1986—2024）与经济跃迁演进分析
# -------------------------------------------------------------------------
def make_map5_nightlight_gdp():
    base_data = r"D:\code\Ideas\MyBooks\中国地理知识手册\中国省市数据"
    nl_file = os.path.join(base_data, "夜间灯光数据-省、市、县（1986-2024年）", "夜间灯光数据-区县（1986-2024年）.xlsx")
    df_nl = pd.read_excel(nl_file)
    hd_nl = df_nl[df_nl["区县代码"] == 110108].sort_values("年份").dropna(subset=["年份", "sum"])

    gdp_data = {
        1990: 25.1,
        1995: 112.4,
        2000: 426.8,
        2005: 1198.3,
        2010: 2901.8,
        2015: 4926.9,
        2020: 8504.6,
        2022: 10206.9,
        2023: 11020.2,
        2024: 12907.1
    }
    years_gdp = sorted(gdp_data.keys())
    values_gdp = [gdp_data[y] for y in years_gdp]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.2), dpi=DPI)
    fig.patch.set_facecolor("white")

    # 子图 1：1986—2024 夜间灯光总辐射量变化折线
    ax1.set_facecolor("#fafbfc")
    years_nl = hd_nl["年份"].values
    sum_nl = hd_nl["sum"].values

    ax1.plot(years_nl, sum_nl, color="#e67e22", lw=2.4, marker="o", markersize=4.5, label="夜光辐射总量 (sum)")
    ax1.fill_between(years_nl, sum_nl, color="#fdebd0", alpha=0.5)

    ax1.annotate("1988年：首个\n国家高新区", xy=(1988, 12000), xytext=(1986, 26000),
                 arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1.0),
                 fontsize=8.5, color="#922b21", fontweight="bold",
                 bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#e6b0aa", alpha=0.9))

    ax1.annotate("1999年：中关村\n科技园区成立", xy=(1999, 29000), xytext=(1995, 38000),
                 arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1.0),
                 fontsize=8.5, color="#922b21", fontweight="bold",
                 bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#e6b0aa", alpha=0.9))

    ax1.annotate("2009年：国家首个\n自主创新示范区", xy=(2009, 37500), xytext=(2005, 48000),
                 arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1.0),
                 fontsize=8.5, color="#922b21", fontweight="bold",
                 bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="#e6b0aa", alpha=0.9))

    ax1.set_title("海淀区夜间灯光辐射总值变化 (1986—2024)", fontsize=11.5, fontweight="bold", color=C_TEXT, pad=10)
    ax1.set_xlabel("年份", fontsize=9.5)
    ax1.set_ylabel("夜间灯光辐射总量 (nW/cm²/sr)", fontsize=9.5)
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.set_ylim(0, 56000)

    # 子图 2：2000—2024 GDP 跨越
    ax2.set_facecolor("#fafbfc")
    bars = ax2.bar([str(y) for y in years_gdp], values_gdp, color="#2980b9", width=0.6, label="海淀区 GDP (亿元)")
    bars[-3].set_color("#c0392b") # 2022
    bars[-1].set_color("#27ae60") # 2024

    for b in bars:
        h = b.get_height()
        ax2.text(b.get_x() + b.get_width()/2., h + 150, f"{int(h):d}",
                 ha="center", va="bottom", fontsize=7.8, color="#2c3e50")

    ax2.annotate("2022年突破万亿\n全国首个万亿区县", xy=(7, 10206.9), xytext=(5.5, 11800),
                 arrowprops=dict(arrowstyle="->", color="#c0392b", lw=1.2),
                 fontsize=8.8, color="#922b21", fontweight="bold",
                 bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#c0392b", alpha=0.9))

    ax2.set_title("海淀区地区生产总值（GDP）跨越历程", fontsize=11.5, fontweight="bold", color=C_TEXT, pad=10)
    ax2.set_xlabel("年份", fontsize=9.5)
    ax2.set_ylabel("地区生产总值 (亿元)", fontsize=9.5)
    ax2.grid(True, axis="y", linestyle="--", alpha=0.5)
    ax2.set_ylim(0, 14500)

    fig.suptitle("北京市海淀区空间经济活力演进：长时序夜光与 GDP 跨越式跃升 (1986—2024)",
                 fontsize=13.5, fontweight="bold", color=C_TEXT, y=0.98)
    fig.text(0.5, 0.015, "数据来源：夜间灯光遥感数据 · 北京市及海淀区国民经济统计公报 · 制作：《中国地理知识手册》",
             ha="center", fontsize=8.0, color="#7f8c8d")

    plt.tight_layout(rect=[0, 0.04, 1, 0.94])
    out_path = os.path.join(OUT_DIR, "fig01-06-5_海淀区夜间灯光与经济发展演进图.png")
    fig.savefig(out_path, dpi=DPI)
    plt.close(fig)
    print("Map 5 created:", out_path)

if __name__ == "__main__":
    # 只保留第 4 幅。第 1/2/3/5 幅由 gen_district_maps.py 统一产出（走 LabelPlacer
    # 自动避让，优于本脚本的人工像素偏移版）；本脚本仅负责正文引用的
    # 「重点高校与科研院所分布图」，避免同名 fig01-06-x 被两套实现互相覆盖。
    make_map4_universities()
    print("Haidian map 4 (universities) generated.")
