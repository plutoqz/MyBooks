# -*- coding: utf-8 -*-
"""广西壮族自治区地理统揽专题地图生成引擎（19-00）
包含 5 幅全区权威出版级地图与分析图表（精细调优排版、微缩字号、严格杜绝压盖）：
1. fig19-00-1_广西壮族自治区地势起伏与珠江水系出海格局图.png
2. fig19-00-2_广西壮族自治区行政区划与四大板块空间格局图.png
3. fig19-00-3_广西壮族自治区综合立体交通与陆海新通道网络图.png
4. fig19-00-4_广西壮族自治区重点产业园区与重大文旅基地分布图.png
5. fig19-00-5_广西壮族自治区1986—2024年夜间灯光演变与区域协调发展图.png
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
from guangxi_configs import GUANGXI_OVERVIEW

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

print("Loading Guangxi provincial boundaries and DEM...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

gx_prov = gpd.read_file(os.path.join(DATAV_DIR, "450000_full.json")).to_crs(ALBERS)
gx_prov["geometry"] = gx_prov.geometry.buffer(0)
gx_union = gx_prov.union_all()

b = gx_prov.total_bounds
span_x = b[2] - b[0]
span_y = b[3] - b[1]
pad_x = span_x * 0.04
pad_y = span_y * 0.04
ax_xlim = (b[0] - pad_x, b[2] + pad_x)
ax_ylim = (b[1] - pad_y, b[3] + pad_y)

# 加载 DEM
dem_file = os.path.join(DATA_DIR, "dem", "province", "450000_z9.npz")
dem_data = np.load(dem_file)
step = 2
dem_raw = np.nan_to_num(dem_data['dem'][::step, ::step], nan=0.0)
dem_raw = np.clip(dem_raw, 0.0, 3000.0)  # 过滤异常负值
res = float(dem_data['res']) * step
minx = float(dem_data['minx'])
maxy = float(dem_data['maxy'])
extent = (minx, minx + dem_raw.shape[1] * res, maxy - dem_raw.shape[0] * res, maxy)
print(f"Downsampled Guangxi DEM shape: {dem_raw.shape}, res: {res}m")

# =============================================================================
# Fig 19-00-1: 广西壮族自治区地势起伏与珠江水系出海格局图
# =============================================================================
print("Generating Fig 19-00-1 (Topography & Water System)...")
fig, ax = plt.subplots(figsize=(11.0, 7.8), dpi=DPI)
fig.subplots_adjust(left=0.015, right=0.985, top=0.960, bottom=0.015)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

cdict = {
    'red':   [(0.0, 0.22, 0.22), (0.15, 0.45, 0.45), (0.4, 0.88, 0.88), (0.7, 0.75, 0.75), (1.0, 0.40, 0.40)],
    'green': [(0.0, 0.55, 0.55), (0.15, 0.75, 0.75), (0.4, 0.82, 0.82), (0.7, 0.52, 0.52), (1.0, 0.20, 0.20)],
    'blue':  [(0.0, 0.28, 0.28), (0.15, 0.40, 0.40), (0.4, 0.45, 0.45), (0.7, 0.30, 0.30), (1.0, 0.15, 0.15)]
}
cmap = LinearSegmentedColormap('gx_hypso', cdict, N=256)
norm = Normalize(vmin=0.0, vmax=2200.0)

hs = calc_hillshade(dem_raw, res, az=315, alt=45)
rgb_color = cmap(norm(dem_raw))[:, :, :3]
rgb_shaded = np.clip(rgb_color * (hs[:, :, np.newaxis] * 0.7 + 0.3), 0.0, 1.0)

im = ax.imshow(rgb_shaded, extent=extent, origin="upper", zorder=1)
patch = get_mpl_clip_patch(gx_union)
ax.add_patch(patch)
im.set_clip_path(patch)

gx_prov.boundary.plot(ax=ax, color="#1b4f72", lw=0.6, linestyle="--", alpha=0.6, zorder=3)
gpd.GeoSeries([gx_union]).boundary.plot(ax=ax, color="#0b2545", lw=1.6, zorder=4)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl = mapkit.SymbolLabels(ax, fig)
sl.reserve([(0.0, 0.0, 0.40, 0.28),
            (0.50, 0.0, 1.0, 0.09),
            (0.88, 0.85, 1.0, 1.0)])

for item in GUANGXI_OVERVIEW["landmarks_macro"]:
    pname, plon, plat, pk = item[0], item[1], item[2], item[3]
    px, py = to_alb(plon, plat)
    nm, nt = mapkit.split_note(pname)
    if pk == "peak_max":
        sl.add(px, py, nm, "peak_max", note=nt, priority=0,
               marker="^", face="#900c3f", size=9.0, kind_label="华南与全区最高峰 · 猫儿山")
    elif pk == "peak":
        sl.add(px, py, nm, "peak", note=nt, priority=1,
               marker="^", face="#784212", size=6.8, kind_label="骨干控制性山峰/高原山系")
    elif pk == "water_hub":
        sl.add(px, py, nm, "water_hub", note=nt, priority=0,
               marker="s", face="#1b4f72", size=8.0, kind_label="世纪超级工程 · 平陆运河出海枢纽")
    elif pk == "port_hub":
        sl.add(px, py, nm, "port_hub", note=nt, priority=1,
               marker="s", face="#0e6251", size=7.5, kind_label="北部湾国际门户大港")
    elif pk == "airport_hub":
        sl.add(px, py, nm, "airport_hub", note=nt, priority=1,
               marker="o", face="#154360", size=7.2, kind_label="面向东盟航空枢纽")
    else:
        sl.add(px, py, nm, "landmark", note=nt, priority=2,
               marker="*", face="#c0392b", size=8.0, kind_label="国家战略高地与重要地标")

for item in GUANGXI_OVERVIEW["rivers_macro"]:
    rname, rlon, rlat, rk = item[0], item[1], item[2], item[3]
    rx, ry = to_alb(rlon, rlat)
    nm, nt = mapkit.split_note(rname)
    sl.add(rx, ry, nm, "river", note=nt, priority=2,
           marker="o", face="#2980b9", size=6.0, kind_label="骨干河流水系与出海运河")

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

ax.set_title("广西壮族自治区地势起伏与珠江水系出海格局图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Topography, Pearl River Drainage & Beibu Gulf Outlets of Guangxi",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：AWS Terrain GLO-30 DEM · 广西壮族自治区自然资源厅标准底图 · 制作：《中国地理知识手册》",
    fontsize=6.5)

f1_path = os.path.join(OUT_DIR, "fig19-00-1_广西壮族自治区地势起伏与珠江水系出海格局图.png")
fig.savefig(f1_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {f1_path}")

# =============================================================================
# Fig 19-00-2: 广西壮族自治区行政区划与四大板块空间格局图
# =============================================================================
print("Generating Fig 19-00-2 (Administrative & Strategy Spatial Pattern)...")
fig, ax = plt.subplots(figsize=(11.0, 7.8), dpi=DPI)
fig.subplots_adjust(left=0.015, right=0.985, top=0.960, bottom=0.015)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

palette = [
    "#d4e6f1", "#d5f5e3", "#fcf3cf", "#ebdef0", "#fadbd8", "#e8f8f5",
    "#fdebd0", "#eaeded", "#f4ecf7", "#eaf2f8", "#fef9e7", "#e8f6f3",
    "#f9ebea", "#e9f7ef"
]

for idx, (_, row) in enumerate(gx_prov.iterrows()):
    color = palette[idx % len(palette)]
    gpd.GeoSeries([row.geometry]).plot(ax=ax, facecolor=color, edgecolor="#7f8c8d", lw=0.7, zorder=2)
gx_prov.boundary.plot(ax=ax, color="#1a5276", lw=1.6, zorder=3)

for _, row in gx_prov.iterrows():
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

for item in GUANGXI_OVERVIEW["strategy_nodes"]:
    sname, slon, slat, sk = item[0], item[1], item[2], item[3]
    sx, sy = to_alb(slon, slat)
    nm, nt = mapkit.split_note(sname)
    if sk == "capital":
        sl.add(sx, sy, nm, "capital", note=nt, priority=0,
               marker="*", face="#c0392b", size=9.5, kind_label="自治区首府 · 开放龙头")
    elif sk == "industry":
        sl.add(sx, sy, nm, "industry", note=nt, priority=1,
               marker="s", face="#784212", size=7.5, kind_label="广西第一工业大市 · 现代智造")
    elif sk == "tourism":
        sl.add(sx, sy, nm, "tourism", note=nt, priority=1,
               marker="o", face="#1e8449", size=7.5, kind_label="世界级旅游城市 · 山水名片")
    elif sk == "port_city":
        sl.add(sx, sy, nm, "port_city", note=nt, priority=1,
               marker="s", face="#1b4f72", size=7.5, kind_label="北部湾向海大港 · 陆海枢纽")
    else:
        sl.add(sx, sy, nm, "node", note=nt, priority=2,
               marker="D", face="#8e44ad", size=6.8, kind_label="区域中心与特色战略支点")

sym_type_h, sym_idx_h = sl.flush()

sb_x0 = ax_xlim[0] + span_x * 0.58
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=120)
add_compass(ax, 0.94, 0.92)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="战略发展节点类型", ncol=2, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="城市战略定位对照", ncol=2, fontsize=6.8, title_fontsize=7.6),
], top=-0.010, gap=0.014)

ax.set_title("广西壮族自治区行政区划与四大板块空间格局图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Administrative Divisions & Four Strategic Regions of Guangxi",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：广西壮族自治区“十四五”规划与国土空间规划 · 天地图 · 制作：《中国地理知识手册》",
    fontsize=6.5)

f2_path = os.path.join(OUT_DIR, "fig19-00-2_广西壮族自治区行政区划与四大板块空间格局图.png")
fig.savefig(f2_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {f2_path}")

# =============================================================================
# Fig 19-00-3: 广西壮族自治区综合立体交通与陆海新通道网络图
# =============================================================================
print("Generating Fig 19-00-3 (Comprehensive Transportation & Land-Sea Gateway)...")
fig, ax = plt.subplots(figsize=(11.0, 7.8), dpi=DPI)
fig.subplots_adjust(left=0.015, right=0.985, top=0.960, bottom=0.015)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

gpd.GeoSeries([gx_union]).plot(ax=ax, facecolor="#f8f9f9", edgecolor="#7f8c8d", lw=0.8, zorder=2)
gx_prov.boundary.plot(ax=ax, color="#bdc3c7", lw=0.5, linestyle=":", zorder=3)

# 绘制骨干铁路与通道示意线条
hsr_lines = [
    # 贵南高铁
    [(106.8, 25.4), (107.5, 24.8), (108.0, 24.5), (108.36, 22.82)],
    # 贵广客专
    [(109.8, 25.8), (110.3, 25.3), (111.3, 24.5), (111.5, 24.4), (112.5, 23.5)],
    # 南广高铁
    [(108.36, 22.82), (109.6, 23.1), (110.1, 23.38), (111.23, 23.41), (112.0, 23.1)],
    # 南深高铁/南凭高铁
    [(106.75, 22.1), (107.37, 22.38), (108.36, 22.82), (109.2, 22.68), (110.15, 22.6)]
]
for line in hsr_lines:
    coords = [to_alb(p[0], p[1]) for p in line]
    xs, ys = mapkit.smooth_line(coords)
    ax.plot(xs, ys, color="#c0392b", lw=2.0, linestyle="-", zorder=5, alpha=0.85)

# 平陆运河走廊
canal_line = [(109.26, 22.68), (108.85, 22.25), (108.62, 21.85)]
coords_c = [to_alb(p[0], p[1]) for p in canal_line]
c_xs, c_ys = mapkit.smooth_line(coords_c)
ax.plot(c_xs, c_ys, color="#1b4f72", lw=3.0, linestyle="--", zorder=6, label="平陆运河世纪工程")

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl = mapkit.SymbolLabels(ax, fig)
sl.reserve([(0.0, 0.0, 0.40, 0.28),
            (0.50, 0.0, 1.0, 0.09),
            (0.88, 0.85, 1.0, 1.0)])

for item in GUANGXI_OVERVIEW["transport_corridors"]:
    tname, tlon, tlat, tk = item[0], item[1], item[2], item[3]
    tx, ty = to_alb(tlon, tlat)
    nm, nt = mapkit.split_note(tname)
    if tk == "corridor":
        sl.add(tx, ty, nm, "corridor", note=nt, priority=0,
               marker="P", face="#8e44ad", size=8.0, kind_label="西部陆海新通道战略主干")
    elif tk == "canal":
        sl.add(tx, ty, nm, "canal", note=nt, priority=0,
               marker="s", face="#1b4f72", size=8.5, kind_label="平陆运河出海骨干航道")
    elif tk == "hsr":
        sl.add(tx, ty, nm, "hsr", note=nt, priority=1,
               marker="o", face="#c0392b", size=7.0, kind_label="时速350高铁枢纽大动脉")
    else:
        sl.add(tx, ty, nm, "highway", note=nt, priority=2,
               marker="D", face="#d35400", size=6.5, kind_label="黄金水道与干线高速公路")

# 增加主要海港、机场标识
hubs = [
    ("南宁吴圩国际机场 (4E级国际门户空港)", 108.170, 22.610, "airport"),
    ("北部湾港钦州自动化集装箱港区", 108.610, 21.720, "port"),
    ("防城港40万吨级散货深水港区", 108.360, 21.560, "port"),
    ("北海铁山港亿吨级临港码头", 109.530, 21.570, "port"),
    ("南宁东站 (西南特等高铁客运中枢)", 108.410, 22.840, "rail"),
    ("友谊关陆路国门口岸 (通达越南中枢)", 106.720, 22.055, "port")
]
for hname, hlon, hlat, hk in hubs:
    hx, hy = to_alb(hlon, hlat)
    nm, nt = mapkit.split_note(hname)
    sl.add(hx, hy, nm, hk, note=nt, priority=1,
           marker="s" if hk == "port" else ("^" if hk == "rail" else "o"),
           face="#154360" if hk == "port" else ("#78281f" if hk == "rail" else "#1b4f72"),
           size=7.5, kind_label="国际海港码头/空港客运枢纽/边关国门")

sym_type_h, sym_idx_h = sl.flush()

sb_x0 = ax_xlim[0] + span_x * 0.58
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=120)
add_compass(ax, 0.94, 0.92)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="立体交通基础设施分类", ncol=2, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="骨干通道与枢纽对照", ncol=2, fontsize=6.8, title_fontsize=7.6),
], top=-0.010, gap=0.014)

ax.set_title("广西壮族自治区综合立体交通与陆海新通道网络图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Comprehensive Transportation & New Western Land-Sea Corridor of Guangxi",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：中国国家铁路集团 · 交通运输部 · 广西交通运输厅 · 制作：《中国地理知识手册》",
    fontsize=6.5)

f3_path = os.path.join(OUT_DIR, "fig19-00-3_广西壮族自治区综合立体交通与陆海新通道网络图.png")
fig.savefig(f3_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {f3_path}")

# =============================================================================
# Fig 19-00-4: 广西壮族自治区重点产业园区与重大文旅基地分布图
# =============================================================================
print("Generating Fig 19-00-4 (Industrial Parks & Cultural Tourism Bases)...")
fig, ax = plt.subplots(figsize=(11.0, 7.8), dpi=DPI)
fig.subplots_adjust(left=0.015, right=0.985, top=0.960, bottom=0.015)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

gpd.GeoSeries([gx_union]).plot(ax=ax, facecolor="#fef9e7", edgecolor="#7f8c8d", lw=0.8, zorder=2)
gx_prov.boundary.plot(ax=ax, color="#d5d8dc", lw=0.6, linestyle=":", zorder=3)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl = mapkit.SymbolLabels(ax, fig)
sl.reserve([(0.0, 0.0, 0.40, 0.28),
            (0.50, 0.0, 1.0, 0.09),
            (0.88, 0.85, 1.0, 1.0)])

for item in GUANGXI_OVERVIEW["industry_clusters"]:
    cname, clon, clat, ck = item[0], item[1], item[2], item[3]
    cx, cy = to_alb(clon, clat)
    nm, nt = mapkit.split_note(cname)
    if ck in ["ict", "auto_machinery", "steel", "paper_chem", "aluminum", "power"]:
        sl.add(cx, cy, nm, "ind", note=nt, priority=0,
               marker="s", face="#c0392b" if ck=="auto_machinery" else ("#8e44ad" if ck=="ict" else "#1b4f72"),
               size=7.5, kind_label="先进制造业基地与战略性产业集群")
    elif ck in ["tourism", "cross_border"]:
        sl.add(cx, cy, nm, "tour", note=nt, priority=1,
               marker="o", face="#196f3d", size=7.5, kind_label="世界自然/文化遗产与世界级旅游度假名胜")
    else:
        sl.add(cx, cy, nm, "energy", note=nt, priority=1,
               marker="D", face="#d35400", size=7.2, kind_label="重大枢纽工程与清洁能源基地")

sym_type_h, sym_idx_h = sl.flush()

sb_x0 = ax_xlim[0] + span_x * 0.58
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=120)
add_compass(ax, 0.94, 0.92)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="产业集群与名胜类型", ncol=2, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="制造基地与文旅地标对照", ncol=2, fontsize=6.8, title_fontsize=7.6),
], top=-0.010, gap=0.014)

ax.set_title("广西壮族自治区重点产业园区与重大文旅基地分布图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Major Industrial Parks & Tourism Bases in Guangxi",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：广西工业和信息化厅 · 广西文化和旅游厅 · 制作：《中国地理知识手册》",
    fontsize=6.5)

f4_path = os.path.join(OUT_DIR, "fig19-00-4_广西壮族自治区重点产业园区与重大文旅基地分布图.png")
fig.savefig(f4_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {f4_path}")

# =============================================================================
# Fig 19-00-5: 广西壮族自治区1986—2024年夜间灯光演变与区域协调发展图
# =============================================================================
print("Generating Fig 19-00-5 (Nightlight Evolution 1986-2024)...")
fig = plt.figure(figsize=(11.5, 7.8), dpi=DPI)
fig.patch.set_facecolor("white")

# 左侧 3/5 绘制夜光曲线分析，右侧 2/5 绘制历年 GDP 柱状图
gs = fig.add_gridspec(2, 2, width_ratios=[1.3, 1.0], height_ratios=[1.0, 1.0],
                      left=0.08, right=0.96, top=0.90, bottom=0.10, wspace=0.22, hspace=0.30)

ax_nl = fig.add_subplot(gs[:, 0])
ax_gdp = fig.add_subplot(gs[0, 1])
ax_pop = fig.add_subplot(gs[1, 1])

# 读取夜光数据
nl_csv = os.path.join(DATA_DIR, "guangxi_nightlight_clean.csv")
if os.path.exists(nl_csv):
    df_nl = pd.read_csv(nl_csv)
    # 按年份聚合总和
    prov_sum = df_nl.groupby("year")["sum"].sum().reset_index()
    prov_sum = prov_sum.sort_values("year")
    years = prov_sum["year"].values
    sums = prov_sum["sum"].values

    ax_nl.plot(years, sums, color="#d35400", lw=2.2, marker="o", ms=4.0, label="全区夜间灯光辐射总量 (DN)")
    ax_nl.fill_between(years, sums, color="#fdebd0", alpha=0.5)

    # 标注重要历史节点
    milestones = [
        (1992, "南昆铁路开工与沿江开放"),
        (2004, "首届中国-东盟博览会举办"),
        (2008, "广西北部湾经济区规划实施"),
        (2013, "广西跨入高铁时代·柳南贵广通达")
    ]
    max_val = max(sums) if len(sums) > 0 else 1.0
    for yr, note in milestones:
        pt = prov_sum[prov_sum["year"] == yr]
        if not pt.empty:
            val = pt["sum"].values[0]
            ax_nl.annotate(f"{yr} {note}", xy=(yr, val), xytext=(yr - 5.5, val + max_val * 0.14),
                           arrowprops=dict(arrowstyle="->", color="#c0392b", lw=0.9),
                           fontsize=7.0, fontweight="bold", color="#78281f",
                           bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffffff", edgecolor="#e74c3c", alpha=0.9))

ax_nl.set_title("广西壮族自治区 1986—2024 年夜间灯光总辐射时序跃迁", fontsize=10.5, fontweight="bold", color=C_TEXT)
ax_nl.set_xlabel("年份 Year", fontsize=8.0, color="#2c3e50")
ax_nl.set_ylabel("夜间灯光辐射总量积分 (DN)", fontsize=8.0, color="#2c3e50")
ax_nl.grid(True, linestyle="--", alpha=0.4)
ax_nl.tick_params(labelsize=7.5)

# GDP 跃升柱状图
gdp_years = [2000, 2005, 2010, 2015, 2020, 2022, 2023, 2024]
gdp_vals = [2080.0, 3984.0, 9569.8, 16803.1, 22156.7, 26300.9, 27202.4, 28200.0]
bars = ax_gdp.bar(gdp_years, gdp_vals, width=2.0, color="#1b4f72", edgecolor="#0b2545", alpha=0.85)
for bar in bars:
    h = bar.get_height()
    ax_gdp.text(bar.get_x() + bar.get_width() / 2.0, h + 300, f"{h:,.0f}",
                ha="center", va="bottom", fontsize=6.8, fontweight="bold", color="#0b2545")

ax_gdp.set_title("全区地区生产总值 (GDP, 亿元) 跨越式跃升", fontsize=9.8, fontweight="bold", color=C_TEXT)
ax_gdp.set_ylabel("GDP (亿元)", fontsize=7.5, color="#2c3e50")
ax_gdp.set_ylim(0, 33000)
ax_gdp.grid(True, linestyle="--", alpha=0.4)
ax_gdp.tick_params(labelsize=7.2)

# 城镇化率演进曲线
ur_years = [2000, 2005, 2010, 2015, 2020, 2022, 2023, 2024]
ur_vals = [28.2, 33.6, 40.0, 47.1, 54.2, 55.7, 56.4, 57.0]
ax_pop.plot(ur_years, ur_vals, color="#27ae60", marker="s", lw=1.8, ms=4.5)
for x, y in zip(ur_years, ur_vals):
    ax_pop.text(x, y + 1.2, f"{y:.1f}%", ha="center", va="bottom", fontsize=6.8, fontweight="bold", color="#196f3d")

ax_pop.set_title("全区常住人口城镇化率 (%) 稳步攀升历程", fontsize=9.8, fontweight="bold", color=C_TEXT)
ax_pop.set_xlabel("年份 Year", fontsize=7.5, color="#2c3e50")
ax_pop.set_ylabel("城镇化率 (%)", fontsize=7.5, color="#2c3e50")
ax_pop.set_ylim(20, 68)
ax_pop.grid(True, linestyle="--", alpha=0.4)
ax_pop.tick_params(labelsize=7.2)

fig.suptitle("广西壮族自治区1986—2024年夜间灯光演变与区域协调发展图", fontsize=12.5, fontweight="bold", y=0.96, color=C_TEXT)
fig.text(0.5, 0.02, "数据来源：夜间灯光遥感时序数据集 (1986-2024) · 广西统计年鉴与国民经济和社会发展统计公报 · 制作：《中国地理知识手册》",
         ha="center", va="bottom", fontsize=7.0, color="#7f8c8d")

f5_path = os.path.join(OUT_DIR, "fig19-00-5_广西壮族自治区1986—2024年夜间灯光演变与区域协调发展图.png")
fig.savefig(f5_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {f5_path}")

print("\n=== ALL 5 GUANGXI OVERVIEW FIGURES GENERATED SUCCESSFULLY! ===")
