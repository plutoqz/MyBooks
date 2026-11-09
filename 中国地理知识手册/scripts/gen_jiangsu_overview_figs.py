# -*- coding: utf-8 -*-
"""江苏省地理统揽专题地图生成引擎（10-00）
包含 5 幅全省权威出版级地图与分析图表（精细调优排版、微缩字号、严格杜绝压盖）：
1. fig10-00-1_江苏省地势水文与平原江海宏观格局图.png
2. fig10-00-2_江苏省行政区划与“1+3”重点功能区空间格局图.png
3. fig10-00-3_江苏省综合立体交通与沿江海空枢纽网络图.png
4. fig10-00-4_江苏省现代化产业体系与新质生产力空间格局图.png
5. fig10-00-5_江苏省1986—2024年夜间灯光演变与区域协调发展图.png
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

def add_scalebar(ax, x0, y0, length_km=60):
    mapkit.add_scalebar(ax, x0, y0, length_km=length_km)

def add_compass(ax, x=0.94, y=0.92):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.055), transform=ax.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=1.8, headwidth=5.5, headlength=6.5),
                ha="center", va="center", fontsize=8.8, fontweight="bold", color="#2c3e50", zorder=30)

print("Loading Jiangsu provincial boundaries and DEM...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

js_prov = gpd.read_file(os.path.join(DATAV_DIR, "320000_full.json")).to_crs(ALBERS)
js_prov["geometry"] = js_prov.geometry.buffer(0)
js_union = js_prov.union_all()

b = js_prov.total_bounds
span_x = b[2] - b[0]
span_y = b[3] - b[1]
pad_x = span_x * 0.04
pad_y = span_y * 0.04
ax_xlim = (b[0] - pad_x, b[2] + pad_x)
ax_ylim = (b[1] - pad_y, b[3] + pad_y)

# 加载 DEM
dem_file = os.path.join(DATA_DIR, "dem", "province", "320000_z9.npz")
dem_data = np.load(dem_file)
step = 2
dem_raw = np.nan_to_num(dem_data['dem'][::step, ::step], nan=0.0)
dem_res = float(dem_data['res']) * step
dem_minx = float(dem_data['minx'])
dem_maxy = float(dem_data['maxy'])
print(f"Downsampled Jiangsu DEM shape: {dem_raw.shape}, res: {dem_res}m")

extent = (dem_minx, dem_minx + dem_raw.shape[1] * dem_res,
          dem_maxy - dem_raw.shape[0] * dem_res, dem_maxy)

hs = calc_hillshade(dem_raw, dem_res)
norm = Normalize(vmin=0.0, vmax=625.0)

# 江苏平原为主、低山残丘阶梯分层色标 (0m-625m)
terrain_colors = [
    (0.00, "#196f3d"),   # 0m-4m 沿海滩涂、里下河洼地与河口冲积区
    (0.03, "#27ae60"),   # 5m-15m 广大平原主体、太湖平原与黄淮平原
    (0.08, "#7dcea0"),   # 20m-40m 古冈身带、岗地与冲积台地
    (0.18, "#f9e79f"),   # 40m-100m 江淮丘陵过渡带与徐州残丘
    (0.35, "#eb984e"),   # 100m-220m 幕府山、栖霞山、南通五山、云龙山
    (0.55, "#dc7633"),   # 220m-350m 惠山、天平山、茅山大茅峰
    (0.75, "#ba4a00"),   # 350m-480m 紫金山、老山、穹窿山、宝华山
    (1.00, "#78281f")    # 480m-624.4m 宜兴黄塔顶、云台山玉女峰 (全省最高峰)
]
terrain_cmap = LinearSegmentedColormap.from_list("js_dem", terrain_colors)
dem_rgb = terrain_cmap(norm(dem_raw))[:, :, :3]
shaded_rgb = dem_rgb * (0.44 + 0.56 * hs[:, :, np.newaxis])

FIGSIZE = (9.8, 9.2)

# =============================================================================
# 图 10-00-1：江苏省地势水文与平原江海宏观格局图
# =============================================================================
print("Generating Fig 10-00-1 (Topography & River-Sea Pattern)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

im = ax.imshow(shaded_rgb, extent=extent, origin="upper", zorder=2)
patch = get_mpl_clip_patch(js_union)
ax.add_patch(patch)
im.set_clip_path(patch)

js_prov.boundary.plot(ax=ax, color="#2c3e50", lw=0.6, ls="--", zorder=5)
gpd.GeoSeries([js_union], crs=ALBERS).boundary.plot(ax=ax, color="#1a5276", lw=1.5, zorder=6)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl1 = mapkit.SymbolLabels(ax, fig)
sl1.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.50, 0.0, 1.0, 0.09),
             (0.88, 0.86, 1.0, 1.0)])

peaks_data = [
    ("云台山玉女峰 (624.4m 全省最高峰·海天胜境)", 119.298, 34.655, "peak", "江苏自然地理第一高峰·连云港"),
    ("宜兴黄塔顶 (611.5m 苏南最高峰·竹海界岭)", 119.680, 31.150, "peak", "苏南第一高峰·无锡宜兴"),
    ("溧阳锅底山 (545.0m 苏皖界岭名山)", 119.380, 31.250, "mt", "常州最高峰·瓦屋山连绵"),
    ("紫金山头陀岭 (448.9m 钟山龙蟠·南京名山)", 118.848, 32.072, "mt", "南京第一名山·世界文化遗产明孝陵"),
    ("老山龙洞山 (442.1m 江北绿色生态屏障)", 118.580, 32.080, "mt", "南京浦口生态氧吧"),
    ("句容宝华山 (420.0m 律宗第一名山)", 119.090, 32.140, "mt", "镇江最高峰·隆昌寺千僧戒坛"),
    ("穹窿山箬帽顶 (398.0m 太湖东岸第一峰)", 120.430, 31.260, "mt", "苏州最高峰·孙子兵法诞生地"),
    ("铜山拉犁山 (396.0m 淮海丘陵高点)", 117.200, 34.120, "mt", "徐州自然最高点"),
    ("茅山大茅峰 (372.5m 道教第一福地第八洞天)", 119.320, 31.790, "mt", "句容常州金坛界山"),
    ("南通狼山 (106.9m 大势至菩萨道场·江海名山)", 120.890, 31.955, "mt", "南通五山之首·长江滨江绿廊")
]

for name, lon, lat, ptype, desc in peaks_data:
    px, py = to_alb(lon, lat)
    m = "*" if ptype == "peak" else "^"
    fc = "#c0392b" if ptype == "peak" else "#922b21"
    sl1.add(px, py, name, ptype, note=desc, priority=0 if ptype == "peak" else 1,
            marker=m, face=fc, size=7.2 if ptype == "peak" else 5.2, kind_label="地形控制性极点与名山大川")

waters_data = [
    ("长江干流江苏段 (横贯东西433公里·通江达海黄金通道)", 119.500, 32.200, "water", "长江横贯苏南苏中注入东海"),
    ("京杭大运河江苏段 (纵贯南北690公里·全线活态水运航道)", 119.450, 33.200, "water", "全国运河航运最繁忙省份"),
    ("太湖水域 (2427km² 中国第三大淡水湖)", 120.200, 31.250, "water", "江南水网核心调蓄水源"),
    ("洪泽湖 (1576km² 中国第四大淡水湖·日出斗金)", 118.750, 33.350, "water", "淮河下游巨大调蓄平原水库"),
    ("高邮湖 (全省第三大淡水湖·水乡胜境)", 119.350, 32.800, "water", "里下河水网重要调蓄湖荡"),
    ("骆马湖 (苏北重要生态湖泊·碧水清波)", 118.200, 34.100, "water", "宿迁徐州交界生态屏障"),
    ("淮河入海水道 (淮河流域特大防洪入海通道)", 119.500, 33.600, "water", "千里淮河直达黄海出海口"),
    ("黄海湿地与辐射沙洲 (中国首个滨海湿地世界自然遗产)", 120.900, 33.000, "water", "东亚候鸟迁徙关键生命通道")
]

for name, lon, lat, wtype, desc in waters_data:
    px, py = to_alb(lon, lat)
    sl1.add(px, py, name, wtype, note=desc, priority=2,
            marker="s", face="#1b4f72", size=4.8, kind_label="骨干江河水系与著名湖泊海域")

sym_type_h, sym_idx_h = sl1.flush()

sb_x0 = ax_xlim[0] + span_x * 0.55
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=60)
add_compass(ax, 0.94, 0.91)

leg1 = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="地形与水系要素分类", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="图上要素编号对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("江苏省地势水文与平原江海宏观格局图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Geomorphology, Estuary Hydrology & Lake Basins of Jiangsu Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg1, "数据源：AWS Terrain 300m 高程 · 投影：Albers 等积圆锥 (中央经线 105°E) · 制作：《中国地理知识手册》",
    fontsize=6.5)

f1_path = os.path.join(OUT_DIR, "fig10-00-1_江苏省地势水文与平原江海宏观格局图.png")
fig.savefig(f1_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"✓ Saved Fig 10-00-1: {f1_path}")

# =============================================================================
# 图 10-00-2：江苏省行政区划与“1+3”重点功能区空间格局图
# =============================================================================
print("Generating Fig 10-00-2 (Administrative & Spatial Function Zones)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

# “1+3”重点功能区底色填涂：
# 扬子江城市群 (沿江8市): 南京(320100)、无锡(320200)、常州(320400)、苏州(320500)、南通(320600)、扬州(321000)、镇江(321100)、泰州(321200) -> 浅蓝绿
# 沿海经济带 (连云港320700、盐城320900、南通320600叠合沿海) -> 浅青色
# 江淮生态经济区 (淮安320800、宿迁321300) -> 浅黄绿
# 徐州淮海经济区中心城市 (徐州320300) -> 浅紫色
zone_colors = {
    "320100": "#e8f8f5", "320200": "#e8f8f5", "320400": "#e8f8f5", "320500": "#e8f8f5",
    "321000": "#e8f8f5", "321100": "#e8f8f5", "321200": "#e8f8f5",
    "320600": "#e0f2f1", # 南通江海联通
    "320700": "#eaf2f8", "320900": "#eaf2f8", # 沿海经济带
    "320800": "#fef9e7", "321300": "#fef9e7", # 江淮生态经济区
    "320300": "#f4ecf7"  # 徐州淮海中心
}

for i, (_, row) in enumerate(js_prov.iterrows()):
    ad = str(row.get("adcode", ""))
    fill_col = zone_colors.get(ad, "#ffffff")
    gpd.GeoSeries([row.geometry], crs=ALBERS).plot(ax=ax, facecolor=fill_col, edgecolor="#7f8c8d", lw=0.6, zorder=3)

gpd.GeoSeries([js_union], crs=ALBERS).boundary.plot(ax=ax, color="#1a5276", lw=1.6, zorder=6)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl2 = mapkit.SymbolLabels(ax, fig)
sl2.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.50, 0.0, 1.0, 0.09),
             (0.88, 0.86, 1.0, 1.0)])

admin_hubs = [
    ("南京市 (省会·特大城市·副省级)", 118.798, 32.058, "core", "东部中心城市·科教中心·1.78万亿极核"),
    ("苏州市 (最强地级市·人间天堂)", 120.590, 31.300, "core", "国家高新技术高地·2.58万亿领头羊"),
    ("无锡市 (太湖明珠·人均GDP第一城)", 120.315, 31.490, "sub", "中国物联网之都·集成电路高地·1.62万亿"),
    ("南通市 (江海门户·近代第一城)", 120.895, 32.010, "sub", "现代船舶海工制造母港·1.24万亿新门户"),
    ("常州市 (长三角新能源之都·万亿之城)", 119.970, 31.810, "sub", "动力电池光伏新能源智造名城·1.06万亿"),
    ("徐州市 (淮海经济区中心城市·五省通衢)", 117.275, 34.225, "hub", "中国工程机械之都·两汉文化策源地·9500亿"),
    ("扬州市 (世界运河之都与美食之都)", 119.390, 32.390, "node", "大运河原点城市·淮左名都·7700亿"),
    ("盐城市 (东方湿地之都·仙鹤神鹿家园)", 120.160, 33.350, "node", "黄海湿地世界遗产·全省第一海岸线·7600亿"),
    ("泰州市 (祥泰之州·中国医药城)", 119.920, 32.460, "node", "全国首个国家级医药高新区·造船重镇·6900亿"),
    ("镇江市 (城市山林·三山名胜·中国醋都)", 119.425, 32.190, "node", "江河交汇第一枢纽·恒顺香醋丹阳眼镜·5500亿"),
    ("淮安市 (运河之都·周总理故乡)", 119.040, 33.560, "node", "苏北重要中心城市·洪泽湖湿地·淮扬菜·5300亿"),
    ("宿迁市 (西楚霸王故里·中国酒都)", 118.280, 33.960, "node", "洋河双沟发祥地·电商名城花木之乡·4600亿"),
    ("连云港市 (新亚欧陆桥东方桥头堡)", 119.220, 34.600, "node", "一带一路强支点·中华药港·深水大港·4500亿")
]

for name, lon, lat, ctype, desc in admin_hubs:
    px, py = to_alb(lon, lat)
    m = "*" if ctype == "core" else ("s" if ctype == "sub" else ("D" if ctype == "hub" else "o"))
    fc = "#c0392b" if ctype == "core" else ("#2980b9" if ctype == "sub" else ("#8e44ad" if ctype == "hub" else "#27ae60"))
    sl2.add(px, py, name, ctype, note=desc, priority=0 if ctype in ("core", "sub") else 1,
            marker=m, face=fc, size=7.2 if ctype == "core" else 5.2, kind_label="地级行政中心与城市能级")

sym_type_h2, sym_idx_h2 = sl2.flush()

sb_x0 = ax_xlim[0] + span_x * 0.55
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=60)
add_compass(ax, 0.94, 0.91)

leg2 = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h2, title="行政中心与城市能级", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h2, title="全省13地级市定位简述", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("江苏省行政区划与“1+3”重点功能区空间格局图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Administrative Structure & '1+3' Functional Regions of Jiangsu Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg2, "数据源：江苏省国土空间总体规划 (2021-2035) · 民政部标准地名代码 · 制作：《中国地理知识手册》",
    fontsize=6.5)

f2_path = os.path.join(OUT_DIR, "fig10-00-2_江苏省行政区划与“1+3”重点功能区空间格局图.png")
fig.savefig(f2_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"✓ Saved Fig 10-00-2: {f2_path}")

# =============================================================================
# 图 10-00-3：江苏省综合立体交通与沿江海空枢纽网络图
# =============================================================================
print("Generating Fig 10-00-3 (Transport & River-Sea Hubs)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

gpd.GeoSeries([js_union], crs=ALBERS).plot(ax=ax, facecolor="#ffffff", edgecolor="#1a5276", lw=1.6, zorder=2)
js_prov.boundary.plot(ax=ax, color="#cbd5e0", lw=0.6, ls=":", zorder=3)

# 绘制高铁走廊骨架
# 京沪高铁、沪宁城际、沪宁沿江、连徐高铁、徐宿淮盐、盐通高铁、连镇高铁、宁杭高铁、沪苏湖高铁
rail_lines = [
    # 京沪高铁 (徐州 -> 宿迁界 -> 蚌埠 -> 南京 -> 镇江 -> 常州 -> 无锡 -> 苏州 -> 昆山)
    [(117.29, 34.27), (117.90, 33.50), (118.79, 31.96), (119.42, 32.14), (119.97, 31.85), (120.44, 31.59), (120.64, 31.42), (120.96, 31.35)],
    # 沪宁城际铁路 (南京 -> 镇江 -> 丹阳 -> 常州 -> 无锡 -> 苏州 -> 昆山)
    [(118.80, 32.08), (119.43, 32.19), (119.57, 31.99), (119.96, 31.79), (120.30, 31.59), (120.60, 31.33), (120.96, 31.35)],
    # 沪宁沿江高铁 (南京南 -> 句容 -> 金坛 -> 武进 -> 江阴 -> 张家港 -> 常熟 -> 太仓)
    [(118.79, 31.96), (119.20, 31.98), (119.62, 31.72), (119.94, 31.70), (120.31, 31.87), (120.68, 31.82), (120.75, 31.65), (121.11, 31.45)],
    # 连徐高铁 (连云港 -> 东海 -> 新沂 -> 邳州 -> 徐州东)
    [(119.18, 34.61), (118.78, 34.52), (118.35, 34.37), (117.96, 34.31), (117.29, 34.27)],
    # 徐宿淮盐高铁 (徐州东 -> 宿迁 -> 泗阳 -> 淮安东 -> 阜宁南 -> 建湖 -> 盐城)
    [(117.29, 34.27), (118.33, 33.93), (118.68, 33.70), (119.14, 33.56), (119.80, 33.60), (120.17, 33.39)],
    # 盐通高铁与沪苏通 (盐城 -> 东台 -> 海安 -> 如皋南 -> 南通西 -> 张家港 -> 常熟 -> 太仓)
    [(120.17, 33.39), (120.33, 32.87), (120.46, 32.53), (120.56, 32.39), (120.78, 32.08), (120.68, 31.82), (121.11, 31.45)],
    # 连镇高铁 (连云港 -> 灌云 -> 灌南 -> 涟水 -> 淮安东 -> 宝应 -> 高邮 -> 扬州东 -> 镇江)
    [(119.18, 34.61), (119.24, 34.28), (119.35, 34.09), (119.26, 33.78), (119.14, 33.56), (119.32, 33.23), (119.45, 32.79), (119.52, 32.41), (119.43, 32.19)],
    # 宁杭高铁 (南京南 -> 江宁 -> 溧水 -> 溧阳 -> 宜兴 -> 湖州)
    [(118.79, 31.96), (119.03, 31.65), (119.51, 31.40), (119.82, 31.36)]
]

for r_pts in rail_lines:
    xs, ys = mapkit.smooth_line([to_alb(p[0], p[1]) for p in r_pts])
    ax.plot(xs, ys, color="#c0392b", lw=2.2, zorder=8, alpha=0.9)

# 绘制高速公路主骨架
# G42沪蓉高速、G2京沪高速、G15沈海高速、G30连霍高速
hwy_lines = [
    [(118.70, 32.05), (119.40, 32.15), (119.95, 31.80), (120.35, 31.60), (120.65, 31.35), (121.05, 31.30)], # 沪蓉
    [(117.30, 34.35), (118.30, 33.90), (119.10, 33.50), (119.50, 32.50), (120.10, 32.20), (120.40, 31.60)], # 京沪
    [(119.30, 34.70), (120.20, 33.40), (120.80, 32.10), (121.10, 31.60)], # 沈海
    [(117.20, 34.30), (118.00, 34.35), (118.80, 34.50), (119.40, 34.70)]  # 连霍
]

for h_pts in hwy_lines:
    xs, ys = mapkit.smooth_line([to_alb(p[0], p[1]) for p in h_pts])
    ax.plot(xs, ys, color="#2980b9", lw=1.6, ls="--", zorder=7, alpha=0.85)

# 绘制京杭运河水运线
canal_pts = [
    (117.30, 34.35), (117.96, 34.31), (118.25, 33.98), (119.06, 33.53),
    (119.45, 32.79), (119.45, 32.40), (119.55, 32.18), (119.95, 31.75),
    (120.30, 31.56), (120.61, 31.28)
]
cxs, cys = zip(*[to_alb(p[0], p[1]) for p in canal_pts])
ax.plot(cxs, cys, color="#1a5276", lw=2.8, zorder=6, alpha=0.9)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl3 = mapkit.SymbolLabels(ax, fig)
sl3.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.50, 0.0, 1.0, 0.09),
             (0.88, 0.86, 1.0, 1.0)])

hubs_data = [
    ("南京南站 (亚洲特大型综合高铁客运总枢纽)", 118.795, 31.968, "rail", "京沪/宁杭/宁安/沪宁沿江大十字枢纽"),
    ("徐州东站 (京沪与徐兰双十字高铁大枢纽)", 117.295, 34.270, "rail", "淮海经济区客运总门户·高铁特等站"),
    ("苏州北站与无锡东站 (苏南高铁核心门户组团)", 120.540, 31.500, "rail", "京沪高铁苏锡高频客流集聚区"),
    ("淮安东站 (苏北高铁金腰带多线交汇枢纽)", 119.145, 33.560, "rail", "徐宿淮盐与连镇高铁交汇综合站"),
    ("太仓港 (长江第一大集装箱外贸内支线良港)", 121.200, 31.600, "port", "年吞吐量超800万标箱·江海联运第一港"),
    ("连云港港 (新亚欧大陆桥东方起点30万吨级深水大港)", 119.420, 34.740, "port", "中哈物流基地·陆桥运输东方出海口"),
    ("南京港新生圩/龙潭港区 (长江深水集装箱大港)", 119.050, 32.180, "port", "长江12.5米深水航道终点门户港"),
    ("南京禄口国际机场 (4F级洲际门户·全省航空第一枢纽)", 118.865, 31.740, "airport", "年旅客吞吐量突破3000万人次"),
    ("苏南硕放国际机场 (4E级军民合用空港·苏锡协同门户)", 120.435, 31.495, "airport", "长三角世界级机场群核心骨干机场"),
    ("江阴长江大桥与苏通长江公路大桥 (跨江咽喉超级工程)", 120.500, 31.950, "bridge", "世界级跨江悬索与斜拉大桥"),
    ("沪苏通长江公铁大桥 (世界首座千米级公铁两用斜拉桥)", 120.750, 32.010, "bridge", "长江下游综合公铁两用跨江大通道")
]

for name, lon, lat, htype, desc in hubs_data:
    px, py = to_alb(lon, lat)
    m = "s" if htype == "rail" else ("p" if htype == "port" else ("D" if htype == "airport" else "^"))
    fc = "#c0392b" if htype == "rail" else ("#1a5276" if htype == "port" else ("#27ae60" if htype == "airport" else "#d35400"))
    sl3.add(px, py, name, htype, note=desc, priority=0 if htype in ("rail", "port") else 1,
            marker=m, face=fc, size=6.8 if htype in ("rail", "port") else 5.2, kind_label="综合交通网络骨干枢纽")

sym_type_h3, sym_idx_h3 = sl3.flush()

sb_x0 = ax_xlim[0] + span_x * 0.55
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=60)
add_compass(ax, 0.94, 0.91)

leg3 = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h3, title="枢纽类型与综合交通要素", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h3, title="骨干交通枢纽名录", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("江苏省综合立体交通与沿江海空枢纽网络图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Integrated Transport Network, Aviation & Deep-water Ports of Jiangsu Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg3, "数据源：中国国家铁路集团 · 江苏省综合立体交通网规划纲要 · 制作：《中国地理知识手册》",
    fontsize=6.5)

f3_path = os.path.join(OUT_DIR, "fig10-00-3_江苏省综合立体交通与沿江海空枢纽网络图.png")
fig.savefig(f3_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"✓ Saved Fig 10-00-3: {f3_path}")

# =============================================================================
# 图 10-00-4：江苏省现代化产业体系与新质生产力空间格局图
# =============================================================================
print("Generating Fig 10-00-4 (Modern Industry & Productive Forces)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

gpd.GeoSeries([js_union], crs=ALBERS).plot(ax=ax, facecolor="#ffffff", edgecolor="#1a5276", lw=1.6, zorder=2)
js_prov.boundary.plot(ax=ax, color="#cbd5e0", lw=0.6, ls="--", zorder=3)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl4 = mapkit.SymbolLabels(ax, fig)
sl4.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.50, 0.0, 1.0, 0.09),
             (0.88, 0.86, 1.0, 1.0)])

industries_data = [
    ("苏州工业园区国家级生物医药与纳米技术高地", 120.750, 31.280, "it", "生物医药创新药全国前列·纳米新材料全球高地"),
    ("无锡国家传感网创新示范区与物联网集群", 120.380, 31.520, "it", "中国物联网第一城·千亿级智能传感与微电子"),
    ("华虹半导体与SK海力士超大规模晶圆制造基地", 120.400, 31.480, "it", "全国规模最大的集成电路半导体制造策源地"),
    ("常州长三角新能源之都 (中创新航/蜂巢/理想)", 119.800, 31.700, "energy", "动力电池产量全国第一·新能源整车百万辆航母"),
    ("徐工集团工程机械大国重器集群 (徐州)", 117.280, 34.310, "mfg", "中国工程机械之都·全地面起重机世界首位"),
    ("中国软件谷与紫金山未来网络国家实验室 (南京)", 118.800, 31.960, "it", "全国首批软件名城核心·未来网络大科学装置"),
    ("南通世界级高端海工装备与豪华邮轮建造母港", 121.250, 31.850, "marine", "招商重工中远海运·极地科考船与深水重装基地"),
    ("连云港中华药港创新药集群 (恒瑞/正大天晴/豪森)", 119.280, 34.620, "med", "抗肿瘤药创新药研发全国第一高地"),
    ("徐圩新区国家级现代石化基地 (盛虹炼化一体化)", 119.550, 34.550, "chem", "全流程绿色低碳现代大型炼化航母"),
    ("盐城海上风电装备制造基地与光伏超级集群", 120.750, 33.220, "energy", "海上风电装机破千万千瓦·通威晶澳天合基地"),
    ("中国医药城 (泰州国家医药高新区)", 119.880, 32.380, "med", "全国首个国家级医药高新区·疫苗与抗体药物基地"),
    ("新扬子造船与新时代造船基地 (靖江)", 120.250, 31.980, "marine", "全国民营造船第一县·清洁能源LNG动力大船"),
    ("洋河股份与双沟酒业中国白酒之都基地 (宿迁)", 118.360, 33.780, "agri", "绵柔型白酒国家标准策源地·百亿级生态酿造"),
    ("丹阳全球眼镜之都产业集群 (镇江)", 119.590, 31.980, "mfg", "镜片出货量占全球四成·中国眼镜第一城"),
    ("盛虹与恒力世界500强高端化纤纺织总部 (吴江)", 120.680, 31.140, "chem", "全球最大差别化涤纶长丝与芳纶新材料基地")
]

for name, lon, lat, ikind, desc in industries_data:
    px, py = to_alb(lon, lat)
    m = "D"
    fc = "#c0392b" if ikind == "mfg" else ("#2980b9" if ikind == "it" else ("#16a085" if ikind in ("med", "marine") else ("#d35400" if ikind == "energy" else "#8e44ad")))
    sl4.add(px, py, name, ikind, note=desc, priority=1,
            marker=m, face=fc, size=5.5, kind_label="先进制造与战略性新兴产业集群")

sym_type_h4, sym_idx_h4 = sl4.flush()

sb_x0 = ax_xlim[0] + span_x * 0.55
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=60)
add_compass(ax, 0.94, 0.91)

leg4 = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h4, title="优势产业集群大类", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h4, title="重大产业地标与领航旗舰", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("江苏省现代化产业体系与新质生产力空间格局图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Major Strategic Industries & Innovation Clusters of Jiangsu Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg4, "数据源：江苏省工业和信息化厅 · 江苏省统计局 · 制作：《中国地理知识手册》",
    fontsize=6.5)

f4_path = os.path.join(OUT_DIR, "fig10-00-4_江苏省现代化产业体系与新质生产力空间格局图.png")
fig.savefig(f4_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"✓ Saved Fig 10-00-4: {f4_path}")

# =============================================================================
# 图 10-00-5：江苏省1986—2024年夜间灯光演变与区域协调发展图
# =============================================================================
print("Generating Fig 10-00-5 (Nightlight Trends)...")
fig = plt.figure(figsize=(11.0, 7.2), dpi=DPI)
fig.patch.set_facecolor("white")

gs = fig.add_gridspec(nrows=1, ncols=2, width_ratios=[1.15, 1.0], wspace=0.18,
                      left=0.03, right=0.97, top=0.92, bottom=0.08)

ax_map = fig.add_subplot(gs[0, 0])
ax_plot = fig.add_subplot(gs[0, 1])

ax_map.set_facecolor("#0b132b")
js_prov.plot(ax=ax_map, facecolor="#1c2541", edgecolor="#3a506b", lw=0.6, zorder=2)
gpd.GeoSeries([js_union], crs=ALBERS).boundary.plot(ax=ax_map, color="#5bc0be", lw=1.2, zorder=6)

nl_df = pd.read_csv(os.path.join(DATA_DIR, "jiangsu_nightlight_clean.csv"))
city_nl = nl_df.groupby(['city_code', 'city_name', 'year'])['sum'].sum().reset_index()

glow_points = [
    ("苏州与昆山太仓连绵带", 120.70, 31.35, 320000, "#f1c40f"),
    ("南京主城与江宁河西", 118.80, 32.05, 180000, "#f1c40f"),
    ("无锡主城与江阴宜兴", 120.30, 31.55, 170000, "#f39c12"),
    ("常州主城与武进新北", 119.95, 31.80, 140000, "#f39c12"),
    ("南通主城与海门海安", 120.90, 32.05, 150000, "#e67e22"),
    ("徐州主城与铜山新城", 117.20, 34.25, 130000, "#f39c12"),
    ("盐城主城与大丰港区", 120.20, 33.35, 120000, "#e67e22"),
    ("扬州主城与江都广陵", 119.45, 32.40, 110000, "#f39c12"),
    ("泰州主城与泰兴靖江", 119.95, 32.40, 105000, "#e67e22"),
    ("镇江主城与丹阳句容", 119.45, 32.15, 95000, "#f39c12"),
    ("淮安主城与涟水清江", 119.05, 33.55, 90000, "#f39c12"),
    ("连云港海州与徐圩港", 119.30, 34.65, 85000, "#f1c40f"),
    ("宿迁主城与沭阳泗洪", 118.30, 33.95, 80000, "#f39c12")
]

for gname, lon, lat, val, gcol in glow_points:
    px, py = to_alb(lon, lat)
    rad = np.sqrt(val) * 110.0
    ax_map.scatter(px, py, s=rad*0.06, c=gcol, alpha=0.35, edgecolors="none", zorder=8)
    ax_map.scatter(px, py, s=rad*0.02, c="#ffffff", alpha=0.75, edgecolors="none", zorder=9)
    ax_map.text(px, py, gname.split("与")[0], color="#ffffff", fontsize=6.8, weight="bold",
                ha="center", va="bottom", zorder=15,
                path_effects=[pe.withStroke(linewidth=1.8, foreground="#000000", alpha=0.8)])

ax_map.set_xlim(ax_xlim)
ax_map.set_ylim(ax_ylim)
ax_map.axis("off")
ax_map.set_title("江苏省夜间灯光辐射空间分布与高亮集聚轴", fontsize=9.2, color="#ffffff", weight="bold", pad=8)

ax_plot.set_facecolor("#ffffff")
ax_plot.grid(True, linestyle="--", alpha=0.45, color="#bdc3c7")

focus_cities = [
    ("苏州市", "#c0392b", 2.4, "-"),
    ("南京市", "#2980b9", 2.4, "-"),
    ("无锡市", "#27ae60", 2.0, "-"),
    ("南通市", "#8e44ad", 2.0, "-"),
    ("常州市", "#d35400", 2.0, "-"),
    ("徐州市", "#16a085", 1.8, "--"),
    ("盐城市", "#f39c12", 1.8, "--"),
    ("扬州市", "#7f8c8d", 1.6, ":"),
    ("泰州市", "#34495e", 1.6, ":"),
    ("镇江市", "#e74c3c", 1.6, "-.")
]

for cname, col, lw, ls in focus_cities:
    sub = city_nl[city_nl['city_name'] == cname].sort_values('year')
    if len(sub) > 0:
        ax_plot.plot(sub['year'], sub['sum'], color=col, lw=lw, ls=ls, label=cname, alpha=0.9)

ax_plot.set_xlabel("年份 (1986—2013/2024)", fontsize=8.5, color="#2c3e50")
ax_plot.set_ylabel("夜间灯光辐射总指数 (DN Sum)", fontsize=8.5, color="#2c3e50")
ax_plot.set_title("江苏省主要地级市夜间灯光演变曲线 (1986—2024)", fontsize=9.2, weight="bold", color="#1a252f", pad=8)
ax_plot.legend(loc="upper left", fontsize=6.8, framealpha=0.9, ncol=2)

fig.suptitle("江苏省1986—2024年夜间灯光演变与区域协调发展图", fontsize=12.5, weight="bold", y=0.985, color="#1a252f")

f5_path = os.path.join(OUT_DIR, "fig10-00-5_江苏省1986—2024年夜间灯光演变与区域协调发展图.png")
fig.savefig(f5_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"✓ Saved Fig 10-00-5: {f5_path}")

print("\n=== ALL 5 JIANGSU OVERVIEW FIGURES COMPLETED SUCCESSFULLY! ===")
