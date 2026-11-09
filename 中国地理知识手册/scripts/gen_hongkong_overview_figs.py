# -*- coding: utf-8 -*-
"""香港特别行政区省级地理统揽专题地图生成引擎（27-00）
包含 5 幅全特区出版级权威地图与分析图表（精细调优排版、严格杜绝压盖）：
1. fig27-00-1_香港特别行政区地势起伏与山海维港格局图.png
2. fig27-00-2_香港特别行政区18区政区与北部都会区战略格局图.png
3. fig27-00-3_香港特别行政区综合立体交通网络与海空港口大通道图.png
4. fig27-00-4_香港特别行政区现代金融与创新科技产业空间分布图.png
5. fig27-00-5_香港特别行政区2000-2024年经济跃升与深港协同对比图.png
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
from hongkong_configs import HONGKONG_OVERVIEW, HONGKONG_DISTRICT_CONFIGS

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

print("Loading Hong Kong boundaries and DEM...")
DATA_DIR = os.path.join(BASE_DIR, "data")
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

hk_all = gpd.read_file(os.path.join(DATAV_DIR, "810000_full.json")).to_crs(ALBERS)
hk_all["geometry"] = hk_all.geometry.buffer(0)
hk_union = hk_all.union_all()

# 邻接深圳底图
sz_path = os.path.join(DATAV_DIR, "440300.json")
if not os.path.exists(sz_path):
    sz_path = os.path.join(DATAV_DIR, "440300_full.json")
sz_gdf = gpd.read_file(sz_path).to_crs(ALBERS) if os.path.exists(sz_path) else None

b = hk_all.total_bounds
span_x = b[2] - b[0]
span_y = b[3] - b[1]
pad_x = span_x * 0.08
pad_y = span_y * 0.08
ax_xlim = (b[0] - pad_x, b[2] + pad_x)
ax_ylim = (b[1] - pad_y, b[3] + pad_y + span_y * 0.05)  # 稍微向上扩展容纳深圳边境

dem_file = os.path.join(DATA_DIR, "dem", "province", "810000_z11.npz")
dem_data = np.load(dem_file)
dem_raw = dem_data['dem']
res = float(dem_data['res'])
minx = float(dem_data['minx'])
maxy = float(dem_data['maxy'])
nrows, ncols = dem_raw.shape
dem_extent = [minx, minx + ncols * res, maxy - nrows * res, maxy]

dem_elev = np.where(dem_raw < 0, np.nan, dem_raw)
hillshade = calc_hillshade(dem_elev, res)

terrain_cmap = LinearSegmentedColormap.from_list("hk_terrain", [
    (0.0, "#2ecc71"),   # 海平面与沿海低平填海区 (0m ~ 100m) 翠绿
    (0.20, "#a9dfbf"),  # 浅丘陵与台地 (100m ~ 250m) 浅绿
    (0.40, "#f9e79f"),  # 丘陵谷地与台原 (250m ~ 450m) 暖黄
    (0.60, "#f5b041"),  # 狮子山/太平山中山 (450m ~ 600m) 橙黄
    (0.80, "#e59866"),  # 大东山/马鞍山 (600m ~ 800m) 棕褐
    (1.0, "#873600")    # 大帽山/凤凰山极顶 (800m ~ 957m) 深褐
])

# =============================================================================
# 图 1: 香港特别行政区地势起伏与山海维港格局图
# =============================================================================
def plot_fig1():
    print("Rendering fig27-00-1: Hong Kong topography & Victoria Harbour...")
    fig, ax = plt.subplots(figsize=(10.5, 7.5), dpi=DPI)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.93, bottom=0.03)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#eaf2f8")  # 海洋浅蓝底色

    norm = Normalize(vmin=0.0, vmax=957.0)
    rgb_c = terrain_cmap(norm(dem_elev))[:, :, :3]
    h_blend = 0.55 * rgb_c + 0.45 * hillshade[:, :, np.newaxis]
    h_blend = np.clip(h_blend, 0.0, 1.0)

    # 邻接深圳
    if sz_gdf is not None:
        sz_gdf.plot(ax=ax, facecolor="#f2f3f4", edgecolor="#bdc3c7", linewidth=0.8, linestyle="--", zorder=2)
        sx, sy = to_alb(114.10, 22.56)
        ax.text(sx, sy, "广东省深圳市 (Shenzhen)", fontsize=10.0, color="#7f8c8d", fontweight="bold",
                ha="center", va="center", zorder=3,
                path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])

    im = ax.imshow(h_blend, extent=dem_extent, origin="upper", zorder=3)
    patch = get_polygon_patch(hk_union)
    if patch is not None:
        ax.add_patch(patch)
        im.set_clip_path(patch)

    # 绘制特区陆界与海岸线
    hk_all.boundary.plot(ax=ax, color="#1b4f72", linewidth=0.9, zorder=5)

    # 深圳河
    s_river = [(114.16, 22.55), (114.13, 22.54), (114.09, 22.53), (114.06, 22.51)]
    s_pts = [to_alb(x, y) for x, y in s_river]
    ax.plot([p[0] for p in s_pts], [p[1] for p in s_pts], color="#2980b9", lw=2.2, zorder=6)
    rx, ry = to_alb(114.11, 22.538)
    ax.text(rx, ry, "深圳河 (深港界河)", fontsize=7.8, color="#1b4f72", fontweight="bold", rotation=-15, zorder=7,
            path_effects=[pe.withStroke(linewidth=2, foreground="white")])

    # 标注重要山峰与海峡水体
    peaks = [
        ("大帽山 (957m 全港最高峰)", 114.120, 22.410, 957.0),
        ("凤凰山 (934m 大屿山主峰)", 113.918, 22.258, 934.0),
        ("大东山 (869m)", 113.955, 22.260, 869.0),
        ("飞鹅山 (602m)", 114.222, 22.342, 602.0),
        ("太平山 (552m 维港之巅)", 114.144, 22.275, 552.0),
        ("狮子山 (495m 九龙地标)", 114.175, 22.355, 495.0),
        ("八仙岭 (634m)", 114.210, 22.490, 634.0),
        ("青山 (583m 屯门西屏)", 113.955, 22.390, 583.0),
    ]
    for name, lon, lat, elev in peaks:
        px, py = to_alb(lon, lat)
        is_max = (elev >= 950)
        ax.plot(px, py, marker="^", color="#c0392b" if is_max else "#8e44ad",
                markersize=8.0 if is_max else 6.0, markeredgecolor="white", markeredgewidth=0.8, zorder=12)
        ax.text(px + 900, py + 200, name, fontsize=7.6 if not is_max else 8.5,
                color="#78281f" if is_max else "#2c3e50", fontweight="bold", zorder=13,
                path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])

    # 著名海域海峡注记
    waters = [
        ("维多利亚港 (Victoria Harbour)", 114.170, 22.292),
        ("吐露港 (Tolo Harbour)", 114.230, 22.440),
        ("大鹏湾 (Mirs Bay)", 114.360, 22.500),
        ("大屿海峡 (Lantau Channel)", 113.880, 22.200),
        ("南丫海峡", 114.100, 22.230),
    ]
    for wname, wlon, wlat in waters:
        wx, wy = to_alb(wlon, wlat)
        ax.text(wx, wy, wname, fontsize=8.0, color="#2471a3", style="italic", fontweight="bold",
                ha="center", va="center", zorder=8,
                path_effects=[pe.withStroke(linewidth=2, foreground="white")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    add_compass(ax, 0.95, 0.92)
    mapkit.add_scalebar(ax, b[0] + span_x * 0.05, b[1] + span_y * 0.05, length_km=10)

    cax = fig.add_axes([0.04, 0.14, 0.015, 0.22])
    sm = plt.cm.ScalarMappable(cmap=terrain_cmap, norm=norm)
    sm.set_array([])
    cb = fig.colorbar(sm, cax=cax, orientation="vertical")
    cb.set_label("高程 Elevation (m)", fontsize=7.2, color=C_TEXT)
    cb.ax.tick_params(labelsize=6.8)

    ax.set_title("香港特别行政区地势起伏与山海维港格局图", fontsize=13.0, fontweight="bold", color=C_TEXT, pad=12)
    fig.text(0.5, 0.012, "制图基准：Albers等积投影 · DEM高程：AWS Terrain z11 (75m) · 制作：《中国地理知识手册》",
             ha="center", fontsize=7.0, color="#7f8c8d")

    out_file = os.path.join(OUT_DIR, "fig27-00-1_香港特别行政区地势起伏与山海维港格局图.png")
    fig.savefig(out_file, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_file}")

# =============================================================================
# 图 2: 香港特别行政区18区政区与北部都会区战略格局图
# =============================================================================
def plot_fig2():
    print("Rendering fig27-00-2: Hong Kong 18 districts & Northern Metropolis...")
    fig, ax = plt.subplots(figsize=(10.5, 7.5), dpi=DPI)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.93, bottom=0.03)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#f4f8fa")

    # 4大归并大区柔和色彩区分
    district_colors = {
        "中西区": "#fef9e7", "湾仔区": "#fef5e7", "东区": "#fdedec", "南区": "#fcf3cf", # 香港岛系
        "油尖旺区": "#ebf5fb", "深水埗区": "#e8f8f5", "九龙城区": "#eaf2f8", "黄大仙区": "#e8f6f3", "观塘区": "#d4efdf", # 九龙半岛系
        "荃湾区": "#f4ecf7", "葵青区": "#f5eef8", "屯门区": "#ebdef0", "元朗区": "#e8daef", # 新界西
        "北区": "#eafaf1", "大埔区": "#d5f5e3", "沙田区": "#d4efdf", "西贡区": "#d1f2eb", # 新界东
        "离岛区": "#fefde8", # 离岛
    }

    if sz_gdf is not None:
        sz_gdf.plot(ax=ax, facecolor="#eaeded", edgecolor="#bdc3c7", linewidth=0.8, linestyle="--", zorder=2)
        sx, sy = to_alb(114.08, 22.56)
        ax.text(sx, sy, "广东省深圳市 (Shenzhen)", fontsize=10.0, color="#95a5a6", fontweight="bold",
                ha="center", va="center", zorder=3)

    for idx, row in hk_all.iterrows():
        dname = row['name']
        c = district_colors.get(dname, "#fcf3cf")
        gpd.GeoSeries([row.geometry]).plot(ax=ax, facecolor=c, edgecolor="#7f8c8d", linewidth=0.6, zorder=3)
        # 注记各区中心
        pt = row.geometry.representative_point()
        ax.text(pt.x, pt.y, dname, fontsize=7.2, fontweight="bold", color="#2c3e50", ha="center", va="center", zorder=6,
                path_effects=[pe.withStroke(linewidth=2.0, foreground="white")])

    # 北部都会区规划红线示意区域 (元朗北/北区/落马洲河套)
    nm_box = ShpPolygon([(113.98, 22.46), (114.22, 22.46), (114.22, 22.55), (113.98, 22.55)])
    nm_alb = gpd.GeoSeries([nm_box], crs="EPSG:4326").to_crs(ALBERS).iloc[0]
    nm_clip = nm_alb.intersection(hk_union)
    gpd.GeoSeries([nm_clip]).plot(ax=ax, facecolor="#f39c12", alpha=0.18, edgecolor="#d35400", linewidth=1.5,
                                  linestyle="--", zorder=4)
    nx, ny = to_alb(114.10, 22.485)
    ax.text(nx, ny, "【北部都会区 Northern Metropolis 规划统揽区】\n深港融合前沿 · 新田科技城 · 现代产业新引擎",
            fontsize=8.5, fontweight="bold", color="#b9770e", ha="center", va="center", zorder=7,
            path_effects=[pe.withStroke(linewidth=2.5, foreground="white")])

    # 维港都会区核心圈示意
    vh_box = ShpPolygon([(114.13, 22.27), (114.22, 22.27), (114.22, 22.32), (114.13, 22.32)])
    vh_alb = gpd.GeoSeries([vh_box], crs="EPSG:4326").to_crs(ALBERS).iloc[0]
    gpd.GeoSeries([vh_alb]).plot(ax=ax, facecolor="#3498db", alpha=0.12, edgecolor="#2980b9", linewidth=1.2,
                                 linestyle=":", zorder=4)
    vx, vy = to_alb(114.175, 22.285)
    ax.text(vx, vy, "维港都会区 (Victoria Harbour Metropolis)\n国际金融中心 · 商业决策枢纽",
            fontsize=8.0, fontweight="bold", color="#1b4f72", ha="center", va="center", zorder=7,
            path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    add_compass(ax, 0.95, 0.92)
    mapkit.add_scalebar(ax, b[0] + span_x * 0.05, b[1] + span_y * 0.05, length_km=10)

    # 图例
    patches = [
        Patch(facecolor="#fef5e7", edgecolor="#7f8c8d", label="香港岛 4 区 (政治金融核心)"),
        Patch(facecolor="#ebf5fb", edgecolor="#7f8c8d", label="九龙半岛 5 区 (高密商住与高铁门户)"),
        Patch(facecolor="#eafaf1", edgecolor="#7f8c8d", label="新界大陆 8 区 (北部都会区主阵地)"),
        Patch(facecolor="#fefde8", edgecolor="#7f8c8d", label="离岛区 1 区 (海空超级大门户)"),
        Patch(facecolor="#f39c12", alpha=0.25, edgecolor="#d35400", linestyle="--", label="北部都会区规划辐射圈"),
    ]
    ax.legend(handles=patches, loc="upper left", bbox_to_anchor=(0.03, 0.96), fontsize=7.0, framealpha=0.92)

    ax.set_title("香港特别行政区18区行政区划与“南金融·北创科”空间战略格局图", fontsize=13.0, fontweight="bold", color=C_TEXT, pad=12)
    fig.text(0.5, 0.012, "数据来源：香港特区政府民政事务总署 · 发展局《北部都会区发展策略》 · 制作：《中国地理知识手册》",
             ha="center", fontsize=7.0, color="#7f8c8d")

    out_file = os.path.join(OUT_DIR, "fig27-00-2_香港特别行政区18区政区与北部都会区战略格局图.png")
    fig.savefig(out_file, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_file}")

# =============================================================================
# 图 3: 香港特别行政区综合立体交通网络与海空港口大通道图
# =============================================================================
def plot_fig3():
    print("Rendering fig27-00-3: Hong Kong comprehensive transport & international corridors...")
    fig, ax = plt.subplots(figsize=(10.5, 7.5), dpi=DPI)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.93, bottom=0.03)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#eaf2f8")

    if sz_gdf is not None:
        sz_gdf.plot(ax=ax, facecolor="#f2f3f4", edgecolor="#bdc3c7", linewidth=0.8, zorder=2)
    hk_all.plot(ax=ax, facecolor="#fefefe", edgecolor="#7f8c8d", linewidth=0.6, zorder=3)

    # 1. 港珠澳大桥 (55km 世纪工程)
    bridge_coords = [(113.88, 22.25), (113.92, 22.29), (113.955, 22.315)]
    b_pts = [to_alb(x, y) for x, y in bridge_coords]
    ax.plot([p[0] for p in b_pts], [p[1] for p in b_pts], color="#c0392b", lw=2.5, ls="--", zorder=7)
    bx, by = to_alb(113.92, 22.28)
    ax.text(bx - 1500, by - 1200, "港珠澳大桥 (HZMB)", fontsize=8.2, fontweight="bold", color="#922b21",
            zorder=8, path_effects=[pe.withStroke(linewidth=2, foreground="white")])

    # 2. 骨干铁路网络示意 (港铁东铁线、屯马线、机场快线、广深港高铁)
    xrl_line = [(114.165, 22.304), (114.150, 22.340), (114.100, 22.420), (114.070, 22.515)]
    x_pts = [to_alb(x, y) for x, y in xrl_line]
    ax.plot([p[0] for p in x_pts], [p[1] for p in x_pts], color="#8e44ad", lw=2.2, zorder=6)
    xx, xy = to_alb(114.12, 22.45)
    ax.text(xx + 1000, xy, "广深港高铁 (直通广州南/深圳北)", fontsize=7.8, fontweight="bold", color="#6c3483", zorder=8,
            path_effects=[pe.withStroke(linewidth=2, foreground="white")])

    # 机场快线
    ael_line = [(114.158, 22.282), (114.161, 22.305), (114.070, 22.352), (113.935, 22.290), (113.915, 22.308)]
    a_pts = [to_alb(x, y) for x, y in ael_line]
    ax.plot([p[0] for p in a_pts], [p[1] for p in a_pts], color="#16a085", lw=2.0, ls="-.", zorder=6)

    # 3. 超级海空国际枢纽
    # 香港国际机场
    air_x, air_y = to_alb(113.915, 22.308)
    ax.plot(air_x, air_y, marker="o", color="#2980b9", markersize=12, markeredgecolor="white", mew=1.2, zorder=10)
    ax.annotate("香港国际机场 (HKG)\n全球货运第一 · 4F级三跑道", xy=(air_x, air_y), xytext=(air_x - 12000, air_y + 4000),
                fontsize=8.0, fontweight="bold", color="#1b4f72",
                arrowprops=dict(arrowstyle="->", color="#1b4f72", lw=1.0), zorder=12,
                path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])

    # 葵青货柜码头
    port_x, port_y = to_alb(114.120, 22.335)
    ax.plot(port_x, port_y, marker="s", color="#d35400", markersize=10, markeredgecolor="white", mew=1.0, zorder=10)
    ax.annotate("葵青货柜码头\n24个深水泊位 · 国际航运中心", xy=(port_x, port_y), xytext=(port_x - 13000, port_y - 4500),
                fontsize=8.0, fontweight="bold", color="#a04000",
                arrowprops=dict(arrowstyle="->", color="#a04000", lw=1.0), zorder=12,
                path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])

    # 西九龙站
    xrl_x, xrl_y = to_alb(114.165, 22.304)
    ax.plot(xrl_x, xrl_y, marker="*", color="#e74c3c", markersize=13, markeredgecolor="white", mew=0.8, zorder=10)
    ax.text(xrl_x + 1200, xrl_y - 200, "香港西九龙站", fontsize=8.2, fontweight="bold", color="#900c3f", zorder=12,
            path_effects=[pe.withStroke(linewidth=2, foreground="white")])

    # 陆路各大口岸
    checkpoints = [
        ("罗湖口岸", 114.115, 22.528),
        ("落马洲/福田口岸", 114.070, 22.515),
        ("深圳湾口岸", 113.945, 22.502),
        ("香园围/莲塘口岸", 114.150, 22.555),
    ]
    for cp_name, c_lon, c_lat in checkpoints:
        cx, cy = to_alb(c_lon, c_lat)
        ax.plot(cx, cy, marker="D", color="#27ae60", markersize=6.0, markeredgecolor="white", mew=0.6, zorder=10)
        ax.text(cx + 800, cy + 200, cp_name, fontsize=7.2, fontweight="bold", color="#196f3d", zorder=12,
                path_effects=[pe.withStroke(linewidth=2, foreground="white")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    add_compass(ax, 0.95, 0.92)
    mapkit.add_scalebar(ax, b[0] + span_x * 0.05, b[1] + span_y * 0.05, length_km=10)

    # 图例
    lines = [
        Line2D([0], [0], color="#c0392b", lw=2.5, ls="--", label="港珠澳大桥跨海通道"),
        Line2D([0], [0], color="#8e44ad", lw=2.2, label="广深港高铁大动脉"),
        Line2D([0], [0], color="#16a085", lw=2.0, ls="-.", label="机场快线 / 港铁骨干线"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#2980b9", markersize=8, label="赤鱲角国际航空超级枢纽"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#d35400", markersize=8, label="葵青国际深水集装箱港"),
        Line2D([0], [0], marker="D", color="w", markerfacecolor="#27ae60", markersize=6, label="深港核心陆路通关口岸"),
    ]
    ax.legend(handles=lines, loc="upper left", bbox_to_anchor=(0.03, 0.96), fontsize=7.0, framealpha=0.92)

    ax.set_title("香港特别行政区综合立体交通网络与海空港口大通道图", fontsize=13.0, fontweight="bold", color=C_TEXT, pad=12)
    fig.text(0.5, 0.012, "数据来源：香港特区政府运输及物流局 · 香港机场管理局 · 制作：《中国地理知识手册》",
             ha="center", fontsize=7.0, color="#7f8c8d")

    out_file = os.path.join(OUT_DIR, "fig27-00-3_香港特别行政区综合立体交通网络与海空港口大通道图.png")
    fig.savefig(out_file, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_file}")

# =============================================================================
# 图 4: 香港特别行政区现代金融与创新科技产业空间分布图
# =============================================================================
def plot_fig4():
    print("Rendering fig27-00-4: Hong Kong finance & innovation industries...")
    fig, ax = plt.subplots(figsize=(10.5, 7.5), dpi=DPI)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.93, bottom=0.03)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#f9f9fb")

    if sz_gdf is not None:
        sz_gdf.plot(ax=ax, facecolor="#f2f3f4", edgecolor="#bdc3c7", linewidth=0.8, zorder=2)
    hk_all.plot(ax=ax, facecolor="#fefefe", edgecolor="#95a5a6", linewidth=0.6, zorder=3)

    # 绘制金融与创科重点基地
    clusters = [
        ("中环-金钟国际金融核心区\n(HKEX/顶级跨国投行/资产管理)", 114.158, 22.282, "#b03a2e", "finance"),
        ("西九龙现代服务与文旅集群\n(环球贸易广场ICC/西九文化区)", 114.161, 22.304, "#b03a2e", "finance"),
        ("港岛东商务副中心\n(太古坊/国际传媒与专业服务)", 114.210, 22.286, "#c0392b", "biz"),
        ("九龙东第二核心商业区(CBD2)\n(启德总部经济/观塘创贸中心)", 114.215, 22.315, "#c0392b", "biz"),
        ("薄扶林数码港 (Cyberport)\n(金融科技/人工智能/Web3.0)", 114.130, 22.260, "#2980b9", "tech"),
        ("白石角香港科学园 (HKSTP)\n(生命健康/微电子/AI研发基地)", 114.210, 22.430, "#2980b9", "tech"),
        ("河套港深创新及科技园 (HSITP)\n(深港一区两园·跨界协同创新极)", 114.075, 22.515, "#27ae60", "tech_core"),
        ("新田科技城规划核心区\n(新一代半导体与先导制造)", 114.060, 22.500, "#27ae60", "tech_core"),
        ("葵青国际航运物流园区\n(智能冷链/高价值航运物流)", 114.120, 22.335, "#d35400", "logistics"),
        ("机场航天城 (11 SKIES)\n(国际会展/零售商业综合体)", 113.935, 22.320, "#e67e22", "airport_biz"),
    ]

    for title, lon, lat, color, ctype in clusters:
        cx, cy = to_alb(lon, lat)
        is_large = ctype in ["finance", "tech_core"]
        ax.plot(cx, cy, marker="o" if "tech" in ctype else "s", color=color,
                markersize=9.0 if is_large else 7.0, markeredgecolor="white", mew=1.0, zorder=8)
        offset_y = 1000 if lat < 22.35 else -1200
        ax.text(cx + 800, cy + offset_y, title, fontsize=7.2, fontweight="bold", color="#1b2631", zorder=9,
                path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])

    ax.set_xlim(ax_xlim)
    ax.set_ylim(ax_ylim)
    add_compass(ax, 0.95, 0.92)
    mapkit.add_scalebar(ax, b[0] + span_x * 0.05, b[1] + span_y * 0.05, length_km=10)

    # 产业图例
    patches = [
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#b03a2e", markersize=8, label="国际金融中枢与CBD"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#c0392b", markersize=8, label="现代商贸副中心与新CBD2"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#2980b9", markersize=8, label="香港科学园/数码港科技孵化"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#27ae60", markersize=9, label="河套港深创科园/新田科技城"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="#d35400", markersize=8, label="国际航运物流与空港商务"),
    ]
    ax.legend(handles=patches, loc="upper left", bbox_to_anchor=(0.03, 0.96), fontsize=7.0, framealpha=0.92)

    ax.set_title("香港特别行政区现代金融与创新科技产业空间分布图", fontsize=13.0, fontweight="bold", color=C_TEXT, pad=12)
    fig.text(0.5, 0.012, "数据来源：香港特区政府创新科技及工业局 · 财经事务及库务局 · 制作：《中国地理知识手册》",
             ha="center", fontsize=7.0, color="#7f8c8d")

    out_file = os.path.join(OUT_DIR, "fig27-00-4_香港特别行政区现代金融与创新科技产业空间分布图.png")
    fig.savefig(out_file, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_file}")

# =============================================================================
# 图 5: 香港特别行政区2000-2024年经济跃升与深港协同对比图
# =============================================================================
def plot_fig5():
    print("Rendering fig27-00-5: Hong Kong GDP trajectory & Shenzhen-HK comparison...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 5.5), dpi=DPI)
    fig.subplots_adjust(left=0.06, right=0.95, top=0.88, bottom=0.12, wspace=0.28)

    # 左图：香港 2000-2024 年 GDP 稳步上升与人均指标
    years = [2000, 2005, 2010, 2015, 2020, 2024]
    hk_gdp_hkd = [13330, 14120, 17760, 24000, 27100, 31770]  # 亿港元
    hk_gdp_cny = [13330 * 1.06, 14120 * 1.04, 17760 * 0.87, 24000 * 0.81, 27100 * 0.89, 28900] # 折合亿元人民币

    bars = ax1.bar(years, [v/10000.0 for v in hk_gdp_cny], width=2.2, color="#b03a2e", edgecolor="#78281f",
                   alpha=0.88, label="GDP (万亿元人民币)")
    for bar in bars:
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2.0, h + 0.05, f"{h:.2f}万亿",
                 ha="center", va="bottom", fontsize=7.8, fontweight="bold", color="#78281f")

    ax1.set_title("香港特别行政区 2000—2024 年本地生产总值增长", fontsize=10.5, fontweight="bold", color=C_TEXT)
    ax1.set_ylabel("GDP (万亿元人民币)", fontsize=8.2, color="#2c3e50")
    ax1.set_xlabel("年份 Year", fontsize=8.2, color="#2c3e50")
    ax1.set_ylim(0, 3.6)
    ax1.grid(True, linestyle="--", alpha=0.4)
    ax1.tick_params(labelsize=7.5)

    # 右图：深港两地四项核心指标对比 (2024 年)
    # 面积 (km²)、人口 (万人)、GDP (亿元人民币)、机场客运量 (万人次)
    metrics = ["陆地面积\n(km²)", "常住人口\n(万人)", "GDP\n(亿元人民币)", "海港吞吐\n(万TEU)"]
    hk_vals = [1114, 753.4, 28900, 1369]
    sz_vals = [1997, 1778.9, 36802, 3339]

    x = np.arange(len(metrics))
    width = 0.35

    b1 = ax2.bar(x - width/2, hk_vals, width, label="香港特别行政区", color="#b03a2e", edgecolor="#78281f", alpha=0.88)
    b2 = ax2.bar(x + width/2, sz_vals, width, label="广东省深圳市", color="#2980b9", edgecolor="#1b4f72", alpha=0.88)

    for b in b1:
        h = b.get_height()
        ax2.text(b.get_x() + b.get_width() / 2.0, h * 1.02, f"{h:g}",
                 ha="center", va="bottom", fontsize=7.2, fontweight="bold", color="#78281f")
    for b in b2:
        h = b.get_height()
        ax2.text(b.get_x() + b.get_width() / 2.0, h * 1.02, f"{h:g}",
                 ha="center", va="bottom", fontsize=7.2, fontweight="bold", color="#1b4f72")

    ax2.set_title("深港“双城三圈” 2024 年四项核心指标协同对比", fontsize=10.5, fontweight="bold", color=C_TEXT)
    ax2.set_xticks(x)
    ax2.set_xticklabels(metrics, fontsize=8.0)
    ax2.set_yscale("log")
    ax2.set_ylabel("指标量值 (对数坐标 log scale)", fontsize=8.0, color="#2c3e50")
    ax2.grid(True, linestyle="--", alpha=0.4)
    ax2.legend(loc="upper left", fontsize=7.5)
    ax2.tick_params(labelsize=7.5)

    fig.suptitle("香港特别行政区 2000—2024 年经济稳步跃升与深港双城协同大格局", fontsize=12.5, fontweight="bold", color=C_TEXT)
    fig.text(0.5, 0.02, "数据来源：香港特区政府统计处 · 深圳市统计局《2024年统计公报》 · 制作：《中国地理知识手册》",
             ha="center", fontsize=7.2, color="#7f8c8d")

    out_file = os.path.join(OUT_DIR, "fig27-00-5_香港特别行政区2000-2024年经济跃升与深港协同对比图.png")
    fig.savefig(out_file, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_file}")

def main():
    plot_fig1()
    plot_fig2()
    plot_fig3()
    plot_fig4()
    plot_fig5()
    print("All 5 overview maps for Chapter 27 (Hong Kong) generated successfully!")

if __name__ == "__main__":
    main()
