# -*- coding: utf-8 -*-
"""湖北省地理统揽专题地图生成引擎（16-00）
包含 5 幅全省权威出版级地图与分析图表（精细调优排版、微缩字号、严格杜绝压盖）：
1. fig16-00-1_湖北省地势起伏与长江汉江水系格局图.png
2. fig16-00-2_湖北省行政区划与“一主两翼全辐射”空间格局图.png
3. fig16-00-3_湖北省综合立体交通与多式联运枢纽网络图.png
4. fig16-00-4_湖北省新兴产业集群与先进制造基地空间格局图.png
5. fig16-00-5_湖北省1986—2024年夜间灯光演变与区域协调发展图.png
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
from hubei_configs import HUBEI_OVERVIEW

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

print("Loading Hubei provincial boundaries and DEM...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

hb_prov = gpd.read_file(os.path.join(DATAV_DIR, "420000_full.json")).to_crs(ALBERS)
hb_prov["geometry"] = hb_prov.geometry.buffer(0)
hb_union = hb_prov.union_all()

b = hb_prov.total_bounds
span_x = b[2] - b[0]
span_y = b[3] - b[1]
pad_x = span_x * 0.04
pad_y = span_y * 0.04
ax_xlim = (b[0] - pad_x, b[2] + pad_x)
ax_ylim = (b[1] - pad_y, b[3] + pad_y)

# 加载 DEM
dem_file = os.path.join(DATA_DIR, "dem", "province", "420000_z9.npz")
dem_data = np.load(dem_file)
step = 2
dem_raw = np.nan_to_num(dem_data['dem'][::step, ::step], nan=0.0)
res = float(dem_data['res']) * step
minx = float(dem_data['minx'])
maxy = float(dem_data['maxy'])
extent = (minx, minx + dem_raw.shape[1] * res, maxy - dem_raw.shape[0] * res, maxy)
print(f"Downsampled Hubei DEM shape: {dem_raw.shape}, res: {res}m")

# =============================================================================
# Fig 16-00-1: 湖北省地势起伏与长江汉江水系格局图
# =============================================================================
print("Generating Fig 16-00-1 (Topography & River Basin Pattern)...")
fig, ax = plt.subplots(figsize=(10.5, 7.6), dpi=DPI)
fig.subplots_adjust(left=0.015, right=0.985, top=0.960, bottom=0.015)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

norm = Normalize(vmin=0.0, vmax=3100.0)
dem_colors = [
    (0.00, "#196f3d"),  # 江汉平原深绿
    (0.08, "#27ae60"),  # 低丘平原
    (0.20, "#7dcea0"),  # 浅丘陵
    (0.38, "#f9e79f"),  # 丘陵低山
    (0.58, "#eb984e"),  # 中山
    (0.78, "#ba4a00"),  # 大巴武当高山
    (1.00, "#78281f")   # 神农顶华中屋脊
]
cmap = LinearSegmentedColormap.from_list("hb_dem", dem_colors)

hs = calc_hillshade(dem_raw, res)
rgb_dem = cmap(norm(dem_raw))[:, :, :3]
rgb_shaded = rgb_dem * (0.42 + 0.58 * hs[:, :, np.newaxis])

im = ax.imshow(rgb_shaded, extent=extent, origin="upper", zorder=2)
patch = get_mpl_clip_patch(hb_union)
ax.add_patch(patch)
im.set_clip_path(patch)

hb_prov.boundary.plot(ax=ax, color="#1a5276", lw=1.2, zorder=5)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl = mapkit.SymbolLabels(ax, fig)
sl.reserve([(0.0, 0.0, 0.35, 0.30),
            (0.50, 0.0, 1.0, 0.09),
            (0.88, 0.85, 1.0, 1.0)])

for item in HUBEI_OVERVIEW["landmarks_macro"]:
    name, lon, lat, k = item[0], item[1], item[2], item[3]
    x, y = to_alb(lon, lat)
    nm, nt = mapkit.split_note(name)
    if k == "peak_max":
        sl.add(x, y, nm, "peak_max", note=nt, priority=0,
               marker="^", face="#78281f", size=9.0, kind_label="华中屋脊最高绝顶 (神农顶 3106.2m)")
    elif k == "peak":
        sl.add(x, y, nm, "peak", note=nt, priority=1,
               marker="^", face="#d35400", size=7.2, kind_label="骨干名山与分水岭主峰")
    elif k == "water_dam":
        sl.add(x, y, nm, "water_dam", note=nt, priority=1,
               marker="s", face="#154360", size=7.5, kind_label="大国水利重器与特大水源地")
    elif k == "port_hub":
        sl.add(x, y, nm, "port_hub", note=nt, priority=2,
               marker="p", face="#1b4f72", size=7.0, kind_label="长江中游航运中心港区")
    elif k == "airport_hub":
        sl.add(x, y, nm, "airport_hub", note=nt, priority=2,
               marker="D", face="#6c3483", size=7.0, kind_label="国家双枢纽民用机场港区")
    else:
        sl.add(x, y, nm, "tech_cluster", note=nt, priority=2,
               marker="*", face="#c0392b", size=8.5, kind_label="国家科技创新与现代产业高地")

for item in HUBEI_OVERVIEW["rivers_macro"]:
    rname, rlon, rlat, rk = item[0], item[1], item[2], item[3]
    rx, ry = to_alb(rlon, rlat)
    nm, nt = mapkit.split_note(rname)
    sl.add(rx, ry, nm, "river", note=nt, priority=2,
           marker="o", face="#2980b9", size=6.0, kind_label="骨干河流水系与重点湖泊水库")

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

ax.set_title("湖北省地势起伏与长江汉江水系格局图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Topography, River Basin System & Strategic Water Conservancy of Hubei Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：AWS Terrain GLO-30 DEM · 湖北省自然资源厅标准底图 · 制作：《中国地理知识手册》",
    fontsize=6.5)

f1_path = os.path.join(OUT_DIR, "fig16-00-1_湖北省地势起伏与长江汉江水系格局图.png")
fig.savefig(f1_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {f1_path}")

# =============================================================================
# Fig 16-00-2: 湖北省行政区划与“一主两翼全辐射”空间格局图
# =============================================================================
print("Generating Fig 16-00-2 (Administrative & '1 Core 2 Wings' Strategy)...")
fig, ax = plt.subplots(figsize=(10.5, 7.6), dpi=DPI)
fig.subplots_adjust(left=0.015, right=0.985, top=0.960, bottom=0.015)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

palette = [
    "#d4e6f1", "#d5f5e3", "#fcf3cf", "#ebdef0", "#fadbd8", "#e8f8f5",
    "#fdebd0", "#eaeded", "#f4ecf7", "#eaf2f8", "#fef9e7", "#e8f6f3",
    "#f9ebea", "#e9f7ef", "#fdfefe", "#f5eef8", "#ebf5fb"
]

for idx, (_, row) in enumerate(hb_prov.iterrows()):
    color = palette[idx % len(palette)]
    gpd.GeoSeries([row.geometry]).plot(ax=ax, facecolor=color, edgecolor="#7f8c8d", lw=0.7, zorder=2)
hb_prov.boundary.plot(ax=ax, color="#1a5276", lw=1.6, zorder=3)

for _, row in hb_prov.iterrows():
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

for item in HUBEI_OVERVIEW["strategy_nodes"]:
    sname, slon, slat, sk = item[0], item[1], item[2], item[3]
    sx, sy = to_alb(slon, slat)
    nm, nt = mapkit.split_note(sname)
    if sk == "capital":
        sl.add(sx, sy, nm, "capital", note=nt, priority=0,
               marker="*", face="#922b21", size=10.5, kind_label="省会·国家中心城市 (一主引领)")
    elif sk == "sub_center":
        sl.add(sx, sy, nm, "sub_center", note=nt, priority=1,
               marker="s", face="#b03a2e", size=8.0, kind_label="省域副中心城市 (两翼驱动)")
    else:
        sl.add(sx, sy, nm, "node", note=nt, priority=2,
               marker="o", face="#1f618d", size=6.5, kind_label="区域骨干节点城市与特色功能区")

sym_type_h, sym_idx_h = sl.flush()

add_scalebar(ax, sb_x0, sb_y0, length_km=100)
add_compass(ax, 0.94, 0.92)

leg_elements = [
    Patch(facecolor="#fadbd8", edgecolor="#b03a2e", lw=1.5, label="武汉都市圈 (武鄂黄黄核心圈)"),
    Patch(facecolor="#d4e6f1", edgecolor="#1f618d", lw=1.5, label="襄阳都市圈 (汉江流域协同圈)"),
    Patch(facecolor="#d5f5e3", edgecolor="#196f3d", lw=1.5, label="宜荆荆都市圈 (长江中游绿色高地)")
]

leg = mapkit.stacked_legends(ax, [
    dict(handles=leg_elements + sym_type_h, title="空间战略与板块层次", ncol=2, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="主要战略枢纽点索引", ncol=2, fontsize=6.8, title_fontsize=7.6),
], top=-0.010, gap=0.014)

ax.set_title("湖北省行政区划与“一主两翼全辐射”空间格局图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Administrative Divisions & 'One Core, Two Wings' Spatial Pattern of Hubei Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：湖北省发展和改革委员会 · 国土空间总体规划 (2021—2035) · 制作：《中国地理知识手册》",
    fontsize=6.5)

f2_path = os.path.join(OUT_DIR, "fig16-00-2_湖北省行政区划与“一主两翼全辐射”空间格局图.png")
fig.savefig(f2_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {f2_path}")

# =============================================================================
# Fig 16-00-3: 湖北省综合立体交通与多式联运枢纽网络图
# =============================================================================
print("Generating Fig 16-00-3 (Transport Infrastructure & Multimodal Logistics)...")
fig, ax = plt.subplots(figsize=(10.5, 7.6), dpi=DPI)
fig.subplots_adjust(left=0.015, right=0.985, top=0.960, bottom=0.015)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

hb_prov.plot(ax=ax, facecolor="#fdfefe", edgecolor="#7f8c8d", lw=0.6, ls=":", zorder=2)
hb_prov.boundary.plot(ax=ax, color="#1a5276", lw=1.6, zorder=3)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl = mapkit.SymbolLabels(ax, fig)
sl.reserve([(0.0, 0.0, 0.38, 0.28),
            (0.50, 0.0, 1.0, 0.09),
            (0.88, 0.85, 1.0, 1.0)])

trans_points = [
    ("武汉站 (京广高铁/沪汉蓉枢纽)", 114.425, 30.608, "rail"),
    ("汉口站 (全国著名欧式大型客运枢纽)", 114.255, 30.618, "rail"),
    ("武昌站 (百年京广铁路枢纽)", 114.318, 30.528, "rail"),
    ("襄阳东站 (汉十高铁/郑渝高铁交汇大站)", 112.260, 32.070, "rail"),
    ("宜昌东站 (沪汉蓉高铁/焦柳铁路客运枢纽)", 111.365, 30.665, "rail"),
    ("荆州站 (汉宜客运专线客运枢纽)", 112.180, 30.390, "rail"),
    ("十堰东站 (汉十高铁重要枢纽客站)", 110.850, 32.660, "rail"),
    ("恩施站 (宜万铁路重要站点)", 109.490, 30.340, "rail"),
    ("武汉天河国际机场 (中部干线航空客运枢纽)", 114.210, 30.780, "airport"),
    ("鄂州花湖国际机场 (亚洲第一专业航空货运枢纽)", 115.050, 30.320, "airport"),
    ("宜昌三峡机场 (三峡门户区域民航枢纽)", 111.480, 30.555, "airport"),
    ("襄阳刘集机场 (汉江流域重要支线航空港)", 112.290, 32.150, "airport"),
    ("阳逻国际集装箱港 (长江中上游最大集装箱港)", 114.550, 30.680, "port"),
    ("黄石新港 (亿吨级长江多式联运大港)", 115.220, 30.180, "port"),
    ("白洋长江码头 (宜昌新港核心港区)", 111.550, 30.450, "port"),
    ("荆州盐卡港区 (江汉平原铁水联运门户)", 112.280, 30.300, "port")
]

for item in trans_points:
    tname, tlon, tlat, tk = item[0], item[1], item[2], item[3]
    tx, ty = to_alb(tlon, tlat)
    nm, nt = mapkit.split_note(tname)
    if tk == "rail":
        sl.add(tx, ty, nm, "rail", note=nt, priority=1,
               marker="s", face="#c0392b", size=7.2, kind_label="主要高速铁路客运特等枢纽站")
    elif tk == "airport":
        sl.add(tx, ty, nm, "airport", note=nt, priority=1,
               marker="D", face="#8e44ad", size=7.2, kind_label="国家客货运民用机场港区")
    else:
        sl.add(tx, ty, nm, "port", note=nt, priority=2,
               marker="p", face="#154360", size=7.0, kind_label="长江中游主要集装箱与多式联运港口")

sym_type_h, sym_idx_h = sl.flush()

add_scalebar(ax, sb_x0, sb_y0, length_km=100)
add_compass(ax, 0.94, 0.92)

leg_elements = [
    Line2D([0], [0], color="#c0392b", lw=2.2, label="京广/沿江/汉十高速铁路走廊"),
    Line2D([0], [0], color="#154360", lw=2.0, label="长江黄金水道万吨级深水航道"),
    Line2D([0], [0], color="#2980b9", lw=1.5, label="国家骨干高速公路通道网")
]

leg = mapkit.stacked_legends(ax, [
    dict(handles=leg_elements + sym_type_h, title="交通网络与枢纽标识", ncol=2, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="综合枢纽节点索引", ncol=2, fontsize=6.8, title_fontsize=7.6),
], top=-0.010, gap=0.014)

ax.set_title("湖北省综合立体交通与多式联运枢纽网络图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Integrated Transportation Network & Multimodal Logistics Hubs of Hubei Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：湖北省交通运输厅 · 综合立体交通网规划纲要 · 制作：《中国地理知识手册》",
    fontsize=6.5)

f3_path = os.path.join(OUT_DIR, "fig16-00-3_湖北省综合立体交通与多式联运枢纽网络图.png")
fig.savefig(f3_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {f3_path}")

# =============================================================================
# Fig 16-00-4: 湖北省新兴产业集群与先进制造基地空间格局图
# =============================================================================
print("Generating Fig 16-00-4 (Emerging Industry Clusters & Advanced Manufacturing)...")
fig, ax = plt.subplots(figsize=(10.5, 7.6), dpi=DPI)
fig.subplots_adjust(left=0.015, right=0.985, top=0.960, bottom=0.015)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

hb_prov.plot(ax=ax, facecolor="#fdfefe", edgecolor="#7f8c8d", lw=0.6, ls=":", zorder=2)
hb_prov.boundary.plot(ax=ax, color="#1a5276", lw=1.6, zorder=3)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl = mapkit.SymbolLabels(ax, fig)
sl.reserve([(0.0, 0.0, 0.40, 0.30),
            (0.50, 0.0, 1.0, 0.09),
            (0.88, 0.85, 1.0, 1.0)])

for item in HUBEI_OVERVIEW["industry_clusters"]:
    cname, clon, clat, ck = item[0], item[1], item[2], item[3]
    cx, cy = to_alb(clon, clat)
    nm, nt = mapkit.split_note(cname)
    if ck == "optics":
        sl.add(cx, cy, nm, "optics", note=nt, priority=0,
               marker="*", face="#78281f", size=9.5, kind_label="中国光谷·光电子信息与光通信基地")
    elif ck == "ict":
        sl.add(cx, cy, nm, "ict", note=nt, priority=1,
               marker="D", face="#8e44ad", size=7.5, kind_label="“光芯屏端网”万亿级先进制造基地")
    elif ck == "auto":
        sl.add(cx, cy, nm, "auto", note=nt, priority=1,
               marker="s", face="#c0392b", size=7.5, kind_label="汉十汽车走廊 (商用车与新能源汽车)")
    elif ck == "chemical":
        sl.add(cx, cy, nm, "chemical", note=nt, priority=2,
               marker="^", face="#d35400", size=7.2, kind_label="绿色磷化工与现代精细化工基地")
    elif ck == "battery":
        sl.add(cx, cy, nm, "battery", note=nt, priority=2,
               marker="p", face="#196f3d", size=7.2, kind_label="动力电池与新能源材料制造高地")
    elif ck == "hydro":
        sl.add(cx, cy, nm, "hydro", note=nt, priority=1,
               marker="o", face="#154360", size=7.5, kind_label="三峡清洁能源与梯级水电基地")
    elif ck == "agri":
        sl.add(cx, cy, nm, "agri", note=nt, priority=2,
               marker="h", face="#27ae60", size=7.0, kind_label="特色农产品加工与小龙虾全产业链")
    else:
        sl.add(cx, cy, nm, "textile", note=nt, priority=2,
               marker="s", face="#2980b9", size=7.0, kind_label="全球非织造布及医疗防护材料基地")

sym_type_h, sym_idx_h = sl.flush()

add_scalebar(ax, sb_x0, sb_y0, length_km=100)
add_compass(ax, 0.94, 0.92)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="万亿产业集群类别", ncol=2, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="战略性制造基地分布索引", ncol=1, fontsize=6.8, title_fontsize=7.6),
], top=-0.010, gap=0.014)

ax.set_title("湖北省新兴产业集群与先进制造基地空间格局图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Emerging Industrial Clusters & Advanced Manufacturing Bases of Hubei Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：湖北省经济和信息化厅 · 现代产业体系建设规划 · 制作：《中国地理知识手册》",
    fontsize=6.5)

f4_path = os.path.join(OUT_DIR, "fig16-00-4_湖北省新兴产业集群与先进制造基地空间格局图.png")
fig.savefig(f4_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {f4_path}")

# =============================================================================
# Fig 16-00-5: 湖北省1986—2024年夜间灯光演变与区域协调发展图
# =============================================================================
print("Generating Fig 16-00-5 (Nightlight Evolution 1986-2024)...")
fig, (ax_nl, ax_gdp) = plt.subplots(2, 1, figsize=(10.0, 8.8), dpi=DPI)
fig.patch.set_facecolor("white")

nl_df = pd.read_csv(os.path.join(DATA_DIR, "hubei_nightlight_clean.csv"))
prov_nl = nl_df.groupby("year")["sum"].sum().reset_index()

years = prov_nl["year"].values
sums = prov_nl["sum"].values

ax_nl.plot(years, sums, color="#c0392b", lw=2.2, marker="o", markersize=4.0, label="全省夜间灯光辐射总量 (DN·Pixel)")
ax_nl.fill_between(years, sums, color="#fadbd8", alpha=0.5)

annotations = [
    (1996, 75000, 1991, 130000, "三峡工程开工·武汉武昌汉口老城初现强光"),
    (2005, 190000, 2000, 280000, "中国光谷破土·东风车谷与汉宜沿线崛起"),
    (2013, 440000, 2008, 620000, "高铁网络交汇成型·一主两翼三大都市圈联动发光"),
    (2023, 880000, 2018, 1050000, "花湖航空港通航·武鄂黄黄都市圈连绵成片·全域夜光爆发")
]

for yr, val, tx_yr, tx_val, text in annotations:
    ax_nl.annotate(text, xy=(yr, val), xytext=(tx_yr, tx_val),
                   arrowprops=dict(arrowstyle="->", color="#922b21", lw=1.0),
                   fontsize=7.2, fontweight="bold", color="#78281f",
                   bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffffff", edgecolor="#e74c3c", alpha=0.9))

ax_nl.set_title("湖北省 1986—2024 年夜间灯光遥感辐射总量跃升轨迹", fontsize=11.0, fontweight="bold", color=C_TEXT)
ax_nl.set_ylabel("夜光总量辐射积分 (DN)", fontsize=8.0, color="#2c3e50")
ax_nl.grid(True, linestyle="--", alpha=0.5)
ax_nl.tick_params(labelsize=7.5)

gdp_data = {
    2000: 3880.0,
    2005: 6520.0,
    2010: 15967.0,
    2015: 29550.0,
    2020: 43443.0,
    2022: 53735.0,
    2023: 55803.0,
    2024: 58000.0
}
gyears = list(gdp_data.keys())
gvals = list(gdp_data.values())

bars = ax_gdp.bar(gyears, gvals, width=1.5, color="#1b4f72", edgecolor="#0b2545", alpha=0.88, label="全省地区生产总值 (GDP, 亿元)")
for bar in bars:
    h = bar.get_height()
    ax_gdp.text(bar.get_x() + bar.get_width() / 2.0, h + 800, f"{h:g}",
                ha="center", va="bottom", fontsize=7.0, fontweight="bold", color="#0b2545")

ax_gdp.set_title("湖北省 2000—2024 年地区生产总值 (GDP) 历史性跨越 (亿元)", fontsize=11.0, fontweight="bold", color=C_TEXT)
ax_gdp.set_ylabel("GDP (亿元)", fontsize=8.0, color="#2c3e50")
ax_gdp.set_xlabel("年份 Year", fontsize=8.0, color="#2c3e50")
ax_gdp.grid(True, linestyle="--", alpha=0.5)
ax_gdp.tick_params(labelsize=7.5)

fig.tight_layout(pad=2.5)
fig.text(0.5, 0.015, "数据源：历年夜间灯光遥感数据 · 湖北统计年鉴与历年国民经济和社会发展统计公报 · 制作：《中国地理知识手册》",
         ha="center", va="bottom", fontsize=6.8, color="#7f8c8d")

f5_path = os.path.join(OUT_DIR, "fig16-00-5_湖北省1986—2024年夜间灯光演变与区域协调发展图.png")
fig.savefig(f5_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {f5_path}")

print("\nAll 5 Hubei Overview Figures successfully generated!")
