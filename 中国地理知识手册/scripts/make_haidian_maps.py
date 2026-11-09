# -*- coding: utf-8 -*-
"""绘制海淀区标准三图：
1. fig01-06-1_海淀区行政区位图.png
2. fig01-06-2_海淀区地形地貌图.png
3. fig01-06-3_海淀区道路交通图.png
"""
import os
import sys
import math
from concurrent.futures import ThreadPoolExecutor
from urllib.request import urlopen
from PIL import Image

import numpy as np
import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import FancyArrow, Rectangle, Patch
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap, Normalize
from rasterio.transform import from_origin
from rasterio.warp import reproject, Resampling
from rasterio.features import rasterize
from pyproj import Transformer
from shapely.geometry import box, Point, LineString

sys.path.insert(0, r"D:\code\Ideas\MyBooks\中国地理知识手册\scripts")
from style import ALBERS, C_TEXT, DATA, DPI, FIGURES, setup
from prov_pipeline import prov_dem

setup()
OUT_DIR = FIGURES
os.makedirs(OUT_DIR, exist_ok=True)
_T = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True)
_T_INV = Transformer.from_crs(ALBERS, "EPSG:4326", always_xy=True)

def to_alb(lon, lat):
    return _T.transform(lon, lat)

def to_wgs(x, y):
    return _T_INV.transform(x, y)

# -------------------------------------------------------------------------
# 数据载入与预处理
# -------------------------------------------------------------------------
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
bj_all = gpd.read_file(os.path.join(DATA_DIR, "boundaries", "datav", "110000_full.json")).to_crs(ALBERS)
haidian = bj_all[bj_all["name"] == "海淀区"]
h_geom = haidian.geometry.iloc[0]
hb = haidian.total_bounds

# 邻居区
neighbors = bj_all[bj_all["name"] != "海淀区"].copy()
neighbors["intersects"] = neighbors.geometry.intersects(h_geom.buffer(1000))
adj_districts = neighbors[neighbors["intersects"]]

# OSM 道路、水系、铁路
osm_dir = os.path.join(DATA_DIR, "transport", "beijing", "Beijing-shp", "shape")
h_bounds_wgs = haidian.to_crs("EPSG:4326").total_bounds
pad = 0.05
bbox_wgs = (h_bounds_wgs[0] - pad, h_bounds_wgs[1] - pad, h_bounds_wgs[2] + pad, h_bounds_wgs[3] + pad)

roads_osm = gpd.read_file(os.path.join(osm_dir, "roads.shp"), bbox=bbox_wgs).to_crs(ALBERS)
rails_osm = gpd.read_file(os.path.join(osm_dir, "railways.shp"), bbox=bbox_wgs).to_crs(ALBERS)
water_osm = gpd.read_file(os.path.join(osm_dir, "waterways.shp"), bbox=bbox_wgs).to_crs(ALBERS)
natural_osm = gpd.read_file(os.path.join(osm_dir, "natural.shp"), bbox=bbox_wgs).to_crs(ALBERS)

# DEM 数据
dem_bj, dem_minx, dem_maxy, dem_res = prov_dem("110000", zoom=9, res=300.0)

# 海淀区在 DEM 中的裁剪范围
hb = haidian.total_bounds
dx_pad, dy_pad = 4000.0, 4000.0
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

def calc_hillshade(dem, res, az=315.0, alt=45.0):
    az_rad = np.radians(az)
    alt_rad = np.radians(alt)
    gy, gx = np.gradient(dem, res)
    slope = np.arctan(np.sqrt(gx * gx + gy * gy))
    aspect = np.arctan2(-gx, gy)
    shaded = np.sin(alt_rad) * np.cos(slope) + np.cos(alt_rad) * np.sin(slope) * np.cos(az_rad - aspect)
    return np.clip(shaded, 0.0, 1.0)
def add_scalebar(ax, x0, y0, length_km=5, label=None):
    """在地图上绘制精美比例尺（Albers投影单位为米）"""
    length_m = length_km * 1000.0
    h = (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.012
    # 黑白分段
    half_m = length_m / 2.0
    ax.add_patch(Rectangle((x0, y0), half_m, h, facecolor="#2c3e50", edgecolor="#2c3e50", zorder=25))
    ax.add_patch(Rectangle((x0 + half_m, y0), half_m, h, facecolor="white", edgecolor="#2c3e50", lw=0.8, zorder=25))
    ax.text(x0, y0 - h * 1.5, "0", ha="center", va="top", fontsize=8.5, color="#2c3e50", zorder=25)
    ax.text(x0 + half_m, y0 - h * 1.5, f"{length_km/2:g}", ha="center", va="top", fontsize=8.5, color="#2c3e50", zorder=25)
    lbl = f"{length_km} km" if label is None else label
    ax.text(x0 + length_m, y0 - h * 1.5, lbl, ha="center", va="top", fontsize=8.5, color="#2c3e50", zorder=25)

def add_compass(ax, x, y, size_ratio=0.06):
    """轴坐标系指北针"""
    trans = ax.transAxes
    s = size_ratio
    ax.add_patch(FancyArrow(x, y - s*0.4, 0, s*0.8, width=0.003, head_width=s*0.35, head_length=s*0.45,
                            fc="#c0392b", ec="#2c3e50", lw=0.8, transform=trans, zorder=25))
    ax.text(x, y + s*0.5, "N", transform=trans, ha="center", va="bottom",
            fontsize=12, fontweight="bold", color="#2c3e50", zorder=25)

# -------------------------------------------------------------------------
# 图 1：海淀区行政区位与区划图
# -------------------------------------------------------------------------
def make_map1_admin():
    fig, ax = plt.subplots(figsize=(10, 10), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#fcfbfa")

    # 1. 邻近区底色与边界
    adj_districts.plot(ax=ax, facecolor="#f5f5f3", edgecolor="#bdc3c7", lw=1.0, linestyle="--", zorder=2)
    # 标注邻近区名称
    adj_labels = {
        "昌平区": (116.24, 40.17),
        "朝阳区": (116.39, 40.02),
        "西城区": (116.36, 39.92),
        "丰台区": (116.29, 39.87),
        "石景山区": (116.16, 39.92),
        "门头沟区": (116.03, 39.98)
    }
    for name, (lon, lat) in adj_labels.items():
        gx, gy = to_alb(lon, lat)
        ax.text(gx, gy, f"【{name}】", fontsize=11, fontweight="bold", color="#7f8c8d",
                ha="center", va="center", zorder=3,
                path_effects=[pe.withStroke(linewidth=3, foreground="white")])

    # 2. 海淀区主体
    haidian.plot(ax=ax, facecolor="#eef6fb", edgecolor="#2980b9", lw=2.5, zorder=4)

    # 3. 自然水系（水面与主干渠）作为地理骨架
    h_clip_water = water_osm[water_osm.intersects(h_geom.buffer(1000))]
    h_clip_water.plot(ax=ax, color="#7fb3d5", lw=1.2, zorder=5)

    # 4. 主要街道、镇及重点地标点位
    places_data = [
        # 北部生态农业与科创组团 (镇)
        ("苏家坨镇", 116.13, 40.08, "town"),
        ("温泉镇", 116.19, 40.04, "town"),
        ("上庄镇", 116.23, 40.12, "town"),
        ("西北旺镇", 116.26, 40.04, "town"),
        ("四季青镇", 116.24, 39.96, "town"),
        # 中部科创极核
        ("永丰产业基地", 116.24, 40.07, "tech"),
        ("中关村软件园", 116.29, 40.04, "tech"),
        ("上地", 116.31, 40.03, "subdistrict"),
        ("清华大学", 116.33, 40.00, "edu"),
        ("北京大学", 116.31, 39.99, "edu"),
        ("五道口", 116.34, 39.99, "landmark"),
        ("学院路", 116.35, 39.98, "subdistrict"),
        # 南部核心城区与历史名胜
        ("海淀街道 (区政府)", 116.30, 39.96, "gov"),
        ("中关村街道", 116.32, 39.97, "subdistrict"),
        ("紫竹院街道", 116.31, 39.94, "subdistrict"),
        ("万寿路街道", 116.28, 39.91, "subdistrict"),
        ("羊坊店街道", 116.32, 39.90, "subdistrict"),
        ("田村路街道", 116.24, 39.93, "subdistrict"),
        ("香山公园", 116.19, 39.99, "scenic"),
        ("国家植物园", 116.21, 40.00, "scenic"),
        ("颐和园", 116.27, 40.00, "scenic"),
        ("圆明园遗址公园", 116.30, 40.01, "scenic"),
        ("玉渊潭公园", 116.32, 39.91, "scenic")
    ]

    for name, lon, lat, ptype in places_data:
        gx, gy = to_alb(lon, lat)
        if ptype == "gov":
            ax.plot(gx, gy, marker="*", color="#c0392b", markersize=14, markeredgecolor="black", markeredgewidth=0.8, zorder=12)
            ax.text(gx, gy + 500, name, fontsize=10.5, fontweight="bold", color="#962d22", ha="center", va="bottom", zorder=13,
                    path_effects=[pe.withStroke(linewidth=3, foreground="white")])
        elif ptype == "town":
            ax.plot(gx, gy, marker="s", color="#e67e22", markersize=7, markeredgecolor="white", markeredgewidth=0.8, zorder=10)
            ax.text(gx, gy + 450, name, fontsize=9.5, fontweight="bold", color="#b95c00", ha="center", va="bottom", zorder=11,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])
        elif ptype == "tech":
            ax.plot(gx, gy, marker="D", color="#8e44ad", markersize=7, markeredgecolor="white", markeredgewidth=0.8, zorder=10)
            ax.text(gx, gy + 450, name, fontsize=9.0, fontweight="bold", color="#6c3483", ha="center", va="bottom", zorder=11,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])
        elif ptype == "scenic":
            ax.plot(gx, gy, marker="o", color="#27ae60", markersize=6, markeredgecolor="white", markeredgewidth=0.8, zorder=10)
            ax.text(gx, gy - 400, name, fontsize=8.8, color="#196f3d", ha="center", va="top", zorder=11,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])
        elif ptype == "edu":
            ax.plot(gx, gy, marker="^", color="#2980b9", markersize=7, markeredgecolor="white", markeredgewidth=0.8, zorder=10)
            ax.text(gx + 400, gy, name, fontsize=9.0, fontweight="bold", color="#1f618d", ha="left", va="center", zorder=11,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])
        else:
            ax.plot(gx, gy, marker="o", color="#34495e", markersize=5, zorder=10)
            ax.text(gx, gy + 400, name, fontsize=8.5, color="#2c3e50", ha="center", va="bottom", zorder=11,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])

    # 范围控制
    pad_m = 3500.0
    ax.set_xlim(hb[0] - pad_m, hb[2] + pad_m)
    ax.set_ylim(hb[1] - pad_m, hb[3] + pad_m)

    # 标尺、指北针
    add_scalebar(ax, hb[0] - 1500, hb[1] - 1500, length_km=5)
    add_compass(ax, 0.94, 0.90)

    # 图例
    leg_elements = [
        Line2D([0], [0], marker="*", color="w", markerfacecolor="#c0392b", markeredgecolor="k", markersize=12, label="区政府驻地"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#e67e22", markersize=8, label="主要建制镇"),
        Line2D([0], [0], marker="D", color="w", markerfacecolor="#8e44ad", markersize=8, label="核心科创园区"),
        Line2D([0], [0], marker="^", color="w", markerfacecolor="#2980b9", markersize=8, label="著名高等学府"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#27ae60", markersize=7, label="重点名胜文保"),
        Patch(facecolor="#eef6fb", edgecolor="#2980b9", linewidth=2.0, label="海淀区辖区边界"),
        Patch(facecolor="#f5f5f3", edgecolor="#bdc3c7", linestyle="--", label="相邻区县边界")
    ]
    ax.legend(handles=leg_elements, loc="lower left", bbox_to_anchor=(0.02, 0.08), fontsize=8.5, framealpha=0.92,
              title="图例凡例", title_fontsize=9.5)

    # 标题与副标题
    ax.set_title("北京市海淀区行政区位与区划图", fontsize=15, fontweight="bold", pad=14, color=C_TEXT)
    ax.text(0.5, 0.985, "Haidian District Administrative & Location Map", transform=ax.transAxes,
            ha="center", va="top", fontsize=9.5, color="#7f8c8d")

    # 右上角北京市全域鹰眼缩略图
    ax_inset = fig.add_axes([0.69, 0.71, 0.26, 0.24])
    ax_inset.set_facecolor("#fcfcfc")
    bj_all.plot(ax=ax_inset, facecolor="#f0f3f4", edgecolor="#7f8c8d", lw=0.45)
    haidian.plot(ax=ax_inset, facecolor="#e74c3c", edgecolor="#922b21", lw=1.2)
    ax_inset.set_xticks([])
    ax_inset.set_yticks([])
    ax_inset.text(0.5, 0.05, "海淀在全市的位置", transform=ax_inset.transAxes, ha="center", fontsize=8.5,
                  fontweight="bold", color="#2c3e50", bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85))

    # 去坐标轴
    ax.set_xticks([])
    ax.set_yticks([])

    footer_text = "底图来源：国家地理信息公共服务平台 / 阿里云 DataV · 审图号：GS(2021)6038号(学习交流参考) · 制作：《中国地理知识手册》"
    fig.text(0.5, 0.015, footer_text, ha="center", va="bottom", fontsize=8.0, color="#7f8c8d")
    out_path = os.path.join(OUT_DIR, "fig01-06-1_海淀区行政区位图.png")
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print("Map 1 saved:", out_path)

# -------------------------------------------------------------------------
# 图 2：海淀区地形地貌与水系图
# -------------------------------------------------------------------------
def make_map2_terrain():
    fig, ax = plt.subplots(figsize=(10, 10), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#f4f6f7")

    # 1. 绘制 DEM 晕渲与分层设色
    # 自定义高程配色：从平原的柔和绿、黄绿，到台地浅黄，山地褐黄、青灰高山
    colors = [
        (0.00, "#a8d5ba"),  # 30m 平原淡绿
        (0.08, "#cce2cb"),  # 60m 倾斜平原
        (0.18, "#f2e394"),  # 120m 山前缓坡
        (0.35, "#e0b06b"),  # 300m 低山丘陵
        (0.55, "#b36b3b"),  # 600m 中低山（香山）
        (0.80, "#7d4223"),  # 950m 中山带
        (1.00, "#4a2d1d")   # 1276m 阳台山最高峰
    ]
    cmap = LinearSegmentedColormap.from_list("haidian_terrain", colors, N=256)

    # 计算山体阴影
    hs = calc_hillshade(sub_dem, dem_res)
    norm = Normalize(vmin=20, vmax=1250)
    rgba = cmap(norm(sub_dem))
    # 叠合阴影
    h_weight = 0.55
    hs_clipped = np.clip(hs, 0, 1)
    for i in range(3):
        rgba[..., i] = rgba[..., i] * (1.0 - h_weight + h_weight * hs_clipped)

    ax.imshow(rgba, extent=sub_extent, origin="upper", interpolation="bilinear", zorder=1)

    # 2. 海淀区外做半透明蒙版以突显海淀本区
    # 生成海淀内部 raster mask
    h_w = sub_dem.shape[1]
    h_h = sub_dem.shape[0]
    tf = from_origin(sub_minx, sub_maxy, dem_res, dem_res)
    inside = rasterize([(h_geom, 1)], out_shape=(h_h, h_w), transform=tf, fill=0, dtype="uint8")

    paper = np.ones((h_h, h_w, 4), dtype=np.float32)
    paper[..., :3] = [0.96, 0.95, 0.93]
    paper[..., 3] = np.where(inside == 1, 0.0, 0.65)  # 区外淡化65%
    ax.imshow(paper, extent=sub_extent, origin="upper", zorder=2)

    # 3. 边界线
    adj_districts.boundary.plot(ax=ax, color="#95a5a6", lw=0.9, linestyle="--", zorder=3)
    haidian.boundary.plot(ax=ax, color="#2c3e50", lw=2.2, zorder=4)

    # 4. 水系 (水体面与河渠线)
    h_water_clip = water_osm[water_osm.intersects(h_geom.buffer(1000))]
    h_water_clip.plot(ax=ax, color="#2980b9", lw=1.5, zorder=5)

    # 标注水系重要河道
    water_labels = [
        ("京密引水渠", 116.23, 40.03, 18),
        ("昆明湖", 116.27, 39.99, 0),
        ("清河", 116.32, 40.03, 0),
        ("南沙河", 116.20, 40.14, 0),
        ("玉渊潭", 116.32, 39.91, 0)
    ]
    for wname, wlon, wlat, rot in water_labels:
        wx, wy = to_alb(wlon, wlat)
        ax.text(wx, wy, wname, fontsize=9.0, color="#1a5276", fontweight="bold", rotation=rot,
                ha="center", va="center", zorder=6,
                path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])

    # 5. 标注名山与主要高程点
    peaks = [
        ("阳台山 (最高峰 1276m)", 116.08, 40.07, 1276),
        ("凤凰岭", 116.11, 40.11, 748),
        ("鹫峰", 116.10, 40.05, 1071),
        ("香炉峰 (鬼见愁 575m)", 116.18, 39.99, 575),
        ("百望山 (太行前哨 210m)", 116.26, 40.03, 210),
        ("万寿山 (颐和园 109m)", 116.27, 40.00, 109),
        ("东部倾斜平原 (约 35~50m)", 116.33, 39.96, 45)
    ]
    for pname, plon, plat, elev in peaks:
        px, py = to_alb(plon, plat)
        if elev > 500:
            ax.plot(px, py, marker="^", color="#900c3f", markersize=9, markeredgecolor="white", markeredgewidth=1.0, zorder=10)
            ax.text(px + 400, py, pname, fontsize=9.0, fontweight="bold", color="#78281f", ha="left", va="center", zorder=11,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])
        elif elev > 100:
            ax.plot(px, py, marker="^", color="#d35400", markersize=7, markeredgecolor="white", markeredgewidth=0.8, zorder=10)
            ax.text(px + 400, py, pname, fontsize=8.5, fontweight="bold", color="#935116", ha="left", va="center", zorder=11,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])
        else:
            ax.text(px, py, pname, fontsize=8.5, color="#1e8449", ha="center", va="center", zorder=11,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])

    # 范围
    pad_m = 3500.0
    ax.set_xlim(hb[0] - pad_m, hb[2] + pad_m)
    ax.set_ylim(hb[1] - pad_m, hb[3] + pad_m)

    # 标尺、指北针
    add_scalebar(ax, hb[0] - 1500, hb[1] - 1500, length_km=5)
    add_compass(ax, 0.94, 0.90)

    # 添加高程色带图例
    cbar_ax = fig.add_axes([0.08, 0.13, 0.24, 0.018])
    cbar = fig.colorbar(matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap),
                        cax=cbar_ax, orientation="horizontal")
    cbar.set_ticks([50, 300, 600, 900, 1200])
    cbar.set_ticklabels(["50m", "300m", "600m", "900m", "1200m"])
    cbar_ax.tick_params(labelsize=8)
    cbar_ax.set_title("高程图例 (海拔 / 米)", fontsize=8.5, pad=4, color="#2c3e50")

    # 标题与副标题
    ax.set_title("北京市海淀区地形地貌与水系图", fontsize=15, fontweight="bold", pad=14, color=C_TEXT)
    ax.text(0.5, 0.985, "Topography, Relief & Water Systems of Haidian District", transform=ax.transAxes,
            ha="center", va="top", fontsize=9.5, color="#7f8c8d")

    # 去坐标轴
    ax.set_xticks([])
    ax.set_yticks([])

    footer_text = "数据来源：AWS Terrain / Copernicus GLO-30 DEM · 阿里云 DataV · OpenStreetMap · 制作：《中国地理知识手册》"
    fig.text(0.5, 0.015, footer_text, ha="center", va="bottom", fontsize=8.0, color="#7f8c8d")
    out_path = os.path.join(OUT_DIR, "fig01-06-2_海淀区地形地貌图.png")
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print("Map 2 saved:", out_path)

# -------------------------------------------------------------------------
# 图 3：海淀区综合道路交通图
# -------------------------------------------------------------------------
def make_map3_transport():
    fig, ax = plt.subplots(figsize=(10, 10), dpi=DPI)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#fafbfc")

    # 1. 辖区底色与邻区背景
    adj_districts.plot(ax=ax, facecolor="#f5f7f8", edgecolor="#d5dbdb", lw=0.8, linestyle="--", zorder=1)
    haidian.plot(ax=ax, facecolor="#ffffff", edgecolor="#34495e", lw=1.8, zorder=2)

    # 2. 水系淡色打底
    h_clip_water = water_osm[water_osm.intersects(h_geom.buffer(1000))]
    h_clip_water.plot(ax=ax, color="#d4e6f1", lw=1.0, zorder=3)

    # 3. 道路分类渲染
    # 裁剪到海淀及周边
    roads_clip = roads_osm[roads_osm.intersects(h_geom.buffer(3000))]

    motorways = roads_clip[roads_clip["type"].isin(["motorway", "motorway_link"])]
    trunks = roads_clip[roads_clip["type"].isin(["trunk", "trunk_link"])]
    primaries = roads_clip[roads_clip["type"].isin(["primary", "primary_link"])]
    secondaries = roads_clip[roads_clip["type"].isin(["secondary", "secondary_link"])]

    # 次干道/主干道浅色绘制
    secondaries.plot(ax=ax, color="#d5d8dc", lw=0.8, zorder=4)
    primaries.plot(ax=ax, color="#f8c471", lw=1.4, zorder=5) # 城市主干道 (橙黄)
    trunks.plot(ax=ax, color="#e67e22", lw=2.0, zorder=6)    # 快速路 / 环线 (橙红)
    motorways.plot(ax=ax, color="#c0392b", lw=2.4, zorder=7) # 高速公路 (深红)

    # 4. 铁路与地铁网
    rails_clip = rails_osm[rails_osm.intersects(h_geom.buffer(3000))]
    national_rail = rails_clip[rails_clip["type"].isin(["rail", "narrow_gauge"])]
    subway_rail = rails_clip[rails_clip["type"].isin(["subway", "light_rail"])]

    # 国铁干线 (黑白虚线/复线感)
    national_rail.plot(ax=ax, color="#2c3e50", lw=2.2, zorder=8)
    national_rail.plot(ax=ax, color="white", lw=1.2, linestyle="--", zorder=9)

    # 地铁线网 (醒目深蓝/紫)
    subway_rail.plot(ax=ax, color="#8e44ad", lw=1.6, zorder=10)

    # 5. 核心交通枢纽与火车站
    stations = [
        ("清河站 (高铁特等枢纽)", 116.315, 40.033, "station"),
        ("国家图书馆 (换乘枢纽)", 116.324, 39.942, "metro_hub"),
        ("海淀黄庄 (4/10换乘)", 116.318, 39.976, "metro_hub"),
        ("西二旗 (13/昌平线换乘)", 116.306, 40.053, "metro_hub"),
        ("巴沟 (10号线/西郊线)", 116.295, 39.975, "metro_hub"),
        ("中关村站", 116.316, 39.984, "metro_hub"),
        ("五道口站", 116.338, 39.993, "metro_hub")
    ]
    for sname, slon, slat, stype in stations:
        sx, sy = to_alb(slon, slat)
        if stype == "station":
            ax.plot(sx, sy, marker="s", color="#e74c3c", markersize=9, markeredgecolor="black", markeredgewidth=1.0, zorder=15)
            ax.text(sx + 500, sy, sname, fontsize=9.5, fontweight="bold", color="#900c3f", ha="left", va="center", zorder=16,
                    path_effects=[pe.withStroke(linewidth=3, foreground="white")])
        else:
            ax.plot(sx, sy, marker="o", color="#8e44ad", markersize=6, markeredgecolor="white", markeredgewidth=0.8, zorder=15)
            ax.text(sx + 400, sy, sname, fontsize=8.5, color="#512e5f", ha="left", va="center", zorder=16,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])

    # 6. 主要交通廊道注记
    corridors = [
        ("京藏高速 (G6)", 116.36, 40.08, -55),
        ("京新高速 (G7)", 116.30, 40.09, -60),
        ("西六环路", 116.14, 40.09, -45),
        ("北五环路", 116.25, 40.015, 0),
        ("北四环西路", 116.31, 39.986, 0),
        ("西四环北路", 116.28, 39.95, 80),
        ("北三环西路", 116.33, 39.967, 0),
        ("北清路 (科创主轴)", 116.24, 40.07, 0),
        ("中关村大街", 116.316, 39.965, 85)
    ]
    for cname, clon, clat, rot in corridors:
        cx, cy = to_alb(clon, clat)
        ax.text(cx, cy, cname, fontsize=8.2, fontweight="bold", color="#a93226", rotation=rot,
                ha="center", va="center", zorder=14,
                path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])

    # 范围
    pad_m = 3500.0
    ax.set_xlim(hb[0] - pad_m, hb[2] + pad_m)
    ax.set_ylim(hb[1] - pad_m, hb[3] + pad_m)

    # 标尺、指北针
    add_scalebar(ax, hb[0] - 1500, hb[1] - 1500, length_km=5)
    add_compass(ax, 0.94, 0.90)

    # 图例
    leg_elements = [
        Line2D([0], [0], color="#c0392b", lw=3.0, label="国家高速公路 (G6/G7/六环)"),
        Line2D([0], [0], color="#e67e22", lw=2.5, label="城市快速路 (三/四/五环路)"),
        Line2D([0], [0], color="#f8c471", lw=2.0, label="城市主干道 (北清路/中关村大街)"),
        Line2D([0], [0], color="#2c3e50", lw=2.5, linestyle="-", label="国铁干线 (京张高铁/京包铁路)"),
        Line2D([0], [0], color="#8e44ad", lw=2.0, label="城市轨道交通 / 地铁线网"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#e74c3c", markeredgecolor="k", markersize=8, label="大型高铁客运站 (清河站)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#8e44ad", markeredgecolor="w", markersize=7, label="重点地铁换乘枢纽"),
        Patch(facecolor="none", edgecolor="#34495e", linewidth=1.8, label="海淀区辖区界线")
    ]
    ax.legend(handles=leg_elements, loc="lower left", bbox_to_anchor=(0.02, 0.08), fontsize=8.5, framealpha=0.92,
              title="交通图例", title_fontsize=9.5)

    # 标题与副标题
    ax.set_title("北京市海淀区综合道路交通图", fontsize=15, fontweight="bold", pad=14, color=C_TEXT)
    ax.text(0.5, 0.985, "Comprehensive Transportation Network of Haidian District", transform=ax.transAxes,
            ha="center", va="top", fontsize=9.5, color="#7f8c8d")

    # 去坐标轴
    ax.set_xticks([])
    ax.set_yticks([])

    footer_text = "数据来源：OpenStreetMap (2026) · 中国铁路与北京地铁运营网 · 制作：《中国地理知识手册》"
    fig.text(0.5, 0.015, footer_text, ha="center", va="bottom", fontsize=8.0, color="#7f8c8d")
    out_path = os.path.join(OUT_DIR, "fig01-06-3_海淀区道路交通图.png")
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print("Map 3 saved:", out_path)

if __name__ == "__main__":
    make_map1_admin()
    make_map2_terrain()
    make_map3_transport()
    print("All 3 Haidian maps successfully generated!")
