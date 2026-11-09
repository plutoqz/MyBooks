# -*- coding: utf-8 -*-
"""西藏自治区地理统揽专题地图生成引擎（34-00）
包含 5 幅全省/全区域权威出版级地图与分析图表（精细调优排版、微缩字号、严格杜绝压盖）：
1. fig34-00-1_西藏自治区地形地貌与“世界屋脊”山盆格局图.png
2. fig34-00-2_西藏自治区行政区划与“一核一圈两带”城镇空间格局图.png
3. fig34-00-3_西藏自治区综合立体交通网与高原进出藏大通道图.png
4. fig34-00-4_西藏自治区现代产业体系与国家清洁能源接续基地布局图.png
5. fig34-00-5_西藏自治区生态安全屏障与“亚洲水塔”河湖水系图.png
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

def add_scalebar(ax, x0, y0, length_km=300):
    mapkit.add_scalebar(ax, x0, y0, length_km=length_km)

def add_compass(ax, x=0.94, y=0.92):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.055), transform=ax.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=1.8, headwidth=5.5, headlength=6.5),
                ha="center", va="center", fontsize=8.8, fontweight="bold", color="#2c3e50", zorder=30)

print("Loading Xizang provincial spatial data...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
xz_prov = gpd.read_file(os.path.join(DATA_DIR, "boundaries", "datav", "540000_full.json")).to_crs(ALBERS)
xz_prov["geometry"] = xz_prov.geometry.buffer(0)
xz_union = xz_prov.union_all()
bb = xz_prov.total_bounds

span_x = bb[2] - bb[0]
span_y = bb[3] - bb[1]
pad_x = span_x * 0.04
pad_y = span_y * 0.04
ax_xlim = (bb[0] - pad_x, bb[2] + pad_x)
ax_ylim = (bb[1] - pad_y, bb[3] + pad_y)

# 加载并降采样 DEM 提高制图效率与清晰度
print("Loading Xizang DEM...")
dem_data = np.load(os.path.join(DATA_DIR, "dem", "province", "540000_z9.npz"))
step = 4
dem_raw = dem_data['dem'][::step, ::step]
dem_res = float(dem_data['res']) * step
dem_minx = float(dem_data['minx'])
dem_maxy = float(dem_data['maxy'])
print(f"Downsampled DEM shape: {dem_raw.shape}, res: {dem_res}m")

extent = (dem_minx, dem_minx + dem_raw.shape[1] * dem_res,
          dem_maxy - dem_raw.shape[0] * dem_res, dem_maxy)

hs = calc_hillshade(dem_raw, dem_res)
norm = Normalize(vmin=150.0, vmax=8848.86)

terrain_colors = [
    (0.00, "#196f3d"),   # 150m 墨脱察隅亚热带低河谷
    (0.12, "#27ae60"),   # 1500m 藏东南暖温带河谷针阔混交林
    (0.25, "#7dcea0"),   # 3000m 雅江主要农耕区宽谷
    (0.42, "#f9e79f"),   # 4000m 高原草甸浅原
    (0.58, "#d4ac0d"),   # 4800m 羌塘高寒草甸湖盆
    (0.72, "#ba4a00"),   # 5500m 高山冻原流石滩
    (0.85, "#78281f"),   # 6500m 极高山冰缘带
    (0.94, "#d7bde2"),   # 7500m 现代大型山谷冰川线
    (1.00, "#ffffff")    # 8848m 珠穆朗玛峰顶终年积雪
]
terrain_cmap = LinearSegmentedColormap.from_list("xz_dem", terrain_colors)
dem_rgb = terrain_cmap(norm(dem_raw))[:, :, :3]
shaded_rgb = dem_rgb * (0.42 + 0.58 * hs[:, :, np.newaxis])

FIGSIZE = (9.8, 7.5)

# =============================================================================
# 图 34-00-1：西藏自治区地形地貌与“世界屋脊”山盆格局图
# =============================================================================
print("Generating Fig 34-00-1 (Topography)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

im = ax.imshow(shaded_rgb, extent=extent, origin="upper", zorder=2)
patch = get_mpl_clip_patch(xz_union)
ax.add_patch(patch)
im.set_clip_path(patch)

xz_prov.boundary.plot(ax=ax, color="#2c3e50", lw=0.6, ls="--", zorder=5)
gpd.GeoSeries([xz_union], crs=ALBERS).boundary.plot(ax=ax, color="#1a5276", lw=1.5, zorder=6)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl1 = mapkit.SymbolLabels(ax, fig)
sl1.reserve([(0.0, 0.0, 0.38, 0.30),      # 左下角放图例
             (0.48, 0.0, 1.0, 0.09),      # 比例尺
             (0.90, 0.84, 1.0, 1.0)])     # 指北针

peaks_data = [
    ("珠穆朗玛峰 (8848.86m 世界第一极高峰)", 86.925, 27.988, "mt", "喜马拉雅山脉主峰·中尼界峰"),
    ("洛子峰 (8516m 世界第四高峰)", 86.933, 27.962, "mt", "珠峰南侧卫峰·极高山冰川发育"),
    ("希夏邦马峰 (8027m 唯一全在华8000m级)", 85.779, 28.353, "mt", "喜马拉雅中段巨峰·高山科考胜地"),
    ("南迦巴瓦峰 (7782m 雅鲁藏布大拐弯之巅)", 95.033, 29.628, "mt", "中国最美雪山·世界最深峡谷谷壁"),
    ("纳木那尼峰 (7694m 藏西神女峰)", 81.300, 30.430, "mt", "喜马拉雅西段巍峨雪峰·圣湖伴侍"),
    ("库拉岗日峰 (7538m 喜马拉雅中部名山)", 90.620, 28.230, "mt", "山南南部界山·大型山谷冰川"),
    ("念青唐古拉峰 (7162m 念青唐古拉主峰)", 90.650, 30.380, "mt", "藏南与藏北地理气候大分界"),
    ("冈仁波齐峰 (6656m 众神之山冈底斯主峰)", 81.312, 31.067, "mt", "世界级宗教朝圣圣地·四大江河发源"),
    ("普若岗日冰原 (6482m 中低纬最大冰原)", 89.200, 33.900, "mt", "羌塘腹地固体水库·极高寒大陆冰原"),
    ("巴昔卡雅鲁藏布出境处 (152m 全区最低点)", 95.300, 28.150, "basin", "印度洋暖湿气流大通道·水热充沛")
]

for name, lon, lat, ptype, note in peaks_data:
    px, py = to_alb(lon, lat)
    m = "^" if ptype == "mt" else "v"
    c = "#78281f" if ptype == "mt" else "#1b4f72"
    sl1.add(px, py, name, ptype, note=note, priority=1, marker=m, face=c, size=6.8,
            kind_label="世界极高峰 / 著名神山" if ptype == "mt" else "区域最低洼点 / 峡谷出口")

waters_data = [
    ("雅鲁藏布江干流 (西藏第一大河/高原母亲河)", 89.500, 29.300, 0),
    ("色林错 (西藏第一大咸水湖 2391km²)", 89.000, 31.800, 0),
    ("纳木错 (世界最高大型咸水湖 2026km²)", 90.600, 30.750, 0),
    ("羊卓雍错 (珊瑚枝状高原碧玉圣湖)", 90.700, 28.950, 0),
    ("玛旁雍错 (三大圣湖之首/万水之母)", 81.500, 30.680, 0),
    ("班公错 (半淡半咸国际著名裂谷湖)", 79.200, 33.700, 0),
    ("金沙江干流 (藏川两省天然界河)", 98.850, 31.200, 0),
    ("怒江上游那曲河 (横贯藏北高寒湿地)", 92.200, 31.500, 0)
]

for name, lon, lat, rot in waters_data:
    wx, wy = to_alb(lon, lat)
    sl1.add(wx, wy, name, "water", priority=2, marker="o", face="#1f618d", size=6.0, kind_label="主要江河干流 / 高原圣湖")

sym_type_h, sym_idx_h = sl1.flush()

sb_x0 = ax_xlim[0] + (ax_xlim[1] - ax_xlim[0]) * 0.55
sb_y0 = ax_ylim[0] + (ax_ylim[1] - ax_ylim[0]) * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=300)
add_compass(ax, 0.94, 0.91)

cax = ax.inset_axes([0.04, 0.07, 0.024, 0.22])
cb = plt.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=terrain_cmap), cax=cax, orientation="vertical")
cb.set_label("高程 Elevation (m)", fontsize=6.8, color="#2c3e50")
cb.ax.tick_params(labelsize=6.0, length=2.0)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="地形与水系要素", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="图上要素编号对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("西藏自治区地形地貌与“世界屋脊”山盆格局图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Geomorphology, Alpine Glaciers & Basin Topography of Xizang Autonomous Region", transform=ax.transAxes,
        ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：AWS Terrain GLO-30 DEM · 投影：Albers 等积圆锥 (中央经线 105°E) · 制作：《中国地理知识手册》",
    fontsize=6.5)

m1_path = os.path.join(OUT_DIR, "fig34-00-1_西藏自治区地形地貌与“世界屋脊”山盆格局图.png")
fig.savefig(m1_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"Map 1 saved: {m1_path}")

# =============================================================================
# 图 34-00-2：西藏自治区行政区划与“一核一圈两带”城镇空间格局图
# =============================================================================
print("Generating Fig 34-00-2 (Administration & Urban Hierarchy)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

palette = [
    "#d4efdf", "#fadbd8", "#d6eaf8", "#fcf3cf",
    "#ebdef0", "#e8f8f5", "#fdebd0"
]

for i, (_, row) in enumerate(xz_prov.iterrows()):
    color = palette[i % len(palette)]
    gpd.GeoSeries([row.geometry], crs=ALBERS).plot(ax=ax, facecolor=color, edgecolor="#7f8c8d", lw=0.6, zorder=3)

gpd.GeoSeries([xz_union], crs=ALBERS).boundary.plot(ax=ax, color="#1a5276", lw=1.6, zorder=6)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl2 = mapkit.SymbolLabels(ax, fig)
sl2.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.48, 0.0, 1.0, 0.09),
             (0.90, 0.84, 1.0, 1.0)])

admin_centers = [
    ("拉萨市 (城关区 · 自治区首府)", 91.132, 29.660, "core", "自治区政治经济文化中心·高原历史名城"),
    ("日喀则市 (桑珠孜区 · 后藏中心)", 88.880, 29.268, "sub", "后藏政治文化枢纽·珠峰门户·中尼陆路通道"),
    ("昌都市 (卡若区 · 藏东门户)", 97.180, 31.140, "sub", "三江并流重镇·川滇藏交界枢纽·清洁能源高地"),
    ("林芝市 (巴宜区八一镇 · 西藏江南)", 94.360, 29.650, "node", "雅江大峡谷门户·生态旅游与现代林果名城"),
    ("山南市 (乃东区泽当镇 · 藏源雅砻)", 91.770, 29.240, "node", "藏民族发祥地·雅江中游清洁能源基地"),
    ("那曲市 (色尼区那曲镇 · 藏北重镇)", 92.060, 31.480, "node", "羌塘草原核心·青藏公路铁路物流集散大中枢"),
    ("阿里地区 (噶尔县狮泉河镇 · 天上阿里)", 80.100, 32.500, "node", "万山之祖百川之源·冈仁波齐圣地·边防重镇")
]

for name, lon, lat, ctype, note in admin_centers:
    cx, cy = to_alb(lon, lat)
    m = "*" if ctype == "core" else ("D" if ctype == "sub" else "s")
    c = "#78281f" if ctype == "core" else ("#1b4f72" if ctype == "sub" else "#935116")
    sz = 9.0 if ctype == "core" else (7.2 if ctype == "sub" else 6.2)
    sl2.add(cx, cy, name, ctype, note=note, priority=1, marker=m, face=c, size=sz,
            kind_label="自治区首府核心核" if ctype == "core" else ("区域中心城市" if ctype == "sub" else "地市州府骨干节点"))

counties_data = [
    ("江孜县 (红河谷英雄古城)", 89.600, 28.910),
    ("吉隆县 (中尼国际陆路口岸)", 85.290, 28.850),
    ("亚东县 (喜马拉雅南麓边贸口岸)", 88.900, 27.480),
    ("墨脱县 (雅江大峡谷热带秘境)", 95.330, 29.330),
    ("波密县 (冰川森林桃花胜地)", 95.770, 29.860),
    ("察隅县 (藏东南水汽充沛林区)", 97.460, 28.660),
    ("贡嘎县 (拉萨空港门户重地)", 90.980, 29.290),
    ("加查县 (雅江中游峡谷水电节点)", 92.580, 29.140),
    ("当雄县 (念青唐古拉与纳木错南岸)", 91.100, 30.480),
    ("安多县 (唐古拉山脚下天路第一县)", 91.680, 32.260),
    ("普兰县 (神山圣湖国际口岸)", 81.180, 30.300),
    ("札达县 (古格王朝与象泉河土林)", 79.800, 31.480),
    ("日土县 (班公错鸟岛生态走廊)", 79.720, 33.230),
    ("类乌齐县 (高山森林与纯种牦牛基地)", 96.600, 31.210),
    ("芒康县 (滇藏川交界古盐田与红酒)", 98.600, 29.680)
]

for cname, clon, clat in counties_data:
    cx, cy = to_alb(clon, clat)
    sl2.add(cx, cy, cname, "county", priority=2, marker="o", face="#27ae60", size=5.0, kind_label="重要区县 / 战略要邑")

sym_type_h, sym_idx_h = sl2.flush()

sb_x0 = ax_xlim[0] + (ax_xlim[1] - ax_xlim[0]) * 0.55
sb_y0 = ax_ylim[0] + (ax_ylim[1] - ax_ylim[0]) * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=300)
add_compass(ax, 0.94, 0.91)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="城镇等级与行政中心", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="行政单元与要邑对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("西藏自治区行政区划与“一核一圈两带”城镇空间格局图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Administrative Divisions & Urban Spatial Hierarchy of Xizang Autonomous Region", transform=ax.transAxes,
        ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：天地图·民政部标准地名数据 · 投影：Albers 等积圆锥 (中央经线 105°E) · 制作：《中国地理知识手册》",
    fontsize=6.5)

m2_path = os.path.join(OUT_DIR, "fig34-00-2_西藏自治区行政区划与“一核一圈两带”城镇空间格局图.png")
fig.savefig(m2_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"Map 2 saved: {m2_path}")

# =============================================================================
# 图 34-00-3：西藏自治区综合立体交通网与高原进出藏大通道图
# =============================================================================
print("Generating Fig 34-00-3 (Transportation & Corridors)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

xz_prov.plot(ax=ax, facecolor="#f8f9fa", edgecolor="#bdc3c7", lw=0.6, zorder=2)
gpd.GeoSeries([xz_union], crs=ALBERS).boundary.plot(ax=ax, color="#2c3e50", lw=1.4, zorder=4)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl3 = mapkit.SymbolLabels(ax, fig)
sl3.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.48, 0.0, 1.0, 0.09),
             (0.90, 0.84, 1.0, 1.0)])

# 铁路骨干网络示意
rail_coords = [
    # 青藏铁路 (西宁-那曲-当雄-拉萨)
    [to_alb(91.90, 32.88), to_alb(91.68, 32.26), to_alb(92.06, 31.48), to_alb(91.10, 30.48), to_alb(91.06, 29.62)],
    # 拉日铁路 (拉萨-曲水-尼木-日喀则)
    [to_alb(91.06, 29.62), to_alb(90.74, 29.35), to_alb(90.16, 29.43), to_alb(88.92, 29.28)],
    # 拉林铁路 (拉萨-贡嘎-扎囊-山南-加查-朗县-米林-林芝)
    [to_alb(91.06, 29.62), to_alb(90.98, 29.29), to_alb(91.74, 29.23), to_alb(92.58, 29.14), to_alb(94.22, 29.22), to_alb(94.34, 29.60)]
]

for rline in rail_coords:
    xs, ys = mapkit.smooth_line(rline)
    ax.plot(xs, ys, color="#154360", lw=2.4, zorder=7, ls="-")
    ax.plot(xs, ys, color="#ffffff", lw=1.0, zorder=8, ls="--")

# 高等级公路网络 (G6拉那高速、拉林高等级、泽贡高速等)
hwy_coords = [
    [to_alb(92.06, 31.48), to_alb(91.50, 30.80), to_alb(91.10, 30.48), to_alb(91.00, 29.65)], # G6拉那段
    [to_alb(91.13, 29.66), to_alb(92.35, 29.84), to_alb(93.24, 29.88), to_alb(94.36, 29.65)], # 拉林高等级
    [to_alb(91.13, 29.66), to_alb(90.98, 29.29), to_alb(91.77, 29.24)]                          # 泽贡高等级
]

for hline in hwy_coords:
    xs, ys = mapkit.smooth_line(hline)
    ax.plot(xs, ys, color="#c0392b", lw=2.0, zorder=6, alpha=0.9)

# 进出藏国道大动脉干线 (G318, G109, G219, G317, G214)
g_corridors = [
    ("G318 川藏南线 (上海至友谊桥/中国最美国道)", 93.50, 29.85, 30),
    ("G109 青藏公路 (京拉线/世界屋脊生命线)", 91.80, 32.10, 45),
    ("G219 新藏公路 (叶城至拉孜/喀喇昆仑边防天路)", 80.50, 32.00, 45),
    ("G317 川藏北线 (那曲至昌都至成都)", 94.50, 31.80, 30),
    ("G214 滇藏公路 (芒康经昌都出青海玉树)", 98.20, 30.80, 50)
]

for gname, glon, glat, grot in g_corridors:
    gx, gy = to_alb(glon, glat)
    sl3.add(gx, gy, gname, "corridor", priority=2, marker="D", face="#e67e22", size=5.0, kind_label="进出藏国道干线走廊")

airports_data = [
    ("拉萨贡嘎国际机场 (4E级高原区域枢纽/年吞吐>500万人次)", 90.850, 29.298, "国际/大型机场"),
    ("林芝米林机场 (4D级最险盲降高高原机场)", 94.335, 29.303, "支线骨干机场"),
    ("昌都邦达机场 (4C级海拔4334m世界顶级高高原航港)", 97.310, 30.550, "支线骨干机场"),
    ("日喀则和平机场 (4E级军民合用高高原机场)", 89.310, 29.350, "支线骨干机场"),
    ("阿里昆莎机场 (4D级打破天上阿里交通绝境)", 80.050, 32.100, "支线骨干机场"),
    ("山南隆子机场 (4C级高高原边境新机场)", 92.540, 28.410, "支线骨干机场"),
    ("阿里普兰机场 (4C级边境空中通道新门户)", 81.150, 30.330, "支线骨干机场")
]

for aname, alon, alat, anote in airports_data:
    ax_pt, ay_pt = to_alb(alon, alat)
    sl3.add(ax_pt, ay_pt, aname, "air", note=anote, priority=1, marker="^", face="#8e44ad", size=7.2,
            kind_label="民用运输机场 (一干六支全网覆盖)")

rail_stations = [
    ("拉萨站 (青藏/拉日/拉林铁路核心总枢纽)", 91.065, 29.625),
    ("日喀则站 (拉日铁路后藏终点站)", 88.920, 29.280),
    ("林芝站 (拉林铁路林芝终点站/川藏雅林段在建)", 94.340, 29.600),
    ("那曲站 (青藏铁路藏北物流最大枢纽站)", 92.050, 31.460),
    ("山南站 (拉林铁路重要节点客运站)", 91.740, 29.230)
]

for sname, slon, slat in rail_stations:
    sx, sy = to_alb(slon, slat)
    sl3.add(sx, sy, sname, "rail", priority=1, marker="s", face="#154360", size=6.5, kind_label="主要铁路枢纽车站")

sym_type_h, sym_idx_h = sl3.flush()

sb_x0 = ax_xlim[0] + (ax_xlim[1] - ax_xlim[0]) * 0.55
sb_y0 = ax_ylim[0] + (ax_ylim[1] - ax_ylim[0]) * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=300)
add_compass(ax, 0.94, 0.91)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="立体交通枢纽与通道", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="交通基础设施编号对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("西藏自治区综合立体交通网与高原进出藏大通道图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Comprehensive Transportation Network & Strategic In/Outbound Corridors of Xizang", transform=ax.transAxes,
        ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：中国国家铁路集团·交通运输部·OSM · 投影：Albers 等积圆锥 (中央经线 105°E) · 制作：《中国地理知识手册》",
    fontsize=6.5)

m3_path = os.path.join(OUT_DIR, "fig34-00-3_西藏自治区综合立体交通网与高原进出藏大通道图.png")
fig.savefig(m3_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"Map 3 saved: {m3_path}")

# =============================================================================
# 图 34-00-4：西藏自治区现代产业体系与国家清洁能源接续基地布局图
# =============================================================================
print("Generating Fig 34-00-4 (Industries & Clean Energy)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

xz_prov.plot(ax=ax, facecolor="#fdfefe", edgecolor="#bdc3c7", lw=0.6, zorder=2)
gpd.GeoSeries([xz_union], crs=ALBERS).boundary.plot(ax=ax, color="#1a5276", lw=1.5, zorder=4)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl4 = mapkit.SymbolLabels(ax, fig)
sl4.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.48, 0.0, 1.0, 0.09),
             (0.90, 0.84, 1.0, 1.0)])

energy_bases = [
    ("藏木水电站 (雅江干流首座51万千瓦大型水电)", 92.520, 29.180, "clean", "西藏第一座大型水电站·稳定电网基荷"),
    ("苏洼龙水电站 (金沙江上游120万千瓦梯级水电)", 99.050, 29.400, "clean", "藏川清洁能源互联外送枢纽"),
    ("羊八井地热电站 (中国最大地热能源科研开发基地)", 90.520, 30.080, "clean", "全国地热发电先驱·高原绿色供暖"),
    ("欧玛亭嘎风电场 (全球最高海拔风电基地 100MW)", 92.150, 31.400, "clean", "高海拔超低风阻大容量风机技术标杆"),
    ("才朋光伏电站 (全球最高海拔光伏电站 5000m+)", 91.550, 29.050, "clean", "山南雅江沿岸超级光伏清洁能源走廊"),
    ("玉龙铜矿工业基地 (全国第二大铜矿/现代绿色采选)", 97.750, 31.250, "mining", "藏东有色金属与新材料循环经济支柱")
]

for ename, elon, elat, etype, enote in energy_bases:
    ex, ey = to_alb(elon, elat)
    m = "p" if etype == "clean" else "h"
    c = "#117864" if etype == "clean" else "#b9770e"
    sl4.add(ex, ey, ename, etype, note=enote, priority=1, marker=m, face=c, size=7.2,
            kind_label="清洁能源基地 (水/风/光/地热)" if etype == "clean" else "战略绿色矿产产业集群")

tour_cultural = [
    ("布达拉宫与大昭寺 (世界文化遗产名录核心)", 91.120, 29.655, "世界文化遗产"),
    ("珠峰大本营国家公园 (世界第三极极致登山生态探险)", 86.850, 28.140, "国际生态科考"),
    ("雅鲁藏布大峡谷 (世界第一大峡谷/国际生态旅游目的地)", 94.950, 29.550, "自然地貌奇观"),
    ("冈仁波齐与玛旁雍错 (亚洲四大宗教神山圣湖文化区)", 81.350, 30.850, "神山圣湖文化"),
    ("古格王朝与札达土林 (千古遗迹与自然地质胜境)", 79.800, 31.470, "历史遗迹名胜")
]

for tname, tlon, tlat, tnote in tour_cultural:
    tx, ty = to_alb(tlon, tlat)
    sl4.add(tx, ty, tname, "tour", note=tnote, priority=2, marker="*", face="#c0392b", size=7.5, kind_label="世界级文化旅游与生态探险地")

ports_data = [
    ("吉隆口岸 (中国对尼泊尔最大陆路国际贸易通道)", 85.350, 28.400),
    ("樟木口岸 (中尼历史友谊桥经典口岸)", 85.980, 27.990),
    ("普兰口岸 (中尼印三国历史边贸要道)", 81.160, 30.250),
    ("亚东口岸/仁青岗边贸市场 (中印乃堆拉山口前沿)", 88.920, 27.420),
    ("里孜口岸 (中尼第四大陆路开放口岸)", 84.100, 29.300)
]

for pname, plon, plat in ports_data:
    px, py = to_alb(plon, plat)
    sl4.add(px, py, pname, "port", priority=2, marker="D", face="#2874a6", size=5.5, kind_label="国家对外开放口岸 / 边贸通道")

sym_type_h, sym_idx_h = sl4.flush()

sb_x0 = ax_xlim[0] + (ax_xlim[1] - ax_xlim[0]) * 0.55
sb_y0 = ax_ylim[0] + (ax_ylim[1] - ax_ylim[0]) * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=300)
add_compass(ax, 0.94, 0.91)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="清洁能源与重点产业布局", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="重点基地与口岸要素对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("西藏自治区现代产业体系与国家清洁能源接续基地布局图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Clean Energy Hubs, Modern Industries & Border Ports of Xizang Autonomous Region", transform=ax.transAxes,
        ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：西藏发改委·文旅厅·海关总署 · 投影：Albers 等积圆锥 (中央经线 105°E) · 制作：《中国地理知识手册》",
    fontsize=6.5)

m4_path = os.path.join(OUT_DIR, "fig34-00-4_西藏自治区现代产业体系与国家清洁能源接续基地布局图.png")
fig.savefig(m4_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"Map 4 saved: {m4_path}")

# =============================================================================
# 图 34-00-5：西藏自治区生态安全屏障与“亚洲水塔”河湖水系图
# =============================================================================
print("Generating Fig 34-00-5 (Ecological Barriers & Asian Water Tower)...")
fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig.subplots_adjust(left=0.012, right=0.988, top=0.962, bottom=0.010)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

xz_prov.plot(ax=ax, facecolor="#eaf2f8", edgecolor="#aed6f1", lw=0.6, zorder=2)
gpd.GeoSeries([xz_union], crs=ALBERS).boundary.plot(ax=ax, color="#1b4f72", lw=1.5, zorder=5)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl5 = mapkit.SymbolLabels(ax, fig)
sl5.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.48, 0.0, 1.0, 0.09),
             (0.90, 0.84, 1.0, 1.0)])

eco_reserves = [
    ("羌塘国家级自然保护区 (中国最大陆地生态保护区 29.8万km²)", 86.500, 33.500, "羌塘高寒荒漠·藏羚羊产羔地"),
    ("珠穆朗玛峰国家级自然保护区 (全球海拔最高保护区 3.38万km²)", 86.800, 28.250, "极高山冰川生态·雪豹栖息地"),
    ("雅鲁藏布大峡谷国家级自然保护区 (生物多样性立体宝库)", 95.100, 29.600, "完整垂直自然带·中国生物基因库"),
    ("色林错黑颈鹤国家级自然保护区 (高原水禽繁殖天堂)", 89.100, 31.700, "世界濒危鸟类黑颈鹤核心繁衍地"),
    ("芒康滇金丝猴国家级自然保护区 (横断山旗舰灵长类)", 98.650, 29.300, "雪山精灵滇金丝猴最北分布区"),
    ("雅鲁藏布江中游水产种质资源保护区", 91.500, 29.250, "巨须裂腹鱼/黑斑原鮡特有冷水鱼")
]

for rname, rlon, rlat, rnote in eco_reserves:
    rx, ry = to_alb(rlon, rlat)
    sl5.add(rx, ry, rname, "reserve", note=rnote, priority=1, marker="s", face="#1e8449", size=6.8,
            kind_label="国家级自然保护区 / 国家公园核心区")

river_systems = [
    ("雅鲁藏布江正源杰马央宗冰川 (全长2057km)", 82.200, 30.200, "雅鲁藏布江源头"),
    ("雅江中游宽谷段 (西藏粮食核心灌区)", 90.500, 29.350, "高原现代灌区"),
    ("雅江大拐弯峡谷段 (世界顶级深切大峡谷)", 95.150, 29.750, "高落差清洁水能富集区"),
    ("怒江上游那曲水系 (横贯藏北奔流滇缅)", 93.000, 31.500, "跨界大河上游源流"),
    ("澜沧江扎曲昂曲汇流 (流贯昌都南下湄公河)", 97.200, 31.100, "东南亚国际大河源头"),
    ("金沙江干流峡谷段 (长江干流上游)", 98.900, 30.500, "万里长江正源汇流段"),
    ("狮泉河 (印度河正源/自阿里西出)", 79.800, 32.600, "南亚跨界大河正源"),
    ("象泉河朗钦藏布 (穿札达出境注入印度河)", 79.500, 31.500, "札达土林滋润之河")
]

for riv_name, riv_lon, riv_lat, riv_note in river_systems:
    rx, ry = to_alb(riv_lon, riv_lat)
    sl5.add(rx, ry, riv_name, "river", note=riv_note, priority=2, marker="o", face="#2980b9", size=5.8,
            kind_label="“亚洲水塔”大江大河源流枢纽")

sym_type_h, sym_idx_h = sl5.flush()

sb_x0 = ax_xlim[0] + (ax_xlim[1] - ax_xlim[0]) * 0.55
sb_y0 = ax_ylim[0] + (ax_ylim[1] - ax_ylim[0]) * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=300)
add_compass(ax, 0.94, 0.91)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="生态屏障与水系源头要素", ncol=1, fontsize=6.8, title_fontsize=7.6),
    dict(handles=sym_idx_h, title="自然保护地与大河源流对照", ncol=2, fontsize=6.6, title_fontsize=7.6),
], top=-0.010, gap=0.012)

ax.set_title("西藏自治区生态安全屏障与“亚洲水塔”河湖水系图", fontsize=12.5, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Ecological Security Barriers & Asian Water Tower Catchments of Xizang", transform=ax.transAxes,
        ha="center", va="bottom", fontsize=7.5, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：生态环境部·水利部水资源公报 · 投影：Albers 等积圆锥 (中央经线 105°E) · 制作：《中国地理知识手册》",
    fontsize=6.5)

m5_path = os.path.join(OUT_DIR, "fig34-00-5_西藏自治区生态安全屏障与“亚洲水塔”河湖水系图.png")
fig.savefig(m5_path, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"Map 5 saved: {m5_path}")

print("\nAll 5 Xizang provincial overview maps generated successfully!")
