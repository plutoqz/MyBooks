# -*- coding: utf-8 -*-
"""上海市地理统揽专题地图生成引擎（09-00）
包含 5 幅全市权威出版级地图与分析图表（精细调优排版、微缩字号、严格杜绝压盖）：
1. fig09-00-1_上海市地势水文与长江河口宏观格局图.png
2. fig09-00-2_上海市行政区划与“中心辐射·两翼齐飞·新城发力·南北转型”空间格局图.png
3. fig09-00-3_上海市综合立体交通与海空枢纽网络图.png
4. fig09-00-4_上海市“五个中心”与高能级产业空间格局图.png
5. fig09-00-5_上海市1986—2024年夜间灯光演变与长三角一体化辐射图.png
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
    # 填充 NaN 以免梯度崩溃
    d = np.nan_to_num(dem, nan=0.0)
    gy, gx = np.gradient(d, res)
    slope = np.arctan(np.sqrt(gx * gx + gy * gy))
    aspect = np.arctan2(-gx, gy)
    shaded = np.sin(alt_rad) * np.cos(slope) + np.cos(alt_rad) * np.sin(slope) * np.cos(az_rad - aspect)
    return np.clip(shaded, 0.0, 1.0)

def add_scalebar(ax, x0, y0, length_km=30):
    mapkit.add_scalebar(ax, x0, y0, length_km=length_km)

def add_compass(ax, x=0.94, y=0.92):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.055), transform=ax.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=1.8, headwidth=5.5, headlength=6.5),
                ha="center", va="center", fontsize=8.8, fontweight="bold", color="#2c3e50", zorder=30)

print("Loading Shanghai municipal boundaries and DEM...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

sh_prov = gpd.read_file(os.path.join(DATAV_DIR, "310000_full.json")).to_crs(ALBERS)
sh_prov["geometry"] = sh_prov.geometry.buffer(0)
sh_union = sh_prov.union_all()

b = sh_prov.total_bounds
span_x = b[2] - b[0]
span_y = b[3] - b[1]
pad_x = span_x * 0.06
pad_y = span_y * 0.06
ax_xlim = (b[0] - pad_x, b[2] + pad_x)
ax_ylim = (b[1] - pad_y, b[3] + pad_y)

# 加载 DEM
dem_file = os.path.join(DATA_DIR, "dem", "province", "310000_z9.npz")
dem_data = np.load(dem_file)
dem_raw = np.nan_to_num(dem_data['dem'], nan=0.0)
dem_res = float(dem_data['res'])
dem_minx = float(dem_data['minx'])
dem_maxy = float(dem_data['maxy'])
print(f"Loaded Shanghai DEM shape: {dem_raw.shape}, res: {dem_res}m")

extent = (dem_minx, dem_minx + dem_raw.shape[1] * dem_res,
          dem_maxy - dem_raw.shape[0] * dem_res, dem_maxy)

hs = calc_hillshade(dem_raw, dem_res)
norm = Normalize(vmin=0.0, vmax=105.0)

# 上海微地貌精细分层色标 (0m-105m)
terrain_colors = [
    (0.00, "#196f3d"),   # 0m-2m 沿海潮间带、滨海滩涂与河口湿地
    (0.03, "#27ae60"),   # 3m-4m 广大水网冲积平原主体
    (0.08, "#52be80"),   # 5m-8m 沿江河堤防、古冈身带 (沙冈高地)
    (0.18, "#a9dfbf"),   # 10m-20m 冈身台地与近山缓坡
    (0.35, "#f9e79f"),   # 20m-40m 残丘低岗基底
    (0.60, "#eb984e"),   # 40m-70m 辰山、东佘山残丘
    (0.85, "#ba4a00"),   # 70m-95m 天马山、西佘山基岩山峰
    (1.00, "#78281f")    # 100m-103.7m 大金山岛峰顶 (全境最高自然极点)
]
terrain_cmap = LinearSegmentedColormap.from_list("sh_dem", terrain_colors)
dem_rgb = terrain_cmap(norm(dem_raw))[:, :, :3]
shaded_rgb = dem_rgb * (0.46 + 0.54 * hs[:, :, np.newaxis])

FIGSIZE = (9.8, 8.8)

# =============================================================================
# 图 09-00-1：上海市地势水文与长江河口宏观格局图
# =============================================================================
print("Generating Fig 09-00-1 (Topography & Hydrology)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

im = ax.imshow(shaded_rgb, extent=extent, origin="upper", zorder=2)
patch = get_mpl_clip_patch(sh_union)
ax.add_patch(patch)
im.set_clip_path(patch)

sh_prov.boundary.plot(ax=ax, color="#2c3e50", lw=0.6, ls="--", zorder=5)
gpd.GeoSeries([sh_union], crs=ALBERS).boundary.plot(ax=ax, color="#1a5276", lw=1.5, zorder=6)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl1 = mapkit.SymbolLabels(ax, fig)
sl1.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.50, 0.0, 1.0, 0.09),
             (0.88, 0.86, 1.0, 1.0)])

peaks_data = [
    ("大金山岛顶峰 (103.7m 杭州湾海岛·上海自然最高点)", 121.417, 30.692, "peak", "杭州湾海岛·全境自然海拔极顶"),
    ("西佘山 (100.8m 上海陆地天然最高峰·天文台)", 121.192, 31.096, "peak", "陆地最高自然峰·佘山天文台与天主教堂"),
    ("天马山 (99.8m 九峰三泖第二高峰·斜塔)", 121.149, 31.077, "mt", "九峰最高残丘·护珠塔倾斜度超比萨"),
    ("东佘山 (72.4m 松竹掩映国家森林公园)", 121.215, 31.097, "mt", "云间九峰名山·林木繁茂"),
    ("辰山 (71.4m 辰山植物园矿坑花园)", 121.182, 31.080, "mt", "亚洲顶尖植物园·生态修复典范"),
    ("小昆山 (54.3m 陆机陆云二陆故里)", 121.115, 31.050, "mt", "西晋文学家陆机《平复帖》渊源"),
    ("小金山岛 (50.5m 杭州湾岛屿群)", 121.442, 30.697, "mt", "金山三岛海洋生态保护区"),
    ("上海中心大厦 (632m 城市垂直巅峰·中国第一高楼)", 121.505, 31.233, "tower", "现代垂直天际线极核·世界第二高楼")
]

for name, lon, lat, ptype, desc in peaks_data:
    px, py = to_alb(lon, lat)
    m = "*" if ptype == "peak" else ("D" if ptype == "tower" else "^")
    fc = "#c0392b" if ptype == "peak" else ("#8e44ad" if ptype == "tower" else "#922b21")
    sl1.add(px, py, name, ptype, note=desc, priority=0 if ptype in ("peak", "tower") else 1,
            marker=m, face=fc, size=7.2 if ptype in ("peak", "tower") else 5.2, kind_label="地貌控制性极点与天际地标")

waters_data = [
    ("长江口南支 (主航道·通江达海黄金水道)", 121.650, 31.450, "water", "长江巨流汇入东海主干道"),
    ("长江口北支 (中隔崇明与江苏海门相望)", 121.500, 31.750, "water", "长江北部分流通道"),
    ("黄浦江 (贯穿上海主城中心母亲河)", 121.490, 31.240, "water", "太湖水系下游入江主干"),
    ("苏州河/吴淞江 (十八湾流经核心市区)", 121.430, 31.245, "water", "近代民族工商业发祥水道"),
    ("淀山湖 (62km² 上海最大天然淡水湖)", 120.970, 31.110, "water", "水源保护地·长三角一体化生态核心"),
    ("滴水湖 (5.56km² 全球最大城市人工正圆湖)", 121.930, 30.900, "water", "临港新片区中心几何水景"),
    ("金海湖/上海之鱼 (金汇港旁生态景观大湖)", 121.480, 30.910, "water", "奉贤新城城市客厅金鱼水系"),
    ("大治河 (人工开挖横贯浦东东西骨干主航道)", 121.650, 31.020, "water", "浦东大型航运通海运河"),
    ("金汇港 (纵贯奉贤连通黄浦江与杭州湾枢纽)", 121.490, 30.950, "water", "南北骨干水运与排涝总干渠"),
    ("明珠湖 (崇明西部最大天然淡水湖)", 121.115, 31.735, "water", "西沙明珠湖5A景区")
]

for name, lon, lat, wtype, desc in waters_data:
    px, py = to_alb(lon, lat)
    sl1.add(px, py, name, wtype, note=desc, priority=2,
            marker="s", face="#1b4f72", size=4.8, kind_label="骨干江河水系与核心湖泊水库")

sym_type_h, sym_idx_h = sl1.flush()

sb_x0 = ax_xlim[0] + span_x * 0.55
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=30)
add_compass(ax, 0.94, 0.91)

leg1 = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="地形与水系要素分类", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="图上要素编号对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("上海市地势水文与长江河口宏观格局图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Geomorphology, Estuary Hydrology & Landmark Relief of Shanghai Municipality",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg1, "数据源：AWS Terrain 300m 高程 · 投影：Albers 等积圆锥 (中央经线 105°E) · 制作：《中国地理知识手册》",
    fontsize=6.5)

f1_path = os.path.join(OUT_DIR, "fig09-00-1_上海市地势水文与长江河口宏观格局图.png")
fig.savefig(f1_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"✓ Saved Fig 09-00-1: {f1_path}")

# =============================================================================
# 图 09-00-2：上海市行政区划与“中心辐射·两翼齐飞·新城发力·南北转型”空间格局图
# =============================================================================
print("Generating Fig 09-00-2 (Administrative & Spatial Pattern)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

# 空间战略分区底色填涂
# CAZ核心区：黄浦(310101)、徐汇(310104)、长宁(310105)、静安(310106)、普陀(310107)、虹口(310109)、杨浦(310110)
# 战略引领区：浦东新区(310115)
# 五大新城所在区：嘉定(310114)、松江(310117)、青浦(310118)、奉贤(310120)
# 南北转型区：宝山(310113)、金山(310116)
# 近郊高能枢纽区：闵行(310112)
# 生态岛：崇明(310151)
zone_colors = {
    "310101": "#fadbd8", "310104": "#fadbd8", "310105": "#fadbd8", "310106": "#fadbd8",
    "310107": "#fadbd8", "310109": "#fadbd8", "310110": "#fadbd8",
    "310115": "#ebf5fb", # 浦东新区
    "310112": "#fdf2e9", # 闵行
    "310114": "#e8f8f5", "310117": "#e8f8f5", "310118": "#e8f8f5", "310120": "#e8f8f5", # 新城梯队
    "310113": "#f4ecf7", "310116": "#f4ecf7", # 南北转型
    "310151": "#eafaf1"  # 崇明世界级生态岛
}

for i, (_, row) in enumerate(sh_prov.iterrows()):
    ad = str(row.get("adcode", ""))
    fill_col = zone_colors.get(ad, "#ffffff")
    gpd.GeoSeries([row.geometry], crs=ALBERS).plot(ax=ax, facecolor=fill_col, edgecolor="#7f8c8d", lw=0.6, zorder=3)

gpd.GeoSeries([sh_union], crs=ALBERS).boundary.plot(ax=ax, color="#1a5276", lw=1.6, zorder=6)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl2 = mapkit.SymbolLabels(ax, fig)
sl2.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.50, 0.0, 1.0, 0.09),
             (0.88, 0.86, 1.0, 1.0)])

admin_hubs = [
    ("黄浦区 (外滩金融·南京路·老城厢豫园)", 121.485, 31.228, "caz", "CAZ核心·上海城市原点·外滩金融集聚带"),
    ("徐汇区 (徐家汇中心·西岸卓越水岸)", 121.436, 31.188, "caz", "衡复风貌区·西岸数智中心·AI与生命健康"),
    ("静安区 (南京西路商圈·静安寺·苏河湾)", 121.448, 31.229, "caz", "高端商务总部门户·张园城市更新样本"),
    ("长宁区 (虹桥国际开放枢纽门户·新华路)", 121.421, 31.220, "caz", "数字长宁·涉外高端居住区·东虹桥片区"),
    ("普陀区 (苏河十八湾·真如副中心)", 121.397, 31.249, "caz", "武宁科创轴·桃浦智创城·网络安全基地"),
    ("虹口区 (北外滩航运金融中心·鲁迅故里)", 121.505, 31.264, "caz", "新时代顶级中央活动区·世界级会客厅"),
    ("杨浦区 (江湾五角场·杨浦滨江工业秀带)", 121.526, 31.259, "caz", "国家创新型城区·双一流高校集聚群"),
    ("浦东新区 (高水平改革开放社会主义现代化建设引领区)", 121.544, 31.221, "lead", "全省第一经济强区·陆家嘴/张江/临港核心"),
    ("闵行区 (虹桥国际中央商务区·莘庄大枢纽)", 121.381, 31.112, "hub", "国家产城融合典范·南部科创中心"),
    ("嘉定区 (国际汽车城·嘉定新城核心)", 121.265, 31.375, "newtown", "全球著名智能网联新能源汽车高地"),
    ("松江区 (长三角G60科创走廊策源地·松江新城)", 121.228, 31.032, "newtown", "上海之根·松江大学城·先进制造高地"),
    ("青浦区 (长三角一体化示范区·青浦新城)", 121.124, 31.151, "newtown", "华为练秋湖研发中心·国家会展中心四叶草"),
    ("奉贤区 (东方美谷生物医药·奉贤新城)", 121.474, 30.918, "newtown", "中国化妆品之都·上海之鱼生态水轴"),
    ("宝山区 (吴淞创新城·绿色低碳科创转型)", 121.489, 31.405, "trans", "北转型主阵地·宝钢超低碳·高铁宝山站"),
    ("金山区 (上海石化碳谷绿湾·南部滨海转型)", 121.341, 30.742, "trans", "南转型排头兵·大金山海岛·枫泾中国古镇"),
    ("崇明区 (世界级生态岛·长江入海口三岛)", 121.397, 31.626, "eco", "长江口大保护标杆·长兴岛大国重器造船母港")
]

for name, lon, lat, ctype, desc in admin_hubs:
    px, py = to_alb(lon, lat)
    m = "*" if ctype == "lead" else ("s" if ctype == "caz" else ("D" if ctype == "newtown" else "o"))
    fc = "#c0392b" if ctype == "lead" else ("#e74c3c" if ctype == "caz" else ("#27ae60" if ctype == "newtown" else "#8e44ad"))
    sl2.add(px, py, name, ctype, note=desc, priority=0 if ctype in ("lead", "caz") else 1,
            marker=m, face=fc, size=7.2 if ctype == "lead" else 5.2, kind_label="战略分区与市辖区能级")

sym_type_h2, sym_idx_h2 = sl2.flush()

sb_x0 = ax_xlim[0] + span_x * 0.55
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=30)
add_compass(ax, 0.94, 0.91)

leg2 = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h2, title="行政中心与战略功能分区", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h2, title="上海市16市辖区定位简述", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("上海市行政区划与“中心辐射·两翼齐飞·新城发力·南北转型”空间格局图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Administrative Structure & Spatial Strategy of Shanghai Municipality",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg2, "数据源：上海市人民政府标准地名与《上海市国土空间总体规划 (2017-2035年)》 · 制作：《中国地理知识手册》",
    fontsize=6.5)

f2_path = os.path.join(OUT_DIR, "fig09-00-2_上海市行政区划与“中心辐射·两翼齐飞·新城发力·南北转型”空间格局图.png")
fig.savefig(f2_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"✓ Saved Fig 09-00-2: {f2_path}")

# =============================================================================
# 图 09-00-3：上海市综合立体交通与海空枢纽网络图
# =============================================================================
print("Generating Fig 09-00-3 (Transport & Mega Hubs)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

gpd.GeoSeries([sh_union], crs=ALBERS).plot(ax=ax, facecolor="#ffffff", edgecolor="#1a5276", lw=1.6, zorder=2)
sh_prov.boundary.plot(ax=ax, color="#cbd5e0", lw=0.6, ls=":", zorder=3)

# 绘制高铁与城际主要骨干廊道
# 京沪高铁/沪宁城际向西北，沪杭高铁向西南，沪苏湖高铁向西，沿江高铁经崇明向北，金山铁路/沪乍杭向南
rail_lines = [
    # 沪宁/京沪走廊 (虹桥/上海站 -> 昆山/苏州)
    [(121.455, 31.250), (121.320, 31.190), (121.150, 31.280), (120.980, 31.350)],
    # 沪杭走廊 (虹桥 -> 松江 -> 嘉兴)
    [(121.320, 31.190), (121.220, 31.000), (121.050, 30.850), (120.800, 30.750)],
    # 沪苏湖高铁 (松江南 -> 青浦练塘 -> 湖州)
    [(121.220, 30.980), (121.050, 30.980), (120.900, 31.000)],
    # 沪通铁路/沿江高铁 (安亭/宝山 -> 太仓 -> 崇明 -> 启东)
    [(121.489, 31.405), (121.280, 31.380), (121.150, 31.550), (121.405, 31.650), (121.550, 31.800)],
    # 金山铁路市域快线 (上海南站 -> 莘庄 -> 金山卫)
    [(121.430, 31.155), (121.385, 31.110), (121.370, 30.900), (121.340, 30.735)],
    # 机场联络线 (虹桥枢纽 -> 浦东机场 -> 上海东站)
    [(121.320, 31.190), (121.450, 31.130), (121.650, 31.140), (121.800, 31.140), (121.790, 31.150)]
]

for r_pts in rail_lines:
    xs, ys = mapkit.smooth_line([to_alb(p[0], p[1]) for p in r_pts])
    ax.plot(xs, ys, color="#c0392b", lw=2.2, zorder=8, alpha=0.9)

# 绘制高速公路骨干网
# G2/G42沪蓉、G60沪昆、G50沪渝、G15沈海、G1503上海绕城、S2沪芦高速、东海大桥、长江隧桥G40
hwy_lines = [
    # G1503 上海绕城高速大环线
    [(121.30, 31.45), (121.55, 31.38), (121.75, 31.25), (121.85, 31.05), (121.70, 30.88), (121.35, 30.82), (121.10, 31.00), (121.15, 31.35), (121.30, 31.45)],
    # G40 沪陕高速上海段 (跨江隧桥连通崇明)
    [(121.60, 31.28), (121.74, 31.425), (121.78, 31.48), (121.62, 31.55), (121.45, 31.62), (121.30, 31.75)],
    # S2 沪芦高速与东海大桥 (直抵洋山深水港)
    [(121.58, 31.18), (121.75, 31.05), (121.90, 30.90), (121.97, 30.85), (122.06, 30.62)],
    # G60 沪昆高速 (松江廊道)
    [(121.35, 31.12), (121.22, 31.03), (121.05, 30.90)],
    # G50 沪渝高速 (青浦廊道)
    [(121.33, 31.18), (121.15, 31.14), (120.95, 31.08)]
]

for h_pts in hwy_lines:
    xs, ys = mapkit.smooth_line([to_alb(p[0], p[1]) for p in h_pts])
    ax.plot(xs, ys, color="#2980b9", lw=1.6, ls="--", zorder=7, alpha=0.85)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl3 = mapkit.SymbolLabels(ax, fig)
sl3.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.50, 0.0, 1.0, 0.09),
             (0.88, 0.86, 1.0, 1.0)])

hubs_data = [
    ("上海虹桥综合交通枢纽 (全球超级客运枢纽·高铁+空港+地铁)", 121.320, 31.190, "airport", "全球客流最大综合客运枢纽·大虹桥商务核"),
    ("上海浦东国际机场 (4F级洲际门户·全国最大国际航空货运口岸)", 121.800, 31.145, "airport", "国际客货吞吐主力港·四期扩建启动"),
    ("上海东站综合交通枢纽 (在建上海第二大铁路客运枢纽)", 121.790, 31.150, "rail", "空铁联运门户·沿江沿海高铁接入"),
    ("上海火车站 (中心城区铁路客运总枢纽)", 121.455, 31.250, "rail", "老牌特等客运站·京沪沪昆普速与高铁"),
    ("上海南站 (西南骨干客运枢纽·金山铁路起点)", 121.430, 31.155, "rail", "特等客运枢纽·首座圆形火车站"),
    ("上海松江站 (沪苏湖高铁大站·西南枢纽门户)", 121.220, 30.980, "rail", "9台23线西南门户综合交通枢纽"),
    ("洋山深水港 (全球最大集装箱自动化码头·东方大港)", 122.060, 30.620, "port", "国际集装箱枢纽第一港·自动化码头标杆"),
    ("外高桥港区 (长江口核心集装箱与整车进出口港)", 121.580, 31.340, "port", "中国通关速度最快口岸·自贸区发源地"),
    ("吴淞口国际邮轮港 (亚洲第一·全球前四邮轮母港)", 121.505, 31.400, "port", "首艘国产大型邮轮爱达·魔都号母港"),
    ("上海长江隧桥 (跨越长江南支连通崇明长兴生命大动脉)", 121.740, 31.425, "bridge", "南隧北桥全长25.5公里·世界级工程"),
    ("东海大桥 (跨越杭州湾长32.5公里深水跨海长桥)", 121.970, 30.750, "bridge", "中国首座真正意义上的外海跨海大桥")
]

for name, lon, lat, htype, desc in hubs_data:
    px, py = to_alb(lon, lat)
    m = "D" if htype == "airport" else ("s" if htype == "rail" else ("p" if htype == "port" else "^"))
    fc = "#27ae60" if htype == "airport" else ("#c0392b" if htype == "rail" else ("#1a5276" if htype == "port" else "#d35400"))
    sl3.add(px, py, name, htype, note=desc, priority=0 if htype in ("airport", "port") else 1,
            marker=m, face=fc, size=6.8 if htype in ("airport", "port") else 5.2, kind_label="综合交通门户与战略枢纽")

sym_type_h3, sym_idx_h3 = sl3.flush()

sb_x0 = ax_xlim[0] + span_x * 0.55
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=30)
add_compass(ax, 0.94, 0.91)

leg3 = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h3, title="枢纽类型与综合交通要素", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h3, title="骨干交通枢纽名录", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("上海市综合立体交通与海空枢纽网络图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Integrated Transport Network, Aviation & Deep-water Ports System of Shanghai",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg3, "数据源：中国国家铁路集团 · 上海国际航运中心建设白皮书 · 制作：《中国地理知识手册》",
    fontsize=6.5)

f3_path = os.path.join(OUT_DIR, "fig09-00-3_上海市综合立体交通与海空枢纽网络图.png")
fig.savefig(f3_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"✓ Saved Fig 09-00-3: {f3_path}")

# =============================================================================
# 图 09-00-4：上海市“五个中心”与高能级产业空间格局图
# =============================================================================
print("Generating Fig 09-00-4 (Five Centers & High-Tier Industries)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

gpd.GeoSeries([sh_union], crs=ALBERS).plot(ax=ax, facecolor="#ffffff", edgecolor="#1a5276", lw=1.6, zorder=2)
sh_prov.boundary.plot(ax=ax, color="#cbd5e0", lw=0.6, ls="--", zorder=3)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl4 = mapkit.SymbolLabels(ax, fig)
sl4.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.50, 0.0, 1.0, 0.09),
             (0.88, 0.86, 1.0, 1.0)])

industries_data = [
    ("陆家嘴金融城 (国家级金融核心区·股票/期货/外汇交易市场)", 121.505, 31.235, "fin", "全国金融资产要素市场最齐备区·万亿级资金枢纽"),
    ("外滩金融集聚带 (全球资产管理中心·历史老外滩融汇)", 121.492, 31.236, "fin", "中外金融总部云集·财富管理高地"),
    ("张江科学城 (综合性国家科学中心·中国药谷·集成电路策源地)", 121.590, 31.190, "it", "上海光源大科学装置·中芯/华虹/张江药谷"),
    ("临港新片区战略产城 (特斯拉超级工厂·芯片/氢能高地)", 121.920, 30.900, "zone", "特殊经济功能区·特斯拉上海/中芯临港/全球算力"),
    ("中国商飞总装制造中心 (C919大型客机研发总装基地)", 121.770, 31.130, "mfg", "大国重器民用航空心脏·C919与ARJ21批量交付"),
    ("中国船舶长兴造船基地 (江南造船/外高桥造船大国母港)", 121.720, 31.380, "mfg", "国产航母/大型LNG船/大型邮轮世界级造船基地"),
    ("嘉定国际汽车城 (上汽大众·国家智能网联汽车示范区)", 121.180, 31.290, "mfg", "中国汽车工业摇篮·自动驾驶与智慧交通前沿"),
    ("国家会展中心“四叶草” (中国国际进口博览会永久主场)", 121.310, 31.192, "trade", "全球单体最大展馆·进博会高水平对外开放窗口"),
    ("宝武钢铁集团总部与吴淞创新城 (特种高端钢与绿色转型)", 121.480, 31.420, "mfg", "全球第一大钢铁巨头总部·工业锈带转科创绿带"),
    ("金山碳谷绿湾与上海石化 (大型先进材料·高性能碳纤维)", 121.330, 30.730, "chem", "大丝束碳纤维基地·绿色高端石化新材料转型"),
    ("东方美谷 (中国化妆品产业之都·奉贤生物医药基地)", 121.460, 30.930, "bio", "全国化妆品企业集聚度最高园区·美丽健康高地"),
    ("长三角G60科创走廊策源地 (松江大学城·先进制造业集群)", 121.220, 31.050, "it", "辐射九城市科技创新大动脉策源地"),
    ("华为练秋湖研发中心 (全球最大单体研发基地·3万人科创城)", 120.950, 31.040, "it", "终端研发/海思芯片/数字能源核心智脑")
]

for name, lon, lat, ikind, desc in industries_data:
    px, py = to_alb(lon, lat)
    m = "D"
    fc = "#c0392b" if ikind == "mfg" else ("#2980b9" if ikind == "it" else ("#f39c12" if ikind == "fin" else ("#16a085" if ikind in ("trade", "bio") else "#8e44ad")))
    sl4.add(px, py, name, ikind, note=desc, priority=1,
            marker=m, face=fc, size=5.5, kind_label="“五个中心”与高能级产业集群")

sym_type_h4, sym_idx_h4 = sl4.flush()

sb_x0 = ax_xlim[0] + span_x * 0.55
sb_y0 = ax_ylim[0] + span_y * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=30)
add_compass(ax, 0.94, 0.91)

leg4 = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h4, title="高能级产业与核心功能", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h4, title="重大产业地标与领航旗舰", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("上海市“五个中心”与高能级产业空间格局图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Major Strategic Industries & 'Five Centers' Spatial Pattern of Shanghai Municipality",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg4, "数据源：上海市统计局 · 上海市经济和信息化委员会 · 制作：《中国地理知识手册》",
    fontsize=6.5)

f4_path = os.path.join(OUT_DIR, "fig09-00-4_上海市“五个中心”与高能级产业空间格局图.png")
fig.savefig(f4_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"✓ Saved Fig 09-00-4: {f4_path}")

# =============================================================================
# 图 09-00-5：上海市1986—2024年夜间灯光演变与长三角一体化辐射图
# =============================================================================
print("Generating Fig 09-00-5 (Nightlight Trends)...")
fig = plt.figure(figsize=(11.0, 7.2), dpi=DPI)
fig.patch.set_facecolor("white")

gs = fig.add_gridspec(nrows=1, ncols=2, width_ratios=[1.15, 1.0], wspace=0.18,
                      left=0.03, right=0.97, top=0.92, bottom=0.08)

ax_map = fig.add_subplot(gs[0, 0])
ax_plot = fig.add_subplot(gs[0, 1])

ax_map.set_facecolor("#0b132b")
sh_prov.plot(ax=ax_map, facecolor="#1c2541", edgecolor="#3a506b", lw=0.6, zorder=2)
gpd.GeoSeries([sh_union], crs=ALBERS).boundary.plot(ax=ax_map, color="#5bc0be", lw=1.2, zorder=6)

nl_df = pd.read_csv(os.path.join(DATA_DIR, "shanghai_nightlight_clean.csv"))

# 各区特征高亮发光点
glow_points = [
    ("陆家嘴与外滩金融核心", 121.50, 31.235, 250000, "#f1c40f"),
    ("张江科学城与软件园", 121.60, 31.190, 180000, "#f39c12"),
    ("大虹桥商务区与枢纽", 121.32, 31.190, 160000, "#f1c40f"),
    ("五角场与杨浦滨江", 121.52, 31.280, 140000, "#e67e22"),
    ("莘庄与闵行南部", 121.38, 31.110, 130000, "#f39c12"),
    ("嘉定主城与汽车城", 121.24, 31.360, 110000, "#f39c12"),
    ("松江新城与大学城", 121.23, 31.030, 110000, "#f39c12"),
    ("临港新片区滴水湖", 121.93, 30.900, 120000, "#f1c40f"),
    ("宝山吴淞与宝钢", 121.48, 31.400, 100000, "#e67e22"),
    ("青浦新城与练秋湖", 121.10, 31.120, 95000, "#f39c12"),
    ("奉贤南桥与上海之鱼", 121.47, 30.920, 90000, "#f39c12"),
    ("金山石化与滨海城", 121.34, 30.730, 85000, "#e67e22"),
    ("崇明城桥与长兴岛", 121.50, 31.500, 70000, "#f39c12")
]

for gname, lon, lat, val, gcol in glow_points:
    px, py = to_alb(lon, lat)
    rad = np.sqrt(val) * 80.0
    ax_map.scatter(px, py, s=rad*0.06, c=gcol, alpha=0.40, edgecolors="none", zorder=8)
    ax_map.scatter(px, py, s=rad*0.02, c="#ffffff", alpha=0.85, edgecolors="none", zorder=9)
    ax_map.text(px, py, gname.split("与")[0], color="#ffffff", fontsize=6.8, weight="bold",
                ha="center", va="bottom", zorder=15,
                path_effects=[pe.withStroke(linewidth=1.8, foreground="#000000", alpha=0.8)])

ax_map.set_xlim(ax_xlim)
ax_map.set_ylim(ax_ylim)
ax_map.axis("off")
ax_map.set_title("上海市夜间灯光辐射空间分布与高亮集聚轴", fontsize=9.2, color="#ffffff", weight="bold", pad=8)

ax_plot.set_facecolor("#ffffff")
ax_plot.grid(True, linestyle="--", alpha=0.45, color="#bdc3c7")

# 重点区夜光演变曲线对照
focus_districts = [
    (310115, "浦东新区", "#c0392b", 2.4, "-"),
    (310112, "闵行区", "#2980b9", 2.0, "-"),
    (310113, "宝山区", "#27ae60", 1.8, "-"),
    (310114, "嘉定区", "#8e44ad", 1.8, "-"),
    (310117, "松江区", "#d35400", 1.8, "-"),
    (310118, "青浦区", "#16a085", 1.8, "--"),
    (310120, "奉贤区", "#f39c12", 1.8, "--"),
    (310101, "黄浦区 (CAZ核心)", "#e74c3c", 1.8, "-."),
    (310104, "徐汇区 (CAZ核心)", "#34495e", 1.6, ":"),
    (310151, "崇明区 (生态岛)", "#2ecc71", 1.6, "-.")
]

for dcode, dname, col, lw, ls in focus_districts:
    sub = nl_df[nl_df['district_code'].astype(int) == int(dcode)].sort_values('year')
    if len(sub) > 0:
        ax_plot.plot(sub['year'], sub['sum'], color=col, lw=lw, ls=ls, label=dname, alpha=0.9)

ax_plot.set_xlabel("年份 (1986—2013/2024)", fontsize=8.5, color="#2c3e50")
ax_plot.set_ylabel("夜间灯光辐射总指数 (DN Sum)", fontsize=8.5, color="#2c3e50")
ax_plot.set_title("上海市重点市辖区夜间灯光演变曲线 (1986—2024)", fontsize=9.2, weight="bold", color="#1a252f", pad=8)
ax_plot.legend(loc="upper left", fontsize=6.8, framealpha=0.9, ncol=2)

fig.suptitle("上海市1986—2024年夜间灯光演变与长三角一体化辐射图", fontsize=12.5, weight="bold", y=0.985, color="#1a252f")

f5_path = os.path.join(OUT_DIR, "fig09-00-5_上海市1986—2024年夜间灯光演变与长三角一体化辐射图.png")
fig.savefig(f5_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"✓ Saved Fig 09-00-5: {f5_path}")

print("\n=== ALL 5 SHANGHAI OVERVIEW FIGURES COMPLETED SUCCESSFULLY! ===")
