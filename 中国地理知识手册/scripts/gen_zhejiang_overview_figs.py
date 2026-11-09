# -*- coding: utf-8 -*-
"""浙江省地理统揽专题地图生成引擎（11-00）
包含 5 幅全省权威出版级地图与分析图表（精细调优排版、微缩字号、严格杜绝压盖）：
1. fig11-00-1_浙江省地势起伏与山海交融水文格局图.png
2. fig11-00-2_浙江省行政区划与四大都市区空间格局图.png
3. fig11-00-3_浙江省综合立体交通与港口航运枢纽网络图.png
4. fig11-00-4_浙江省现代产业集群与数字经济高地空间格局图.png
5. fig11-00-5_浙江省1986—2024年夜间灯光演变与山海协作发展图.png
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

print("Loading Zhejiang provincial boundaries and DEM...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

zj_prov = gpd.read_file(os.path.join(DATAV_DIR, "330000_full.json")).to_crs(ALBERS)
zj_prov["geometry"] = zj_prov.geometry.buffer(0)
zj_union = zj_prov.union_all()

b = zj_prov.total_bounds
span_x = b[2] - b[0]
span_y = b[3] - b[1]
pad_x = span_x * 0.04
pad_y = span_y * 0.04
ax_xlim = (b[0] - pad_x, b[2] + pad_x)
ax_ylim = (b[1] - pad_y, b[3] + pad_y)

# 加载 DEM
dem_file = os.path.join(DATA_DIR, "dem", "province", "330000_z9.npz")
dem_data = np.load(dem_file)
step = 2
dem_raw = np.nan_to_num(dem_data['dem'][::step, ::step], nan=0.0)
dem_res = float(dem_data['res']) * step
dem_minx = float(dem_data['minx'])
dem_maxy = float(dem_data['maxy'])
print(f"Downsampled Zhejiang DEM shape: {dem_raw.shape}, res: {dem_res}m")

extent = (dem_minx, dem_minx + dem_raw.shape[1] * dem_res,
          dem_maxy - dem_raw.shape[0] * dem_res, dem_maxy)

hs = calc_hillshade(dem_raw, dem_res)
norm = Normalize(vmin=0.0, vmax=1930.0)

# 浙江“七山一水二分田”山海交融阶梯地貌色标 (0m-1929m)
terrain_colors = [
    (0.00, "#196f3d"),   # 0m-20m 杭嘉湖平原、宁绍平原、温黄平原与沿海滩涂
    (0.04, "#27ae60"),   # 20m-80m 滨海平原冲积带向内陆低阶地过渡
    (0.10, "#52be80"),   # 80m-200m 金衢盆地红层低丘与山前冲积扇
    (0.20, "#f9e79f"),   # 200m-400m 浙北低山丘陵、富春江两岸缓丘
    (0.35, "#eb984e"),   # 400m-700m 四明山、会稽山、天台山中低山体
    (0.55, "#dc7633"),   # 700m-1100m 括苍山、大盘山、千里岗主体山脊
    (0.75, "#ba4a00"),   # 1100m-1500m 雁荡山白云尖、仙霞岭大龙岗、天目山龙王山
    (0.92, "#873600"),   # 1500m-1800m 临安清凉峰、庆元百山祖
    (1.00, "#4a235a")    # 1800m-1929m 龙泉凤阳山黄茅尖（长三角最高峰）
]
terrain_cmap = LinearSegmentedColormap.from_list("zj_dem", terrain_colors)
dem_rgb = terrain_cmap(norm(dem_raw))[:, :, :3]
shaded_rgb = dem_rgb * (0.44 + 0.56 * hs[:, :, np.newaxis])

FIGSIZE = (9.8, 9.4)

# =============================================================================
# 图 11-00-1：浙江省地势起伏与山海交融水文格局图
# =============================================================================
print("Generating Fig 11-00-1 (Topography & River-Sea Pattern)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

im = ax.imshow(shaded_rgb, extent=extent, origin="upper", zorder=2)
patch = get_mpl_clip_patch(zj_union)
ax.add_patch(patch)
im.set_clip_path(patch)

zj_prov.boundary.plot(ax=ax, color="#2c3e50", lw=0.6, ls="--", zorder=5)
gpd.GeoSeries([zj_union], crs=ALBERS).boundary.plot(ax=ax, color="#1a5276", lw=1.5, zorder=6)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl1 = mapkit.SymbolLabels(ax, fig)
sl1.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.50, 0.0, 1.0, 0.09),
             (0.88, 0.86, 1.0, 1.0)])

peaks_data = [
    ("黄茅尖 (1929.0m 龙泉凤阳山·浙江及长三角第一高峰)", 119.185, 27.895, "peak", "华东大陆地理制高点"),
    ("百山祖 (1856.7m 庆元·百山之祖)", 119.065, 27.755, "peak", "浙江第二高峰·百山祖冷杉模式产地"),
    ("清凉峰 (1787.4m 临安皖浙界山)", 118.895, 30.089, "peak", "浙西北屋脊·清凉峰国家级自然保护区"),
    ("白云尖 (1611.3m 泰顺乌岩岭)", 119.695, 27.698, "peak", "浙南最高峰·温州市第一高峰"),
    ("龙王山 (1587.4m 安吉天目山主峰)", 119.410, 30.395, "mt", "黄浦江源头·湖州第一高峰"),
    ("大龙岗 (1500.3m 开化白际山)", 118.252, 29.235, "mt", "衢州最高峰·钱江源生态高地"),
    ("米筛浪 (1382.4m 括苍山主峰)", 121.125, 28.855, "mt", "台州第一高峰·风电场云海胜境"),
    ("大盘山 (1245.0m 磐安中药材宝库)", 120.520, 29.015, "mt", "金华最高峰·钱塘瓯江曹娥江源头"),
    ("东白山太白尖 (1194.6m 会稽山脉主峰)", 120.485, 29.545, "mt", "绍兴最高峰·高山草甸湿地"),
    ("青虎湾岗 (979.0m 四明山主峰)", 121.135, 29.742, "mt", "宁波第一高峰·浙东四明山腹地"),
    ("桃花岛对峙山 (544.4m 舟山最高峰)", 122.285, 29.835, "mt", "舟山群岛海岛第一高地")
]

for name, lon, lat, ptype, desc in peaks_data:
    px, py = to_alb(lon, lat)
    m = "*" if ptype == "peak" else "^"
    fc = "#c0392b" if ptype == "peak" else "#922b21"
    sl1.add(px, py, name, ptype, note=desc, priority=0 if ptype == "peak" else 1,
            marker=m, face=fc, size=7.2 if ptype == "peak" else 5.2, kind_label="地形控制性极点与名山大川")

waters_data = [
    ("钱塘江干流 (省内第一大河·全长588km)", 120.250, 30.220, "water", "富春江新安江汇入杭州湾出海"),
    ("瓯江干流 (省内第二大河·全长388km)", 120.550, 28.020, "water", "穿浙西南山区注入温州湾"),
    ("曹娥江 (浙东大河·全长197km)", 120.875, 30.015, "water", "曹娥江大闸控制杭州湾南岸水网"),
    ("千岛湖 (新安江水库·长三角特大战略水源)", 119.043, 29.608, "water", "573km²水面华东第一大人工湖"),
    ("太湖南岸苕溪 (东苕溪与西苕溪)", 120.080, 30.850, "water", "太湖重要来水通道与防洪屏障"),
    ("宁波三江口 (姚江奉化江汇为甬江)", 121.554, 29.873, "water", "港通天下书藏古今之源"),
    ("舟山群岛海域 (中国最大群岛·海域2.08万km²)", 122.350, 30.200, "water", "大国海疆与世界一流深水强港"),
    ("杭州湾 (世界著名强潮河口·钱塘潮源)", 121.200, 30.400, "water", "强涌潮与杭州湾跨海大桥雄姿")
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

ax.set_title("浙江省地势起伏与山海交融水文格局图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Geomorphology, Mountain Systems & Marine Hydrology of Zhejiang Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg1, "数据源：AWS Terrain 300m 高程 · 投影：Albers 等积圆锥 (中央经线 105°E) · 制作：《中国地理知识手册》",
    fontsize=6.5)

p1 = os.path.join(OUT_DIR, "fig11-00-1_浙江省地势起伏与山海交融水文格局图.png")
fig.savefig(p1, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {p1}")

# =============================================================================
# 图 11-00-2：浙江省行政区划与四大都市区空间格局图
# =============================================================================
print("Generating Fig 11-00-2 (Administrative & 4 Metropolitan Regions)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

# 11 市划分四大都市区赋色：
# 1. 杭州都市区：杭州、嘉兴、湖州、绍兴 (#d4efdf 淡绿蓝)
# 2. 宁波都市区：宁波、舟山 (#d6eaf8 淡海蓝)
# 3. 温州都市区：温州、台州 (#fdebd0 淡暖橙)
# 4. 金义都市区：金华、衢州、丽水 (#fcf3cf 淡金黄)
city_metro_map = {
    "330100": ("#d4efdf", "杭州都市区核心"),
    "330400": ("#e8f8f5", "杭州都市区·嘉兴"),
    "330500": ("#e8f8f5", "杭州都市区·湖州"),
    "330600": ("#d4efdf", "杭州都市区·绍兴"),
    "330200": ("#d6eaf8", "宁波都市区核心"),
    "330900": ("#ebf5fb", "宁波都市区·舟山"),
    "330300": ("#fdebd0", "温州都市区核心"),
    "331000": ("#fef5e7", "温州/宁波协同·台州"),
    "330700": ("#fcf3cf", "金义都市区核心"),
    "330800": ("#fef9e7", "金义都市区·衢州"),
    "331100": ("#fef9e7", "金义都市区·丽水")
}

for idx, row in zj_prov.iterrows():
    adcode = str(row.get("adcode", ""))
    color, mname = city_metro_map.get(adcode, ("#f2f4f4", "其他"))
    gpd.GeoSeries([row.geometry], crs=ALBERS).plot(ax=ax, facecolor=color, edgecolor="#566573", lw=0.9, zorder=3)

gpd.GeoSeries([zj_union], crs=ALBERS).boundary.plot(ax=ax, color="#1b4f72", lw=1.8, zorder=6)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl2 = mapkit.SymbolLabels(ax, fig)
sl2.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.50, 0.0, 1.0, 0.09),
             (0.88, 0.86, 1.0, 1.0)])

# 标注 11 个地级市中心与属性
from zhejiang_configs import ZHEJIANG_CITIES
for c in ZHEJIANG_CITIES:
    geom = zj_prov[zj_prov["adcode"] == int(c["adcode"])].geometry.iloc[0]
    rp = geom.representative_point()
    cx, cy = rp.x, rp.y
    note = f"GDP: {c['gdp_yi']}亿元 | 人口: {c['pop_wan']}万人 | 人均: {c['per_capita_gdp_yuan']//10000}万"
    sl2.add(cx, cy, c["name"], "capital", note=note, priority=0,
            marker="o", face="#c0392b" if c["adcode"] in ["330100", "330200"] else "#2980b9",
            size=7.0 if c["adcode"] in ["330100", "330200"] else 5.2,
            kind_label="设区市行政中心与综合能级")

# 标注山海协作与重点经济走廊
corridors = [
    ("杭甬“双城记”走廊 (唱响长三角一体化发展南翼)", 120.850, 30.080, "杭甬一体化数字与先进制造隆起带"),
    ("甬舟一体化海洋经济圈 (世界一流强港与自贸试验区)", 122.050, 29.950, "全球大宗商品与集装箱超级枢纽"),
    ("杭嘉湖南排工程与水乡智造链 (沪浙联动前哨)", 120.820, 30.680, "长三角生态绿色示范与智造集聚"),
    ("金衢盆地商贸与智造金走廊 (义新欧陆港走廊)", 119.550, 29.150, "内陆开放陆港与先进制造腹地"),
    ("温台沿海先进制造业带 (民营经济与新能源高地)", 121.250, 28.350, "传统优势民营产业转型与风光核储"),
    ("浙西南生态屏障与山海协作示范区 (绿水青山就是金山银山)", 119.350, 28.250, "丽水衢州生态价值实现与共同富裕")
]

for cname, clon, clat, cdesc in corridors:
    cx, cy = to_alb(clon, clat)
    sl2.add(cx, cy, cname, "corridor", note=cdesc, priority=1,
            marker="D", face="#8e44ad", size=5.5, kind_label="重点功能走廊与山海协作战略布局")

sym_type_h, sym_idx_h = sl2.flush()

add_scalebar(ax, sb_x0, sb_y0, length_km=60)
add_compass(ax, 0.94, 0.91)

metro_patches = [
    Patch(facecolor="#d4efdf", edgecolor="#566573", label="杭州都市区（杭嘉湖绍协同）"),
    Patch(facecolor="#d6eaf8", edgecolor="#566573", label="宁波都市区（甬舟台海洋联动）"),
    Patch(facecolor="#fdebd0", edgecolor="#566573", label="温州都市区（东南沿海极核）"),
    Patch(facecolor="#fcf3cf", edgecolor="#566573", label="金义都市区（内陆开放与金丽衢腹地）")
]

leg2 = mapkit.stacked_legends(ax, [
    dict(handles=metro_patches, title="四大都市区战略空间格局", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_type_h, title="要素类型与标注符号", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="行政中心与重点走廊编号对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("浙江省行政区划与“四大都市区”空间格局图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Administrative Structure & Four Metropolitan Areas of Zhejiang Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg2, "数据源：浙江省国土空间总体规划 (2021-2035) · 民政部标准地名代码 · 制作：《中国地理知识手册》",
    fontsize=6.5)

p2 = os.path.join(OUT_DIR, "fig11-00-2_浙江省行政区划与四大都市区空间格局图.png")
fig.savefig(p2, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {p2}")

# =============================================================================
# 图 11-00-3：浙江省综合立体交通与港口航运枢纽网络图
# =============================================================================
print("Generating Fig 11-00-3 (Transport & Ports Network)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

zj_prov.plot(ax=ax, facecolor="#f9f9f9", edgecolor="#bdc3c7", lw=0.6, zorder=2)
gpd.GeoSeries([zj_union], crs=ALBERS).boundary.plot(ax=ax, color="#2c3e50", lw=1.5, zorder=4)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

# 绘制主要高铁网络（示意主干连线）
hsi_lines = [
    # 沪杭-杭深线 (沿海通道)
    ([120.75, 120.15, 120.58, 121.55, 121.44, 120.67, 120.59],
     [30.75, 30.28, 29.99, 29.87, 28.67, 28.00, 27.58], "#e74c3c", 2.2, "沪杭/杭深沿海高铁大通道"),
    # 杭金衢-沪昆高铁线
    ([120.15, 120.25, 119.64, 118.86],
     [30.28, 29.71, 29.11, 28.96], "#c0392b", 2.2, "沪昆高铁大通道 (杭州-诸暨-金华-衢州)"),
    # 杭黄高铁
    ([120.15, 119.68, 119.04, 118.89],
     [30.28, 29.80, 29.60, 30.08], "#d35400", 1.8, "杭黄高铁 (西湖-富春江-千岛湖-黄山)"),
    # 杭台高铁
    ([120.15, 120.58, 120.83, 121.12, 121.36],
     [30.28, 29.99, 29.50, 28.85, 28.37], "#8e44ad", 1.8, "杭台高铁 (首条民资控股高铁)"),
    # 金丽温高铁
    ([119.64, 120.08, 119.91, 120.67],
     [29.11, 28.69, 28.45, 28.00], "#2980b9", 1.8, "金丽温客运专线 (金华-武义-缙云-丽水-青田-温州)"),
    # 甬金铁路与甬舟铁路(在建跨海)
    ([120.07, 119.64, 120.31, 121.55, 122.21],
     [29.30, 29.11, 29.14, 29.87, 29.98], "#16a085", 1.6, "甬金-甬舟港口海铁联运通道")
]

for lons, lats, col, lw, desc in hsi_lines:
    albs = [to_alb(x, y) for x, y in zip(lons, lats)]
    xs = [p[0] for p in albs]
    ys = [p[1] for p in albs]
    ax.plot(xs, ys, color=col, lw=lw, zorder=5, alpha=0.85)

# 绘制超级跨海大桥
bridges = [
    ([121.15, 121.22], [30.55, 30.35], "#2e4053", 3.0, "杭州湾跨海大桥 (跨越杭州湾北岸至慈溪)"),
    ([121.85, 122.21], [30.01, 29.98], "#2e4053", 3.0, "舟山跨海大桥 (五桥连岛工程)")
]
for lons, lats, col, lw, desc in bridges:
    albs = [to_alb(x, y) for x, y in zip(lons, lats)]
    ax.plot([p[0] for p in albs], [p[1] for p in albs], color=col, lw=lw, zorder=6)

sl3 = mapkit.SymbolLabels(ax, fig)
sl3.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.50, 0.0, 1.0, 0.09),
             (0.88, 0.86, 1.0, 1.0)])

hubs = [
    ("宁波舟山港 (全球首个13亿吨大港·集装箱超3500万标箱)", 121.848, 29.939, "port", "世界第一大综合枢纽强港"),
    ("杭州萧山国际机场 (年吞吐量超4000万人次/国际枢纽)", 120.435, 30.229, "airport", "长三角世界级机场群核心支柱"),
    ("义乌国际陆港与西站 (义新欧始发港/海铁联运第一站)", 120.035, 29.285, "port", "一带一路内陆最大国际陆港"),
    ("宁波栎社国际机场 (区域核心航空物流枢纽)", 121.462, 29.826, "airport", "浙东国际航空货运前沿"),
    ("温州龙湾国际机场 (浙南闽北赣东区域航空枢纽)", 120.852, 27.912, "airport", "海峡西岸与浙南国际门户"),
    ("杭州东站 (全国特大型综合客运铁路枢纽)", 120.213, 30.291, "station", "亚洲最大动车高铁枢纽之一"),
    ("嘉兴港与独山港区 (浙北接沪河海联运第一外贸港)", 121.185, 30.655, "port", "杭州湾北岸海河联运枢纽"),
    ("温州港与状元岙深水港区 (浙南沿海主枢纽港)", 121.050, 27.920, "port", "辐射浙南闽北深水外贸良港"),
    ("台州湾大麦屿港与头门港区 (直航台湾海上客货运通道)", 121.280, 28.120, "port", "对台交流与先进制造出海口"),
    ("金华铁路枢纽南站 (全国44个铁路枢纽之一)", 119.645, 29.085, "station", "浙中内陆综合物资集散中心")
]

for hname, hlon, hlat, htype, hdesc in hubs:
    hx, hy = to_alb(hlon, hlat)
    m = "s" if htype == "port" else ("^" if htype == "airport" else "o")
    fc = "#1b4f72" if htype == "port" else ("#e67e22" if htype == "airport" else "#27ae60")
    sl3.add(hx, hy, hname, htype, note=hdesc, priority=0 if htype == "port" else 1,
            marker=m, face=fc, size=6.5, kind_label="沿海强港、国际航空与铁路大枢纽")

sym_type_h, sym_idx_h = sl3.flush()

add_scalebar(ax, sb_x0, sb_y0, length_km=60)
add_compass(ax, 0.94, 0.91)

hsi_lines_legend = [
    Line2D([0], [0], color="#e74c3c", lw=2.2, label="沿海高铁大通道（沪杭/杭深客专）"),
    Line2D([0], [0], color="#c0392b", lw=2.2, label="沪昆高铁通道（杭金衢主干线）"),
    Line2D([0], [0], color="#8e44ad", lw=1.8, label="杭台高铁 / 杭温高铁（民资与区域连接）"),
    Line2D([0], [0], color="#2980b9", lw=1.8, label="金丽温客运专线（山海联动快速线）"),
    Line2D([0], [0], color="#2e4053", lw=3.0, label="杭州湾跨海大桥 / 舟山跨海大桥")
]

leg3 = mapkit.stacked_legends(ax, [
    dict(handles=hsi_lines_legend, title="骨干高速铁路与跨海工程", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_type_h, title="交通基础设施类型", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="枢纽设施名称对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("浙江省综合立体交通与港口航运枢纽网络图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Integrated Transport Network, High-Speed Rails & World-Class Ports of Zhejiang",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg3, "数据源：浙江省综合交通运输发展“十四五”规划 · 宁波舟山港年鉴 · 制作：《中国地理知识手册》",
    fontsize=6.5)

p3 = os.path.join(OUT_DIR, "fig11-00-3_浙江省综合立体交通与港口航运枢纽网络图.png")
fig.savefig(p3, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {p3}")

# =============================================================================
# 图 11-00-4：浙江省现代产业集群与数字经济高地空间格局图
# =============================================================================
print("Generating Fig 11-00-4 (Industrial Clusters & Digital Economy)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

zj_prov.plot(ax=ax, facecolor="#fcfcfc", edgecolor="#bdc3c7", lw=0.6, zorder=2)
gpd.GeoSeries([zj_union], crs=ALBERS).boundary.plot(ax=ax, color="#1b4f72", lw=1.6, zorder=4)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl4 = mapkit.SymbolLabels(ax, fig)
sl4.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.50, 0.0, 1.0, 0.09),
             (0.88, 0.86, 1.0, 1.0)])

industries = [
    ("杭州“中国视谷”与滨江高新区 (视觉智能/安防/海康威视/新华三)", 120.218, 30.178, "digital", "全球安防与智能物联极核"),
    ("杭州未来科技城与阿里云 (阿里巴巴/达摩院/云计算高地)", 119.995, 30.278, "digital", "全国数字经济第一城创新核"),
    ("宁波绿色石化与高端新材料基地 (镇海炼化/万华化学/大榭)", 121.710, 29.980, "manu", "国家级先进石化制造业集群"),
    ("宁波单项冠军制造业群 (模具/注塑机/汽车零部件海天极核)", 121.560, 29.880, "manu", "全国制造业单项冠军第一城"),
    ("舟山鱼山岛绿色石化基地 (全球最大单体石化/浙石化4000万吨)", 121.985, 30.295, "energy", "大国重器超级炼化一体化"),
    ("温州乐清电气与智能仪器仪表集群 (正泰/德力西/中国电器之都)", 120.985, 28.125, "manu", "国家级先进制造业电气集群"),
    ("义乌国际小商品商贸集群 (全球最大小商品集散/万商云集)", 120.075, 29.305, "trade", "全球商贸晴雨表与电商之都"),
    ("嘉兴秀洲光伏科技城 (隆基/阿特斯/全球光伏新材料高地)", 120.695, 30.765, "energy", "绿色清洁能源与光伏高地"),
    ("湖州长兴动力电池与绿色智造 (天能/超威锂电储能产业集群)", 119.910, 31.025, "energy", "全国绿色动力电池之都"),
    ("绍兴柯桥现代纺织集群 (中国轻纺城/全球最大纺织品交易链)", 120.495, 30.075, "manu", "千亿级国际现代纺织产业高地"),
    ("绍兴越城集成电路小镇 (中芯集成/长电科技半导体集聚区)", 120.620, 30.050, "digital", "全省集成电路万亩千亿新平台"),
    ("台州吉利汽车与临海新能源汽车基地 (民营车企摇篮/沃尔沃)", 121.150, 28.860, "manu", "中国民营汽车工业发源地"),
    ("台州椒江/临海现代原料药与医化基地 (华海/海正/绿色药都)", 121.385, 28.735, "biomed", "全国化学原料药出口第一高地"),
    ("衢州巨化氟硅新材料高新技术园区 (全国最大氟化工先进基地)", 118.892, 28.948, "manu", "大国特种氟硅与电子化学品"),
    ("丽水特色半导体与生态合成革制造 (生态工业跨越式高质量发展)", 119.920, 28.460, "manu", "浙西南生态工业转型升级标杆")
]

for iname, ilon, ilat, itype, idesc in industries:
    ix, iy = to_alb(ilon, ilat)
    m = "*" if itype == "digital" else ("s" if itype == "manu" else ("^" if itype == "energy" else "o"))
    fc = "#8e44ad" if itype == "digital" else ("#c0392b" if itype == "manu" else ("#27ae60" if itype == "energy" else "#d35400"))
    sl4.add(ix, iy, iname, itype, note=idesc, priority=0 if itype in ["digital", "energy"] else 1,
            marker=m, face=fc, size=6.5, kind_label="先进制造业与数字经济高能级集群")

sym_type_h, sym_idx_h = sl4.flush()

add_scalebar(ax, sb_x0, sb_y0, length_km=60)
add_compass(ax, 0.94, 0.91)

leg4 = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="产业集群核心门类", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="标志性集群与龙头基地编号对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("浙江省现代产业集群与数字经济高地空间格局图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Advanced Manufacturing Clusters & Digital Innovation Hubs of Zhejiang Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg4, "数据源：浙江省经济和信息化厅 · 浙江省统计局 · 制作：《中国地理知识手册》",
    fontsize=6.5)

p4 = os.path.join(OUT_DIR, "fig11-00-4_浙江省现代产业集群与数字经济高地空间格局图.png")
fig.savefig(p4, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {p4}")

# =============================================================================
# 图 11-00-5：浙江省 1986—2024 年夜间灯光演变与山海协作发展图
# =============================================================================
print("Generating Fig 11-00-5 (Nightlight Evolution 1986-2024)...")
fig = plt.figure(figsize=(10.2, 9.2), dpi=DPI)
fig.patch.set_facecolor("white")

gs = fig.add_gridspec(2, 2, height_ratios=[1.2, 1.0], hspace=0.28, wspace=0.22,
                       left=0.07, right=0.95, top=0.92, bottom=0.08)

ax_map = fig.add_subplot(gs[0, :])
ax_curve = fig.add_subplot(gs[1, 0])
ax_city = fig.add_subplot(gs[1, 1])

# 上半部分：全省夜光空间扩展示意图
zj_prov.plot(ax=ax_map, facecolor="#f5f7f8", edgecolor="#bdc3c7", lw=0.6, zorder=2)
gpd.GeoSeries([zj_union], crs=ALBERS).boundary.plot(ax=ax_map, color="#2c3e50", lw=1.4, zorder=4)
ax_map.set_xlim(ax_xlim)
ax_map.set_ylim(ax_ylim)
ax_map.axis("off")

# 标注夜光三大隆起带与山海协作
nl_belts = [
    ("环杭州湾高光连绵带 (杭州-嘉兴-绍兴-宁波超级都市廊道)", 120.950, 30.250, "#e74c3c", 85),
    ("温台沿海民营经济光带 (台州湾-温州湾-乐清湾光芒汇聚)", 121.150, 28.200, "#d35400", 72),
    ("金衢盆地义乌商贸走廊 (金华-义乌-永康辐射走廊)", 120.000, 29.200, "#f39c12", 65),
    ("舟山绿色石化与海岛光点 (鱼山岛深水不夜港)", 122.150, 30.250, "#8e44ad", 58),
    ("浙西南生态绿谷与点状星火 (丽水衢州绿色崛起)", 119.350, 28.300, "#27ae60", 45)
]

for bname, blon, blat, bcol, bsize in nl_belts:
    bx, by = to_alb(blon, blat)
    circle = plt.Circle((bx, by), span_x * 0.06, color=bcol, alpha=0.22, zorder=3)
    ax_map.add_patch(circle)
    ax_map.scatter(bx, by, s=bsize * 1.5, color=bcol, edgecolors="#ffffff", lw=1.2, zorder=5)
    ax_map.annotate(bname, xy=(bx, by), xytext=(bx, by + span_y * 0.035),
                    ha="center", va="bottom", fontsize=7.8, fontweight="bold", color="#1c2833",
                    bbox=dict(boxstyle="round,pad=0.25", fc="#ffffff", ec=bcol, alpha=0.92, lw=0.8),
                    zorder=6)

ax_map.set_title("浙江省夜间灯光宏观空间集聚格局与演进带", fontsize=11.0, fontweight="bold", pad=6, color=C_TEXT)

# 下左：1986—2024 年全省灯光总量与人均 GDP 协同增长曲线
nl_df = pd.read_csv(os.path.join(DATA_DIR, "zhejiang_nightlight_clean.csv"))
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

# 拟合近年增长趋势
ax_curve.set_title("浙江省夜光辐射总量演化轨迹 (1986—2024)", fontsize=9.2, fontweight="bold", color=C_TEXT)

# 下右：11 个设区市夜光总量对比横向柱状图（以最近基准年为例）
latest_year = yearly_nl.index.max()
city_latest = nl_df[nl_df["year"] == latest_year].groupby("city_name")["sum"].sum().sort_values()

# 清洗城市名称中的乱码或提取标准名
clean_city_names = []
for c in city_latest.index:
    c_str = str(c)
    # 匹配标准市名
    matched = None
    for item in ZHEJIANG_CITIES:
        if item["name"][:2] in c_str or c_str[:2] in item["name"]:
            matched = item["name"]
            break
    clean_city_names.append(matched if matched else c_str)

bars = ax_city.barh(clean_city_names, city_latest.values / 1000.0, color="#2980b9", alpha=0.85, edgecolor="#1a5276", height=0.65)
ax_city.set_xlabel(f"夜光辐射总量 ({int(latest_year)}年, 千单位)", fontsize=8.5)
ax_city.tick_params(axis='both', labelsize=7.5)
ax_city.grid(True, ls=":", alpha=0.5, axis="x")
ax_city.set_title("11 个设区市夜间灯光辐射总量分布", fontsize=9.2, fontweight="bold", color=C_TEXT)

# 在柱状图上标注数值
for bar in bars:
    w = bar.get_width()
    ax_city.text(w + 1.2, bar.get_y() + bar.get_height()/2, f"{w:.1f}", va='center', ha='left', fontsize=6.8, color="#2c3e50")

fig.suptitle("浙江省 1986—2024 年夜间灯光演变与山海协作发展格局", fontsize=12.5, fontweight="bold", y=0.98, color=C_TEXT)
p5 = os.path.join(OUT_DIR, "fig11-00-5_浙江省1986—2024年夜间灯光演变与山海协作发展图.png")
fig.savefig(p5, dpi=DPI)
plt.close(fig)
print(f"  ✓ Saved {p5}")

print("\n=== ALL 5 OVERVIEW FIGURES FOR ZHEJIANG COMPLETED SUCCESSFULLY! ===")
