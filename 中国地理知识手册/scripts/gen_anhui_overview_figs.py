# -*- coding: utf-8 -*-
"""安徽省地理统揽专题地图生成引擎（12-00）
包含 5 幅全省权威出版级地图与分析图表（精细调优排版、微缩字号、严格杜绝压盖）：
1. fig12-00-1_安徽省地势水系与江淮山地宏观格局图.png
2. fig12-00-2_安徽省行政区划与“一圈五区”空间格局图.png
3. fig12-00-3_安徽省综合立体交通与长三角联动网络图.png
4. fig12-00-4_安徽省新兴产业集群与科技创新策源地空间格局图.png
5. fig12-00-5_安徽省1986—2024年夜间灯光演变与区域协调发展图.png
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

print("Loading Anhui provincial boundaries and DEM...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

ah_prov = gpd.read_file(os.path.join(DATAV_DIR, "340000_full.json")).to_crs(ALBERS)
ah_prov["geometry"] = ah_prov.geometry.buffer(0)
ah_union = ah_prov.union_all()

b = ah_prov.total_bounds
span_x = b[2] - b[0]
span_y = b[3] - b[1]
pad_x = span_x * 0.04
pad_y = span_y * 0.04
ax_xlim = (b[0] - pad_x, b[2] + pad_x)
ax_ylim = (b[1] - pad_y, b[3] + pad_y)

# 加载 DEM
dem_file = os.path.join(DATA_DIR, "dem", "province", "340000_z9.npz")
dem_data = np.load(dem_file)
step = 2
dem_raw = np.nan_to_num(dem_data['dem'][::step, ::step], nan=0.0)
dem_res = float(dem_data['res']) * step
dem_minx = float(dem_data['minx'])
dem_maxy = float(dem_data['maxy'])
print(f"Downsampled Anhui DEM shape: {dem_raw.shape}, res: {dem_res}m")

extent = (dem_minx, dem_minx + dem_raw.shape[1] * dem_res,
          dem_maxy - dem_raw.shape[0] * dem_res, dem_maxy)

hs = calc_hillshade(dem_raw, dem_res)
norm = Normalize(vmin=0.0, vmax=1865.0)

# 安徽省地貌阶梯色标：沿淮平原-江淮低丘-皖南/大别山中山 (0m-1865m)
terrain_colors = [
    (0.00, "#196f3d"),   # 0m-25m 沿淮黄泛平原、沿江平原与河湖漫滩
    (0.03, "#27ae60"),   # 25m-60m 淮北平原与江淮分水岭低缓丘陵
    (0.08, "#52be80"),   # 60m-150m 巢湖周边台地、滁州定远波状岗地
    (0.18, "#f9e79f"),   # 150m-350m 琅琊山、八公山、涂山、敬亭山低山残丘
    (0.35, "#eb984e"),   # 350m-700m 大别山东麓余脉、叶山、浮山中低山体
    (0.55, "#dc7633"),   # 700m-1100m 牯牛降低中山、皖南群峰基座
    (0.72, "#ba4a00"),   # 1100m-1450m 九华山十王峰、天柱山天柱峰
    (0.88, "#873600"),   # 1450m-1750m 大别山白马尖、清凉峰
    (1.00, "#4a235a")    # 1750m-1864.8m 黄山莲花峰、光明顶、天都峰
]
terrain_cmap = LinearSegmentedColormap.from_list("ah_dem", terrain_colors)
dem_rgb = terrain_cmap(norm(dem_raw))[:, :, :3]
shaded_rgb = dem_rgb * (0.44 + 0.56 * hs[:, :, np.newaxis])

FIGSIZE = (9.8, 10.2)

# =============================================================================
# 图 12-00-1：安徽省地势水系与江淮山地宏观格局图
# =============================================================================
print("Generating Fig 12-00-1 (Topography & River-Mountain Pattern)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

im = ax.imshow(shaded_rgb, extent=extent, origin="upper", zorder=2)
patch = get_mpl_clip_patch(ah_union)
ax.add_patch(patch)
im.set_clip_path(patch)

ah_prov.boundary.plot(ax=ax, color="#2c3e50", lw=0.6, ls="--", zorder=5)
gpd.GeoSeries([ah_union], crs=ALBERS).boundary.plot(ax=ax, color="#1a5276", lw=1.5, zorder=6)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl1 = mapkit.SymbolLabels(ax, fig)
sl1.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.50, 0.0, 1.0, 0.09),
             (0.88, 0.86, 1.0, 1.0)])

peaks_data = [
    ("黄山莲花峰 (1864.8m 全省第一高峰·世界双遗产)", 118.175, 30.135, "peak", "天下第一奇山自然极峰"),
    ("大别山白马尖 (1777.0m 霍山·大别山主峰)", 116.185, 31.115, "peak", "大别山脉地理制高点"),
    ("天柱山天柱峰 (1488.4m 潜山·世界地质公园)", 116.455, 30.715, "peak", "古南岳擎天一柱奇观"),
    ("九华山十王峰 (1344.4m 青阳·地藏王道场)", 117.805, 30.485, "peak", "中国佛教四大名山"),
    ("牯牛降主峰 (1727.6m 石台祁门交界·华东绿肺)", 117.385, 30.185, "mt", "华东最后原始森林高地"),
    ("清凉峰 (1787.4m 绩溪临安界峰·皖浙屋脊)", 118.895, 30.089, "mt", "天目山脉最高峰"),
    ("琅琊山北峰 (317.0m 滁州醉翁亭名山)", 118.285, 32.285, "mt", "欧阳修醉翁之意名胜"),
    ("八公山白塔寺峰 (241.2m 淮南豆腐发源地)", 116.835, 32.625, "mt", "淮南子诞生与风声鹤唳名山"),
    ("荆涂山 (258.0m 蚌埠禹会村大禹治水)", 117.275, 32.935, "mt", "大禹会诸侯历史圣山")
]

for name, lon, lat, ptype, desc in peaks_data:
    px, py = to_alb(lon, lat)
    m = "*" if ptype == "peak" else "^"
    fc = "#c0392b" if ptype == "peak" else "#922b21"
    sl1.add(px, py, name, ptype, note=desc, priority=0 if ptype == "peak" else 1,
            marker=m, face=fc, size=7.2 if ptype == "peak" else 5.2, kind_label="地形控制性极点与名山大川")

waters_data = [
    ("长江干流安徽段 (全长416km·八百里皖江黄金水道)", 117.800, 31.200, "water", "穿安庆池州铜陵芜湖马鞍山入苏"),
    ("淮河干流安徽段 (全长430km·千里淮河第一闸王家坝)", 116.500, 32.800, "water", "横贯淮北平原与江淮分水岭以北"),
    ("新安江水系 (全长242km·千岛湖源头生态画廊)", 118.350, 29.750, "water", "皖浙跨省生态补偿全国典范"),
    ("巢湖水域 (780km² 全国五大淡水湖之一)", 117.500, 31.550, "water", "合肥环湖大都市生态绿心"),
    ("引江济淮工程 (全长723km·世纪水利江淮运河)", 117.200, 31.850, "water", "长江淮河两大水系世纪世纪连通"),
    ("淠史杭工程横排头与六安茶谷", 116.500, 31.700, "water", "新中国特大型人工天河灌区"),
    ("太平湖水域 (88km² 黄山情侣高山清泉)", 118.050, 30.380, "water", "青弋江上游黄山脚下秀丽名湖"),
    ("升金湖湿地 (国际重要湿地·中国鹤湖)", 117.025, 30.415, "water", "东亚越冬水鸟关键停歇庇护所")
]

for name, lon, lat, wtype, desc in waters_data:
    px, py = to_alb(lon, lat)
    sl1.add(px, py, name, wtype, note=desc, priority=2,
            marker="s", face="#1b4f72", size=4.8, kind_label="骨干江河水系与著名湖泊湿地")

sym_type_h, sym_idx_h = sl1.flush()

sb_x0 = ax_xlim[0] + span_x * 0.55
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=80)
add_compass(ax, 0.94, 0.91)

leg1 = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="地形与水系要素分类", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="图上要素编号对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("安徽省地势水系与江淮山地宏观格局图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Geomorphology, Mountain Systems & Water Networks of Anhui Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg1, "数据源：AWS Terrain 300m 高程 · 投影：Albers 等积圆锥 (中央经线 105°E) · 制作：《中国地理知识手册》",
    fontsize=6.5)

p1 = os.path.join(OUT_DIR, "fig12-00-1_安徽省地势水系与江淮山地宏观格局图.png")
fig.savefig(p1, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {p1}")

# =============================================================================
# 图 12-00-2：安徽省行政区划与“一圈五区”空间格局图
# =============================================================================
print("Generating Fig 12-00-2 (Administrative & '1 Circle 5 Zones')...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

# 16 市赋色划分空间战略区：
# 1. 合肥都市圈核心与腹地：合肥、淮南、六安、滁州、马鞍山、芜湖 (#d4efdf 淡绿)
# 2. 皖北承接产业转移集聚区：阜阳、亳州、宿州、淮北、蚌埠 (#fdebd0 淡暖橙)
# 3. 皖江城市带与皖南国际文化旅游示范区：安庆、池州、铜陵、黄山、宣城 (#d6eaf8 淡海蓝)
city_zone_map = {
    "340100": ("#d4efdf", "合肥都市圈极核"),
    "340200": ("#e8f8f5", "合肥都市圈/省域副中心·芜湖"),
    "340300": ("#fdebd0", "皖北承接集聚区·蚌埠"),
    "340400": ("#e8f8f5", "合肥都市圈·淮南"),
    "340500": ("#d4efdf", "合肥都市圈/宁马一体·马鞍山"),
    "340600": ("#fdebd0", "皖北承接集聚区·淮北"),
    "340700": ("#e8f8f5", "皖江城市带·铜陵"),
    "340800": ("#ebf5fb", "皖江城市带/皖西南·安庆"),
    "341000": ("#d6eaf8", "皖南文旅示范区·黄山"),
    "341100": ("#e8f8f5", "合肥都市圈/皖东接宁·滁州"),
    "341200": ("#fdebd0", "皖北承接集聚区·阜阳"),
    "341300": ("#fdebd0", "皖北承接集聚区·宿州"),
    "341500": ("#e8f8f5", "合肥都市圈/大别山老区·六安"),
    "341600": ("#fdebd0", "皖北承接集聚区·亳州"),
    "341700": ("#d6eaf8", "皖南文旅示范区·池州"),
    "341800": ("#d6eaf8", "皖南文旅示范区·宣城")
}

for idx, row in ah_prov.iterrows():
    adcode = str(row.get("adcode", ""))
    color, zname = city_zone_map.get(adcode, ("#f2f4f4", "其他"))
    gpd.GeoSeries([row.geometry], crs=ALBERS).plot(ax=ax, facecolor=color, edgecolor="#566573", lw=0.9, zorder=3)

gpd.GeoSeries([ah_union], crs=ALBERS).boundary.plot(ax=ax, color="#1b4f72", lw=1.8, zorder=6)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl2 = mapkit.SymbolLabels(ax, fig)
sl2.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.50, 0.0, 1.0, 0.09),
             (0.88, 0.86, 1.0, 1.0)])

from anhui_configs import ANHUI_CITIES
for c in ANHUI_CITIES:
    geom = ah_prov[ah_prov["adcode"] == int(c["adcode"])].geometry.iloc[0]
    rp = geom.representative_point()
    cx, cy = rp.x, rp.y
    note = f"GDP: {c['gdp_yi']}亿元 | 人口: {c['pop_wan']}万人 | 城镇化率: {c['urbanization_rate']}%"
    sl2.add(cx, cy, c["name"], "capital", note=note, priority=0,
            marker="o", face="#c0392b" if c["adcode"] in ["340100", "340200"] else "#2980b9",
            size=7.2 if c["adcode"] in ["340100", "340200"] else 5.2,
            kind_label="设区市行政中心与综合能级")

# 标注战略走廊
corridors = [
    ("合肥都市圈引领核 (全省创新策源与万亿增长极)", 117.280, 31.860, "综合性国家科学中心与世界新能源汽车高地"),
    ("皖江城市带承接产业转移示范区 (长江经济带黄金水道轴线)", 118.150, 31.150, "长江深水岸线产业集聚与跨江融合"),
    ("皖北承接产业转移集聚区 (淮北阜亳宿蚌六市协同发力)", 116.500, 33.500, "人口红利与现代化农业制造腹地"),
    ("大别山革命老区绿色振兴带 (淠史杭与生态经济廊道)", 116.100, 31.450, "绿色屏障与老区高质量转型"),
    ("皖南国际文化旅游示范区 (大黄山世界级生态文化康养高地)", 118.200, 30.050, "徽文化与名山生态文旅顶级名片")
]

for cname, clon, clat, cdesc in corridors:
    cx, cy = to_alb(clon, clat)
    sl2.add(cx, cy, cname, "corridor", note=cdesc, priority=1,
            marker="D", face="#8e44ad", size=5.5, kind_label="“一圈五区”战略区域与经济廊道")

sym_type_h, sym_idx_h = sl2.flush()

add_scalebar(ax, sb_x0, sb_y0, length_km=80)
add_compass(ax, 0.94, 0.91)

zone_patches = [
    Patch(facecolor="#d4efdf", edgecolor="#566573", label="合肥都市圈（引领创新策源极核）"),
    Patch(facecolor="#fdebd0", edgecolor="#566573", label="皖北承接产业转移集聚区（人口与腹地优势）"),
    Patch(facecolor="#d6eaf8", edgecolor="#566573", label="皖南国际文化旅游示范区（生态与徽文化圣地）"),
    Patch(facecolor="#e8f8f5", edgecolor="#566573", label="皖江城市带与联动协同区")
]

leg2 = mapkit.stacked_legends(ax, [
    dict(handles=zone_patches, title="“一圈五区”战略空间格局", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_type_h, title="行政中心与走廊类型", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="行政中心与走廊编号对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("安徽省行政区划与“一圈五区”空间格局图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Administrative Divisions & 'One Circle, Five Zones' Spatial Framework of Anhui",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg2, "数据源：安徽省国土空间总体规划 (2021-2035) · 民政部标准地名代码 · 制作：《中国地理知识手册》",
    fontsize=6.5)

p2 = os.path.join(OUT_DIR, "fig12-00-2_安徽省行政区划与“一圈五区”空间格局图.png")
fig.savefig(p2, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {p2}")

# =============================================================================
# 图 12-00-3：安徽省综合立体交通与长三角联动网络图
# =============================================================================
print("Generating Fig 12-00-3 (Transport & Interconnection Network)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

ah_prov.plot(ax=ax, facecolor="#f9f9f9", edgecolor="#bdc3c7", lw=0.6, zorder=2)
gpd.GeoSeries([ah_union], crs=ALBERS).boundary.plot(ax=ax, color="#2c3e50", lw=1.5, zorder=4)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

# 骨干高铁廊道（示意线）
hsi_lines = [
    # 京沪高铁
    ([117.06, 117.38, 118.35, 118.52], [34.12, 32.94, 32.31, 31.54], "#c0392b", 2.2, "京沪高铁通道 (宿州-蚌埠-滁州-跨长江)"),
    # 京港/合福高铁 (合肥辐射主轴)
    ([115.84, 116.83, 117.28, 118.37, 118.17], [32.91, 32.62, 31.86, 31.33, 30.13], "#e74c3c", 2.2, "京港/合福高铁通道 (阜阳-淮南-合肥-芜湖-黄山)"),
    # 商合杭高铁 (西北至东南大通道)
    ([115.77, 115.84, 116.83, 117.28, 118.37, 118.75], [33.86, 32.91, 32.62, 31.86, 31.33, 30.98], "#8e44ad", 2.0, "商合杭高铁 (亳州-阜阳-淮南-合肥-芜湖-宣城)"),
    # 沪汉蓉沿江高铁
    ([116.18, 116.51, 117.28, 118.44], [31.11, 31.75, 31.86, 31.67], "#2980b9", 2.0, "沪汉蓉沿江高铁通道 (六安-合肥-马鞍山)")
]

for lons, lats, col, lw, desc in hsi_lines:
    albs = [to_alb(x, y) for x, y in zip(lons, lats)]
    xs = [p[0] for p in albs]
    ys = [p[1] for p in albs]
    ax.plot(xs, ys, color=col, lw=lw, zorder=5, alpha=0.85)

# 引江济淮江淮运河超级航道
yjjh_lons = [117.80, 117.45, 117.27, 117.20, 116.85, 116.70]
yjjh_lats = [31.20, 31.55, 31.75, 32.10, 32.60, 32.85]
yjjh_albs = [to_alb(x, y) for x, y in zip(yjjh_lons, yjjh_lats)]
ax.plot([p[0] for p in yjjh_albs], [p[1] for p in yjjh_albs], color="#1b4f72", lw=3.0, ls="-.", zorder=6, label="引江济淮江淮运河航道")

sl3 = mapkit.SymbolLabels(ax, fig)
sl3.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.50, 0.0, 1.0, 0.09),
             (0.88, 0.86, 1.0, 1.0)])

hubs = [
    ("合肥新桥国际机场 (长三角世界级机场群枢纽)", 116.975, 31.985, "airport", "4E级洲际航空枢纽港"),
    ("合肥南站 (全国特大型高铁枢纽站)", 117.295, 31.805, "station", "米字形高铁综合枢纽核心"),
    ("芜湖港朱家桥港区 (安徽第一大外贸枢纽港)", 118.425, 31.355, "port", "长江集装箱千万标箱潜力港"),
    ("马鞍山港郑蒲港区 (深水公铁水联运港区)", 118.385, 31.625, "port", "皖江第一深水外贸枢纽港"),
    ("安庆港中心港区 (皖西南江海联运直达港)", 117.065, 30.515, "port", "国家一类对外开放口岸"),
    ("蚌埠港与淮河集装箱码头 (千里淮河第一大港)", 117.385, 32.965, "port", "淮河水系通江达海门户"),
    ("阜阳西站 (皖北大型综合高铁交通客运港)", 115.845, 32.915, "station", "商合杭与郑阜高铁枢纽"),
    ("芜宣机场 (芜湖宣城协同军民合用航空港)", 118.575, 31.385, "airport", "皖东南国际航空物流港")
]

for hname, hlon, hlat, htype, hdesc in hubs:
    hx, hy = to_alb(hlon, hlat)
    m = "s" if htype == "port" else ("^" if htype == "airport" else "o")
    fc = "#1b4f72" if htype == "port" else ("#e67e22" if htype == "airport" else "#27ae60")
    sl3.add(hx, hy, hname, htype, note=hdesc, priority=0 if htype in ["airport", "port"] else 1,
            marker=m, face=fc, size=6.5, kind_label="立体交通大枢纽与沿江沿淮强港")

sym_type_h, sym_idx_h = sl3.flush()

add_scalebar(ax, sb_x0, sb_y0, length_km=80)
add_compass(ax, 0.94, 0.91)

hsi_lines_legend = [
    Line2D([0], [0], color="#c0392b", lw=2.2, label="京沪高铁大通道"),
    Line2D([0], [0], color="#e74c3c", lw=2.2, label="京港/合福高铁通道"),
    Line2D([0], [0], color="#8e44ad", lw=2.0, label="商合杭高铁跨省通道"),
    Line2D([0], [0], color="#2980b9", lw=2.0, label="沪汉蓉沿江高铁通道"),
    Line2D([0], [0], color="#1b4f72", lw=3.0, ls="-.", label="引江济淮世纪运河航运线")
]

leg3 = mapkit.stacked_legends(ax, [
    dict(handles=hsi_lines_legend, title="骨干高速铁路与世纪运河", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_type_h, title="交通基础设施类型", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="综合枢纽名称对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("安徽省综合立体交通与长三角联动网络图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Integrated Transportation System, High-Speed Rail & Waterway Networks of Anhui",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg3, "数据源：安徽省综合立体交通网规划纲要 (2021-2035) · 制作：《中国地理知识手册》",
    fontsize=6.5)

p3 = os.path.join(OUT_DIR, "fig12-00-3_安徽省综合立体交通与长三角联动网络图.png")
fig.savefig(p3, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {p3}")

# =============================================================================
# 图 12-00-4：安徽省新兴产业集群与科技创新策源地空间格局图
# =============================================================================
print("Generating Fig 12-00-4 (Emerging Industry Clusters & Science Hub)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

ah_prov.plot(ax=ax, facecolor="#fcfcfc", edgecolor="#bdc3c7", lw=0.6, zorder=2)
gpd.GeoSeries([ah_union], crs=ALBERS).boundary.plot(ax=ax, color="#1b4f72", lw=1.6, zorder=4)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl4 = mapkit.SymbolLabels(ax, fig)
sl4.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.50, 0.0, 1.0, 0.09),
             (0.88, 0.86, 1.0, 1.0)])

industries = [
    ("合肥综合性国家科学中心与量子科学大道 (墨子/九章/超导托卡马克)", 117.145, 31.848, "science", "国家原始科技创新策源极核"),
    ("合肥全球新能源汽车第一城基地 (蔚来/比亚迪/大众安徽/江淮)", 117.025, 31.715, "auto", "全国最大新能源乘用车制造中心"),
    ("合肥新型显示与集成电路产业群 (京东方/晶合集成/长鑫存储)", 117.320, 31.910, "digital", "全球新型显示产业链核心承载区"),
    ("芜湖奇瑞汽车全球总部与超级智能互联工厂", 118.365, 31.425, "auto", "自主汽车品牌出口全国第一"),
    ("芜湖国家级机器人产业集聚区 (埃夫特机器人/核心零部件)", 118.415, 31.285, "manu", "全国首个国家级机器人产业发展集聚区"),
    ("马鞍山宝武马钢特种钢铁新材料基地 (车轮/冷轧硅钢)", 118.495, 31.715, "manu", "大国重器轨道交通特种钢航母"),
    ("铜陵先进铜基材料产业基地 (铜陵有色/极薄锂电铜箔)", 117.845, 30.965, "manu", "全球高端PCB与动力电池铜箔生产地"),
    ("蚌埠硅基新材料产业集群 (超薄触控玻璃/柔性可折叠玻璃)", 117.345, 32.985, "materials", "大国特种显示玻璃策源高地"),
    ("蚌埠丰原生物基新材料基地 (聚乳酸PLA可降解全产业链)", 117.360, 33.020, "materials", "全球领先绿色可降解材料基地"),
    ("滁州经开区光伏产业基地 (隆基/东方日升/全球光伏名城)", 118.355, 32.315, "energy", "全球光伏组件产能最大集聚区之一"),
    ("亳州现代中药产业集聚基地 (全球最大中药材交易中心)", 115.775, 33.865, "biomed", "中华药都现代配方颗粒与饮片基地"),
    ("淮北陶铝新材料产业园 (航天航空特种陶铝新材料)", 116.815, 33.965, "materials", "颠覆性轻量化合金材料研发地"),
    ("淮南潘集千亿级清洁煤电化基地与水面漂浮光伏群", 116.985, 32.645, "energy", "华东特大型煤电化绿色转型高地"),
    ("宿州高新区华为云计算中心 (华东大数据存储与处理中心)", 116.985, 33.635, "digital", "皖北数字经济与算力枢纽"),
    ("宁国中鼎汽车核心密封件制造基地 (全球橡胶非轮胎领先)", 118.985, 30.635, "auto", "全球汽车零部件单项冠军领军企业")
]

for iname, ilon, ilat, itype, idesc in industries:
    ix, iy = to_alb(ilon, ilat)
    m = "*" if itype in ["science", "auto"] else ("s" if itype == "manu" else ("^" if itype == "energy" else "D"))
    fc = "#8e44ad" if itype == "science" else ("#c0392b" if itype == "auto" else ("#27ae60" if itype == "energy" else "#d35400"))
    sl4.add(ix, iy, iname, itype, note=idesc, priority=0 if itype in ["science", "auto"] else 1,
            marker=m, face=fc, size=6.5, kind_label="先进制造与科技创新高能级集群")

sym_type_h, sym_idx_h = sl4.flush()

add_scalebar(ax, sb_x0, sb_y0, length_km=80)
add_compass(ax, 0.94, 0.91)

leg4 = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="战略新兴产业门类", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="标志性集群与科技策源地索引", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("安徽省新兴产业集群与科技创新策源地空间格局图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Emerging Industrial Clusters & Science Innovation Centers of Anhui Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg4, "数据源：安徽省发展和改革委员会 · 安徽省科学技术厅 · 制作：《中国地理知识手册》",
    fontsize=6.5)

p4 = os.path.join(OUT_DIR, "fig12-00-4_安徽省新兴产业集群与科技创新策源地空间格局图.png")
fig.savefig(p4, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {p4}")

# =============================================================================
# 图 12-00-5：安徽省 1986—2024 年夜间灯光演变与区域协调发展图
# =============================================================================
print("Generating Fig 12-00-5 (Nightlight Evolution 1986-2024)...")
fig = plt.figure(figsize=(10.2, 9.6), dpi=DPI)
fig.patch.set_facecolor("white")

gs = fig.add_gridspec(2, 2, height_ratios=[1.2, 1.0], hspace=0.28, wspace=0.22,
                       left=0.07, right=0.95, top=0.92, bottom=0.08)

ax_map = fig.add_subplot(gs[0, :])
ax_curve = fig.add_subplot(gs[1, 0])
ax_city = fig.add_subplot(gs[1, 1])

# 上半部分：全省夜光空间扩展
ah_prov.plot(ax=ax_map, facecolor="#f5f7f8", edgecolor="#bdc3c7", lw=0.6, zorder=2)
gpd.GeoSeries([ah_union], crs=ALBERS).boundary.plot(ax=ax_map, color="#2c3e50", lw=1.4, zorder=4)
ax_map.set_xlim(ax_xlim)
ax_map.set_ylim(ax_ylim)
ax_map.axis("off")

nl_belts = [
    ("合肥特大都市区高光隆起核 (合肥主城-肥西-肥东环巢湖辐射带)", 117.280, 31.860, "#e74c3c", 90),
    ("皖江沿江工业密集发光带 (芜湖-马鞍山-铜陵-池州-安庆)", 118.150, 31.350, "#d35400", 78),
    ("皖北工业与人口城镇密集带 (阜阳-亳州-宿州-淮北-蚌埠)", 116.500, 33.200, "#f39c12", 72),
    ("滁州东向融宁高光走廊 (滁州主城-天长高光集聚)", 118.550, 32.400, "#27ae60", 65),
    ("大黄山生态文化国际旅游光带 (黄山-池州九华山-宣城徽风)", 118.150, 30.150, "#8e44ad", 58)
]

for bname, blon, blat, bcol, bsize in nl_belts:
    bx, by = to_alb(blon, blat)
    circle = plt.Circle((bx, by), span_x * 0.055, color=bcol, alpha=0.22, zorder=3)
    ax_map.add_patch(circle)
    ax_map.scatter(bx, by, s=bsize * 1.5, color=bcol, edgecolors="#ffffff", lw=1.2, zorder=5)
    ax_map.annotate(bname, xy=(bx, by), xytext=(bx, by + span_y * 0.035),
                    ha="center", va="bottom", fontsize=7.8, fontweight="bold", color="#1c2833",
                    bbox=dict(boxstyle="round,pad=0.25", fc="#ffffff", ec=bcol, alpha=0.92, lw=0.8),
                    zorder=6)

ax_map.set_title("安徽省夜间灯光宏观空间集聚格局与区域演变带", fontsize=11.0, fontweight="bold", pad=6, color=C_TEXT)

# 下左：全省灯光总量增长曲线
nl_df = pd.read_csv(os.path.join(DATA_DIR, "anhui_nightlight_clean.csv"))
yearly_nl = nl_df.groupby("year")["sum"].sum()
years = yearly_nl.index.astype(int)
radiance = yearly_nl.values / 10000.0

color_curve = "#d35400"
ax_curve.plot(years, radiance, marker="o", markersize=3.8, color=color_curve, lw=2.0, label="夜光辐射总量 (万 nW/cm²/sr)")
ax_curve.set_xlabel("年份 (Year)", fontsize=8.5)
ax_curve.set_ylabel("夜光总量 (万单位)", fontsize=8.5, color=color_curve)
ax_curve.tick_params(axis='y', labelcolor=color_curve, labelsize=7.5)
ax_curve.tick_params(axis='x', labelsize=7.5)
ax_curve.grid(True, ls=":", alpha=0.5)
ax_curve.set_title("安徽省夜光辐射总量跨越式增长轨迹 (1986—2024)", fontsize=9.2, fontweight="bold", color=C_TEXT)

# 下右：16 市夜光总量对比横向柱状图
latest_year = yearly_nl.index.max()
city_latest = nl_df[nl_df["year"] == latest_year].groupby("city_name")["sum"].sum().sort_values()

clean_city_names = []
for c in city_latest.index:
    c_str = str(c)
    matched = None
    for item in ANHUI_CITIES:
        if item["name"][:2] in c_str or c_str[:2] in item["name"]:
            matched = item["name"]
            break
    clean_city_names.append(matched if matched else c_str)

bars = ax_city.barh(clean_city_names, city_latest.values / 1000.0, color="#2980b9", alpha=0.85, edgecolor="#1a5276", height=0.65)
ax_city.set_xlabel(f"夜光辐射总量 ({int(latest_year)}年, 千单位)", fontsize=8.5)
ax_city.tick_params(axis='both', labelsize=7.2)
ax_city.grid(True, ls=":", alpha=0.5, axis="x")
ax_city.set_title("16 个设区市夜间灯光辐射总量阶梯分布", fontsize=9.2, fontweight="bold", color=C_TEXT)

for bar in bars:
    w = bar.get_width()
    ax_city.text(w + 1.2, bar.get_y() + bar.get_height()/2, f"{w:.1f}", va='center', ha='left', fontsize=6.5, color="#2c3e50")

fig.suptitle("安徽省 1986—2024 年夜间灯光演变与区域协调发展格局", fontsize=12.5, fontweight="bold", y=0.98, color=C_TEXT)
p5 = os.path.join(OUT_DIR, "fig12-00-5_安徽省1986—2024年夜间灯光演变与区域协调发展图.png")
fig.savefig(p5, dpi=DPI)
plt.close(fig)
print(f"  ✓ Saved {p5}")

print("\n=== ALL 5 OVERVIEW FIGURES FOR ANHUI COMPLETED SUCCESSFULLY! ===")
