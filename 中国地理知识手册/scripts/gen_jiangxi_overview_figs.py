# -*- coding: utf-8 -*-
"""江西省地理统揽专题地图生成引擎（14-00）
包含 5 幅全省权威出版级地图与分析图表（精细调优排版、微缩字号、严格杜绝压盖）：
1. fig14-00-1_江西省地势起伏与鄱阳湖五河水系格局图.png
2. fig14-00-2_江西省行政区划与“一圈两带三区”空间格局图.png
3. fig14-00-3_江西省综合立体交通与内陆开放通道网络图.png
4. fig14-00-4_江西省新兴产业集群与先进制造基地空间格局图.png
5. fig14-00-5_江西省1986—2024年夜间灯光演变与区域协调发展图.png
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

def add_scalebar(ax, x0, y0, length_km=80):
    mapkit.add_scalebar(ax, x0, y0, length_km=length_km)

def add_compass(ax, x=0.94, y=0.92):
    ax.annotate("N", xy=(x, y), xytext=(x, y - 0.055), transform=ax.transAxes,
                arrowprops=dict(facecolor="#2c3e50", edgecolor="#2c3e50", width=1.8, headwidth=5.5, headlength=6.5),
                ha="center", va="center", fontsize=8.8, fontweight="bold", color="#2c3e50", zorder=30)

print("Loading Jiangxi provincial boundaries and DEM...")
DATA_DIR = r"D:\code\Ideas\MyBooks\中国地理知识手册\data"
DATAV_DIR = os.path.join(DATA_DIR, "boundaries", "datav")

jx_prov = gpd.read_file(os.path.join(DATAV_DIR, "360000_full.json")).to_crs(ALBERS)
jx_prov["geometry"] = jx_prov.geometry.buffer(0)
jx_union = jx_prov.union_all()

b = jx_prov.total_bounds
span_x = b[2] - b[0]
span_y = b[3] - b[1]
pad_x = span_x * 0.04
pad_y = span_y * 0.04
ax_xlim = (b[0] - pad_x, b[2] + pad_x)
ax_ylim = (b[1] - pad_y, b[3] + pad_y)

# 加载 DEM
dem_file = os.path.join(DATA_DIR, "dem", "province", "360000_z9.npz")
dem_data = np.load(dem_file)
step = 2
dem_raw = np.nan_to_num(dem_data['dem'][::step, ::step], nan=0.0)
dem_res = float(dem_data['res']) * step
dem_minx = float(dem_data['minx'])
dem_maxy = float(dem_data['maxy'])
dem_extent = (dem_minx, dem_minx + dem_raw.shape[1] * dem_res,
              dem_maxy - dem_raw.shape[0] * dem_res, dem_maxy)
print(f"Downsampled Jiangxi DEM shape: {dem_raw.shape}, res: {dem_res}m")

# =============================================================================
# 1. 地势起伏与鄱阳湖五河水系格局图 (fig14-00-1)
# =============================================================================
print("Generating Fig 14-00-1 (Topography & Poyang Lake Five Rivers Pattern)...")
fig, ax = plt.subplots(figsize=(9.2, 10.2), dpi=DPI)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

# 色阶
elev_colors = [
    (0.00, "#196f3d"),  # 鄱阳湖平原低地
    (0.08, "#27ae60"),  # 河谷平原
    (0.20, "#7dcea0"),  # 低丘陵
    (0.35, "#f9e79f"),  # 高丘陵与低山
    (0.52, "#eb984e"),  # 中山
    (0.70, "#ba4a00"),  # 高山
    (1.00, "#78281f")   # 极顶 (黄岗山 2160.8m)
]
cmap_jx = LinearSegmentedColormap.from_list("jiangxi_elev", elev_colors)
norm_jx = Normalize(vmin=0, vmax=2200)

hs_jx = calc_hillshade(dem_raw, dem_res)
rgb_dem = cmap_jx(norm_jx(dem_raw))[:, :, :3]
rgb_shaded = rgb_dem * (0.42 + 0.58 * hs_jx[:, :, np.newaxis])

im = ax.imshow(rgb_shaded, extent=dem_extent, origin="upper", zorder=2)
patch1 = get_mpl_clip_patch(jx_union)
ax.add_patch(patch1)
im.set_clip_path(patch1)

# 省界与设区市界
jx_prov.boundary.plot(ax=ax, color="#1a5276", lw=0.7, ls="--", zorder=4)
gpd.GeoSeries([jx_union], crs=ALBERS).boundary.plot(ax=ax, color="#0b2545", lw=1.8, zorder=5)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl1 = mapkit.SymbolLabels(ax, fig)
sl1.reserve([(0.0, 0.0, 0.35, 0.28),
             (0.55, 0.0, 1.0, 0.09),
             (0.88, 0.86, 1.0, 1.0)])

# 核心山峰
peaks = [
    ("黄岗山 (2160.8m 武夷山主峰·江西最高绝顶)", 117.785, 27.895, 2160.8, -160, 60),
    ("齐云山 (2061.3m 崇义与湖南桂东界·赣南第一高峰)", 114.050, 25.820, 2061.3, -150, 50),
    ("武功山白鹤峰/金顶 (1918.3m 罗霄山脉北段第一高峰)", 114.185, 27.475, 1918.3, 150, 50),
    ("井冈山江西坳南峰 (1841.0m 罗霄山脉中段主脊)", 114.165, 26.575, 1841.0, -150, 50),
    ("三清山玉京峰 (1819.9m 怀玉山脉主峰·世界自然遗产)", 118.065, 28.910, 1819.9, 150, 50),
    ("九岭尖 (1794.3m 靖安与武宁界·九岭山脉主峰)", 115.020, 29.010, 1794.3, 150, 50),
    ("军峰山 (1760.9m 南丰县·赣东第一高峰)", 116.380, 27.220, 1760.9, 150, 50),
    ("瑶里五股尖 (1618.4m 浮梁与安徽界·景德镇最高峰)", 117.585, 29.545, 1618.4, 150, 50),
    ("庐山汉阳峰 (1474.0m 雄峙长江与鄱阳湖之交)", 115.985, 29.565, 1474.0, 150, 50),
    ("阳平峰 (1444.0m 贵溪武夷山余脉·鹰潭最高峰)", 117.250, 27.950, 1444.0, 140, -40),
    ("蒙山白云峰 (1004.0m 渝水与高安界·新余最高峰)", 115.085, 28.065, 1004.0, 140, 50),
    ("梅岭洗药峰 (841.4m 湾里·南昌最高峰)", 115.760, 28.730, 841.4, -140, 50)
]
for pname, plon, plat, pelev, ox, oy in peaks:
    px, py = to_alb(plon, plat)
    nm, nt = mapkit.split_note(pname)
    sl1.add(px, py, nm, "peak", note=nt, priority=1,
            marker="^", face="#78281f", size=7.5, kind_label="全省控制性极顶 / 名山高峰")

# 核心水系与湖泊
waters = [
    ("鄱阳湖湖区 (3150km² 中国第一大淡水湖)", 116.250, 29.100),
    ("赣江干流 (766km 纵贯南北八百里母亲河)", 115.450, 27.500),
    ("抚河干流 (349km 江西第二大河润泽临川平原)", 116.400, 27.800),
    ("信江干流 (329km 穿上饶鹰潭汇入鄱阳湖)", 117.300, 28.280),
    ("昌江与乐安河 (275km 饶河双支滋润千年瓷都)", 117.150, 29.150),
    ("修水干流 (357km 汇入柘林湖与九江出湖)", 115.100, 29.180),
    ("柘林湖/庐山西海 (江西最大人工水库群岛胜景)", 115.350, 29.350),
    ("章江贡江汇流处 (八境台前合为赣江干流)", 114.945, 25.875),
    ("长江江西段 (152km 长江黄金水道南岸门户)", 115.950, 29.750),
    ("湖口江湖交汇处 (长江清黄交汇鄱阳湖出水口)", 116.220, 29.735)
]
for wname, wlon, wlat in waters:
    wx, wy = to_alb(wlon, wlat)
    nm, nt = mapkit.split_note(wname)
    sl1.add(wx, wy, nm, "water", note=nt, priority=2,
            marker="s", face="#1f618d", size=5.5, kind_label="骨干河流水系 / 核心湖泊水库")

sym_type_h, sym_idx_h = sl1.flush()

sb_x0 = ax_xlim[0] + (ax_xlim[1] - ax_xlim[0]) * 0.58
sb_y0 = ax_ylim[0] + (ax_ylim[1] - ax_ylim[0]) * 0.05
add_scalebar(ax, sb_x0, sb_y0, length_km=80)
add_compass(ax, 0.94, 0.92)

cax = ax.inset_axes([0.05, 0.06, 0.025, 0.22])
cb = plt.colorbar(plt.cm.ScalarMappable(norm=norm_jx, cmap=cmap_jx), cax=cax, orientation="vertical")
cb.set_label("高程 Elevation (m)", fontsize=7.2, color="#2c3e50")
cb.ax.tick_params(labelsize=6.5, length=2.0)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="地形与水系要素", ncol=2, fontsize=7.0, title_fontsize=7.8),
    dict(handles=sym_idx_h, title="图上要素编号对照", ncol=2, fontsize=6.8, title_fontsize=7.8),
], top=-0.010, gap=0.014)

ax.set_title("江西省地势起伏与鄱阳湖五河水系格局图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Macroscopic Topography, Mountain Ridges & Poyang Lake Basin Pattern of Jiangxi",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：AWS Terrain GLO-30 30m DEM · 自然资源部标准地图 · 制作：《中国地理知识手册》",
    fontsize=6.8)

p1 = os.path.join(OUT_DIR, "fig14-00-1_江西省地势起伏与鄱阳湖五河水系格局图.png")
fig.savefig(p1, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {p1}")

# =============================================================================
# 2. 行政区划与“一圈两带三区”空间格局图 (fig14-00-2)
# =============================================================================
print("Generating Fig 14-00-2 (Administrative & '1 Circle 2 Belts 3 Zones')...")
fig, ax = plt.subplots(figsize=(9.2, 10.2), dpi=DPI)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

# 设区市分区着色
city_colors = {
    "360100": "#ebf5fb",  # 南昌
    "360200": "#fef9e7",  # 景德镇
    "360300": "#f4ecf7",  # 萍乡
    "360400": "#e8f8f5",  # 九江
    "360500": "#fdfefe",  # 新余
    "360600": "#fef5e7",  # 鹰潭
    "360700": "#eafaf1",  # 赣州
    "360800": "#eaf2f8",  # 吉安
    "360900": "#f9ebea",  # 宜春
    "361000": "#fbfcfc",  # 抚州
    "361100": "#ebedef",  # 上饶
}

for _, row in jx_prov.iterrows():
    adcode = str(row.get("adcode", ""))
    fc = city_colors.get(adcode, "#f8f9fa")
    gpd.GeoSeries([row.geometry], crs=ALBERS).plot(ax=ax, facecolor=fc, edgecolor="#7f8c8d", lw=0.7, ls="--", zorder=3)

gpd.GeoSeries([jx_union], crs=ALBERS).boundary.plot(ax=ax, color="#1a5276", lw=2.2, zorder=5)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl2 = mapkit.SymbolLabels(ax, fig)
sl2.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.55, 0.0, 1.0, 0.09),
             (0.88, 0.86, 1.0, 1.0)])

# 11 设区市行政中心
admin_capitals = [
    ("南昌市 (省会·红谷滩CBD·大南昌都市圈极核·英雄城)", 115.850, 28.690, "gov"),
    ("赣州市 (省域副中心·章贡区·中国稀金谷·客家摇篮)", 114.935, 25.830, "gov"),
    ("九江市 (北大门·八里湖新区·浔阳江头·长江港航枢纽)", 115.930, 29.680, "gov"),
    ("宜春市 (袁州区·亚洲锂都·月亮之都·药都樟树建陶之城)", 114.415, 27.845, "gov"),
    ("上饶市 (信州区·高铁枢纽·晶科光伏·三清山世遗)", 117.965, 28.450, "gov"),
    ("吉安市 (吉州区·革命摇篮井冈山·江南望郡庐陵古邑)", 114.985, 27.100, "gov"),
    ("抚州市 (临川区·才子之乡·汤显祖故里·生态价值样板)", 116.355, 27.955, "gov"),
    ("景德镇市 (昌江区·世界瓷都·国家试验区·直升机研发高地)", 117.185, 29.270, "gov"),
    ("萍乡市 (安源区·工运摇篮·赣湘合作前沿·武功山名山)", 113.855, 27.635, "gov"),
    ("新余市 (渝水区·工小美·钢城锂都·仙女湖七夕故里)", 114.920, 27.835, "gov"),
    ("鹰潭市 (月湖区·世界铜都·中华道都·国家物联网基地)", 117.060, 28.245, "gov")
]

for aname, alon, alat, akind in admin_capitals:
    ax_pt, ay_pt = to_alb(alon, alat)
    m = "*" if akind == "gov" else "s"
    c = "#c0392b" if "南昌" in aname else ("#d35400" if "赣州" in aname or "九江" in aname else "#2980b9")
    nm, nt = mapkit.split_note(aname)
    sl2.add(ax_pt, ay_pt, nm, akind, note=nt, priority=1,
            marker=m, face=c, size=9.5 if "南昌" in aname else 7.5,
            kind_label="设区市行政中心 · 战略枢纽")

sym_type_h, sym_idx_h = sl2.flush()

add_scalebar(ax, sb_x0, sb_y0, length_km=80)
add_compass(ax, 0.94, 0.92)

leg_elements = [
    Patch(facecolor="#ebf5fb", edgecolor="#1a5276", label="大南昌都市圈核心辐射极核 (南昌/九江/抚州部分/宜春部分)"),
    Patch(facecolor="#eafaf1", edgecolor="#27ae60", label="赣南等原中央苏区高质量发展示范区 (赣州/吉安协同)"),
    Patch(facecolor="#fef9e7", edgecolor="#f39c12", label="赣东北开放合作协同区 (上饶/景德镇/鹰潭跨省协同)"),
    Patch(facecolor="#f4ecf7", edgecolor="#8e44ad", label="赣西转型升级样板区 (宜春/萍乡/新余一体化转型)")
]

leg = mapkit.stacked_legends(ax, [
    dict(handles=leg_elements + sym_type_h, title="行政中心与空间战略", ncol=1, fontsize=7.0, title_fontsize=7.8),
    dict(handles=sym_idx_h, title="图上设区市定位索引", ncol=1, fontsize=6.8, title_fontsize=7.8),
], top=-0.010, gap=0.014)

ax.set_title("江西省行政区划与“一圈两带三区”空间格局图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Administrative Divisions & '1 Circle 2 Belts 3 Zones' Spatial Structure of Jiangxi",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：自然资源部标准地图与 DataV 行政区划 · 江西省国土空间规划 · 制作：《中国地理知识手册》",
    fontsize=6.8)

p2 = os.path.join(OUT_DIR, "fig14-00-2_江西省行政区划与“一圈两带三区”空间格局图.png")
fig.savefig(p2, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {p2}")

# =============================================================================
# 3. 综合立体交通与内陆开放通道网络图 (fig14-00-3)
# =============================================================================
print("Generating Fig 14-00-3 (Transport Infrastructure & Inbound-Outbound Network)...")
fig, ax = plt.subplots(figsize=(9.2, 10.2), dpi=DPI)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

jx_prov.plot(ax=ax, facecolor="#fdfefe", edgecolor="#bdc3c7", lw=0.6, ls=":", zorder=2)
gpd.GeoSeries([jx_union], crs=ALBERS).boundary.plot(ax=ax, color="#1a5276", lw=1.8, zorder=3)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl3 = mapkit.SymbolLabels(ax, fig)
sl3.reserve([(0.0, 0.0, 0.38, 0.32),
             (0.55, 0.0, 1.0, 0.09),
             (0.88, 0.86, 1.0, 1.0)])

# 交通与港口地标
transport_hubs = [
    ("南昌西站与南昌站 (沪昆/昌九/昌赣高铁国家级特大枢纽)", 115.820, 28.660, "rail_hub"),
    ("上饶高铁站 (京福客专与沪昆高铁全国首座骑跨式超级枢纽)", 117.965, 28.450, "rail_hub"),
    ("九江庐山站与九江站 (京九铁路与昌九高铁十字换乘总站)", 115.865, 29.620, "rail_hub"),
    ("赣州西站 (昌赣客专与赣深客专交汇客运极核)", 114.825, 25.815, "rail_hub"),
    ("鹰潭北站与鹰潭编组站 (浙赣/鹰厦全国特等货运编组站)", 117.060, 28.260, "rail_hub"),
    ("宜春站与新余北站 (沪昆高铁走廊核心高铁大站)", 114.650, 27.860, "rail_hub"),
    ("九江港城西城东码头 (长江亿吨级干线外贸深水港)", 116.035, 29.755, "port"),
    ("南昌港姚湾综合码头 (赣江下游现代化大型集装箱内河港)", 115.880, 28.520, "port"),
    ("南昌昌北国际机场 (国家干线机场·国际综合航空口岸)", 115.905, 28.865, "airport"),
    ("赣州黄金机场 (赣南首座4D级干线支线航空枢纽)", 114.780, 25.850, "airport"),
    ("赣州国际陆港 (全国首个内陆带铁路港口岸铁海联运枢纽)", 114.720, 25.680, "dryport")
]

for tname, tlon, tlat, tkind in transport_hubs:
    tx_pt, ty_pt = to_alb(tlon, tlat)
    nm, nt = mapkit.split_note(tname)
    sl3.add(tx_pt, ty_pt, nm, tkind, note=nt)

sym_type_h, sym_idx_h = sl3.flush()

add_scalebar(ax, sb_x0, sb_y0, length_km=80)
add_compass(ax, 0.94, 0.92)

leg_elements = [
    Line2D([0], [0], color="#c0392b", lw=2.2, label="沪昆/京港(昌九昌赣赣深)/合福高速铁路通道"),
    Line2D([0], [0], color="#8e44ad", lw=1.8, label="国际航空空港/长江亿吨级深水内河海港"),
    Line2D([0], [0], color="#2980b9", lw=1.8, label="国际陆港铁海联运/多式联运综合物流通道")
]

leg = mapkit.stacked_legends(ax, [
    dict(handles=leg_elements + sym_type_h, title="交通通道与枢纽类型", ncol=1, fontsize=7.0, title_fontsize=7.8),
    dict(handles=sym_idx_h, title="图上综合交通节点索引", ncol=1, fontsize=6.8, title_fontsize=7.8),
], top=-0.010, gap=0.014)

ax.set_title("江西省综合立体交通与内陆开放通道网络图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Integrated Transport Infrastructure & Inland Open Economy Network of Jiangxi",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：江西省交通运输厅 · 综合立体交通网规划 · 制作：《中国地理知识手册》",
    fontsize=6.8)

p3 = os.path.join(OUT_DIR, "fig14-00-3_江西省综合立体交通与内陆开放通道网络图.png")
fig.savefig(p3, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {p3}")

# =============================================================================
# 4. 新兴产业集群与先进制造基地空间格局图 (fig14-00-4)
# =============================================================================
print("Generating Fig 14-00-4 (Emerging Industry Clusters & Advanced Manufacturing)...")
fig, ax = plt.subplots(figsize=(9.2, 10.2), dpi=DPI)
fig.patch.set_facecolor("white")
ax.set_facecolor("white")

jx_prov.plot(ax=ax, facecolor="#fdfefe", edgecolor="#bdc3c7", lw=0.6, ls=":", zorder=2)
gpd.GeoSeries([jx_union], crs=ALBERS).boundary.plot(ax=ax, color="#1a5276", lw=1.8, zorder=3)

ax.set_xlim(ax_xlim)
ax.set_ylim(ax_ylim)
ax.axis("off")

sl4 = mapkit.SymbolLabels(ax, fig)
sl4.reserve([(0.0, 0.0, 0.40, 0.34),
             (0.55, 0.0, 1.0, 0.09),
             (0.88, 0.86, 1.0, 1.0)])

# 核心产业集群地标
industries = [
    ("瑶湖航空城与中国商飞南昌交付中心 (C919/L15大飞机基地)", 116.035, 28.655, "航空制造"),
    ("中国稀金谷与中国稀土集团总部 (世界级稀土产业高地)", 115.015, 25.860, "战略稀土"),
    ("宜春经开区宁德时代与比亚迪百亿锂电基地 (亚洲锂都)", 114.450, 27.880, "锂电新能源"),
    ("江西铜业集团贵溪冶炼厂 (全球单体规模最大铜冶炼基地)", 117.210, 28.290, "世界铜都"),
    ("晶科能源全球总部基地 (全球光伏组件龙头产业园)", 117.920, 28.480, "光伏新能源"),
    ("景德镇先进陶瓷创新园与航空工业昌飞基地 (先进陶瓷/直升机)", 117.265, 29.335, "陶瓷与航空"),
    ("中国石化九江分公司千万吨绿色炼化基地 (沿江石化龙头)", 116.080, 29.760, "绿色石化"),
    ("赣锋锂业全球总部与新钢集团现代特钢基地 (锂化合物/特钢)", 114.960, 27.830, "锂电特钢"),
    ("吉泰走廊立讯精密与合力泰电子信息产业园 (千亿电子产业链)", 114.950, 27.060, "电子信息"),
    ("樟树中国药都现代中医药健康产业园 (千年药都创新升级)", 115.545, 28.065, "现代中医药"),
    ("南康现代家具国际博览中心 (中国现代实木家居之都)", 114.760, 25.660, "实木家居")
]

ind_palette = [
    ("#c0392b", "o", "航空制造/大飞机产业链"),
    ("#8e44ad", "s", "战略稀土/世界铜都有色金属"),
    ("#27ae60", "D", "锂电新能源/光伏组件极核"),
    ("#d35400", "^", "绿色石化/高端特钢新材料"),
    ("#1f618d", "p", "电子信息/现代中医药与特色轻工")
]

for idx, (iname, ilon, ilat, idesc) in enumerate(industries):
    ix_pt, iy_pt = to_alb(ilon, ilat)
    color, marker, kind_lbl = ind_palette[idx % len(ind_palette)]
    nm, nt = mapkit.split_note(iname)
    sl4.add(ix_pt, iy_pt, nm, f"ind_{idx}", note=idesc, priority=1,
            marker=marker, face=color, size=7.5, kind_label=kind_lbl)

sym_type_h, sym_idx_h = sl4.flush()

add_scalebar(ax, sb_x0, sb_y0, length_km=80)
add_compass(ax, 0.94, 0.92)

leg = mapkit.stacked_legends(ax, [
    dict(handles=sym_type_h, title="战略性支柱产业类别", ncol=1, fontsize=7.0, title_fontsize=7.8),
    dict(handles=sym_idx_h, title="图上先进制造龙头基地索引", ncol=1, fontsize=6.8, title_fontsize=7.8),
], top=-0.010, gap=0.014)

ax.set_title("江西省新兴产业集群与先进制造基地空间格局图", fontsize=13.0, fontweight="bold", pad=24, color=C_TEXT)
ax.text(0.5, 1.008, "Spatial Clusters of Emerging Industries & Modern Manufacturing in Jiangxi",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=7.8, color="#7f8c8d")
mapkit.footer_below_legend(
    ax, leg, "数据源：江西省工业和信息化厅 · 制造业重点产业链现代化建设“1269”行动计划 · 制作：《中国地理知识手册》",
    fontsize=6.8)

p4 = os.path.join(OUT_DIR, "fig14-00-4_江西省新兴产业集群与先进制造基地空间格局图.png")
fig.savefig(p4, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {p4}")

# =============================================================================
# 5. 1986—2024年夜间灯光演变与区域协调发展图 (fig14-00-5)
# =============================================================================
print("Generating Fig 14-00-5 (Nightlight Evolution 1986-2024)...")
fig, (ax_nl, ax_gdp) = plt.subplots(2, 1, figsize=(9.5, 8.5), dpi=DPI)
fig.patch.set_facecolor("white")

nl_clean_df = pd.read_csv(os.path.join(DATA_DIR, "jiangxi_nightlight_clean.csv"))
nl_prov = nl_clean_df.groupby("year")["sum"].sum().reset_index()

# 上图：夜间灯光演变
ax_nl.set_facecolor("#fbfcfc")
ax_nl.plot(nl_prov["year"], nl_prov["sum"] / 1000.0, color="#d35400", lw=2.4, marker="o", ms=4, zorder=5, label="江西省全域夜间灯光总强度 (DN×10³)")
ax_nl.fill_between(nl_prov["year"], 0, nl_prov["sum"] / 1000.0, color="#f8c471", alpha=0.25, zorder=3)

# 历史节点标注
nl_notes = [
    (1992, 22.0, "1992 邓小平南巡讲话\n昌九工业走廊与沿江开放提速"),
    (2001, 38.0, "2001 加入世贸组织\n东部沿海产业向赣加速梯度转移"),
    (2008, 125.0, "2008 应对国际金融危机\n鄱阳湖生态经济区升为国家战略"),
    (2012, 195.0, "2012 若干意见出台\n赣南等原中央苏区振兴全面突破")
]
for yr, yval, txt in nl_notes:
    sub_df = nl_prov[nl_prov["year"] == yr]
    if not sub_df.empty:
        curr_y = sub_df["sum"].values[0] / 1000.0
        ax_nl.annotate(txt, xy=(yr, curr_y), xytext=(yr, yval),
                       arrowprops=dict(arrowstyle="->", color="#78281f", lw=1.0),
                       fontsize=6.8, ha="center", va="bottom",
                       bbox=dict(boxstyle="round,pad=0.2", facecolor="#fef9e7", edgecolor="#f39c12", alpha=0.9))

ax_nl.set_title("江西省1986—2013年全域夜间灯光总辐射量演进轨迹 (DMSP/OLS卫星校准数据)", fontsize=9.2, fontweight="bold", color=C_TEXT)
ax_nl.set_ylabel("夜间灯光总值 (×10³ DN)", fontsize=7.5, color="#2c3e50")
ax_nl.set_xlim(1985, 2014)
ax_nl.grid(True, ls=":", alpha=0.6)
ax_nl.legend(loc="upper left", fontsize=7.2, frameon=True, facecolor="white")

# 下图：设区市 GDP 增长演化 (2000-2024)
from jiangxi_city_configs import JIANGXI_CONFIGS
ax_gdp.set_facecolor("#fbfcfc")
years = [2000, 2005, 2010, 2015, 2020, 2022, 2023, 2024]

city_plot_styles = {
    "360100": ("#c0392b", "-", 2.5, "南昌市 (省会龙头)"),
    "360700": ("#e67e22", "--", 2.0, "赣州市 (省域副中心)"),
    "360400": ("#2980b9", "-.", 1.8, "九江市 (沿江门户)"),
    "360900": ("#27ae60", ":", 1.8, "宜春市 (锂都黑马)"),
    "361100": ("#8e44ad", "-", 1.6, "上饶市 (高铁与光伏)"),
    "360800": ("#16a085", "--", 1.5, "吉安市 (革命摇篮)"),
    "361000": ("#d35400", "-.", 1.5, "抚州市 (才子之乡)"),
    "360600": ("#34495e", ":", 1.4, "鹰潭市 (世界铜都)"),
    "360200": ("#7f8c8d", "-", 1.4, "景德镇市 (千年瓷都)"),
    "360500": ("#b7950b", "--", 1.4, "新余市 (钢城锂都)"),
    "360300": ("#5d6d7e", ":", 1.4, "萍乡市 (红色工运)")
}

for code, (col, ls, lw, lbl) in city_plot_styles.items():
    cfg = JIANGXI_CONFIGS.get(code)
    if cfg and "gdp_series" in cfg:
        s = cfg["gdp_series"]
        y_vals = [s.get(y, np.nan) for y in years]
        ax_gdp.plot(years, y_vals, color=col, ls=ls, lw=lw, label=lbl, marker="s", ms=3.5)

ax_gdp.set_title("2000—2024年江西省11个设区市地区生产总值（GDP）跨越式梯次增长格局", fontsize=9.2, fontweight="bold", color=C_TEXT)
ax_gdp.set_xlabel("年份 Year", fontsize=7.5, color="#2c3e50")
ax_gdp.set_ylabel("地区生产总值 (亿元)", fontsize=7.5, color="#2c3e50")
ax_gdp.set_xlim(1999, 2025)
ax_gdp.grid(True, ls=":", alpha=0.6)
ax_gdp.legend(loc="upper left", bbox_to_anchor=(0.01, 0.98), ncol=3, fontsize=6.5, frameon=True, facecolor="white")

plt.tight_layout()
p5 = os.path.join(OUT_DIR, "fig14-00-5_江西省1986—2024年夜间灯光演变与区域协调发展图.png")
fig.savefig(p5, dpi=DPI, bbox_inches="tight")
plt.close(fig)
print(f"  ✓ Saved {p5}")

print("\nAll 5 Jiangxi Overview Figures successfully generated!")
