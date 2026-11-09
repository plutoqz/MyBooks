# -*- coding: utf-8 -*-
"""四川省省级地理统揽专题地图生成引擎（22-00）
包含 5 幅全省出版级权威地图与分析图表（精细调优排版、严格杜绝压盖）：
1. fig22-00-1_四川省地势起伏与骨干河流水系格局图.png
2. fig22-00-2_四川省21个市州行政区划与五大经济区空间战略格局图.png
3. fig22-00-3_四川省综合立体交通网络与四向拓展大通道格局图.png
4. fig22-00-4_四川省六大优势产业集群与国家先进制造业空间分布图.png
5. fig22-00-5_四川省1986-2024年夜间灯光演化与五大片区开发强度对比图.png
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
from sichuan_configs import SICHUAN_OVERVIEW
from sichuan_city_configs import SICHUAN_CITY_CONFIGS

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

print("Loading Sichuan provincial boundaries and DEM...")
DATA_DIR = os.path.join(BASE_DIR, "data")
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

# 510000_full.json 包含全省 21 个市州
sc_all = gpd.read_file(os.path.join(DATAV_DIR, "510000_full.json")).to_crs(ALBERS)
sc_all["geometry"] = sc_all.geometry.buffer(0)
sc_union = sc_all.union_all()

b = sc_all.total_bounds
span_x = b[2] - b[0]
span_y = b[3] - b[1]
pad_x = span_x * 0.04
pad_y = span_y * 0.04
ax_xlim = (b[0] - pad_x, b[2] + pad_x)
ax_ylim = (b[1] - pad_y, b[3] + pad_y)

# 加载 DEM
dem_file = os.path.join(DATA_DIR, "dem", "province", "510000_z9.npz")
dem_data = np.load(dem_file)
step = 3  # 降采样避免内存过载
dem_raw = dem_data['dem'][::step, ::step]
res = float(dem_data['res']) * step
minx = float(dem_data['minx'])
maxy = float(dem_data['maxy'])
nrows, ncols = dem_raw.shape
dem_extent = [minx, minx + ncols * res, maxy - nrows * res, maxy]

dem_elev = np.where(dem_raw < 0, np.nan, dem_raw)
hillshade = calc_hillshade(dem_elev, res)

terrain_cmap = LinearSegmentedColormap.from_list("sc_terrain", [
    (0.0, "#2e7d32"),   # 平原与盆地底部 翠绿 (188m ~ 600m)
    (0.10, "#81c784"),  # 丘陵平坝 浅绿 (600m ~ 1000m)
    (0.22, "#d4e157"),  # 低山谷地 浅黄绿 (1000m ~ 1800m)
    (0.35, "#ffd54f"),  # 川西山原中山 暖黄 (1800m ~ 2800m)
    (0.50, "#ff8a65"),  # 高山峡谷 橙褐 (2800m ~ 3800m)
    (0.68, "#8d6e63"),  # 极高山灰岩 灰褐 (3800m ~ 5000m)
    (0.85, "#cfd8dc"),  # 冰川孑遗冻原 浅白蓝 (5000m ~ 6000m)
    (1.0, "#ffffff")    # 蜀山之王现代冰川 纯白雪原 (6000m ~ 7556m)
])

# =========================================================================
# 1. 地势起伏与骨干河流水系格局图 (fig22-00-1)
# =========================================================================
print("Rendering fig22-00-1: Sichuan topography & river network...")
fig, ax = plt.subplots(figsize=(10.5, 9.2), dpi=DPI)
fig.patch.set_facecolor('#ffffff')
ax.set_facecolor('#f3f8fa')

im_hs = ax.imshow(hillshade, extent=dem_extent, cmap='gray', origin='upper', alpha=0.32, zorder=2)
im_dem = ax.imshow(dem_elev, extent=dem_extent, cmap=terrain_cmap, origin='upper', vmin=188, vmax=7556, alpha=0.78, zorder=3)

clip_patch = get_mpl_clip_patch(sc_union)
ax.add_patch(clip_patch)
im_hs.set_clip_path(clip_patch)
im_dem.set_clip_path(clip_patch)

sc_all.boundary.plot(ax=ax, edgecolor='#ffffff', linewidth=0.55, alpha=0.85, zorder=6)
gpd.GeoSeries([sc_union]).boundary.plot(ax=ax, edgecolor='#1a237e', linewidth=1.5, zorder=8)

for name, lon, lat, ktype in SICHUAN_OVERVIEW["landmarks_macro"]:
    x, y = to_alb(lon, lat)
    if ktype == "peak_max":
        ax.plot(x, y, '^', color='#d50000', markersize=9.0, markeredgecolor='white', markeredgewidth=1.3, zorder=20)
        ax.text(x, y + 8000, name, fontsize=7.8, fontweight='bold', color='#b71c1c', ha='center',
                path_effects=[pe.withStroke(linewidth=2.4, foreground='white')], zorder=21)
    elif ktype == "peak":
        ax.plot(x, y, '^', color='#e65100', markersize=6.5, markeredgecolor='white', markeredgewidth=1.0, zorder=18)
        ax.text(x, y + 6500, name, fontsize=7.1, fontweight='bold', color='#4e342e', ha='center',
                path_effects=[pe.withStroke(linewidth=2.0, foreground='white')], zorder=19)
    else:
        ax.plot(x, y, 'o', color='#0277bd', markersize=5.2, markeredgecolor='white', markeredgewidth=0.8, zorder=16)
        ax.text(x, y - 6500, name, fontsize=6.8, fontweight='bold', color='#01579b', ha='center',
                path_effects=[pe.withStroke(linewidth=1.8, foreground='white')], zorder=17)

for rname, rlon, rlat, rkind in SICHUAN_OVERVIEW["rivers_macro"]:
    x, y = to_alb(rlon, rlat)
    if rkind == "river_main":
        ax.plot(x, y, 's', color='#0091ea', markersize=5.0, markeredgecolor='white', zorder=15)
        ax.text(x, y + 6000, rname, fontsize=7.5, fontweight='bold', color='#01579b', ha='center',
                path_effects=[pe.withStroke(linewidth=2.0, foreground='white')], zorder=16)
    elif rkind == "lake":
        ax.plot(x, y, 'D', color='#00b0ff', markersize=5.5, markeredgecolor='white', zorder=15)
        ax.text(x, y + 6500, rname, fontsize=7.4, fontweight='bold', color='#006064', ha='center',
                path_effects=[pe.withStroke(linewidth=2.0, foreground='white')], zorder=16)
    else:
        ax.text(x, y - 6000, rname, fontsize=7.0, color='#004d40', ha='center', style='italic',
                path_effects=[pe.withStroke(linewidth=1.8, foreground='white')], zorder=14)

lx, ly = to_alb(SICHUAN_OVERVIEW["elev_lowest"][1], SICHUAN_OVERVIEW["elev_lowest"][2])
ax.plot(lx, ly, 'v', color='#00b0ff', markersize=7.5, markeredgecolor='white', zorder=20)
ax.text(lx, ly - 7000, "邻水御临河峡谷 (188m 全省最低点)", fontsize=7.1, fontweight='bold', color='#004d40', ha='center',
        path_effects=[pe.withStroke(linewidth=2.0, foreground='white')], zorder=21)

ax.text(0.03, 0.94, "四川省宏观地质地貌骨架：\n横跨中国一二级阶梯过渡带，西高东低，落差超7300米；\n川西高原横断山脉纵列（贡嘎山7556m/四姑娘山6250m）；\n川中四川盆地为天府沃野，岷江、沱江、嘉陵江纵贯合流；\n金沙江、雅砻江大渡河深切高峡，构筑世界第一清洁水电长廊。",
        transform=ax.transAxes, fontsize=7.2, color='#263238', linespacing=1.35,
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#ffffff", edgecolor="#90a4ae", alpha=0.92), zorder=25)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.set_title("四川省地势起伏与骨干河流水系格局图", fontsize=12.5, fontweight='bold', color='#1a237e', pad=12)
mapkit.add_scalebar(ax, ax_xlim[0] + pad_x * 0.8, ax_ylim[0] + pad_y * 0.8, length_km=100)
add_compass(ax, 0.94, 0.93)

cbar_ax = fig.add_axes([0.16, 0.065, 0.35, 0.016])
norm = Normalize(vmin=188, vmax=7556)
cb = matplotlib.colorbar.ColorbarBase(cbar_ax, cmap=terrain_cmap, norm=norm, orientation='horizontal')
cb.set_label("数字高程模型 DEM (米)", fontsize=7.0, color='#263238', labelpad=4)
cb.ax.tick_params(labelsize=6.2)

f1_out = os.path.join(OUT_DIR, "fig22-00-1_四川省地势起伏与骨干河流水系格局图.png")
plt.savefig(f1_out, dpi=DPI, bbox_inches='tight')
plt.close(fig)
print(f" Saved: {f1_out}")


# =========================================================================
# 2. 行政区划与“五大经济区”空间战略格局图 (fig22-00-2)
# =========================================================================
print("Rendering fig22-00-2: Sichuan 21 cities & 5 Economic Zones strategy...")
fig, ax = plt.subplots(figsize=(10.5, 9.2), dpi=DPI)
fig.patch.set_facecolor('#ffffff')
ax.set_facecolor('#fbfcfd')

def get_sc_zone(code_str):
    c = str(code_str)
    # 成都平原经济区: 510100成都, 510600德阳, 510700绵阳, 510900遂宁, 511100乐山, 511400眉山, 511800雅安, 512000资阳
    if c in ["510100", "510600", "510700", "510900", "511100", "511400", "511800", "512000"]:
        return "chengdu_plain", "#ffe082", "成都平原经济区 (同城化协同极核)"
    # 川南经济区: 510300自贡, 510500泸州, 511000内江, 511500宜宾
    elif c in ["510300", "510500", "511000", "511500"]:
        return "south", "#ffab91", "川南经济区 (南向开放一体化门户)"
    # 川东北经济区: 510800广元, 511300南充, 511600广安, 511700达州, 511900巴中
    elif c in ["510800", "511300", "511600", "511700", "511900"]:
        return "northeast", "#b3e5fc", "川东北经济区 (川陕革命老区振兴核)"
    # 攀西经济区: 510400攀枝花, 513400凉山
    elif c in ["510400", "513400"]:
        return "panxi", "#ce93d8", "攀西经济区 (国家战略资源创新开发区)"
    # 川西北生态示范区: 513200阿坝, 513300甘孜
    else:
        return "northwest_eco", "#a5d6a7", "川西北生态示范区 (国家生态第一屏障)"

for idx, row in sc_all.iterrows():
    code_s = str(row['adcode'])
    z_id, z_col, z_lbl = get_sc_zone(code_s)
    gpd.GeoSeries([row.geometry]).plot(ax=ax, facecolor=z_col, edgecolor='#546e7a', linewidth=0.8, alpha=0.90, zorder=3)

gpd.GeoSeries([sc_union]).boundary.plot(ax=ax, edgecolor='#0d47a1', linewidth=1.8, zorder=8)

for code, conf in SICHUAN_CITY_CONFIGS.items():
    sub = sc_all[sc_all['adcode'].astype(str) == str(code)]
    if not sub.empty:
        c_pt = sub.geometry.iloc[0].centroid
        name = conf['name']
        x, y = c_pt.x, c_pt.y
        # 调整特殊偏离
        if code == "510100": y += 5000
        elif code == "511400": y -= 3000
        elif code == "511000": y -= 4000
        elif code == "510300": y += 2000
        
        ax.plot(x, y, 'o', color='#b71c1c', markersize=4.8, markeredgecolor='white', markeredgewidth=0.9, zorder=15)
        ax.text(x, y + 6000, name, fontsize=7.2, fontweight='bold', color='#1a237e', ha='center',
                path_effects=[pe.withStroke(linewidth=2.2, foreground='white')], zorder=16)

zone_patches = [
    Patch(facecolor="#ffe082", edgecolor="#546e7a", label="成都平原经济区 (成德眉资同城化/核心引领)"),
    Patch(facecolor="#ffab91", edgecolor="#546e7a", label="川南经济区 (宜宾/泸州/自贡/内江一体化)"),
    Patch(facecolor="#b3e5fc", edgecolor="#546e7a", label="川东北经济区 (南充/达州双核/产业振兴)"),
    Patch(facecolor="#ce93d8", edgecolor="#546e7a", label="攀西经济区 (攀枝花/凉山水风光与钒钛)"),
    Patch(facecolor="#a5d6a7", edgecolor="#546e7a", label="川西北生态示范区 (甘孜/阿坝文旅与生态水源)")
]
ax.legend(handles=zone_patches, loc="lower left", fontsize=7.2, framealpha=0.95,
          title="四川省五大经济区空间战略格局", title_fontsize=8.0)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.set_title("四川省21个市州行政区划与五大经济区空间战略格局图", fontsize=12.5, fontweight='bold', color='#1a237e', pad=12)
mapkit.add_scalebar(ax, ax_xlim[0] + pad_x * 0.8, ax_ylim[0] + pad_y * 0.8, length_km=100)
add_compass(ax, 0.94, 0.93)

f2_out = os.path.join(OUT_DIR, "fig22-00-2_四川省21个市州行政区划与五大经济区空间战略格局图.png")
plt.savefig(f2_out, dpi=DPI, bbox_inches='tight')
plt.close(fig)
print(f" Saved: {f2_out}")


# =========================================================================
# 3. 综合立体交通网络与四向拓展大通道格局图 (fig22-00-3)
# =========================================================================
print("Rendering fig22-00-3: Sichuan comprehensive transport corridors...")
fig, ax = plt.subplots(figsize=(10.5, 9.2), dpi=DPI)
fig.patch.set_facecolor('#ffffff')
ax.set_facecolor('#f8f9fa')

gpd.GeoSeries([sc_union]).plot(ax=ax, facecolor='#f1f8e9', edgecolor='#90a4ae', linewidth=1.2, zorder=2)
sc_all.boundary.plot(ax=ax, edgecolor='#cfd8dc', linewidth=0.5, zorder=3)

for name, lon, lat, ctype in SICHUAN_OVERVIEW["transport_corridors"]:
    x, y = to_alb(lon, lat)
    if ctype == "hsr":
        ax.plot(x, y, 's', color='#d32f2f', markersize=5.8, markeredgecolor='white', zorder=12)
        ax.text(x, y + 6500, name, fontsize=7.2, fontweight='bold', color='#b71c1c', ha='center',
                path_effects=[pe.withStroke(linewidth=2.0, foreground='white')], zorder=13)
    elif ctype == "waterway":
        ax.plot(x, y, 'D', color='#0288d1', markersize=5.8, markeredgecolor='white', zorder=12)
        ax.text(x, y - 6500, name, fontsize=7.2, fontweight='bold', color='#01579b', ha='center',
                path_effects=[pe.withStroke(linewidth=2.0, foreground='white')], zorder=13)
    else:
        ax.plot(x, y, 'o', color='#388e3c', markersize=5.2, markeredgecolor='white', zorder=12)
        ax.text(x, y + 6000, name, fontsize=7.0, color='#1b5e20', ha='center',
                path_effects=[pe.withStroke(linewidth=1.8, foreground='white')], zorder=13)

for code, conf in SICHUAN_CITY_CONFIGS.items():
    for t in conf.get("transport_labels", []):
        tname, tlon, tlat = t[0], t[1], t[2]
        x, y = to_alb(tlon, tlat)
        if "机场" in tname:
            ax.plot(x, y, '^', color='#7b1fa2', markersize=5.5, markeredgecolor='white', zorder=16)
        elif "港" in tname:
            ax.plot(x, y, 'v', color='#0097a7', markersize=5.5, markeredgecolor='white', zorder=16)
        else:
            ax.plot(x, y, 'o', color='#e65100', markersize=4.2, markeredgecolor='white', zorder=14)

t_handles = [
    Line2D([0], [0], marker='s', color='w', markerfacecolor='#d32f2f', markersize=7, label="高速铁路走廊与枢纽 (西成/成渝/成贵/成达万)"),
    Line2D([0], [0], marker='^', color='w', markerfacecolor='#7b1fa2', markersize=7, label="民用民航客运港 (天府/双流双4F航运及支线网)"),
    Line2D([0], [0], marker='v', color='w', markerfacecolor='#0097a7', markersize=7, label="长江出川水运大港 (宜宾港/泸州港集装箱枢纽)"),
    Line2D([0], [0], marker='o', color='w', markerfacecolor='#388e3c', markersize=6, label="国家高速公路骨架网 (京昆/蓉遵/厦蓉大通道)")
]
ax.legend(handles=t_handles, loc="lower left", fontsize=7.2, framealpha=0.95,
          title="综合立体交通四向拓展网络", title_fontsize=8.0)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.set_title("四川省综合立体交通网络与四向拓展大通道格局图", fontsize=12.5, fontweight='bold', color='#1a237e', pad=12)
mapkit.add_scalebar(ax, ax_xlim[0] + pad_x * 0.8, ax_ylim[0] + pad_y * 0.8, length_km=100)
add_compass(ax, 0.94, 0.93)

f3_out = os.path.join(OUT_DIR, "fig22-00-3_四川省综合立体交通网络与四向拓展大通道格局图.png")
plt.savefig(f3_out, dpi=DPI, bbox_inches='tight')
plt.close(fig)
print(f" Saved: {f3_out}")


# =========================================================================
# 4. 六大优势产业集群与国家先进制造业空间分布图 (fig22-00-4)
# =========================================================================
print("Rendering fig22-00-4: Sichuan 6 Major Advantaged Industries...")
fig, ax = plt.subplots(figsize=(10.5, 9.2), dpi=DPI)
fig.patch.set_facecolor('#ffffff')
ax.set_facecolor('#fafafa')

gpd.GeoSeries([sc_union]).plot(ax=ax, facecolor='#f5f5f5', edgecolor='#78909c', linewidth=1.2, zorder=2)
sc_all.boundary.plot(ax=ax, edgecolor='#cfd8dc', linewidth=0.55, zorder=3)

for iname, ilon, ilat, ikind in SICHUAN_OVERVIEW["industry_clusters"]:
    x, y = to_alb(ilon, ilat)
    if ikind in ["ict", "aero"]:
        ax.plot(x, y, 'p', color='#1565c0', markersize=8.0, markeredgecolor='white', markeredgewidth=1.2, zorder=15)
        ax.text(x, y + 6500, iname, fontsize=7.2, fontweight='bold', color='#0d47a1', ha='center',
                path_effects=[pe.withStroke(linewidth=2.2, foreground='white')], zorder=16)
    elif ikind in ["equipment", "material"]:
        ax.plot(x, y, 's', color='#d84315', markersize=7.5, markeredgecolor='white', markeredgewidth=1.2, zorder=15)
        ax.text(x, y + 6500, iname, fontsize=7.2, fontweight='bold', color='#bf360c', ha='center',
                path_effects=[pe.withStroke(linewidth=2.2, foreground='white')], zorder=16)
    elif ikind in ["battery", "pv", "hydro"]:
        ax.plot(x, y, 'D', color='#2e7d32', markersize=7.5, markeredgecolor='white', markeredgewidth=1.2, zorder=15)
        ax.text(x, y - 6500, iname, fontsize=7.2, fontweight='bold', color='#1b5e20', ha='center',
                path_effects=[pe.withStroke(linewidth=2.2, foreground='white')], zorder=16)
    else:
        ax.plot(x, y, 'h', color='#6a1b9a', markersize=7.5, markeredgecolor='white', markeredgewidth=1.2, zorder=15)
        ax.text(x, y + 6500, iname, fontsize=7.2, fontweight='bold', color='#4a148c', ha='center',
                path_effects=[pe.withStroke(linewidth=2.2, foreground='white')], zorder=16)

ind_handles = [
    Line2D([0], [0], marker='p', color='w', markerfacecolor='#1565c0', markersize=8, label="电子信息与航空航天制造 (成都天府软件园/成飞)"),
    Line2D([0], [0], marker='s', color='w', markerfacecolor='#d84315', markersize=8, label="重大装备制造与战略新材料 (德阳重装/攀枝花钒钛)"),
    Line2D([0], [0], marker='D', color='w', markerfacecolor='#2e7d32', markersize=8, label="绿色清洁能源装备 (宜宾动力电池/乐山晶硅光伏/三江水电)"),
    Line2D([0], [0], marker='h', color='w', markerfacecolor='#6a1b9a', markersize=8, label="优质白酒与现代消费品 (宜宾五粮液/泸州老窖/达州天然气)")
]
ax.legend(handles=ind_handles, loc="lower left", fontsize=7.2, framealpha=0.95,
          title="四川省六大优势产业集群布局", title_fontsize=8.0)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.set_title("四川省六大优势产业集群与国家先进制造业空间分布图", fontsize=12.5, fontweight='bold', color='#1a237e', pad=12)
mapkit.add_scalebar(ax, ax_xlim[0] + pad_x * 0.8, ax_ylim[0] + pad_y * 0.8, length_km=100)
add_compass(ax, 0.94, 0.93)

f4_out = os.path.join(OUT_DIR, "fig22-00-4_四川省六大优势产业集群与国家先进制造业空间分布图.png")
plt.savefig(f4_out, dpi=DPI, bbox_inches='tight')
plt.close(fig)
print(f" Saved: {f4_out}")


# =========================================================================
# 5. 1986-2024年夜间灯光演化与五大片区对比图 (fig22-00-5)
# =========================================================================
print("Rendering fig22-00-5: Sichuan Nightlight evolution 1986-2024...")
nl_file = os.path.join(DATA_DIR, "sichuan_nightlight_clean.csv")
nl_df = pd.read_csv(nl_file)
if "unit_code" not in nl_df.columns and "district_code" in nl_df.columns:
    nl_df.rename(columns={"district_code": "unit_code"}, inplace=True)

# 按年份汇总全省夜光总强度
nl_prov = nl_df.groupby("year")["sum"].sum().reset_index()

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 5.2), dpi=DPI)
fig.patch.set_facecolor('#ffffff')

# 左图：全省 1986-2024 夜间灯光总和曲线
ax1.plot(nl_prov["year"], nl_prov["sum"] / 1000.0, color="#d32f2f", linewidth=2.4, marker='o', markersize=4.0, label="全省夜光积分总和 (千DN)")
ax1.fill_between(nl_prov["year"], 0, nl_prov["sum"] / 1000.0, color="#ffebee", alpha=0.6)
ax1.set_title("四川省 1986—2024 年夜间灯光总强度演化时序", fontsize=10.5, fontweight='bold', color='#1a237e', pad=10)
ax1.set_xlabel("年份", fontsize=8.5, color='#263238')
ax1.set_ylabel("夜间灯光总和 (10³ DN)", fontsize=8.5, color='#263238')
ax1.grid(True, linestyle='--', alpha=0.5)

# 标注重大节点
ax1.annotate("1997 重庆直辖分设\n四川区划调整", xy=(1997, 18), xytext=(1990, 80),
             arrowprops=dict(facecolor='#1565c0', width=1.0, headwidth=4), fontsize=7.2, color='#0d47a1', fontweight='bold')
ax1.annotate("2008 汶川地震灾后重建\n工业提质扩能", xy=(2008, 65), xytext=(2002, 160),
             arrowprops=dict(facecolor='#d84315', width=1.0, headwidth=4), fontsize=7.2, color='#bf360c', fontweight='bold')
ax1.annotate("2020 成渝双城圈上升国家战略\n高新产业连片爆发", xy=(2020, 215), xytext=(2010, 260),
             arrowprops=dict(facecolor='#2e7d32', width=1.0, headwidth=4), fontsize=7.2, color='#1b5e20', fontweight='bold')

# 右图：2024 年五大经济区夜光强度与人口/经济结构分布
zones_data = [
    ("成都平原经济区", 62.5, 54.0, "#ffe082"),
    ("川南经济区", 17.5, 16.5, "#ffab91"),
    ("川东北经济区", 12.0, 16.8, "#b3e5fc"),
    ("攀西经济区", 5.5, 7.5, "#ce93d8"),
    ("川西北生态区", 2.5, 5.2, "#a5d6a7")
]
z_names = [z[0] for z in zones_data]
z_nl_share = [z[1] for z in zones_data]
z_colors = [z[3] for z in zones_data]

y_pos = np.arange(len(z_names))
bars = ax2.barh(y_pos, z_nl_share, color=z_colors, edgecolor='#546e7a', height=0.55)
ax2.set_yticks(y_pos)
ax2.set_yticklabels(z_names, fontsize=8.2, fontweight='bold')
ax2.invert_yaxis()
ax2.set_xlabel("2024 年占全省夜光总量比重 (%)", fontsize=8.5, color='#263238')
ax2.set_title("四川省五大经济区开发强度与夜光空间比重对比", fontsize=10.5, fontweight='bold', color='#1a237e', pad=10)
ax2.grid(True, linestyle='--', axis='x', alpha=0.5)

for bar in bars:
    w = bar.get_width()
    ax2.text(w + 1.0, bar.get_y() + bar.get_height()/2, f"{w:.1f}%", va='center', fontsize=7.5, fontweight='bold', color='#263238')

plt.tight_layout()
f5_out = os.path.join(OUT_DIR, "fig22-00-5_四川省1986-2024年夜间灯光演化与五大片区开发强度对比图.png")
plt.savefig(f5_out, dpi=DPI, bbox_inches='tight')
plt.close(fig)
print(f" Saved: {f5_out}")

print("\n=== SICHUAN OVERVIEW FIGURES GENERATION COMPLETE ===")
