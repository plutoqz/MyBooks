# -*- coding: utf-8 -*-
"""山东省地理统揽专题地图生成引擎（08-00）
包含 5 幅全省权威出版级地图与分析图表（精细调优排版、微缩字号、严格杜绝压盖）：
1. fig08-00-1_山东省地势阶梯与山脉水系格局图.png
2. fig08-00-2_山东省行政区划与“一群两心三圈”空间格局图.png
3. fig08-00-3_山东省综合立体交通与港口航运枢纽网络图.png
4. fig08-00-4_山东省现代海洋与十强产业经济集聚格局图.png
5. fig08-00-5_山东省1986—2024年夜间灯光演变与半岛城市群发展图.png
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
    gy, gx = np.gradient(dem, res)
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

print("Loading Shandong provincial boundaries and DEM...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

sd_prov = gpd.read_file(os.path.join(DATAV_DIR, "370000_full.json")).to_crs(ALBERS)
sd_prov["geometry"] = sd_prov.geometry.buffer(0)
sd_union = sd_prov.union_all()

b = sd_prov.total_bounds
span_x = b[2] - b[0]
span_y = b[3] - b[1]
pad_x = span_x * 0.04
pad_y = span_y * 0.04
ax_xlim = (b[0] - pad_x, b[2] + pad_x)
ax_ylim = (b[1] - pad_y, b[3] + pad_y)

# 加载 DEM
dem_file = os.path.join(DATA_DIR, "dem", "province", "370000_z9.npz")
dem_data = np.load(dem_file)
step = 2
dem_raw = dem_data['dem'][::step, ::step]
dem_res = float(dem_data['res']) * step
dem_minx = float(dem_data['minx'])
dem_maxy = float(dem_data['maxy'])
print(f"Downsampled DEM shape: {dem_raw.shape}, res: {dem_res}m")

extent = (dem_minx, dem_minx + dem_raw.shape[1] * dem_res,
          dem_maxy - dem_raw.shape[0] * dem_res, dem_maxy)

hs = calc_hillshade(dem_raw, dem_res)
norm = Normalize(vmin=0.0, vmax=1533.0)

terrain_colors = [
    (0.00, "#196f3d"),   # 0m 沿海滩涂与河口湿地
    (0.03, "#27ae60"),   # 40m 鲁西北平原与鲁西南洼地
    (0.10, "#7dcea0"),   # 150m 胶莱平原与丘陵缓坡
    (0.22, "#f9e79f"),   # 350m 胶东丘陵与山前台地
    (0.42, "#eb984e"),   # 650m 鲁中低山与沂蒙崮群
    (0.65, "#dc7633"),   # 1000m 鲁山/崂山/沂山主脊
    (0.85, "#ba4a00"),   # 1300m 泰山中高山区
    (1.00, "#ffffff")    # 1532.7m 泰山极顶玉皇顶
]
terrain_cmap = LinearSegmentedColormap.from_list("sd_dem", terrain_colors)
dem_rgb = terrain_cmap(norm(dem_raw))[:, :, :3]
shaded_rgb = dem_rgb * (0.42 + 0.58 * hs[:, :, np.newaxis])

FIGSIZE = (10.5, 6.8)

# =============================================================================
# 图 08-00-1：山东省地势阶梯与山脉水系格局图
# =============================================================================
print("Generating Fig 08-00-1 (Topography)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

im = ax.imshow(shaded_rgb, extent=extent, origin="upper", zorder=2)
patch = get_mpl_clip_patch(sd_union)
ax.add_patch(patch)
im.set_clip_path(patch)

sd_prov.boundary.plot(ax=ax, color="#2c3e50", lw=0.6, ls="--", zorder=5)
gpd.GeoSeries([sd_union], crs=ALBERS).boundary.plot(ax=ax, color="#1a5276", lw=1.5, zorder=6)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl1 = mapkit.SymbolLabels(ax, fig)
sl1.reserve([(0.0, 0.0, 0.38, 0.34),
             (0.50, 0.0, 1.0, 0.09),
             (0.90, 0.85, 1.0, 1.0)])

peaks_data = [
    ("泰山玉皇顶 (1532.7m 五岳独尊·全省最高峰)", 117.105, 36.255, "peak", "世界自然文化双遗产·封禅名山"),
    ("蒙山龟蒙顶 (1156m 沂蒙山主峰)", 117.780, 35.480, "mt", "山东第二高峰·世界地质公园"),
    ("崂山巨峰 (1132.7m 大陆海岸第一峰)", 120.610, 36.170, "mt", "海上名山第一·道教全真圣地"),
    ("鲁山 (1108.3m 鲁中最高主峰)", 118.130, 36.310, "mt", "淄河发源地·鲁中生态氧吧"),
    ("沂山玉皇顶 (1032m 东镇名山)", 118.630, 36.210, "mt", "大海向西第一座高山·国家森林公园"),
    ("徂徕山 (1027m 泰安南部名山)", 117.330, 36.080, "mt", "抗日根据地·山岳生态屏障"),
    ("昆嵛山泰礴顶 (922.8m 胶东屋脊)", 121.740, 37.280, "mt", "全真道发祥地·胶东最高峰"),
    ("梯子山 (976m 济南最高峰)", 117.130, 36.380, "mt", "南部山区重要水源涵养区"),
    ("抱犊崮 (584m 鲁南天下第一崮)", 117.650, 35.030, "mt", "岱南奇观·典型崮貌地质遗迹"),
    ("屋楼崮 (706m 日照最高峰)", 118.780, 35.650, "mt", "鲁东南沿海山地屏障")
]

for name, lon, lat, ptype, desc in peaks_data:
    px, py = to_alb(lon, lat)
    m = "*" if ptype == "peak" else "^"
    fc = "#c0392b" if ptype == "peak" else "#922b21"
    sl1.add(px, py, name, ptype, note=desc, priority=0 if ptype == "peak" else 1,
            marker=m, face=fc, size=7.0 if ptype == "peak" else 5.2, kind_label="地形控制性极点与名山大川")

waters_data = [
    ("黄河干流 (穿鲁入海·下游地上悬河)", 116.850, 36.700, "water", "穿鲁入海黄河地上悬河"),
    ("黄河入海口 (黄蓝交汇世界奇观)", 119.260, 37.780, "water", "东营河口湿地"),
    ("小清河 (贯通省会通向莱州湾全线复航)", 117.900, 37.050, "water", "海河水系水运通道"),
    ("南四湖/微山湖群 (1266km² 全省最大淡水湖)", 116.850, 35.000, "water", "淮河水系最大湖泊"),
    ("东平湖 (水泊梁山仅存水域·南水北调调蓄)", 116.380, 35.980, "water", "水泊梁山遗存"),
    ("京杭大运河 (山东鲁运河与台儿庄段)", 116.550, 35.250, "water", "古代黄金内河航道"),
    ("沂河水系 (八水绕城贯通沂蒙)", 118.400, 35.150, "water", "鲁东南骨干水系"),
    ("峡山水库 (山东第一大水库·库容14亿m³)", 119.380, 36.480, "water", "潍坊水利枢纽"),
    ("大沽河 (胶东半岛母亲河贯入胶州湾)", 120.150, 36.350, "water", "胶东核心水系")
]

for name, lon, lat, wtype, desc in waters_data:
    px, py = to_alb(lon, lat)
    sl1.add(px, py, name, wtype, note=desc, priority=2,
            marker="s", face="#1b4f72", size=4.8, kind_label="骨干江河水系与著名湖泊水库")

sym_type_h, sym_idx_h = sl1.flush()

sb_x0 = ax_xlim[0] + span_x * 0.52
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=100)
add_compass(ax, 0.94, 0.91)

leg1 = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="地形与水系要素分类", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="图上要素编号对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("山东省地势阶梯与山脉水系格局图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Geomorphology, Mountain Chains & River Basins of Shandong Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg1, "数据源：AWS Terrain 300m 高程 · 投影：Albers 等积圆锥 (中央经线 105°E) · 制作：《中国地理知识手册》",
    fontsize=6.5)

f1_path = os.path.join(OUT_DIR, "fig08-00-1_山东省地势阶梯与山脉水系格局图.png")
fig.savefig(f1_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"✓ Saved Fig 08-00-1: {f1_path}")

# =============================================================================
# 图 08-00-2：山东省行政区划与“一群两心三圈”空间格局图
# =============================================================================
print("Generating Fig 08-00-2 (Administrative & Urban Pattern)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

circle_colors = {
    "370100": "#e8f4f8", "370300": "#e8f4f8", "370900": "#e8f4f8",
    "371400": "#e8f4f8", "371500": "#e8f4f8", "371600": "#e8f4f8", "370500": "#e8f4f8",
    "370200": "#eafaf1", "370600": "#eafaf1", "370700": "#eafaf1",
    "371000": "#eafaf1", "371100": "#eafaf1",
    "371300": "#fef9e7", "370800": "#fef9e7", "371700": "#fef9e7", "370400": "#fef9e7"
}

for i, (_, row) in enumerate(sd_prov.iterrows()):
    ad = str(row.get("adcode", ""))
    fill_col = circle_colors.get(ad, "#f4ecf7")
    gpd.GeoSeries([row.geometry], crs=ALBERS).plot(ax=ax, facecolor=fill_col, edgecolor="#7f8c8d", lw=0.6, zorder=3)

gpd.GeoSeries([sd_union], crs=ALBERS).boundary.plot(ax=ax, color="#1a5276", lw=1.6, zorder=6)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl2 = mapkit.SymbolLabels(ax, fig)
sl2.reserve([(0.0, 0.0, 0.38, 0.34),
             (0.50, 0.0, 1.0, 0.09),
             (0.90, 0.85, 1.0, 1.0)])

admin_hubs = [
    ("济南市 (省会·特大城市·副省级)", 117.120, 36.650, "core", "全省政治经济科技科教中心·1.3万亿极核"),
    ("青岛市 (计划单列·特大城市·副省级)", 120.380, 36.065, "core", "现代海洋名城·北方第三城·1.63万亿领头羊"),
    ("烟台市 (北方万亿新城·仙境海岸)", 121.445, 37.465, "sub", "胶东骨干支柱·裕龙岛石化与高端海工装备"),
    ("潍坊市 (动力之都·制造业冠军之城)", 119.165, 36.705, "sub", "潍柴歌尔龙头高地·全国农业现代化策源地"),
    ("临沂市 (中国物流之都·千万人口大市)", 118.355, 35.105, "sub", "全省面积最大人口最多·临沂商城商贸枢纽"),
    ("济宁市 (孔孟圣地·北方内河航运中心)", 116.585, 35.350, "sub", "曲阜儒学文化·梁山港亿吨级运河枢纽"),
    ("淄博市 (齐国故都·老工业基地转型标杆)", 118.055, 36.815, "node", "齐鲁石化·新材料名都·全域文旅典范"),
    ("菏泽市 (中国牡丹之都·鲁西崛起排头兵)", 115.465, 35.250, "node", "黄河入鲁第一站·现代医药港·曹县电商集群"),
    ("德州市 (九达天衢·京津冀协同示范区)", 116.360, 37.435, "node", "双高铁十字枢纽·体育器材与功能糖名城"),
    ("东营市 (黄河入海口门户·胜利油田大本营)", 118.675, 37.435, "node", "全国人均GDP前列·生态湿地与全球轮胎之都"),
    ("泰安市 (五岳独尊·国泰民安精神家园)", 117.085, 36.195, "node", "首个世界双遗产泰山·全球最大压缩空气储能"),
    ("威海市 (精致城市典范·中韩合作前沿)", 122.115, 37.505, "node", "千里山海自驾公路·全球激光打印机基地"),
    ("滨州市 (世界级高端铝业基地·孙子故里)", 117.970, 37.385, "node", "魏桥创业世界500强·黄河穿城入海前沿"),
    ("聊城市 (江北水城·两河明珠交汇名城)", 115.985, 36.455, "node", "东昌湖城湖相依·信发万亿铝业·东阿阿胶"),
    ("日照市 (新亚欧大陆桥桥头堡·亿吨深水大港)", 119.525, 35.415, "node", "联合国人居奖·山钢千万吨沿海绿色精品钢"),
    ("枣庄市 (中国北方锂电之都·台儿庄大战名城)", 117.320, 34.805, "node", "资源枯竭型转型典范·运河古城文化旅游")
]

for name, lon, lat, ctype, desc in admin_hubs:
    px, py = to_alb(lon, lat)
    m = "*" if ctype == "core" else ("o" if ctype == "sub" else "s")
    fc = "#c0392b" if ctype == "core" else ("#2980b9" if ctype == "sub" else "#d35400")
    sl2.add(px, py, name, ctype, note=desc, priority=0 if ctype == "core" else 1,
            marker=m, face=fc, size=7.5 if ctype == "core" else 5.2, kind_label="地级行政中心与能级层级")

sym_type_h2, sym_idx_h2 = sl2.flush()

sb_x0 = ax_xlim[0] + span_x * 0.52
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=100)
add_compass(ax, 0.94, 0.91)

leg2 = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h2, title="行政中心与城市能级", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h2, title="全省16地级市定位简述", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("山东省行政区划与“一群两心三圈”空间格局图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Administrative Divisions & 'One Urban Agglomeration, Two Cores, Three Circles' of Shandong",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg2, "数据源：民政部标准地名代码 · 山东省国土空间总体规划 (2021-2035) · 制作：《中国地理知识手册》",
    fontsize=6.5)

f2_path = os.path.join(OUT_DIR, "fig08-00-2_山东省行政区划与“一群两心三圈”空间格局图.png")
fig.savefig(f2_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"✓ Saved Fig 08-00-2: {f2_path}")

# =============================================================================
# 图 08-00-3：山东省综合立体交通与港口航运枢纽网络图
# =============================================================================
print("Generating Fig 08-00-3 (Transport & Ports)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

gpd.GeoSeries([sd_union], crs=ALBERS).plot(ax=ax, facecolor="#ffffff", edgecolor="#1a5276", lw=1.6, zorder=2)
sd_prov.boundary.plot(ax=ax, color="#bdc3c7", lw=0.6, ls=":", zorder=3)

# 绘制高铁走廊
rail_lines = [
    # 京沪高铁
    [(116.48, 37.44), (116.89, 36.67), (117.04, 36.17), (117.07, 35.55), (117.24, 35.10), (117.31, 34.79)],
    # 济青高铁
    [(116.89, 36.67), (117.15, 36.72), (118.04, 36.88), (119.17, 36.80), (120.37, 36.17)],
    # 日兰高铁
    [(115.54, 35.25), (116.58, 35.35), (117.07, 35.55), (118.34, 35.18), (119.41, 35.38)],
    # 青荣城际
    [(120.37, 36.17), (121.40, 37.44), (122.11, 37.43), (122.48, 37.16)],
    # 潍烟高铁
    [(119.17, 36.80), (120.50, 37.65), (120.98, 37.66), (121.40, 37.44)],
    # 济郑高铁
    [(116.89, 36.67), (115.91, 36.46), (115.40, 36.10)]
]

for r_pts in rail_lines:
    xs, ys = mapkit.smooth_line([to_alb(p[0], p[1]) for p in r_pts])
    ax.plot(xs, ys, color="#c0392b", lw=2.2, zorder=8, alpha=0.9)

# 绘制高速公路主骨架
hwy_lines = [
    # 京沪高速 G2
    [(116.90, 37.00), (117.10, 36.65), (117.65, 36.20), (118.30, 35.15), (118.36, 34.60)],
    # 青银高速 G20
    [(115.60, 37.10), (116.40, 37.00), (117.10, 36.75), (118.10, 36.85), (119.15, 36.78), (120.35, 36.15)],
    # 沈海高速 G15
    [(121.25, 37.55), (120.45, 36.35), (119.95, 35.85), (119.40, 35.20)],
    # 京台高速 G3
    [(116.35, 37.45), (116.90, 36.65), (117.05, 36.15), (117.25, 34.80)]
]

for h_pts in hwy_lines:
    xs, ys = mapkit.smooth_line([to_alb(p[0], p[1]) for p in h_pts])
    ax.plot(xs, ys, color="#2980b9", lw=1.5, ls="--", zorder=7, alpha=0.85)

# 绘制京杭运河水运线
canal_pts = [(116.08, 35.75), (116.58, 35.35), (116.85, 35.00), (117.72, 34.53)]
cxs, cys = zip(*[to_alb(p[0], p[1]) for p in canal_pts])
ax.plot(cxs, cys, color="#1a5276", lw=3.0, zorder=6, alpha=0.9)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl3 = mapkit.SymbolLabels(ax, fig)
sl3.reserve([(0.0, 0.0, 0.38, 0.34),
             (0.50, 0.0, 1.0, 0.09),
             (0.90, 0.85, 1.0, 1.0)])

hubs_data = [
    ("济南西/济南东枢纽 (米字型高铁总核)", 117.020, 36.690, "rail", "京沪济青济郑石济济莱枢纽"),
    ("青岛北/红岛枢纽 (胶东半岛枢纽门户)", 120.370, 36.180, "rail", "胶济济青青盐青荣大枢纽"),
    ("德州东站 (京沪与石济双十字高铁枢纽)", 116.480, 37.440, "rail", "南北客运与太青客运交汇特等站"),
    ("曲阜东站 (京沪与日兰双十字高铁枢纽)", 117.070, 35.550, "rail", "鲁南与京沪交汇综合大站"),
    ("聊城西站 (济郑与京雄商双十字枢纽)", 115.910, 36.460, "rail", "鲁西高铁十字客运门户"),
    ("临沂北站 (日兰与京沪二通道交汇枢纽)", 118.340, 35.185, "rail", "鲁南中心城市特等客运站"),
    ("青岛港前湾/董家口 (世界级综合海港)", 120.150, 35.850, "port", "东北亚国际航运中心·40万吨级散货码头"),
    ("日照港石臼/岚山 (全球铁矿石与能源大港)", 119.560, 35.370, "port", "年吞吐量超5亿吨·瓦日铁路直达"),
    ("烟台港芝罘湾/西港 (中非铝土矿与滚装大港)", 121.250, 37.600, "port", "环渤海客滚大通道·商品车进出口"),
    ("梁山港 (京杭运河与瓦日铁路铁水联运枢纽)", 116.080, 35.750, "port", "西煤东运北方内河第一大港"),
    ("青岛胶东国际机场 (4F级综合门户航空港)", 120.085, 36.370, "airport", "面向日韩东北亚核心空中门户"),
    ("济南遥墙国际机场 (4E级区域骨干空港)", 121.215, 36.855, "airport", "二期改扩建·全省空中客运门户"),
    ("烟台蓬莱国际机场 (4E级胶东骨干空港)", 120.980, 37.660, "airport", "半岛北部重要客货航空口岸")
]

for name, lon, lat, htype, desc in hubs_data:
    px, py = to_alb(lon, lat)
    m = "s" if htype == "rail" else ("p" if htype == "port" else "D")
    fc = "#c0392b" if htype == "rail" else ("#1a5276" if htype == "port" else "#27ae60")
    sl3.add(px, py, name, htype, note=desc, priority=0 if htype in ("rail", "port") else 1,
            marker=m, face=fc, size=6.5 if htype in ("rail", "port") else 5.2, kind_label="交通网络骨干枢纽")

sym_type_h3, sym_idx_h3 = sl3.flush()

sb_x0 = ax_xlim[0] + span_x * 0.52
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=100)
add_compass(ax, 0.94, 0.91)

leg3 = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h3, title="枢纽类型与网络骨架", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h3, title="骨干交通枢纽名录", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("山东省综合立体交通与港口航运枢纽网络图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Integrated Transport Network & Deep-water Ports System of Shandong Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg3, "数据源：中国国家铁路集团 · 山东省综合立体交通网规划纲要 · 制作：《中国地理知识手册》",
    fontsize=6.5)

f3_path = os.path.join(OUT_DIR, "fig08-00-3_山东省综合立体交通与港口航运枢纽网络图.png")
fig.savefig(f3_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"✓ Saved Fig 08-00-3: {f3_path}")

# =============================================================================
# 图 08-00-4：山东省现代海洋与十强产业经济集聚格局图
# =============================================================================
print("Generating Fig 08-00-4 (Economy & Marine)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

gpd.GeoSeries([sd_union], crs=ALBERS).plot(ax=ax, facecolor="#ffffff", edgecolor="#1a5276", lw=1.6, zorder=2)
sd_prov.boundary.plot(ax=ax, color="#cbd5e0", lw=0.6, ls="--", zorder=3)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl4 = mapkit.SymbolLabels(ax, fig)
sl4.reserve([(0.0, 0.0, 0.38, 0.34),
             (0.50, 0.0, 1.0, 0.09),
             (0.90, 0.85, 1.0, 1.0)])

industries_data = [
    ("中车青岛四方高铁动车研发制造基地", 120.360, 36.270, "mfg", "中国高速动车组摇篮·复兴号主力研发基地"),
    ("海尔集团工业互联网生态总部 (卡奥斯)", 120.420, 36.120, "it", "国家级跨行业双跨平台榜首·智慧住居标杆"),
    ("青岛国家深海基地与海洋试点实验室", 120.680, 36.360, "marine", "蛟龙号母港·我国海洋综合科研力量最密集地"),
    ("万华化学全球总部与聚氨酯MDI研发基地", 121.200, 37.610, "chem", "全球聚氨酯MDI领航者·自主化工技术典范"),
    ("裕龙岛炼化一体化4000万吨级石化航母", 120.320, 37.730, "chem", "山东新旧动能转换头号标志工程"),
    ("中集来福士蓝鲸1号超深水半潜式平台", 121.390, 37.570, "marine", "世界最深钻井深度海工大国重器制造基地"),
    ("潍柴动力本体高热效率柴油机制造高地", 119.140, 36.720, "mfg", "全球首款热效率53.09%柴油机·中国动力城"),
    ("歌尔声学微电子与元宇宙XR智能硬件", 119.200, 36.720, "it", "全球VR高端头显主要制造基地·微电声龙头"),
    ("寿光全国蔬菜种业硅谷与现代农业科技", 118.760, 36.900, "agri", "全国蔬菜集散定价中心·寿光模式策源地"),
    ("中国重汽集团商用车研发制造总部", 116.960, 36.560, "mfg", "中国第一辆重型卡车黄河牌诞生地"),
    ("国家超算济南中心与神威大科学装置", 117.135, 36.670, "it", "算力中国核心支撑·超算大模型创新高地"),
    ("济南新旧动能转换起步区战略新区", 117.030, 36.780, "zone", "跨黄河北展国家级绿色低碳先行示范区"),
    ("魏桥创业集团世界500强高端铝业基地", 117.760, 36.870, "mfg", "全球最大特纺与铝业航母·轻量化新材料"),
    ("博兴兴福全球商用厨具智造基地", 118.170, 37.130, "mfg", "中国厨都·全国40%以上商用厨具产地"),
    ("齐鲁化学工业区国家级绿色化工基地", 118.360, 36.810, "chem", "特大型综合石化产业基地·精细化工转型"),
    ("胜利油田CCUS全流程碳捕集封存工程", 118.580, 37.450, "energy", "全国首个百万吨级CCUS示范项目"),
    ("广饶全球橡胶轮胎制造与出口基地", 118.450, 37.080, "mfg", "中国轮胎第一县·子午胎产量占全国四分之一"),
    ("枣庄中国北方锂电之都全产业链矩阵", 117.420, 34.820, "energy", "欣旺达精工电子集聚·北方动力储能高地"),
    ("临沂商城千亿级专业批发市场集群", 118.310, 35.070, "logistics", "中国物流之都·南义乌北临沂·131处专业市场"),
    ("山钢日照千万吨级沿海绿色精品钢基", 119.300, 35.080, "mfg", "全流程超低排放·高附加值汽车板家电板"),
    ("威高集团国家级高端医疗器械产业园", 122.030, 37.540, "med", "打破国外垄断的高值医用耗材航母"),
    ("信发集团万亿级铝电化工绿色循环基地", 116.240, 36.590, "chem", "全国领先的工业热电循环综合经济样本"),
    ("菏泽现代医药港与鲁南生物医药高地", 115.520, 35.260, "med", "高端仿制药创新药全生命周期创新基地"),
    ("曹县汉服与木制品全球电商智造基地", 115.600, 34.780, "it", "全国汉服电商集聚区·板材深加工出口基地")
]

for name, lon, lat, ikind, desc in industries_data:
    px, py = to_alb(lon, lat)
    m = "D"
    fc = "#c0392b" if ikind == "mfg" else ("#2980b9" if ikind == "it" else ("#16a085" if ikind in ("marine", "med") else "#8e44ad"))
    sl4.add(px, py, name, ikind, note=desc, priority=1,
            marker=m, face=fc, size=5.5, kind_label="十强产业与海洋强省集群")

sym_type_h4, sym_idx_h4 = sl4.flush()

sb_x0 = ax_xlim[0] + span_x * 0.52
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=100)
add_compass(ax, 0.94, 0.91)

leg4 = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h4, title="优势产业集群大类", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h4, title="重大产业地标与领航龙头", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("山东省现代海洋与十强产业经济集聚格局图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Major Modern Marine & Industrial Clusters Spatial Pattern of Shandong Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg4, "数据源：山东省工业和信息化厅 · 山东省海洋经济统计公报 · 制作：《中国地理知识手册》",
    fontsize=6.5)

f4_path = os.path.join(OUT_DIR, "fig08-00-4_山东省现代海洋与十强产业经济集聚格局图.png")
fig.savefig(f4_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"✓ Saved Fig 08-00-4: {f4_path}")

# =============================================================================
# 图 08-00-5：山东省1986—2024年夜间灯光演变与半岛城市群发展图
# =============================================================================
print("Generating Fig 08-00-5 (Nightlight Trends)...")
fig = plt.figure(figsize=(11.0, 7.2), dpi=DPI)
fig.patch.set_facecolor("white")

gs = fig.add_gridspec(nrows=1, ncols=2, width_ratios=[1.15, 1.0], wspace=0.18,
                      left=0.03, right=0.97, top=0.92, bottom=0.08)

ax_map = fig.add_subplot(gs[0, 0])
ax_plot = fig.add_subplot(gs[0, 1])

ax_map.set_facecolor("#0b132b")
sd_prov.plot(ax=ax_map, facecolor="#1c2541", edgecolor="#3a506b", lw=0.6, zorder=2)
gpd.GeoSeries([sd_union], crs=ALBERS).boundary.plot(ax=ax_map, color="#5bc0be", lw=1.2, zorder=6)

nl_df = pd.read_csv(os.path.join(DATA_DIR, "shandong_nightlight_clean.csv"))
city_nl = nl_df.groupby(['city_code', 'city_name', 'year'])['sum'].sum().reset_index()

glow_points = [
    ("青岛主城与胶州湾", 120.38, 36.10, 165904, "#f1c40f"),
    ("济南主城与经十路", 117.05, 36.66, 102533, "#f39c12"),
    ("烟台主城与芝罘湾", 121.39, 37.52, 114850, "#e67e22"),
    ("潍坊主城与寒亭", 119.16, 36.71, 105231, "#e67e22"),
    ("临沂主城与兰山", 118.35, 35.08, 89261, "#f39c12"),
    ("淄博主城与临淄", 118.05, 36.81, 60613, "#f1c40f"),
    ("济宁主城与兖州", 116.60, 35.42, 69808, "#f39c12"),
    ("东营主城与油田", 118.65, 37.45, 67704, "#f1c40f"),
    ("滨州主城与邹平", 117.85, 37.05, 60292, "#e67e22"),
    ("菏泽主城与曹县", 115.50, 35.10, 50213, "#f39c12"),
    ("德州主城与高铁东站", 116.40, 37.44, 38249, "#f39c12"),
    ("威海主城与荣成", 122.20, 37.30, 39103, "#f1c40f"),
    ("聊城主城与茌平", 116.10, 36.50, 37534, "#f39c12"),
    ("日照主城与港区", 119.50, 35.35, 37113, "#f1c40f"),
    ("枣庄主城与新城", 117.40, 34.80, 31895, "#f39c12"),
    ("泰安主城与新泰", 117.30, 36.10, 32709, "#f39c12")
]

for gname, lon, lat, val, gcol in glow_points:
    px, py = to_alb(lon, lat)
    rad = np.sqrt(val) * 120.0
    ax_map.scatter(px, py, s=rad*0.06, c=gcol, alpha=0.35, edgecolors="none", zorder=8)
    ax_map.scatter(px, py, s=rad*0.02, c="#ffffff", alpha=0.75, edgecolors="none", zorder=9)
    ax_map.text(px, py, gname.split("与")[0], color="#ffffff", fontsize=6.8, weight="bold",
                ha="center", va="bottom", zorder=15,
                path_effects=[pe.withStroke(linewidth=1.8, foreground="#000000", alpha=0.8)])

ax_map.set_xlim(ax_xlim)
ax_map.set_ylim(ax_ylim)
ax_map.axis("off")
ax_map.set_title("山东省夜间灯光辐射空间分布与高亮集聚轴", fontsize=9.2, color="#ffffff", weight="bold", pad=8)

ax_plot.set_facecolor("#ffffff")
ax_plot.grid(True, linestyle="--", alpha=0.45, color="#bdc3c7")

focus_cities = [
    ("青岛市", "#c0392b", 2.4, "-"),
    ("济南市", "#2980b9", 2.4, "-"),
    ("烟台市", "#27ae60", 2.0, "-"),
    ("潍坊市", "#8e44ad", 2.0, "-"),
    ("临沂市", "#d35400", 2.0, "-"),
    ("淄博市", "#16a085", 1.8, "--"),
    ("济宁市", "#f39c12", 1.8, "--"),
    ("东营市", "#7f8c8d", 1.6, ":"),
    ("滨州市", "#34495e", 1.6, ":"),
    ("菏泽市", "#e74c3c", 1.6, "-.")
]

for cname, col, lw, ls in focus_cities:
    sub = city_nl[city_nl['city_name'] == cname].sort_values('year')
    if len(sub) > 0:
        ax_plot.plot(sub['year'], sub['sum'], color=col, lw=lw, ls=ls, label=cname, alpha=0.9)

ax_plot.set_xlabel("年份 (1986—2013/2024)", fontsize=8.5, color="#2c3e50")
ax_plot.set_ylabel("夜间灯光辐射总指数 (DN Sum)", fontsize=8.5, color="#2c3e50")
ax_plot.set_title("山东省主要城市群夜间灯光演变曲线 (1986—2024)", fontsize=9.2, weight="bold", color="#1a252f", pad=8)
ax_plot.legend(loc="upper left", fontsize=6.8, framealpha=0.9, ncol=2)

fig.suptitle("山东省1986—2024年夜间灯光演变与半岛城市群发展图", fontsize=12.5, weight="bold", y=0.985, color="#1a252f")

f5_path = os.path.join(OUT_DIR, "fig08-00-5_山东省1986—2024年夜间灯光演变与半岛城市群发展图.png")
fig.savefig(f5_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"✓ Saved Fig 08-00-5: {f5_path}")

print("\n=== ALL 5 OVERVIEW FIGURES COMPLETED SUCCESSFULLY! ===")
