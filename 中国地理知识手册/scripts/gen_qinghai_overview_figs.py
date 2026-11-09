# -*- coding: utf-8 -*-
"""青海省地理统揽专题地图生成引擎（33-00）
包含 5 幅全省域权威出版级地图与分析图表（精细调优排版、微缩字号、严格杜绝压盖）：
1. fig33-00-1_青海省地形地貌与青藏高原东北部山盆格局图.png
2. fig33-00-2_青海省行政区划与“一核两副三带”城镇空间格局图.png
3. fig33-00-3_青海省综合立体交通网与高原出疆入藏大通道图.png
4. fig33-00-4_青海省现代产业体系与国家清洁能源产业高地布局图.png
5. fig33-00-5_青海省生态安全屏障与“中华水塔”三江源水系图.png
"""
import os
import sys
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Rectangle, Patch, PathPatch, Polygon
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
    gy, gx = np.gradient(dem, res)
    slope = np.arctan(np.sqrt(gx * gx + gy * gy))
    aspect = np.arctan2(-gx, gy)
    shaded = np.sin(alt_rad) * np.cos(slope) + np.cos(alt_rad) * np.sin(slope) * np.cos(az_rad - aspect)
    return np.clip(shaded, 0.0, 1.0)

def add_scalebar(ax, x0, y0, length_km=200):
    mapkit.add_scalebar(ax, x0, y0, length_km=length_km)

def add_compass(ax, x=0.94, y=0.92):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.055), transform=ax.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=1.8, headwidth=5.5, headlength=6.5),
                ha="center", va="center", fontsize=8.8, fontweight="bold", color="#2c3e50", zorder=30)

print("Loading Qinghai provincial spatial data...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
qh_prov = gpd.read_file(os.path.join(DATA_DIR, "boundaries", "datav", "630000_full.json")).to_crs(ALBERS)
qh_prov["geometry"] = qh_prov.geometry.buffer(0)
qh_union = qh_prov.union_all()
bb = qh_prov.total_bounds

span_x = bb[2] - bb[0]
span_y = bb[3] - bb[1]
pad_x = span_x * 0.05
pad_y = span_y * 0.05
ax_xlim = (bb[0] - pad_x, bb[2] + pad_x)
ax_ylim = (bb[1] - pad_y, bb[3] + pad_y)

# 加载并降采样 DEM 提高制图效率与清晰度
print("Loading Qinghai DEM...")
dem_data = np.load(os.path.join(DATA_DIR, "dem", "province", "630000_z9.npz"))
step = 2
dem_raw = dem_data['dem'][::step, ::step]
dem_res = float(dem_data['res']) * step
dem_minx = float(dem_data['minx'])
dem_maxy = float(dem_data['maxy'])
print(f"Downsampled DEM shape: {dem_raw.shape}, res: {dem_res}m")

extent = (dem_minx, dem_minx + dem_raw.shape[1] * dem_res,
          dem_maxy - dem_raw.shape[0] * dem_res, dem_maxy)

hs = calc_hillshade(dem_raw, dem_res)
norm = Normalize(vmin=1600.0, vmax=6500.0)

# 专属高原地形色带：河谷绿->黄原->棕山->冰川白紫
terrain_colors = [
    (0.00, "#27ae60"),   # 1600m 低海拔河谷林农带
    (0.12, "#7dcea0"),   # 2200m 湟水谷地与黄河河谷平原
    (0.25, "#f9e79f"),   # 2800m 柴达木盆地底与环湖浅原
    (0.38, "#d4ac0d"),   # 3400m 高原草甸丘陵
    (0.55, "#ba4a00"),   # 4200m 高寒草原与山地
    (0.72, "#78281f"),   # 5100m 高山冻原流石滩
    (0.88, "#d7bde2"),   # 5900m 现代冰川发育线
    (1.00, "#ffffff")    # 6860m 极高峰雪线白雪
]
terrain_cmap = LinearSegmentedColormap.from_list("qh_dem", terrain_colors)
dem_rgb = terrain_cmap(norm(dem_raw))[:, :, :3]
shaded_rgb = dem_rgb * (0.42 + 0.58 * hs[:, :, np.newaxis])

FIGSIZE = (9.8, 7.6)

# =============================================================================
# 图 33-00-1：青海省地形地貌与青藏高原东北部山盆格局图
# =============================================================================
print("Generating Fig 33-00-1 (Topography)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

im = ax.imshow(shaded_rgb, extent=extent, origin="upper", zorder=2)
patch = get_mpl_clip_patch(qh_union)
ax.add_patch(patch)
im.set_clip_path(patch)

qh_prov.boundary.plot(ax=ax, color="#2c3e50", lw=0.6, ls="--", zorder=5)
gpd.GeoSeries([qh_union], crs=ALBERS).boundary.plot(ax=ax, color="#1a5276", lw=1.5, zorder=6)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl1 = mapkit.SymbolLabels(ax, fig)
sl1.reserve([(0.0, 0.0, 0.38, 0.30),      # 左下角放图例
             (0.50, 0.0, 1.0, 0.09),      # 比例尺
             (0.90, 0.84, 1.0, 1.0)])     # 指北针

peaks_data = [
    ("布喀达坂峰 (6860m 青海最高峰/昆仑之巅)", 90.860, 36.020, "mt", "昆仑山脉主峰·终年冰雪覆盖"),
    ("各拉丹冬峰 (6621m 长江正源发源地)", 91.170, 33.400, "mt", "唐古拉山脉主峰·沱沱河发源冰川"),
    ("玛卿岗日 (6282m 阿尼玛卿雪山主峰)", 99.470, 34.790, "mt", "藏区四大神山之一·黄河九曲环抱"),
    ("红旗峰 (5742m 柴达木山主峰)", 96.000, 37.950, "mt", "柴达木盆地北缘天然屏障"),
    ("年保玉则主峰 (5369m 天神后花园)", 101.120, 33.280, "mt", "果洛南部冰蚀峰丛与圣湖群"),
    ("岗什卡雪峰 (5254m 祁连山东段冷龙岭)", 101.500, 37.680, "mt", "门源万亩油菜花海雪山背景"),
    ("日月山主峰 (4877m 农牧过渡天堑)", 101.050, 36.550, "mt", "季风区与非季风区地理分界隘口"),
    ("柴达木盆地干盐滩 (2675m 察尔汗)", 95.200, 36.900, "basin", "中国最大内陆封闭盐湖盆地腹地"),
    ("民和官亭黄河出境点 (1652m 青海最低点)", 102.880, 35.850, "basin", "全省海拔最低点·垂直极差达 5208m")
]

for name, lon, lat, ptype, note in peaks_data:
    px, py = to_alb(lon, lat)
    m = "^" if ptype == "mt" else "v"
    c = "#78281f" if ptype == "mt" else "#1b4f72"
    sl1.add(px, py, name, ptype, note=note, priority=1, marker=m, face=c, size=6.8,
            kind_label="主要山峰 / 极点标高" if ptype == "mt" else "主要盆地 / 最低低洼点")

waters_data = [
    ("青海湖 (中国最大咸水内陆湖 4583km²)", 100.350, 36.650, 0),
    ("扎陵湖 (黄河源姊妹湖/国际湿地)", 97.280, 34.920, 0),
    ("鄂陵湖 (黄河源第一大淡水吞吐湖)", 97.750, 34.900, 0),
    ("察尔汗盐湖 (世界级超大天然干盐滩)", 95.300, 36.850, 0),
    ("哈拉湖 (青海第二大咸水湖 607km²)", 97.580, 38.300, 0),
    ("通天河 (长江上游水系干流)", 96.800, 33.500, 40),
    ("黄河干流 (九曲黄河九曲回环)", 100.800, 35.500, 50)
]

for name, lon, lat, rot in waters_data:
    wx, wy = to_alb(lon, lat)
    sl1.add(wx, wy, name, "water", priority=2, marker="o", face="#1f618d", size=6.0, kind_label="主要江河源头 / 高原湖泊")

sym_type_h, sym_idx_h = sl1.flush()

sb_x0 = ax_xlim[0] + (ax_xlim[1] - ax_xlim[0]) * 0.58
sb_y0 = ax_ylim[0] + (ax_ylim[1] - ax_ylim[0]) * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=200)
add_compass(ax, 0.94, 0.91)

cax = ax.inset_axes([0.04, 0.07, 0.024, 0.22])
cb = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=terrain_cmap), cax=cax, orientation="vertical")
cb.set_label("高程 Elevation (m)", fontsize=6.8, color="#2c3e50")
cb.ax.tick_params(labelsize=6.0, length=2.0)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="地形与水系要素", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="图上要素编号对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("青海省地形地貌与青藏高原东北部山盆格局图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Geomorphology, Mountain Ranges & Basin Topography of Qinghai Province", transform=ax.transAxes,
        ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：AWS Terrain GLO-30 DEM · 投影：Albers 等积圆锥 (中央经线 105°E) · 制作：《中国地理知识手册》",
    fontsize=6.5)

m1_path = os.path.join(OUT_DIR, "fig33-00-1_青海省地形地貌与青藏高原东北部山盆格局图.png")
fig.savefig(m1_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"Map 1 saved: {m1_path}")

# =============================================================================
# 图 33-00-2：青海省行政区划与“一核两副三带”城镇空间格局图
# =============================================================================
print("Generating Fig 33-00-2 (Administration & Urban Hierarchy)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

palette = [
    "#d4efdf", "#fadbd8", "#d6eaf8", "#fcf3cf",
    "#ebdef0", "#e8f8f5", "#fdebd0", "#e5e8e8"
]

for i, (_, row) in enumerate(qh_prov.iterrows()):
    color = palette[i % len(palette)]
    gpd.GeoSeries([row.geometry], crs=ALBERS).plot(ax=ax, facecolor=color, edgecolor="#7f8c8d", lw=0.6, zorder=3)

gpd.GeoSeries([qh_union], crs=ALBERS).boundary.plot(ax=ax, color="#1a5276", lw=1.6, zorder=5)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl2 = mapkit.SymbolLabels(ax, fig)
sl2.reserve([(0.0, 0.0, 0.42, 0.30),
             (0.50, 0.0, 1.0, 0.09),
             (0.90, 0.84, 1.0, 1.0)])

admin_nodes = [
    ("西宁市 (全省省会/极核核心)", 101.780, 36.621, "cap", "全省政治经济中心·全省人口聚集度超 40%"),
    ("海东市 (平安区/全省第二大城市)", 102.100, 36.500, "city", "兰西城市群核心支点·临空保税区"),
    ("海北州府 (海晏县西海镇/原子城)", 100.900, 36.955, "pref", "祁连山国家公园前沿·金银滩明珠"),
    ("黄南州府 (同仁市隆务镇)", 102.015, 35.515, "pref", "热贡艺术发祥地·国家历史文化名城"),
    ("海南州府 (共和县恰卜恰镇)", 100.620, 36.280, "pref", "青海湖南岸重镇·塔拉滩绿电中心"),
    ("果洛州府 (玛沁县大武镇)", 100.240, 34.480, "pref", "阿尼玛卿雪山脚下·黄河源生态屏障"),
    ("玉树州府 (玉树市结古镇)", 97.005, 33.005, "pref", "三江之源名誉天下·三江源副中心"),
    ("海西州府 (德令哈市)", 97.370, 37.370, "pref", "柴达木东大门·金色世界德令哈"),
    ("格尔木市 (柴达木副中心/交通枢纽)", 94.900, 36.400, "sub_center", "青藏铁路线大枢纽·高原国际陆港"),
    ("茫崖市 (柴达木西大门/石油石棉新城)", 90.400, 38.250, "city", "连接新疆若羌通道·翡翠湖地标")
]

for name, lon, lat, ptype, note in admin_nodes:
    px, py = to_alb(lon, lat)
    if ptype == "cap":
        m, c, sz, kl = "*", "#922b21", 10.0, "省会中心 · 极核城市"
    elif ptype == "sub_center":
        m, c, sz, kl = "s", "#1b4f72", 7.2, "区域副中心城市"
    else:
        m, c, sz, kl = "o", "#2e4053", 6.2, "州/市府驻地 · 重点城镇"
    sl2.add(px, py, name, ptype, note=note, priority=1, marker=m, face=c, size=sz, kind_label=kl)

sym_type_h, sym_idx_h = sl2.flush()

for _, row in qh_prov.iterrows():
    c = row.geometry.representative_point()
    sname = row.get("name", "")
    if len(sname) <= 8 and sname:
        ax.text(c.x, c.y, sname, fontsize=8.0, color="#1c2833", fontweight="bold",
                ha="center", va="center", zorder=10,
                path_effects=[pe.withStroke(linewidth=2.0, foreground="#ffffff")])

add_scalebar(ax, sb_x0, sb_y0, length_km=200)
add_compass(ax, 0.94, 0.91)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="城镇等级与行政中心", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="重要节点编号对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("青海省行政区划与“一核两副三带”城镇空间格局图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Administrative Divisions & Urban Spatial Hierarchy of Qinghai Province", transform=ax.transAxes,
        ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：自然资源部标准地图与 DataV 行政区划 · 制作：《中国地理知识手册》",
    fontsize=6.5)

m2_path = os.path.join(OUT_DIR, "fig33-00-2_青海省行政区划与“一核两副三带”城镇空间格局图.png")
fig.savefig(m2_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"Map 2 saved: {m2_path}")

# =============================================================================
# 图 33-00-3：青海省综合立体交通网与高原出疆入藏大通道图
# =============================================================================
print("Generating Fig 33-00-3 (Transportation & Corridors)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

qh_prov.plot(ax=ax, facecolor="#f8f9fa", edgecolor="#bdc3c7", lw=0.6, zorder=2)
gpd.GeoSeries([qh_union], crs=ALBERS).boundary.plot(ax=ax, color="#7f8c8d", lw=1.2, zorder=3)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl3 = mapkit.SymbolLabels(ax, fig)
sl3.reserve([(0.0, 0.0, 0.40, 0.32),
             (0.50, 0.0, 1.0, 0.09),
             (0.90, 0.84, 1.0, 1.0)])

airports_data = [
    ("西宁曹家堡国际机场 (XNN/4E)", 102.040, 36.525, "airport", "高原骨干航空枢纽·覆盖全国主要城市"),
    ("格尔木机场 (GOQ/4D)", 94.790, 36.400, "airport", "青海副中心干支通航空港"),
    ("玉树巴塘机场 (YUS/4D)", 97.140, 32.835, "airport", "三江源空中生命通道"),
    ("果洛玛沁机场 (GYS/4C)", 100.300, 34.420, "airport", "阿尼玛卿雪域高原支线机场"),
    ("德令哈机场 (HXD/4C)", 97.260, 37.130, "airport", "海西首府支线机场"),
    ("花土沟机场 (HTT/4C)", 90.750, 38.200, "airport", "柴达木西大门与油田航线"),
    ("祁连机场 (HBQ/4C)", 100.680, 38.010, "airport", "东方小瑞士祁连生态旅游机场")
]

for name, lon, lat, stype, note in airports_data:
    ax_x, ay_y = to_alb(lon, lat)
    sl3.add(ax_x, ay_y, name, "airport", note=note, priority=1, marker="^", face="#7d3c98", size=7.0, kind_label="民用运输机场 (4E/4D/4C)")

rail_stations = [
    ("西宁站 (兰新高铁/青藏铁路特等枢纽)", 101.810, 36.625, "rail_hub", "青藏高原最大客运枢纽中心"),
    ("格尔木站 (青藏铁路与格库铁路交汇)", 94.920, 36.410, "rail_hub", "出疆入藏重要陆路物流大枢纽"),
    ("门源站 (兰新高铁客运大站)", 101.610, 37.360, "rail_hub", "祁连山东段高铁节点"),
    ("唐古拉站 (海拔5068m 世界最高铁路车站)", 91.920, 32.880, "rail_hub", "青藏铁路全线海拔最高极限火车站")
]

for name, lon, lat, stype, note in rail_stations:
    rx, ry = to_alb(lon, lat)
    sl3.add(rx, ry, name, "rail_hub", note=note, priority=1, marker="s", face="#1b4f72", size=6.5, kind_label="主要干线铁路客货枢纽")

corridors_data = [
    ("青藏铁路 (高原钢铁天路·西宁至拉萨)", 96.500, 36.800, 30),
    ("格库铁路 (格尔木至新疆库尔勒出疆通道)", 92.500, 37.200, 35),
    ("兰新高铁 (穿越达坂山连通甘青新)", 101.700, 37.200, 45),
    ("敦格铁路 (敦煌至格尔木重载线路)", 95.000, 38.500, 75),
    ("共玉高速 (G0613 穿越多年冻土第一高速)", 98.500, 34.600, 60),
    ("京藏高速 (G6 经西宁直抵格尔木)", 97.500, 36.900, 25),
    ("青藏公路 G109 (昆仑山口至唐古拉山口天路)", 93.000, 35.000, 50),
    ("唐蕃古道 G214 (西宁至玉树历史商道)", 98.200, 33.800, 60)
]

for name, lon, lat, rot in corridors_data:
    cx, cy = to_alb(lon, lat)
    sl3.add(cx, cy, name, "corridor", priority=2, kind_label="出省综合陆桥通道")

sym_type_h, sym_idx_h = sl3.flush()

leg_elements = [
    Line2D([0], [0], color="#c0392b", lw=2.2, label="兰新高铁客运大通道"),
    Line2D([0], [0], color="#1b4f72", lw=2.0, label="青藏铁路 / 格库 / 敦格普速动脉"),
    Line2D([0], [0], color="#e67e22", lw=1.8, label="京藏高速 / 共玉高速国家通道"),
    Line2D([0], [0], color="#27ae60", lw=1.5, ls="--", label="G109青藏线 / G214唐蕃古道")
]

add_scalebar(ax, sb_x0, sb_y0, length_km=200)
add_compass(ax, 0.94, 0.91)

leg = mapkit.stacked_legends(ax, [
    dict(handles=leg_elements + sym_type_h, title="交通方式与通道类型", ncol=2, fontsize=6.6, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="图上枢纽与通道对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("青海省综合立体交通网与高原出疆入藏大通道图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Comprehensive Transportation Network & Tibetan-Xinjiang Corridors", transform=ax.transAxes,
        ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：青海省“十四五”综合交通运输体系规划 · 制作：《中国地理知识手册》",
    fontsize=6.5)

m3_path = os.path.join(OUT_DIR, "fig33-00-3_青海省综合立体交通网与高原出疆入藏大通道图.png")
fig.savefig(m3_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"Map 3 saved: {m3_path}")

# =============================================================================
# 图 33-00-4：青海省现代产业体系与国家清洁能源产业高地布局图
# =============================================================================
print("Generating Fig 33-00-4 (Industries & Clean Energy)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

qh_prov.plot(ax=ax, facecolor="#fdfefe", edgecolor="#bdc3c7", lw=0.6, zorder=2)
gpd.GeoSeries([qh_union], crs=ALBERS).boundary.plot(ax=ax, color="#7f8c8d", lw=1.2, zorder=3)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl4 = mapkit.SymbolLabels(ax, fig)
sl4.reserve([(0.0, 0.0, 0.42, 0.32),
             (0.50, 0.0, 1.0, 0.09),
             (0.90, 0.84, 1.0, 1.0)])

industry_items = [
    ("海南州塔拉滩生态光伏基地 (全球最大单体光伏电站)", 100.450, 36.180, "pwr", "千万千瓦级光伏蓝海·光伏羊生态奇迹·绿电外送"),
    ("龙羊峡水电站 (黄河上游第一大水电龙头)", 100.920, 36.115, "hydro", "总装机128万千瓦·水光互补调峰支撑电站"),
    ("海西格尔木光伏风电基地 (戈壁大型清洁电港)", 94.600, 36.420, "pwr", "千万千瓦级多能互补综合能源基地"),
    ("察尔汗盐湖世界级钾肥与盐湖提锂基地", 95.350, 36.900, "salt", "中国最大氯化钾生产基地·全国锂盐战略重镇"),
    ("西宁南川工业园光伏锂电先进制造基地", 101.765, 36.530, "mfg", "高景太阳能·阿特斯·弗迪电池百亿先进智造"),
    ("冷湖赛什腾山世界一流天文观测基地", 93.900, 38.610, "tech", "视宁度比肩智利夏威夷·墨子巡天望远镜台址"),
    ("乌兰茶卡盐湖国家5A级景区 (天空之镜)", 99.090, 36.710, "tour", "纯白结晶盐湖·倒映蓝天雪山文旅名片"),
    ("青海湖国家5A级风景名胜区 (生态文旅地标)", 100.560, 36.585, "tour", "中国最美五大湖之首·环湖自行车赛国际舞台"),
    ("互助土族故土园5A与青稞酒酿造基地", 101.960, 36.845, "tour", "高原特色酿造·彩虹部落非遗体验"),
    ("热贡艺术之乡 (同仁国家历史文化名城)", 102.035, 35.545, "cult", "人类非物质文化遗产·藏传佛教唐卡堆绣最高峰")
]

for idx, (name, lon, lat, itype, note) in enumerate(industry_items):
    ix, iy = to_alb(lon, lat)
    if itype == "pwr":
        m, c, kl = "^", "#d35400", "国家清洁能源大基地 (光伏/风电)"
    elif itype == "hydro":
        m, c, kl = "D", "#1f618d", "大型梯级水电水光互补枢纽"
    elif itype == "salt":
        m, c, kl = "s", "#117a65", "世界级盐湖资源与现代化工"
    elif itype == "mfg":
        m, c, kl = "h", "#7d3c98", "光伏锂电先进装备制造"
    elif itype == "tech":
        m, c, kl = "p", "#2874a6", "冷湖世界一流天文观测台"
    else:
        m, c, kl = "o", "#c0392b", "国际生态文旅 / 世界文化遗产"
    sl4.add(ix, iy, name, f"ind_{idx}", note=note, priority=1, marker=m, face=c, size=6.8, kind_label=kl)

sym_type_h, sym_idx_h = sl4.flush()

add_scalebar(ax, sb_x0, sb_y0, length_km=200)
add_compass(ax, 0.94, 0.91)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="现代产业与重大示范基地", ncol=2, fontsize=6.6, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="重点基地编号对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("青海省现代产业体系与国家清洁能源产业高地布局图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Strategic Industry Clusters, Clean Energy & Salt Lake Base in Qinghai", transform=ax.transAxes,
        ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：青海省打造国家清洁能源产业高地行动方案 · 制作：《中国地理知识手册》",
    fontsize=6.5)

m4_path = os.path.join(OUT_DIR, "fig33-00-4_青海省现代产业体系与国家清洁能源产业高地布局图.png")
fig.savefig(m4_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"Map 4 saved: {m4_path}")

# =============================================================================
# 图 33-00-5：青海省生态安全屏障与“中华水塔”三江源水系图
# =============================================================================
print("Generating Fig 33-00-5 (Ecological Barriers & Sanjiangyuan)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

qh_prov.plot(ax=ax, facecolor="#f4fbf7", edgecolor="#a3e4d7", lw=0.6, zorder=2)
gpd.GeoSeries([qh_union], crs=ALBERS).boundary.plot(ax=ax, color="#145a32", lw=1.5, zorder=3)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl5 = mapkit.SymbolLabels(ax, fig)
sl5.reserve([(0.0, 0.0, 0.42, 0.32),
             (0.50, 0.0, 1.0, 0.09),
             (0.90, 0.84, 1.0, 1.0)])

eco_elements = [
    ("三江源国家公园·长江源园区 (各拉丹冬峰/沱沱河)", 92.500, 34.000, "eco_park", "格拉丹东冰川融水·孕育万里长江浩瀚水源"),
    ("三江源国家公园·黄河源园区 (扎陵湖/鄂陵湖)", 97.600, 34.910, "eco_park", "黄河源头千湖之县·牛头碑高山湿地生态核心"),
    ("三江源国家公园·澜沧江源园区 (扎曲大峡谷)", 95.300, 32.890, "eco_park", "一江连六国澜沧江湄公河正源·雪豹栖息繁育胜地"),
    ("青海可可西里世界自然遗产 (索南达杰保护站)", 92.500, 35.500, "world_herit", "无人区高原生态宝库·藏羚羊迁徙产仔通道"),
    ("祁连山国家公园 (青海片区/黑泉水源保护区)", 100.800, 37.800, "eco_park", "青藏高原东北边缘生态安全第一道绿屏"),
    ("青海湖国家级自然保护区 (鸟岛湿地/裸鲤洄游)", 100.150, 36.850, "wetland", "东亚—澳大利西亚候鸟迁徙重要中继驿站"),
    ("隆宝滩黑颈鹤国家级自然保护区 (玉树湿地)", 96.560, 33.190, "wetland", "中国最早建立的高原湿地保护区·黑颈鹤故乡"),
    ("贵德清黄河国家水利风景区 (天下黄河贵德清)", 101.435, 36.045, "river", "清澈碧水见底·黄河中上游水质调蓄带")
]

for idx, (name, lon, lat, etype, note) in enumerate(eco_elements):
    ex, ey = to_alb(lon, lat)
    if etype == "eco_park":
        m, c, kl = "s", "#196f3d", "国家公园园区 (三江源/祁连山)"
    elif etype == "world_herit":
        m, c, kl = "*", "#b7950b", "世界自然遗产 (可可西里)"
    elif etype == "wetland":
        m, c, kl = "o", "#2471a3", "国际重要湿地 / 高原鸟类乐园"
    else:
        m, c, kl = "D", "#117864", "水源涵养区 / 水土保持典范"
    sl5.add(ex, ey, name, f"eco_{idx}", note=note, priority=1, marker=m, face=c, size=7.0, kind_label=kl)

sym_type_h, sym_idx_h = sl5.flush()

add_scalebar(ax, sb_x0, sb_y0, length_km=200)
add_compass(ax, 0.94, 0.91)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="国家生态安全屏障体系", ncol=2, fontsize=6.6, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="生态关键区编号对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("青海省生态安全屏障与“中华水塔”三江源水系图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Ecological Security Barriers, Sanjiangyuan National Park & River Headwaters", transform=ax.transAxes,
        ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：三江源国家公园总体规划与生态红线保护名录 · 制作：《中国地理知识手册》",
    fontsize=6.5)

m5_path = os.path.join(OUT_DIR, "fig33-00-5_青海省生态安全屏障与“中华水塔”三江源水系图.png")
fig.savefig(m5_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"Map 5 saved: {m5_path}")

print("\nAll 5 Qinghai provincial overview maps generated successfully!")
