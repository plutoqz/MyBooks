# -*- coding: utf-8 -*-
"""广东省地理统揽专题地图生成引擎（18-00）
包含 5 幅全省权威出版级地图与分析图表（精细调优排版、微缩字号、严格杜绝压盖）：
1. fig18-00-1_广东省地势起伏与珠江水系海湾格局图.png
2. fig18-00-2_广东省行政区划与“一核一带一区”空间格局图.png
3. fig18-00-3_广东省综合立体交通与湾区通道网络图.png
4. fig18-00-4_广东省战略性产业集群与先进制造基地空间格局图.png
5. fig18-00-5_广东省1986—2024年夜间灯光演变与区域协调发展图.png
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

sys.path.insert(0, r"D:\code\Ideas\MyBooks\中国地理知识手册\scripts")
from style import ALBERS, C_TEXT, DATA, DPI, FIGURES, setup
import mapkit
from guangdong_configs import GUANGDONG_OVERVIEW

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
    d = np.nan_to_num(dem, nan=0.0)
    gy, gx = np.gradient(d, res)
    slope = np.arctan(np.sqrt(gx * gx + gy * gy))
    aspect = np.arctan2(-gx, gy)
    shaded = np.sin(alt_rad) * np.cos(slope) + np.cos(alt_rad) * np.sin(slope) * np.cos(az_rad - aspect)
    return np.clip(shaded, 0.0, 1.0)

def add_scalebar(ax, x0, y0, length_km=100):
    mapkit.add_scalebar(ax, x0, y0, length_km=length_km)

def add_compass(ax, x=0.94, y=0.92):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.055), transform=ax.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=1.8, headwidth=5.5, headlength=6.5),
                ha="center", va="center", fontsize=8.8, fontweight="bold", color="#2c3e50", zorder=30)

print("Loading Guangdong provincial boundaries and DEM...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

gd_prov = gpd.read_file(os.path.join(DATAV_DIR, "440000_full.json")).to_crs(ALBERS)
gd_prov["geometry"] = gd_prov.geometry.buffer(0)
gd_union = gd_prov.union_all()

b = gd_prov.total_bounds
span_x = b[2] - b[0]
span_y = b[3] - b[1]
pad_x = span_x * 0.04
pad_y = span_y * 0.04
ax_xlim = (b[0] - pad_x, b[2] + pad_x)
ax_ylim = (b[1] - pad_y, b[3] + pad_y)

# 加载 DEM
dem_file = os.path.join(DATA_DIR, "dem", "province", "440000_z9.npz")
dem_data = np.load(dem_file)
step = 2
dem_raw = np.nan_to_num(dem_data['dem'][::step, ::step], nan=0.0)
res = float(dem_data['res']) * step
minx = float(dem_data['minx'])
maxy = float(dem_data['maxy'])
extent = (minx, minx + dem_raw.shape[1] * res, maxy - dem_raw.shape[0] * res, maxy)
print(f"Downsampled Guangdong DEM shape: {dem_raw.shape}, res: {res}m")

# =============================================================================
# Fig 18-00-1: 广东省地势起伏与珠江水系海湾格局图
# =============================================================================
print("Generating Fig 18-00-1 (Topography & River-Bay Basin Pattern)...")
fig, ax = plt.subplots(figsize=(11.0, 7.8), dpi=DPI)
fig.subplots_adjust(left=0.015, right=0.985, top=0.960, bottom=0.015)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

norm = Normalize(vmin=0.0, vmax=1950.0)
dem_colors = [
    (0.00, "#196f3d"),  # 珠三角与沿海平原深绿
    (0.08, "#27ae60"),  # 低丘与阶地
    (0.20, "#7dcea0"),  # 丘陵低山
    (0.40, "#f9e79f"),  # 低中山
    (0.60, "#eb984e"),  # 中山 (莲花山/云雾山)
    (0.80, "#ba4a00"),  # 南岭高山
    (1.00, "#78281f")   # 石坑崆绝顶
]
cmap = LinearSegmentedColormap.from_list("gd_dem", dem_colors)

hs = calc_hillshade(dem_raw, res)
rgb_dem = cmap(norm(dem_raw))[:, :, :3]
rgb_shaded = rgb_dem * (0.42 + 0.58 * hs[:, :, np.newaxis])

im = ax.imshow(rgb_shaded, extent=extent, origin="upper", zorder=2)
patch = get_mpl_clip_patch(gd_union)
ax.add_patch(patch)
im.set_clip_path(patch)

gd_prov.boundary.plot(ax=ax, color="#1a5276", lw=1.2, zorder=5)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl = mapkit.SymbolLabels(ax, fig)
sl.reserve([(0.0, 0.0, 0.35, 0.30),
            (0.50, 0.0, 1.0, 0.09),
            (0.88, 0.85, 1.0, 1.0)])

for item in GUANGDONG_OVERVIEW["landmarks_macro"]:
    name, lon, lat, k = item[0], item[1], item[2], item[3]
    x, y = to_alb(lon, lat)
    nm, nt = mapkit.split_note(name)
    if k == "peak_max":
        sl.add(x, y, nm, "peak_max", note=nt, priority=0,
               marker="^", face="#78281f", size=9.0, kind_label="广东第一峰 (乳源石坑崆 1903.2m)")
    elif k == "peak":
        sl.add(x, y, nm, "peak", note=nt, priority=1,
               marker="^", face="#d35400", size=7.2, kind_label="骨干名山与分水岭主峰")
    elif k == "bridge_hub":
        sl.add(x, y, nm, "bridge_hub", note=nt, priority=1,
               marker="s", face="#154360", size=7.5, kind_label="世界级跨海通道工程 (深中/港珠澳)")
    elif k == "port_hub":
        sl.add(x, y, nm, "port_hub", note=nt, priority=2,
               marker="p", face="#1b4f72", size=7.0, kind_label="全球级集装箱核心港区")
    elif k == "airport_hub":
        sl.add(x, y, nm, "airport_hub", note=nt, priority=2,
               marker="D", face="#6c3483", size=7.0, kind_label="国际客货超级航空枢纽机场")
    else:
        sl.add(x, y, nm, "tech_cluster", note=nt, priority=2,
               marker="*", face="#c0392b", size=8.5, kind_label="大湾区战略合作平台与产业高地")

for item in GUANGDONG_OVERVIEW["rivers_macro"]:
    rname, rlon, rlat, rk = item[0], item[1], item[2], item[3]
    rx, ry = to_alb(rlon, rlat)
    nm, nt = mapkit.split_note(rname)
    sl.add(rx, ry, nm, "river", note=nt, priority=2,
           marker="o", face="#2980b9", size=6.0, kind_label="骨干河流水系与优良海湾水库")

sym_type_h, sym_idx_h = sl.flush()

sb_x0 = ax_xlim[0] + span_x * 0.58
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=120)
add_compass(ax, 0.94, 0.92)

cax = ax.inset_axes([0.04, 0.06, 0.025, 0.25])
cb = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax, orientation="vertical")
cb.set_label("高程 Elevation (m)", fontsize=7.0, color="#2c3e50")
cb.ax.tick_params(labelsize=6.2, length=2.0)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="地理与战略要素分类", ncol=2, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="图上要素编号对照", ncol=2, fontsize=6.8, title_fontsize=7.6),
], top=-0.010, gap=0.014)

ax.set_title("广东省地势起伏与珠江水系海湾格局图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Topography, Pearl River System & Coastal Bay Pattern of Guangdong Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：AWS Terrain GLO-30 DEM · 广东省自然资源厅标准底图 · 制作：《中国地理知识手册》",
    fontsize=6.5)

f1_path = os.path.join(OUT_DIR, "fig18-00-1_广东省地势起伏与珠江水系海湾格局图.png")
fig.savefig(f1_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {f1_path}")

# =============================================================================
# Fig 18-00-2: 广东省行政区划与“一核一带一区”空间格局图
# =============================================================================
print("Generating Fig 18-00-2 (Administrative & '1 Core 1 Belt 1 Area' Strategy)...")
fig, ax = plt.subplots(figsize=(11.0, 7.8), dpi=DPI)
fig.subplots_adjust(left=0.015, right=0.985, top=0.960, bottom=0.015)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

palette = [
    "#d4e6f1", "#d5f5e3", "#fcf3cf", "#ebdef0", "#fadbd8", "#e8f8f5",
    "#fdebd0", "#eaeded", "#f4ecf7", "#eaf2f8", "#fef9e7", "#e8f6f3",
    "#f9ebea", "#e9f7ef", "#d6eaf8", "#edbb99", "#d2b4de", "#a9dfbf",
    "#f9e79f", "#a3e4d7", "#f5cba7"
]

for idx, (_, row) in enumerate(gd_prov.iterrows()):
    color = palette[idx % len(palette)]
    gpd.GeoSeries([row.geometry]).plot(ax=ax, facecolor=color, edgecolor="#7f8c8d", lw=0.7, zorder=2)
gd_prov.boundary.plot(ax=ax, color="#1a5276", lw=1.6, zorder=3)

for _, row in gd_prov.iterrows():
    name = row.get("name", "")
    pt = row.geometry.representative_point()
    ax.text(pt.x, pt.y, name, fontsize=8.0, fontweight="bold", color="#1b4f72",
            ha="center", va="center", zorder=6,
            path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")])

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl = mapkit.SymbolLabels(ax, fig)
sl.reserve([(0.0, 0.0, 0.40, 0.28),
            (0.50, 0.0, 1.0, 0.09),
            (0.88, 0.85, 1.0, 1.0)])

for item in GUANGDONG_OVERVIEW["strategy_nodes"]:
    sname, slon, slat, sk = item[0], item[1], item[2], item[3]
    sx, sy = to_alb(slon, slat)
    nm, nt = mapkit.split_note(sname)
    if sk == "capital":
        sl.add(sx, sy, nm, "capital", note=nt, priority=0,
               marker="*", face="#922b21", size=10.5, kind_label="省会·国家中心城市 (广州)")
    elif sk == "core":
        sl.add(sx, sy, nm, "core", note=nt, priority=0,
               marker="*", face="#c0392b", size=9.5, kind_label="大湾区核心极核城市 (深圳·佛山·东莞)")
    elif sk == "sub_center":
        sl.add(sx, sy, nm, "sub_center", note=nt, priority=1,
               marker="s", face="#b03a2e", size=8.0, kind_label="省域副中心城市 (汕头·湛江)")
    else:
        sl.add(sx, sy, nm, "node", note=nt, priority=2,
               marker="o", face="#1f618d", size=6.5, kind_label="区域骨干节点城市与特色功能区")

sym_type_h, sym_idx_h = sl.flush()

add_scalebar(ax, sb_x0, sb_y0, length_km=120)
add_compass(ax, 0.94, 0.92)

leg_elements = [
    Patch(facecolor="#fadbd8", edgecolor="#b03a2e", lw=1.5, label="珠三角核心区 (大湾区极核引擎)"),
    Patch(facecolor="#d4e6f1", edgecolor="#1f618d", lw=1.5, label="沿海经济带 (东西两翼产业新支点)"),
    Patch(facecolor="#d5f5e3", edgecolor="#196f3d", lw=1.5, label="北部生态发展区 (南岭生态安全屏障)")
]

leg = mapkit.stacked_legends(ax, [
    dict(handles=leg_elements + sym_type_h, title="空间战略与板块层次", ncol=2, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="主要战略枢纽点索引", ncol=2, fontsize=6.8, title_fontsize=7.6),
], top=-0.010, gap=0.014)

ax.set_title("广东省行政区划与“一核一带一区”空间格局图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Administrative Divisions & 'One Core, One Belt, One Area' Spatial Pattern of Guangdong",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：广东省自然资源厅 · 广东省国土空间规划 (2021—2035) · 制作：《中国地理知识手册》",
    fontsize=6.5)

f2_path = os.path.join(OUT_DIR, "fig18-00-2_广东省行政区划与“一核一带一区”空间格局图.png")
fig.savefig(f2_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {f2_path}")

# =============================================================================
# Fig 18-00-3: 广东省综合立体交通与湾区通道网络图
# =============================================================================
print("Generating Fig 18-00-3 (Transport Infrastructure & Bay Area Corridors)...")
fig, ax = plt.subplots(figsize=(11.0, 7.8), dpi=DPI)
fig.subplots_adjust(left=0.015, right=0.985, top=0.960, bottom=0.015)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

gd_prov.plot(ax=ax, facecolor="#fdfefe", edgecolor="#7f8c8d", lw=0.6, ls=":", zorder=2)
gd_prov.boundary.plot(ax=ax, color="#1a5276", lw=1.6, zorder=3)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl = mapkit.SymbolLabels(ax, fig)
sl.reserve([(0.0, 0.0, 0.38, 0.28),
            (0.50, 0.0, 1.0, 0.09),
            (0.88, 0.85, 1.0, 1.0)])

trans_points = [
    ("广州南站 (全国客流量最大特等客运高铁枢纽)", 113.270, 22.990, "rail"),
    ("深圳北站 (广深港客运通道特等枢纽)", 114.030, 22.610, "rail"),
    ("广州白云站 (特大型现代化客运综合枢纽)", 113.250, 23.180, "rail"),
    ("汕头站 (广汕汕高铁/厦深铁路粤东枢纽)", 116.755, 23.375, "rail"),
    ("湛江西站 (深湛/广湛高铁粤西综合客站)", 110.300, 21.210, "rail"),
    ("佛山西站 (贵广南广高铁大站)", 113.030, 23.080, "rail"),
    ("江门站 (珠江西岸第四大综合铁路枢纽)", 113.050, 22.470, "rail"),
    ("惠州北站 (赣深高铁粤东骨干枢纽)", 114.380, 23.200, "rail"),
    ("虎门站 (广深港高铁东莞枢纽)", 113.660, 22.855, "rail"),
    ("潮汕站 (粤东动车组核心枢纽站)", 116.550, 23.540, "rail"),
    ("广州白云国际机场 (4F级大型国际航空枢纽港)", 113.300, 23.390, "airport"),
    ("深圳宝安国际机场 (4F级综合国际客货运航空港)", 113.810, 22.640, "airport"),
    ("揭阳潮汕国际机场 (4E级粤东核心航空港)", 116.510, 23.550, "airport"),
    ("湛江吴川国际机场 (4E级粤西民航枢纽)", 110.780, 21.480, "airport"),
    ("南沙港区 (广州港千万标箱级枢纽港)", 113.670, 22.680, "port"),
    ("盐田港区 (深圳港世界超级集装箱港)", 114.270, 22.580, "port"),
    ("港珠澳大桥 (世界最长跨海大桥)", 113.780, 22.280, "bridge"),
    ("深中通道 (珠江口跨海交通集群工程)", 113.730, 22.570, "bridge")
]

for item in trans_points:
    tname, tlon, tlat, tk = item[0], item[1], item[2], item[3]
    tx, ty = to_alb(tlon, tlat)
    nm, nt = mapkit.split_note(tname)
    if tk == "rail":
        sl.add(tx, ty, nm, "rail", note=nt, priority=1,
               marker="s", face="#c0392b", size=7.2, kind_label="高速铁路客运特等与综合枢纽客站")
    elif tk == "airport":
        sl.add(tx, ty, nm, "airport", note=nt, priority=1,
               marker="D", face="#8e44ad", size=7.2, kind_label="国家双枢纽及骨干民用航空港区")
    elif tk == "port":
        sl.add(tx, ty, nm, "port", note=nt, priority=2,
               marker="p", face="#154360", size=7.0, kind_label="世界级千万标箱超级海港港区")
    else:
        sl.add(tx, ty, nm, "bridge", note=nt, priority=1,
               marker="h", face="#d35400", size=7.5, kind_label="大湾区跨海超级通道工程枢纽")

sym_type_h, sym_idx_h = sl.flush()

add_scalebar(ax, sb_x0, sb_y0, length_km=120)
add_compass(ax, 0.94, 0.92)

leg_elements = [
    Line2D([0], [0], color="#c0392b", lw=2.2, label="京广/广深港/广汕汕/广湛高铁通道"),
    Line2D([0], [0], color="#154360", lw=2.0, label="港珠澳大桥与深中通道跨海纽带"),
    Line2D([0], [0], color="#2980b9", lw=1.5, label="国家骨干高速公路与城际环网")
]

leg = mapkit.stacked_legends(ax, [
    dict(handles=leg_elements + sym_type_h, title="交通网络与枢纽标识", ncol=2, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="综合枢纽节点索引", ncol=2, fontsize=6.8, title_fontsize=7.6),
], top=-0.010, gap=0.014)

ax.set_title("广东省综合立体交通与湾区通道网络图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Integrated Transportation Network & Bay Area Corridors of Guangdong Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：广东省交通运输厅 · 广东省综合立体交通网规划纲要 · 制作：《中国地理知识手册》",
    fontsize=6.5)

f3_path = os.path.join(OUT_DIR, "fig18-00-3_广东省综合立体交通与湾区通道网络图.png")
fig.savefig(f3_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {f3_path}")

# =============================================================================
# Fig 18-00-4: 广东省战略性产业集群与先进制造基地空间格局图
# =============================================================================
print("Generating Fig 18-00-4 (Strategic Industrial Clusters & Advanced Manufacturing)...")
fig, ax = plt.subplots(figsize=(11.0, 7.8), dpi=DPI)
fig.subplots_adjust(left=0.015, right=0.985, top=0.960, bottom=0.015)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

gd_prov.plot(ax=ax, facecolor="#fdfefe", edgecolor="#7f8c8d", lw=0.6, ls=":", zorder=2)
gd_prov.boundary.plot(ax=ax, color="#1a5276", lw=1.6, zorder=3)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl = mapkit.SymbolLabels(ax, fig)
sl.reserve([(0.0, 0.0, 0.40, 0.30),
            (0.50, 0.0, 1.0, 0.09),
            (0.88, 0.85, 1.0, 1.0)])

for item in GUANGDONG_OVERVIEW["industry_clusters"]:
    cname, clon, clat, ck = item[0], item[1], item[2], item[3]
    cx, cy = to_alb(clon, clat)
    nm, nt = mapkit.split_note(cname)
    if ck == "ict":
        sl.add(cx, cy, nm, "ict", note=nt, priority=0,
               marker="*", face="#78281f", size=9.5, kind_label="前海·河套深港科技创新与战略芯片集聚区")
    elif ck == "science":
        sl.add(cx, cy, nm, "science", note=nt, priority=1,
               marker="D", face="#8e44ad", size=7.5, kind_label="广州科学城·中新广州知识城创新策源极")
    elif ck == "auto":
        sl.add(cx, cy, nm, "auto", note=nt, priority=1,
               marker="s", face="#c0392b", size=7.5, kind_label="广深佛莞智能网联与新能源汽车走廊")
    elif ck == "home_appliances":
        sl.add(cx, cy, nm, "home_appliances", note=nt, priority=2,
               marker="^", face="#d35400", size=7.2, kind_label="佛莞智能家电与现代高端装备集群")
    elif ck == "petrochem":
        sl.add(cx, cy, nm, "petrochem", note=nt, priority=2,
               marker="p", face="#196f3d", size=7.2, kind_label="大亚湾与东海岛世界级绿色石化基地")
    elif ck == "wind_power":
        sl.add(cx, cy, nm, "wind_power", note=nt, priority=2,
               marker="o", face="#154360", size=7.0, kind_label="阳江千万千瓦级海上风电产业基地")
    elif ck == "computing":
        sl.add(cx, cy, nm, "computing", note=nt, priority=2,
               marker="h", face="#27ae60", size=7.0, kind_label="韶关粤港澳大湾区全国一体化算力枢纽")
    else:
        sl.add(cx, cy, nm, "hardware", note=nt, priority=1,
               marker="s", face="#2980b9", size=7.2, kind_label="松山湖科学城与全球智能终端制造")

sym_type_h, sym_idx_h = sl.flush()

add_scalebar(ax, sb_x0, sb_y0, length_km=120)
add_compass(ax, 0.94, 0.92)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="万亿产业集群类别", ncol=2, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="战略性制造基地分布索引", ncol=1, fontsize=6.8, title_fontsize=7.6),
], top=-0.010, gap=0.014)

ax.set_title("广东省战略性产业集群与先进制造基地空间格局图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Strategic Industrial Clusters & Advanced Manufacturing Bases of Guangdong Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：广东省工业和信息化厅 · “双十”战略性产业集群行动计划 · 制作：《中国地理知识手册》",
    fontsize=6.5)

f4_path = os.path.join(OUT_DIR, "fig18-00-4_广东省战略性产业集群与先进制造基地空间格局图.png")
fig.savefig(f4_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {f4_path}")

# =============================================================================
# Fig 18-00-5: 广东省1986—2024年夜间灯光演变与区域协调发展图
# =============================================================================
print("Generating Fig 18-00-5 (Nightlight Evolution 1986-2024)...")
fig, (ax_nl, ax_gdp) = plt.subplots(2, 1, figsize=(10.2, 8.8), dpi=DPI)
fig.patch.set_facecolor("white")

nl_df = pd.read_csv(os.path.join(DATA_DIR, "guangdong_nightlight_clean.csv"))
prov_nl = nl_df.groupby("year")["sum"].sum().reset_index()

years = prov_nl["year"].values
sums = prov_nl["sum"].values

ax_nl.plot(years, sums, color="#c0392b", lw=2.2, marker="o", markersize=4.0, label="全省夜间灯光辐射总量 (DN·Pixel)")
ax_nl.fill_between(years, sums, color="#fadbd8", alpha=0.5)

annotations = [
    (1996, 180000, 1991, 280000, "广州天河、深圳罗湖福田与珠三角外贸工业带初显强光"),
    (2005, 420000, 2000, 580000, "广深科技走廊破土·佛莞制造腹地与东西两翼工业全面铺开"),
    (2013, 850000, 2008, 1150000, "广深港高铁开通·南沙前海横琴大湾区核心片区成片跃升"),
    (2023, 1680000, 2018, 1980000, "大湾区世界级城市群全面建成·深中通道通车·全省全域璀璨发光")
]

for yr, val, tx_yr, tx_val, text in annotations:
    ax_nl.annotate(text, xy=(yr, val), xytext=(tx_yr, tx_val),
                   arrowprops=dict(arrowstyle="->", color="#922b21", lw=1.0),
                   fontsize=7.2, fontweight="bold", color="#78281f",
                   bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffffff", edgecolor="#e74c3c", alpha=0.9))

ax_nl.set_title("广东省 1986—2024 年夜间灯光遥感辐射总量跃升轨迹", fontsize=11.0, fontweight="bold", color=C_TEXT)
ax_nl.set_ylabel("夜光总量辐射积分 (DN)", fontsize=8.0, color="#2c3e50")
ax_nl.grid(True, linestyle="--", alpha=0.5)
ax_nl.tick_params(labelsize=7.5)

gdp_data = {
    2000: 10741.0,
    2005: 22557.0,
    2010: 46013.0,
    2015: 72812.0,
    2020: 110760.0,
    2022: 129118.0,
    2023: 135673.0,
    2024: 141600.0
}
gyears = list(gdp_data.keys())
gvals = list(gdp_data.values())

bars = ax_gdp.bar(gyears, gvals, width=1.5, color="#1b4f72", edgecolor="#0b2545", alpha=0.88, label="全省地区生产总值 (GDP, 亿元)")
for bar in bars:
    h = bar.get_height()
    ax_gdp.text(bar.get_x() + bar.get_width() / 2.0, h + 2000, f"{h:g}",
                ha="center", va="bottom", fontsize=7.0, fontweight="bold", color="#0b2545")

ax_gdp.set_title("广东省 2000—2024 年地区生产总值 (GDP) 连续 36 年领跑全国历史性跨越 (亿元)", fontsize=11.0, fontweight="bold", color=C_TEXT)
ax_gdp.set_ylabel("GDP (亿元)", fontsize=8.0, color="#2c3e50")
ax_gdp.set_xlabel("年份 Year", fontsize=8.0, color="#2c3e50")
ax_gdp.grid(True, linestyle="--", alpha=0.5)
ax_gdp.tick_params(labelsize=7.5)

fig.tight_layout(pad=2.5)
fig.text(0.5, 0.015, "数据源：历年夜间灯光遥感数据 · 广东统计年鉴与历年国民经济和社会发展统计公报 · 制作：《中国地理知识手册》",
         ha="center", va="bottom", fontsize=6.8, color="#7f8c8d")

f5_path = os.path.join(OUT_DIR, "fig18-00-5_广东省1986—2024年夜间灯光演变与区域协调发展图.png")
fig.savefig(f5_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {f5_path}")

print("\nAll 5 Guangdong Overview Figures successfully generated!")
