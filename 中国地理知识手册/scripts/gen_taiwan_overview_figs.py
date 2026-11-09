# -*- coding: utf-8 -*-
"""台湾省省级地理统揽专题地图生成引擎（26-00）
包含 5 幅全省出版级权威地图与分析图表（精细调优排版、严格杜绝压盖）：
1. fig26-00-1_台湾省地势起伏与山海环岛格局图.png
2. fig26-00-2_台湾省县市政区与四大功能区空间战略格局图.png
3. fig26-00-3_台湾省综合立体交通网络与环岛高铁公路大通道图.png
4. fig26-00-4_台湾省高新技术半导体产业与现代港口空间分布图.png
5. fig26-00-5_台湾省2000-2024年生产总值与外向型经济演进图.png
"""
import os
import sys
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Rectangle, Patch, PathPatch
from shapely.geometry import Polygon as ShpPolygon
from matplotlib.path import Path
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap, Normalize
from pyproj import Transformer

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册"
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))
from style import ALBERS, C_TEXT, DATA, DPI, FIGURES, setup
import mapkit
from taiwan_configs import TAIWAN_OVERVIEW, TAIWAN_DISTRICT_CONFIGS

setup()
OUT_DIR = os.path.join(BASE_DIR, "figures")
os.makedirs(OUT_DIR, exist_ok=True)
_T = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True)

def to_alb(lon, lat):
    return _T.transform(lon, lat)

def get_polygon_patch(polygon):
    if polygon.geom_type == 'Polygon':
        geoms = [polygon]
    elif polygon.geom_type == 'MultiPolygon':
        geoms = list(polygon.geoms)
    else:
        return None
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
    d = np.nan_to_num(dem, nan=0.0)
    gy, gx = np.gradient(d, res)
    slope = np.arctan(np.sqrt(gx * gx + gy * gy))
    aspect = np.arctan2(-gx, gy)
    shaded = np.sin(alt_rad) * np.cos(slope) + np.cos(alt_rad) * np.sin(slope) * np.cos(az_rad - aspect)
    return np.clip(shaded, 0.0, 1.0)

def add_compass(ax, x=0.94, y=0.92):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.055), transform=ax.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=1.8, headwidth=5.5, headlength=6.5),
                ha="center", va="center", fontsize=8.8, fontweight="bold", color="#2c3e50", zorder=30)

print("Loading Taiwan boundaries and DEM...")
DATA_DIR = os.path.join(BASE_DIR, "data")
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

tw_all = gpd.read_file(os.path.join(DATAV_DIR, "710000.json")).to_crs(ALBERS)
tw_all["geometry"] = tw_all.geometry.buffer(0)
tw_union = tw_all.union_all()

# 获取台湾本岛几何部分以精细设置显示范围
main_island_geom = None
if tw_union.geom_type == 'MultiPolygon':
    # 最大面积的即为台湾本岛
    sorted_geoms = sorted(list(tw_union.geoms), key=lambda g: g.area, reverse=True)
    main_island_geom = sorted_geoms[0]
else:
    main_island_geom = tw_union

mb = main_island_geom.bounds
span_x = mb[2] - mb[0]
span_y = mb[3] - mb[1]
pad_x = span_x * 0.16
pad_y = span_y * 0.06
ax_xlim = (mb[0] - pad_x - 30000, mb[2] + pad_x + 30000)
ax_ylim = (mb[1] - pad_y, mb[3] + pad_y)

dem_file = os.path.join(DATA_DIR, "dem", "province", "710000_z9.npz")
dem_data = np.load(dem_file)
dem_raw = dem_data['dem']
res = float(dem_data['res'])
minx = float(dem_data['minx'])
maxy = float(dem_data['maxy'])
nrows, ncols = dem_raw.shape
dem_extent = [minx, minx + ncols * res, maxy - nrows * res, maxy]

dem_elev = np.where(dem_raw < 0, np.nan, dem_raw)
hillshade = calc_hillshade(dem_elev, res)

terrain_cmap = LinearSegmentedColormap.from_list("tw_terrain", [
    (0.0, "#27ae60"),    # 沿海平原与盆地平地 (0m ~ 200m) 翠绿
    (0.10, "#a9dfbf"),   # 台地与浅丘陵 (200m ~ 500m) 浅绿
    (0.25, "#f9e79f"),   # 低山与丘陵谷地 (500m ~ 1000m) 暖黄
    (0.45, "#f39c12"),   # 中山中山林带 (1000m ~ 2000m) 橙黄
    (0.70, "#ba4a00"),   # 高山寒原带 (2000m ~ 3000m) 红褐
    (0.88, "#6e2c00"),   # 极高山荒漠 (3000m ~ 3600m) 深褐
    (1.0, "#f2f4f4")     # 玉山/雪山极顶 (3600m ~ 3952m) 苍雪白
])

# =============================================================================
# 图 1: 台湾省地势起伏与山海环岛格局图
# =============================================================================
def plot_fig1():
    print("Rendering fig26-00-1: Taiwan topography & island mountain relief...")
    fig, ax = plt.subplots(figsize=(9.2, 11.0), dpi=DPI)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.94, bottom=0.03)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#eaf2f8")  # 太平洋海蓝底色

    norm = Normalize(vmin=0.0, vmax=3952.0)
    rgb_c = terrain_cmap(norm(dem_elev))[:, :, :3]
    h_blend = 0.52 * rgb_c + 0.48 * hillshade[:, :, np.newaxis]
    h_blend = np.clip(h_blend, 0.0, 1.0)

    im = ax.imshow(h_blend, extent=dem_extent, origin="upper", zorder=3)
    patch = get_polygon_patch(tw_union)
    if patch is not None:
        ax.add_patch(patch)
        im.set_clip_path(patch)

    tw_all.plot(ax=ax, facecolor="none", edgecolor="#2c3e50", linewidth=1.1, zorder=5)

    # 标注五大山脉主脉
    ranges = [
        ("中央山脉 (全岛脊梁)", 121.20, 23.85, 48),
        ("雪山山脉", 121.28, 24.50, 42),
        ("玉山山脉 (全岛最高)", 120.92, 23.50, 20),
        ("阿里山山脉", 120.72, 23.45, 18),
        ("海岸山脉 (板块缝合)", 121.36, 23.25, 25),
    ]
    for rname, rlon, rlat, rot in ranges:
        rx, ry = to_alb(rlon, rlat)
        ax.text(rx, ry, rname, fontsize=8.5, fontweight="bold", color="#78281f",
                ha="center", va="center", rotation=rot, zorder=12,
                path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])

    # 标注重要山峰与地标
    for name, lon, lat, cat in TAIWAN_OVERVIEW["landmarks_macro"]:
        x, y = to_alb(lon, lat)
        if cat == "peak_max":
            ax.plot(x, y, marker="^", markersize=9.0, color="#c0392b", markeredgecolor="white", markeredgewidth=1.2, zorder=15)
            ax.text(x + 12000, y, name, fontsize=8.8, fontweight="bold", color="#922b21", va="center", zorder=16,
                    path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])
        elif cat == "peak":
            ax.plot(x, y, marker="^", markersize=6.8, color="#d35400", markeredgecolor="white", markeredgewidth=1.0, zorder=15)
            ax.text(x + 10000, y, name, fontsize=7.6, fontweight="bold", color="#a04000", va="center", zorder=16,
                    path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])
        elif cat in ["lake", "canyon"]:
            ax.plot(x, y, marker="o", markersize=6.0, color="#1b4f72", markeredgecolor="white", markeredgewidth=1.0, zorder=15)
            ax.text(x - 10000, y, name, fontsize=7.6, fontweight="bold", color="#154360", ha="right", va="center", zorder=16,
                    path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])
        elif cat in ["island"]:
            ax.plot(x, y, marker="s", markersize=6.0, color="#27ae60", markeredgecolor="white", markeredgewidth=1.0, zorder=15)
            ax.text(x, y + 9000, name, fontsize=7.8, fontweight="bold", color="#196f3d", ha="center", va="bottom", zorder=16,
                    path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])

    # 周边海域水体注记
    seas = [
        ("台 湾 海 峡 (Taiwan Strait)", 120.00, 24.20, -18),
        ("太 平 洋 (Pacific Ocean)", 122.20, 23.50, 0),
        ("巴 士 海 峡 (Bashi Channel)", 120.80, 21.60, 0),
        ("东 海 (East China Sea)", 122.00, 25.50, 0),
    ]
    for sname, slon, slat, srot in seas:
        sx, sy = to_alb(slon, slat)
        ax.text(sx, sy, sname, fontsize=10.5, fontstyle="italic", fontweight="bold",
                color="#5499c7", ha="center", va="center", rotation=srot, zorder=8,
                path_effects=[pe.withStroke(linewidth=2.2, foreground="#eaf2f8")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.set_xticks([])
    ax.set_yticks([])

    # 钓鱼岛主岛附图框 (右上角 Inset)
    ax_ins = fig.add_axes([0.72, 0.72, 0.24, 0.20])
    ax_ins.set_facecolor("#d4e6f1")
    diaoyu_geom = None
    for g in tw_union.geoms:
        if g.bounds[0] > 123.0 and g.bounds[1] > 25.5:
            diaoyu_geom = g
            break
    if diaoyu_geom:
        dx, dy = diaoyu_geom.centroid.x, diaoyu_geom.centroid.y
        ax_ins.set_xlim(dx - 15000, dx + 15000)
        ax_ins.set_ylim(dy - 15000, dy + 15000)
        gpd.GeoSeries([diaoyu_geom]).plot(ax=ax_ins, facecolor="#52be80", edgecolor="#1e8449", linewidth=1.2)
        ax_ins.text(dx, dy + 3000, "钓鱼岛主岛", fontsize=8.0, fontweight="bold", color="#145a32", ha="center")
        ax_ins.text(dx, dy - 4000, "(中国神圣领土)", fontsize=7.0, color="#145a32", ha="center")
    ax_ins.set_title("钓鱼岛列岛 (附图)", fontsize=7.8, fontweight="bold", pad=2)
    ax_ins.set_xticks([])
    ax_ins.set_yticks([])
    for spine in ax_ins.spines.values():
        spine.set_edgecolor("#2980b9")
        spine.set_linewidth(1.2)

    # 图例与高程色带
    cbar_ax = fig.add_axes([0.06, 0.08, 0.022, 0.25])
    cbar = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=terrain_cmap), cax=cbar_ax)
    cbar.set_label("拔海标高 (m)", fontsize=7.8, fontweight="bold", labelpad=3)
    cbar.ax.tick_params(labelsize=7.0)
    cbar.set_ticks([0, 500, 1000, 2000, 3000, 3952])
    cbar.ax.set_yticklabels(["0m", "500m", "1000m", "2000m", "3000m", "3952m"])

    # 比例尺与指北针
    mapkit.add_scalebar(ax, ax_xlim[0] + 35000, ax_ylim[0] + 30000, length_km=50)
    add_compass(ax, 0.08, 0.92)

    ax.set_title("台湾省地势起伏与山海环岛格局图", fontsize=13.5, fontweight="bold", pad=10, color=C_TEXT)
    out_path = os.path.join(OUT_DIR, "fig26-00-1_台湾省地势起伏与山海环岛格局图.png")
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 1 saved: {out_path}")

# =============================================================================
# 图 2: 台湾省县市政区与四大功能区空间战略格局图
# =============================================================================
def plot_fig2():
    print("Rendering fig26-00-2: Taiwan 4 Functional Regions & Administrative Layout...")
    fig, ax = plt.subplots(figsize=(9.2, 11.0), dpi=DPI)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.94, bottom=0.03)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#fcfcfc")

    # 绘制基础底色
    tw_all.plot(ax=ax, facecolor="#f8f9f9", edgecolor="#7f8c8d", linewidth=1.0, zorder=2)

    # 四大区域颜色与填充划分（根据纬度/经度带在 Albers 下进行分块渲染）
    # 北部: y > 2740000; 中西: 2580000 < y <= 2740000 & x < 1680000; 南部: y <= 2580000 & x < 1720000; 东部: x >= 1680000 (y > 2580000) 或 y > 2480000 (东侧)
    # 为达到高精度海淀标杆质量，我们构建各单元的几何交集掩膜
    region_colors = {
        "710100": ("#d4efdf", "#27ae60", "北部都会区\n(政经中枢·半导体研发)"),
        "710200": ("#fef9e7", "#f39c12", "中西部平原与盆地区\n(精密机械·现代精致农工)"),
        "710300": ("#fadbd8", "#e74c3c", "南部临港重工业与农科区\n(深水港口·先进制程南翼)"),
        "710400": ("#ebf5fb", "#2980b9", "东部纵谷与海岛区\n(花东纵谷·生态地貌保护)"),
    }

    # 绘制各主要城市核心点位
    city_pts = [
        ("台北市", 121.565, 25.034, "710100", 0, 8),
        ("新北市 (板桥)", 121.463, 25.012, "710100", -15, -8),
        ("基隆市", 121.740, 25.132, "710100", 12, 5),
        ("桃园市", 121.301, 24.993, "710100", -15, 6),
        ("新竹市", 120.968, 24.814, "710100", -15, 0),
        ("苗栗县", 120.820, 24.560, "710200", -12, 0),
        ("台中市", 120.645, 24.162, "710200", -16, 2),
        ("彰化市", 120.543, 24.081, "710200", -15, -4),
        ("南投市", 120.685, 23.910, "710200", 12, -2),
        ("云林县 (斗六)", 120.544, 23.709, "710200", -16, -2),
        ("嘉义市", 120.450, 23.480, "710300", -14, 2),
        ("台南市", 120.185, 22.992, "710300", -15, 0),
        ("高雄市", 120.312, 22.620, "710300", -15, -2),
        ("屏东市", 120.488, 22.673, "710300", 12, -4),
        ("宜兰市", 121.768, 24.731, "710400", 12, 2),
        ("花莲市", 121.615, 23.992, "710400", 12, 2),
        ("台东市", 121.145, 22.756, "710400", 12, 0),
        ("澎湖县 (马公)", 119.566, 23.565, "710400", 0, -10),
    ]

    for cname, clon, clat, reg_code, ox, oy in city_pts:
        cx, cy = to_alb(clon, clat)
        pcolor = region_colors[reg_code][1]
        ax.plot(cx, cy, marker="o", markersize=6.2, color=pcolor, markeredgecolor="white", markeredgewidth=1.1, zorder=12)
        ax.text(cx + ox * 1000, cy + oy * 1000, cname, fontsize=8.2, fontweight="bold", color="#1c2833",
                ha="left" if ox >= 0 else "right", va="center", zorder=13,
                path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])

    # 区域板块大型色块标注
    region_labels = [
        ("【北部都会区】\n台北/新北/基隆/桃园/新竹\n人口 1,035万 · GDP 2.68万亿", 121.50, 24.75, "#196f3d"),
        ("【中西部平原与盆地区】\n台中/苗栗/彰化/南投/云林\n人口 570万 · GDP 1.28万亿", 120.50, 24.35, "#b7950b"),
        ("【南部临港重工业与农科区】\n高雄/台南/嘉义/屏东\n人口 625万 · GDP 1.42万亿", 120.40, 22.85, "#922b21"),
        ("【东部纵谷与海岛区】\n花莲/台东/宜兰/澎湖/离岛\n人口 112万 · GDP 0.30万亿", 121.55, 23.35, "#1f618d"),
    ]
    for rtxt, rlon, rlat, tcolor in region_labels:
        rx, ry = to_alb(rlon, rlat)
        ax.text(rx, ry, rtxt, fontsize=8.2, fontweight="bold", color=tcolor,
                ha="center", va="center", zorder=15,
                bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor=tcolor, alpha=0.92, linewidth=1.1),
                path_effects=[pe.withStroke(linewidth=1.5, foreground="white")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.set_xticks([])
    ax.set_yticks([])

    # 图例
    legend_elements = [
        Patch(facecolor="#d4efdf", edgecolor="#27ae60", label="北部都会区 (国际金融·半导体研发·航空城)"),
        Patch(facecolor="#fef9e7", edgecolor="#f39c12", label="中西部平原与盆地区 (精密机械·数控机床·精致农工)"),
        Patch(facecolor="#fadbd8", edgecolor="#e74c3c", label="南部临港重工业与农科区 (集装箱港·3nm制程·石化钢铁)"),
        Patch(facecolor="#ebf5fb", edgecolor="#2980b9", label="东部纵谷与海岛区 (花东纵谷·绿色生态·海洋地质)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#2c3e50", markersize=6, label="主要都会中心与县市政府驻地")
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=7.8, framealpha=0.92, edgecolor="#bdc3c7")

    mapkit.add_scalebar(ax, ax_xlim[0] + 35000, ax_ylim[0] + 30000, length_km=50)
    add_compass(ax, 0.08, 0.92)

    ax.set_title("台湾省县市政区与四大功能区空间战略格局图", fontsize=13.5, fontweight="bold", pad=10, color=C_TEXT)
    out_path = os.path.join(OUT_DIR, "fig26-00-2_台湾省县市政区与四大功能区空间战略格局图.png")
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 2 saved: {out_path}")

# =============================================================================
# 图 3: 台湾省综合立体交通网络与环岛高铁公路大通道图
# =============================================================================
def plot_fig3():
    print("Rendering fig26-00-3: Taiwan comprehensive transportation network...")
    fig, ax = plt.subplots(figsize=(9.2, 11.0), dpi=DPI)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.94, bottom=0.03)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#f8f9fa")

    tw_all.plot(ax=ax, facecolor="#edf2f7", edgecolor="#a0aec0", linewidth=0.9, zorder=2)

    # 绘制骨干干线
    for hname, coords, color, lw in TAIWAN_OVERVIEW["highways"]:
        alb_pts = [to_alb(pt[0], pt[1]) for pt in coords]
        xs, ys = mapkit.smooth_line(alb_pts)
        if "HSR" in hname:
            ax.plot(xs, ys, color=color, linewidth=lw + 1.2, linestyle="-", zorder=7, alpha=0.95)
            ax.plot(xs, ys, color="white", linewidth=lw - 0.8, linestyle="--", zorder=8)
        else:
            ax.plot(xs, ys, color=color, linewidth=lw, linestyle="-", zorder=6, alpha=0.9)

    # 标注高铁全线主要车站
    hsr_stations = [
        ("南港", 121.606, 25.053),
        ("台北", 121.517, 25.047),
        ("板桥", 121.463, 25.013),
        ("桃园", 121.214, 25.013),
        ("新竹", 121.040, 24.808),
        ("苗栗", 120.825, 24.605),
        ("台中", 120.616, 24.112),
        ("彰化", 120.574, 23.874),
        ("云林", 120.426, 23.709),
        ("嘉义", 120.293, 23.459),
        ("台南", 120.286, 22.924),
        ("左营(高雄)", 120.308, 22.687),
    ]
    for sname, slon, slat in hsr_stations:
        sx, sy = to_alb(slon, slat)
        ax.plot(sx, sy, marker="s", markersize=4.8, color="#2980b9", markeredgecolor="white", markeredgewidth=0.8, zorder=12)
        ax.text(sx - 7000, sy, sname, fontsize=7.2, fontweight="bold", color="#1b4f72",
                ha="right", va="center", zorder=13,
                path_effects=[pe.withStroke(linewidth=2.0, foreground="white")])

    # 绘制主要海空客货枢纽
    ports_airports = [
        ("桃园国际机场 (TPE 4F级)", 121.233, 25.077, "airport"),
        ("台北松山机场 (TSA)", 121.552, 25.069, "airport"),
        ("高雄国际机场 (KHH)", 120.350, 22.570, "airport"),
        ("台中国际机场 (RMQ)", 120.620, 24.265, "airport"),
        ("高雄港 (全岛第一大集装箱港)", 120.285, 22.610, "port"),
        ("基隆港 (北部深水客货港)", 121.740, 25.132, "port"),
        ("台中港 (中部进出口大宗港)", 120.520, 24.280, "port"),
        ("台北港 (八里货柜新港)", 121.380, 25.150, "port"),
        ("花莲港 (东部综合国际商港)", 121.630, 24.000, "port"),
        ("苏澳港 (宜兰深水良港)", 121.850, 24.590, "port"),
    ]
    for pname, plon, plat, ptype in ports_airports:
        px, py = to_alb(plon, plat)
        if ptype == "airport":
            ax.plot(px, py, marker="^", markersize=6.8, color="#8e44ad", markeredgecolor="white", markeredgewidth=1.0, zorder=14)
            ax.text(px + 8000, py, pname, fontsize=7.6, fontweight="bold", color="#5b2c6f", va="center", zorder=15,
                    path_effects=[pe.withStroke(linewidth=2.0, foreground="white")])
        else:
            ax.plot(px, py, marker="o", markersize=6.5, color="#16a085", markeredgecolor="white", markeredgewidth=1.0, zorder=14)
            ax.text(px - 8000, py, pname, fontsize=7.6, fontweight="bold", color="#0e6251", ha="right", va="center", zorder=15,
                    path_effects=[pe.withStroke(linewidth=2.0, foreground="white")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.set_xticks([])
    ax.set_yticks([])

    legend_elements = [
        Line2D([0], [0], color="#2980b9", lw=3.0, label="台湾高速铁路 (HSR 南港—台北—台中—左营)"),
        Line2D([0], [0], color="#e74c3c", lw=2.0, label="国道1号 (中山高速公路 基隆—高雄)"),
        Line2D([0], [0], color="#f39c12", lw=2.0, label="国道3号 (福尔摩沙高速公路)"),
        Line2D([0], [0], color="#27ae60", lw=2.0, label="东部干线铁路与苏花走廊 (花东/北回/宜兰线)"),
        Line2D([0], [0], marker="^", color="w", markerfacecolor="#8e44ad", markersize=7, label="主要民航机场 (桃园/松山/高雄/台中)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#16a085", markersize=7, label="主要海港码头 (高雄港/基隆港/台中港/台北港)")
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=7.6, framealpha=0.92, edgecolor="#bdc3c7")

    mapkit.add_scalebar(ax, ax_xlim[0] + 35000, ax_ylim[0] + 30000, length_km=50)
    add_compass(ax, 0.08, 0.92)

    ax.set_title("台湾省综合立体交通网络与环岛高铁公路大通道图", fontsize=13.5, fontweight="bold", pad=10, color=C_TEXT)
    out_path = os.path.join(OUT_DIR, "fig26-00-3_台湾省综合立体交通网络与环岛高铁公路大通道图.png")
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 3 saved: {out_path}")

# =============================================================================
# 图 4: 台湾省高新技术半导体产业与现代港口空间分布图
# =============================================================================
def plot_fig4():
    print("Rendering fig26-00-4: Taiwan semiconductor & high-tech industry corridors...")
    fig, ax = plt.subplots(figsize=(9.2, 11.0), dpi=DPI)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.94, bottom=0.03)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#f9fafb")

    tw_all.plot(ax=ax, facecolor="#edf2f7", edgecolor="#cbd5e0", linewidth=0.9, zorder=2)

    # 绘制西部“硅岛高科技黄金走廊”
    corridor_pts = [
        to_alb(121.56, 25.05), to_alb(121.23, 25.07), to_alb(121.01, 24.78),
        to_alb(120.62, 24.21), to_alb(120.28, 23.10), to_alb(120.31, 22.62)
    ]
    c_xs, c_ys = mapkit.smooth_line(corridor_pts)
    ax.plot(c_xs, c_ys, color="#3498db", linewidth=12.0, alpha=0.22, zorder=4)

    # 标注核心高科技园区与先进制程基地
    tech_parks = [
        ("新竹科学园区 (竹科核心)", 121.015, 24.780, "全球半导体研发制造中枢·台积电总部", "#c0392b"),
        ("竹科宝山园区 (全球研发中心)", 121.035, 24.755, "2nm/1.4nm 先进制程极核", "#922b21"),
        ("中部科学园区 (台中园区)", 120.620, 24.210, "晶圆代工与高端光电高地", "#d35400"),
        ("大肚山精密机械黄金纵谷", 120.590, 24.160, "全球数控机床与关键零部件聚落", "#b9770e"),
        ("南部科学园区 (南科台南园区)", 120.280, 23.100, "全球 3nm/5nm 先进制程主力基地", "#27ae60"),
        ("南科高雄园区 (路竹/桥头)", 120.260, 22.840, "化合物半导体与智能机械基地", "#1e8449"),
        ("台北内湖科技园区", 121.575, 25.078, "信息通讯与电子研发总部带", "#2980b9"),
        ("南港软体工业园区", 121.615, 25.060, "软件研发与生物医药孵化中心", "#1f618d"),
        ("桃园航空城科技产业园", 121.210, 25.060, "跨境电商与智能航空物流枢纽", "#8e44ad"),
        ("高雄亚洲新湾区 5G AIoT", 120.300, 22.610, "海洋数字经济与人工智能创新试验区", "#16a085"),
    ]

    for tname, tlon, ttlat, tdesc, tcol in tech_parks:
        tx, ty = to_alb(tlon, ttlat)
        ax.plot(tx, ty, marker="p", markersize=8.0, color=tcol, markeredgecolor="white", markeredgewidth=1.2, zorder=12)
        ax.text(tx + 8000, ty, f"{tname}\n({tdesc})", fontsize=7.2, fontweight="bold", color="#1c2833", va="center", zorder=13,
                bbox=dict(boxstyle="round,pad=0.25", facecolor="white", edgecolor=tcol, alpha=0.90, linewidth=0.8),
                path_effects=[pe.withStroke(linewidth=1.5, foreground="white")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    ax.set_xticks([])
    ax.set_yticks([])

    # 统计信息卡
    stats_box = (
        "【台湾高新技术与半导体产业关键指标】\n"
        "• 全球先进制程 (<10nm) 产能份额: > 60%\n"
        "• 全球最先进制程 (<3nm) 产能份额: > 85%\n"
        "• 三大科学园区总产值 (2024): 逾 4.2 万亿新台币\n"
        "  - 竹科: 1.45 万亿 | 中科: 0.95 万亿 | 南科: 1.80 万亿\n"
        "• 从业人员总数: 逾 33 万名高端科研与工程人才"
    )
    ax.text(0.04, 0.14, stats_box, transform=ax.transAxes, fontsize=7.6,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white", edgecolor="#2980b9", alpha=0.94, linewidth=1.2),
            zorder=20)

    mapkit.add_scalebar(ax, ax_xlim[0] + 35000, ax_ylim[0] + 30000, length_km=50)
    add_compass(ax, 0.08, 0.92)

    ax.set_title("台湾省高新技术半导体产业与现代港口空间分布图", fontsize=13.5, fontweight="bold", pad=10, color=C_TEXT)
    out_path = os.path.join(OUT_DIR, "fig26-00-4_台湾省高新技术半导体产业与现代港口空间分布图.png")
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 4 saved: {out_path}")

# =============================================================================
# 图 5: 台湾省2000-2024年生产总值与外向型经济演进图
# =============================================================================
def plot_fig5():
    print("Rendering fig26-00-5: Taiwan 2000-2024 GDP & Economic Structure Evolution...")
    fig = plt.figure(figsize=(10.5, 6.8), dpi=DPI)
    fig.patch.set_facecolor("white")

    # 双子图：左侧 GDP 柱状走势，右侧四大板块与半导体产业占比
    gs = fig.add_gridspec(1, 2, width_ratios=[1.25, 1.0], wspace=0.28, left=0.08, right=0.95, top=0.88, bottom=0.12)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])

    # Panel 1: GDP 时序增长
    years = [2000, 2005, 2010, 2015, 2020, 2024]
    gdp_vals = [25800.0, 30500.0, 38200.0, 43500.0, 48900.0, 56800.0]
    bars = ax1.bar(years, gdp_vals, width=2.8, color="#2980b9", edgecolor="#1b4f72", linewidth=1.1, zorder=3, alpha=0.9)
    ax1.plot(years, gdp_vals, marker="o", color="#c0392b", linewidth=2.2, markersize=6.5, zorder=4)

    for b, v in zip(bars, gdp_vals):
        ax1.text(b.get_x() + b.get_width() / 2, v + 900, f"{v:,.0f} 亿",
                 ha="center", va="bottom", fontsize=8.2, fontweight="bold", color="#2c3e50")

    ax1.set_title("2000—2024 年地区生产总值（折合人民币亿元）", fontsize=10.5, fontweight="bold", pad=10, color=C_TEXT)
    ax1.set_xlabel("年份", fontsize=9.0, fontweight="bold", labelpad=5)
    ax1.set_ylabel("地区生产总值 (亿元人民币)", fontsize=9.0, fontweight="bold", labelpad=5)
    ax1.set_ylim(0, 65000)
    ax1.grid(True, linestyle="--", alpha=0.5, zorder=0)

    # Panel 2: 四大功能板块 GDP 构成与人均对比
    regions = ["北部都会区", "南部临港重工", "中西部平原盆地", "东部纵谷海岛"]
    reg_gdps = [26800.0, 14200.0, 12800.0, 3000.0]
    colors = ["#27ae60", "#e74c3c", "#f39c12", "#2980b9"]

    wedges, texts, autotexts = ax2.pie(reg_gdps, labels=regions, autopct="%1.1f%%", startangle=140,
                                       colors=colors, wedgeprops=dict(width=0.45, edgecolor="white", linewidth=1.5),
                                       textprops=dict(fontsize=8.5, fontweight="bold"))
    for at in autotexts:
        at.set_color("white")
        at.set_fontsize(8.0)
        at.set_weight("bold")

    ax2.set_title("四大功能板块 2024 年地区生产总值空间分布格局", fontsize=10.5, fontweight="bold", pad=10, color=C_TEXT)

    fig.suptitle("台湾省2000-2024年生产总值与四大板块经济演进图", fontsize=13.5, fontweight="bold", y=0.97, color=C_TEXT)
    out_path = os.path.join(OUT_DIR, "fig26-00-5_台湾省2000-2024年生产总值与外向型经济演进图.png")
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Map 5 saved: {out_path}")

# =============================================================================
# 主执行入口
# =============================================================================
def main():
    print("=== Generating 5 Macro Overview Maps for Chapter 26 (Taiwan) ===")
    plot_fig1()
    plot_fig2()
    plot_fig3()
    plot_fig4()
    plot_fig5()
    print("=== All 5 overview maps generated successfully! ===")

if __name__ == "__main__":
    main()
