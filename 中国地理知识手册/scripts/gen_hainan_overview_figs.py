# -*- coding: utf-8 -*-
"""海南省地理统揽专题地图生成引擎（20-00）
包含 5 幅全省权威出版级地图与分析图表（精细调优排版、微缩字号、严格杜绝压盖）：
1. fig20-00-1_海南省地势起伏与环岛放射水系格局图.png
2. fig20-00-2_海南省19个市县行政区划与三极一带一区战略格局图.png
3. fig20-00-3_海南自由贸易港综合交通网络与环岛高铁高速航线图.png
4. fig20-00-4_海南自由贸易港重点园区与特色现代产业空间格局图.png
5. fig20-00-5_海南省1986-2024年夜间灯光演化与自贸港开发强度对比图.png
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

BASE_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册"
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))
from style import ALBERS, C_TEXT, DATA, DPI, FIGURES, setup
import mapkit
from hainan_configs import HAINAN_OVERVIEW
from hainan_city_configs import HAINAN_CONFIGS

setup()
OUT_DIR = os.path.join(BASE_DIR, "figures")
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

def add_compass(ax, x=0.94, y=0.92):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.055), transform=ax.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=1.8, headwidth=5.5, headlength=6.5),
                ha="center", va="center", fontsize=8.8, fontweight="bold", color="#2c3e50", zorder=30)

print("Loading Hainan provincial boundaries and DEM...")
DATA_DIR = os.path.join(BASE_DIR, "data")
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

# 460000_full.json 包含全省 19 个单元
hn_all = gpd.read_file(os.path.join(DATAV_DIR, "460000_full.json")).to_crs(ALBERS)
hn_all["geometry"] = hn_all.geometry.buffer(0)

# 本岛 18 市县与三沙市
hn_main = hn_all[hn_all['adcode'] != 460300].copy()
hn_sansha = hn_all[hn_all['adcode'] == 460300].copy()

main_union = hn_main.union_all()
b = hn_main.total_bounds
span_x = b[2] - b[0]
span_y = b[3] - b[1]
pad_x = span_x * 0.05
pad_y = span_y * 0.05
ax_xlim = (b[0] - pad_x, b[2] + pad_x)
ax_ylim = (b[1] - pad_y, b[3] + pad_y)

# 加载 DEM
dem_file = os.path.join(DATA_DIR, "dem", "province", "460000_z9.npz")
dem_data = np.load(dem_file)
step = 2
dem_raw = dem_data['dem'][::step, ::step]
res = float(dem_data['res']) * step
minx = float(dem_data['minx'])
maxy = float(dem_data['maxy'])
nrows, ncols = dem_raw.shape
dem_extent = [minx, minx + ncols * res, maxy - nrows * res, maxy]

# 过滤 DEM 水体负值
dem_elev = np.where(dem_raw < 0, np.nan, dem_raw)
hillshade = calc_hillshade(dem_elev, res)

terrain_cmap = LinearSegmentedColormap.from_list("hn_terrain", [
    (0.0, "#2d8b57"),   # 沿海平原低地 深绿
    (0.10, "#66bb6a"),  # 台地浅绿
    (0.25, "#d4e157"),  # 丘陵浅黄绿
    (0.45, "#ffd54f"),  # 低山暖黄
    (0.65, "#ff8a65"),  # 中山橙褐
    (0.85, "#a1887f"),  # 崇山灰褐
    (1.0, "#5d4037")    # 极顶深褐
])

def draw_sansha_inset(fig, rect=[0.74, 0.12, 0.22, 0.32]):
    """绘制三沙市南海诸岛附图（符合中国测绘国家标准规范）"""
    ax_in = fig.add_axes(rect, facecolor='#e3f2fd')
    ax_in.set_title("三沙市南海诸岛附图", fontsize=7.5, fontweight='bold', color='#1a237e', pad=3)
    
    # 绘制三沙市岛礁多边形
    hn_sansha.plot(ax=ax_in, facecolor='#ff7043', edgecolor='#d84315', linewidth=0.8, zorder=5)
    
    # 标出重要群岛与地理节点
    sansha_points = [
        ("永兴岛 (三沙驻地)", 112.333, 16.833),
        ("西沙群岛", 111.800, 16.500),
        ("中沙群岛", 114.500, 15.800),
        ("黄岩岛", 117.750, 15.150),
        ("南沙群岛", 114.000, 10.000),
        ("美济礁", 115.530, 9.900),
        ("渚碧礁", 114.060, 10.910),
        ("永暑礁", 112.980, 9.620),
        ("曾母暗沙", 112.280, 3.970)
    ]
    for name, lon, lat in sansha_points:
        x, y = to_alb(lon, lat)
        ax_in.plot(x, y, 'o', color='#b71c1c', markersize=3.0, markeredgecolor='white', markeredgewidth=0.5, zorder=10)
        ax_in.text(x, y + 25000, name, fontsize=5.5, fontweight='bold', color='#0d47a1', ha='center',
                   path_effects=[pe.withStroke(linewidth=1.5, foreground='white')], zorder=12)
    
    # 设定附图范围（南沙到西沙全域）
    sx0, sy0 = to_alb(108.0, 3.0)
    sx1, sy1 = to_alb(118.5, 18.0)
    ax_in.set_xlim(min(sx0, sx1) - 40000, max(sx0, sx1) + 40000)
    ax_in.set_ylim(min(sy0, sy1) - 40000, max(sy0, sy1) + 40000)
    ax_in.set_xticks([])
    ax_in.set_yticks([])
    for spine in ax_in.spines.values():
        spine.set_color('#1565c0')
        spine.set_linewidth(1.2)
    ax_in.text(0.04, 0.04, "南海诸岛归属海南省三沙市管辖", transform=ax_in.transAxes,
               fontsize=5.0, color='#37474f', style='italic',
               path_effects=[pe.withStroke(linewidth=1.2, foreground='white')])
    return ax_in

# =========================================================================
# 1. 地势起伏与放射水系格局图 (fig20-00-1)
# =========================================================================
print("Rendering fig20-00-1: Hainan topography and radial river network...")
fig, ax = plt.subplots(figsize=(10.5, 8.2), dpi=DPI)
fig.patch.set_facecolor('#ffffff')
ax.set_facecolor('#e8f4f8')

# DEM 渲染
im_hs = ax.imshow(hillshade, extent=dem_extent, cmap='gray', origin='upper', alpha=0.35, zorder=2)
im_dem = ax.imshow(dem_elev, extent=dem_extent, cmap=terrain_cmap, origin='upper', vmin=0, vmax=1867, alpha=0.72, zorder=3)

# 边界裁剪
clip_patch = get_mpl_clip_patch(main_union)
ax.add_patch(clip_patch)
im_hs.set_clip_path(clip_patch)
im_dem.set_clip_path(clip_patch)

# 绘制行政边界
hn_main.boundary.plot(ax=ax, edgecolor='#37474f', linewidth=0.7, linestyle='--', alpha=0.7, zorder=6)
gpd.GeoSeries([main_union]).boundary.plot(ax=ax, edgecolor='#1a237e', linewidth=1.4, zorder=7)

# 标注地貌山峰
for item in HAINAN_OVERVIEW["landmarks_macro"]:
    name, lon, lat, ptype = item
    x, y = to_alb(lon, lat)
    if not (ax_xlim[0] <= x <= ax_xlim[2] if len(ax_xlim)==3 else ax_xlim[0] <= x <= ax_xlim[1]):
        continue
    if ptype == "peak_max":
        ax.plot(x, y, '^', color='#d50000', markersize=9.0, markeredgecolor='white', markeredgewidth=1.2, zorder=20)
        ax.text(x, y + 6000, name, fontsize=8.5, fontweight='black', color='#b71c1c', ha='center',
                path_effects=[pe.withStroke(linewidth=2.5, foreground='white')], zorder=21)
    elif ptype == "peak":
        ax.plot(x, y, '^', color='#e65100', markersize=6.5, markeredgecolor='white', markeredgewidth=1.0, zorder=18)
        ax.text(x, y + 4500, name, fontsize=7.2, fontweight='bold', color='#4e342e', ha='center',
                path_effects=[pe.withStroke(linewidth=2.0, foreground='white')], zorder=19)
    else:
        ax.plot(x, y, 'o', color='#0277bd', markersize=5.0, markeredgecolor='white', markeredgewidth=0.8, zorder=16)
        ax.text(x, y - 5500, name, fontsize=6.8, fontweight='bold', color='#01579b', ha='center',
                path_effects=[pe.withStroke(linewidth=1.8, foreground='white')], zorder=17)

# 标注水系海湾
for rname, rlon, rlat, rkind in HAINAN_OVERVIEW["rivers_macro"]:
    x, y = to_alb(rlon, rlat)
    if rkind == "river_main":
        ax.plot(x, y, 's', color='#0091ea', markersize=4.5, markeredgecolor='white', zorder=15)
        ax.text(x, y + 4500, rname, fontsize=7.5, fontweight='bold', color='#01579b', ha='center',
                path_effects=[pe.withStroke(linewidth=2.0, foreground='white')], zorder=16)
    elif rkind == "reservoir":
        ax.plot(x, y, 'D', color='#00b0ff', markersize=5.5, markeredgecolor='white', zorder=15)
        ax.text(x, y + 5000, rname, fontsize=7.5, fontweight='bold', color='#006064', ha='center',
                path_effects=[pe.withStroke(linewidth=2.0, foreground='white')], zorder=16)
    else:
        ax.text(x, y - 4500, rname, fontsize=7.0, color='#004d40', ha='center', style='italic',
                path_effects=[pe.withStroke(linewidth=1.8, foreground='white')], zorder=14)

# 环形阶梯标注圈
ax.text(0.04, 0.93, "海南岛环状梯级地貌结构：\n中部高山雨林穹窿（五指山1867m/鹦哥岭1811m）\n向四周逐级递降为丘陵、阶地与台地平原\n三大江河（南渡江·昌化江·万泉河）呈典型放射状奔流入海",
        transform=ax.transAxes, fontsize=7.5, color='#263238', linespacing=1.4,
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#ffffff", edgecolor="#90a4ae", alpha=0.92), zorder=25)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.set_title("海南省地势起伏与环岛放射水系格局图", fontsize=12.5, fontweight='bold', color='#1a237e', pad=12)
mapkit.add_scalebar(ax, ax_xlim[0] + pad_x * 0.8, ax_ylim[0] + pad_y * 0.8, length_km=50)
add_compass(ax, 0.94, 0.93)

# 颜色条
cbar_ax = fig.add_axes([0.16, 0.08, 0.35, 0.016])
norm = Normalize(vmin=0, vmax=1867)
cb = matplotlib.colorbar.ColorbarBase(cbar_ax, cmap=terrain_cmap, norm=norm, orientation='horizontal')
cb.set_label("数字高程模型 DEM (米)", fontsize=7.2, color='#263238', labelpad=4)
cb.ax.tick_params(labelsize=6.5)

# 三沙南海附图
draw_sansha_inset(fig, [0.73, 0.09, 0.23, 0.30])

f1_out = os.path.join(OUT_DIR, "fig20-00-1_海南省地势起伏与环岛放射水系格局图.png")
plt.savefig(f1_out, dpi=DPI, bbox_inches='tight')
plt.close(fig)
print(f" Saved: {f1_out}")


# =========================================================================
# 2. 行政区划与三极一带一区格局图 (fig20-00-2)
# =========================================================================
print("Rendering fig20-00-2: Hainan administrative & 3-pole strategic zones...")
fig, ax = plt.subplots(figsize=(10.5, 8.2), dpi=DPI)
fig.patch.set_facecolor('#ffffff')
ax.set_facecolor('#f4f9f9')

# 四大功能板块颜色映射
zone_colors = {
    "haikou_zone": "#bbdefb",    # 海口经济圈 浅蓝
    "sanya_zone": "#ffe082",     # 三亚经济圈 暖黄
    "danyang_zone": "#c8e6c9",   # 儋洋经济圈/西北工业 浅绿
    "rainforest_zone": "#a5d6a7" # 中部雨林生态保护区 苍翠绿
}

# 19 个单元分类匹配
def get_zone_color(code):
    c = str(code)
    if c in ["460100", "469005", "469021", "469022", "469023", "469024"]:
        return "#bbdefb"  # 海口核心经济圈
    elif c in ["460200", "469027", "469028", "469029", "469006"]:
        return "#ffe082"  # 三亚南部滨海旅游消费圈
    elif c in ["460400", "469007", "469026"]:
        return "#d1c4e9"  # 儋洋一体化及西部临港重工带
    elif c in ["469001", "469025", "469030"]:
        return "#a5d6a7"  # 中部生态雨林国家公园核心圈
    elif c in ["469002"]:
        return "#b2dfdb"  # 东部博鳌医疗对话名城
    return "#e0e0e0"

for idx, row in hn_main.iterrows():
    c = get_zone_color(row['adcode'])
    gpd.GeoSeries([row.geometry]).plot(ax=ax, facecolor=c, edgecolor='#37474f', linewidth=0.9, alpha=0.85, zorder=3)

# 绘制市县边界与高亮轮廓
gpd.GeoSeries([main_union]).boundary.plot(ax=ax, edgecolor='#0d47a1', linewidth=1.6, zorder=8)

# 标注 18 个市县行政驻地及名称
for code, conf in HAINAN_CONFIGS.items():
    if code == "460300":
        continue
    c_lat, c_lon = 0, 0
    # 找到驻地坐标
    gov_found = False
    for p in conf.get("places_admin", []):
        if len(p) >= 6 and (p[5] == "gov" or "市委" in p[0] or "县委" in p[0]):
            c_lon, c_lat = p[1], p[2]
            gov_found = True
            break
    if not gov_found:
        # 使用多边形质心
        match_poly = hn_main[hn_main['adcode'] == int(code)]
        if not match_poly.empty:
            pt = match_poly.geometry.iloc[0].centroid
            x, y = pt.x, pt.y
        else:
            continue
    else:
        x, y = to_alb(c_lon, c_lat)
    
    # 标记市县驻地圆点
    is_prefecture = code in ["460100", "460200", "460400"]
    if is_prefecture:
        ax.plot(x, y, 'o', color='#b71c1c', markersize=7.5, markeredgecolor='white', markeredgewidth=1.2, zorder=20)
        ax.text(x, y + 4200, f"{conf['name']}\n(地级市·{conf['gdp_2024']}亿)", fontsize=7.8, fontweight='bold',
                color='#b71c1c', ha='center', va='bottom',
                path_effects=[pe.withStroke(linewidth=2.2, foreground='white')], zorder=22)
    else:
        ax.plot(x, y, 'o', color='#1565c0', markersize=5.0, markeredgecolor='white', markeredgewidth=0.8, zorder=18)
        ax.text(x, y + 3200, f"{conf['name']}", fontsize=6.8, fontweight='bold',
                color='#1a237e', ha='center', va='bottom',
                path_effects=[pe.withStroke(linewidth=1.8, foreground='white')], zorder=19)

# 标注战略廊道与发展极核
ax.annotate("海口经济圈极核\n(省会门户·江东新区·美兰枢纽)", xy=to_alb(110.33, 20.03), xytext=to_alb(109.80, 20.25),
            arrowprops=dict(arrowstyle="->", color='#c2185b', lw=1.5),
            fontsize=7.8, fontweight='bold', color='#880e4f',
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#fce4ec", edgecolor="#c2185b", alpha=0.9), zorder=26)

ax.annotate("三亚经济圈极核\n(国际旅游消费中心·崖州湾科技城)", xy=to_alb(109.51, 18.25), xytext=to_alb(108.70, 18.15),
            arrowprops=dict(arrowstyle="->", color='#e65100', lw=1.5),
            fontsize=7.8, fontweight='bold', color='#e65100',
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#fff3e0", edgecolor="#ff9800", alpha=0.9), zorder=26)

ax.annotate("儋洋一体化发展极\n(自贸港先行示范·绿色新材料与深水枢纽)", xy=to_alb(109.20, 19.70), xytext=to_alb(108.50, 20.00),
            arrowprops=dict(arrowstyle="->", color='#2e7d32', lw=1.5),
            fontsize=7.8, fontweight='bold', color='#1b5e20',
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#e8f5e9", edgecolor="#4caf50", alpha=0.9), zorder=26)

# 图例与说明卡片
legend_elements = [
    Patch(facecolor='#bbdefb', edgecolor='#1565c0', label='海口核心经济圈 (省会现代服务/江东新区)'),
    Patch(facecolor='#ffe082', edgecolor='#f57f17', label='三亚南部旅游经济圈 (免税消费/南繁深海)'),
    Patch(facecolor='#d1c4e9', edgecolor='#512da8', label='儋洋一体化先行区 (西部临港工业/洋浦枢纽)'),
    Patch(facecolor='#b2dfdb', edgecolor='#004d40', label='琼海博鳌国际对话区 (乐城医疗/外交名片)'),
    Patch(facecolor='#a5d6a7', edgecolor='#1b5e20', label='中部雨林生态保育区 (热带雨林国家公园核心)')
]
ax.legend(handles=legend_elements, loc='upper left', fontsize=7.0, framealpha=0.92, facecolor='#ffffff', edgecolor='#90a4ae')

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.set_title("海南省19个市县行政区划与“三极一带一区”空间战略格局图", fontsize=12.2, fontweight='bold', color='#1a237e', pad=12)
mapkit.add_scalebar(ax, ax_xlim[0] + pad_x * 0.8, ax_ylim[0] + pad_y * 0.8, length_km=50)
add_compass(ax, 0.94, 0.93)

draw_sansha_inset(fig, [0.73, 0.09, 0.23, 0.30])

f2_out = os.path.join(OUT_DIR, "fig20-00-2_海南省19个市县行政区划与三极一带一区战略格局图.png")
plt.savefig(f2_out, dpi=DPI, bbox_inches='tight')
plt.close(fig)
print(f" Saved: {f2_out}")


# =========================================================================
# 3. 综合交通网络与环岛高铁高速航线图 (fig20-00-3)
# =========================================================================
print("Rendering fig20-00-3: Hainan integrated transport & high-speed ring...")
fig, ax = plt.subplots(figsize=(10.5, 8.2), dpi=DPI)
fig.patch.set_facecolor('#ffffff')
ax.set_facecolor('#f4f8fa')

# 陆地浅灰底色
hn_main.plot(ax=ax, facecolor='#edf2f4', edgecolor='#b0bec5', linewidth=0.8, zorder=2)
gpd.GeoSeries([main_union]).boundary.plot(ax=ax, edgecolor='#455a64', linewidth=1.2, zorder=5)

# 模拟绘制海南环岛高铁走向闭环（连接海口-文昌-琼海-万宁-陵水-三亚-乐东-东方-昌江-儋州-临高-澄迈-海口）
hsr_coords = [
    (110.355, 19.985), # 海口东
    (110.460, 19.930), # 美兰
    (110.753, 19.612), # 文昌
    (110.466, 19.245), # 琼海
    (110.590, 19.150), # 博鳌
    (110.388, 18.796), # 万宁
    (110.037, 18.505), # 陵水
    (109.630, 18.280), # 亚龙湾
    (109.508, 18.247), # 三亚
    (109.175, 18.360), # 崖州
    (108.950, 18.700), # 乐东
    (108.653, 19.101), # 东方
    (109.053, 19.260), # 棋子湾
    (109.200, 19.730), # 洋浦/白马井
    (109.687, 19.912), # 临高南
    (110.007, 19.738), # 福山镇/老城镇
    (110.290, 20.010), # 海口站
    (110.355, 19.985)  # 闭环
]
hsr_x = [to_alb(pt[0], pt[1])[0] for pt in hsr_coords]
hsr_y = [to_alb(pt[0], pt[1])[1] for pt in hsr_coords]
ax.plot(hsr_x, hsr_y, color='#d32f2f', linewidth=3.2, linestyle='-', zorder=12, label='海南环岛高速铁路 (全球首条环岛高铁·时速250km)')
ax.plot(hsr_x, hsr_y, color='#ffffff', linewidth=1.2, linestyle='--', zorder=13)

# G9811海三中线高速与横向万洋高速
mid_hwy = [(110.33, 20.03), (110.10, 19.36), (109.84, 19.03), (109.52, 18.78), (109.51, 18.25)]
mh_x = [to_alb(pt[0], pt[1])[0] for pt in mid_hwy]
mh_y = [to_alb(pt[0], pt[1])[1] for pt in mid_hwy]
ax.plot(mh_x, mh_y, color='#ff9800', linewidth=2.4, linestyle='-', zorder=10, label='海三高速 (贯穿中部五指山琼中走廊)')

wy_hwy = [(110.388, 18.796), (109.84, 19.03), (109.576, 19.520), (109.20, 19.73)]
wy_x = [to_alb(pt[0], pt[1])[0] for pt in wy_hwy]
wy_y = [to_alb(pt[0], pt[1])[1] for pt in wy_hwy]
ax.plot(wy_x, wy_y, color='#ffb74d', linewidth=2.0, linestyle='-.', zorder=9, label='万洋高速 (串联东部万宁与西部洋浦跨岛廊道)')

# 环岛旅游公路示范线
ax.plot(hsr_x, hsr_y, color='#00897b', linewidth=1.2, linestyle=':', alpha=0.8, zorder=8, label='海南环岛旅游公路 (988公里风景大环线)')

# 粤海铁路轮渡跨海走廊
fx = [to_alb(110.15, 20.06)[0], to_alb(110.15, 20.25)[0]]
fy = [to_alb(110.15, 20.06)[1], to_alb(110.15, 20.25)[1]]
ax.plot(fx, fy, color='#0288d1', linewidth=2.8, linestyle=':', zorder=14, label='粤海跨海铁路轮渡通道 (连接湛江徐闻与海口)')

# 标注空港枢纽
airports = [
    ("海口美兰国际机场 (4F枢纽)", 110.460, 19.930),
    ("三亚凤凰国际机场 (4E枢纽)", 109.410, 18.310),
    ("琼海博鳌机场 (4C级)", 110.530, 19.140)
]
for aname, alon, alat in airports:
    x, y = to_alb(alon, alat)
    ax.plot(x, y, '^', color='#7b1fa2', markersize=8.0, markeredgecolor='white', markeredgewidth=1.2, zorder=20)
    ax.text(x, y - 4800, aname, fontsize=7.2, fontweight='bold', color='#4a148c', ha='center',
            path_effects=[pe.withStroke(linewidth=2.0, foreground='white')], zorder=22)

# 标注主要海港枢纽
ports = [
    ("洋浦国际集装箱枢纽港 (西部陆海新通道门户)", 109.180, 19.730),
    ("海口新海客滚枢纽 (全球最大单体客滚枢纽)", 110.150, 20.060),
    ("三亚国际邮轮港 (南中国海邮轮母港)", 109.480, 18.230),
    ("八所港 (国家一类开放口岸/大宗散货)", 108.620, 19.100),
    ("文昌清澜港 (航天火箭海运入港)", 110.820, 19.550)
]
for pname, plon, plat in ports:
    x, y = to_alb(plon, plat)
    ax.plot(x, y, 's', color='#00695c', markersize=6.5, markeredgecolor='white', markeredgewidth=1.0, zorder=18)
    ax.text(x, y + 4200, pname, fontsize=6.8, fontweight='bold', color='#004d40', ha='center',
            path_effects=[pe.withStroke(linewidth=1.8, foreground='white')], zorder=21)

ax.legend(loc='upper left', fontsize=7.0, framealpha=0.92, facecolor='#ffffff', edgecolor='#90a4ae')
ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.set_title("海南自由贸易港综合立体交通网络与环岛高铁高速航线图", fontsize=12.2, fontweight='bold', color='#1a237e', pad=12)
mapkit.add_scalebar(ax, ax_xlim[0] + pad_x * 0.8, ax_ylim[0] + pad_y * 0.8, length_km=50)
add_compass(ax, 0.94, 0.93)

draw_sansha_inset(fig, [0.73, 0.09, 0.23, 0.30])

f3_out = os.path.join(OUT_DIR, "fig20-00-3_海南自由贸易港综合交通网络与环岛高铁高速航线图.png")
plt.savefig(f3_out, dpi=DPI, bbox_inches='tight')
plt.close(fig)
print(f" Saved: {f3_out}")


# =========================================================================
# 4. 自贸港重点园区与特色现代产业空间格局图 (fig20-00-4)
# =========================================================================
print("Rendering fig20-00-4: Hainan Free Trade Port key industrial zones...")
fig, ax = plt.subplots(figsize=(10.5, 8.2), dpi=DPI)
fig.patch.set_facecolor('#ffffff')
ax.set_facecolor('#f7f9fa')

hn_main.plot(ax=ax, facecolor='#e8ecef', edgecolor='#cfd8dc', linewidth=0.8, zorder=2)
gpd.GeoSeries([main_union]).boundary.plot(ax=ax, edgecolor='#37474f', linewidth=1.2, zorder=5)

# 自贸港重点园区与现代特色产业
zones_13 = [
    ("海口江东新区\n(总部经济与现代服务先导区)", 110.450, 19.980, "#c2185b", "headquarters"),
    ("三亚崖州湾科技城\n(国家南繁硅谷·深海科技城)", 109.170, 18.360, "#00897b", "tech"),
    ("洋浦经济开发区\n(千万吨炼化·绿色新材料与保税港)", 109.200, 19.740, "#1565c0", "industry"),
    ("文昌国际航天城\n(中国首个滨海商业航天发射场)", 110.950, 19.620, "#6a1b9a", "aerospace"),
    ("博鳌乐城医疗旅游先行区\n(中国医疗特区·国际创新药械)", 110.530, 19.190, "#e65100", "medical"),
    ("陵水黎安国际教育区\n(中外合作办学聚集地)", 110.050, 18.450, "#00838f", "education"),
    ("海南生态软件园\n(澄迈数字经济·国家级科技孵化)", 110.080, 19.950, "#2e7d32", "digital"),
    ("三亚中央商务区\n(凤凰海岸·免税城·游艇邮轮)", 109.510, 18.250, "#f57c00", "trade"),
    ("海口高新技术开发区\n(药谷生物医药产业集群)", 110.260, 19.980, "#ad1457", "pharma"),
    ("海口综合保税区\n(跨境电商·保税钻石珠宝制造)", 110.160, 19.960, "#4e342e", "logistics"),
    ("东方临港产业园\n(八所绿色化工·海洋新能源)", 108.660, 19.120, "#37474f", "energy"),
    ("临高金牌港开发区\n(新型装配式建筑产业集群)", 109.760, 19.950, "#546e7a", "building"),
    ("热带雨林国家公园核心区\n(五指山/霸王岭生态碳汇)", 109.680, 18.900, "#2e7d32", "ecology")
]

for name, lon, lat, color, cat in zones_13:
    x, y = to_alb(lon, lat)
    ax.plot(x, y, 'h', color=color, markersize=8.5, markeredgecolor='white', markeredgewidth=1.2, zorder=18)
    # 智能微调位置避免压盖
    dy = 4500 if lat < 19.0 else (-5000 if lat > 19.8 else 4500)
    dx = -6000 if lon < 109.2 else (6000 if lon > 110.2 else 0)
    ax.text(x + dx, y + dy, name, fontsize=6.8, fontweight='bold', color=color, ha='center',
            path_effects=[pe.withStroke(linewidth=2.0, foreground='white')], zorder=20)

# 特色热带高效农业标注（带箭头）
agri_points = [
    ("三亚芒果 (国家地理标志)", 109.30, 18.42),
    ("文昌鸡 (海南四大名菜之首)", 110.65, 19.70),
    ("万宁兴隆咖啡与东山羊", 110.35, 18.72),
    ("澄迈桥头地瓜与福山咖啡", 110.02, 19.80),
    ("昌江芒果与木棉之乡", 109.10, 19.20),
    ("琼中绿橙 (高山富硒名产)", 109.80, 19.10),
    ("白沙绿茶与陨石坑名茶", 109.40, 19.25),
    ("乐东哈密瓜与南繁制种", 109.05, 18.65)
]
for aname, alon, alat in agri_points:
    x, y = to_alb(alon, alat)
    ax.plot(x, y, '*', color='#2e7d32', markersize=5.0, markeredgecolor='white', zorder=15)
    ax.text(x, y - 3600, aname, fontsize=6.2, color='#1b5e20', ha='center',
            path_effects=[pe.withStroke(linewidth=1.6, foreground='white')], zorder=16)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.set_title("海南自由贸易港重点园区与特色现代产业空间格局图", fontsize=12.2, fontweight='bold', color='#1a237e', pad=12)
mapkit.add_scalebar(ax, ax_xlim[0] + pad_x * 0.8, ax_ylim[0] + pad_y * 0.8, length_km=50)
add_compass(ax, 0.94, 0.93)

draw_sansha_inset(fig, [0.73, 0.09, 0.23, 0.30])

f4_out = os.path.join(OUT_DIR, "fig20-00-4_海南自由贸易港重点园区与特色现代产业空间格局图.png")
plt.savefig(f4_out, dpi=DPI, bbox_inches='tight')
plt.close(fig)
print(f" Saved: {f4_out}")


# =========================================================================
# 5. 夜间灯光演化与自贸港开发强度对比图 (fig20-00-5)
# =========================================================================
print("Rendering fig20-00-5: Hainan nightlight 1986-2024 & development intensity...")
nl_file = os.path.join(DATA_DIR, "hainan_nightlight_clean.csv")
nl_df = pd.read_csv(nl_file)
if "unit_code" in nl_df.columns:
    nl_df.rename(columns={"unit_code": "adcode", "sum": "dn_sum"}, inplace=True)
nl_df["year"] = nl_df["year"].astype(int)

fig = plt.figure(figsize=(11.5, 8.5), dpi=DPI)
fig.patch.set_facecolor('#ffffff')

# 上半部：全省历年夜光演化折线与里程碑
ax_top = fig.add_axes([0.08, 0.54, 0.88, 0.40])
ax_top.set_facecolor('#fdfdfd')

# 按年份汇总全省夜光总量
prov_annual = nl_df.groupby("year")["dn_sum"].sum().reset_index()

years = prov_annual["year"].values
dn_vals = prov_annual["dn_sum"].values

ax_top.plot(years, dn_vals, color='#1565c0', linewidth=2.8, marker='o', markersize=4.5,
            markerfacecolor='#d32f2f', markeredgecolor='white', label='海南全省夜光辐射总量 (DN Sum)')
ax_top.fill_between(years, 0, dn_vals, color='#1565c0', alpha=0.12)

# 历史重大里程碑标注
milestones = [
    (1988, "1988年：海南正式建省\n设立全国最大经济特区"),
    (2001, "2001年：博鳌亚洲论坛\n成立大会隆重召开"),
    (2009, "2009年：国务院发布意见\n推进海南国际旅游岛建设"),
    (2015, "2015年：全球首条\n环岛高铁全线闭环贯通"),
    (2018, "2018年：支持海南建设\n自由贸易试验区"),
    (2020, "2020年：《海南自由贸易港\n建设总体方案》公布实施")
]
for yr, text in milestones:
    if yr in years:
        idx = list(years).index(yr)
        val = dn_vals[idx]
        ax_top.plot([yr, yr], [0, val + 15000], linestyle='--', color='#d84315', linewidth=1.1, alpha=0.7)
        ax_top.scatter([yr], [val], color='#d84315', s=35, zorder=10)
        ax_top.text(yr, val + 20000, text, fontsize=6.8, fontweight='bold', color='#bf360c', ha='center',
                    bbox=dict(boxstyle="round,pad=0.25", facecolor="#fff8e1", edgecolor="#ffb300", alpha=0.9))

ax_top.set_title("海南省1986—2024年夜间灯光辐射演变与自由贸易港腾飞轨迹", fontsize=11.5, fontweight='bold', color='#1a237e', pad=10)
ax_top.set_ylabel("夜间灯光辐射总指数 (DN Sum)", fontsize=8.0, color='#37474f')
ax_top.grid(True, linestyle=':', alpha=0.6)
ax_top.set_xlim(1985, 2025)
ax_top.set_ylim(0, max(dn_vals) * 1.35)
ax_top.tick_params(labelsize=7.5)

# 下半部左侧：19 个市县 2024 年夜光总量横向对比
ax_bl = fig.add_axes([0.08, 0.08, 0.40, 0.38])
ax_bl.set_facecolor('#fdfdfd')

# 提取 2024（或最新年份）各个市县的灯光值
df_latest = nl_df[nl_df["year"] == nl_df["year"].max()].sort_values("dn_sum", ascending=True)
city_names = [HAINAN_CONFIGS.get(str(ad), {}).get("name", str(ad)) for ad in df_latest["adcode"]]
dn_latest = df_latest["dn_sum"].values

bar_colors = ['#c62828' if n in ['海口市', '三亚市', '儋州市'] else '#1976d2' for n in city_names]
bars = ax_bl.barh(range(len(city_names)), dn_latest, color=bar_colors, height=0.65, alpha=0.85)
ax_bl.set_yticks(range(len(city_names)))
ax_bl.set_yticklabels(city_names, fontsize=6.5)
ax_bl.set_xlabel("2024年夜间灯光辐射总值", fontsize=7.5, color='#37474f')
ax_bl.set_title("19个市县夜光辐射总量对比（红色为地级市）", fontsize=9.2, fontweight='bold', color='#1a237e')
ax_bl.grid(True, axis='x', linestyle=':', alpha=0.6)
ax_bl.tick_params(labelsize=6.8)

# 下半部右侧：三大发展极核夜光占比与经济拉动分析
ax_br = fig.add_axes([0.56, 0.08, 0.40, 0.38])
ax_br.set_facecolor('#fdfdfd')

# 分组计算三大极核夜光时序：海口经济圈、三亚经济圈、儋洋先行区
hk_codes = [460100, 469005, 469021, 469022, 469023, 469024]
sy_codes = [460200, 469027, 469028, 469029, 469006]
dy_codes = [460400, 469007, 469026]

nl_df_hk = nl_df[nl_df["adcode"].isin(hk_codes)].groupby("year")["dn_sum"].sum()
nl_df_sy = nl_df[nl_df["adcode"].isin(sy_codes)].groupby("year")["dn_sum"].sum()
nl_df_dy = nl_df[nl_df["adcode"].isin(dy_codes)].groupby("year")["dn_sum"].sum()

c_years = nl_df_hk.index
ax_br.plot(c_years, nl_df_hk.values, color='#1565c0', linewidth=2.0, label='海口经济圈 (北极核)')
ax_br.plot(c_years, nl_df_sy.values, color='#f57f17', linewidth=2.0, label='三亚经济圈 (南极核)')
ax_br.plot(c_years, nl_df_dy.values, color='#2e7d32', linewidth=2.0, label='儋洋先行区 (西极核)')

ax_br.set_title("三大核心发展极夜光时序演进对比（1986—2024）", fontsize=9.2, fontweight='bold', color='#1a237e')
ax_br.set_xlabel("年份", fontsize=7.5, color='#37474f')
ax_br.set_ylabel("区域夜光辐射总值", fontsize=7.5, color='#37474f')
ax_br.legend(fontsize=7.0, loc='upper left', framealpha=0.9)
ax_br.grid(True, linestyle=':', alpha=0.6)
ax_br.tick_params(labelsize=6.8)

f5_out = os.path.join(OUT_DIR, "fig20-00-5_海南省1986-2024年夜间灯光演化与自贸港开发强度对比图.png")
plt.savefig(f5_out, dpi=DPI, bbox_inches='tight')
plt.close(fig)
print(f" Saved: {f5_out}")

print("All 5 Hainan overview figures generated successfully!")
