# -*- coding: utf-8 -*-
"""重庆市市级地理统揽专题地图生成引擎（21-00）
包含 5 幅全市出版级权威地图与分析图表（精细调优排版、严格杜绝压盖）：
1. fig21-00-1_重庆市地势起伏与骨干河流水系格局图.png
2. fig21-00-2_重庆市38个区县行政区划与一区两群空间战略格局图.png
3. fig21-00-3_重庆市综合立体交通网络与国际物流大通道格局图.png
4. fig21-00-4_重庆市现代制造业万亿产业集群与战略性新兴产业空间分布图.png
5. fig21-00-5_重庆市1986-2024年夜间灯光演化与直辖开发强度对比图.png
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
from chongqing_configs import CHONGQING_OVERVIEW
from chongqing_district_configs import CHONGQING_DISTRICT_CONFIGS

setup()
OUT_DIR = os.path.join(BASE_DIR, "figures")
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

print("Loading Chongqing municipal boundaries and DEM...")
DATA_DIR = os.path.join(BASE_DIR, "data")
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

# 500000_full.json 包含全市 38 个区县
cq_all = gpd.read_file(os.path.join(DATAV_DIR, "500000_full.json")).to_crs(ALBERS)
cq_all["geometry"] = cq_all.geometry.buffer(0)
cq_union = cq_all.union_all()

b = cq_all.total_bounds
span_x = b[2] - b[0]
span_y = b[3] - b[1]
pad_x = span_x * 0.04
pad_y = span_y * 0.04
ax_xlim = (b[0] - pad_x, b[2] + pad_x)
ax_ylim = (b[1] - pad_y, b[3] + pad_y)

# 加载 DEM
dem_file = os.path.join(DATA_DIR, "dem", "province", "500000_z9.npz")
dem_data = np.load(dem_file)
step = 2
dem_raw = dem_data['dem'][::step, ::step]
res = float(dem_data['res']) * step
minx = float(dem_data['minx'])
maxy = float(dem_data['maxy'])
nrows, ncols = dem_raw.shape
dem_extent = [minx, minx + ncols * res, maxy - nrows * res, maxy]

# 处理水体负值与山阴
dem_elev = np.where(dem_raw < 0, np.nan, dem_raw)
hillshade = calc_hillshade(dem_elev, res)

terrain_cmap = LinearSegmentedColormap.from_list("cq_terrain", [
    (0.0, "#2e7d32"),   # 谷底沿江平坝 翠绿 (73m ~ 300m)
    (0.12, "#66bb6a"),  # 丘陵低阶地 浅绿 (300m ~ 600m)
    (0.25, "#d4e157"),  # 低山平行岭谷 浅黄绿 (600m ~ 900m)
    (0.42, "#ffd54f"),  # 中低山山岭 暖黄 (900m ~ 1300m)
    (0.62, "#ff8a65"),  # 喀斯特台原中山 橙褐 (1300m ~ 1800m)
    (0.82, "#a1887f"),  # 高山绝壁深谷 灰褐 (1800m ~ 2300m)
    (1.0, "#5d4037")    # 大巴山极顶 苍黑深褐 (2300m ~ 2797m)
])

# =========================================================================
# 1. 地势起伏与骨干河流水系格局图 (fig21-00-1)
# =========================================================================
print("Rendering fig21-00-1: Chongqing topography & river network...")
fig, ax = plt.subplots(figsize=(10.5, 8.8), dpi=DPI)
fig.patch.set_facecolor('#ffffff')
ax.set_facecolor('#f3f8fa')

# DEM 渲染
im_hs = ax.imshow(hillshade, extent=dem_extent, cmap='gray', origin='upper', alpha=0.35, zorder=2)
im_dem = ax.imshow(dem_elev, extent=dem_extent, cmap=terrain_cmap, origin='upper', vmin=73, vmax=2797, alpha=0.75, zorder=3)

# 边界裁剪
clip_patch = get_mpl_clip_patch(cq_union)
ax.add_patch(clip_patch)
im_hs.set_clip_path(clip_patch)
im_dem.set_clip_path(clip_patch)

# 矢量区县边界与全境外轮廓
cq_all.boundary.plot(ax=ax, edgecolor='#ffffff', linewidth=0.6, alpha=0.85, zorder=6)
gpd.GeoSeries([cq_union]).boundary.plot(ax=ax, edgecolor='#1a237e', linewidth=1.4, zorder=8)

# 标注骨干山峰与地貌极值
for name, lon, lat, ktype in CHONGQING_OVERVIEW["landmarks_macro"]:
    x, y = to_alb(lon, lat)
    if ktype == "peak_max":
        ax.plot(x, y, '^', color='#d50000', markersize=8.0, markeredgecolor='white', markeredgewidth=1.2, zorder=20)
        ax.text(x, y + 6000, name, fontsize=7.6, fontweight='bold', color='#b71c1c', ha='center',
                path_effects=[pe.withStroke(linewidth=2.2, foreground='white')], zorder=21)
    elif ktype == "peak":
        ax.plot(x, y, '^', color='#e65100', markersize=6.2, markeredgecolor='white', markeredgewidth=1.0, zorder=18)
        ax.text(x, y + 5000, name, fontsize=7.0, fontweight='bold', color='#4e342e', ha='center',
                path_effects=[pe.withStroke(linewidth=2.0, foreground='white')], zorder=19)
    else:
        ax.plot(x, y, 'o', color='#0277bd', markersize=5.0, markeredgecolor='white', markeredgewidth=0.8, zorder=16)
        ax.text(x, y - 5500, name, fontsize=6.8, fontweight='bold', color='#01579b', ha='center',
                path_effects=[pe.withStroke(linewidth=1.8, foreground='white')], zorder=17)

# 标注水系与峡谷
for rname, rlon, rlat, rkind in CHONGQING_OVERVIEW["rivers_macro"]:
    x, y = to_alb(rlon, rlat)
    if rkind == "river_main":
        ax.plot(x, y, 's', color='#0091ea', markersize=4.8, markeredgecolor='white', zorder=15)
        ax.text(x, y + 5000, rname, fontsize=7.4, fontweight='bold', color='#01579b', ha='center',
                path_effects=[pe.withStroke(linewidth=2.0, foreground='white')], zorder=16)
    elif rkind == "reservoir":
        ax.plot(x, y, 'D', color='#00b0ff', markersize=5.5, markeredgecolor='white', zorder=15)
        ax.text(x, y + 5500, rname, fontsize=7.4, fontweight='bold', color='#006064', ha='center',
                path_effects=[pe.withStroke(linewidth=2.0, foreground='white')], zorder=16)
    else:
        ax.text(x, y - 5000, rname, fontsize=6.8, color='#004d40', ha='center', style='italic',
                path_effects=[pe.withStroke(linewidth=1.8, foreground='white')], zorder=14)

# 最低点标注
lx, ly = to_alb(CHONGQING_OVERVIEW["elev_lowest"][1], CHONGQING_OVERVIEW["elev_lowest"][2])
ax.plot(lx, ly, 'v', color='#00b0ff', markersize=7.0, markeredgecolor='white', zorder=20)
ax.text(lx, ly - 6000, f"巫山培石长江谷底 (73.1m 市域最低点)", fontsize=7.0, fontweight='bold', color='#004d40', ha='center',
        path_effects=[pe.withStroke(linewidth=2.0, foreground='white')], zorder=21)

# 地质地貌说明看板
ax.text(0.03, 0.94, "重庆市巨型地质地貌骨架：\n川东平行岭谷（华蓥山、明月山、铜锣山、缙云山等）呈梳状紧密褶皱；\n北部大巴山与东部巫山高耸如屏，南部武陵山、大娄山喀斯特台原大观；\n万里长江自西南向东北贯通全境（691km），嘉陵江、乌江于此汇注，高峡平湖百里壮丽。",
        transform=ax.transAxes, fontsize=7.2, color='#263238', linespacing=1.35,
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#ffffff", edgecolor="#90a4ae", alpha=0.92), zorder=25)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.set_title("重庆市地势起伏与骨干河流水系格局图", fontsize=12.5, fontweight='bold', color='#1a237e', pad=12)
mapkit.add_scalebar(ax, ax_xlim[0] + pad_x * 0.8, ax_ylim[0] + pad_y * 0.8, length_km=50)
add_compass(ax, 0.94, 0.93)

# 颜色条
cbar_ax = fig.add_axes([0.16, 0.07, 0.35, 0.016])
norm = Normalize(vmin=73, vmax=2797)
cb = matplotlib.colorbar.ColorbarBase(cbar_ax, cmap=terrain_cmap, norm=norm, orientation='horizontal')
cb.set_label("数字高程模型 DEM (米)", fontsize=7.0, color='#263238', labelpad=4)
cb.ax.tick_params(labelsize=6.2)

f1_out = os.path.join(OUT_DIR, "fig21-00-1_重庆市地势起伏与骨干河流水系格局图.png")
plt.savefig(f1_out, dpi=DPI, bbox_inches='tight')
plt.close(fig)
print(f" Saved: {f1_out}")


# =========================================================================
# 2. 行政区划与“一区两群”空间战略格局图 (fig21-00-2)
# =========================================================================
print("Rendering fig21-00-2: Chongqing 38 districts & 1-Area-2-Clusters strategy...")
fig, ax = plt.subplots(figsize=(10.5, 8.8), dpi=DPI)
fig.patch.set_facecolor('#ffffff')
ax.set_facecolor('#fbfcfd')

# 四大战略板块分类：
# 1. 中心城区 (9区): 500103, 500104, 500105, 500106, 500107, 500108, 500109, 500112, 500113
# 2. 主城新区 (12区): 500102, 500110, 500111, 500115, 500116, 500117, 500118, 500119, 500120, 500151, 500152, 500153
# 3. 渝东北三峡库区城镇群 (11区县): 500101, 500154, 500155, 500229, 500230, 500231, 500233, 500235, 500236, 500237, 500238
# 4. 渝东南武陵山区城镇群 (6区县): 500114, 500156, 500240, 500241, 500242, 500243

def get_cq_zone(code_str):
    c = str(code_str)
    if c in ["500103", "500104", "500105", "500106", "500107", "500108", "500109", "500112", "500113"]:
        return "core", "#ffcdd2", "中心城区 (9区·引领极)"
    elif c in ["500102", "500110", "500111", "500115", "500116", "500117", "500118", "500119", "500120", "500151", "500152", "500153"]:
        return "new", "#ffe0b2", "主城新区 (12区·战略支点)"
    elif c in ["500101", "500154", "500155", "500229", "500230", "500231", "500233", "500235", "500236", "500237", "500238"]:
        return "northeast", "#b3e5fc", "渝东北三峡库区城镇群 (11区县)"
    else:
        return "southeast", "#c8e6c9", "渝东南武陵山区城镇群 (6区县)"

for idx, row in cq_all.iterrows():
    code_s = str(row['adcode'])
    z_id, z_col, z_lbl = get_cq_zone(code_s)
    gpd.GeoSeries([row.geometry]).plot(ax=ax, facecolor=z_col, edgecolor='#546e7a', linewidth=0.8, alpha=0.88, zorder=3)

# 边界强化
gpd.GeoSeries([cq_union]).boundary.plot(ax=ax, edgecolor='#0d47a1', linewidth=1.8, zorder=8)

# 标注 38 个区县驻地与名称
for code, conf in CHONGQING_DISTRICT_CONFIGS.items():
    gov_lon, gov_lat = 0, 0
    gov_found = False
    for p in conf.get("places_admin", []):
        if len(p) >= 6 and (p[5] == "gov" or "区委" in p[0] or "县委" in p[0]):
            gov_lon, gov_lat = p[1], p[2]
            gov_found = True
            break
    if not gov_found:
        # 使用多边形质心
        sub = cq_all[cq_all['adcode'].astype(str) == str(code)]
        if not sub.empty:
            c = sub.geometry.iloc[0].centroid
            gx, gy = c.x, c.y
        else:
            gx, gy = to_alb(106.55, 29.56)
    else:
        gx, gy = to_alb(gov_lon, gov_lat)

    d_name = conf["name"]
    # 标注点与文字
    ax.plot(gx, gy, 'o', color='#c62828', markersize=3.8, markeredgecolor='white', markeredgewidth=0.6, zorder=15)
    
    # 针对中心城区9区做防压盖偏移
    if code in ["500103", "500104", "500105", "500106", "500107", "500108"]:
        # 渝中、大渡口、江北、沙坪坝、九龙坡、南岸等高度密集
        offsets = {
            "500103": (-6000, 6000),   # 渝中
            "500104": (-8000, -6000),  # 大渡口
            "500105": (7000, 7000),    # 江北
            "500106": (-12000, 6000),  # 沙坪坝
            "500107": (-12000, -5000), # 九龙坡
            "500108": (8000, -6000)    # 南岸
        }
        dx, dy = offsets.get(code, (0, 4500))
        ax.text(gx + dx, gy + dy, d_name, fontsize=6.2, fontweight='bold', color='#1a237e', ha='center',
                path_effects=[pe.withStroke(linewidth=1.8, foreground='white')], zorder=16)
    else:
        ax.text(gx, gy + 4500, d_name, fontsize=6.6, fontweight='bold', color='#263238', ha='center',
                path_effects=[pe.withStroke(linewidth=1.8, foreground='white')], zorder=16)

# 图例
legend_elements = [
    Patch(facecolor="#ffcdd2", edgecolor="#c62828", label="中心城区 (9区·引领极核)"),
    Patch(facecolor="#ffe0b2", edgecolor="#e65100", label="主城新区 (12区·重要战略支点)"),
    Patch(facecolor="#b3e5fc", edgecolor="#0277bd", label="渝东北三峡库区城镇群 (11区县·生态优先发展)"),
    Patch(facecolor="#c8e6c9", edgecolor="#2e7d32", label="渝东南武陵山区城镇群 (6区县·文旅康养与绿色协同)"),
    Line2D([0], [0], color='#0d47a1', lw=1.8, label="重庆直辖市行政边界"),
    Line2D([0], [0], marker='o', color='w', markerfacecolor='#c62828', markersize=5, label="区县党委/人民政府驻地")
]
ax.legend(handles=legend_elements, loc='upper left', fontsize=7.2, framealpha=0.92,
          facecolor='#ffffff', edgecolor='#90a4ae', title="“一区两群”空间战略格局", title_fontsize=7.8)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.set_title("重庆市38个区县行政区划与“一区两群”空间战略格局图", fontsize=12.5, fontweight='bold', color='#1a237e', pad=12)
mapkit.add_scalebar(ax, ax_xlim[0] + pad_x * 0.8, ax_ylim[0] + pad_y * 0.8, length_km=50)
add_compass(ax, 0.94, 0.93)

f2_out = os.path.join(OUT_DIR, "fig21-00-2_重庆市38个区县行政区划与一区两群空间战略格局图.png")
plt.savefig(f2_out, dpi=DPI, bbox_inches='tight')
plt.close(fig)
print(f" Saved: {f2_out}")


# =========================================================================
# 3. 综合立体交通网络与国际物流大通道格局图 (fig21-00-3)
# =========================================================================
print("Rendering fig21-00-3: Chongqing comprehensive transport & logistics hubs...")
fig, ax = plt.subplots(figsize=(10.5, 8.8), dpi=DPI)
fig.patch.set_facecolor('#ffffff')
ax.set_facecolor('#f4f7f6')

# 区域底图
for idx, row in cq_all.iterrows():
    c = "#e8eaed"
    gpd.GeoSeries([row.geometry]).plot(ax=ax, facecolor=c, edgecolor='#b0bec5', linewidth=0.5, alpha=0.9, zorder=2)
gpd.GeoSeries([cq_union]).boundary.plot(ax=ax, edgecolor='#37474f', linewidth=1.4, zorder=5)

# 长江航道干线 (长江黄金水道示意)
river_pts = [
    (105.92, 29.15), (106.25, 29.29), (106.58, 29.56), (106.75, 29.63),
    (107.09, 29.82), (107.40, 29.72), (107.72, 29.87), (108.05, 30.30),
    (108.40, 30.80), (108.70, 30.92), (109.60, 31.04), (110.00, 31.06), (110.35, 31.05)
]
rx_list, ry_list = [], []
for p_lon, p_lat in river_pts:
    px, py = to_alb(p_lon, p_lat)
    rx_list.append(px)
    ry_list.append(py)
ax.plot(rx_list, ry_list, '-', color='#0288d1', linewidth=4.0, alpha=0.75, zorder=7)
ax.plot(rx_list, ry_list, '--', color='#e1f5fe', linewidth=1.2, alpha=0.9, zorder=8)

# 骨干铁路通道示意
# 1. 成渝高铁/成渝中线 (重庆中心 -> 璧山 -> 铜梁/大足 -> 荣昌/内江)
rail_cr = [(106.55, 29.56), (106.25, 29.57), (105.78, 29.48), (105.62, 29.44)]
cx, cy = mapkit.smooth_line([to_alb(x, y) for x, y in rail_cr])
ax.plot(cx, cy, '-.', color='#d32f2f', linewidth=2.5, zorder=9)

# 2. 郑渝高铁 (万州 -> 云阳 -> 奉节 -> 巫山 -> 襄阳/北京)
rail_zy = [(108.38, 30.85), (108.72, 30.96), (109.49, 31.06), (109.85, 31.10)]
zx, zy = mapkit.smooth_line([to_alb(x, y) for x, y in rail_zy])
ax.plot(zx, zy, '-.', color='#c2185b', linewidth=2.5, zorder=9)

# 3. 渝利/渝万高铁 (重庆中心 -> 长寿 -> 垫江/梁平 -> 万州)
rail_yw = [(106.55, 29.60), (107.06, 29.87), (107.32, 30.30), (107.76, 30.64), (108.38, 30.85)]
yx, yy = mapkit.smooth_line([to_alb(x, y) for x, y in rail_yw])
ax.plot(yx, yy, '-.', color='#7b1fa2', linewidth=2.2, zorder=9)

# 4. 渝怀铁路/渝湘高铁 (重庆中心 -> 南川 -> 武隆 -> 彭水 -> 黔江 -> 酉阳 -> 秀山)
rail_yx = [(106.65, 29.50), (107.11, 29.19), (107.76, 29.32), (108.18, 29.33), (108.79, 29.46), (109.03, 28.80), (109.02, 28.45)]
xx, xy = mapkit.smooth_line([to_alb(x, y) for x, y in rail_yx])
ax.plot(xx, xy, '-.', color='#1976d2', linewidth=2.2, zorder=9)

# 5. 西渝高铁通道 (重庆中心 -> 北碚/合川 -> 开州 -> 城口 -> 安康/西安)
rail_xy = [(106.55, 29.60), (106.44, 29.82), (108.43, 31.21), (108.65, 31.96)]
sx, sy = mapkit.smooth_line([to_alb(x, y) for x, y in rail_xy])
ax.plot(sx, sy, ':', color='#00796b', linewidth=2.2, zorder=9)

# 核心物流与综合交通枢纽标绘
hubs = [
    ("团结村铁路集装箱中心站 (中欧班列/西部陆海新通道策源港)", 106.340, 29.650, "rail_hub"),
    ("果园港国际物流枢纽 (长江上游铁水联运第一大港)", 106.750, 29.630, "port_hub"),
    ("重庆江北国际机场 (4F级双楼四跑道民航超级枢纽)", 106.640, 29.720, "airport_hub"),
    ("重庆东站高铁枢纽 (在建特大型铁路综合客运中枢)", 106.675, 29.475, "rail_hub"),
    ("重庆西站综合客运枢纽 (西南最大高铁客运站之一)", 106.430, 29.510, "rail_hub"),
    ("万州北站与新田港 (渝东北公铁水联运枢纽大港)", 108.360, 30.730, "port_hub"),
    ("万州五桥机场 (4C级三峡库区支线国际机场)", 108.435, 30.760, "airport"),
    ("黔江武陵山机场与黔江站 (渝东南综合交通中枢)", 108.810, 29.490, "airport"),
    ("巫山机场 (云端航母俯瞰长江三峡高峡平湖)", 109.920, 31.085, "airport"),
    ("武隆仙女山机场 (高山生态避暑旅游机场)", 107.755, 29.465, "airport"),
    ("涪陵龙头港 (乌江汇流千吨级铁公水联运大港)", 107.450, 29.760, "port_hub"),
    ("江津珞璜港 (西部陆海新通道骨干水运枢纽港)", 106.450, 29.295, "port_hub"),
    ("忠县新生港 (万吨级铁公水联运直达港)", 108.005, 30.360, "port_hub")
]

for name, lon, lat, k in hubs:
    x, y = to_alb(lon, lat)
    if "airport" in k:
        ax.plot(x, y, '^', color='#f57f17', markersize=8.0, markeredgecolor='white', markeredgewidth=1.2, zorder=20)
        ax.text(x, y + 5500, name, fontsize=7.2, fontweight='bold', color='#e65100', ha='center',
                path_effects=[pe.withStroke(linewidth=2.0, foreground='white')], zorder=21)
    elif "port" in k:
        ax.plot(x, y, 's', color='#0091ea', markersize=7.5, markeredgecolor='white', markeredgewidth=1.0, zorder=19)
        ax.text(x, y - 6000, name, fontsize=7.2, fontweight='bold', color='#01579b', ha='center',
                path_effects=[pe.withStroke(linewidth=2.0, foreground='white')], zorder=20)
    else:
        ax.plot(x, y, 'D', color='#d32f2f', markersize=7.0, markeredgecolor='white', markeredgewidth=1.0, zorder=19)
        ax.text(x, y + 5500, name, fontsize=7.2, fontweight='bold', color='#b71c1c', ha='center',
                path_effects=[pe.withStroke(linewidth=2.0, foreground='white')], zorder=20)

# 图例看板
legend_trans = [
    Line2D([0], [0], color='#0288d1', lw=3.5, label="长江黄金水道航道 (万吨级通航)"),
    Line2D([0], [0], color='#d32f2f', lw=2.2, linestyle='-.', label="成渝双城干线铁路 (成渝高铁/中线)"),
    Line2D([0], [0], color='#c2185b', lw=2.2, linestyle='-.', label="郑渝高铁大通道 (京郑渝昆)"),
    Line2D([0], [0], color='#7b1fa2', lw=2.2, linestyle='-.', label="渝万/渝利沿江高铁大动脉"),
    Line2D([0], [0], color='#1976d2', lw=2.2, linestyle='-.', label="渝怀/渝湘高铁大通道"),
    Line2D([0], [0], color='#00796b', lw=2.2, linestyle=':', label="西渝高铁大通道 (在建)"),
    Line2D([0], [0], marker='D', color='w', markerfacecolor='#d32f2f', markersize=6, label="特大型铁路集装箱/客运枢纽"),
    Line2D([0], [0], marker='s', color='w', markerfacecolor='#0091ea', markersize=6, label="国家级铁水公多式联运枢纽港"),
    Line2D([0], [0], marker='^', color='w', markerfacecolor='#f57f17', markersize=7, label="民用运输航空机场 (江北4F及支线)")
]
ax.legend(handles=legend_trans, loc='lower left', fontsize=7.0, framealpha=0.92,
          facecolor='#ffffff', edgecolor='#90a4ae', title="综合立体交通与物流通道", title_fontsize=7.6)

# 国际大通道说明框
ax.text(0.68, 0.94, "两核引领四大通道：\n1. 西部陆海新通道（重庆-钦州港-东盟全球）\n2. 中欧班列渝新欧（重庆-霍尔果斯-欧洲）\n3. 长江黄金水道铁水联运（果园港至江海直达）\n4. 国际空中走廊（江北国际机场四跑道国际货运）",
        transform=ax.transAxes, fontsize=6.8, color='#1a237e', linespacing=1.35,
        bbox=dict(boxstyle="round,pad=0.45", facecolor="#ffffff", edgecolor="#0d47a1", alpha=0.92), zorder=25)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.set_title("重庆市综合立体交通网络与国际物流大通道格局图", fontsize=12.5, fontweight='bold', color='#1a237e', pad=12)
mapkit.add_scalebar(ax, ax_xlim[0] + pad_x * 0.8, ax_ylim[0] + pad_y * 0.8, length_km=50)
add_compass(ax, 0.94, 0.93)

f3_out = os.path.join(OUT_DIR, "fig21-00-3_重庆市综合立体交通网络与国际物流大通道格局图.png")
plt.savefig(f3_out, dpi=DPI, bbox_inches='tight')
plt.close(fig)
print(f" Saved: {f3_out}")


# =========================================================================
# 4. 现代制造业万亿产业集群与特色产业空间分布图 (fig21-00-4)
# =========================================================================
print("Rendering fig21-00-4: Chongqing modern manufacturing clusters & industries...")
fig, ax = plt.subplots(figsize=(10.5, 8.8), dpi=DPI)
fig.patch.set_facecolor('#ffffff')
ax.set_facecolor('#fafaf9')

# 底图淡雅
for idx, row in cq_all.iterrows():
    c = "#eef2f3"
    gpd.GeoSeries([row.geometry]).plot(ax=ax, facecolor=c, edgecolor='#cfd8dc', linewidth=0.6, alpha=0.9, zorder=2)
gpd.GeoSeries([cq_union]).boundary.plot(ax=ax, edgecolor='#37474f', linewidth=1.5, zorder=5)

# 战略性支柱与现代特色产业高地
ind_nodes = [
    ("两江新区国家级智能网联新能源汽车与芯片研发制造极", 106.600, 29.680, "auto_tech"),
    ("西部（重庆）科学城·西永微电园与金凤实验室", 106.320, 29.580, "science"),
    ("璧山比亚迪刀片电池生产超级基地 (动力电池之都)", 106.260, 29.510, "battery"),
    ("永川长城汽车西南基地与智能网联自动驾驶试验区", 106.015, 29.380, "auto_tech"),
    ("长寿经开区综合化工与万亿级绿色新材料高地", 107.015, 29.835, "material"),
    ("涪陵百亿方页岩气田与华峰高分子新材料基地", 107.550, 29.600, "energy"),
    ("万州经开区绿色先进材料与三峡智能装备基地", 108.320, 30.750, "material"),
    ("九龙坡西南铝业 (中国航空航天先进铝合金之都)", 106.320, 29.320, "material"),
    ("江津珞璜综合保税区装备制造与粮油加工港", 106.435, 29.290, "logistics"),
    ("巴南国际生物医药城 (智飞生物国家医药集群)", 106.865, 29.560, "pharma"),
    ("荣昌国家生猪大数据中心与国家农高区", 105.615, 29.425, "agri"),
    ("铜梁海辰储能西南超级工厂 (新型储能示范高地)", 106.090, 29.860, "battery"),
    ("大足石刻与龙水五金博览中心 (世界文旅与五金名都)", 105.780, 29.720, "heritage"),
    ("武隆喀斯特世界自然遗产文旅产业极", 107.800, 29.430, "heritage"),
    ("奉节脐橙与白帝城三峡之巅文旅区", 109.560, 31.060, "agri"),
    ("石柱中国黄连中药材交易基地与康养森林", 108.435, 30.275, "pharma"),
    ("黔江濯水世界第一风雨廊桥文旅聚集区", 108.770, 29.325, "heritage"),
    ("彭水蚩尤九黎城与阿依河苗乡文旅产业", 108.160, 29.230, "heritage"),
    ("云阳环湖绿道与世界级恐龙化石地质长廊", 108.700, 30.850, "heritage"),
    ("忠县新生港万吨级枢纽与三峡橘乡综合体", 108.010, 30.340, "agri")
]

# 符号分类映射
ind_colors = {
    "auto_tech": ("#d32f2f", 'h', "智能网联新能源汽车"),
    "science": ("#7b1fa2", 'p', "新一代电子信息/科学城研发"),
    "battery": ("#f57f17", 'D', "新能源动力电池与新型储能"),
    "material": ("#0288d1", 's', "先进材料与绿色化工"),
    "energy": ("#00897b", 'o', "国家级清洁能源与页岩气"),
    "pharma": ("#43a047", 'v', "生物医药与大健康产业"),
    "agri": ("#8d6e63", '*', "现代山地特色高效农业/大数据"),
    "heritage": ("#e64a19", '^', "世界级文旅遗产与现代服务业"),
    "logistics": ("#3949ab", 'P', "现代临港装备与综合保税")
}

for name, lon, lat, k in ind_nodes:
    x, y = to_alb(lon, lat)
    col, mk, lbl = ind_colors.get(k, ("#263238", 'o', "其他"))
    ax.plot(x, y, marker=mk, color=col, markersize=8.0, markeredgecolor='white', markeredgewidth=1.2, zorder=18)
    ax.text(x, y + 5500, name, fontsize=6.8, fontweight='bold', color='#263238', ha='center',
            path_effects=[pe.withStroke(linewidth=2.0, foreground='white')], zorder=19)

# 现代制造业“33618”集群产业看板
ax.text(0.03, 0.94, "重庆市“33618”现代制造业集群体系：\n三大万亿级主导产业：智能网联新能源汽车、新一代电子信息制造业、先进材料；\n三大五千亿级支柱产业：智能装备及智能制造、食品及农产品加工、软件信息服务；\n六大千亿级特色优势产业与十八个高成长性未来产业集群协同共进。",
        transform=ax.transAxes, fontsize=7.0, color='#1a237e', linespacing=1.35,
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#ffffff", edgecolor="#1a237e", alpha=0.92), zorder=25)

# 图例
legend_ind = [
    Line2D([0], [0], marker='h', color='w', markerfacecolor='#d32f2f', markersize=7.5, label="智能网联新能源汽车产业"),
    Line2D([0], [0], marker='p', color='w', markerfacecolor='#7b1fa2', markersize=7.5, label="新一代电子信息制造业/科学城"),
    Line2D([0], [0], marker='D', color='w', markerfacecolor='#f57f17', markersize=7.0, label="动力电池与新型储能基地"),
    Line2D([0], [0], marker='s', color='w', markerfacecolor='#0288d1', markersize=7.0, label="先进材料与绿色综合化工"),
    Line2D([0], [0], marker='o', color='w', markerfacecolor='#00897b', markersize=7.0, label="国家页岩气清洁能源基地"),
    Line2D([0], [0], marker='v', color='w', markerfacecolor='#43a047', markersize=7.0, label="生物医药与高端健康产业"),
    Line2D([0], [0], marker='*', color='w', markerfacecolor='#8d6e63', markersize=8.5, label="国家级现代农业/生猪大数据"),
    Line2D([0], [0], marker='^', color='w', markerfacecolor='#e64a19', markersize=8.0, label="世界遗产与巴渝文旅产业极")
]
ax.legend(handles=legend_ind, loc='lower left', fontsize=6.8, framealpha=0.92,
          facecolor='#ffffff', edgecolor='#90a4ae', title="“33618”现代产业集群分类", title_fontsize=7.4)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.set_title("重庆市现代制造业万亿产业集群与战略性新兴产业空间分布图", fontsize=12.5, fontweight='bold', color='#1a237e', pad=12)
mapkit.add_scalebar(ax, ax_xlim[0] + pad_x * 0.8, ax_ylim[0] + pad_y * 0.8, length_km=50)
add_compass(ax, 0.94, 0.93)

f4_out = os.path.join(OUT_DIR, "fig21-00-4_重庆市现代制造业万亿产业集群与战略性新兴产业空间分布图.png")
plt.savefig(f4_out, dpi=DPI, bbox_inches='tight')
plt.close(fig)
print(f" Saved: {f4_out}")


# =========================================================================
# 5. 1986-2024年夜间灯光演化与直辖开发强度对比图 (fig21-00-5)
# =========================================================================
print("Rendering fig21-00-5: Chongqing nightlight evolution & development intensity...")
nl_clean_file = os.path.join(DATA_DIR, "chongqing_nightlight_clean.csv")
df_nl = pd.read_csv(nl_clean_file)

# 计算全市每年总量
df_sum = df_nl.groupby('year')['sum'].sum().reset_index()

fig = plt.figure(figsize=(12.0, 7.5), dpi=DPI)
fig.patch.set_facecolor('#ffffff')

# Subplot 1: 1986-2024年重庆市域夜光辐射总量时序折线图
ax1 = fig.add_axes([0.08, 0.55, 0.88, 0.38], facecolor='#fafbfc')
ax1.plot(df_sum['year'], df_sum['sum'] / 1000.0, 'o-', color='#1565c0', linewidth=2.2, markersize=5.0,
         markeredgecolor='white', markeredgewidth=1.0, label='重庆市域夜间灯光辐射总量 (×10³ DN)')
ax1.fill_between(df_sum['year'], 0, df_sum['sum'] / 1000.0, color='#90caf9', alpha=0.35)

# 历史重大节点标注
events = [
    (1997, 28.0, "1997 重庆恢复设立中央直辖市"),
    (2003, 58.0, "2003 三峡工程蓄水135米库区初成"),
    (2010, 115.0, "2010 两江新区获批首个内陆国家级新区"),
    (2017, 168.0, "2017 中新互联互通·西部陆海新通道开通"),
    (2020, 205.0, "2020 成渝地区双城经济圈上升国家战略")
]
for yr, ypos, elbl in events:
    ax1.axvline(x=yr, color='#d32f2f', linestyle='--', linewidth=1.0, alpha=0.7)
    ax1.annotate(elbl, xy=(yr, ypos), xytext=(yr + 0.4, ypos + 12),
                 fontsize=6.8, fontweight='bold', color='#b71c1c',
                 arrowprops=dict(arrowstyle="->", color='#d32f2f', lw=0.9),
                 bbox=dict(boxstyle="round,pad=0.3", facecolor="#ffffff", edgecolor="#ffcdd2", alpha=0.92))

ax1.set_ylabel("夜光总量 (×10³ DN)", fontsize=7.8, color='#263238')
ax1.set_title("重庆市 1986—2024 年夜间灯光总辐射量演化与直辖战略腾飞节点", fontsize=10.5, fontweight='bold', color='#1a237e', pad=8)
ax1.grid(True, linestyle=':', alpha=0.6)
ax1.legend(loc='upper left', fontsize=7.5)
ax1.set_xlim(1985, 2025)

# Subplot 2: 38 个区县 2024 年夜光辐射总量梯队对比柱状图
ax2 = fig.add_axes([0.08, 0.10, 0.88, 0.36], facecolor='#fafbfc')

# 提取最新年份（2013 或 2024）各区县数据
max_yr = df_nl['year'].max()
df_recent = df_nl[df_nl['year'] == max_yr].sort_values(by='sum', ascending=False)

# 上色规则：四大板块不同色彩
colors_bar = []
for idx, r in df_recent.iterrows():
    c_str = str(int(float(r['unit_code'])))
    _, col, _ = get_cq_zone(c_str)
    colors_bar.append(col)

bars = ax2.bar(range(len(df_recent)), df_recent['sum'], color=colors_bar, edgecolor='#455a64', linewidth=0.6, width=0.75)
ax2.set_xticks(range(len(df_recent)))
ax2.set_xticklabels(df_recent['unit_name'], rotation=65, ha='right', fontsize=6.2)
ax2.set_ylabel("夜间灯光辐射总值 (DN)", fontsize=7.8, color='#263238')
ax2.set_title(f"重庆市 38 个区县夜间灯光辐射总量横向梯队对比（红:中心城区 黄:主城新区 蓝:渝东北 绿:渝东南）",
              fontsize=9.5, fontweight='bold', color='#1a237e', pad=6)
ax2.grid(axis='y', linestyle=':', alpha=0.6)

f5_out = os.path.join(OUT_DIR, "fig21-00-5_重庆市1986-2024年夜间灯光演化与直辖开发强度对比图.png")
plt.savefig(f5_out, dpi=DPI, bbox_inches='tight')
plt.close(fig)
print(f" Saved: {f5_out}")

print("\n=== ALL 5 CHONGQING OVERVIEW FIGURES SUCCESSFULLY GENERATED ===")
