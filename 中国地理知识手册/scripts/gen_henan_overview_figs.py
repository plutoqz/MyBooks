# -*- coding: utf-8 -*-
"""河南省地理统揽专题地图生成引擎（15-00）
包含 5 幅全省权威出版级地图与分析图表（精细调优排版、微缩字号、严格杜绝压盖）：
1. fig15-00-1_河南省地势起伏与四大流域水系格局图.png
2. fig15-00-2_河南省行政区划与“一核两翼三区”空间格局图.png
3. fig15-00-3_河南省综合立体交通与米字型高铁枢纽网络图.png
4. fig15-00-4_河南省新兴产业集群与先进制造基地空间格局图.png
5. fig15-00-5_河南省1986—2024年夜间灯光演变与区域协调发展图.png
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

print("Loading Henan provincial boundaries and DEM...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

hn_prov = gpd.read_file(os.path.join(DATAV_DIR, "410000_full.json")).to_crs(ALBERS)
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
dem_file = os.path.join(DATA_DIR, "dem", "province", "410000_z9.npz")
dem_data = np.load(dem_file)
step = 2
dem_raw = np.nan_to_num(dem_data['dem'][::step, ::step], nan=0.0)
dem_res = float(dem_data['res']) * step
dem_minx = float(dem_data['minx'])
dem_maxy = float(dem_data['maxy'])
dem_extent = (dem_minx, dem_minx + dem_raw.shape[1] * dem_res,
              dem_maxy - dem_raw.shape[0] * dem_res, dem_maxy)
print(f"Downsampled Henan DEM shape: {dem_raw.shape}, res: {dem_res}m")

# =============================================================================
# 1. 地势起伏与四大流域水系格局图 (fig15-00-1)
# =============================================================================
print("Generating Fig 15-00-1 (Topography & Four River Basins Pattern)...")
fig, ax = plt.subplots(figsize=(10.0, 9.2), dpi=DPI)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

# 色阶
elev_colors = [
    (0.00, "#196f3d"),  # 黄淮平原低地
    (0.06, "#27ae60"),  # 平原与缓丘
    (0.18, "#7dcea0"),  # 山前岗地
    (0.32, "#f9e79f"),  # 低山与中丘
    (0.50, "#eb984e"),  # 中山
    (0.72, "#ba4a00"),  # 高山
    (1.00, "#78281f")   # 极顶 (老鸦岔脑 2413.8m)
]
cmap_hn = LinearSegmentedColormap.from_list("henan_elev", elev_colors)
norm_hn = Normalize(vmin=0, vmax=2500)

hs_hn = calc_hillshade(dem_raw, dem_res)
rgb_dem = cmap_hn(norm_hn(dem_raw))[:, :, :3]
rgb_shaded = rgb_dem * (0.42 + 0.58 * hs_hn[:, :, np.newaxis])

im = ax.imshow(rgb_shaded, extent=dem_extent, origin="upper", zorder=2)
patch1 = get_mpl_clip_patch(hn_union)
ax.add_patch(patch1)
im.set_clip_path(patch1)

# 省界与地市界
hn_prov.boundary.plot(ax=ax, color="#1a5276", lw=0.7, ls="--", zorder=4)
gpd.GeoSeries([hn_union], crs=ALBERS).boundary.plot(ax=ax, color="#0b2545", lw=1.8, zorder=5)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl1 = mapkit.SymbolLabels(ax, fig)
sl1.reserve([(0.0, 0.0, 0.35, 0.28),
             (0.55, 0.0, 1.0, 0.09),
             (0.88, 0.86, 1.0, 1.0)])

# 核心山峰
peaks = [
    ("老鸦岔脑 (2413.8m 灵宝小秦岭主峰·中原最高绝顶)", 110.450, 34.420, 2413.8, -160, 60),
    ("老界岭鸡角尖 (2217.0m 西峡伏牛山主峰·南阳第一峰)", 111.480, 33.620, 2217.0, -150, 50),
    ("伏牛山白石尖 (2212.5m 嵩县栾川界·洛阳最高绝顶)", 111.835, 33.680, 2212.5, 150, 50),
    ("尧山玉皇顶 (2153.1m 鲁山县·平顶山第一峰)", 112.285, 33.745, 2153.1, 140, 50),
    ("十字岭 (1732.0m 辉县南太行第一峰)", 113.585, 35.750, 1732.0, 140, 50),
    ("王屋山天坛顶 (1715.7m 济源·愚公移山名岳)", 112.285, 35.155, 1715.7, -150, 50),
    ("四方垴 (1632.0m 林州太行山·安阳最高峰)", 113.725, 36.350, 1632.0, -140, 50),
    ("金刚台 (1584.0m 商城大别山主脊·信阳最高峰)", 115.520, 31.710, 1584.0, 150, -50),
    ("嵩山连天峰 (1512.0m 登封少室山·郑州第一高峰)", 113.030, 34.505, 1512.0, 140, 50),
    ("茱萸峰 (1297.6m 修武云台山绝顶·重阳登高处)", 113.375, 35.435, 1297.6, 140, 50),
    ("桐柏山太白顶 (1140.0m 桐柏县·千里淮河发源地)", 113.285, 32.350, 1140.0, 150, -50)
]
for pname, plon, plat, pelev, ox, oy in peaks:
    px, py = to_alb(plon, plat)
    nm, nt = mapkit.split_note(pname)
    sl1.add(px, py, nm, "peak", note=nt, priority=1,
            marker="^", face="#78281f", size=7.5, kind_label="全省控制性极顶 / 名山高峰")

# 核心水系与大国工程
waters = [
    ("黄河干流豫境段 (711km 穿中原高峡平湖与地上悬河)", 113.600, 34.920),
    ("淮河干流豫境段 (363km 发源桐柏山润泽豫南)", 114.800, 32.350),
    ("南水北调中线渠首与总干渠 (淅川陶岔大水网)", 111.720, 32.650),
    ("沙颍河干流 (穿漯河周口淮河最大支流通江达海)", 114.650, 33.620),
    ("丹江口水库南阳库区 (南水北调中线清澈水源地)", 111.485, 32.750),
    ("小浪底水利枢纽 (大国重器调水调沙黄河明珠)", 112.435, 34.920),
    ("黄河三门峡大坝 (万里黄河第一坝中流砥柱)", 111.350, 34.825),
    ("宿鸭湖水库 (亚洲最大平原人工湖候鸟天堂)", 114.285, 33.025),
    ("卫河与海河水系 (豫北重要排涝与生态大网)", 114.300, 35.600),
    ("白河水系 (纵贯南阳盆地南入长江汉江)", 112.530, 32.950)
]
for wname, wlon, wlat in waters:
    wx, wy = to_alb(wlon, wlat)
    nm, nt = mapkit.split_note(wname)
    sl1.add(wx, wy, nm, "water", note=nt, priority=2,
            marker="s", face="#1f618d", size=5.5, kind_label="四大流域骨干水系 / 水利枢纽工程")

sym_type_h, sym_idx_h = sl1.flush()

sb_x0 = ax_xlim[0] + (ax_xlim[1] - ax_xlim[0]) * 0.58
sb_y0 = ax_ylim[0] + (ax_ylim[1] - ax_ylim[0]) * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=80)
add_compass(ax, 0.94, 0.92)

cax = ax.inset_axes([0.05, 0.06, 0.025, 0.22])
cb = plt.colorbar(plt.cm.ScalarMappable(norm=norm_hn, cmap=cmap_hn), cax=cax, orientation="vertical")
cb.set_label("高程 Elevation (m)", fontsize=7.2, color="#2c3e50")
cb.ax.tick_params(labelsize=6.5, length=2.0)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="地形与水文要素", ncol=2, fontsize=7.0, title_fontsize=7.8),
    dict(handles=sym_idx_h, title="图上要素编号对照", ncol=2, fontsize=6.8, title_fontsize=7.8),
], top=-0.010, gap=0.014)

ax.set_title("河南省地势起伏与四大流域水系格局图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Macroscopic Topography, Mountain Ridges & Four River Basins Pattern of Henan",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：AWS Terrain GLO-30 30m DEM · 自然资源部标准地图 · 制作：《中国地理知识手册》",
    fontsize=6.8)

p1 = os.path.join(OUT_DIR, "fig15-00-1_河南省地势起伏与四大流域水系格局图.png")
fig.savefig(p1, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {p1}")

# =============================================================================
# 2. 行政区划与“一核两翼三区”空间格局图 (fig15-00-2)
# =============================================================================
print("Generating Fig 15-00-2 (Administrative & '1 Core 2 Wings 3 Zones')...")
fig, ax = plt.subplots(figsize=(10.0, 9.2), dpi=DPI)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

# 分区着色
city_colors = {
    "410100": "#ebf5fb",  # 郑州 (核心)
    "410200": "#fef9e7",  # 开封 (郑开同城)
    "410300": "#e8f8f5",  # 洛阳 (副中心)
    "410400": "#f4ecf7",  # 平顶山
    "410500": "#fbfcfc",  # 安阳 (豫北)
    "410600": "#ebedef",  # 鹤壁 (豫北)
    "410700": "#eaf2f8",  # 新乡 (都市圈)
    "410800": "#fef5e7",  # 焦作 (都市圈)
    "410900": "#fdfefe",  # 濮阳 (豫北)
    "411000": "#eafaf1",  # 许昌 (都市圈)
    "411100": "#f9ebea",  # 漯河 (都市圈)
    "411200": "#fdfefe",  # 三门峡 (豫西)
    "411300": "#e8f8f5",  # 南阳 (副中心)
    "411400": "#fef9e7",  # 商丘 (豫东)
    "411500": "#eafaf1",  # 信阳 (大别山)
    "411600": "#fef5e7",  # 周口 (豫东)
    "411700": "#f4ecf7",  # 驻马店 (豫南)
    "419001": "#eaf2f8",  # 济源 (直辖市)
}

for _, row in hn_prov.iterrows():
    adcode = str(row.get("adcode", ""))
    fc = city_colors.get(adcode, "#f8f9fa")
    gpd.GeoSeries([row.geometry], crs=ALBERS).plot(ax=ax, facecolor=fc, edgecolor="#7f8c8d", lw=0.7, ls="--", zorder=3)

gpd.GeoSeries([hn_union], crs=ALBERS).boundary.plot(ax=ax, color="#1a5276", lw=2.2, zorder=5)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl2 = mapkit.SymbolLabels(ax, fig)
sl2.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.55, 0.0, 1.0, 0.09),
             (0.88, 0.86, 1.0, 1.0)])

# 18 行政单元行政中心
admin_capitals = [
    ("郑州市 (国家中心城市·省会·特大城市·中原极核)", 113.665, 34.755, "gov"),
    ("洛阳市 (中原城市群副中心·神都古都·先进装备重镇)", 112.455, 34.620, "gov"),
    ("南阳市 (河南省域副中心·南水北调源头·医药农牧大市)", 112.525, 32.995, "gov"),
    ("开封市 (八朝古都·郑开同城化·清明上河宋文化名城)", 114.310, 34.795, "gov"),
    ("平顶山市 (中国尼龙城·能源转型示范·汝瓷之都)", 113.200, 33.735, "gov"),
    ("安阳市 (七朝古都·殷墟甲骨文发祥地·红旗渠故里)", 114.380, 36.085, "gov"),
    ("鹤壁市 (中国汽车电子电器之都·商业航天新城)", 114.295, 35.745, "gov"),
    ("新乡市 (电池工业之都·长垣起重医疗·南太行画廊)", 113.925, 35.305, "gov"),
    ("焦作市 (太极圣地陈家沟·云台山世遗·氟硅材料之都)", 113.240, 35.215, "gov"),
    ("濮阳市 (中华帝都·华夏龙都·中原油田石油化工基地)", 115.030, 35.760, "gov"),
    ("许昌市 (曹魏故都·特高压电力装备·世界发制品之都)", 113.850, 34.035, "gov"),
    ("漯河市 (中国食品名城·双汇肉类航母·贾湖契刻源乡)", 114.025, 33.595, "gov"),
    ("三门峡市 (黄河明珠·天鹅之城·黄金之都·仰韶故里)", 111.195, 34.780, "gov"),
    ("商丘市 (华商之源·殷商起源·综合交通枢纽·超硬材料)", 115.655, 34.415, "gov"),
    ("信阳市 (中国毛尖之都·大别山首府·淮滨通江达海港)", 114.120, 32.145, "gov"),
    ("周口市 (羲皇故都·老子故里·中原内河第一大港)", 114.675, 33.640, "gov"),
    ("驻马店市 (天下之中·中国农产品加工之都·嵖岈山胜境)", 114.025, 32.985, "gov"),
    ("济源市 (省直辖县级行政区·国家产城示范·愚公精神)", 112.590, 35.090, "gov")
]

for aname, alon, alat, akind in admin_capitals:
    ax_pt, ay_pt = to_alb(alon, alat)
    m = "*" if akind == "gov" else "s"
    c = "#c0392b" if "郑州" in aname else ("#d35400" if "洛阳" in aname or "南阳" in aname else "#2980b9")
    nm, nt = mapkit.split_note(aname)
    sl2.add(ax_pt, ay_pt, nm, akind, note=nt, priority=1,
            marker=m, face=c, size=9.5 if "郑州" in aname else (8.0 if "洛阳" in aname or "南阳" in aname else 6.8),
            kind_label="省辖市 / 济源直辖示范区行政中心")

sym_type_h, sym_idx_h = sl2.flush()

add_scalebar(ax, sb_x0, sb_y0, length_km=80)
add_compass(ax, 0.94, 0.92)

leg_elements = [
    Patch(facecolor="#ebf5fb", edgecolor="#1a5276", label="郑州国家中心城市引领极核 (郑州都市圈)"),
    Patch(facecolor="#e8f8f5", edgecolor="#16a085", label="中原城市群副中心两翼支撑 (洛阳/南阳双副中心)"),
    Patch(facecolor="#fef9e7", edgecolor="#f39c12", label="豫东承接产业转移示范区 (商丘/周口/开封)"),
    Patch(facecolor="#eafaf1", edgecolor="#27ae60", label="豫南大别山革命老区生态振兴区 (信阳/驻马店)")
]

leg = mapkit.stacked_legends(ax, [
    dict(handles=leg_elements + sym_type_h, title="空间战略与行政节点", ncol=1, fontsize=7.0, title_fontsize=7.8),
    dict(handles=sym_idx_h, title="图上行政单元定位索引", ncol=1, fontsize=6.8, title_fontsize=7.8),
], top=-0.010, gap=0.014)

ax.set_title("河南省行政区划与“一核两翼三区”空间格局图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Administrative Divisions & '1 Core 2 Wings 3 Zones' Spatial Structure of Henan",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：自然资源部标准地图与 DataV 行政区划 · 河南省国土空间规划 · 制作：《中国地理知识手册》",
    fontsize=6.8)

p2 = os.path.join(OUT_DIR, "fig15-00-2_河南省行政区划与“一核两翼三区”空间格局图.png")
fig.savefig(p2, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {p2}")

# =============================================================================
# 3. 综合立体交通与米字型高铁枢纽网络图 (fig15-00-3)
# =============================================================================
print("Generating Fig 15-00-3 (Transport Infrastructure & 'Asterisk' HSR Network)...")
fig, ax = plt.subplots(figsize=(10.0, 9.2), dpi=DPI)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

hn_prov.plot(ax=ax, facecolor="#fdfefe", edgecolor="#bdc3c7", lw=0.6, ls=":", zorder=2)
gpd.GeoSeries([hn_union], crs=ALBERS).boundary.plot(ax=ax, color="#1a5276", lw=1.8, zorder=3)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl3 = mapkit.SymbolLabels(ax, fig)
sl3.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.55, 0.0, 1.0, 0.09),
             (0.88, 0.86, 1.0, 1.0)])

# 交通与港口地标
transport_hubs = [
    ("郑州东站与郑州站 (京广与徐兰高铁全国特大十字米字极核)", 113.780, 34.760, "rail_hub"),
    ("郑州新郑国际机场 (4F级国际航空双枢纽港/空港核心)", 113.840, 34.530, "airport"),
    ("洛阳龙门站 (徐兰高铁中原城市群副中心大站)", 112.440, 34.595, "rail_hub"),
    ("商丘站与商丘东站 (徐兰客专与商合杭高铁十字枢纽)", 115.655, 34.440, "rail_hub"),
    ("南阳东站 (郑渝高铁豫西南综合客运极核)", 112.635, 32.975, "rail_hub"),
    ("周口中心港集装箱码头 (沙颍河全省第一大通江达海出海港)", 114.710, 33.620, "port"),
    ("信阳港淮滨中心港区 (千里淮河第一大出海内河港)", 115.420, 32.470, "port"),
    ("安阳红旗渠机场与信阳明港机场 (南北两翼现代化空港)", 114.580, 35.920, "airport"),
    ("郑州国际陆港中欧班列中原集结中心 (内陆陆港枢纽)", 113.760, 34.680, "dryport")
]

for tname, tlon, tlat, tkind in transport_hubs:
    tx_pt, ty_pt = to_alb(tlon, tlat)
    nm, nt = mapkit.split_note(tname)
    sl3.add(tx_pt, ty_pt, nm, tkind, note=nt)

sym_type_h, sym_idx_h = sl3.flush()

add_scalebar(ax, sb_x0, sb_y0, length_km=80)
add_compass(ax, 0.94, 0.92)

leg_elements = [
    Line2D([0], [0], color="#c0392b", lw=2.2, label="米字型高速铁路通道 (京广/徐兰/郑渝/济郑/郑阜/郑太)"),
    Line2D([0], [0], color="#8e44ad", lw=1.8, label="4F级国际航空枢纽港/千吨级通江达海内河海港"),
    Line2D([0], [0], color="#2980b9", lw=1.8, label="国家高速公路网/中欧班列中原多式联运大通道")
]

leg = mapkit.stacked_legends(ax, [
    dict(handles=leg_elements + sym_type_h, title="交通通道与枢纽类型", ncol=1, fontsize=7.0, title_fontsize=7.8),
    dict(handles=sym_idx_h, title="图上综合交通节点索引", ncol=1, fontsize=6.8, title_fontsize=7.8),
], top=-0.010, gap=0.014)

ax.set_title("河南省综合立体交通与米字型高铁枢纽网络图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Integrated Transport Infrastructure & 'Asterisk' HSR Network of Henan",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：河南省交通运输厅 · 综合立体交通网规划 · 制作：《中国地理知识手册》",
    fontsize=6.8)

p3 = os.path.join(OUT_DIR, "fig15-00-3_河南省综合立体交通与米字型高铁枢纽网络图.png")
fig.savefig(p3, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {p3}")

# =============================================================================
# 4. 新兴产业集群与先进制造基地空间格局图 (fig15-00-4)
# =============================================================================
print("Generating Fig 15-00-4 (Emerging Industry Clusters & Advanced Manufacturing)...")
fig, ax = plt.subplots(figsize=(10.0, 9.2), dpi=DPI)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

hn_prov.plot(ax=ax, facecolor="#fdfefe", edgecolor="#bdc3c7", lw=0.6, ls=":", zorder=2)
gpd.GeoSeries([hn_union], crs=ALBERS).boundary.plot(ax=ax, color="#1a5276", lw=1.8, zorder=3)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl4 = mapkit.SymbolLabels(ax, fig)
sl4.reserve([(0.0, 0.0, 0.40, 0.34),
             (0.55, 0.0, 1.0, 0.09),
             (0.88, 0.86, 1.0, 1.0)])

# 核心产业集群地标
industries = [
    ("郑州富士康与超聚变服务器智能制造基地 (全球服务器极核)", 113.850, 34.560, "电子信息"),
    ("宇通客车与比亚迪新能源汽车郑州智造基地 (商用与乘用龙头)", 113.720, 34.680, "新能源汽车"),
    ("中国一拖与中信重工高端装备研发制造基地 (共和国装备长子)", 112.395, 34.655, "高端装备"),
    ("中国平煤神马集团中国尼龙城高分子基地 (全球尼龙龙头)", 113.285, 33.775, "化工新材料"),
    ("多氟多新能源与龙佰集团钛白粉全球制造中心 (氟硅新材料/钛白粉)", 113.155, 35.250, "新材料极核"),
    ("许昌许继集团特高压智能电网装备核心基地 (特高压重器)", 113.840, 34.045, "特高压装备"),
    ("双汇集团国际总部与肉类全产业链园区 (全球肉类第一)", 114.010, 33.565, "现代食品"),
    ("三门峡中原黄金冶炼厂与宝武铝业特种铝基地 (黄金与铝材)", 111.240, 34.750, "有色金属"),
    ("南阳牧原食品全球数字化生猪现代食品园区 (农牧科技航母)", 112.520, 32.980, "现代农牧"),
    ("柘城中国超硬材料力量钻石微粉制造基地 (全球人造金刚石)", 115.305, 34.080, "超硬材料"),
    ("济源豫光金铅国家级循环经济与全国白银之都基地 (电解铅与白银)", 112.585, 35.080, "有色循环")
]

ind_palette = [
    ("#c0392b", "o", "电子信息/智能服务器极核"),
    ("#8e44ad", "s", "高端重型装备/特高压电网"),
    ("#27ae60", "D", "新能源汽车/电池与氟材料"),
    ("#d35400", "^", "超硬金刚石/有色金属新材料"),
    ("#1f618d", "p", "现代食品/生猪农牧全产业链")
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

ax.set_title("河南省新兴产业集群与先进制造基地空间格局图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Spatial Clusters of Emerging Industries & Modern Manufacturing in Henan",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：河南省工业和信息化厅 · 制造业高质量发展规划 · 制作：《中国地理知识手册》",
    fontsize=6.8)

p4 = os.path.join(OUT_DIR, "fig15-00-4_河南省新兴产业集群与先进制造基地空间格局图.png")
fig.savefig(p4, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {p4}")

# =============================================================================
# 5. 1986—2024年夜间灯光演变与区域协调发展图 (fig15-00-5)
# =============================================================================
print("Generating Fig 15-00-5 (Nightlight Evolution 1986-2024)...")
fig, (ax_nl, ax_gdp) = plt.subplots(2, 1, figsize=(10.0, 9.0), dpi=DPI)
fig.patch.set_facecolor("white")

nl_clean_df = pd.read_csv(os.path.join(DATA_DIR, "henan_nightlight_clean.csv"))
nl_prov = nl_clean_df.groupby("year")["sum"].sum().reset_index()

# 上图：夜间灯光演变
ax_nl.set_facecolor("#fbfcfc")
ax_nl.plot(nl_prov["year"], nl_prov["sum"] / 1000.0, color="#d35400", lw=2.4, marker="o", ms=4, zorder=5, label="河南省全域夜间灯光总强度 (DN×10³)")
ax_nl.fill_between(nl_prov["year"], 0, nl_prov["sum"] / 1000.0, color="#f8c471", alpha=0.25, zorder=3)

# 历史节点标注
nl_notes = [
    (1990, 85.0, "1990 郑州商品交易所成立\n商贸中心与陇海京广集聚"),
    (2003, 160.0, "2003 郑东新区规划建设启动\n中原城市群战略全面提出"),
    (2010, 390.0, "2010 富士康郑州科技园投产\n郑州航空港迈向买全球卖全球"),
    (2016, 560.0, "2016 郑州国家中心城市获批\n米字型高铁网全面连通成型")
]
for yr, yval, txt in nl_notes:
    sub_df = nl_prov[nl_prov["year"] == yr]
    if not sub_df.empty:
        curr_y = sub_df["sum"].values[0] / 1000.0
        ax_nl.annotate(txt, xy=(yr, curr_y), xytext=(yr, yval),
                       arrowprops=dict(arrowstyle="->", color="#78281f", lw=1.0),
                       fontsize=6.8, ha="center", va="bottom",
                       bbox=dict(boxstyle="round,pad=0.2", facecolor="#fef9e7", edgecolor="#f39c12", alpha=0.9))

ax_nl.set_title("河南省1986—2013年全域夜间灯光总辐射量演进轨迹 (DMSP/OLS卫星校准数据)", fontsize=9.2, fontweight="bold", color=C_TEXT)
ax_nl.set_ylabel("夜间灯光总值 (×10³ DN)", fontsize=7.5, color="#2c3e50")
ax_nl.set_xlim(1985, 2014)
ax_nl.grid(True, ls=":", alpha=0.6)
ax_nl.legend(loc="upper left", fontsize=7.2, frameon=True, facecolor="white")

# 下图：主要单元 GDP 增长演化 (2000-2024)
from henan_city_configs import HENAN_CONFIGS
ax_gdp.set_facecolor("#fbfcfc")
years = [2000, 2005, 2010, 2015, 2020, 2022, 2023, 2024]

city_plot_styles = {
    "410100": ("#c0392b", "-", 2.5, "郑州市 (省会国家中心城市)"),
    "410300": ("#e67e22", "--", 2.0, "洛阳市 (中原副中心)"),
    "411300": ("#2980b9", "-.", 1.8, "南阳市 (副中心两翼)"),
    "411000": ("#27ae60", ":", 1.8, "许昌市 (特高压与发制品)"),
    "411600": ("#8e44ad", "-", 1.6, "周口市 (内河航运出海港)"),
    "410700": ("#16a085", "--", 1.5, "新乡市 (豫北重镇电池谷)"),
    "411700": ("#d35400", "-.", 1.5, "驻马店市 (天下之中农都)"),
    "411500": ("#34495e", ":", 1.4, "信阳市 (江南北国毛尖之都)"),
    "411400": ("#7f8c8d", "-", 1.4, "商丘市 (华商之源超硬材料)"),
    "410400": ("#b7950b", "--", 1.4, "平顶山市 (中国尼龙城)"),
    "410200": ("#5d6d7e", ":", 1.4, "开封市 (八朝古都宋文化)"),
    "419001": ("#1f618d", "-", 1.3, "济源市 (产城融合示范区)")
}

for code, (col, ls, lw, lbl) in city_plot_styles.items():
    cfg = HENAN_CONFIGS.get(code)
    if cfg and "gdp_series" in cfg:
        s = cfg["gdp_series"]
        y_vals = [s.get(y, np.nan) for y in years]
        ax_gdp.plot(years, y_vals, color=col, ls=ls, lw=lw, label=lbl, marker="s", ms=3.5)

ax_gdp.set_title("2000—2024年河南省主要城市地区生产总值（GDP）跨越式跃升格局", fontsize=9.2, fontweight="bold", color=C_TEXT)
ax_gdp.set_xlabel("年份 Year", fontsize=7.5, color="#2c3e50")
ax_gdp.set_ylabel("地区生产总值 (亿元)", fontsize=7.5, color="#2c3e50")
ax_gdp.set_xlim(1999, 2025)
ax_gdp.grid(True, ls=":", alpha=0.6)
ax_gdp.legend(loc="upper left", bbox_to_anchor=(0.01, 0.98), ncol=3, fontsize=6.5, frameon=True, facecolor="white")

plt.tight_layout()
p5 = os.path.join(OUT_DIR, "fig15-00-5_河南省1986—2024年夜间灯光演变与区域协调发展图.png")
fig.savefig(p5, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {p5}")

print("\nAll 5 Henan Overview Figures successfully generated!")
