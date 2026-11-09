# -*- coding: utf-8 -*-
"""吉林省地理统揽专题地图生成引擎（06-00）
包含 5 幅全省权威出版级地图与分析图表（精细调优排版、微缩字号、严格杜绝压盖）：
1. fig06-00-1_吉林省地形地貌与“东林中农西草”三带格局图.png
2. fig06-00-2_吉林省行政区划与“一主六双”城镇空间格局图.png
3. fig06-00-3_吉林省综合立体交通网与图们江出海大通道图.png
4. fig06-00-4_吉林省1986—2024年夜间灯光演变与长春首位度演进图.png
5. fig06-00-5_吉林省生态安全屏障与松花江图们江水系图.png
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

def add_scalebar(ax, x0, y0, length_km=100):
    mapkit.add_scalebar(ax, x0, y0, length_km=length_km)

def add_compass(ax, x=0.94, y=0.92):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.055), transform=ax.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=1.8, headwidth=5.5, headlength=6.5),
                ha="center", va="center", fontsize=8.8, fontweight="bold", color="#2c3e50", zorder=30)

print("Loading Jilin provincial boundaries and DEM...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

jl_prov = gpd.read_file(os.path.join(DATAV_DIR, "220000_full.json")).to_crs(ALBERS)
jl_prov["geometry"] = jl_prov.geometry.buffer(0)
jl_union = jl_prov.union_all()

b = jl_prov.total_bounds
span_x = b[2] - b[0]
span_y = b[3] - b[1]
pad_x = span_x * 0.04
pad_y = span_y * 0.04
ax_xlim = (b[0] - pad_x, b[2] + pad_x)
ax_ylim = (b[1] - pad_y, b[3] + pad_y)

# 加载 DEM
dem_file = os.path.join(DATA_DIR, "dem", "province", "220000_z9.npz")
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
norm = Normalize(vmin=5.0, vmax=2691.0)

terrain_colors = [
    (0.00, "#196f3d"),   # 5m 图们江出海口与松嫩低平原
    (0.06, "#27ae60"),   # 150m 松辽平原黑土地核心
    (0.14, "#7dcea0"),   # 350m 平原向台地丘陵过渡带
    (0.24, "#f9e79f"),   # 600m 大黑山/吉林哈达岭低山
    (0.42, "#eb984e"),   # 1000m 老岭/龙岗山脉中山林区
    (0.60, "#dc7633"),   # 1500m 长白山暗针叶林带
    (0.78, "#ba4a00"),   # 2000m 岳桦林亚高山带
    (0.90, "#8e44ad"),   # 2400m 高山苔原与火山锥体
    (1.00, "#ffffff")    # 2691m 白云峰天池之巅
]
terrain_cmap = LinearSegmentedColormap.from_list("jl_dem", terrain_colors)
dem_rgb = terrain_cmap(norm(dem_raw))[:, :, :3]
shaded_rgb = dem_rgb * (0.42 + 0.58 * hs[:, :, np.newaxis])

FIGSIZE = (9.8, 7.5)

# =============================================================================
# 图 06-00-1：吉林省地形地貌与“东林中农西草”三带格局图
# =============================================================================
print("Generating Fig 06-00-1 (Topography)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

im = ax.imshow(shaded_rgb, extent=extent, origin="upper", zorder=2)
patch = get_mpl_clip_patch(jl_union)
ax.add_patch(patch)
im.set_clip_path(patch)

jl_prov.boundary.plot(ax=ax, color="#2c3e50", lw=0.6, ls="--", zorder=5)
gpd.GeoSeries([jl_union], crs=ALBERS).boundary.plot(ax=ax, color="#1a5276", lw=1.5, zorder=6)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl1 = mapkit.SymbolLabels(ax, fig)
sl1.reserve([(0.0, 0.0, 0.36, 0.30),
             (0.48, 0.0, 1.0, 0.09),
             (0.90, 0.84, 1.0, 1.0)])

peaks_data = [
    ("白云峰 (2691m 东北第一高峰·长白山主峰)", 128.060, 42.025, "peak", "休眠火山锥体·天池十六峰之首"),
    ("天文峰 (2670m 天池气象台名峰)", 128.080, 42.035, "mt", "长白山北坡天池观景制高点"),
    ("老岭峰 (1589m 通化集安最高峰)", 126.120, 41.350, "mt", "长白山余脉南部高耸屏障"),
    ("南楼山 (1404.8m 吉林市最高峰·北大湖之巅)", 126.620, 43.430, "mt", "亚洲最大滑雪场北大湖垂直雪道依托"),
    ("大顶子山 (711m 长春市最高峰)", 125.850, 43.420, "mt", "长春南部低山林区生态氧吧"),
    ("大寒楼山 (680m 辽源最高峰)", 125.680, 42.620, "mt", "吉林哈达岭南延主峰"),
    ("白石头山 (662m 白城最高峰·大兴安岭余脉)", 122.350, 45.850, "mt", "大兴安岭向松嫩平原过渡山体"),
    ("下看台山 (532m 四平最高峰)", 125.420, 43.280, "mt", "伊通火山群外围低山"),
    ("大金山 (282m 松原最高峰)", 123.850, 44.150, "mt", "松辽分水岭微隆起高岗"),
    ("防川图们江口 (5m 吉林省陆地最低洼点)", 130.650, 42.420, "coast", "中朝俄三国接壤·距日本海仅15公里")
]

for name, lon, lat, ptype, note in peaks_data:
    px, py = to_alb(lon, lat)
    m = "^" if ptype in ["peak", "mt"] else "o"
    c = "#78281f" if ptype == "peak" else ("#ba4a00" if ptype == "mt" else "#1b4f72")
    sl1.add(px, py, name, ptype, note=note, priority=1, marker=m, face=c, size=6.8,
            kind_label="东北第一峰 / 著名名山" if ptype in ["peak", "mt"] else "边境河口 / 最低洼地基准")

waters_data = [
    ("长白山天池 (世界最高火山口湖/三江之源)", 128.055, 42.010, "water", "松花江/鸭绿江/图们江发源地"),
    ("第二松花江干流 (横贯吉林省中部生命之水)", 126.500, 43.900, "water", "水能充沛·滋润吉林长春沃野"),
    ("图们江干流 (中朝界河东入日本海)", 129.900, 42.850, "water", "全省东向开放面向东北亚大走廊"),
    ("鸭绿江上游 (中朝界河西入黄海)", 127.300, 41.500, "water", "长白山南麓清澈界江"),
    ("嫩江干流 (吉黑界河汇入松花江)", 124.250, 45.600, "water", "全省西部湿地之母"),
    ("查干湖 (全国十大淡水湖/冰湖腾鱼冬捕)", 124.280, 45.250, "water", "面积420km²·国家级自然保护区"),
    ("松花湖 (丰满水电站高峡平湖)", 126.650, 43.700, "water", "总库容超百亿立方米·人工生态明珠"),
    ("向海湿地 (丹顶鹤家园/国际重要湿地)", 122.350, 44.980, "water", "沙丘榆树沼泽水鸟四位一体奇绝")
]

for wname, wlon, wlat, wtype, wnote in waters_data:
    wx, wy = to_alb(wlon, wlat)
    sl1.add(wx, wy, wname, wtype, note=wnote, priority=2, marker="o", face="#1f618d", size=6.0,
            kind_label="江河干流 / 高原圣湖与生态湿地")

sym_type_h, sym_idx_h = sl1.flush()

sb_x0 = ax_xlim[0] + span_x * 0.52
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=100)
add_compass(ax, 0.94, 0.91)

cax = ax.inset_axes([0.04, 0.06, 0.024, 0.22])
cb = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=terrain_cmap), cax=cax, orientation="vertical")
cb.set_label("高程 Elevation (m)", fontsize=6.8, color="#2c3e50")
cb.ax.tick_params(labelsize=6.0, length=2.0)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="地形与水系要素", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="图上要素编号对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("吉林省地形地貌与“东林中农西草”三带格局图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Geomorphology, Mountain Chains & Eco-Agricultural Belts of Jilin Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：AWS Terrain GLO-30 DEM · 投影：Albers 等积圆锥 (中央经线 105°E) · 制作：《中国地理知识手册》",
    fontsize=6.5)

m1_path = os.path.join(OUT_DIR, "fig06-00-1_吉林省地形地貌与“东林中农西草”三带格局图.png")
fig.savefig(m1_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"Map 1 saved: {m1_path}")

# =============================================================================
# 图 06-00-2：吉林省行政区划与“一主六双”城镇空间格局图
# =============================================================================
print("Generating Fig 06-00-2 (Administrative & Urban Hierarchy)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

palette = [
    "#ebf5fb", "#e8f8f5", "#fef9e7", "#fdf2e9", "#f4ecf7",
    "#eafaf1", "#f5eef8", "#e8f6f3", "#fef5e7"
]

for i, (_, row) in enumerate(jl_prov.iterrows()):
    color = palette[i % len(palette)]
    gpd.GeoSeries([row.geometry], crs=ALBERS).plot(ax=ax, facecolor=color, edgecolor="#7f8c8d", lw=0.6, zorder=3)

gpd.GeoSeries([jl_union], crs=ALBERS).boundary.plot(ax=ax, color="#1a5276", lw=1.6, zorder=6)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl2 = mapkit.SymbolLabels(ax, fig)
sl2.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.48, 0.0, 1.0, 0.09),
             (0.90, 0.84, 1.0, 1.0)])

admin_centers = [
    ("长春市 (省会 · 副省级特大城市 · 汽车城)", 125.324, 43.886, "core", "吉林省政治经济科创文化中心·长春都市圈核心极"),
    ("吉林市 (中国唯一省市同名城市 · 雾凇之都)", 126.550, 43.840, "sub", "现代化工基地·世界级冰雪旅游胜地"),
    ("四平市 (英雄城 · 黄金玉米带腹心)", 124.380, 43.170, "node", "现代农机装备与换热设备制造基地"),
    ("辽源市 (百年煤城转型 · 中国棉袜之乡)", 125.140, 42.900, "node", "东辽河源头·高端高精铝型材基地"),
    ("通化市 (长白山南部门户 · 中国医药城)", 125.940, 41.730, "node", "中国葡萄酒发祥地·现代医药与新材料"),
    ("白山市 (长白山核心腹地 · 矿泉水之乡)", 126.420, 41.940, "node", "长白山西坡·人参集散中心与绿色硅藻土"),
    ("松原市 (查干湖冬捕 · 吉林油田大本营)", 124.820, 45.140, "node", "松嫩两江汇流·绿色农畜产品供给基地"),
    ("白城市 (绿氢之都 · 风光绿电综合基地)", 122.840, 45.620, "node", "嫩江右岸·千亿级氢氨醇新能源基地"),
    ("延边朝鲜族自治州 (延吉市 · 边境门户)", 129.510, 42.900, "sub", "长白山主峰天池坐落地·防川一眼望三国")
]

for name, lon, lat, ctype, note in admin_centers:
    cx, cy = to_alb(lon, lat)
    m = "*" if ctype == "core" else ("D" if ctype == "sub" else "s")
    c = "#78281f" if ctype == "core" else ("#1b4f72" if ctype == "sub" else "#935116")
    sz = 9.0 if ctype == "core" else (7.2 if ctype == "sub" else 6.2)
    sl2.add(cx, cy, name, ctype, note=note, priority=1, marker=m, face=c, size=sz,
            kind_label="省会特大城市 / 核心极核" if ctype == "core" else ("副中心城市 / 自治州府" if ctype == "sub" else "地级市行政中心"))

sym_type_h, sym_idx_h = sl2.flush()

sb_x0 = ax_xlim[0] + span_x * 0.52
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=100)
add_compass(ax, 0.94, 0.91)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="城市等级与空间节点", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="行政中心编号对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("吉林省行政区划与“一主六双”城镇空间格局图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Administrative Divisions & 'One Core, Six Double' Urban Pattern of Jilin Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：自然资源部标准地图服务 · 投影：Albers 等积圆锥 (中央经线 105°E) · 制作：《中国地理知识手册》",
    fontsize=6.5)

m2_path = os.path.join(OUT_DIR, "fig06-00-2_吉林省行政区划与“一主六双”城镇空间格局图.png")
fig.savefig(m2_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"Map 2 saved: {m2_path}")

# =============================================================================
# 图 06-00-3：吉林省综合立体交通网与图们江出海大通道图
# =============================================================================
print("Generating Fig 06-00-3 (Comprehensive Transportation)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

jl_prov.plot(ax=ax, facecolor="#f8f9fa", edgecolor="#bdc3c7", lw=0.6, zorder=2)
gpd.GeoSeries([jl_union], crs=ALBERS).boundary.plot(ax=ax, color="#2c3e50", lw=1.5, zorder=6)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl3 = mapkit.SymbolLabels(ax, fig)
sl3.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.48, 0.0, 1.0, 0.09),
             (0.90, 0.84, 1.0, 1.0)])

# 绘制高铁与干线铁路
corridors_lines = [
    # 哈大高铁 (四平-公主岭-长春-扶余)
    ([(124.460, 43.150), (124.820, 43.500), (125.190, 43.865), (125.320, 43.910), (126.020, 45.050)], "#c0392b", 2.4),
    # 长珲城际客专 (长春-九台-吉林-蛟河-敦化-安图-延吉-图们-珲春)
    ([(125.320, 43.910), (125.840, 44.150), (126.575, 43.870), (127.340, 43.720), (128.220, 43.380), (128.900, 43.110), (129.450, 42.920), (129.840, 42.960), (130.340, 42.880)], "#c0392b", 2.4),
    # 敦白客运专线 (敦化-二道白河长白山站)
    ([(128.220, 43.380), (128.280, 43.080), (128.210, 42.750), (128.150, 42.420)], "#c0392b", 2.0),
    # 长白客专 (长春-农安-松原-大安-白城)
    ([(125.320, 43.910), (125.180, 44.430), (124.845, 45.135), (124.280, 45.510), (122.835, 45.625)], "#e67e22", 2.0),
    # 京哈高速 G1
    ([(124.420, 43.250), (125.150, 43.800), (125.700, 44.530)], "#2980b9", 1.8),
    # 珲乌高速 G12 (白城-松原-长春-吉林-敦化-延吉-珲春)
    ([(122.840, 45.620), (124.900, 45.150), (125.400, 44.050), (126.500, 43.950), (128.220, 43.380), (129.510, 42.900), (130.360, 42.860)], "#27ae60", 1.8)
]

for pts, lcolor, lw in corridors_lines:
    alb_pts = [to_alb(p[0], p[1]) for p in pts]
    xs, ys = mapkit.smooth_line(alb_pts)
    ax.plot(xs, ys, color=lcolor, lw=lw, zorder=5, alpha=0.88)
    ax.plot(xs, ys, color="#ffffff", lw=lw * 0.4, ls="--", zorder=6)

transport_nodes = [
    ("长春龙嘉国际机场 (4E级区域门户空铁联运)", 125.685, 43.996, "air", "东北干线枢纽机场/长吉城际直通航站楼"),
    ("延吉朝阳川国际机场 (4D级对韩国际航空口岸)", 129.450, 42.880, "air", "直通首尔釜山等东北亚重点航线"),
    ("长白山机场 (全国首个森林生态旅游机场)", 127.610, 42.070, "air", "直达长白山西坡与天池旅游度假区"),
    ("长春西站 (京哈高铁特等客运站)", 125.190, 43.865, "rail", "东北高寒高速铁路骨干十字中枢"),
    ("吉林站 (长吉城际与长珲高铁核心大站)", 126.575, 43.870, "rail", "松花江畔综合立体客运枢纽"),
    ("延吉西站 (长珲城际高铁重要客站)", 129.450, 42.920, "rail", "延边自治州主客运枢纽中心"),
    ("珲春站 (高铁东北边境最东端终点站)", 130.340, 42.880, "rail", "中俄朝陆路口岸联运交通枢纽"),
    ("四平东站 (哈大高铁吉林南大门)", 124.460, 43.150, "rail", "连接沈阳与长春的高铁枢纽站"),
    ("大安港 (吉林省唯一对外开放内河口岸港)", 124.320, 45.520, "port", "嫩江右岸江海联运综合码头")
]

for name, lon, lat, k, desc in transport_nodes:
    x, y = to_alb(lon, lat)
    m = "^" if k == "air" else ("s" if k == "rail" else "o")
    c = "#8e44ad" if k == "air" else ("#154360" if k == "rail" else "#117864")
    sz = 7.5 if k in ["air", "port"] else 6.5
    sl3.add(x, y, name, k, note=desc, priority=1, marker=m, face=c, size=sz,
            kind_label="民航门户机场" if k == "air" else ("高铁特等客运站 / 枢纽中心" if k == "rail" else "对外开放内河口岸水运港"))

sym_type_h, sym_idx_h = sl3.flush()

sb_x0 = ax_xlim[0] + span_x * 0.52
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=100)
add_compass(ax, 0.94, 0.91)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="交通基础设施要素", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="交通枢纽编号对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("吉林省综合立体交通网与图们江出海大通道图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Comprehensive Transportation Network & Tumen River Maritime Corridors of Jilin",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：中国国家铁路集团·交通运输部·吉林省交通厅 · 投影：Albers 等积圆锥 (中央经线 105°E) · 制作：《中国地理知识手册》",
    fontsize=6.5)

m3_path = os.path.join(OUT_DIR, "fig06-00-3_吉林省综合立体交通网与图们江出海大通道图.png")
fig.savefig(m3_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"Map 3 saved: {m3_path}")

# =============================================================================
# 图 06-00-4：吉林省1986—2024年夜间灯光演变与长春首位度演进图
# =============================================================================
print("Generating Fig 06-00-4 (Nightlight Evolution)...")
nl_clean = pd.read_csv(os.path.join(DATA_DIR, "jilin_nightlight_clean.csv"))

fig, (ax_chart, ax_map) = plt.subplots(1, 2, figsize=(11.5, 6.2), dpi=DPI,
                                       gridspec_kw={'width_ratios': [1.15, 1.0]})
fig.subplots_adjust(left=0.065, right=0.975, top=0.920, bottom=0.090, wspace=0.22)
fig.patch.set_facecolor("white")

nl_prov = nl_clean.groupby(['year', 'city_name'])['sum'].sum().reset_index()

for city in nl_prov['city_name'].unique():
    cdf = nl_prov[nl_prov['city_name'] == city].sort_values('year')
    if "长春" in city:
        ax_chart.plot(cdf['year'], cdf['sum'], color="#c0392b", lw=2.6, label="长春市 (省会极核·高首位度)", zorder=10)
    elif "吉林" in city:
        ax_chart.plot(cdf['year'], cdf['sum'], color="#2980b9", lw=2.0, label="吉林市 (省域副中心·松花江)", zorder=9)
    elif "延边" in city:
        ax_chart.plot(cdf['year'], cdf['sum'], color="#27ae60", lw=1.8, label="延边州 (边境开放·文旅新极)", zorder=8)
    elif "松原" in city:
        ax_chart.plot(cdf['year'], cdf['sum'], color="#8e44ad", lw=1.5, ls="--", label="松原市 (油田石化·查干湖)", zorder=6)
    elif "四平" in city:
        ax_chart.plot(cdf['year'], cdf['sum'], color="#d35400", lw=1.4, ls="-.", label="四平市 (黄金玉米带·英雄城)", zorder=5)
    else:
        ax_chart.plot(cdf['year'], cdf['sum'], color="#bdc3c7", lw=0.9, alpha=0.7, zorder=3)

ax_chart.set_xlabel("统计年份 (1986—2024年)", fontsize=8.5, color="#2c3e50")
ax_chart.set_ylabel("夜间灯光总辐射累积值 (DN总和)", fontsize=8.5, color="#2c3e50")
ax_chart.set_title("吉林省9地市州夜间灯光辐射时序跃迁 (1986—2024)", fontsize=10.0, fontweight="bold", color="#1a5276")
ax_chart.grid(True, linestyle=":", alpha=0.5)
ax_chart.legend(loc="upper left", fontsize=7.2, frameon=True, facecolor="white", framealpha=0.9)
ax_chart.tick_params(labelsize=7.5)

jl_prov.plot(ax=ax_map, facecolor="#f4f6f7", edgecolor="#7f8c8d", lw=0.6, zorder=2)
gpd.GeoSeries([jl_union], crs=ALBERS).boundary.plot(ax=ax_map, color="#1a5276", lw=1.4, zorder=6)

ax_map.set_xlim(ax_xlim)
ax_map.set_ylim(ax_ylim)
ax_map.axis("off")
ax_map.set_title("长春“单核首位凸显·多极并进”夜光空间热性格局", fontsize=10.0, fontweight="bold", color="#1a5276")

heat_spots = [
    (125.324, 43.886, 52000, "#c0392b", "长春极核·一汽高新核心区"),
    (126.550, 43.840, 26000, "#2980b9", "吉林副中心·松花江沿江光带"),
    (129.510, 42.900, 22000, "#27ae60", "延吉核心·朝鲜族文旅夜生活"),
    (124.820, 45.140, 18000, "#8e44ad", "松原主城与吉林油田基地"),
    (124.380, 43.170, 16000, "#d35400", "四平主城铁东铁西开发区"),
    (125.940, 41.730, 14000, "#e67e22", "通化浑江河谷医药高新带"),
    (122.840, 45.620, 15000, "#16a085", "白城主城与绿电化工园区"),
    (130.360, 42.860, 12000, "#117864", "珲春边境口岸与边合区"),
    (126.420, 41.940, 12000, "#f39c12", "白山浑江山城核心带")
]

for lon, lat, r, col, label in heat_spots:
    hx, hy = to_alb(lon, lat)
    c1 = plt.Circle((hx, hy), r * 1.5, color=col, alpha=0.18, zorder=4)
    c2 = plt.Circle((hx, hy), r * 0.8, color=col, alpha=0.45, zorder=5)
    ax_map.add_patch(c1)
    ax_map.add_patch(c2)

mapkit.add_scalebar(ax_map, 0.60, 0.05, length_km=100)
ax_map.annotate("N", xy=(0.93, 0.93), xytext=(0.93, 0.87), transform=ax_map.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=1.5, headwidth=4.5, headlength=5.5),
                ha="center", va="center", fontsize=7.8, fontweight="bold", color="#2c3e50", zorder=30)

fig.text(0.018, 0.968, "图 06-00-4", fontsize=9.2, fontweight="bold", color="#1a5276")
fig.suptitle("吉林省1986—2024年夜间灯光演变与长春首位度演进图", fontsize=11.5, fontweight="bold", color="#1a5276", y=0.975)
fig.text(0.985, 0.015, "数据源：公开遥感夜间灯光时间序列 · 统计处理：中国地理知识手册工作组",
         fontsize=6.5, color="#7f8c8d", ha="right")

fig4_path = os.path.join(OUT_DIR, "fig06-00-4_吉林省1986—2024年夜间灯光演变与长春首位度演进图.png")
fig.savefig(fig4_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"Map 4 saved: {fig4_path}")

# =============================================================================
# 图 06-00-5：吉林省生态安全屏障与松花江图们江水系图
# =============================================================================
print("Generating Fig 06-00-5 (Ecological Security & Hydrology)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

jl_prov.plot(ax=ax, facecolor="#f2f9f1", edgecolor="#a3e4d7", lw=0.6, zorder=2)
gpd.GeoSeries([jl_union], crs=ALBERS).boundary.plot(ax=ax, color="#1e8449", lw=1.5, zorder=6)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl5 = mapkit.SymbolLabels(ax, fig)
sl5.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.48, 0.0, 1.0, 0.09),
             (0.90, 0.84, 1.0, 1.0)])

eco_nodes = [
    ("东北虎豹国家公园核心区 (野生虎豹栖息乐园)", 129.850, 43.400, "nature", "横跨吉黑两省·中俄边境野生东北虎繁衍核心地"),
    ("长白山国家级自然保护区 (欧亚大陆森林生态标杆)", 128.055, 42.020, "nature", "完整垂直景观带·温带原始红松针阔混交林"),
    ("查干湖国家级自然保护区 (圣水湖鸟类天堂)", 124.260, 45.260, "wetland", "全国十大淡水湖·珍稀水禽繁殖栖息生态明珠"),
    ("向海国家级自然保护区 (国际重要湿地)", 122.320, 44.980, "wetland", "引嫩入白关键节点·丹顶鹤重要繁育庇护所"),
    ("莫莫格国家级自然保护区 (白鹤之乡)", 123.620, 45.920, "wetland", "全球90%以上白鹤迁徙必经生态停歇驿站"),
    ("松花湖国家重点风景名胜区 (水利水源保护)", 126.680, 43.680, "water", "总库容超百亿立方米·吉林长春重要水塔"),
    ("大安嫩江湾国家湿地公园 (千里嫩江第一湾)", 124.320, 45.520, "wetland", "嫩江右岸江滩湿地与生态涵养防护林带"),
    ("吉林龙湾群国家森林公园 (火山火山口湖群)", 126.430, 42.360, "nature", "世界罕见火山口湖群·水质清澈无污染"),
    ("东辽河源头生态涵养保护区", 125.400, 42.750, "forest", "东辽河发源地·辽河水系上游森林生态屏障"),
    ("长白山高山苔原生态保护红线区", 128.080, 42.060, "nature", "第四纪冰川孑遗植物物种基因库")
]

for name, lon, lat, k, desc in eco_nodes:
    x, y = to_alb(lon, lat)
    m = "o" if k == "water" else ("s" if k == "wetland" else ("^" if k == "nature" else "D"))
    c = "#1f618d" if k == "water" else ("#27ae60" if k == "wetland" else ("#196f3d" if k == "nature" else "#117864"))
    sl5.add(x, y, name, k, note=desc, priority=1, marker=m, face=c, size=6.8,
            kind_label="特大型水库 / 饮用水源地" if k == "water" else ("国家级湖泊湿地保护区" if k == "wetland" else "国家公园 / 自然生态保护区"))

rivers_data = [
    ([(128.055, 42.010), (127.500, 42.800), (126.650, 43.700), (126.500, 43.900), (125.200, 45.420)], "#2980b9", 2.2), # 松花江
    ([(128.055, 42.010), (129.500, 42.800), (130.000, 42.700), (130.650, 42.420)], "#16a085", 2.0), # 图们江
    ([(128.055, 42.010), (127.500, 41.600), (126.150, 41.100)], "#3498db", 2.0), # 鸭绿江
    ([(123.800, 46.200), (124.250, 45.650), (125.200, 45.420)], "#2980b9", 2.0), # 嫩江
    ([(125.300, 42.800), (124.800, 43.100), (123.600, 43.480)], "#8e44ad", 1.8)  # 东辽河
]

for r_pts, r_col, r_lw in rivers_data:
    r_alb = [to_alb(p[0], p[1]) for p in r_pts]
    r_xs, r_ys = zip(*r_alb)
    ax.plot(r_xs, r_ys, color=r_col, lw=r_lw, zorder=5, alpha=0.85)

sym_type_h, sym_idx_h = sl5.flush()

sb_x0 = ax_xlim[0] + span_x * 0.52
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=100)
add_compass(ax, 0.94, 0.91)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="生态与水源涵养格局", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="生态保护区编号对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("吉林省生态安全屏障与松花江图们江水系图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Ecological Security Barriers & River-Lake Basin Ecosystems of Jilin Province",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：生态环境部·国家公园管理局·水利部 · 投影：Albers 等积圆锥 (中央经线 105°E) · 制作：《中国地理知识手册》",
    fontsize=6.5)

m5_path = os.path.join(OUT_DIR, "fig06-00-5_吉林省生态安全屏障与松花江图们江水系图.png")
fig.savefig(m5_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"Map 5 saved: {m5_path}")

print("\n=== ALL 5 JILIN OVERVIEW MAPS GENERATED SUCCESSFULLY ===")
