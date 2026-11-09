# -*- coding: utf-8 -*-
"""辽宁省地理统揽专题地图生成引擎（05-00）
包含 5 幅全省权威出版级地图与分析图表（精细调优排版、微缩字号、严格杜绝压盖）：
1. fig05-00-1_辽宁省地形地貌与“山海相拥”地貌格局图.png
2. fig05-00-2_辽宁省行政区划与“沈大双核·辽中南”城镇空间格局图.png
3. fig05-00-3_辽宁省陆海综合立体交通网与东北出海走廊图.png
4. fig05-00-4_辽宁省1986—2024年夜间灯光演变与沈大双核经济带图.png
5. fig05-00-5_辽宁省生态安全屏障与大辽河水系海洋生态图.png
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

def add_scalebar(ax, x0, y0, length_km=80):
    mapkit.add_scalebar(ax, x0, y0, length_km=length_km)

def add_compass(ax, x=0.94, y=0.92):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.055), transform=ax.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=1.8, headwidth=5.5, headlength=6.5),
                ha="center", va="center", fontsize=8.8, fontweight="bold", color="#2c3e50", zorder=30)

# 加载基础空间数据
print("Loading Liaoning provincial boundaries and DEM...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

ln_prov = gpd.read_file(os.path.join(DATAV_DIR, "210000_full.json")).to_crs(ALBERS)
ln_prov["geometry"] = ln_prov.geometry.buffer(0)
ln_union = ln_prov.union_all()

b = ln_prov.total_bounds
span_x = b[2] - b[0]
span_y = b[3] - b[1]
pad_x = span_x * 0.04
pad_y = span_y * 0.04
ax_xlim = (b[0] - pad_x, b[2] + pad_x)
ax_ylim = (b[1] - pad_y, b[3] + pad_y)

# 加载 DEM
dem_file = os.path.join(DATA_DIR, "dem", "province", "210000_z9.npz")
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
norm = Normalize(vmin=0.0, vmax=1336.1)

terrain_colors = [
    (0.00, "#27ae60"),   # 0m 渤海黄海滨海平原与三角洲
    (0.05, "#58d68d"),   # 50m 辽河平原冲积沃野
    (0.12, "#a9dfbf"),   # 150m 辽河平原丘陵过渡台地
    (0.22, "#f9e79f"),   # 300m 辽西辽东低山浅丘
    (0.40, "#eb984e"),   # 550m 医巫闾山千山中段
    (0.60, "#dc7633"),   # 800m 辽东千米低中山
    (0.80, "#ba4a00"),   # 1100m 辽东长白山余脉
    (0.92, "#78281f"),   # 1250m 辽宁脊梁佛顶山
    (1.00, "#4a235a")    # 1336.1m 花脖山辽宁之巅
]
terrain_cmap = LinearSegmentedColormap.from_list("ln_dem", terrain_colors)
dem_rgb = terrain_cmap(norm(dem_raw))[:, :, :3]
shaded_rgb = dem_rgb * (0.42 + 0.58 * hs[:, :, np.newaxis])

FIGSIZE = (9.8, 7.5)

# =============================================================================
# 图 05-00-1：辽宁省地形地貌与“山海相拥”地貌格局图
# =============================================================================
print("Generating Fig 05-00-1 (Topography)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

im = ax.imshow(shaded_rgb, extent=extent, origin="upper", zorder=2)
patch = get_mpl_clip_patch(ln_union)
ax.add_patch(patch)
im.set_clip_path(patch)

ln_prov.boundary.plot(ax=ax, color="#2c3e50", lw=0.6, ls="--", zorder=5)
gpd.GeoSeries([ln_union], crs=ALBERS).boundary.plot(ax=ax, color="#1a5276", lw=1.5, zorder=6)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl1 = mapkit.SymbolLabels(ax, fig)
sl1.reserve([(0.0, 0.0, 0.36, 0.30),      # 左下角放图例
             (0.48, 0.0, 1.0, 0.09),      # 比例尺
             (0.90, 0.84, 1.0, 1.0)])     # 指北针

peaks_data = [
    ("花脖山 (1336.1m 辽宁第一峰·辽宁屋脊)", 124.950, 40.950, "peak", "长白山脉南延最高峰·宽甸与桓仁分界"),
    ("佛顶山 (1305m 桓仁全省第二高峰)", 125.280, 41.450, "mt", "辽东茂密原始针阔混交林带"),
    ("金山 (1256m 辽西最高峰·凌源之巅)", 119.250, 41.150, "mt", "努鲁儿虎山脉南段巍峨险峰"),
    ("帽儿山 (1141m 岫岩之巅鞍山最高)", 123.420, 40.450, "mt", "千山山脉向南延伸主峰"),
    ("大青山 (1140m 葫芦岛最高峰)", 119.750, 40.750, "mt", "燕山余脉建昌生态水源林山地"),
    ("步云山 (1130.7m 辽南第一峰)", 122.860, 39.950, "mt", "大连庄河最高峰·地热温泉富集"),
    ("乌兰木图山 (1071.4m 阜新最高峰)", 121.320, 42.120, "mt", "医巫闾山北延山峰"),
    ("老凤楼 (1046m 营口盖州之巅)", 122.750, 40.180, "mt", "辽南群峰连绵屏障"),
    ("医巫闾山望海寺 (866.6m 北方镇山)", 121.720, 41.620, "mt", "古代五大镇山之北方镇山·辽代皇家圣山"),
    ("凤凰山 (836m 险绝东北第一名山)", 124.080, 40.400, "mt", "丹东凤城雄奇花岗岩险峰"),
    ("千山仙人台 (708.5m 东北明珠)", 123.130, 41.020, "mt", "释道同山·无峰不奇东北名岳"),
    ("大黑山 (663m 辽南第一名山)", 121.820, 39.090, "mt", "大连金普新区俯瞰黄渤海要冲"),
    ("笔架山 (78m 海中潮汐天桥奇峰)", 121.070, 40.810, "coast", "锦州湾海蚀卵石天然海桥"),
    ("辽河口湿地红海滩 (0m 渤海滩涂基线)", 121.800, 40.850, "coast", "世界最大潮间带翅碱蓬湿地")
]

for name, lon, lat, ptype, note in peaks_data:
    px, py = to_alb(lon, lat)
    m = "^" if ptype in ["peak", "mt"] else "o"
    c = "#78281f" if ptype == "peak" else ("#ba4a00" if ptype == "mt" else "#1b4f72")
    sl1.add(px, py, name, ptype, note=note, priority=1, marker=m, face=c, size=6.8,
            kind_label="全省最高极顶 / 著名名山" if ptype in ["peak", "mt"] else "滨海奇观 / 河口湿地基线")

waters_data = [
    ("辽河干流 (穿辽河平原入渤海)", 122.900, 41.700, "water", "全省第一大河·冲积黑土平原"),
    ("浑河干流 (沈阳抚顺母亲河)", 123.500, 41.760, "water", "流经抚顺沈阳注入大辽河"),
    ("太子河干流 (本溪辽阳命脉)", 123.300, 41.280, "water", "穿山过城润泽辽东半岛"),
    ("鸭绿江干流 (中朝界河入黄海)", 124.450, 40.150, "water", "水能充沛水丰水库"),
    ("大凌河干流 (横贯辽西入渤海)", 120.600, 41.500, "water", "辽西第一大河·滋养三燕文明")
]

for wname, wlon, wlat, wtype, wnote in waters_data:
    wx, wy = to_alb(wlon, wlat)
    sl1.add(wx, wy, wname, wtype, note=wnote, priority=2, marker="o", face="#1f618d", size=6.0,
            kind_label="骨干水系干流 / 江河湖泊")

sym_type_h, sym_idx_h = sl1.flush()

sb_x0 = ax_xlim[0] + span_x * 0.52
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=80)
add_compass(ax, 0.94, 0.91)

cax = ax.inset_axes([0.04, 0.06, 0.024, 0.22])
cb = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=terrain_cmap), cax=cax, orientation="vertical")
cb.set_label("高程 Elevation (m)", fontsize=6.8, color="#2c3e50")
cb.ax.tick_params(labelsize=6.0, length=2.0)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="地形与水系要素", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="图上要素编号对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("辽宁省地形地貌与“山海相拥”宏观格局图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Geomorphology, Mountain Chains & Coastal Basins of Liaoning Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：AWS Terrain GLO-30 DEM · 投影：Albers 等积圆锥 (中央经线 105°E) · 制作：《中国地理知识手册》",
    fontsize=6.5)

m1_path = os.path.join(OUT_DIR, "fig05-00-1_辽宁省地形地貌与“山海相拥”地貌格局图.png")
fig.savefig(m1_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"Map 1 saved: {m1_path}")

# =============================================================================
# 图 05-00-2：辽宁省行政区划与“沈大双核·辽中南”城镇空间格局图
# =============================================================================
print("Generating Fig 05-00-2 (Administrative & Urban Hierarchy)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

palette = [
    "#ebf5fb", "#e8f8f5", "#fef9e7", "#fdf2e9", "#f4ecf7",
    "#eafaf1", "#f5eef8", "#e8f6f3", "#fef5e7", "#f9ebea",
    "#eaf2f8", "#fcf3cf", "#eaeded", "#ebedef"
]

for i, (_, row) in enumerate(ln_prov.iterrows()):
    color = palette[i % len(palette)]
    gpd.GeoSeries([row.geometry], crs=ALBERS).plot(ax=ax, facecolor=color, edgecolor="#7f8c8d", lw=0.6, zorder=3)

gpd.GeoSeries([ln_union], crs=ALBERS).boundary.plot(ax=ax, color="#1a5276", lw=1.6, zorder=6)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl2 = mapkit.SymbolLabels(ax, fig)
sl2.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.48, 0.0, 1.0, 0.09),
             (0.90, 0.84, 1.0, 1.0)])

admin_centers = [
    ("沈阳市 (省会 · 特大城市 · 副省级)", 123.450, 41.720, "core", "辽宁省政治经济文化金融中心·沈阳都市圈核心极"),
    ("大连市 (副省级 · 计划单列市 · 特大城市)", 121.615, 38.914, "core", "东北亚国际航运中心·沿海经济带极核"),
    ("鞍山市 (钢都 · 千山风景名胜)", 122.990, 41.110, "sub", "中国钢铁冶金重镇·世界菱镁之都"),
    ("抚顺市 (煤都转型 · 大伙房水源)", 123.950, 41.880, "node", "雷锋精神发祥地·现代高端精细化工"),
    ("本溪市 (山城铁都 · 中国药都)", 123.770, 41.290, "node", "本溪水洞·生物医药健康产业基地"),
    ("丹东市 (中国最大边境口岸城市)", 124.320, 39.980, "node", "鸭绿江入海口·抗美援朝出征地·对朝经贸门户"),
    ("锦州市 (辽西走廊门户 · 现代港口)", 121.130, 41.100, "sub", "辽沈战役转折地·锦州港陆海联动枢纽"),
    ("营口市 (大辽河出海口 · 近代百年商埠)", 122.230, 40.670, "node", "鲅鱼圈亿吨深水港·中国镁都民营经济"),
    ("阜新市 (首批资源枯竭转型示范)", 121.650, 41.980, "node", "海州露天矿生态修复·风光氢储绿能基地"),
    ("辽阳市 (东北第一古城 · 两千三百年文脉)", 123.180, 41.280, "node", "太子河中游·现代芳烃化纤基地"),
    ("盘锦市 (辽河三角洲 · 湿地之都)", 122.050, 41.180, "node", "辽河油田·红海滩湿地·优质粳稻大米"),
    ("铁岭市 (辽北粮仓 · 全国超级产粮大市)", 123.730, 42.220, "node", "辽河平原黑土地沃野·特色曲艺幽默之都"),
    ("朝阳市 (三燕古都 · 世界古生物化石宝库)", 120.450, 41.570, "node", "牛河梁红山文化·第一只鸟飞起之地"),
    ("葫芦岛市 (关外第一市 · 辽西走廊南咽喉)", 120.850, 40.720, "node", "兴城海滨明代古城·特种造船与徐大堡核电")
]

for name, lon, lat, ctype, note in admin_centers:
    cx, cy = to_alb(lon, lat)
    m = "*" if ctype == "core" else ("D" if ctype == "sub" else "s")
    c = "#78281f" if ctype == "core" else ("#1b4f72" if ctype == "sub" else "#935116")
    sz = 9.0 if ctype == "core" else (7.2 if ctype == "sub" else 6.2)
    sl2.add(cx, cy, name, ctype, note=note, priority=1, marker=m, face=c, size=sz,
            kind_label="省会特大城市 / 经济极核" if ctype == "core" else ("区域次中心城市" if ctype == "sub" else "地级市行政中心"))

sym_type_h, sym_idx_h = sl2.flush()

sb_x0 = ax_xlim[0] + span_x * 0.52
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=80)
add_compass(ax, 0.94, 0.91)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="城市等级与空间节点", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="行政中心编号对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("辽宁省行政区划与“沈大双核·辽中南”城镇空间格局图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Administrative Divisions & Urban Hierarchy Pattern of Liaoning Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：自然资源部标准地图服务 · 投影：Albers 等积圆锥 (中央经线 105°E) · 制作：《中国地理知识手册》",
    fontsize=6.5)

m2_path = os.path.join(OUT_DIR, "fig05-00-2_辽宁省行政区划与“沈大双核·辽中南”城镇空间格局图.png")
fig.savefig(m2_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"Map 2 saved: {m2_path}")

# =============================================================================
# 图 05-00-3：辽宁省陆海综合立体交通网与东北出海走廊图
# =============================================================================
print("Generating Fig 05-00-3 (Comprehensive Transportation)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

ln_prov.plot(ax=ax, facecolor="#f8f9fa", edgecolor="#bdc3c7", lw=0.6, zorder=2)
gpd.GeoSeries([ln_union], crs=ALBERS).boundary.plot(ax=ax, color="#2c3e50", lw=1.5, zorder=6)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl3 = mapkit.SymbolLabels(ax, fig)
sl3.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.48, 0.0, 1.0, 0.09),
             (0.90, 0.84, 1.0, 1.0)])

# 绘制干线铁路与高铁
corridors_lines = [
    # 哈大客专
    ([(121.615, 39.010), (122.250, 40.450), (122.900, 41.135), (123.155, 41.275), (123.435, 41.818), (123.720, 42.230), (124.100, 42.790)], "#c0392b", 2.4),
    # 京沈高铁
    ([(119.410, 41.250), (120.445, 41.605), (121.680, 42.050), (123.435, 41.818)], "#c0392b", 2.4),
    # 秦沈客专
    ([(120.350, 40.310), (120.820, 40.770), (121.150, 41.010), (121.880, 41.380), (123.398, 41.794)], "#d35400", 2.0),
    # 沈丹客专
    ([(123.435, 41.818), (123.765, 41.295), (124.385, 40.125)], "#c0392b", 2.0),
    # 丹大快铁
    ([(124.385, 40.125), (124.150, 39.880), (122.967, 39.697), (121.615, 39.010)], "#e67e22", 1.8),
    # 朝凌客专
    ([(120.445, 41.605), (120.720, 41.450), (120.950, 41.300), (121.180, 41.180)], "#c0392b", 1.8)
]

for pts, lcolor, lw in corridors_lines:
    alb_pts = [to_alb(p[0], p[1]) for p in pts]
    xs, ys = mapkit.smooth_line(alb_pts)
    ax.plot(xs, ys, color=lcolor, lw=lw, zorder=5, alpha=0.88)
    ax.plot(xs, ys, color="#ffffff", lw=lw * 0.4, ls="--", zorder=6)

transport_nodes = [
    ("沈阳桃仙国际机场 (4E级区域门户枢纽)", 123.483, 41.639, "air", "东北旅客与航空货运前列枢纽"),
    ("大连周水子国际机场 (4E级沿海门户)", 121.538, 38.965, "air", "对日韩关键国际航空桥梁"),
    ("沈阳北站 (特等客运站/京哈高铁中枢)", 123.435, 41.818, "rail", "哈大/京沈/沈丹客专黄金大交汇"),
    ("大连北站 (特等客运站/哈大客专终点)", 121.615, 39.010, "rail", "辽南陆海空立体换乘综合枢纽"),
    ("大连港大窑湾港区 (全球深水泊位)", 121.750, 39.000, "port", "东北亚国际航运中心核心港区"),
    ("营口港鲅鱼圈港区 (亿吨级综合大港)", 122.100, 40.300, "port", "东北腹地最近出海主通道"),
    ("锦州港 (辽西北与蒙东黄金出海口)", 120.980, 40.790, "port", "锡赤朝锦新通道陆海联动枢纽"),
    ("丹东港大东港区 (黄海北部优质良港)", 124.150, 39.820, "port", "对朝经贸与东北东部物流出海口"),
    ("盘锦港 (辽滨港区精细化工专业港)", 121.950, 40.700, "port", "石化原料进出口专业深水码头"),
    ("葫芦岛港 (辽西重装特种船舶深水港)", 120.920, 40.720, "port", "重装出海与军民融合关键港区"),
    ("锦州南站 (中国高铁试验第一站)", 121.150, 41.010, "rail", "秦沈客运专线首座高铁客站"),
    ("朝阳站 (京沈高铁辽西中心枢纽)", 120.445, 41.605, "rail", "朝凌客专与京沈客专换乘枢纽")
]

for name, lon, lat, k, desc in transport_nodes:
    x, y = to_alb(lon, lat)
    m = "^" if k == "air" else ("s" if k == "rail" else "o")
    c = "#8e44ad" if k == "air" else ("#154360" if k == "rail" else "#117864")
    sz = 7.5 if k in ["air", "port"] else 6.5
    sl3.add(x, y, name, k, note=desc, priority=1, marker=m, face=c, size=sz,
            kind_label="民航门户机场" if k == "air" else ("高铁特等车站 / 综合客站" if k == "rail" else "亿吨级综合深水港区"))

sym_type_h, sym_idx_h = sl3.flush()

sb_x0 = ax_xlim[0] + span_x * 0.52
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=80)
add_compass(ax, 0.94, 0.91)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="交通基础设施要素", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="交通枢纽编号对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("辽宁省陆海综合立体交通网与东北出海走廊图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Comprehensive Transportation Network & Northeast Maritime Corridors of Liaoning",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：中国国家铁路集团·交通运输部·中国港口协会 · 投影：Albers 等积圆锥 (中央经线 105°E) · 制作：《中国地理知识手册》",
    fontsize=6.5)

m3_path = os.path.join(OUT_DIR, "fig05-00-3_辽宁省陆海综合立体交通网与东北出海走廊图.png")
fig.savefig(m3_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"Map 3 saved: {m3_path}")

# =============================================================================
# 图 05-00-4：辽宁省1986—2024年夜间灯光演变与沈大双核经济带图
# =============================================================================
print("Generating Fig 05-00-4 (Nightlight Evolution)...")
nl_clean = pd.read_csv(os.path.join(DATA_DIR, "liaoning_nightlight_clean.csv"))

fig, (ax_chart, ax_map) = plt.subplots(1, 2, figsize=(11.5, 6.2), dpi=DPI,
                                       gridspec_kw={'width_ratios': [1.15, 1.0]})
fig.subplots_adjust(left=0.065, right=0.975, top=0.920, bottom=0.090, wspace=0.22)
fig.patch.set_facecolor("white")

nl_prov = nl_clean.groupby(['year', 'city_name'])['sum'].sum().reset_index()

for city in nl_prov['city_name'].unique():
    cdf = nl_prov[nl_prov['city_name'] == city].sort_values('year')
    if "沈阳" in city:
        ax_chart.plot(cdf['year'], cdf['sum'], color="#c0392b", lw=2.5, label="沈阳市 (省会·特大城市)", zorder=10)
    elif "大连" in city:
        ax_chart.plot(cdf['year'], cdf['sum'], color="#2980b9", lw=2.5, label="大连市 (副省级·航运中心)", zorder=9)
    elif "鞍山" in city:
        ax_chart.plot(cdf['year'], cdf['sum'], color="#d35400", lw=1.6, ls="-", label="鞍山市 (钢铁冶金之都)", zorder=7)
    elif "营口" in city:
        ax_chart.plot(cdf['year'], cdf['sum'], color="#27ae60", lw=1.5, ls="--", label="营口市 (近代商埠·大辽河口)", zorder=6)
    elif "盘锦" in city:
        ax_chart.plot(cdf['year'], cdf['sum'], color="#8e44ad", lw=1.5, ls="-.", label="盘锦市 (辽河油田·湿地之都)", zorder=6)
    elif "锦州" in city:
        ax_chart.plot(cdf['year'], cdf['sum'], color="#16a085", lw=1.3, ls=":", label="锦州市 (辽西走廊枢纽)", zorder=5)
    else:
        ax_chart.plot(cdf['year'], cdf['sum'], color="#bdc3c7", lw=0.9, alpha=0.7, zorder=3)

ax_chart.set_xlabel("统计年份 (1986—2024年)", fontsize=8.5, color="#2c3e50")
ax_chart.set_ylabel("夜间灯光总辐射累积值 (DN总和)", fontsize=8.5, color="#2c3e50")
ax_chart.set_title("辽宁省14地市夜间灯光辐射时序跃迁 (1986—2024)", fontsize=10.0, fontweight="bold", color="#1a5276")
ax_chart.grid(True, linestyle=":", alpha=0.5)
ax_chart.legend(loc="upper left", fontsize=7.2, frameon=True, facecolor="white", framealpha=0.9)
ax_chart.tick_params(labelsize=7.5)

ln_prov.plot(ax=ax_map, facecolor="#f4f6f7", edgecolor="#7f8c8d", lw=0.6, zorder=2)
gpd.GeoSeries([ln_union], crs=ALBERS).boundary.plot(ax=ax_map, color="#1a5276", lw=1.4, zorder=6)

ax_map.set_xlim(ax_xlim)
ax_map.set_ylim(ax_ylim)
ax_map.axis("off")
ax_map.set_title("沈大“双核驱动”夜间灯光空间辐射热力格局", fontsize=10.0, fontweight="bold", color="#1a5276")

heat_spots = [
    (123.450, 41.750, 45000, "#c0392b", "沈阳极核"),
    (121.620, 39.000, 42000, "#2980b9", "大连极核"),
    (122.980, 41.120, 22000, "#d35400", "鞍山核心"),
    (123.950, 41.870, 18000, "#e67e22", "抚顺核心"),
    (123.750, 41.300, 16000, "#f39c12", "本溪核心"),
    (122.150, 40.350, 22000, "#27ae60", "营口港城"),
    (122.050, 41.150, 20000, "#8e44ad", "盘锦核心"),
    (121.150, 41.100, 19000, "#16a085", "锦州核心"),
    (124.350, 40.050, 18000, "#2ecc71", "丹东口岸")
]

for lon, lat, r, col, label in heat_spots:
    hx, hy = to_alb(lon, lat)
    c1 = plt.Circle((hx, hy), r * 1.5, color=col, alpha=0.18, zorder=4)
    c2 = plt.Circle((hx, hy), r * 0.8, color=col, alpha=0.45, zorder=5)
    ax_map.add_patch(c1)
    ax_map.add_patch(c2)

mapkit.add_scalebar(ax_map, 0.60, 0.05, length_km=80)
ax_map.annotate("N", xy=(0.93, 0.93), xytext=(0.93, 0.87), transform=ax_map.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=1.5, headwidth=4.5, headlength=5.5),
                ha="center", va="center", fontsize=7.8, fontweight="bold", color="#2c3e50", zorder=30)

fig.text(0.018, 0.968, "图 05-00-4", fontsize=9.2, fontweight="bold", color="#1a5276")
fig.suptitle("辽宁省1986—2024年夜间灯光演变与沈大双核经济带图", fontsize=11.5, fontweight="bold", color="#1a5276", y=0.975)
fig.text(0.985, 0.015, "数据源：公开遥感夜间灯光时间序列 · 统计处理：中国地理知识手册工作组",
         fontsize=6.5, color="#7f8c8d", ha="right")

fig4_path = os.path.join(OUT_DIR, "fig05-00-4_辽宁省1986—2024年夜间灯光演变与沈大双核经济带图.png")
fig.savefig(fig4_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"Map 4 saved: {fig4_path}")

# =============================================================================
# 图 05-00-5：辽宁省生态安全屏障与大辽河水系海洋生态图
# =============================================================================
print("Generating Fig 05-00-5 (Ecological Security & Hydrology)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

ln_prov.plot(ax=ax, facecolor="#f2f9f1", edgecolor="#a3e4d7", lw=0.6, zorder=2)
gpd.GeoSeries([ln_union], crs=ALBERS).boundary.plot(ax=ax, color="#1e8449", lw=1.5, zorder=6)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl5 = mapkit.SymbolLabels(ax, fig)
sl5.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.48, 0.0, 1.0, 0.09),
             (0.90, 0.84, 1.0, 1.0)])

eco_nodes = [
    ("大伙房水库水源涵养区 (全省七大城市生命水塔)", 124.150, 41.890, "water", "总库容22亿立方米·辽宁供水压舱石"),
    ("盘锦辽河口国家级自然保护区 (红海滩湿地)", 121.750, 40.850, "wetland", "黑嘴鸥之乡·全球斑海豹产仔繁殖地"),
    ("鸭绿江口湿地国家级自然保护区 (候鸟驿站)", 124.200, 39.850, "wetland", "东亚候鸟数百万鸻鹬类北迁关键停歇地"),
    ("大连蛇岛老铁山国家级自然保护区", 121.150, 38.730, "nature", "蛇岛蝮蛇孤岛演化奇观·猛禽过海中枢"),
    ("彰武三北防护林治沙示范区 (固沙丰碑)", 122.500, 42.450, "forest", "科尔沁沙地南缘绿色长城筑牢屏障"),
    ("桓仁水库与浑江水源生态涵养区", 125.400, 41.200, "water", "辽东茂密林海涵养水源·水质常年I类"),
    ("清河水库生态自然区 (铁岭北部屏障)", 124.220, 42.560, "water", "辽北平原防洪蓄水生态涵养大肾"),
    ("白石水库水生态保护区 (辽西大水库)", 120.950, 41.700, "water", "大凌河中游控制性水利水生态枢纽"),
    ("长白山余脉森林生态安全屏障 (辽东林海)", 124.800, 41.600, "forest", "全省森林覆盖率最高区域·天然水库"),
    ("努鲁儿虎山-医巫闾山水土保持生态带", 121.200, 41.800, "forest", "辽西半干旱过渡带防风固沙保土带"),
    ("渤海辽东湾海洋生态红线保护区", 121.500, 40.500, "sea", "对虾海参海蜇产卵场·重要渔业水域"),
    ("黄海北部海洋生态与长山群岛保护区", 122.800, 39.300, "sea", "国家级海洋牧场示范区·深远海冷水养殖")
]

for name, lon, lat, k, desc in eco_nodes:
    x, y = to_alb(lon, lat)
    m = "o" if k in ["water", "sea"] else ("s" if k == "wetland" else "^")
    c = "#1f618d" if k == "water" else ("#27ae60" if k == "wetland" else ("#196f3d" if k == "forest" else "#117864"))
    sl5.add(x, y, name, k, note=desc, priority=1, marker=m, face=c, size=6.8,
            kind_label="特大型水库 / 饮用水源地" if k == "water" else ("国家级滨海湿地保护区" if k == "wetland" else ("森林生态屏障 / 治沙示范区" if k == "forest" else "海洋生态保护区")))

rivers_data = [
    ([(123.650, 42.800), (123.500, 42.200), (122.950, 41.700), (122.200, 41.100), (121.950, 41.050), (121.750, 40.850)], "#2980b9", 2.2),
    ([(124.800, 41.950), (124.150, 41.890), (123.900, 41.870), (123.400, 41.750), (122.500, 41.350), (122.300, 41.000)], "#3498db", 1.8),
    ([(124.600, 41.250), (123.850, 41.300), (123.180, 41.260), (122.700, 41.100), (122.250, 40.800)], "#3498db", 1.8),
    ([(125.100, 41.000), (124.700, 40.500), (124.450, 40.150), (124.250, 39.800)], "#16a085", 2.2),
    ([(119.500, 41.200), (120.400, 41.600), (120.950, 41.700), (121.350, 41.250), (121.800, 40.950)], "#2980b9", 1.8)
]

for r_pts, r_col, r_lw in rivers_data:
    r_alb = [to_alb(p[0], p[1]) for p in r_pts]
    r_xs, r_ys = zip(*r_alb)
    ax.plot(r_xs, r_ys, color=r_col, lw=r_lw, zorder=5, alpha=0.85)

sym_type_h, sym_idx_h = sl5.flush()

sb_x0 = ax_xlim[0] + span_x * 0.52
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=80)
add_compass(ax, 0.94, 0.91)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="生态与水源涵养格局", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="生态保护区编号对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("辽宁省生态安全屏障与大辽河水系海洋生态图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Ecological Security Barriers & Hydrological River-Lake-Ocean Ecosystems of Liaoning",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：生态环境部·水利部国家重要湿地名录 · 投影：Albers 等积圆锥 (中央经线 105°E) · 制作：《中国地理知识手册》",
    fontsize=6.5)

m5_path = os.path.join(OUT_DIR, "fig05-00-5_辽宁省生态安全屏障与大辽河水系海洋生态图.png")
fig.savefig(m5_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"Map 5 saved: {m5_path}")

print("\n=== ALL 5 LIAONING OVERVIEW MAPS GENERATED SUCCESSFULLY ===")
