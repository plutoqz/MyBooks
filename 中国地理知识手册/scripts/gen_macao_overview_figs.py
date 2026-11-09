# -*- coding: utf-8 -*-
"""澳门特别行政区省级地理统揽专题地图生成引擎（28-00）
包含 5 幅全特区出版级权威地图与分析图表（精细调优排版、严格杜绝压盖）：
1. fig28-00-1_澳门特别行政区地势起伏与珠江口海陆格局图.png
2. fig28-00-2_澳门特别行政区堂区分区与琴澳一体化空间战略格局图.png
3. fig28-00-3_澳门特别行政区综合立体交通网络与港珠澳大桥连通图.png
4. fig28-00-4_澳门特别行政区世界旅游休闲中心与现代金融商贸空间分布图.png
5. fig28-00-5_澳门特别行政区2000-2024年本地生产总值与入境旅客演进图.png
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
from macao_configs import MACAO_OVERVIEW, MACAO_DISTRICT_CONFIGS

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

print("Loading Macao boundaries and DEM...")
DATA_DIR = os.path.join(BASE_DIR, "data")
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

mo_all = gpd.read_file(os.path.join(DATAV_DIR, "820000_full.json")).to_crs(ALBERS)
mo_all["geometry"] = mo_all.geometry.buffer(0)
mo_union = mo_all.union_all()

# 邻接珠海市
zh_path = os.path.join(DATAV_DIR, "440400.json")
if not os.path.exists(zh_path):
    zh_path = os.path.join(DATAV_DIR, "440400_full.json")
zh_gdf = gpd.read_file(zh_path).to_crs(ALBERS) if os.path.exists(zh_path) else None

b = mo_all.total_bounds
span_x = b[2] - b[0]
span_y = b[3] - b[1]
pad_x = span_x * 0.25
pad_y = span_y * 0.15
ax_xlim = (b[0] - pad_x, b[2] + pad_x)
ax_ylim = (b[1] - pad_y, b[3] + pad_y)

dem_file = os.path.join(DATA_DIR, "dem", "province", "820000_z9.npz")
dem_data = np.load(dem_file)
dem_raw = dem_data['dem']
res = float(dem_data['res'])
minx = float(dem_data['minx'])
maxy = float(dem_data['maxy'])
nrows, ncols = dem_raw.shape
dem_extent = [minx, minx + ncols * res, maxy - nrows * res, maxy]

dem_elev = np.where(dem_raw < 0, np.nan, dem_raw)
hillshade = calc_hillshade(dem_elev, res)

terrain_cmap = LinearSegmentedColormap.from_list("mo_terrain", [
    (0.0, "#2ecc71"),   # 海平面与沿海填海区 (0m ~ 30m) 翠绿
    (0.25, "#a9dfbf"),  # 缓坡与台地 (30m ~ 70m) 浅绿
    (0.50, "#f9e79f"),  # 东望洋山/西望洋山 (70m ~ 100m) 暖黄
    (0.75, "#f5b041"),  # 大潭山/小潭山 (100m ~ 140m) 橙黄
    (1.0, "#873600")    # 叠石塘山极顶 (140m ~ 170.6m) 深褐
])

# =============================================================================
# 图 1: 澳门特别行政区地势起伏与珠江口海陆格局图
# =============================================================================
def plot_fig1():
    print("Rendering fig28-00-1: Macao topography & Pearl River Estuary...")
    fig, ax = plt.subplots(figsize=(8.8, 9.5), dpi=DPI)
    fig.subplots_adjust(left=0.03, right=0.97, top=0.94, bottom=0.03)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#eaf2f8")  # 海洋浅蓝

    norm = Normalize(vmin=0.0, vmax=170.6)
    rgb_c = terrain_cmap(norm(dem_elev))[:, :, :3]
    h_blend = 0.55 * rgb_c + 0.45 * hillshade[:, :, np.newaxis]
    h_blend = np.clip(h_blend, 0.0, 1.0)

    # 邻接珠海与横琴
    if zh_gdf is not None:
        zh_gdf.plot(ax=ax, facecolor="#f2f3f4", edgecolor="#bdc3c7", linewidth=0.8, linestyle="--", zorder=2)
        zx, zy = to_alb(113.51, 22.18)
        ax.text(zx, zy, "广东省珠海市 (Zhuhai)", fontsize=9.0, color="#7f8c8d", fontweight="bold",
                ha="center", va="center", zorder=3, rotation=45,
                path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])
        hx, hy = to_alb(113.52, 22.13)
        ax.text(hx, hy, "珠海横琴岛 (Hengqin)", fontsize=8.5, color="#7f8c8d", fontweight="bold",
                ha="center", va="center", zorder=3,
                path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])

    im = ax.imshow(h_blend, extent=dem_extent, origin="upper", zorder=3)
    patch = get_polygon_patch(mo_union)
    if patch is not None:
        ax.add_patch(patch)
        im.set_clip_path(patch)

    mo_all.boundary.plot(ax=ax, color="#1b4f72", linewidth=1.0, zorder=5)

    # 标注四大跨海大桥
    bridges = MACAO_OVERVIEW.get("bridges", [])
    for b_name, b_coords, b_col, b_lw in bridges:
        pts = [to_alb(x, y) for x, y in b_coords]
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=b_col, lw=b_lw, zorder=6)

    # 标注主要制高点
    peaks = [
        ("叠石塘山 (170.6m 全澳最高峰)", 113.560, 22.125, 170.6),
        ("大潭山 (159.0m)", 113.565, 22.160, 159.0),
        ("小潭山 (111.0m)", 113.545, 22.160, 111.0),
        ("东望洋山 (91.0m)", 113.550, 22.196, 91.0),
        ("西望洋山 (62.7m)", 113.534, 22.184, 62.7),
    ]
    for name, lon, lat, elev in peaks:
        px, py = to_alb(lon, lat)
        is_max = (elev >= 170)
        ax.plot(px, py, marker="^", color="#c0392b" if is_max else "#8e44ad",
                markersize=8.0 if is_max else 6.0, markeredgecolor="white", mew=0.8, zorder=12)
        ax.text(px + 300, py + 100, name, fontsize=7.5 if not is_max else 8.5,
                color="#78281f" if is_max else "#2c3e50", fontweight="bold", zorder=13,
                path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    add_compass(ax, 0.94, 0.92)
    mapkit.add_scalebar(ax, b[0] + span_x * 0.05, b[1] + span_y * 0.05, length_km=2)

    cax = fig.add_axes([0.05, 0.14, 0.018, 0.22])
    sm = plt.cm.ScalarMappable(cmap=terrain_cmap, norm=norm)
    sm.set_array([])
    cb = fig.colorbar(sm, cax=cax, orientation="vertical")
    cb.set_label("高程 (m)", fontsize=7.0, color=C_TEXT)
    cb.ax.tick_params(labelsize=6.8)

    ax.set_title("澳门特别行政区地势起伏与珠江口海陆格局图", fontsize=12.5, fontweight="bold", color=C_TEXT, pad=10)
    fig.text(0.5, 0.012, "制图基准：Albers等积投影 · DEM高程：AWS Terrain z9 · 制作：《中国地理知识手册》",
             ha="center", fontsize=6.8, color="#7f8c8d")

    out_file = os.path.join(OUT_DIR, "fig28-00-1_澳门特别行政区地势起伏与珠江口海陆格局图.png")
    fig.savefig(out_file, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_file}")

# =============================================================================
# 图 2: 澳门特别行政区堂区分区与琴澳一体化空间战略格局图
# =============================================================================
def plot_fig2():
    print("Rendering fig28-00-2: Macao parishes & Hengqin cooperation...")
    fig, ax = plt.subplots(figsize=(8.8, 9.5), dpi=DPI)
    fig.subplots_adjust(left=0.03, right=0.97, top=0.94, bottom=0.03)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#f4f8fa")

    parish_colors = {
        "花地玛堂区": "#fef9e7", "花王堂区": "#fef5e7", "望德堂区": "#fcf3cf",
        "大堂区": "#fdebd0", "风顺堂区": "#fadbd8",
        "嘉模堂区": "#ebf5fb", "路凼填海区": "#d4efdf", "圣方济各堂区": "#e8f8f5",
    }

    if zh_gdf is not None:
        zh_gdf.plot(ax=ax, facecolor="#eaeded", edgecolor="#bdc3c7", linewidth=0.8, linestyle="--", zorder=2)
        zx, zy = to_alb(113.51, 22.18)
        ax.text(zx, zy, "珠海市香洲区", fontsize=8.8, color="#95a5a6", fontweight="bold", ha="center", va="center", zorder=3)
        hx, hy = to_alb(113.52, 22.13)
        ax.text(hx, hy, "横琴粤澳深度合作区\n(一国两制新实践新平台)", fontsize=8.0, color="#b9770e",
                fontweight="bold", ha="center", va="center", zorder=3,
                path_effects=[pe.withStroke(linewidth=2.0, foreground="white")])

    for idx, row in mo_all.iterrows():
        pname = row['name']
        c = parish_colors.get(pname, "#fcf3cf")
        gpd.GeoSeries([row.geometry]).plot(ax=ax, facecolor=c, edgecolor="#7f8c8d", linewidth=0.7, zorder=3)
        pt = row.geometry.representative_point()
        ax.text(pt.x, pt.y, pname, fontsize=7.2, fontweight="bold", color="#2c3e50", ha="center", va="center", zorder=6,
                path_effects=[pe.withStroke(linewidth=2.0, foreground="white")])

    # 3大分析大区框线示意
    # 澳门半岛
    penin_x, penin_y = to_alb(113.565, 22.205)
    ax.text(penin_x, penin_y, "【澳门半岛核心区】\n政治商贸 · 世界文化遗产城区", fontsize=7.8, fontweight="bold",
            color="#922b21", zorder=8, path_effects=[pe.withStroke(linewidth=2.0, foreground="white")])

    # 路氹城
    cotai_x, cotai_y = to_alb(113.585, 22.148)
    ax.text(cotai_x, cotai_y, "【路氹城综合度假区】\n世界旅游休闲中心核心", fontsize=7.8, fontweight="bold",
            color="#196f3d", zorder=8, path_effects=[pe.withStroke(linewidth=2.0, foreground="white")])

    # 路环岛
    colo_x, colo_y = to_alb(113.585, 22.115)
    ax.text(colo_x, colo_y, "【路环生态休闲区】\n城市后花园 · 滨海度假", fontsize=7.8, fontweight="bold",
            color="#1b4f72", zorder=8, path_effects=[pe.withStroke(linewidth=2.0, foreground="white")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    add_compass(ax, 0.94, 0.92)
    mapkit.add_scalebar(ax, b[0] + span_x * 0.05, b[1] + span_y * 0.05, length_km=2)

    patches = [
        Patch(facecolor="#fef5e7", edgecolor="#7f8c8d", label="澳门半岛 5 堂区 (老城政商与世遗核心)"),
        Patch(facecolor="#ebf5fb", edgecolor="#7f8c8d", label="氹仔岛 1 堂区 (居住与海空门户)"),
        Patch(facecolor="#d4efdf", edgecolor="#7f8c8d", label="路氹填海区 (金光大道综合度假城)"),
        Patch(facecolor="#e8f8f5", edgecolor="#7f8c8d", label="路环岛 1 堂区 (全澳生态后花园)"),
    ]
    ax.legend(handles=patches, loc="upper left", bbox_to_anchor=(0.03, 0.96), fontsize=7.0, framealpha=0.92)

    ax.set_title("澳门特别行政区堂区分区与琴澳一体化空间战略格局图", fontsize=12.5, fontweight="bold", color=C_TEXT, pad=10)
    fig.text(0.5, 0.012, "数据来源：澳门特区政府统计暨普查局 · 地图绘制暨地籍局 · 制作：《中国地理知识手册》",
             ha="center", fontsize=6.8, color="#7f8c8d")

    out_file = os.path.join(OUT_DIR, "fig28-00-2_澳门特别行政区堂区分区与琴澳一体化空间战略格局图.png")
    fig.savefig(out_file, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_file}")

# =============================================================================
# 图 3: 澳门特别行政区综合立体交通网络与港珠澳大桥连通图
# =============================================================================
def plot_fig3():
    print("Rendering fig28-00-3: Macao transport & HZMB connectivity...")
    fig, ax = plt.subplots(figsize=(8.8, 9.5), dpi=DPI)
    fig.subplots_adjust(left=0.03, right=0.97, top=0.94, bottom=0.03)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#eaf2f8")

    if zh_gdf is not None:
        zh_gdf.plot(ax=ax, facecolor="#f2f3f4", edgecolor="#bdc3c7", linewidth=0.8, zorder=2)
    mo_all.plot(ax=ax, facecolor="#fefefe", edgecolor="#7f8c8d", linewidth=0.7, zorder=3)

    # 1. 港珠澳大桥澳门连接线及口岸
    bridge_coords = [(113.555, 22.215), (113.575, 22.208)]
    pts = [to_alb(x, y) for x, y in bridge_coords]
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color="#c0392b", lw=2.5, ls="--", zorder=7)
    hzmb_x, hzmb_y = to_alb(113.575, 22.208)
    ax.plot(hzmb_x, hzmb_y, marker="o", color="#c0392b", markersize=9, markeredgecolor="white", mew=1.0, zorder=10)
    ax.text(hzmb_x + 300, hzmb_y, "港珠澳大桥\n澳门边检大楼", fontsize=7.5, fontweight="bold", color="#922b21", zorder=12,
            path_effects=[pe.withStroke(linewidth=2, foreground="white")])

    # 2. 澳氹跨海大桥群
    bridges = MACAO_OVERVIEW.get("bridges", [])
    for b_name, b_coords, b_col, b_lw in bridges:
        b_pts = [to_alb(x, y) for x, y in b_coords]
        ax.plot([p[0] for p in b_pts], [p[1] for p in b_pts], color=b_col, lw=b_lw, zorder=6)

    # 3. 澳门国际机场与氹仔客运码头
    air_x, air_y = to_alb(113.592, 22.155)
    ax.plot(air_x, air_y, marker="o", color="#2980b9", markersize=10, markeredgecolor="white", mew=1.0, zorder=10)
    ax.text(air_x + 300, air_y, "澳门国际机场 (MFM)\n人工岛跑道空港", fontsize=7.5, fontweight="bold", color="#1b4f72", zorder=12,
            path_effects=[pe.withStroke(linewidth=2, foreground="white")])

    port_x, port_y = to_alb(113.580, 22.164)
    ax.plot(port_x, port_y, marker="s", color="#d35400", markersize=8, markeredgecolor="white", mew=0.8, zorder=10)
    ax.text(port_x + 300, port_y, "氹仔客运码头", fontsize=7.0, fontweight="bold", color="#a04000", zorder=12,
            path_effects=[pe.withStroke(linewidth=2, foreground="white")])

    # 4. 关闸与横琴口岸
    g_x, g_y = to_alb(113.549, 22.217)
    ax.plot(g_x, g_y, marker="D", color="#27ae60", markersize=7, markeredgecolor="white", mew=0.8, zorder=10)
    ax.text(g_x + 200, g_y + 100, "关闸口岸 (直通珠海拱北)", fontsize=7.2, fontweight="bold", color="#196f3d", zorder=12,
            path_effects=[pe.withStroke(linewidth=2, foreground="white")])

    hq_x, hq_y = to_alb(113.548, 22.140)
    ax.plot(hq_x, hq_y, marker="D", color="#27ae60", markersize=7, markeredgecolor="white", mew=0.8, zorder=10)
    ax.text(hq_x - 1800, hq_y, "横琴口岸\n(合作查验一次放行)", fontsize=7.2, fontweight="bold", color="#196f3d", zorder=12,
            path_effects=[pe.withStroke(linewidth=2, foreground="white")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    add_compass(ax, 0.94, 0.92)
    mapkit.add_scalebar(ax, b[0] + span_x * 0.05, b[1] + span_y * 0.05, length_km=2)

    lines = [
        Line2D([0], [0], color="#c0392b", lw=2.5, ls="--", label="港珠澳大桥跨海通道"),
        Line2D([0], [0], color="#2980b9", lw=2.0, label="跨海大桥群 (嘉乐庇/友谊/西湾/澳门大桥)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#2980b9", markersize=8, label="澳门国际机场 (海上空港)"),
        Line2D([0], [0], marker="D", color="w", markerfacecolor="#27ae60", markersize=6, label="特区核心通关陆路口岸"),
    ]
    ax.legend(handles=lines, loc="upper left", bbox_to_anchor=(0.03, 0.96), fontsize=7.0, framealpha=0.92)

    ax.set_title("澳门特别行政区综合立体交通网络与港珠澳大桥连通图", fontsize=12.5, fontweight="bold", color=C_TEXT, pad=10)
    fig.text(0.5, 0.012, "数据来源：澳门特区政府交通事务局 · 制作：《中国地理知识手册》",
             ha="center", fontsize=6.8, color="#7f8c8d")

    out_file = os.path.join(OUT_DIR, "fig28-00-3_澳门特别行政区综合立体交通网络与港珠澳大桥连通图.png")
    fig.savefig(out_file, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_file}")

# =============================================================================
# 图 4: 澳门特别行政区世界旅游休闲中心与现代金融商贸空间分布图
# =============================================================================
def plot_fig4():
    print("Rendering fig28-00-4: Macao tourism & modern finance industries...")
    fig, ax = plt.subplots(figsize=(8.8, 9.5), dpi=DPI)
    fig.subplots_adjust(left=0.03, right=0.97, top=0.94, bottom=0.03)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#f9f9fb")

    if zh_gdf is not None:
        zh_gdf.plot(ax=ax, facecolor="#f2f3f4", edgecolor="#bdc3c7", linewidth=0.8, zorder=2)
    mo_all.plot(ax=ax, facecolor="#fefefe", edgecolor="#7f8c8d", linewidth=0.7, zorder=3)

    spots = [
        ("大三巴牌坊 (世界文化遗产)", 113.541, 22.198, "#b03a2e", "heritage"),
        ("议事亭前地与历史城区", 113.540, 22.193, "#b03a2e", "heritage"),
        ("妈阁庙 (世界文化遗产)", 113.531, 22.186, "#b03a2e", "heritage"),
        ("澳门旅游塔 (338m)", 113.537, 22.180, "#e67e22", "tower"),
        ("新口岸现代金融商贸区", 113.553, 22.188, "#2980b9", "finance"),
        ("路氹金光大道综合度假城", 113.563, 22.148, "#27ae60", "resort"),
        ("官也街美食文化名街", 113.557, 22.154, "#e67e22", "food"),
        ("龙环葡韵住宅式博物馆", 113.559, 22.153, "#b03a2e", "heritage"),
        ("澳门大学横琴新校区", 113.545, 22.130, "#8e44ad", "univ"),
        ("黑沙海滩休闲度假区", 113.568, 22.122, "#16a085", "beach"),
    ]

    for title, lon, lat, color, stype in spots:
        sx, sy = to_alb(lon, lat)
        ax.plot(sx, sy, marker="*" if stype=="heritage" else "o", color=color,
                markersize=8.5, markeredgecolor="white", mew=0.8, zorder=10)
        ax.text(sx + 250, sy + 50, title, fontsize=7.2, fontweight="bold", color="#1b2631", zorder=11,
                path_effects=[pe.withStroke(linewidth=2.0, foreground="white")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    add_compass(ax, 0.94, 0.92)
    mapkit.add_scalebar(ax, b[0] + span_x * 0.05, b[1] + span_y * 0.05, length_km=2)

    patches = [
        Line2D([0], [0], marker="*", color="w", markerfacecolor="#b03a2e", markersize=8, label="“澳门历史城区”世界文化遗产"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#27ae60", markersize=8, label="路氹金光大道综合度假胜地"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#2980b9", markersize=8, label="新口岸现代金融与中葡商贸中枢"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#8e44ad", markersize=8, label="澳门大学现代科技创新园区"),
    ]
    ax.legend(handles=patches, loc="upper left", bbox_to_anchor=(0.03, 0.96), fontsize=7.0, framealpha=0.92)

    ax.set_title("澳门特别行政区世界旅游休闲中心与现代金融商贸空间分布图", fontsize=12.5, fontweight="bold", color=C_TEXT, pad=10)
    fig.text(0.5, 0.012, "数据来源：澳门特区政府旅游局 · 经济及科技发展局 · 制作：《中国地理知识手册》",
             ha="center", fontsize=6.8, color="#7f8c8d")

    out_file = os.path.join(OUT_DIR, "fig28-00-4_澳门特别行政区世界旅游休闲中心与现代金融商贸空间分布图.png")
    fig.savefig(out_file, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_file}")

# =============================================================================
# 图 5: 澳门特别行政区2000-2024年本地生产总值与入境旅客演进图
# =============================================================================
def plot_fig5():
    print("Rendering fig28-00-5: Macao GDP trajectory & visitor arrivals...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 5.2), dpi=DPI)
    fig.subplots_adjust(left=0.06, right=0.95, top=0.88, bottom=0.12, wspace=0.26)

    # 左图：本地生产总值 GDP (折合亿元人民币)
    gdp_data = MACAO_OVERVIEW["gdp_series"]
    gyears = list(gdp_data.keys())
    gvals = list(gdp_data.values())

    bars = ax1.bar(gyears, gvals, width=2.0, color="#16a085", edgecolor="#0e6251", alpha=0.88)
    for bar in bars:
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2.0, h + 80, f"{h:g}",
                 ha="center", va="bottom", fontsize=7.5, fontweight="bold", color="#0e6251")

    ax1.set_title("澳门特别行政区 2000—2024 年本地生产总值演进", fontsize=10.0, fontweight="bold", color=C_TEXT)
    ax1.set_ylabel("本地生产总值 (GDP, 亿元人民币)", fontsize=8.0, color="#2c3e50")
    ax1.set_xlabel("年份 Year", fontsize=8.0, color="#2c3e50")
    ax1.set_ylim(0, 4200)
    ax1.grid(True, linestyle="--", alpha=0.4)
    ax1.tick_params(labelsize=7.5)

    # 右图：历年入境旅客总量 (万人次)
    vis_data = MACAO_OVERVIEW["visitors_series"]
    vyears = list(vis_data.keys())
    vvals = list(vis_data.values())

    bars2 = ax2.bar(vyears, vvals, width=2.0, color="#d35400", edgecolor="#873600", alpha=0.88)
    for bar in bars2:
        h = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width() / 2.0, h + 80, f"{h:g}万",
                 ha="center", va="bottom", fontsize=7.5, fontweight="bold", color="#873600")

    ax2.set_title("澳门特别行政区 2000—2024 年入境旅客人次跨越", fontsize=10.0, fontweight="bold", color=C_TEXT)
    ax2.set_ylabel("入境旅客总量 (万人次)", fontsize=8.0, color="#2c3e50")
    ax2.set_xlabel("年份 Year", fontsize=8.0, color="#2c3e50")
    ax2.set_ylim(0, 4600)
    ax2.grid(True, linestyle="--", alpha=0.4)
    ax2.tick_params(labelsize=7.5)

    fig.suptitle("澳门特别行政区 2000—2024 年经济稳健复苏与世界旅游休闲中心跨越", fontsize=12.0, fontweight="bold", color=C_TEXT)
    fig.text(0.5, 0.02, "数据来源：澳门特别行政区政府统计暨普查局（DSEC） · 制作：《中国地理知识手册》",
             ha="center", fontsize=7.0, color="#7f8c8d")

    out_file = os.path.join(OUT_DIR, "fig28-00-5_澳门特别行政区2000-2024年本地生产总值与入境旅客演进图.png")
    fig.savefig(out_file, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_file}")

def main():
    plot_fig1()
    plot_fig2()
    plot_fig3()
    plot_fig4()
    plot_fig5()
    print("All 5 overview maps for Chapter 28 (Macao) generated successfully!")

if __name__ == "__main__":
    main()
