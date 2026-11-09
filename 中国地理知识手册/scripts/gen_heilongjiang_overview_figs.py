# -*- coding: utf-8 -*-
"""黑龙江省地理统揽专题地图生成引擎（07-00）
包含 5 幅全省权威出版级地图与分析图表（精细调优排版、微缩字号、严格杜绝压盖）：
1. fig07-00-1_黑龙江省地形地貌与“五山一水一草三分田”宏观地貌格局图.png
2. fig07-00-2_黑龙江省行政区划与“一圈一带三带”城镇空间格局图.png
3. fig07-00-3_黑龙江省综合立体交通网与对俄互联互通大通道图.png
4. fig07-00-4_黑龙江省1986—2024年夜间灯光演变与哈尔滨首位度演进图.png
5. fig07-00-5_黑龙江省生态安全屏障与大界江大森林大湿地水系图.png
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

def add_scalebar(ax, x0, y0, length_km=150):
    mapkit.add_scalebar(ax, x0, y0, length_km=length_km)

def add_compass(ax, x=0.94, y=0.92):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.055), transform=ax.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=1.8, headwidth=5.5, headlength=6.5),
                ha="center", va="center", fontsize=8.8, fontweight="bold", color="#2c3e50", zorder=30)

print("Loading Heilongjiang provincial boundaries and DEM...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

hlj_prov = gpd.read_file(os.path.join(DATAV_DIR, "230000_full.json")).to_crs(ALBERS)
hlj_prov["geometry"] = hlj_prov.geometry.buffer(0)
hlj_union = hlj_prov.union_all()

b = hlj_prov.total_bounds
span_x = b[2] - b[0]
span_y = b[3] - b[1]
pad_x = span_x * 0.04
pad_y = span_y * 0.04
ax_xlim = (b[0] - pad_x, b[2] + pad_x)
ax_ylim = (b[1] - pad_y, b[3] + pad_y)

# 加载 DEM
dem_file = os.path.join(DATA_DIR, "dem", "province", "230000_z9.npz")
dem_data = np.load(dem_file)
step = 3
dem_raw = dem_data['dem'][::step, ::step]
dem_res = float(dem_data['res']) * step
dem_minx = float(dem_data['minx'])
dem_maxy = float(dem_data['maxy'])
print(f"Downsampled DEM shape: {dem_raw.shape}, res: {dem_res}m")

extent = (dem_minx, dem_minx + dem_raw.shape[1] * dem_res,
          dem_maxy - dem_raw.shape[0] * dem_res, dem_maxy)

hs = calc_hillshade(dem_raw, dem_res)
norm = Normalize(vmin=34.0, vmax=1690.0)

terrain_colors = [
    (0.00, "#196f3d"),   # 34m 抚远三江口与三江平原湿地
    (0.08, "#27ae60"),   # 120m 松嫩平原与大庆百湖低平原
    (0.18, "#7dcea0"),   # 250m 平原向台地农垦过渡带
    (0.32, "#f9e79f"),   # 450m 低山丘陵与漫岗黑土区
    (0.50, "#eb984e"),   # 800m 完达山/老爷岭中山林区
    (0.70, "#dc7633"),   # 1200m 小兴安岭与大兴安岭针阔叶混交林
    (0.88, "#ba4a00"),   # 1500m 大白山泰加林与高寒矮曲林
    (1.00, "#ffffff")    # 1690m 大秃顶子山张广才岭巅峰
]
terrain_cmap = LinearSegmentedColormap.from_list("hlj_dem", terrain_colors)
dem_rgb = terrain_cmap(norm(dem_raw))[:, :, :3]
shaded_rgb = dem_rgb * (0.42 + 0.58 * hs[:, :, np.newaxis])

FIGSIZE = (9.8, 8.2)

# =============================================================================
# 图 07-00-1：黑龙江省地形地貌与“五山一水一草三分田”宏观地貌格局图
# =============================================================================
print("Generating Fig 07-00-1 (Topography)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

im = ax.imshow(shaded_rgb, extent=extent, origin="upper", zorder=2)
patch = get_mpl_clip_patch(hlj_union)
ax.add_patch(patch)
im.set_clip_path(patch)

hlj_prov.boundary.plot(ax=ax, color="#2c3e50", lw=0.6, ls="--", zorder=5)
gpd.GeoSeries([hlj_union], crs=ALBERS).boundary.plot(ax=ax, color="#1a5276", lw=1.5, zorder=6)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl1 = mapkit.SymbolLabels(ax, fig)
sl1.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.48, 0.0, 1.0, 0.09),
             (0.90, 0.84, 1.0, 1.0)])

peaks_data = [
    ("大秃顶子山 (1690m 黑龙江最高峰·张广才岭)", 128.180, 44.510, "peak", "全省第一高峰·高山气象站·积雪深厚"),
    ("老秃顶子 (1686m 张广才岭主脊)", 128.150, 44.480, "mt", "长白山北延山系高耸分水岭"),
    ("伊勒呼里山卡伦山 (1528m 大兴安岭主脊)", 123.500, 51.900, "mt", "大兴安岭黑龙江段最高地标"),
    ("呼中大白山 (1528m 兴安北段泰加林之巅)", 123.300, 51.850, "mt", "国家级自然保护区·高寒苔原奇观"),
    ("平顶山 (1429m 小兴安岭最高峰)", 129.150, 47.380, "mt", "红松林海之巅·小兴安岭生态水塔"),
    ("大黑山 (1380m 小兴安岭西麓界峰)", 127.200, 49.000, "mt", "黑河南部险峻山屏"),
    ("亚布力大锅盔 (1374m 国际滑雪胜地)", 128.460, 44.770, "mt", "亚洲最大综合高山滑雪赛场依托"),
    ("完达山神顶峰 (854m 三江平原第一峰)", 133.550, 46.680, "mt", "迎接祖国第一缕阳光朝霞圣地"),
    ("老黑山/火烧山 (五大连池近代火山锥)", 126.150, 48.720, "mt", "1719-1721年火山溢流玄武岩石龙石海"),
    ("华夏东极三江口 (34m 黑龙江省陆地最低洼)", 134.780, 48.250, "lake", "黑龙江与乌苏里江交汇出境处")
]

for name, lon, lat, ptype, note in peaks_data:
    px, py = to_alb(lon, lat)
    m = "*" if ptype == "peak" else ("^" if ptype == "mt" else "o")
    fc = "#c0392b" if ptype == "peak" else ("#78281f" if ptype == "mt" else "#27ae60")
    sl1.add(px, py, name, ptype, note=note, priority=0 if ptype == "peak" else 1,
            marker=m, face=fc, size=7.0 if ptype == "peak" else 5.2, kind_label="地形控制性极点与名山大川")

waters_data = [
    ("黑龙江 (中俄跨界宏伟界江·中国第三大河)", 126.000, 50.800, "water", "黑龙江水系"),
    ("松花江干流 (横贯哈尔滨佳木斯同江)", 128.200, 46.100, "water", "松花江干流"),
    ("嫩江 (发源伊勒呼里山流贯齐齐哈尔)", 124.300, 48.000, "water", "嫩江水系"),
    ("乌苏里江 (中俄界江·三江平原东界)", 133.800, 46.500, "water", "乌苏里江界江"),
    ("牡丹江 (流经镜泊湖注入松花江)", 129.500, 44.800, "water", "牡丹江水系"),
    ("兴凯湖 (中俄界湖·亚洲最大淡水界湖)", 132.300, 45.250, "water", "兴凯湖"),
    ("镜泊湖 (世界第二大火山熔岩堰塞湖)", 128.900, 43.900, "water", "镜泊湖"),
    ("五大连池 (十四座火山相拥堰塞湖群)", 126.180, 48.700, "water", "五大连池"),
    ("扎龙国家级湿地 (丹顶鹤世界庇护水网)", 124.250, 47.200, "water", "扎龙湿地")
]

for name, lon, lat, wtype, note in waters_data:
    px, py = to_alb(lon, lat)
    sl1.add(px, py, name, wtype, note=note, priority=2,
            marker="s", face="#1b4f72", size=4.8, kind_label="骨干江河水系与著名湖泊湿地")

sym_type_h, sym_idx_h = sl1.flush()

sb_x0 = ax_xlim[0] + span_x * 0.52
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=200)
add_compass(ax, 0.94, 0.91)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="地形与水系要素分类", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="图上要素编号对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("黑龙江省地形地貌与“五山一水一草三分田”宏观地貌格局图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Geomorphology, Mountain Chains & River Basins of Heilongjiang Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：AWS Terrain 300m 高程 · 投影：Albers 等积圆锥 (中央经线 105°E) · 制作：《中国地理知识手册》",
    fontsize=6.5)

m1_path = os.path.join(OUT_DIR, "fig07-00-1_黑龙江省地形地貌与“五山一水一草三分田”宏观地貌格局图.png")
fig.savefig(m1_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"✓ Saved Fig 07-00-1: {m1_path}")

# =============================================================================
# 图 07-00-2：黑龙江省行政区划与“一圈一带三带”城镇空间格局图
# =============================================================================
print("Generating Fig 07-00-2 (Administrative & Urban Pattern)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

palette = [
    "#ebf5fb", "#e8f8f5", "#fef9e7", "#fdf2e9", "#f4ecf7",
    "#eafaf1", "#f5eef8", "#e8f6f3", "#fef5e7", "#eaeded",
    "#d5f5e3", "#fcf3cf", "#ebdef0"
]

for i, (_, row) in enumerate(hlj_prov.iterrows()):
    color = palette[i % len(palette)]
    gpd.GeoSeries([row.geometry], crs=ALBERS).plot(ax=ax, facecolor=color, edgecolor="#7f8c8d", lw=0.6, zorder=3)

gpd.GeoSeries([hlj_union], crs=ALBERS).boundary.plot(ax=ax, color="#1a5276", lw=1.6, zorder=6)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl2 = mapkit.SymbolLabels(ax, fig)
sl2.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.48, 0.0, 1.0, 0.09),
             (0.90, 0.84, 1.0, 1.0)])

# 标注 13 个地市州驻地
admin_hubs = [
    ("哈尔滨市 (省会·特大城市·副省级)", 126.540, 45.805, "core", "全省政治经济科技文化中心·特等客站机场枢纽"),
    ("齐齐哈尔市 (装备母机基地·鹤城)", 123.955, 47.360, "sub", "嫩江流域中心城市·中国一重中车齐车大本营"),
    ("牡丹江市 (雪城·镜泊湖·对俄枢纽)", 129.610, 44.550, "sub", "龙江南部区域中心·哈牡客专与沿边开放桥头堡"),
    ("佳木斯市 (东极枢纽·三江大粮仓)", 130.365, 46.810, "sub", "三江平原中心城市·现代农业与大型农机基地"),
    ("大庆市 (绿色油化之都·百湖之城)", 125.105, 46.590, "node", "中国最大石油石化基地·沃尔沃高端汽车制造"),
    ("鸡西市 (中国石墨之都·兴凯湖畔)", 130.970, 45.300, "node", "麻山石墨新材料基地·老煤城转型样板"),
    ("双鸭山市 (煤电化与三江平原稻麦仓)", 131.155, 46.640, "node", "国家煤电基地·友谊农场天下第一场"),
    ("伊春市 (祖国林都·红松故乡)", 128.910, 47.730, "node", "小兴安岭生态安全水塔·世界级森林康养名城"),
    ("七台河市 (中国冬奥冠军之乡·焦煤之都)", 131.015, 45.770, "node", "短道速滑世界金牌摇篮·高品质主焦煤与石墨烯"),
    ("黑河市 (中俄双子城·黑龙江公路大桥)", 127.500, 50.245, "node", "对俄边境全天候大通道·极寒汽车测试之都"),
    ("绥化市 (寒地黑土核心区·农业强市)", 126.985, 46.635, "node", "呼兰河流域粮都·千亿玉米生化产业集群"),
    ("鹤岗市 (精明收缩转型·龙江三峡)", 130.295, 47.345, "node", "萝北云山石墨超级基地·界江生态风光"),
    ("大兴安岭地区 (神州北极漠河·加格达奇)", 124.120, 50.420, "node", "黑龙江源头·北极村极光胜境·原始针叶泰加林")
]

for name, lon, lat, ctype, note in admin_hubs:
    cx, cy = to_alb(lon, lat)
    m = "*" if ctype == "core" else ("D" if ctype == "sub" else "s")
    c = "#78281f" if ctype == "core" else ("#1b4f72" if ctype == "sub" else "#935116")
    sz = 9.0 if ctype == "core" else (7.2 if ctype == "sub" else 6.2)
    sl2.add(cx, cy, name, ctype, note=note, priority=1, marker=m, face=c, size=sz,
            kind_label="省会特大城市 / 核心极核" if ctype == "core" else ("区域副中心城市" if ctype == "sub" else "地级行政中心"))

sym_type_h, sym_idx_h = sl2.flush()

sb_x0 = ax_xlim[0] + span_x * 0.52
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=200)
add_compass(ax, 0.94, 0.91)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="城市等级与空间节点", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="行政中心编号对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("黑龙江省行政区划与“一圈一带三带”城镇空间格局图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Administrative Divisions & 'One Circle, Four Belts' Urban Pattern of Heilongjiang Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：民政部标准地名代码 · 黑龙江省国土空间总体规划 (2021-2035) · 制作：《中国地理知识手册》",
    fontsize=6.5)

m2_path = os.path.join(OUT_DIR, "fig07-00-2_黑龙江省行政区划与“一圈一带三带”城镇空间格局图.png")
fig.savefig(m2_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"✓ Saved Fig 07-00-2: {m2_path}")

# =============================================================================
# 图 07-00-3：黑龙江省综合立体交通网与对俄互联互通大通道图
# =============================================================================
print("Generating Fig 07-00-3 (Transportation & Cross-border corridors)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

# 绘制行政底图
gpd.GeoSeries([hlj_union], crs=ALBERS).plot(ax=ax, facecolor="#ffffff", edgecolor="#1a5276", lw=1.6, zorder=2)
hlj_prov.boundary.plot(ax=ax, color="#bdc3c7", lw=0.6, ls=":", zorder=3)

# 绘制骨干高铁与铁路走廊
rail_lines = [
    # 哈大/京哈客专
    [(126.30, 45.30), (126.54, 45.75), (126.63, 45.76)],
    # 哈齐客专
    [(126.63, 45.76), (125.96, 46.06), (125.16, 46.57), (123.96, 47.26)],
    # 哈牡客专
    [(126.63, 45.76), (127.97, 45.21), (129.38, 44.58), (129.61, 44.59)],
    # 哈佳快速铁路
    [(126.63, 45.76), (127.48, 45.75), (129.56, 46.32), (130.37, 46.80)],
    # 牡佳高铁
    [(129.61, 44.59), (130.88, 45.28), (130.90, 45.77), (131.05, 46.66), (130.37, 46.80)],
    # 滨洲铁路/绥满铁路 (通满洲里)
    [(123.96, 47.26), (123.18, 47.33), (122.50, 48.00)],
    # 滨绥铁路 (直通绥芬河口岸)
    [(129.61, 44.59), (131.16, 44.42)],
    # 嫩林铁路 (纵贯大兴安岭)
    [(124.87, 48.48), (124.13, 50.41), (124.40, 51.68), (122.52, 52.96)],
    # 同江中俄铁路大桥
    [(130.37, 46.80), (132.51, 47.64), (132.54, 47.70)]
]

for r_pts in rail_lines:
    xs, ys = mapkit.smooth_line([to_alb(p[0], p[1]) for p in r_pts])
    ax.plot(xs, ys, color="#c0392b", lw=2.2, zorder=8, alpha=0.9)

# 高速公路走廊
hwy_lines = [
    # 绥满高速 G10
    [(123.20, 47.30), (123.95, 47.34), (125.10, 46.59), (126.60, 45.75), (129.60, 44.58), (131.15, 44.41)],
    # 鹤大高速 G11
    [(130.29, 47.34), (130.37, 46.80), (131.05, 46.66), (130.50, 45.70), (129.60, 44.58), (129.40, 43.80)],
    # 吉黑高速 G1211
    [(126.60, 45.75), (126.98, 46.63), (126.48, 48.24), (127.50, 50.24)],
    # 建黑高速 (通往抚远东极)
    [(130.37, 46.80), (132.03, 47.25), (134.29, 48.36)]
]

for h_pts in hwy_lines:
    xs, ys = mapkit.smooth_line([to_alb(p[0], p[1]) for p in h_pts])
    ax.plot(xs, ys, color="#2980b9", lw=1.6, ls="-", zorder=7, alpha=0.85)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl3 = mapkit.SymbolLabels(ax, fig)
sl3.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.48, 0.0, 1.0, 0.09),
             (0.90, 0.84, 1.0, 1.0)])

# 综合枢纽节点
trans_nodes = [
    ("哈尔滨西站/哈尔滨站 (国家特等综合客运枢纽)", 126.630, 45.758, "rail", "京哈高铁路网总中枢·欧式百年名站"),
    ("哈尔滨太平国际机场 (4E/4F大型国际枢纽)", 126.250, 45.620, "airport", "东北面向东北亚与北美航线核心门户"),
    ("齐齐哈尔南站 (哈齐高铁终点大客站)", 123.960, 47.260, "rail", "龙江西翼高速客运中心"),
    ("牡丹江站 (哈牡客专/牡佳高铁枢纽)", 129.610, 44.590, "rail", "龙江南部最大客运枢纽"),
    ("佳木斯站 (哈佳高铁/三江平原枢纽)", 130.370, 46.800, "rail", "哈佳与牡佳高铁交汇客站"),
    ("大庆东站 (哈齐高铁油田商务客站)", 125.160, 46.570, "rail", "大庆核心高铁客运大站"),
    ("绥芬河口岸站 (中俄跨境百年铁路大门)", 131.160, 44.420, "port", "中欧班列东通道第一大口岸"),
    ("同江中俄跨江铁路大桥 (跨界铁运枢纽)", 132.540, 47.700, "port", "首座跨江界河铁路大桥·大宗散货跨境通道"),
    ("黑河黑龙江公路大桥 (跨国公路客货通道)", 127.600, 50.220, "port", "中俄黑河—布拉戈维申斯克公路大桥"),
    ("抚远东极机场 (中国最东端民用机场)", 134.370, 48.190, "airport", "直通北京哈尔滨华夏东极通航空港"),
    ("漠河古莲机场 (中国最北端民航机场)", 122.420, 52.910, "airport", "直抵神州北极北极村空中快道")
]

for name, lon, lat, ptype, note in trans_nodes:
    px, py = to_alb(lon, lat)
    m = "s" if ptype == "rail" else ("o" if ptype == "airport" else "D")
    fc = "#c0392b" if ptype == "rail" else ("#1b4f72" if ptype == "airport" else "#e67e22")
    sl3.add(px, py, name, ptype, note=note, priority=0 if ptype == "rail" else 1,
            marker=m, face=fc, size=6.5 if ptype == "rail" else 5.5, kind_label="高铁航空与对俄口岸枢纽")

sym_type_h, sym_idx_h = sl3.flush()

sb_x0 = ax_xlim[0] + span_x * 0.52
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=200)
add_compass(ax, 0.94, 0.91)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="交通网络与口岸类型", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="枢纽节点编号对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("黑龙江省综合立体交通网与对俄互联互通大通道图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Integrated Transportation System & China-Russia Corridors of Heilongjiang Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：中国国家铁路集团 · 交通运输部全国公路网 · 编绘：《中国地理知识手册》",
    fontsize=6.5)

m3_path = os.path.join(OUT_DIR, "fig07-00-3_黑龙江省综合立体交通网与对俄互联互通大通道图.png")
fig.savefig(m3_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"✓ Saved Fig 07-00-3: {m3_path}")

# =============================================================================
# 图 07-00-4：黑龙江省1986—2024年夜间灯光演变与哈尔滨首位度演进图
# =============================================================================
print("Generating Fig 07-00-4 (Nightlight Evolution & Primacy)...")
fig, (ax_nl, ax_ratio) = plt.subplots(2, 1, figsize=(9.8, 8.5), dpi=DPI)
fig.patch.set_facecolor("white")

nl_clean_df = pd.read_csv(os.path.join(DATA_DIR, "heilongjiang_nightlight_clean.csv"))
nl_prov = nl_clean_df.groupby("year")["sum"].sum().reset_index()

# 筛选哈尔滨 (代码以 2301 开头)
nl_hrb = nl_clean_df[nl_clean_df["city_code"].astype(str).str.startswith("2301")].groupby("year")["sum"].sum().reset_index()

merged_nl = pd.merge(nl_prov, nl_hrb, on="year", suffixes=("_prov", "_hrb"))
merged_nl["ratio"] = merged_nl["sum_hrb"] / merged_nl["sum_prov"] * 100.0

years = merged_nl["year"].values
sum_prov = merged_nl["sum_prov"].values
sum_hrb = merged_nl["sum_hrb"].values
ratios = merged_nl["ratio"].values

# 上子图：时序夜光辐射总量跃升
ax_nl.plot(years, sum_prov, color="#d35400", lw=2.2, marker="o", markersize=3.5, label="全省夜间灯光辐射总积分 (DN·Pixel)")
ax_nl.plot(years, sum_hrb, color="#2980b9", lw=2.0, marker="s", markersize=3.5, label="哈尔滨市夜间灯光辐射总量")
ax_nl.fill_between(years, sum_prov, color="#fdebd0", alpha=0.45)
ax_nl.fill_between(years, sum_hrb, color="#d4e6f1", alpha=0.55)

# 历史拐点标注
ax_nl.annotate("1996：哈尔滨与齐齐哈尔老工业区\n夜间基础重工业生产",
               xy=(1996, sum_prov[np.where(years == 1996)[0][0]]),
               xytext=(1988, sum_prov.max() * 0.45),
               arrowprops=dict(arrowstyle="->", color="#c0392b", lw=0.9),
               fontsize=7.2, fontweight="bold", color="#78281f",
               bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffffff", edgecolor="#e74c3c", alpha=0.9))

ax_nl.annotate("2008：哈大齐工业走廊推进\n大庆油田与松北新区大片铺开",
               xy=(2008, sum_prov[np.where(years == 2008)[0][0]]),
               xytext=(2000, sum_prov.max() * 0.72),
               arrowprops=dict(arrowstyle="->", color="#c0392b", lw=0.9),
               fontsize=7.2, fontweight="bold", color="#78281f",
               bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffffff", edgecolor="#e74c3c", alpha=0.9))

ax_nl.set_title("黑龙江省 1986—2024 年夜间灯光辐射时序跃迁演进", fontsize=10.5, fontweight="bold", color=C_TEXT)
ax_nl.set_ylabel("夜光总量辐射积分 (DN·Pixel)", fontsize=7.8, color="#2c3e50")
ax_nl.grid(True, linestyle="--", alpha=0.4)
ax_nl.legend(loc="upper left", fontsize=7.5)
ax_nl.tick_params(labelsize=7.2)

# 下子图：哈尔滨首位度比重变化
bars = ax_ratio.bar(years, ratios, width=0.6, color="#16a085", edgecolor="#0e6251", alpha=0.85, label="哈尔滨夜光占全省比重 (%)")
ax_ratio.axhline(ratios.mean(), color="#c0392b", lw=1.2, ls="--", label=f"历年平均占比基准线 ({ratios.mean():.1f}%)")

for i in range(0, len(years), 5):
    yr = years[i]
    r = ratios[i]
    ax_ratio.text(yr, r + 0.8, f"{r:.1f}%", ha="center", va="bottom", fontsize=6.5, fontweight="bold", color="#0e6251")

ax_ratio.set_title("哈尔滨市夜间灯光首位度比重演变轨迹 (1986—2024)", fontsize=10.5, fontweight="bold", color=C_TEXT)
ax_ratio.set_ylabel("占全省总辐射比重 (%)", fontsize=7.8, color="#2c3e50")
ax_ratio.set_xlabel("年份 Year", fontsize=7.8, color="#2c3e50")
ax_ratio.set_ylim(0, max(ratios) * 1.25)
ax_ratio.grid(True, linestyle="--", alpha=0.4)
ax_ratio.legend(loc="upper left", fontsize=7.5)
ax_ratio.tick_params(labelsize=7.2)

fig.tight_layout(pad=2.8)
fig.text(0.5, 0.01, "数据来源：夜间灯光连续遥感数据集 (1986-2024) · DMSP-OLS & VIIRS 跨传感器一致性校准 · 制作：《中国地理知识手册》",
         ha="center", va="bottom", fontsize=6.8, color="#7f8c8d")

m4_path = os.path.join(OUT_DIR, "fig07-00-4_黑龙江省1986—2024年夜间灯光演变与哈尔滨首位度演进图.png")
fig.savefig(m4_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"✓ Saved Fig 07-00-4: {m4_path}")

# =============================================================================
# 图 07-00-5：黑龙江省生态安全屏障与大界江大森林大湿地水系图
# =============================================================================
print("Generating Fig 07-00-5 (Ecological Barrier & Wetland Hydrology)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

# 绘制行政底图
gpd.GeoSeries([hlj_union], crs=ALBERS).plot(ax=ax, facecolor="#ffffff", edgecolor="#145a32", lw=1.6, zorder=2)
hlj_prov.boundary.plot(ax=ax, color="#a9dfbf", lw=0.6, ls=":", zorder=3)

# 绘制主要森林生态屏障区域（大兴安岭、小兴安岭、张广才岭、完达山）示意性色块
eco_zones = [
    # 大兴安岭生态屏障
    ([(121.5, 53.4), (124.5, 52.8), (125.0, 51.5), (124.0, 50.4), (122.5, 51.0), (121.5, 53.0)], "#1e8449", "大兴安岭寒温带原始针叶林生态安全屏障"),
    # 小兴安岭生态屏障
    ([(127.5, 49.2), (129.5, 48.5), (130.5, 47.6), (129.0, 47.0), (128.0, 47.2), (127.0, 48.2)], "#27ae60", "小兴安岭温带红松针阔混交林涵养屏障"),
    # 张广才岭-老爷岭森林区
    ([(127.8, 45.2), (129.5, 44.5), (131.0, 44.2), (129.5, 43.8), (128.2, 44.5)], "#2ecc71", "张广才岭-老爷岭水源涵养与生物多样性屏障"),
    # 三江平原大湿地带
    ([(132.0, 47.5), (134.5, 48.2), (134.0, 46.8), (132.5, 46.5)], "#76d7c4", "三江平原大湿地群与国家核心黑土生态农业区"),
    # 松嫩平原西部湿地草原带
    ([(123.5, 47.5), (124.8, 46.8), (124.5, 45.5), (123.5, 46.5)], "#a3e4d7", "松嫩平原湿地草甸与扎龙丹顶鹤自然保护区")
]

for pts, col, label in eco_zones:
    poly_alb = ShpPolygon([to_alb(p[0], p[1]) for p in pts])
    poly_inter = poly_alb.intersection(hlj_union)
    if not poly_inter.is_empty:
        gpd.GeoSeries([poly_inter], crs=ALBERS).plot(ax=ax, facecolor=col, edgecolor="none", alpha=0.35, zorder=4)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl5 = mapkit.SymbolLabels(ax, fig)
sl5.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.48, 0.0, 1.0, 0.09),
             (0.90, 0.84, 1.0, 1.0)])

eco_points = [
    ("扎龙国家级自然保护区 (5A·丹顶鹤摇篮)", 124.250, 47.200, "wetland", "国际重要湿地·野生丹顶鹤最大栖息繁殖地"),
    ("三江国家级自然保护区 (抚远三江平原腹心)", 134.400, 47.800, "wetland", "原始淡水沼泽森林湿地生态系统"),
    ("兴凯湖国家级自然保护区 (大白鱼与鸟类驿站)", 132.300, 45.250, "wetland", "东北亚候鸟迁飞大通道核心停歇枢纽"),
    ("五营国家级森林公园 (红松原始森林故乡)", 129.250, 48.120, "forest", "小兴安岭最完好的红松原生群落"),
    ("呼中大白山国家级自然保护区 (最北泰加林)", 123.300, 51.850, "forest", "寒温带多年连续冻土与高山苔原"),
    ("黑瞎子岛国家湿地公园 (中俄交界东极明珠)", 134.650, 48.330, "wetland", "乌苏里江汇入黑龙江天然低位沼泽"),
    ("镜泊湖世界地质公园 (熔岩堰塞湖与地下森林)", 128.900, 43.900, "water", "地下火山口森林与吊水楼瀑布"),
    ("五大连池世界地质公园 (天然火山活博物馆)", 126.180, 48.700, "water", "14座火山锥与五池相连矿泉宝库"),
    ("大庆龙凤湿地自然保护区 (亚洲最大城中湿地)", 125.180, 46.550, "wetland", "百湖之城核心生态绿肺与候鸟家园")
]

for name, lon, lat, ptype, note in eco_points:
    px, py = to_alb(lon, lat)
    m = "s" if ptype == "wetland" else ("^" if ptype == "forest" else "o")
    fc = "#148f77" if ptype == "wetland" else ("#196f3d" if ptype == "forest" else "#2e86c1")
    sl5.add(px, py, name, ptype, note=note, priority=0 if ptype == "wetland" else 1,
            marker=m, face=fc, size=6.5 if ptype == "wetland" else 5.5, kind_label="国家级湿地/森林自然保护区")

sym_type_h, sym_idx_h = sl5.flush()

sb_x0 = ax_xlim[0] + span_x * 0.52
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=200)
add_compass(ax, 0.94, 0.91)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="生态屏障与保护区类型", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="重点生态节点编号对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("黑龙江省生态安全屏障与大界江大森林大湿地水系图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Ecological Security Barriers, Virgin Forests & Wetland Network of Heilongjiang Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：生态环境部国家生态红线 · 林草局国家级自然保护区名录 · 制作：《中国地理知识手册》",
    fontsize=6.5)

m5_path = os.path.join(OUT_DIR, "fig07-00-5_黑龙江省生态安全屏障与大界江大森林大湿地水系图.png")
fig.savefig(m5_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"✓ Saved Fig 07-00-5: {m5_path}")

print("\n" + "=" * 60)
print("All 5 overview publication figures for Heilongjiang generated successfully!")
print("=" * 60)
