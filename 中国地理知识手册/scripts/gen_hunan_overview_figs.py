# -*- coding: utf-8 -*-
"""湖南省地理统揽专题地图生成引擎（17-00）
包含 5 幅全省权威出版级地图与分析图表（精细调优排版、微缩字号、严格杜绝压盖）：
1. fig17-00-1_湖南省地势起伏与洞庭湖四水格局图.png
2. fig17-00-2_湖南省行政区划与“一核两副三带四区”空间格局图.png
3. fig17-00-3_湖南省综合立体交通与骨干高铁网络图.png
4. fig17-00-4_湖南省先进制造业集群与特色产业基地空间格局图.png
5. fig17-00-5_湖南省1986—2024年夜间灯光演变与区域协调发展图.png
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
from hunan_configs import HUNAN_OVERVIEW

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

def add_scalebar(ax, x0, y0, length_km=80):
    mapkit.add_scalebar(ax, x0, y0, length_km=length_km)

def add_compass(ax, x=0.94, y=0.92):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.055), transform=ax.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=1.8, headwidth=5.5, headlength=6.5),
                ha="center", va="center", fontsize=8.8, fontweight="bold", color="#2c3e50", zorder=30)

print("Loading Hunan provincial boundaries and DEM...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

hn_prov = gpd.read_file(os.path.join(DATAV_DIR, "430000_full.json")).to_crs(ALBERS)
hn_prov["geometry"] = hn_prov.geometry.buffer(0)
hn_union = hn_prov.union_all()

b = hn_prov.total_bounds
span_x = b[2] - b[0]
span_y = b[3] - b[1]
pad_x = span_x * 0.04
pad_y = span_y * 0.04
ax_xlim = (b[0] - pad_x, b[2] + pad_x)
ax_ylim = (b[1] - pad_y, b[3] + pad_y)

# 加载 DEM
dem_file = os.path.join(DATA_DIR, "dem", "province", "430000_z9.npz")
dem_data = np.load(dem_file)
step = 2
dem_raw = np.nan_to_num(dem_data['dem'][::step, ::step], nan=0.0)
res = float(dem_data['res']) * step
minx = float(dem_data['minx'])
maxy = float(dem_data['maxy'])
extent = (minx, minx + dem_raw.shape[1] * res, maxy - dem_raw.shape[0] * res, maxy)
print(f"Downsampled Hunan DEM shape: {dem_raw.shape}, res: {res}m")

# =============================================================================
# Fig 17-00-1: 湖南省地势起伏与洞庭湖四水格局图
# =============================================================================
print("Generating Fig 17-00-1 (Topography & River Basin Pattern)...")
fig, ax = plt.subplots(figsize=(10.5, 8.0), dpi=DPI)
fig.subplots_adjust(left=0.015, right=0.985, top=0.960, bottom=0.015)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

norm = Normalize(vmin=0.0, vmax=2150.0)
dem_colors = [
    (0.00, "#196f3d"),  # 洞庭湖平原深绿
    (0.10, "#27ae60"),  # 低丘与河谷平原
    (0.22, "#7dcea0"),  # 湘中丘陵盆地
    (0.40, "#f9e79f"),  # 低中山
    (0.60, "#eb984e"),  # 中山 (雪峰山脉/南岭)
    (0.80, "#ba4a00"),  # 壶瓶山/韭菜岭高山
    (1.00, "#78281f")   # 酃峰罗霄绝顶
]
cmap = LinearSegmentedColormap.from_list("hn_dem", dem_colors)

hs = calc_hillshade(dem_raw, res)
rgb_dem = cmap(norm(dem_raw))[:, :, :3]
rgb_shaded = rgb_dem * (0.42 + 0.58 * hs[:, :, np.newaxis])

im = ax.imshow(rgb_shaded, extent=extent, origin="upper", zorder=2)
patch = get_mpl_clip_patch(hn_union)
ax.add_patch(patch)
im.set_clip_path(patch)

hn_prov.boundary.plot(ax=ax, color="#1a5276", lw=1.2, zorder=5)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl = mapkit.SymbolLabels(ax, fig)
sl.reserve([(0.0, 0.0, 0.35, 0.30),
            (0.50, 0.0, 1.0, 0.09),
            (0.88, 0.85, 1.0, 1.0)])

for item in HUNAN_OVERVIEW["landmarks_macro"]:
    name, lon, lat, k = item[0], item[1], item[2], item[3]
    x, y = to_alb(lon, lat)
    nm, nt = mapkit.split_note(name)
    if k == "peak_max":
        sl.add(x, y, nm, "peak_max", note=nt, priority=0,
               marker="^", face="#78281f", size=9.0, kind_label="湖南第一高峰 (炎陵酃峰 2115.2m)")
    elif k == "peak":
        sl.add(x, y, nm, "peak", note=nt, priority=1,
               marker="^", face="#d35400", size=7.2, kind_label="骨干名山与分水岭主峰")
    elif k == "port_hub":
        sl.add(x, y, nm, "port_hub", note=nt, priority=2,
               marker="p", face="#1b4f72", size=7.0, kind_label="长江中游通江达海港口枢纽")
    elif k == "airport_hub":
        sl.add(x, y, nm, "airport_hub", note=nt, priority=2,
               marker="D", face="#6c3483", size=7.0, kind_label="国家区域枢纽民用机场港区")
    elif k == "logistic_hub":
        sl.add(x, y, nm, "logistic_hub", note=nt, priority=2,
               marker="s", face="#154360", size=7.2, kind_label="西部陆海新通道战略国际陆港")
    else:
        sl.add(x, y, nm, "tech_cluster", note=nt, priority=2,
               marker="*", face="#c0392b", size=8.5, kind_label="国家战略制造与先进产业高地")

for item in HUNAN_OVERVIEW["rivers_macro"]:
    rname, rlon, rlat, rk = item[0], item[1], item[2], item[3]
    rx, ry = to_alb(rlon, rlat)
    nm, nt = mapkit.split_note(rname)
    sl.add(rx, ry, nm, "river", note=nt, priority=2,
           marker="o", face="#2980b9", size=6.0, kind_label="四水一湖骨干水系与特大水库")

sym_type_h, sym_idx_h = sl.flush()

sb_x0 = ax_xlim[0] + span_x * 0.58
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=100)
add_compass(ax, 0.94, 0.92)

cax = ax.inset_axes([0.04, 0.06, 0.025, 0.25])
cb = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), cax=cax, orientation="vertical")
cb.set_label("高程 Elevation (m)", fontsize=7.0, color="#2c3e50")
cb.ax.tick_params(labelsize=6.2, length=2.0)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="地理与水利要素分类", ncol=2, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="图上要素编号对照", ncol=2, fontsize=6.8, title_fontsize=7.6),
], top=-0.010, gap=0.014)

ax.set_title("湖南省地势起伏与洞庭湖四水格局图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Topography, Dongting Basin System & Strategic Water Conservancy of Hunan Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：AWS Terrain GLO-30 DEM · 湖南省自然资源厅标准底图 · 制作：《中国地理知识手册》",
    fontsize=6.5)

f1_path = os.path.join(OUT_DIR, "fig17-00-1_湖南省地势起伏与洞庭湖四水格局图.png")
fig.savefig(f1_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {f1_path}")

# =============================================================================
# Fig 17-00-2: 湖南省行政区划与“一核两副三带四区”空间格局图
# =============================================================================
print("Generating Fig 17-00-2 (Administrative & '1 Core 2 Subcenters' Strategy)...")
fig, ax = plt.subplots(figsize=(10.5, 8.0), dpi=DPI)
fig.subplots_adjust(left=0.015, right=0.985, top=0.960, bottom=0.015)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

palette = [
    "#d4e6f1", "#d5f5e3", "#fcf3cf", "#ebdef0", "#fadbd8", "#e8f8f5",
    "#fdebd0", "#eaeded", "#f4ecf7", "#eaf2f8", "#fef9e7", "#e8f6f3",
    "#f9ebea", "#e9f7ef"
]

for idx, (_, row) in enumerate(hn_prov.iterrows()):
    color = palette[idx % len(palette)]
    gpd.GeoSeries([row.geometry]).plot(ax=ax, facecolor=color, edgecolor="#7f8c8d", lw=0.7, zorder=2)
hn_prov.boundary.plot(ax=ax, color="#1a5276", lw=1.6, zorder=3)

for _, row in hn_prov.iterrows():
    name = row.get("name", "")
    pt = row.geometry.representative_point()
    ax.text(pt.x, pt.y, name, fontsize=8.2, fontweight="bold", color="#1b4f72",
            ha="center", va="center", zorder=6,
            path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")])

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl = mapkit.SymbolLabels(ax, fig)
sl.reserve([(0.0, 0.0, 0.40, 0.28),
            (0.50, 0.0, 1.0, 0.09),
            (0.88, 0.85, 1.0, 1.0)])

for item in HUNAN_OVERVIEW["strategy_nodes"]:
    sname, slon, slat, sk = item[0], item[1], item[2], item[3]
    sx, sy = to_alb(slon, slat)
    nm, nt = mapkit.split_note(sname)
    if sk == "capital":
        sl.add(sx, sy, nm, "capital", note=nt, priority=0,
               marker="*", face="#922b21", size=10.5, kind_label="强省会·长株潭核心核 (长沙)")
    elif sk == "sub_center":
        sl.add(sx, sy, nm, "sub_center", note=nt, priority=1,
               marker="s", face="#b03a2e", size=8.0, kind_label="省域副中心城市 (岳阳·衡阳)")
    else:
        sl.add(sx, sy, nm, "node", note=nt, priority=2,
               marker="o", face="#1f618d", size=6.5, kind_label="区域骨干节点城市与特色功能区")

sym_type_h, sym_idx_h = sl.flush()

add_scalebar(ax, sb_x0, sb_y0, length_km=100)
add_compass(ax, 0.94, 0.92)

leg_elements = [
    Patch(facecolor="#fadbd8", edgecolor="#b03a2e", lw=1.5, label="长株潭都市圈 (半小时经济绿心圈)"),
    Patch(facecolor="#d4e6f1", edgecolor="#1f618d", lw=1.5, label="岳阳长江经济带与通江达海门户"),
    Patch(facecolor="#d5f5e3", edgecolor="#196f3d", lw=1.5, label="衡阳湘南区域中心与陆港物流枢纽"),
    Patch(facecolor="#fcf3cf", edgecolor="#b7950b", lw=1.5, label="大湘西生态文化旅游圈与绿色功能区")
]

leg = mapkit.stacked_legends(ax, [
    dict(handles=leg_elements + sym_type_h, title="空间战略与板块层次", ncol=2, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="主要战略枢纽点索引", ncol=2, fontsize=6.8, title_fontsize=7.6),
], top=-0.010, gap=0.014)

ax.set_title("湖南省行政区划与“一核两副三带四区”空间格局图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Administrative Divisions & 'One Core, Two Subcenters' Spatial Pattern of Hunan Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：湖南省发展和改革委员会 · 国土空间总体规划 (2021—2035) · 制作：《中国地理知识手册》",
    fontsize=6.5)

f2_path = os.path.join(OUT_DIR, "fig17-00-2_湖南省行政区划与“一核两副三带四区”空间格局图.png")
fig.savefig(f2_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {f2_path}")

# =============================================================================
# Fig 17-00-3: 湖南省综合立体交通与骨干高铁网络图
# =============================================================================
print("Generating Fig 17-00-3 (Transport Infrastructure & High-Speed Rail Network)...")
fig, ax = plt.subplots(figsize=(10.5, 8.0), dpi=DPI)
fig.subplots_adjust(left=0.015, right=0.985, top=0.960, bottom=0.015)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

hn_prov.plot(ax=ax, facecolor="#fdfefe", edgecolor="#7f8c8d", lw=0.6, ls=":", zorder=2)
hn_prov.boundary.plot(ax=ax, color="#1a5276", lw=1.6, zorder=3)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl = mapkit.SymbolLabels(ax, fig)
sl.reserve([(0.0, 0.0, 0.38, 0.28),
            (0.50, 0.0, 1.0, 0.09),
            (0.88, 0.85, 1.0, 1.0)])

trans_points = [
    ("长沙南站 (京广高铁/沪昆高铁双十字特等客运枢纽)", 113.065, 28.148, "rail"),
    ("株洲西站 (京广高铁先进装备枢纽节点)", 113.065, 27.810, "rail"),
    ("湘潭北站 (沪昆高铁融城核心节点)", 112.890, 27.960, "rail"),
    ("衡阳东站 (京广/衡柳/怀邵衡交汇特等枢纽)", 112.700, 26.890, "rail"),
    ("岳阳东站 (京广高铁长江门户枢纽客站)", 113.190, 29.360, "rail"),
    ("常德站 (常益长高铁/黔常铁路综合客运枢纽)", 111.685, 29.065, "rail"),
    ("益阳南站 (常益长高铁骨干客站)", 112.380, 28.530, "rail"),
    ("郴州西站 (京广高铁对接粤港澳节点大站)", 112.980, 25.780, "rail"),
    ("永州站 (衡柳高铁/益湛铁路枢纽)", 111.590, 26.450, "rail"),
    ("怀化南站 (沪昆/张吉怀/怀邵衡特等高铁枢纽)", 109.980, 27.520, "rail"),
    ("娄底南站 (沪昆高铁湘中重要枢纽客站)", 111.980, 27.690, "rail"),
    ("吉首东站 (张吉怀高铁核心枢纽客站)", 109.750, 28.335, "rail"),
    ("张家界西站 (黔常铁路/张吉怀高铁枢纽)", 110.440, 29.165, "rail"),
    ("长沙黄花国际机场 (4F级大型双跑道国际航空港)", 113.220, 28.190, "airport"),
    ("张家界荷花国际机场 (4D级国际旅游空港)", 110.450, 29.100, "airport"),
    ("城陵矶新港 (湖南唯一长江通江达海集装箱外贸大港)", 113.140, 29.450, "port"),
    ("怀化国际陆港 (西部陆海新通道东线战略集结中心)", 109.950, 27.510, "port")
]

for item in trans_points:
    tname, tlon, tlat, tk = item[0], item[1], item[2], item[3]
    tx, ty = to_alb(tlon, tlat)
    nm, nt = mapkit.split_note(tname)
    if tk == "rail":
        sl.add(tx, ty, nm, "rail", note=nt, priority=1,
               marker="s", face="#c0392b", size=7.2, kind_label="主要高速铁路客运特等与骨干枢纽站")
    elif tk == "airport":
        sl.add(tx, ty, nm, "airport", note=nt, priority=1,
               marker="D", face="#8e44ad", size=7.2, kind_label="国家区域与旅游民用机场港区")
    else:
        sl.add(tx, ty, nm, "port", note=nt, priority=2,
               marker="p", face="#154360", size=7.0, kind_label="长江中游通江达海港口与战略国际陆港")

sym_type_h, sym_idx_h = sl.flush()

add_scalebar(ax, sb_x0, sb_y0, length_km=100)
add_compass(ax, 0.94, 0.92)

leg_elements = [
    Line2D([0], [0], color="#c0392b", lw=2.2, label="京广/沪昆/常益长/张吉怀高铁主通道"),
    Line2D([0], [0], color="#154360", lw=2.0, label="城陵矶江海直达与洞庭湖千吨级航道"),
    Line2D([0], [0], color="#2980b9", lw=1.5, label="国家骨干高速公路通道网")
]

leg = mapkit.stacked_legends(ax, [
    dict(handles=leg_elements + sym_type_h, title="交通网络与枢纽标识", ncol=2, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="综合枢纽节点索引", ncol=2, fontsize=6.8, title_fontsize=7.6),
], top=-0.010, gap=0.014)

ax.set_title("湖南省综合立体交通与骨干高铁网络图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Integrated Transportation Network & High-Speed Rail Hubs of Hunan Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：湖南省交通运输厅 · 综合立体交通网规划纲要 · 制作：《中国地理知识手册》",
    fontsize=6.5)

f3_path = os.path.join(OUT_DIR, "fig17-00-3_湖南省综合立体交通与骨干高铁网络图.png")
fig.savefig(f3_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {f3_path}")

# =============================================================================
# Fig 17-00-4: 湖南省先进制造业集群与特色产业基地空间格局图
# =============================================================================
print("Generating Fig 17-00-4 (Advanced Manufacturing & Strategic Clusters)...")
fig, ax = plt.subplots(figsize=(10.5, 8.0), dpi=DPI)
fig.subplots_adjust(left=0.015, right=0.985, top=0.960, bottom=0.015)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

hn_prov.plot(ax=ax, facecolor="#fdfefe", edgecolor="#7f8c8d", lw=0.6, ls=":", zorder=2)
hn_prov.boundary.plot(ax=ax, color="#1a5276", lw=1.6, zorder=3)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl = mapkit.SymbolLabels(ax, fig)
sl.reserve([(0.0, 0.0, 0.40, 0.30),
            (0.50, 0.0, 1.0, 0.09),
            (0.88, 0.85, 1.0, 1.0)])

for item in HUNAN_OVERVIEW["industry_clusters"]:
    cname, clon, clat, ck = item[0], item[1], item[2], item[3]
    cx, cy = to_alb(clon, clat)
    nm, nt = mapkit.split_note(cname)
    if ck == "machinery":
        sl.add(cx, cy, nm, "machinery", note=nt, priority=0,
               marker="*", face="#78281f", size=9.5, kind_label="长沙全球工程机械先进制造集群")
    elif ck == "rail":
        sl.add(cx, cy, nm, "rail", note=nt, priority=1,
               marker="s", face="#c0392b", size=7.5, kind_label="株洲现代先进轨道交通装备集群")
    elif ck == "steel_power":
        sl.add(cx, cy, nm, "steel_power", note=nt, priority=1,
               marker="D", face="#8e44ad", size=7.2, kind_label="湘潭先进精品钢材与特种电机重型装备")
    elif ck == "petrochem":
        sl.add(cx, cy, nm, "petrochem", note=nt, priority=2,
               marker="^", face="#d35400", size=7.2, kind_label="岳阳万亿现代石化新材料产业基地")
    elif ck == "power_trans":
        sl.add(cx, cy, nm, "power_trans", note=nt, priority=2,
               marker="p", face="#196f3d", size=7.2, kind_label="衡阳特高压输变电与深井特种钢管产业集群")
    elif ck == "electronics":
        sl.add(cx, cy, nm, "electronics", note=nt, priority=2,
               marker="o", face="#154360", size=7.0, kind_label="益阳先进电子元器件与铝电解电容器基地")
    elif ck == "metals":
        sl.add(cx, cy, nm, "metals", note=nt, priority=2,
               marker="h", face="#27ae60", size=7.0, kind_label="郴州世界有色金属与稀贵金属精深加工")
    else:
        sl.add(cx, cy, nm, "tea_agri", note=nt, priority=2,
               marker="s", face="#2980b9", size=7.0, kind_label="安化黑茶与黄金茶国家地理标志生态茶带")

sym_type_h, sym_idx_h = sl.flush()

add_scalebar(ax, sb_x0, sb_y0, length_km=100)
add_compass(ax, 0.94, 0.92)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="制造与产业集群类别", ncol=2, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="战略性制造基地分布索引", ncol=1, fontsize=6.8, title_fontsize=7.6),
], top=-0.010, gap=0.014)

ax.set_title("湖南省先进制造业集群与特色产业基地空间格局图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Advanced Manufacturing Clusters & Characteristic Industrial Bases of Hunan Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：湖南省工业和信息化厅 · 现代制造业基地发展规划 · 制作：《中国地理知识手册》",
    fontsize=6.5)

f4_path = os.path.join(OUT_DIR, "fig17-00-4_湖南省先进制造业集群与特色产业基地空间格局图.png")
fig.savefig(f4_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {f4_path}")

# =============================================================================
# Fig 17-00-5: 湖南省1986—2024年夜间灯光演变与区域协调发展图
# =============================================================================
print("Generating Fig 17-00-5 (Nightlight Evolution 1986-2024)...")
fig, (ax_nl, ax_gdp) = plt.subplots(2, 1, figsize=(10.0, 8.8), dpi=DPI)
fig.patch.set_facecolor("white")

nl_df = pd.read_csv(os.path.join(DATA_DIR, "hunan_nightlight_clean.csv"))
prov_nl = nl_df.groupby("year")["sum"].sum().reset_index()

years = prov_nl["year"].values
sums = prov_nl["sum"].values

ax_nl.plot(years, sums, color="#c0392b", lw=2.2, marker="o", markersize=4.0, label="全省夜间灯光辐射总量 (DN·Pixel)")
ax_nl.fill_between(years, sums, color="#fadbd8", alpha=0.5)

annotations = [
    (1996, 68000, 1991, 120000, "长沙五一商圈与湘江两岸、京广沪昆交汇老城初现强光"),
    (2005, 175000, 2000, 260000, "长株潭一体化破土·星沙九华经开区拓荒·京珠高速沿线发光"),
    (2013, 390000, 2008, 560000, "武广与沪昆高铁相继贯通·长株潭城市群与岳衡两副组团连片跃升"),
    (2023, 820000, 2018, 990000, "强省会战略全面落地·工程机械与先进轨交集群闪耀·大湘西全域璀璨")
]

for yr, val, tx_yr, tx_val, text in annotations:
    ax_nl.annotate(text, xy=(yr, val), xytext=(tx_yr, tx_val),
                   arrowprops=dict(arrowstyle="->", color="#922b21", lw=1.0),
                   fontsize=7.2, fontweight="bold", color="#78281f",
                   bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffffff", edgecolor="#e74c3c", alpha=0.9))

ax_nl.set_title("湖南省 1986—2024 年夜间灯光遥感辐射总量跃升轨迹", fontsize=11.0, fontweight="bold", color=C_TEXT)
ax_nl.set_ylabel("夜光总量辐射积分 (DN)", fontsize=8.0, color="#2c3e50")
ax_nl.grid(True, linestyle="--", alpha=0.5)
ax_nl.tick_params(labelsize=7.5)

gdp_data = {
    2000: 3551.0,
    2005: 6596.0,
    2010: 16038.0,
    2015: 28902.0,
    2020: 41781.0,
    2022: 48670.0,
    2023: 50013.0,
    2024: 53230.0
}
gyears = list(gdp_data.keys())
gvals = list(gdp_data.values())

bars = ax_gdp.bar(gyears, gvals, width=1.5, color="#1b4f72", edgecolor="#0b2545", alpha=0.88, label="全省地区生产总值 (GDP, 亿元)")
for bar in bars:
    h = bar.get_height()
    ax_gdp.text(bar.get_x() + bar.get_width() / 2.0, h + 800, f"{h:g}",
                ha="center", va="bottom", fontsize=7.0, fontweight="bold", color="#0b2545")

ax_gdp.set_title("湖南省 2000—2024 年地区生产总值 (GDP) 历史性跨越 (亿元)", fontsize=11.0, fontweight="bold", color=C_TEXT)
ax_gdp.set_ylabel("GDP (亿元)", fontsize=8.0, color="#2c3e50")
ax_gdp.set_xlabel("年份 Year", fontsize=8.0, color="#2c3e50")
ax_gdp.grid(True, linestyle="--", alpha=0.5)
ax_gdp.tick_params(labelsize=7.5)

fig.tight_layout(pad=2.5)
fig.text(0.5, 0.015, "数据源：历年夜间灯光遥感数据 · 湖南统计年鉴与历年国民经济和社会发展统计公报 · 制作：《中国地理知识手册》",
         ha="center", va="bottom", fontsize=6.8, color="#7f8c8d")

f5_path = os.path.join(OUT_DIR, "fig17-00-5_湖南省1986—2024年夜间灯光演变与区域协调发展图.png")
fig.savefig(f5_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {f5_path}")

print("\nAll 5 Hunan Overview Figures successfully generated!")
