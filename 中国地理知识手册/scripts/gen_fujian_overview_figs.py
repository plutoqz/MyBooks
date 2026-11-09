# -*- coding: utf-8 -*-
"""福建省地理统揽专题地图生成引擎（13-00）
包含 5 幅全省权威出版级地图与分析图表（精细调优排版、微缩字号、严格杜绝压盖）：
1. fig13-00-1_福建省地势起伏与山海交融水系格局图.png
2. fig13-00-2_福建省行政区划与“两极两带六轴”空间格局图.png
3. fig13-00-3_福建省综合立体交通与两岸融合出海网络图.png
4. fig13-00-4_福建省新兴产业集群与先进制造基地空间格局图.png
5. fig13-00-5_福建省1986—2024年夜间灯光演变与区域协调发展图.png
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

print("Loading Fujian provincial boundaries and DEM...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

fj_prov = gpd.read_file(os.path.join(DATAV_DIR, "350000_full.json")).to_crs(ALBERS)
fj_prov["geometry"] = fj_prov.geometry.buffer(0)
fj_union = fj_prov.union_all()

b = fj_prov.total_bounds
span_x = b[2] - b[0]
span_y = b[3] - b[1]
pad_x = span_x * 0.04
pad_y = span_y * 0.04
ax_xlim = (b[0] - pad_x, b[2] + pad_x)
ax_ylim = (b[1] - pad_y, b[3] + pad_y)

# 加载 DEM
dem_file = os.path.join(DATA_DIR, "dem", "province", "350000_z9.npz")
dem_data = np.load(dem_file)
step = 2
dem_raw = np.nan_to_num(dem_data['dem'][::step, ::step], nan=0.0)
dem_res = float(dem_data['res']) * step
dem_minx = float(dem_data['minx'])
dem_maxy = float(dem_data['maxy'])
dem_extent = (dem_minx, dem_minx + dem_raw.shape[1] * dem_res,
              dem_maxy - dem_raw.shape[0] * dem_res, dem_maxy)
print(f"Downsampled Fujian DEM shape: {dem_raw.shape}, res: {dem_res}m")

# =============================================================================
# 1. 地势起伏与山海交融水系格局图 (fig13-00-1)
# =============================================================================
print("Generating Fig 13-00-1 (Topography & Mountain-Sea Water Pattern)...")
fig, ax = plt.subplots(figsize=(9.2, 10.2), dpi=DPI)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

# 色阶
elev_colors = [
    (0.00, "#196f3d"),  # 沿海平原低地
    (0.10, "#27ae60"),  # 丘陵
    (0.22, "#7dcea0"),  # 低山
    (0.38, "#f9e79f"),  # 中山
    (0.55, "#eb984e"),  # 中高山
    (0.72, "#ba4a00"),  # 高山
    (1.00, "#78281f")   # 极顶 (黄岗山 2160.8m)
]
cmap_fj = LinearSegmentedColormap.from_list("fujian_elev", elev_colors)
norm_fj = Normalize(vmin=0, vmax=2200)

hs_fj = calc_hillshade(dem_raw, dem_res)
rgb_dem = cmap_fj(norm_fj(dem_raw))[:, :, :3]
rgb_shaded = rgb_dem * (0.42 + 0.58 * hs_fj[:, :, np.newaxis])

im = ax.imshow(rgb_shaded, extent=dem_extent, origin="upper", zorder=2)
patch1 = get_mpl_clip_patch(fj_union)
ax.add_patch(patch1)
im.set_clip_path(patch1)

# 省界与设区市界
fj_prov.boundary.plot(ax=ax, color="#1a5276", lw=0.7, ls="--", zorder=4)
gpd.GeoSeries([fj_union], crs=ALBERS).boundary.plot(ax=ax, color="#0b2545", lw=1.8, zorder=5)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl1 = mapkit.SymbolLabels(ax, fig)
sl1.reserve([(0.0, 0.0, 0.35, 0.28),
             (0.55, 0.0, 1.0, 0.09),
             (0.88, 0.86, 1.0, 1.0)])

# 核心山峰
peaks = [
    ("黄岗山 (2160.8m 武夷山主峰·华东第一高峰)", 117.755, 27.895, 2160.8, -160, 60),
    ("大戴云峰 (1856.0m 德化县·闽中戴云山第一峰)", 118.245, 25.685, 1856.0, 150, 50),
    ("石谷解 (1803.3m 仙游县·莆田最高峰)", 118.665, 25.595, 1803.3, 140, 50),
    ("山羊尖 (1649.0m 寿宁县·宁德最高峰)", 119.575, 27.465, 1649.0, 150, 50),
    ("狗爪脑 (1811.0m 长汀县·龙岩最高峰)", 116.355, 25.685, 1811.0, -150, 50),
    ("大尖山 (1416.0m 平和县·漳州最高峰)", 117.295, 24.365, 1416.0, -140, 50),
    ("云顶山 (1175.2m 同安区·厦门最高峰)", 118.155, 24.735, 1175.2, 140, -40),
    ("白石顶 (1858.0m 建宁县·三明最高峰)", 116.855, 26.855, 1858.0, -150, 50)
]
for pname, plon, plat, pelev, ox, oy in peaks:
    px, py = to_alb(plon, plat)
    nm, nt = mapkit.split_note(pname)
    sl1.add(px, py, nm, "peak", note=nt, priority=1,
            marker="^", face="#78281f", size=7.5, kind_label="全省控制性极顶 / 名山高峰")

# 核心水系与海湾
waters = [
    ("闽江干流 (562km 穿延平汇入东海)", 119.050, 26.150),
    ("九龙江 (258km 汇入厦门湾黄金出海口)", 117.850, 24.450),
    ("晋江 (182km 泉州母亲河催生千亿轻工)", 118.550, 24.850),
    ("汀江 (285km 客家母亲河南入广东韩江)", 116.600, 25.100),
    ("赛江/交溪 (175km 流经福安入三都澳)", 119.650, 26.900),
    ("木兰溪 (105km 全国首条全流域生态示范水系)", 119.020, 25.380),
    ("三都澳天然深水良港 (良港三都天下无)", 119.680, 26.650),
    ("湄洲湾 (深水良港与石化LNG能源基地)", 119.050, 25.120),
    ("厦门湾与鼓浪屿 (海上花园之核)", 118.060, 24.430),
    ("平潭海坛海峡与平潭岛 (全省第一大岛)", 119.780, 25.500)
]
for wname, wlon, wlat in waters:
    wx, wy = to_alb(wlon, wlat)
    nm, nt = mapkit.split_note(wname)
    sl1.add(wx, wy, nm, "water", note=nt, priority=2,
            marker="s", face="#1f618d", size=5.5, kind_label="骨干河流水系 / 深水良港海湾")

sym_type_h, sym_idx_h = sl1.flush()

sb_x0 = ax_xlim[0] + (ax_xlim[1] - ax_xlim[0]) * 0.58
sb_y0 = ax_ylim[0] + (ax_ylim[1] - ax_ylim[0]) * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=80)
add_compass(ax, 0.94, 0.92)

cax = ax.inset_axes([0.05, 0.06, 0.025, 0.22])
cb = plt.colorbar(plt.cm.ScalarMappable(norm=norm_fj, cmap=cmap_fj), cax=cax, orientation="vertical")
cb.set_label("高程 Elevation (m)", fontsize=7.2, color="#2c3e50")
cb.ax.tick_params(labelsize=6.5, length=2.0)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="地形与水系要素", ncol=2, fontsize=7.0, title_fontsize=7.8),
    dict(handles=sym_idx_h, title="图上要素编号对照", ncol=2, fontsize=6.8, title_fontsize=7.8),
], top=-0.010, gap=0.014)

ax.set_title("福建省地势起伏与山海交融水系格局图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Macroscopic Topography, Mountain Ridges & River-Sea Estuary Pattern of Fujian Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：AWS Terrain GLO-30 30m DEM · 自然资源部标准地图 · 制作：《中国地理知识手册》",
    fontsize=6.8)

p1 = os.path.join(OUT_DIR, "fig13-00-1_福建省地势起伏与山海交融水系格局图.png")
fig.savefig(p1, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {p1}")

# =============================================================================
# 2. 行政区划与“两极两带六轴”空间格局图 (fig13-00-2)
# =============================================================================
print("Generating Fig 13-00-2 (Administrative & '2 Poles 2 Belts 6 Axes')...")
fig, ax = plt.subplots(figsize=(9.2, 10.2), dpi=DPI)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

# 设区市分区着色
city_colors = {
    "350100": "#ebf5fb",  # 福州
    "350200": "#e8f8f5",  # 厦门
    "350300": "#fef9e7",  # 莆田
    "350400": "#eafaf1",  # 三明
    "350500": "#fbfcfc",  # 泉州
    "350600": "#fef5e7",  # 漳州
    "350700": "#eaf2f8",  # 南平
    "350800": "#f4ecf7",  # 龙岩
    "350900": "#f9ebea",  # 宁德
}

for _, row in fj_prov.iterrows():
    adcode = str(row.get("adcode", ""))
    fc = city_colors.get(adcode, "#f8f9fa")
    gpd.GeoSeries([row.geometry], crs=ALBERS).plot(ax=ax, facecolor=fc, edgecolor="#7f8c8d", lw=0.7, ls="--", zorder=3)

gpd.GeoSeries([fj_union], crs=ALBERS).boundary.plot(ax=ax, color="#1a5276", lw=2.2, zorder=5)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl2 = mapkit.SymbolLabels(ax, fig)
sl2.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.55, 0.0, 1.0, 0.09),
             (0.88, 0.86, 1.0, 1.0)])

# 9 设区市行政中心与平潭
admin_capitals = [
    ("福州市 (省会·鼓楼区·三坊七巷·福州都市圈核)", 119.300, 26.085, "gov"),
    ("厦门市 (副省级·特区·思明区·厦漳泉都市圈核)", 118.085, 24.475, "gov"),
    ("泉州市 (丰泽区·世遗之城·民营经济之都)", 118.665, 24.875, "gov"),
    ("漳州市 (芗城区·九龙江下游·食品与石化名城)", 117.655, 24.515, "gov"),
    ("莆田市 (城厢区·文献名邦·妈祖故里与鞋都)", 119.005, 25.435, "gov"),
    ("宁德市 (蕉城区·全球锂电新能源之都)", 119.525, 26.665, "gov"),
    ("南平市 (建阳区·武夷山双世遗·理学名城)", 118.115, 27.335, "gov"),
    ("三明市 (三元区·中国绿都·医改林改策源地)", 117.635, 26.265, "gov"),
    ("龙岩市 (新罗区·古田红土地·紫金矿业发祥地)", 117.035, 25.075, "gov"),
    ("平潭综合实验区 (平潭岛·两岸融合前沿示范)", 119.785, 25.505, "subdistrict")
]

for aname, alon, alat, akind in admin_capitals:
    ax_pt, ay_pt = to_alb(alon, alat)
    m = "*" if akind == "gov" else "s"
    c = "#c0392b" if "福州" in aname or "厦门" in aname else ("#d35400" if akind == "gov" else "#2980b9")
    nm, nt = mapkit.split_note(aname)
    sl2.add(ax_pt, ay_pt, nm, akind, note=nt, priority=1,
            marker=m, face=c, size=9.0 if akind == "gov" else 6.5,
            kind_label="设区市行政中心 · 战略支点")

sym_type_h, sym_idx_h = sl2.flush()

add_scalebar(ax, sb_x0, sb_y0, length_km=80)
add_compass(ax, 0.94, 0.92)

leg_elements = [
    Patch(facecolor="#ebf5fb", edgecolor="#1a5276", label="福州都市圈辐射极核 (福州/平潭/莆田/宁德协同)"),
    Patch(facecolor="#e8f8f5", edgecolor="#16a085", label="厦漳泉都市圈辐射极核 (厦门/泉州/漳州强强联动)"),
    Patch(facecolor="#eafaf1", edgecolor="#27ae60", label="绿色生态发展带 (南平/三明/龙岩国家生态文明区)")
]

leg = mapkit.stacked_legends(ax, [
    dict(handles=leg_elements + sym_type_h, title="行政中心与空间战略", ncol=1, fontsize=7.0, title_fontsize=7.8),
    dict(handles=sym_idx_h, title="图上设区市定位索引", ncol=1, fontsize=6.8, title_fontsize=7.8),
], top=-0.010, gap=0.014)

ax.set_title("福建省行政区划与“两极两带六轴”空间格局图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Administrative Divisions & '2 Poles 2 Belts 6 Axes' Spatial Structure of Fujian",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：自然资源部标准地图与 DataV 行政区划 · 福建省国土空间规划 · 制作：《中国地理知识手册》",
    fontsize=6.8)

p2 = os.path.join(OUT_DIR, "fig13-00-2_福建省行政区划与“两极两带六轴”空间格局图.png")
fig.savefig(p2, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {p2}")

# =============================================================================
# 3. 综合立体交通与两岸融合出海网络图 (fig13-00-3)
# =============================================================================
print("Generating Fig 13-00-3 (Transport & Cross-Strait Outbound Network)...")
fig, ax = plt.subplots(figsize=(9.2, 10.2), dpi=DPI)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

fj_prov.plot(ax=ax, facecolor="#fdfefe", edgecolor="#bdc3c7", lw=0.6, ls=":", zorder=2)
gpd.GeoSeries([fj_union], crs=ALBERS).boundary.plot(ax=ax, color="#1a5276", lw=1.8, zorder=3)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl3 = mapkit.SymbolLabels(ax, fig)
sl3.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.55, 0.0, 1.0, 0.09),
             (0.88, 0.86, 1.0, 1.0)])

# 交通与港口地标
transport_hubs = [
    ("福州站与福州南站 (东南沿海高铁大型客运枢纽)", 119.320, 26.110, "rail_hub"),
    ("厦门北站 (福厦、厦深高铁特大型枢纽)", 118.075, 24.635, "rail_hub"),
    ("福厦高铁泉州湾跨海大桥 (首条时速350km跨海高铁)", 118.720, 24.850, "corridor"),
    ("平潭海峡公铁两用大桥 (超级跨海公铁综合工程)", 119.680, 25.680, "corridor"),
    ("厦门港集装箱码头 (全球第十三大集装箱海港)", 118.030, 24.460, "port"),
    ("福州江阴港区与罗源湾港 (海丝核心集装箱深水港)", 119.385, 25.435, "port"),
    ("湄洲湾港与古雷石化港区 (万吨级液体化工大港)", 118.980, 25.150, "port"),
    ("厦门翔安国际机场 (在建4F级国际航空枢纽港)", 118.235, 24.545, "airport"),
    ("福州长乐国际机场 (年吞吐千万级海丝空港)", 119.660, 25.930, "airport"),
    ("武夷山机场与泉州晋江国际机场", 118.000, 27.670, "airport")
]

for tname, tlon, tlat, tkind in transport_hubs:
    tx_pt, ty_pt = to_alb(tlon, tlat)
    nm, nt = mapkit.split_note(tname)
    sl3.add(tx_pt, ty_pt, nm, tkind, note=nt)

sym_type_h, sym_idx_h = sl3.flush()

add_scalebar(ax, sb_x0, sb_y0, length_km=80)
add_compass(ax, 0.94, 0.92)

leg_elements = [
    Line2D([0], [0], color="#c0392b", lw=2.2, label="福厦客专/京福/龙龙高速铁路通道"),
    Line2D([0], [0], color="#8e44ad", lw=1.8, label="国际航空空港/深水海港外贸港区"),
    Line2D([0], [0], color="#2980b9", lw=1.8, label="国家高速公路网/特大型跨海大桥")
]

leg = mapkit.stacked_legends(ax, [
    dict(handles=leg_elements + sym_type_h, title="交通通道与枢纽类型", ncol=1, fontsize=7.0, title_fontsize=7.8),
    dict(handles=sym_idx_h, title="图上综合交通节点索引", ncol=1, fontsize=6.8, title_fontsize=7.8),
], top=-0.010, gap=0.014)

ax.set_title("福建省综合立体交通与两岸融合出海网络图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Integrated Transport Infrastructure & Maritime Silk Road Gateway of Fujian",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：福建省交通运输厅 · 综合立体交通网规划 · 制作：《中国地理知识手册》",
    fontsize=6.8)

p3 = os.path.join(OUT_DIR, "fig13-00-3_福建省综合立体交通与两岸融合出海网络图.png")
fig.savefig(p3, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {p3}")

# =============================================================================
# 4. 新兴产业集群与先进制造基地空间格局图 (fig13-00-4)
# =============================================================================
print("Generating Fig 13-00-4 (Emerging Industry Clusters & Advanced Manufacturing)...")
fig, ax = plt.subplots(figsize=(9.2, 10.2), dpi=DPI)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

fj_prov.plot(ax=ax, facecolor="#fdfefe", edgecolor="#bdc3c7", lw=0.6, ls=":", zorder=2)
gpd.GeoSeries([fj_union], crs=ALBERS).boundary.plot(ax=ax, color="#1a5276", lw=1.8, zorder=3)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl4 = mapkit.SymbolLabels(ax, fig)
sl4.reserve([(0.0, 0.0, 0.40, 0.34),
             (0.55, 0.0, 1.0, 0.09),
             (0.88, 0.86, 1.0, 1.0)])

# 核心产业集群地标
industries = [
    ("宁德时代总部基地 (全球动力电池与储能第一强)", 119.545, 26.685, "锂电新能源"),
    ("青拓集团不锈钢新材料基地 (全球不锈钢巨头)", 119.780, 26.850, "高端金属"),
    ("晋江鞋服与体育用品集群 (安踏/特步/361度总部)", 118.585, 24.815, "鞋服轻工"),
    ("德化中国瓷都国际陶瓷创新园 (世界瓷都百年窑火)", 118.245, 25.495, "特色轻工"),
    ("厦门天马微电子与三安光电化合物半导体基地", 118.010, 24.580, "电子信息"),
    ("长乐中国东南大数据产业园与恒申纺织基地", 119.535, 25.925, "数字与纺织"),
    ("漳州古雷石化基地 (全国七大石化基地之一)", 117.625, 23.775, "绿色石化"),
    ("泉港石化工业区 (炼化一体化百亿工程)", 118.915, 25.215, "绿色石化"),
    ("龙岩紫金矿业全球研发总部与金铜深加工基地", 116.425, 25.055, "有色金属"),
    ("三明三钢闽光智能工厂与高端氟化工新材料园", 117.625, 26.265, "特种钢铁")
]

ind_palette = [
    ("#c0392b", "o", "锂电新能源/储能极核"),
    ("#1f618d", "s", "现代轻纺/全球鞋服之都"),
    ("#16a085", "D", "集成电路/半导体显示"),
    ("#d35400", "^", "石油化工/临港新材料"),
    ("#7d3c98", "p", "有色金属/特种钢铁先进装备")
]

for idx, (iname, ilon, ilat, idesc) in enumerate(industries):
    ix_pt, iy_pt = to_alb(ilon, ilat)
    color, marker, kind_lbl = ind_palette[idx % len(ind_palette)]
    nm, nt = mapkit.split_note(iname)
    sl4.add(ix_pt, iy_pt, nm, f"ind_{idx}", note=idesc, priority=1,
            marker=marker, face=color, size=7.5, kind_label=kind_lbl)

sym_type_h, sym_idx_h = sl4.flush()

add_scalebar(ax, sb_x0, sb_y0, length_km=80)
add_compass(ax, 0.94, 0.92)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="战略性支柱产业类别", ncol=1, fontsize=7.0, title_fontsize=7.8),
    dict(handles=sym_idx_h, title="图上先进制造龙头基地索引", ncol=1, fontsize=6.8, title_fontsize=7.8),
], top=-0.010, gap=0.014)

ax.set_title("福建省新兴产业集群与先进制造基地空间格局图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Spatial Clusters of Emerging Industries & Modern Manufacturing in Fujian",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：福建省工业和信息化厅 · 先进制造业集群规划 · 制作：《中国地理知识手册》",
    fontsize=6.8)

p4 = os.path.join(OUT_DIR, "fig13-00-4_福建省新兴产业集群与先进制造基地空间格局图.png")
fig.savefig(p4, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {p4}")

# =============================================================================
# 5. 1986—2024年夜间灯光演变与区域协调发展图 (fig13-00-5)
# =============================================================================
print("Generating Fig 13-00-5 (Nightlight Evolution 1986-2024)...")
fig, (ax_nl, ax_gdp) = plt.subplots(2, 1, figsize=(9.5, 8.5), dpi=DPI)
fig.patch.set_facecolor("white")

nl_clean_df = pd.read_csv(os.path.join(DATA_DIR, "fujian_nightlight_clean.csv"))
nl_prov = nl_clean_df.groupby("year")["sum"].sum().reset_index()

if len(nl_prov) > 0:
    years = nl_prov["year"].values
    sums = nl_prov["sum"].values
    ax_nl.plot(years, sums, color="#c0392b", lw=2.2, marker="o", markersize=4.0, label="福建省夜间灯光辐射总量 (DN·Pixel)")
    ax_nl.fill_between(years, sums, color="#f9ebea", alpha=0.55)

    max_sum = max(sums)
    annotations = [
        (1996, "厦门经济特区开发与福州马尾沿海开放原点集聚"),
        (2005, "“晋江经验”引领民营经济爆发，泉州厦漳城市走廊快速连绵"),
        (2013, "宁德时代横空出世、高铁全面成网与自贸试验区扬帆出海")
    ]
    for y_pt, note in annotations:
        sub_pt = nl_prov[nl_prov["year"] == y_pt]
        if not sub_pt.empty:
            real_val = float(sub_pt["sum"].values[0])
            ty = real_val + max_sum * 0.18
            if ty > max_sum * 1.12:
                ty = real_val - max_sum * 0.16
            ax_nl.annotate(note, xy=(y_pt, real_val), xytext=(y_pt - 4.5, ty),
                           arrowprops=dict(arrowstyle="->", color="#922b21", lw=0.9),
                           fontsize=7.2, fontweight="bold", color="#78281f",
                           bbox=dict(boxstyle="round,pad=0.25", facecolor="#ffffff", edgecolor="#e74c3c", alpha=0.92))

ax_nl.set_title("福建省 1986—2024 年夜间灯光辐射时序跃迁演进", fontsize=11.0, fontweight="bold", color=C_TEXT)
ax_nl.set_ylabel("全省夜光总量积分 (DN)", fontsize=7.8, color="#2c3e50")
ax_nl.grid(True, linestyle="--", alpha=0.4)
ax_nl.tick_params(labelsize=7.0)

# 福建省历年 GDP 柱状图
gdp_series = {
    2000: 3920.1, 2005: 6560.1, 2010: 14737.1, 2015: 25979.8,
    2020: 43903.9, 2022: 53109.8, 2023: 54355.0, 2024: 57500.0
}
gyears = list(gdp_series.keys())
gvals = list(gdp_series.values())
bars = ax_gdp.bar(gyears, gvals, width=1.4, color="#1b4f72", edgecolor="#0b2545", alpha=0.85, label="地区生产总值 (GDP, 亿元)")
for bar in bars:
    h = bar.get_height()
    ax_gdp.text(bar.get_x() + bar.get_width() / 2.0, h + max(gvals) * 0.015, f"{h:g}",
                ha="center", va="bottom", fontsize=6.8, fontweight="bold", color="#0b2545")

ax_gdp.set_title("福建省 2000—2024 年全省经济总量 (GDP) 历史跨越", fontsize=11.0, fontweight="bold", color=C_TEXT)
ax_gdp.set_ylabel("GDP (亿元)", fontsize=7.8, color="#2c3e50")
ax_gdp.set_xlabel("年份 Year", fontsize=7.8, color="#2c3e50")
ax_gdp.grid(True, linestyle="--", alpha=0.4)
ax_gdp.tick_params(labelsize=7.0)

fig.tight_layout(pad=2.5)
fig.text(0.5, 0.01, "数据来源：夜间灯光遥感时序数据集 (1986-2024) · 福建统计年鉴与历年国民经济和社会发展统计公报 · 制作：《中国地理知识手册》",
         ha="center", va="bottom", fontsize=6.8, color="#7f8c8d")

p5 = os.path.join(OUT_DIR, "fig13-00-5_福建省1986—2024年夜间灯光演变与区域协调发展图.png")
fig.savefig(p5, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {p5}")

print("\n=== ALL 5 OVERVIEW FIGURES FOR FUJIAN COMPLETED SUCCESSFULLY! ===")
